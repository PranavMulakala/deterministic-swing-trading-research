"""Compare a causal online implementation to the pinned batch reference."""
import importlib.util
import json
from pathlib import Path
import unittest
from cloud.ibkr_paper_v1.signal_adapter import MinuteStream,MINUTE,NS,session_start

ROOT=Path(__file__).resolve().parents[2]
REF=ROOT/'vendor/reference_mnq/engine.py'
if not REF.exists():REF=ROOT/'research/mnq_feasibility_v1/engine.py'
spec=importlib.util.spec_from_file_location('frozen_mnq_reference',REF)
reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)


def fixture(day,second):
    events=[]
    for minute in range(390):
        prices=[40000]
        if not second and minute==5:prices=[39950,40050,40000]
        if second and minute==14:prices=[39951,39940]
        if second and minute==15:prices=[39941,39952]
        if second and minute==16:prices=[39952]
        for k,price in enumerate(prices):
            events.append({'type':'trade','ts_ns':session_start(day)+minute*MINUTE+(k+1)*NS,
                           'price_ticks':price,'size':100 if second and minute in (14,15) else 1000})
    return {'date':day,'contract':'MNQZ6','events':events}


class SignalTests(unittest.TestCase):
    def test_stream_matches_frozen_batch_without_future_trades(self):
        previous=fixture('2026-09-21',False)
        current=fixture('2026-09-22',True)
        prior_bars=reference.bars(previous)
        expected,_=reference.signals(current,previous,{'stop_buffer_ticks':2})
        self.assertEqual(len(expected),1)
        stream=MinuteStream(current['date'],'MNQZ6',prior_bars,'MNQZ6')
        for event in current['events']:
            stream.trade(event['ts_ns'],event['price_ticks'],event['size'])
            # Confirmation never appears while its bar remains open.
            self.assertTrue(all(s['signal_ns']<=event['ts_ns'] for s in stream.signals))
        stream.advance(session_start(current['date'])+390*MINUTE)
        self.assertEqual(stream.bars,reference.bars(current))
        actual=[{k:v for k,v in s.items() if k in expected[0]} for s in stream.signals]
        self.assertEqual(actual,expected)
        self.assertTrue(stream.minute_coverage_complete())

    def test_incomplete_prior_or_contract_roll_suppresses_signals(self):
        previous=fixture('2026-09-21',False)
        current=fixture('2026-09-22',True)
        for prior,contract in (({},'MNQZ6'),(reference.bars(previous),'MNQU6')):
            stream=MinuteStream(current['date'],'MNQZ6',prior,contract)
            for event in current['events']:stream.trade(event['ts_ns'],event['price_ticks'],event['size'])
            stream.advance(session_start(current['date'])+390*MINUTE)
            self.assertFalse(stream.warmup_ready)
            self.assertEqual(stream.signals,[])

    def test_missing_minute_latches_and_late_data_cannot_repair_it(self):
        stream=MinuteStream('2026-09-22','MNQZ6')
        start=session_start(stream.day)
        stream.trade(start+NS,40000,1)
        stream.advance(start+2*MINUTE)
        self.assertEqual(stream.halt,'MISSING_TRADE_MINUTE')
        with self.assertRaises(ValueError):stream.trade(start+MINUTE+NS,40000,1)
        self.assertFalse(stream.minute_coverage_complete())

if __name__=='__main__':unittest.main()
