from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from .engine import Ledger, config, digest, fill_quantity, initial, manage, mark, mock_proposal, select, stamp
from .fixtures import packet, resign, scenario, sourced
from .report import build, html_report


class ShadowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'ledger.sqlite'
        self.ledger=Ledger(self.path)
        self.cfg=config()

    def tearDown(self):
        self.ledger.close()
        self.tmp.cleanup()

    def tick(self,at,**kw):
        return self.ledger.step(packet(at,**kw))

    def test_exact_capital_and_risk(self):
        c,r,_=select(packet(),stamp(packet()['observed_at']),self.cfg)
        self.assertIsNone(r)
        self.assertEqual(c['loss_cents'],6730)
        for s in self.ledger.state().values(): self.assertEqual(s['cash_cents'],750000)
        for ask,accepted in ((72,True),(73,False)):
            q=packet(ask=ask,bid=ask-3)
            c,_,reject=select(q,stamp(q['observed_at']),self.cfg)
            self.assertEqual(c is not None,accepted)
            if not accepted: self.assertIn('risk_budget',reject)

    def test_decisions_commit_before_later_fills(self):
        first=self.ledger.step(packet())
        self.assertIsNone(first['state']['deterministic']['position'])
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM events').fetchone()[0],1)
        second=self.tick('2026-09-14T14:00:02+00:00')
        s=second['state']['deterministic']
        self.assertEqual(s['cash_cents'],743335)
        self.assertEqual(s['position']['entry_cents'],66)
        self.assertEqual(s['equity_cents'],749370)
        self.assertEqual(s['fees_cents'],65)
        self.assertEqual(s['position']['quantity'],1)

    def test_round_trip_arithmetic_and_matching_arms(self):
        for p in scenario(): self.ledger.step(p)
        states=self.ledger.state()
        for s in states.values():
            self.assertEqual(s['cash_cents'],751370)
            self.assertEqual(s['realized_cents'],1370)
            self.assertEqual(s['fees_cents'],130)
            self.assertEqual(s['slippage_cents'],200)
            self.assertEqual(s['spread_cents'],300)
            self.assertIsNone(s['position'])
        self.assertEqual({s['equity_cents'] for s in states.values()},{751370})

    def test_agent_critic_only_filters(self):
        p=packet(); ph=digest(p)
        critic=mock_proposal('critic',ph); critic['action']='veto'
        r=self.ledger.step(p,{'critic':critic})
        self.assertEqual(r['decisions']['analyst_critic']['verdict'],'agent_abstain_or_veto')
        self.assertEqual(r['decisions']['analyst']['verdict'],'accepted')
        self.assertIsNone(r['state']['analyst_critic']['pending'])

    def test_model_cannot_override_authority(self):
        for key in ('quantity','limit_cents','orders_enabled','risk','symbol','cash_cents'):
            with self.subTest(key=key):
                p=packet(); proposal=mock_proposal('analyst',digest(p)); proposal[key]=999
                db=Ledger(Path(self.tmp.name)/(key+'.sqlite'))
                result=db.step(p,{'analyst':proposal});db.close()
                self.assertEqual(result['decisions']['analyst']['verdict'],'invalid_proposal')
                self.assertEqual(result['decisions']['deterministic']['verdict'],'accepted')

    def test_proposal_must_cite_exact_input(self):
        proposal=mock_proposal('analyst','wrong')
        r=self.ledger.step(packet(),{'analyst':proposal})
        self.assertEqual(r['decisions']['analyst']['verdict'],'invalid_proposal')

    def test_restart_exact_recovery(self):
        self.ledger.step(packet())
        self.ledger.close(); self.ledger=Ledger(self.path)
        self.tick('2026-09-14T14:00:02+00:00')
        self.assertEqual(self.ledger.state()['deterministic']['fills'],1)
        self.ledger.close(); self.ledger=Ledger(self.path)
        self.assertEqual(self.ledger.state()['deterministic']['fills'],1)

    def test_duplicate_idempotent_and_conflict_rejected(self):
        p=packet(); first=self.ledger.step(p)
        self.assertEqual(first,self.ledger.step(p))
        changed=deepcopy(p); changed['extra']='conflict'
        with self.assertRaisesRegex(ValueError,'conflicting_duplicate'): self.ledger.step(changed)
        self.assertEqual(len(self.ledger.history()),1)

    def test_older_and_equal_time_rejected(self):
        self.ledger.step(packet())
        for t in ('2026-09-14T13:59:59+00:00','2026-09-14T14:00:00+00:00'):
            with self.assertRaisesRegex(ValueError,'out_of_order'):
                self.ledger.step(packet(t,event_id='new-id'))

    def test_atomic_rollback_before_append(self):
        with patch('research.agentic_shadow_indicative_v1.engine.manage',side_effect=RuntimeError('crash')):
            with self.assertRaises(RuntimeError): self.ledger.step(packet())
        self.assertEqual(len(self.ledger.history()),0)
        self.ledger.step(packet())
        self.assertEqual(len(self.ledger.history()),1)

    def test_fractional_partial_and_multiple_contracts_rejected(self):
        self.assertEqual(fill_quantity(1,0),0)
        self.assertEqual(fill_quantity(1,5),1)
        for requested,available in ((1,.5),(2,1),(1,True),(1,-1)):
            with self.assertRaises(ValueError): fill_quantity(requested,available)

    def test_ioc_timeout_and_price_movement(self):
        self.ledger.step(packet())
        r=self.tick('2026-09-14T14:01:01+00:00')
        self.assertIsNone(r['state']['deterministic']['position'])
        self.assertEqual(r['decisions']['deterministic']['actions'][0]['reason'],'ioc_timeout')
        r=self.tick('2026-09-14T14:01:03+00:00',ask=69,bid=66)
        self.assertEqual(r['decisions']['deterministic']['actions'][0]['reason'],'entry_limit_or_risk')

    def test_cannot_fill_using_decision_quote(self):
        self.ledger.step(packet())
        p=packet('2026-09-14T14:00:02+00:00')
        q=p['chain']['contracts'][0]['quote'];q['market_at']='2026-09-14T14:00:00+00:00';resign(q);resign(p['chain'])
        r=self.ledger.step(p)
        self.assertIsNone(r['state']['deterministic']['position'])
        self.assertEqual(r['decisions']['deterministic']['actions'][0]['reason'],'no_later_quote')

    def test_stale_missing_future_inputs_fail_closed(self):
        for key in ('chain','underlying','bars','calendar','events','news'):
            with self.subTest(missing=key):
                p=packet();del p[key]
                self.assertIsNone(select(p,stamp(p['observed_at']),self.cfg)[0])
        for key in ('chain','underlying','calendar','events','news'):
            with self.subTest(future=key):
                p=packet();p[key]['provenance']['received_at']='2026-09-14T14:00:01+00:00'
                self.assertIsNone(select(p,stamp(p['observed_at']),self.cfg)[0])
        p=packet();p['bars'][-1]['end']='2026-09-14T14:05:00+00:00';resign(p['bars'][-1])
        self.assertIsNone(select(p,stamp(p['observed_at']),self.cfg)[0])

    def test_quote_rejection_matrix(self):
        cases={'bid_cents':[-1,True,100], 'ask_cents':[float('nan'),0], 'bid_size':[0,.5],
               'ask_size':[0,.5], 'condition':['halted'],'symbol':['WRONG'],'volume':[0]}
        for field,values in cases.items():
            for value in values:
                with self.subTest(field=field,value=value):
                    p=packet();q=p['chain']['contracts'][0]['quote'];q[field]=value
                    if isinstance(value,float) and value!=value:
                        self.assertIsNone(select(p,stamp(p['observed_at']),self.cfg)[0]);continue
                    resign(q);resign(p['chain'])
                    self.assertIsNone(select(p,stamp(p['observed_at']),self.cfg)[0])

    def test_earnings_and_corporate_action_exclusion(self):
        for field,value in (('earnings','scheduled'),('earnings','unknown'),('corporate_actions','unknown')):
            p=packet();p['events'][field]=value;resign(p['events'])
            self.assertIsNone(select(p,stamp(p['observed_at']),self.cfg)[0])

    def test_contract_identity_and_adjustments(self):
        for field,value in (('right','S'),('multiplier',10),('adjusted',True),('symbol','WRONG'),('expiry','2026-09-14')):
            p=packet();c=p['chain']['contracts'][0]['contract'];c[field]=value;resign(c);resign(p['chain'])
            self.assertIsNone(select(p,stamp(p['observed_at']),self.cfg)[0])

    def test_duplicate_chain_and_incomplete_chain(self):
        p=packet();p['chain']['contracts']*=2;resign(p['chain'])
        self.assertEqual(select(p,stamp(p['observed_at']),self.cfg)[1],'duplicate_contract')
        p=packet();p['chain']['complete']=False;resign(p['chain'])
        self.assertIsNone(select(p,stamp(p['observed_at']),self.cfg)[0])

    def test_news_future_revision_and_missing_url(self):
        for future,url in ((True,'https://example.com'),(False,'')):
            p=packet();n=sourced({'headline':'test','url':url},p['observed_at'])
            if future:n['provenance']['received_at']='2026-09-14T14:00:01+00:00'
            p['news']['items']=[n];resign(p['news'])
            self.assertIsNone(select(p,stamp(p['observed_at']),self.cfg)[0])

    def test_daily_and_drawdown_thresholds_and_latches(self):
        s=initial(self.cfg)['deterministic'];s['day']='2026-09-14'
        s['cash_cents']=735001;mark(s,{},stamp(packet()['observed_at']),self.cfg)
        self.assertFalse(s['daily_pause'])
        s['cash_cents']=735000;mark(s,{},stamp(packet()['observed_at']),self.cfg)
        self.assertTrue(s['daily_pause'])
        s['cash_cents']=712500;mark(s,{},stamp(packet()['observed_at']),self.cfg)
        self.assertTrue(s['experiment_pause'])
        s['cash_cents']=750000;mark(s,{},stamp(packet()['observed_at']),self.cfg)
        self.assertTrue(s['experiment_pause']);self.assertTrue(s['daily_pause'])
        manage(s,{'event_id':'next'},stamp('2026-09-15T14:00:00+00:00'),self.cfg)
        self.assertFalse(s['daily_pause']);self.assertTrue(s['experiment_pause'])

    def test_pause_does_not_stop_exit_management(self):
        self.ledger.step(packet());self.tick('2026-09-14T14:00:02+00:00')
        s=self.ledger.state()['deterministic'];s['experiment_pause']=True;s['daily_pause']=True
        p=packet('2026-09-14T16:00:03+00:00')
        actions=manage(s,p,stamp(p['observed_at']),self.cfg)
        self.assertEqual(s['pending']['side'],'sell')
        p=packet('2026-09-14T16:00:05+00:00')
        actions=manage(s,p,stamp(p['observed_at']),self.cfg)
        self.assertIsNone(s['position']);self.assertTrue(s['experiment_pause'])
        self.assertTrue(any(a['kind']=='simulated_fill' for a in actions))

    def test_unknown_marks_are_not_option_prices_and_time_exit_continues(self):
        self.ledger.step(packet());self.tick('2026-09-14T14:00:02+00:00')
        r=self.ledger.step({'kind':'fixture','event_id':'missing','observed_at':'2026-09-14T16:01:00+00:00'})
        s=r['state']['deterministic']
        self.assertTrue(s['unknown_mark']);self.assertIsNone(s['position']['mark_cents'])
        self.assertEqual(s['pending']['side'],'sell')
        self.assertEqual(s['equity_cents'],743270)

    def test_expiry_DNE_lapse_and_no_stock_exposure(self):
        self.ledger.step(packet());self.tick('2026-09-14T14:00:02+00:00')
        r=self.ledger.step({'kind':'fixture','event_id':'expiry','observed_at':'2026-09-24T20:00:01+00:00'})
        s=r['state']['deterministic']
        self.assertIsNone(s['position']);self.assertIsNone(s['pending'])
        self.assertEqual(s['realized_cents'],-6665)
        self.assertEqual(s['breaches'][0]['forfeited_intrinsic'],'unknown')

    def test_exit_zero_bid_size_stays_unresolved(self):
        for p in scenario()[:3]:self.ledger.step(p)
        p=packet('2026-09-14T16:00:05+00:00');q=p['chain']['contracts'][0]['quote'];q['bid_size']=0;resign(q);resign(p['chain'])
        r=self.ledger.step(p)
        self.assertIsNotNone(r['state']['deterministic']['position'])
        self.assertEqual(r['state']['deterministic']['pending']['side'],'sell')

    def test_ledger_hash_tamper_and_sql_mutation_guard(self):
        self.ledger.step(packet())
        with self.assertRaises(sqlite3.IntegrityError):self.ledger.db.execute("UPDATE events SET hash='x'")
        self.ledger.db.execute('DROP TRIGGER no_event_update')
        self.ledger.db.execute("UPDATE events SET hash='x'")
        with self.assertRaisesRegex(ValueError,'ledger_integrity'):self.ledger.history()

    def test_fixture_and_indicative_ledgers_cannot_mix(self):
        with self.assertRaisesRegex(ValueError,'mismatch'):Ledger(self.path,'indicative')
        p=packet();p['kind']='observed'
        with self.assertRaisesRegex(ValueError,'invalid_envelope'):self.ledger.step(p)

    def test_indicative_wall_clock_future_and_old(self):
        db=Ledger(Path(self.tmp.name)/'indicative.sqlite','indicative')
        p=packet();p['kind']='indicative'
        for now in (stamp(p['observed_at'])-timedelta(seconds=1),stamp(p['observed_at'])+timedelta(seconds=61)):
            with self.assertRaisesRegex(ValueError,'not_current'):db.step(p,now=now)
        db.close()

    def test_report_has_evidence_and_rejections(self):
        self.ledger.step(packet(ask=100,bid=97))
        r=build(self.ledger)
        self.assertEqual(r['contract_rejections']['risk_budget'],1)
        self.assertEqual(r['evidence_kind'],'fixture')
        self.assertIn('BLOCKED',r['real_data_readiness'])
        self.assertIn('Real-money options: DISABLED',html_report(r))

    def test_end_to_end_loss_pauses_across_sessions(self):
        for n in range(7):
            day=14+n//3
            minute=(n%3)*2
            start=f'2026-09-{day:02d}T14:{minute:02d}:'
            self.ledger.step(packet(start+'00+00:00'))
            self.ledger.step(packet(start+'02+00:00'))
            self.ledger.step(packet(start+'04+00:00',bid=10,ask=13))
            self.ledger.step(packet(start+'06+00:00',bid=10,ask=65))
            s=self.ledger.state()['deterministic']
            self.assertEqual(s['realized_cents'],-5830*(n+1))
            if n in (2,5): self.assertTrue(s['daily_pause'])
        self.assertTrue(s['experiment_pause'])
        self.assertEqual(s['max_drawdown_cents'],40810)
        self.assertIsNone(s['position'])
        r=self.ledger.step(packet('2026-09-16T14:10:00+00:00'))
        self.assertEqual(r['decisions']['deterministic']['verdict'],'entry_pause')

    def test_stale_quote_and_market_before_publication(self):
        for qt in ('2026-09-14T13:59:00+00:00','2026-09-14T14:00:01+00:00'):
            p=packet();q=p['chain']['contracts'][0]['quote'];q['market_at']=qt;resign(q);resign(p['chain'])
            self.assertIsNone(select(p,stamp(p['observed_at']),self.cfg)[0])

    def test_indicative_rejects_relabelled_fixture(self):
        db=Ledger(Path(self.tmp.name)/'indicative.sqlite','indicative')
        p=packet();p['kind']='indicative';p['purpose']='plumbing_only';p['orders_enabled']=False
        with self.assertRaisesRegex(ValueError,'non_alpaca_evidence'): db.step(p,now=stamp(p['observed_at']))
        db.close()

    def test_malformed_quote_keeps_time_exit_management(self):
        self.ledger.step(packet());self.tick('2026-09-14T14:00:02+00:00')
        p=packet('2026-09-14T16:01:00+00:00');p['chain']=None
        r=self.ledger.step(p)
        self.assertTrue(r['state']['deterministic']['unknown_mark'])
        self.assertEqual(r['state']['deterministic']['pending']['side'],'sell')

    def test_learning_cannot_rewrite_rules_or_decisions(self):
        from .learning import propose
        p=packet();self.ledger.step(p)
        before=self.ledger.history()
        path=propose(self.ledger,Path(self.tmp.name)/'suggestions','Evaluate later, never promote automatically',[p['event_id']])
        self.assertEqual(json.loads(path.read_text())['status'],'PROPOSED_ONLY')
        self.assertEqual(before,self.ledger.history())
        with self.assertRaises(ValueError):propose(self.ledger,Path(self.tmp.name),'bad',['future-event'])

    def test_cli_malformed_indicative_input_emits_blocked_report(self):
        from .run import main
        path=Path(self.tmp.name)/'bad.json';path.write_text('{broken')
        state=Path(self.tmp.name)/'runtime'
        with patch('sys.argv',['shadow','--kind','indicative','--state',str(state),'--input',str(path)]):main()
        report=json.loads((state/'report.json').read_text())
        self.assertIn('BLOCKED',report['real_data_readiness'])
        self.assertEqual(report['ingestion_error'],'JSONDecodeError')
        self.assertEqual(report['observations'],1)

    def test_concurrent_duplicate_has_one_committed_event(self):
        import concurrent.futures
        def worker():
            db=Ledger(self.path)
            try:return db.step(packet())['packet_hash']
            finally:db.close()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            a,b=list(pool.map(lambda _:worker(),range(2)))
        self.assertEqual(a,b)
        self.assertEqual(len(self.ledger.history()),1)

    def test_sourced_expiry_time_required(self):
        p=packet();del p['chain']['contracts'][0]['contract']['expiry_at']
        resign(p['chain']['contracts'][0]['contract']);resign(p['chain'])
        self.assertIsNone(select(p,stamp(p['observed_at']),self.cfg)[0])

    def test_symlink_ledger_refused(self):
        other=Path(self.tmp.name)/'alias.sqlite';other.symlink_to(self.path)
        with self.assertRaises(PermissionError):Ledger(other)

    def test_rules_edited_fail_closed(self):
        with patch('research.agentic_shadow_indicative_v1.engine.config',side_effect=ValueError('frozen_rules_changed')):
            with self.assertRaisesRegex(ValueError,'frozen_rules_changed'):self.ledger.step(packet())


if __name__=='__main__':unittest.main()
