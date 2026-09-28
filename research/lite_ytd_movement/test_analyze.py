from dataclasses import replace
from datetime import datetime,timedelta
from decimal import Decimal
import json
import unittest
from zoneinfo import ZoneInfo

from research.lite_reversal_v1.experiment import Bar
from research.lite_ytd_movement.analyze import (
    ROOT, analyze, at_least, at_most, describe_session, group_summary, later_recovery, rate,
)


def fixture():
    start=datetime(2026,1,2,9,30,tzinfo=ZoneInfo("America/New_York"))
    return [Bar(start+timedelta(minutes=5*i),100,100,100,100,1,100) for i in range(78)]


class DescriptiveTests(unittest.TestCase):
    def test_exact_thresholds(self):
        self.assertTrue(at_least(101,100,1))
        self.assertFalse(at_least(100.999,100,1))
        self.assertTrue(at_most(99,100,-1))
        self.assertFalse(at_most(99.001,100,-1))

    def test_flat_day(self):
        row=describe_session("2026-01-02",fixture())
        self.assertFalse(row['opening_dip_1pct'])
        self.assertEqual(group_summary([row])['close_equal_open']['count'],1)
        self.assertEqual(row['sentiment'],'unknown')

    def test_recovery_requires_post_ten_prices(self):
        bars=fixture()
        bars[1]=replace(bars[1],l=99)
        for i in range(6,78):
            bars[i]=replace(bars[i],o=98,h=99,l=97,c=98)
        row=describe_session("2026-01-02",bars)
        self.assertTrue(row['opening_dip_1pct'])
        self.assertFalse(row['touched_open_after_ten'])
        self.assertEqual(group_summary([row])['still_down_touched_open']['count'],0)

    def test_first_touch_precision_and_final_bar_close(self):
        bars=fixture()
        bars[0]=replace(bars[0],l=99)
        for i in range(6,78):
            bars[i]=replace(bars[i],o=98,h=99,l=97,c=98)
        bars[10]=replace(bars[10],h=100)
        bars[-1]=replace(bars[-1],c=99)
        row=describe_session("2026-01-02",bars)
        self.assertTrue(row['touched_open_after_ten'])
        self.assertIn('10:20',row['first_touch_bar_start'])
        self.assertEqual(row['close'],99)
        self.assertFalse(row['above_open_at_close'])

    def test_late_dip_not_opening_dip(self):
        bars=fixture(); bars[6]=replace(bars[6],l=97)
        self.assertFalse(describe_session("2026-01-02",bars)['opening_dip_1pct'])

    def test_both_excursions_not_directional_sequence(self):
        bars=fixture(); bars[10]=replace(bars[10],h=105,l=95)
        result=group_summary([describe_session("2026-01-02",bars)])
        self.assertEqual(result['thresholds'][-1]['both']['count'],1)
        self.assertEqual(result['close_equal_open']['count'],1)

    def test_missing_or_reordered_bars_rejected(self):
        bars=fixture()
        with self.assertRaises(ValueError): describe_session('x',bars[:-1])
        bars[0],bars[1]=bars[1],bars[0]
        with self.assertRaises(ValueError): describe_session('x',bars)

    def test_empty_denominators(self):
        self.assertEqual(group_summary([]),{'n':0})
        self.assertIsNone(rate(0,0)['pct'])

    def test_censoring_excludes_early_success_without_full_window(self):
        rows=[dict(date='a',opening=100,opening_dip_1pct=True,below_open_at_ten=True,later_high=99,high=100),
              dict(date='b',opening=100,opening_dip_1pct=True,below_open_at_ten=True,later_high=101,high=101)]
        r=later_recovery(rows)
        self.assertEqual(r['observations'][0]['first_touch_session_offset'],1)
        self.assertEqual(r['fixed_horizons'][1]['full_window_rate']['denominator'],1)
        self.assertEqual(r['fixed_horizons'][1]['full_window_rate']['count'],1)
        self.assertIsNone(r['fixed_horizons'][2]['full_window_rate']['pct'])

    def test_unresolved_is_not_a_fabricated_win(self):
        rows=[dict(date='a',opening=100,opening_dip_1pct=True,below_open_at_ten=True,later_high=99,high=100)]
        r=later_recovery(rows)
        self.assertEqual(len(r['unresolved_at_snapshot_end']),1)
        self.assertEqual(r['fixed_horizons'][0]['full_window_rate']['count'],0)


class CachedEvidenceTests(unittest.TestCase):
    def test_independent_decimal_recount_all_sessions(self):
        # Independent parser/counting arithmetic; does not use describe_session,
        # the shared load_bars function or the threshold helpers to form expected counts.
        r=analyze()
        payload=json.loads((ROOT/r['source']).read_text(),parse_float=Decimal,parse_int=Decimal)
        grouped={}
        for b in payload['rows']:
            t=datetime.fromisoformat(b['t']).astimezone(ZoneInfo('America/New_York'))
            if 570<=60*t.hour+t.minute<960:
                grouped.setdefault(t.date().isoformat(),[]).append(b)
        expected_up=sum(bs[-1]['c']>bs[0]['o'] for bs in grouped.values())
        self.assertEqual(expected_up,r['summary']['close_above_open']['count'])
        dip_count=recovered=still_down=still_recovered=0
        for bs in grouped.values():
            self.assertEqual(len(bs),78)
            o=bs[0]['o']
            if min(b['l'] for b in bs[:6])<=o*Decimal('.99'):
                dip_count+=1
                hit=max(b['h'] for b in bs[6:])>=o
                recovered+=hit
                if bs[6]['o']<o:
                    still_down+=1; still_recovered+=hit
        s=r['summary']
        self.assertEqual((dip_count,recovered,still_down,still_recovered),
                         (s['opening_dips']['count'],s['dip_touched_open_after_ten']['count'],
                          s['dip_still_below_open_at_ten'],s['still_down_touched_open']['count']))
        for entry in s['thresholds']:
            k=Decimal(entry['threshold_pct'])/100
            up=sum(max(b['h'] for b in bs)>=bs[0]['o']*(1+k) for bs in grouped.values())
            down=sum(min(b['l'] for b in bs)<=bs[0]['o']*(1-k) for bs in grouped.values())
            self.assertEqual((up,down),(entry['high_at_least']['count'],entry['low_at_most']['count']))

    def test_group_counts_reconcile_and_results_repeat(self):
        r=analyze()
        self.assertEqual(r,analyze())
        self.assertEqual(sum(v['n'] for v in r['by_month'].values()),r['summary']['n'])
        self.assertEqual(sum(v['opening_dips']['count'] for v in r['by_month'].values()),
                         r['summary']['opening_dips']['count'])
        self.assertTrue(all(d['sentiment']=='unknown' for d in r['daily']))


if __name__=='__main__': unittest.main()
