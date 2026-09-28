from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import tempfile
import unittest
from research.lite_capital_diagnostic_v1 import run as r
from research.lite_reversal_v1 import experiment as e
from research.lite_reversal_v1.test_experiment import bars,config

class Tests(unittest.TestCase):
    def sample(self):return e.run_variant({'2026-09-09':bars('2026-09-09')},config(),'vwap_retest',10,'whole')
    def test_fixed_capital_only_and_unsupported_values(self):
        parent=config()
        for capital in r.CAPITALS:
            changed=asdict(r.capital_config(parent,capital));changed['initial_cash']=parent.initial_cash
            self.assertEqual(changed,asdict(parent))
        for capital in (True,1000,5000.0):
            with self.assertRaises(ValueError):r.capital_config(parent,capital)
    def test_complete_matrix_and_independent_ledgers(self):
        data={'2026-09-09':bars('2026-09-09')}
        result=r.matrix(data,None,config())
        self.assertEqual(len(result),12)
        for label,case in result.items():
            self.assertEqual(case['initial_cash'],int(label.split('_')[0]))
            self.assertEqual(case['independent_accounting']['status'],'PASS')
    def test_unmatched_or_empty_sessions_rejected(self):
        with self.assertRaises(ValueError):r.matrix({},None,config())
        with self.assertRaises(ValueError):r.matrix({'2026-09-09':bars()}, {},config())
    def test_repeat_matrix_is_identical(self):
        data={'2026-09-09':bars('2026-09-09')}
        self.assertEqual(r.matrix(data,None,config()),r.matrix(data,None,config()))
    def test_missing_duplicate_or_orphan_trades_rejected(self):
        for change in ('missing','duplicate','orphan'):
            run=self.sample()
            if change=='missing':run['trades']=[]
            elif change=='duplicate':run['trades']*=2
            else:run['trades'][0]['date']='2026-09-10'
            with self.subTest(change=change),self.assertRaises(ValueError):r.audit(run,500,.005)
    def test_every_accounting_field_tamper_is_detected(self):
        for field in ('equity_before','entry_debit','exit_credit','pnl','gross_pnl','modeled_costs','equity_after'):
            run=self.sample();run['trades'][0][field]+=1
            with self.subTest(field=field),self.assertRaises(ValueError):r.audit(run,500,.005)
    def test_sizing_and_terminal_tamper_rejected(self):
        for field,value in (('quantity',.5),('planned_risk',3),('planned_risk',-1),('entry_cap',0),('quantity',float('nan'))):
            run=self.sample();run['trades'][0][field]=value
            with self.assertRaises(ValueError):r.audit(run,500,.005)
        run=self.sample();run['summary']['final_cash']+=1
        with self.assertRaises(ValueError):r.audit(run,500,.005)
    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileExistsError):r.run(Path(folder))

if __name__=='__main__':unittest.main()
