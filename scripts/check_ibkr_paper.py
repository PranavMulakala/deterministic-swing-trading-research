"""Bounded, read-only TWS probe. Requires official ibapi 10.50.2.

Does not read credentials, place orders, or purchase market data. The caller
must supply the exact paper account observed in the authenticated TWS UI.
"""
import argparse
import json
import logging
import math
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from ibapi.client import EClient
from ibapi.common import PROTOBUF_MSG_ID
from ibapi.const import UNSET_DOUBLE
from ibapi.contract import Contract
from ibapi.message import OUT
from ibapi.wrapper import EWrapper
from ibapi.ticktype import TickTypeEnum


ALLOWED = frozenset((OUT.START_API, OUT.REQ_MANAGED_ACCTS,
    OUT.REQ_CURRENT_TIME, OUT.REQ_CONTRACT_DATA, OUT.REQ_MKT_DATA,
    OUT.CANCEL_MKT_DATA, OUT.REQ_MARKET_DATA_TYPE))


def permitted(message_id, protobuf=False):
    return message_id - (PROTOBUF_MSG_ID if protobuf else 0) in ALLOWED


def paper_matches(accounts, expected):
    return expected.startswith('DU') and accounts == [expected]


def contract_matches(c, contract_month='202609'):
    expected = {'202609': ('MNQU6', '20260918'),
                '202612': ('MNQZ6', '20261218')}.get(contract_month)
    if expected is None:
        return False
    return (c.conId > 0 and (contract_month != '202609' or c.conId == 793356225)
            and c.secType == 'FUT'
            and c.localSymbol == expected[0] and c.exchange == 'CME'
            and c.currency == 'USD' and c.multiplier == '2'
            and c.lastTradeDateOrContractMonth == expected[1])


def valid_price(price):
    return math.isfinite(price) and 0 < price < UNSET_DOUBLE


def quote_health(prices, data_type):
    """Separate a diagnostic quote from evidence usable for live paper comparison."""
    fields = (TickTypeEnum.BID, TickTypeEnum.ASK) if data_type in (1, 2) else (
        TickTypeEnum.DELAYED_BID, TickTypeEnum.DELAYED_ASK)
    latest = {x['tick_type']: x['price'] for x in prices}
    bid, ask = (latest.get(field, -1) for field in fields)
    usable = valid_price(bid) and valid_price(ask) and bid <= ask
    return {'bid': bid if valid_price(bid) else None,
        'ask': ask if valid_price(ask) else None,
        'two_sided_quote_observed': usable,
        'real_time_two_sided_quote_observed': usable and data_type == 1}


def console_summary(report):
    """Keep quote values in the local receipt, outside chat/tool output."""
    summary = {key: report[key] for key in (
        'started_utc', 'finished_utc', 'mode', 'handshake_verified',
        'expected_paper_account_verified', 'contract_verified',
        'requested_market_data_type', 'market_data_type', 'market_data_label',
        'valid_price_observed', 'paper_execution_tested', 'failure') if key in report}
    summary['price_callback_count'] = len(report.get('prices', []))
    summary['error_codes'] = [entry['code'] for entry in report.get('errors', [])]
    summary['two_sided_quote_observed'] = report.get('quote_health', {}).get('two_sided_quote_observed', False)
    summary['real_time_two_sided_quote_observed'] = report.get('quote_health', {}).get('real_time_two_sided_quote_observed', False)
    return summary


class Probe(EWrapper, EClient):
    def __init__(self, expected):
        EClient.__init__(self, self)
        self.expected = expected
        self.ready = threading.Event()
        self.accounts_ready = threading.Event()
        self.contract_ready = threading.Event()
        self.accounts = []
        self.contracts = []
        self.report = {'started_utc': datetime.now(timezone.utc).isoformat(),
            'mode': 'read_only_no_orders', 'endpoint': '127.0.0.1:7497',
            'handshake_verified': False, 'expected_paper_account_verified': False,
            'contract_verified': False, 'market_data_type': None,
            'prices': [], 'trade_timestamps': [], 'errors': [], 'sent_message_ids': []}

    def sendMsg(self, msgId, msg):
        if not permitted(msgId):
            raise RuntimeError('Outbound request blocked by read-only allowlist')
        self.report['sent_message_ids'].append(msgId)
        return super().sendMsg(msgId, msg)

    def sendMsgProtoBuf(self, msgId, msg):
        if not permitted(msgId, True):
            raise RuntimeError('Outbound protobuf request blocked by read-only allowlist')
        self.report['sent_message_ids'].append(msgId - PROTOBUF_MSG_ID)
        return super().sendMsgProtoBuf(msgId, msg)

    def nextValidId(self, orderId):
        self.report['handshake_verified'] = True
        self.ready.set()

    def managedAccounts(self, accountsList):
        self.accounts = sorted(x.strip() for x in accountsList.split(',') if x.strip())
        self.accounts_ready.set()

    def currentTime(self, timestamp):
        self.report['server_time_utc'] = datetime.fromtimestamp(timestamp, timezone.utc).isoformat()

    def contractDetails(self, reqId, details):
        if reqId == 101:
            self.contracts.append(details)

    def contractDetailsEnd(self, reqId):
        if reqId == 101:
            self.contract_ready.set()

    def marketDataType(self, reqId, marketDataType):
        if reqId == 102:
            self.report['market_data_type'] = marketDataType

    def tickPrice(self, reqId, tickType, price, attrib):
        if reqId == 102:
            self.report['prices'].append({'tick_type': tickType, 'price': price,
                'received_utc': datetime.now(timezone.utc).isoformat()})

    def tickString(self, reqId, tickType, value):
        if reqId == 102 and tickType in (TickTypeEnum.LAST_TIMESTAMP,
                TickTypeEnum.DELAYED_LAST_TIMESTAMP):
            try:
                stamp = datetime.fromtimestamp(int(value), timezone.utc).isoformat()
            except (ValueError, OverflowError, OSError):
                return
            self.report['trade_timestamps'].append({'tick_type': tickType,
                'exchange_trade_time_utc': stamp})

    def error(self, reqId, errorTime, errorCode, errorString, advancedOrderRejectJson=''):
        entry = {'request_id': reqId, 'code': errorCode}
        if reqId == 102 and errorCode in (10167, 10168, 10186, 10089, 354):
            entry['message'] = re.sub(r'\b(?:DU|U|F)\d+\b', '[account]',
                errorString.replace(self.expected, '[paper account]'))[:700]
        self.report['errors'].append(entry)


def run(expected, quote_seconds=15, market_data_type=3, contract_month='202609'):
    logging.disable(logging.CRITICAL)
    p = Probe(expected)
    if (market_data_type not in (1, 3, 4) or not 1 <= quote_seconds <= 30
            or contract_month not in ('202609', '202612')):
        raise ValueError('Invalid bounded quote diagnostic settings')
    p.report['requested_market_data_type'] = market_data_type
    stop = threading.Event()
    # A hard watchdog also bounds SDK connect/decoder failures.
    timer = threading.Timer(50, lambda: (stop.set(), p.disconnect()))
    timer.daemon = True
    timer.start()
    subscribed = False
    try:
        p.connect('127.0.0.1', 7497, clientId=71)
        threading.Thread(target=p.run, daemon=True).start()
        if not p.ready.wait(8):
            raise RuntimeError('api_handshake_not_received')
        p.report['server_version'] = p.serverVersion()
        p.reqManagedAccts()
        if not p.accounts_ready.wait(5) or not paper_matches(p.accounts, expected):
            raise RuntimeError('expected_paper_account_not_verified')
        p.report['expected_paper_account_verified'] = True
        p.reqCurrentTime()
        c = Contract()
        c.secType, c.exchange, c.currency = 'FUT', 'CME', 'USD'
        if contract_month == '202609':
            c.conId = 793356225
        else:
            c.symbol, c.multiplier = 'MNQ', '2'
            c.lastTradeDateOrContractMonth = contract_month
        p.reqContractDetails(101, c)
        if not p.contract_ready.wait(8):
            raise RuntimeError('contract_details_not_received')
        if len(p.contracts) != 1 or not contract_matches(p.contracts[0].contract, contract_month):
            raise RuntimeError('exact_mnq_contract_not_verified')
        d = p.contracts[0]
        p.report['contract_verified'] = True
        p.report['contract'] = {'con_id': d.contract.conId, 'symbol': d.contract.localSymbol,
            'expiry': d.contract.lastTradeDateOrContractMonth, 'multiplier': d.contract.multiplier,
            'minimum_tick': d.minTick}
        p.reqMarketDataType(market_data_type)
        p.reqMktData(102, d.contract, '', False, False, [])
        subscribed = True
        stop.wait(quote_seconds)
    except Exception as exc:
        p.report['failure'] = str(exc) if type(exc) is RuntimeError else type(exc).__name__
    finally:
        if subscribed and p.isConnected():
            p.cancelMktData(102)
        p.disconnect()
        timer.cancel()
    p.report['finished_utc'] = datetime.now(timezone.utc).isoformat()
    p.report['market_data_label'] = {1: 'real_time', 2: 'frozen',
        3: 'delayed', 4: 'delayed_frozen'}.get(p.report['market_data_type'], 'unverified')
    p.report['valid_price_observed'] = any(valid_price(x['price']) for x in p.report['prices'])
    p.report['quote_health'] = quote_health(p.report['prices'], p.report['market_data_type'])
    p.report['paper_execution_tested'] = False
    return p.report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-paper-account', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--quote-seconds', type=int, choices=range(1, 31), default=15)
    parser.add_argument('--market-data-type', type=int, choices=(1, 3, 4), default=3)
    parser.add_argument('--contract-month', choices=('202609', '202612'), default='202609')
    args = parser.parse_args()
    if not args.expected_paper_account.startswith('DU'):
        parser.error('Expected account must be a paper account verified in TWS')
    report = run(args.expected_paper_account, args.quote_seconds, args.market_data_type,
                 args.contract_month)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(console_summary(report), indent=2))
