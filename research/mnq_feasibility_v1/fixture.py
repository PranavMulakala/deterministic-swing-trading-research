"""Invented market tape for exercising the entire signal-to-ledger pipeline."""
from .engine import MINUTE, SECOND, timestamp


def dataset():
    sessions = []
    for day, previous in [('2026-09-03', None), ('2026-09-04', '2026-09-03')]:
        start = timestamp(day, 9, 30)
        events = []
        for minute in range(390):
            prices = [40000]
            if previous is None and minute == 5:
                prices = [39950, 40050, 40000]
            if previous and minute == 14:
                prices = [39951, 39940]
            if previous and minute == 15:
                prices = [39941, 39952]
            if previous and minute == 16:
                prices = [39952]
            for k, price in enumerate(prices):
                events.append({'type': 'trade', 'ts_ns': start + minute * MINUTE + (k + 1) * SECOND,
                               'price_ticks': price, 'size': 100 if previous and minute in (14, 15) else 1000})
        if previous:
            # One quote per second around the artificial entry and exit.
            for second in range(14 * 60, 18 * 60):
                bid = 39953 + max(0, second - 16 * 60 - 1) * 8
                events.append({'type': 'quote', 'ts_ns': start + second * SECOND,
                               'bid_ticks': bid, 'ask_ticks': bid + 1, 'bid_size': 10, 'ask_size': 10})
        events.sort(key=lambda e: e['ts_ns'])
        for seq, event in enumerate(events):
            event['seq'] = seq
        sessions.append({'date': day, 'previous_date': previous, 'contract': 'MNQU6',
                         'regular_session_complete': True, 'events': events})
    return {'schema_version': 1, 'evidence': 'SYNTHETIC',
            'source': 'Invented fixture; neither prices nor profits are market observations',
            'time_basis': 'exchange_event_time', 'sessions': sessions}
