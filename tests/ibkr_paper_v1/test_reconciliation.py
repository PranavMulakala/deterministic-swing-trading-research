from copy import deepcopy
from datetime import datetime,timezone
import unittest

from cloud.ibkr_paper_v1.reconciliation import inspect,epoch_ns
from cloud.ibkr_paper_v1.execution import NS,SYMBOL


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.start=epoch_ns('2026-09-22T14:00:00+00:00')
        self.snapshot={'version':1,'mode':'PAPER_READ_ONLY','paper_account_verified':True,
                       'orders_sent':False,'snapshot_is_atomic':False,'failure':None,'errors':[],
                       'started_at':'2026-09-22T14:00:00+00:00',
                       'ended_at':'2026-09-22T14:00:03+00:00',
                       'execution_history_scope':'BROKER_API_AVAILABLE_WINDOW_NOT_FULL_ACCOUNT_HISTORY',
                       'query_end_markers':{k:True for k in ('positions','orders','executions','summary')},
                       'records':[{'kind':k+'_end','receipt_ns':self.start+NS}
                                  for k in ('positions','orders','executions','summary')]}
        self.orders={100:{'side':'BUY','order_ref':'owned-entry','perm_id':800}}

    def check(self,snapshot=None,now=None,after=None):
        return inspect(snapshot or self.snapshot,self.orders,12345,75,
                       now or self.start+4*NS,after or self.start)

    def execution(self,**changes):
        r={'kind':'execution','receipt_ns':self.start+NS//2,'order_id':100,
           'perm_id':800,'client_id':75,'contract':SYMBOL,'con_id':12345,
           'side':'BOT','quantity':'1','price':'10000.25','order_ref':'owned-entry',
           'pending_price_revision':False,'execution_id':'TEST-EXEC',
           'broker_time':'20260922 14:00:00 UTC'}
        return dict(r,**changes)

    def fee(self,**changes):
        r={'kind':'commission','receipt_ns':self.start+2*NS,
           'execution_id':'TEST-EXEC','currency':'USD','commission_and_fees':'2.00'}
        return dict(r,**changes)

    def test_empty_flat_observation_never_authorizes_retry_or_full_history(self):
        result=self.check()
        self.assertEqual(result['status'],'OBSERVED_FLAT')
        self.assertFalse(result['history_complete'])
        self.assertFalse(result['retry_authorized'])
        self.assertFalse(result['snapshot_is_atomic'])

    def test_stale_preactivity_or_missing_callback_end_rejected(self):
        with self.assertRaises(ValueError):self.check(now=self.start+9*NS)
        with self.assertRaises(ValueError):self.check(after=self.start+1)
        s=deepcopy(self.snapshot);s['records'].pop()
        with self.assertRaises(ValueError):self.check(s)
        s=deepcopy(self.snapshot);s['paper_account_verified']=False
        with self.assertRaises(ValueError):self.check(s)

    def test_positions_open_orders_or_post_end_changes_block(self):
        for r in ({'kind':'position','con_id':12345,'quantity':'1'},
                  {'kind':'order','order_id':100}):
            s=deepcopy(self.snapshot)
            s['records'].insert(0,dict(r,receipt_ns=self.start+NS//2))
            with self.assertRaises(ValueError):self.check(s)
        s=deepcopy(self.snapshot)
        s['records'].append({'kind':'position','con_id':12345,'quantity':'0',
                             'receipt_ns':self.start+2*NS})
        with self.assertRaises(ValueError):self.check(s)

    def test_owned_execution_and_late_commission_are_preserved(self):
        s=deepcopy(self.snapshot);s['records'].insert(0,self.execution())
        self.assertIsNone(self.check(s)['executions'][0]['fee_cents'])
        s['records'] += [self.fee(),self.fee(receipt_ns=self.start+2*NS+1)]
        e=self.check(s)['executions'][0]
        self.assertEqual(e['price_ticks'],40001)
        self.assertEqual(e['fee_cents'],200)

    def test_foreign_or_revised_execution_requires_review(self):
        for changes in ({'client_id':76},{'order_id':101},{'contract':'OTHER'},
                        {'side':'SLD'},{'quantity':'2'},{'order_ref':'manual'},
                        {'pending_price_revision':True},{'perm_id':999}):
            s=deepcopy(self.snapshot);s['records'].insert(0,self.execution(**changes))
            with self.assertRaises(ValueError):self.check(s)

    def test_fee_precision_currency_and_conflicts_are_not_silently_rounded(self):
        for changes in ({'commission_and_fees':'1.005'},{'currency':'EUR'},
                        {'commission_and_fees':'NaN'},{'commission_and_fees':'-1'}):
            s=deepcopy(self.snapshot);s['records'].insert(0,self.execution())
            s['records'].append(self.fee(**changes))
            result=self.check(s)
            self.assertFalse(result['all_execution_fees_known'])
            self.assertIsNone(result['executions'][0]['fee_cents'])
        s=deepcopy(self.snapshot);s['records'].insert(0,self.execution())
        s['records'] += [self.fee(),self.fee(commission_and_fees='3.00')]
        with self.assertRaises(ValueError):self.check(s)

    def test_backward_callback_clock_is_not_sorted_away(self):
        s=deepcopy(self.snapshot);s['records'].append(self.fee(receipt_ns=self.start))
        with self.assertRaises(ValueError):self.check(s)
