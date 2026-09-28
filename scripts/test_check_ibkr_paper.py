"""Offline checks; run with the isolated official-SDK Python environment."""
import unittest
from unittest.mock import patch

from ibapi.common import PROTOBUF_MSG_ID
from ibapi.contract import Contract
from ibapi.message import OUT
from check_ibkr_paper import Probe, contract_matches, paper_matches, permitted, quote_health, valid_price, console_summary
from ibapi.const import UNSET_DOUBLE


class ReadOnlyProbeTests(unittest.TestCase):
    def test_console_output_contains_status_not_raw_quote_values(self):
        report = {'prices': [{'price': 23456.75}], 'trade_timestamps': ['private timestamp'],
            'quote_health': {'bid': 23456.75, 'ask': 23457, 'two_sided_quote_observed': True},
            'errors': [{'code': 10167, 'message': 'sensitive diagnostic'}]}
        result = console_summary(report)
        self.assertEqual(result['price_callback_count'], 1)
        self.assertTrue(result['two_sided_quote_observed'])
        for excluded in ('23456', '23457', 'private timestamp', 'sensitive diagnostic'):
            self.assertNotIn(excluded, str(result))

    def test_sentinel_and_nonfinite_prices_are_missing(self):
        for price in (-1, 0, float('nan'), float('inf'), UNSET_DOUBLE):
            self.assertFalse(valid_price(price))

    def test_delayed_or_one_sided_prices_never_mean_real_time_ready(self):
        delayed = [{'tick_type': 66, 'price': 20000}, {'tick_type': 67, 'price': 20000.25}]
        self.assertTrue(quote_health(delayed, 3)['two_sided_quote_observed'])
        self.assertFalse(quote_health(delayed, 3)['real_time_two_sided_quote_observed'])
        self.assertFalse(quote_health(delayed, None)['real_time_two_sided_quote_observed'])
        self.assertFalse(quote_health([{'tick_type': 1, 'price': 20000}], 1)['two_sided_quote_observed'])
        crossed = [{'tick_type': 1, 'price': 20001}, {'tick_type': 2, 'price': 20000}]
        self.assertFalse(quote_health(crossed, 1)['two_sided_quote_observed'])

    def test_both_protocol_paths_block_orders_before_sending(self):
        probe = Probe('DU123')
        for msg in (OUT.PLACE_ORDER, OUT.CANCEL_ORDER, OUT.REQ_GLOBAL_CANCEL):
            with self.assertRaises(RuntimeError):
                probe.sendMsg(msg, '')
            with self.assertRaises(RuntimeError):
                probe.sendMsgProtoBuf(msg + PROTOBUF_MSG_ID, b'')
        self.assertEqual(probe.report['sent_message_ids'], [])

    def test_handshake_and_market_data_allowed(self):
        for msg in (OUT.START_API, OUT.REQ_CONTRACT_DATA, OUT.REQ_MKT_DATA):
            self.assertTrue(permitted(msg))
            self.assertTrue(permitted(msg + PROTOBUF_MSG_ID, True))
        self.assertFalse(permitted(999999))

    def test_account_gate_rejects_live_unknown_or_mixed_accounts(self):
        self.assertTrue(paper_matches(['DU123'], 'DU123'))
        for accounts in ([], ['U123'], ['DU456'], ['DU123', 'U123']):
            self.assertFalse(paper_matches(accounts, 'DU123'))
        self.assertFalse(paper_matches(['U123'], 'U123'))

    def test_contract_gate_rejects_other_expiry_or_product(self):
        c = Contract()
        values = dict(conId=793356225, secType='FUT', localSymbol='MNQU6',
            exchange='CME', currency='USD', multiplier='2',
            lastTradeDateOrContractMonth='20260918')
        for key, value in values.items():
            setattr(c, key, value)
        self.assertTrue(contract_matches(c))
        for key, value in values.items():
            with patch.object(c, key, 0 if key == 'conId' else 'wrong'):
                self.assertFalse(contract_matches(c))

    def test_known_data_error_redacts_account(self):
        probe = Probe('DU123')
        probe.error(102, 0, 10167, 'DU123 U987 not subscribed')
        self.assertNotIn('DU123', str(probe.report))
        self.assertNotIn('U987', str(probe.report))

    def test_december_resolution_rejects_wrong_contract_and_unknown_month(self):
        c = Contract()
        values = dict(conId=123, secType='FUT', localSymbol='MNQZ6',
            exchange='CME', currency='USD', multiplier='2',
            lastTradeDateOrContractMonth='20261218')
        for key, value in values.items():
            setattr(c, key, value)
        self.assertTrue(contract_matches(c, '202612'))
        self.assertFalse(contract_matches(c))
        self.assertFalse(contract_matches(c, '202703'))
        for key in values:
            with patch.object(c, key, 0 if key == 'conId' else 'wrong'):
                self.assertFalse(contract_matches(c, '202612'))


if __name__ == '__main__':
    unittest.main()
