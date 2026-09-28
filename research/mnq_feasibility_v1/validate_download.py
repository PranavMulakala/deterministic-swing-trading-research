"""Offline transport, scope, definition, and streaming DBN structure checks.

This does not certify exchange completeness or implement the trading replay.
"""
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import importlib.metadata
import json
from pathlib import Path
import struct
import sys

from acquire_databento import DEST, ROOT, plan, save, sha256

sys.path.insert(0, str(ROOT / 'research/mnq_feasibility_v1/data/validation-tools'))
import databento_dbn as dbn
import numpy as np
import zstandard


DTYPE = np.dtype(dict(names=['length', 'rtype', 'publisher_id', 'instrument_id', 'ts_event',
    'price', 'size', 'action', 'side', 'flags', 'depth', 'ts_recv', 'ts_in_delta',
    'sequence', 'bid_px_00', 'ask_px_00', 'bid_sz_00', 'ask_sz_00', 'bid_ct_00', 'ask_ct_00'],
    formats=['u1', 'u1', '<u2', '<u4', '<u8', '<i8', '<u4', 'S1', 'S1', 'u1', 'u1',
    '<u8', '<i4', '<u4', '<i8', '<i8', '<u4', '<u4', '<u4', '<u4'],
    offsets=[0, 1, 2, 4, 8, 16, 24, 28, 29, 30, 31, 32, 40, 44, 48, 56, 64, 68, 72, 76],
    itemsize=80))


def ns(text):
    return int(datetime.fromisoformat(text.replace('Z', '+00:00')).timestamp()) * 1_000_000_000


def check_header(arr):
    assert len(arr) and np.all(arr['length'] == 20), 'Record length mismatch'
    assert np.all(arr['rtype'] == 1), 'Unexpected record type'
    assert np.all(arr['instrument_id'] == 42004800), 'Unexpected instrument'
    assert np.all(arr['publisher_id'] == 1), 'Unexpected publisher'


def compare_official_decoder(block, version):
    # Validate the vectorized layout against Databento's decoder throughout each file.
    decoder = dbn.DBNDecoder(has_metadata=False, input_version=version)
    rows = decoder.write_and_decode(block)
    array = np.frombuffer(block, dtype=DTYPE)
    assert len(rows) == len(array) and not decoder.buffer()
    for row, item in zip(rows, array):
        assert row.record_size() == 80
        for name in ['instrument_id', 'publisher_id', 'ts_event', 'ts_recv', 'price',
                     'size', 'flags', 'depth', 'ts_in_delta', 'sequence',
                     'bid_px_00', 'ask_px_00', 'bid_sz_00', 'ask_sz_00', 'bid_ct_00', 'ask_ct_00']:
            assert int(getattr(row, name)) == int(item[name]), name
        assert str(row.action).encode() == item['action']
        assert str(row.side).encode() == item['side']


def scan_market_file(path, request, expected_count):
    start, end = ns(request['start']), ns(request['end'])
    count = 0
    counts = Counter()
    actions = Counter()
    last_recv = last_event = None
    min_recv = min_event = 2**64 - 1
    max_recv = max_event = 0
    trade_minutes = set()
    sampled_records = 0
    with path.open('rb') as stream, zstandard.ZstdDecompressor().stream_reader(stream) as reader:
        prefix = reader.read(8)
        assert len(prefix) == 8 and prefix[:3] == b'DBN' and prefix[3] == 3
        length = struct.unpack('<I', prefix[4:])[0]
        assert length < 1_000_000
        metadata = dbn.Metadata.decode(prefix + reader.read(length))
        assert metadata.dataset == 'GLBX.MDP3' and str(metadata.schema) == 'mbp-1'
        assert metadata.symbols == ['MNQU6'] and not metadata.partial and not metadata.not_found
        assert metadata.start == start and metadata.end == end and not metadata.ts_out
        remainder = b''
        while True:
            incoming = reader.read(80 * 100_000)
            if not incoming:
                break
            block = remainder + incoming
            whole = len(block) // 80 * 80
            remainder = block[whole:]
            block = block[:whole]
            if not block:
                continue
            arr = np.frombuffer(block, dtype=DTYPE)
            check_header(arr)
            # Cross-check first and last records of every block with the official decoder.
            sample = block[:80 * min(5, len(arr))] + block[-80 * min(5, len(arr)):]
            compare_official_decoder(sample, metadata.version)
            sampled_records += len(sample) // 80
            count += len(arr)
            recv, event = arr['ts_recv'], arr['ts_event']
            assert np.all((recv >= start) & (recv < end)), 'Capture timestamp outside request'
            counts['receive_time_regressions'] += int(np.count_nonzero(recv[1:] < recv[:-1]))
            counts['event_time_regressions'] += int(np.count_nonzero(event[1:] < event[:-1]))
            if last_recv is not None:
                counts['receive_time_regressions'] += int(recv[0] < last_recv)
                counts['event_time_regressions'] += int(event[0] < last_event)
            last_recv, last_event = int(recv[-1]), int(event[-1])
            min_recv, max_recv = min(min_recv, int(recv.min())), max(max_recv, int(recv.max()))
            min_event, max_event = min(min_event, int(event.min())), max(max_event, int(event.max()))
            counts['event_timestamps_outside_capture_window'] += int(np.count_nonzero((event < start) | (event >= end)))
            for name, mask in [('bad_receive_timestamp_flag', dbn.F_BAD_TS_RECV),
                               ('maybe_bad_book_flag', dbn.F_MAYBE_BAD_BOOK),
                               ('snapshot_flag', dbn.F_SNAPSHOT)]:
                counts[name] += int(np.count_nonzero(arr['flags'] & mask))
            good = (arr['bid_px_00'] != dbn.UNDEF_PRICE) & (arr['ask_px_00'] != dbn.UNDEF_PRICE)
            counts['undefined_bid_or_ask'] += int(np.count_nonzero(~good))
            counts['crossed_book'] += int(np.count_nonzero(good & (arr['bid_px_00'] > arr['ask_px_00'])))
            counts['locked_book'] += int(np.count_nonzero(good & (arr['bid_px_00'] == arr['ask_px_00'])))
            for field in ['price', 'bid_px_00', 'ask_px_00']:
                defined = arr[field] != dbn.UNDEF_PRICE
                counts[field + '_off_tick'] += int(np.count_nonzero(defined & (arr[field] % 250_000_000 != 0)))
            trade = arr['action'] == b'T'
            # Minute coverage is a diagnostic, not proof of exchange completeness.
            in_session_trade = trade & (event >= start) & (event < end)
            trade_minutes.update(int(x) for x in np.unique((event[in_session_trade] - start) // 60_000_000_000))
            kinds, amounts = np.unique(arr['action'], return_counts=True)
            actions.update({x.decode(): int(n) for x, n in zip(kinds, amounts)})
        assert not remainder, 'Truncated trailing DBN record'
    assert count == expected_count, 'Provider record count mismatch'
    return dict(filename=path.name, record_count=count, actions=dict(actions),
        capture_start_ns=min_recv, capture_last_ns=max_recv, event_min_ns=min_event, event_max_ns=max_event,
        trade_minutes_present=len(trade_minutes), expected_minutes=390,
        official_decoder_cross_checked_records=sampled_records, diagnostics=dict(counts))


def main():
    output = ROOT / 'research/mnq_feasibility_v1/runs/databento-validation-20260908.json'
    assert not output.exists(), 'Preserve previous validation artifacts'
    summary = json.loads((DEST / 'download-summary.json').read_text())
    assert len(summary['requests']) == 6
    scanned = []
    definitions = []
    files_checked = 0
    for i, request in enumerate(plan()):
        folder = DEST / ('request-%02d' % i)
        details = json.loads((folder / 'completed-job.json').read_text())
        assert details['state'] == 'done'
        for field in ['dataset', 'symbols', 'stype_in', 'schema']:
            assert details[field] == request[field]
        assert ns(details['start']) == ns(request['start']) and ns(details['end']) == ns(request['end'])
        meta = json.loads((folder / 'files/metadata.json').read_text())
        assert meta['job_id'] == details['id'] and meta['query']['symbols'] == ['MNQU6']
        assert meta['query']['start'] == ns(request['start']) and meta['query']['end'] == ns(request['end'])
        conditions = json.loads((folder / 'files/condition.json').read_text())
        assert conditions and all(x['condition'] == 'available' for x in conditions)
        listing = json.loads((folder / 'file-list.json').read_text())
        for item in listing:
            file = folder / 'files' / item['filename']
            assert file.stat().st_size == item['size'] and sha256(file) == item['hash'].removeprefix('sha256:')
            files_checked += 1
        dbns = sorted((folder / 'files').glob('*.dbn.zst'))
        assert len(dbns) == (1 if i < 5 else 5)
        if i < 5:
            scan = scan_market_file(dbns[0], request, details['record_count'])
            scanned.append(scan)
            print('Validated', dbns[0].name, scan['record_count'], 'records;', scan['trade_minutes_present'], 'trade minutes', flush=True)
        else:
            for file in dbns:
                decoder = dbn.DBNDecoder(compression=dbn.Compression.ZSTD)
                rows = decoder.write_and_decode(file.read_bytes())
                assert len(rows) == 2 and not decoder.buffer()
                meta, row = rows
                assert meta.symbols == ['MNQU6'] and str(meta.schema) == 'definition'
                assert row.raw_symbol == 'MNQU6' and row.instrument_id == 42004800
                assert row.asset == 'MNQ' and str(row.instrument_class) == 'F'
                assert row.min_price_increment == 250_000_000 and row.unit_of_measure_qty == 2_000_000_000
                definitions.append(dict(filename=file.name, instrument_id=row.instrument_id,
                    symbol=row.raw_symbol, currency=row.currency, tick_size='0.25', multiplier='2',
                    tick_value_usd='0.50', expiration_utc=datetime.fromtimestamp(row.expiration / 1e9, timezone.utc).isoformat()))
            assert len(definitions) == details['record_count']
    assert files_checked == summary['file_count'] == 28
    assert not list(DEST.glob('request-*/files/*.partial'))
    result = dict(status='DOWNLOAD_AND_STRUCTURAL_VALIDATION_COMPLETE',
        checked_at_utc=datetime.now(timezone.utc).isoformat(), files_verified=files_checked,
        compressed_files_bytes=summary['total_bytes'], provider_cost_usd=summary['provider_cost_usd'],
        market_record_count=sum(x['record_count'] for x in scanned), definition_record_count=len(definitions),
        market_files=scanned, definitions=definitions,
        tools={x: importlib.metadata.version(x) for x in ['databento-dbn', 'numpy', 'zstandard']},
        validator_sha256=sha256(Path(__file__)),
        limitations=['Not an independent exchange completeness audit.',
            'Capture-time request boundaries differ from event-time replay boundaries.',
            'Flags, trade/book semantics, sequencing, and replay importer require separate validation.',
            'No strategy results, paper orders, or live trading were produced.'])
    save(output, result)
    print('COMPLETE:', result['market_record_count'], 'market records;', files_checked, 'files verified', flush=True)
    print('Saved:', output)


if __name__ == '__main__':
    main()
