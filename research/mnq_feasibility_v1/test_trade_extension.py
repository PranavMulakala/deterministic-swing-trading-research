"""Offline regressions for the trade-only extension; all prices are invented."""
import copy
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import screen_trade_extension as screen
from engine import MINUTE, SECOND, bars, signals, timestamp

CFG = json.loads((HERE / 'config.json').read_text())
DAY = '2026-08-04'
START = timestamp(DAY, 9, 30)
END = timestamp(DAY, 16)
TICK = 250_000_000


def rows(count=3):
    arr = screen.np.zeros(count, dtype=screen.SOURCE)
    for name, value in dict(length=12, rtype=0, publisher_id=1,
                            instrument_id=42004800, price=40000*TICK,
                            size=7, action=b'T', side=b'B').items():
        arr[name] = value
    arr['ts_event'] = START + screen.np.arange(count, dtype='<u8') + 10
    arr['ts_recv'] = arr['ts_event'] + 1
    arr['sequence'] = 123
    return arr


def pattern_sessions(confirmation=15, mirror=False):
    sessions = []
    for day in ('2026-08-03', DAY):
        events = []
        for minute in range(390):
            prices, size = [40000], 1000
            if day != DAY and minute == 5:
                prices = [39950, 40050, 40000]
            elif day == DAY and minute == confirmation - 1:
                prices, size = [39951, 39940], 100
            elif day == DAY and minute == confirmation:
                prices, size = [39952], 100
            for index, price in enumerate(prices):
                events.append(dict(type='trade', ts_ns=timestamp(day, 9, 30) + minute*MINUTE + (index+1)*SECOND,
                    seq=len(events), price_ticks=80000-price if mirror else price, size=size))
        sessions.append(dict(date=day, contract='MNQU6', events=events))
    return sessions


class TradeNormalizationTests(unittest.TestCase):
    def test_retains_all_trades_without_last_flag_and_preserves_identity(self):
        source = rows()
        source['flags'] = [0, screen.dbn.F_LAST, 0]
        # Exchange sequence is not a unique trade identifier.
        source['ts_event'][:] = START + 10
        result, excluded = screen.normalize(source, 41, START, END)
        self.assertEqual(excluded, 0)
        self.assertEqual(result['seq'].tolist(), [82, 84, 86])
        self.assertEqual(result['source_sequence'].tolist(), [123]*3)
        self.assertEqual(result['price_ticks'].tolist(), [40000]*3)
        self.assertEqual(result['flags'].tolist(), source['flags'].tolist())
        self.assertEqual(result['size'].tolist(), [7]*3)

    def test_event_boundary_exclusions_keep_original_ordinals(self):
        source = rows(4)
        source['ts_event'] = [START-1, START, END-1, END]
        source['ts_recv'][:] = START+100
        result, excluded = screen.normalize(source, 5, START, END)
        self.assertEqual(excluded, 2)
        self.assertEqual(result['ts_ns'].tolist(), [START, END-1])
        self.assertEqual(result['seq'].tolist(), [12, 14])
        self.assertEqual(result['ts_recv'].tolist(), [START+100]*2)

    def test_rejects_wrong_record_and_instrument_scope(self):
        for field, value in [('length',20), ('rtype',1), ('publisher_id',2),
                             ('instrument_id',42004801), ('action',b'A')]:
            with self.subTest(field=field):
                source = rows(); source[field][1] = value
                with self.assertRaises(ValueError):
                    screen.normalize(source, 0, START, END)

    def test_rejects_bad_flags(self):
        for flag in (screen.dbn.F_SNAPSHOT, screen.dbn.F_BAD_TS_RECV,
                     screen.dbn.F_MAYBE_BAD_BOOK):
            with self.subTest(flag=flag):
                source = rows(); source['flags'][1] = flag
                with self.assertRaises(ValueError):
                    screen.normalize(source, 0, START, END)

    def test_rejects_bad_prices_sizes_and_uint32_tick_overflow(self):
        for price in (0, -TICK, screen.dbn.UNDEF_PRICE, 40000*TICK+1,
                      (2**32+4)*TICK):
            with self.subTest(price=price):
                source = rows(); source['price'][1] = price
                with self.assertRaises(ValueError):
                    screen.normalize(source, 0, START, END)
        source = rows(); source['size'][1] = 0
        with self.assertRaises(ValueError):
            screen.normalize(source, 0, START, END)

    def test_rejects_capture_scope_event_order_and_empty_block(self):
        for recv in (START-1, END):
            source = rows(); source['ts_recv'][1] = recv
            with self.assertRaises(ValueError):
                screen.normalize(source, 0, START, END)
        source = rows(); source['ts_event'][1] = START
        with self.assertRaises(ValueError):
            screen.normalize(source, 0, START, END)
        with self.assertRaises(ValueError):
            screen.normalize(rows(0), 0, START, END)

    def test_chunk_boundaries_preserve_source_identity(self):
        source = rows(9)
        source['flags'][::2] = screen.dbn.F_LAST
        whole, excluded = screen.normalize(source, 21, START, END)
        left, _ = screen.normalize(source[:4], 21, START, END)
        right, _ = screen.normalize(source[4:], 25, START, END)
        screen.np.testing.assert_array_equal(whole, screen.np.concatenate([left, right]))
        self.assertEqual(excluded, 0)

    def test_official_decoder_accepts_independently_packed_48_byte_layout(self):
        # struct layout is constructed independently of the NumPy dtype.
        fmt = '<BBHIQqIccBBQiI'
        payload = struct.pack(fmt, 12, 0, 1, 42004800, START+15,
            40123*TICK, 37, b'T', b'A', screen.dbn.F_LAST, 4,
            START+20, -15, 4294967294)
        self.assertEqual(struct.calcsize(fmt), 48)
        screen.official_check(payload)
        parsed = screen.np.frombuffer(payload, dtype=screen.SOURCE)
        self.assertEqual(parsed['price'][0], 40123*TICK)
        self.assertEqual(parsed['ts_in_delta'][0], -15)
        self.assertEqual(parsed['sequence'][0], 4294967294)
        result, excluded = screen.normalize(parsed, 0, START, END)
        self.assertEqual(result['price_ticks'].tolist(), [40123])
        self.assertEqual(excluded, 0)
        with self.assertRaises((ValueError, RuntimeError)):
            screen.official_check(payload[:-1])


class IndependentSignalTests(unittest.TestCase):
    def test_real_trade_bar_pipeline_matches_both_directions_and_entry_boundaries(self):
        for confirmation, expected_count in ((13,0), (14,1), (15,1), (118,1), (119,0)):
            for mirror in (False, True):
                with self.subTest(confirmation=confirmation, mirror=mirror):
                    previous, current = pattern_sessions(confirmation, mirror)
                    expected, reason = signals(current, previous, CFG)
                    separate, counts = screen.independent_signals(DAY, bars(current), bars(previous), CFG)
                    self.assertIsNone(reason)
                    self.assertEqual(separate, expected)
                    self.assertEqual(len(expected), expected_count)
                    if expected_count:
                        self.assertEqual(expected[0]['direction'], -1 if mirror else 1)
                        self.assertEqual(expected[0]['signal_ns'], START+(confirmation+1)*MINUTE)
                        self.assertGreater(sum(counts.values()), 0)

    def test_strict_three_sd_prior_level_and_reversal_conditions(self):
        previous, current = pattern_sessions()
        pb = bars(previous)
        template = bars(current)
        original = template[14]
        # Test the enumerators on identical controlled bars to isolate predicates.
        cases = (
            (14, {'close': original['vwap'] - 3*original['sd']}),  # equality is insufficient
            (14, {'sd': 0}),
            (14, {'low': pb[5]['low']+1}),  # prior low no longer intersects bar A
            (15, {'close': original['high']}),  # reversal must strictly exceed A high
        )
        for minute, replacement in cases:
            cb = copy.deepcopy(template)
            cb[minute].update(replacement)
            with self.subTest(replacement=replacement), patch('engine.bars', side_effect=[pb, cb]):
                expected, reason = signals(current, previous, CFG)
                separate, _ = screen.independent_signals(DAY, cb, pb, CFG)
                self.assertIsNone(reason)
                self.assertEqual(separate, expected)
                self.assertEqual(separate, [])


class AcquisitionCompletenessTests(unittest.TestCase):
    def test_partial_paid_batch_cannot_create_import_or_report_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            research = root/'research/mnq_feasibility_v1'
            (research/'runs').mkdir(parents=True)
            (research/'runs/pre-import-frozen-files.json').write_text('{}')
            source = root/'source'; source.mkdir()
            (source/'download-summary.json').write_text(json.dumps({'requests':[{}]*13}))
            output, report = root/'import', root/'report'
            with patch.multiple(screen, ROOT=root, DEST=source, OUT=output, REPORT=report):
                with self.assertRaisesRegex(ValueError, 'Acquisition incomplete'):
                    screen.main()
            self.assertFalse(output.exists())
            self.assertFalse(report.exists())


if __name__ == '__main__':
    unittest.main()
