import io
import json
import urllib.error
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch

from swingbot.alpaca_paper import (
    AlpacaPaperClient,
    AlpacaPaperError,
    _NoRedirect,
    _default_transport,
    _paper_order,
)
from swingbot.paper_journal import PaperJournal

from paper_fixtures import NOW, sample_permit, sample_proposal


class AlpacaPaperClientTests(unittest.TestCase):
    def test_constructor_rejects_live_trading_endpoint(self) -> None:
        with self.assertRaises(AlpacaPaperError):
            AlpacaPaperClient(
                "paper-key", "paper-secret",
                trading_base_url="https://api.alpaca.markets",
            )

        with self.assertRaisesRegex(AlpacaPaperError, "credentials are missing"):
            AlpacaPaperClient("", "paper-secret")
        for kwargs in (
            {"cancel_verification_attempts": 0},
            {"cancel_verification_interval_seconds": -1},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(
                AlpacaPaperError, "cancel verification settings"
            ):
                AlpacaPaperClient("paper-key", "paper-secret", **kwargs)

    def test_entry_payload_is_exact_paper_oto_with_native_stop(self) -> None:
        calls = []

        def transport(method, url, headers, body, timeout):
            calls.append((method, url, headers, body, timeout))
            payload = json.loads(body)
            return {
                "id": "broker-1",
                "client_order_id": payload["client_order_id"],
                "symbol": payload["symbol"],
                "side": payload["side"],
                "type": payload["type"],
                "time_in_force": payload["time_in_force"],
                "order_class": payload["order_class"],
                "status": "new",
                "qty": payload["qty"],
                "filled_qty": "0",
                "legs": [],
            }

        client = AlpacaPaperClient(
            "paper-key", "paper-secret", transport=transport,
            permit_validator=lambda *_: True,
        )
        proposal = sample_proposal()
        client.submit_entry(proposal, sample_permit(proposal))
        method, url, headers, raw, _ = calls[0]
        self.assertEqual(method, "POST")
        self.assertEqual(url, "https://paper-api.alpaca.markets/v2/orders")
        payload = json.loads(raw)
        self.assertEqual(
            payload,
            {
                "client_order_id": "swing-test-1",
                "extended_hours": False,
                "order_class": "oto",
                "qty": "1",
                "side": "buy",
                "stop_loss": {"stop_price": "118"},
                "symbol": "SPY",
                "time_in_force": "gtc",
                "type": "market",
            },
        )
        self.assertEqual(headers["APCA-API-KEY-ID"], "paper-key")
        self.assertNotIn("paper-key", url)
        self.assertNotIn("paper-secret", raw.decode())

    def test_transport_error_redacts_both_credentials(self) -> None:
        def transport(*_):
            raise RuntimeError("failure key-123 secret-456")

        client = AlpacaPaperClient("key-123", "secret-456", transport=transport)
        with self.assertRaises(AlpacaPaperError) as captured:
            client.get_account()
        self.assertNotIn("key-123", str(captured.exception))
        self.assertNotIn("secret-456", str(captured.exception))
        self.assertIn("[REDACTED]", str(captured.exception))

    def test_fractional_or_day_entry_is_rejected_by_adapter(self) -> None:
        client = AlpacaPaperClient(
            "key", "secret", transport=lambda *_: {}, permit_validator=lambda *_: True
        )
        proposal = sample_proposal(fractional=True)
        with self.assertRaises(AlpacaPaperError):
            client.submit_entry(proposal, sample_permit(proposal))

    def test_every_invalid_entry_envelope_is_rejected_before_transport(self) -> None:
        calls = []
        client = AlpacaPaperClient(
            "key", "secret", transport=lambda *args: calls.append(args),
            permit_validator=lambda *_: True,
        )
        base = sample_proposal()
        invalid = (
            replace(base, action="close_position"),
            replace(base, side="sell"),
            replace(base, order_type="limit"),
            replace(base, time_in_force="day"),
            replace(base, order_class="simple"),
            replace(base, stop_price=None),
            replace(base, extended_hours=True),
            replace(base, quantity=Decimal("0")),
            replace(base, maximum_entry_reference=None),
            replace(base, stop_price=base.maximum_entry_reference),
        )
        for proposal in invalid:
            with self.subTest(proposal=proposal):
                with self.assertRaises(AlpacaPaperError):
                    client.submit_entry(proposal, sample_permit(proposal))
        self.assertEqual(calls, [])

    def test_every_invalid_exit_and_cancel_envelope_is_rejected_before_transport(self) -> None:
        calls = []
        client = AlpacaPaperClient(
            "key", "secret", transport=lambda *args: calls.append(args),
            permit_validator=lambda *_: True,
        )
        base = sample_proposal(action="close_position")
        invalid = (
            replace(base, action="entry_oto"),
            replace(base, side="buy"),
            replace(base, quantity=Decimal("0")),
            replace(base, order_type="limit"),
            replace(base, time_in_force="gtc"),
            replace(base, order_class="oto"),
            replace(base, extended_hours=True),
            replace(base, stop_price=Decimal("118")),
            replace(base, maximum_entry_reference=Decimal("120")),
        )
        for proposal in invalid:
            with self.subTest(proposal=proposal):
                with self.assertRaises(AlpacaPaperError):
                    client.close_position(proposal, sample_permit(proposal))
        with self.assertRaisesRegex(AlpacaPaperError, "approved exit proposal"):
            entry = sample_proposal()
            client.cancel_order("stop-1", Decimal("118"), entry, sample_permit(entry))
        with self.assertRaisesRegex(AlpacaPaperError, "valid approved exit terms"):
            invalid_exit = replace(base, side="buy")
            client.cancel_order(
                "stop-1", Decimal("118"), invalid_exit, sample_permit(invalid_exit)
            )
        with self.assertRaisesRegex(AlpacaPaperError, "broker order id"):
            client.cancel_order("", Decimal("118"), base, sample_permit(base))
        with self.assertRaisesRegex(AlpacaPaperError, "stop price"):
            client.cancel_order("stop-1", Decimal("0"), base, sample_permit(base))
        with self.assertRaisesRegex(AlpacaPaperError, "approved protective stop id"):
            client.cancel_order("stop-2", Decimal("118"), base, sample_permit(base))
        self.assertEqual(calls, [])

    def test_mutation_without_matching_consumed_approval_permit_is_rejected(self) -> None:
        client = AlpacaPaperClient(
            "key", "secret", transport=lambda *_: {}, permit_validator=lambda *_: False
        )
        proposal = sample_proposal()
        wrong = sample_permit(sample_proposal(action="close_position"))
        with self.assertRaisesRegex(AlpacaPaperError, "approval permit"):
            client.submit_entry(proposal, wrong)

    def test_low_level_request_cannot_bypass_mutation_gate(self) -> None:
        calls = []
        client = AlpacaPaperClient(
            "key", "secret", transport=lambda *args: calls.append(args)
        )
        with self.assertRaisesRegex(AlpacaPaperError, "direct broker mutation"):
            client._request("POST", "/v2/orders", body={})
        with self.assertRaisesRegex(AlpacaPaperError, "direct broker mutation"):
            client._request("DELETE", "/v2/orders/order-1")
        with self.assertRaisesRegex(AlpacaPaperError, "direct broker mutation"):
            client._request(" post ", "/v2/orders", body={})
        with self.assertRaisesRegex(AlpacaPaperError, "unsupported broker HTTP method"):
            client._request("TRACE", "/v2/orders")
        self.assertEqual(calls, [])

    def test_malformed_entry_terms_are_rejected_before_permit_claim(self) -> None:
        claims = []
        client = AlpacaPaperClient(
            "key", "secret", transport=lambda *_: {},
            permit_validator=lambda *args: claims.append(args) or True,
        )
        proposal = sample_proposal()
        malformed = proposal.__class__(
            **{**proposal.__dict__, "quantity": proposal.quantity + proposal.quantity / 2}
        )
        with self.assertRaisesRegex(AlpacaPaperError, "whole-share"):
            client.submit_entry(malformed, sample_permit(malformed))
        self.assertEqual(claims, [])

    def test_real_journal_permit_allows_exactly_one_adapter_submission(self) -> None:
        with TemporaryDirectory() as directory:
            proposal = sample_proposal()
            journal = PaperJournal(Path(directory) / "journal.sqlite")
            journal.record_proposal(proposal)
            review = journal.record_review(
                proposal, quote_timestamp=NOW, bid="119.9", ask="120.1", reviewed_at=NOW
            )
            permit = journal.approve_and_consume(
                proposal, journal.confirmation_code_for_review(proposal, review),
                review_event_id=review["event_id"], session_id="session", now=NOW
            )
            calls = []

            def transport(method, url, headers, body, timeout):
                calls.append((method, url, headers, body, timeout))
                payload = json.loads(body)
                return {
                    "id": "one", "client_order_id": payload["client_order_id"],
                    "symbol": "SPY", "side": "buy", "type": "market",
                    "time_in_force": "gtc", "order_class": "oto", "status": "new",
                    "qty": "1", "filled_qty": "0", "legs": [],
                }

            client = AlpacaPaperClient(
                "key", "secret", transport=transport, permit_validator=journal.claim_permit
            )
            client.submit_entry(proposal, permit)
            with self.assertRaisesRegex(AlpacaPaperError, "unused journal-backed"):
                client.submit_entry(proposal, permit)
            self.assertEqual(len(calls), 1)

    def test_simple_order_wire_value_and_broker_fill_time_are_normalized(self) -> None:
        order = _paper_order(
            {
                "id": "exit-1",
                "client_order_id": "client-1",
                "symbol": "SPY",
                "side": "sell",
                "type": "market",
                "time_in_force": "day",
                "order_class": "",
                "status": "filled",
                "qty": "1",
                "filled_qty": "1",
                "filled_avg_price": "120",
                "filled_at": NOW.isoformat(),
                "extended_hours": False,
            }
        )
        self.assertEqual(order.order_class, "simple")
        self.assertEqual(order.filled_at, NOW)
        self.assertFalse(order.extended_hours)

    def test_broker_boolean_fields_must_be_real_json_booleans(self) -> None:
        with self.assertRaisesRegex(AlpacaPaperError, "non-boolean"):
            _paper_order(
                {
                    "id": "order-1", "client_order_id": "client-1", "symbol": "SPY",
                    "side": "buy", "type": "market", "time_in_force": "day",
                    "order_class": "", "status": "new", "qty": "1",
                    "filled_qty": "0", "extended_hours": "false",
                }
            )

    def test_broker_timestamps_must_include_an_offset(self) -> None:
        with self.assertRaisesRegex(ValueError, "UTC offset"):
            _paper_order(
                {
                    "id": "order-1", "client_order_id": "client-1", "symbol": "SPY",
                    "side": "sell", "type": "market", "time_in_force": "day",
                    "order_class": "", "status": "filled", "qty": "1",
                    "filled_qty": "1", "filled_avg_price": "120",
                    "filled_at": "2026-01-05T15:00:00", "extended_hours": False,
                }
            )

    def test_exit_adapter_requires_verified_stop_cancel_before_sell(self) -> None:
        with TemporaryDirectory() as directory:
            proposal = sample_proposal(action="close_position")
            journal = PaperJournal(Path(directory) / "journal.sqlite")
            journal.record_proposal(proposal)
            review = journal.record_review(
                proposal, quote_timestamp=NOW, bid="119.9", ask="120.1", reviewed_at=NOW
            )
            permit = journal.approve_and_consume(
                proposal,
                journal.confirmation_code_for_review(proposal, review),
                review_event_id=review["event_id"],
                session_id="session",
                now=NOW,
            )
            calls = []

            def transport(method, url, headers, body, timeout):
                calls.append((method, url, body))
                if method == "DELETE":
                    return None
                if method == "GET":
                    return {
                        "id": "stop-1", "client_order_id": "", "symbol": "SPY",
                        "side": "sell", "type": "stop", "time_in_force": "gtc",
                        "order_class": "", "status": "canceled", "qty": "1",
                        "filled_qty": "0", "stop_price": "118", "legs": [],
                        "extended_hours": False,
                    }
                payload = json.loads(body)
                return {
                    "id": "exit-1", "client_order_id": payload["client_order_id"],
                    "symbol": "SPY", "side": "sell", "type": "market",
                    "time_in_force": "day", "order_class": "", "status": "new",
                    "qty": "1", "filled_qty": "0", "legs": [],
                    "extended_hours": False,
                }

            client = AlpacaPaperClient(
                "key", "secret", transport=transport,
                permit_validator=journal.claim_permit,
            )
            with self.assertRaisesRegex(AlpacaPaperError, "verified protective-stop"):
                client.close_position(proposal, permit)
            stop = client.cancel_order(
                "stop-1", Decimal("118"), proposal, permit
            )
            self.assertEqual(stop.status, "canceled")
            journal.record_protective_stop_cancellation_verified(
                proposal, permit, stop_order_id="stop-1", verified_at=NOW
            )
            order = client.close_position(proposal, permit)
            self.assertEqual(order.order_class, "simple")
            self.assertEqual([call[0] for call in calls], ["DELETE", "GET", "POST"])

    def test_mismatched_stop_cancel_ack_never_unlocks_exit_submission(self) -> None:
        proposal = sample_proposal(action="close_position")
        permit = sample_permit(proposal)
        calls = []

        def transport(method, url, headers, body, timeout):
            calls.append((method, url, body))
            if method == "DELETE":
                return None
            return {
                "id": "different-stop",
                "client_order_id": "",
                "symbol": "QQQ",
                "side": "sell",
                "type": "stop",
                "time_in_force": "gtc",
                "order_class": "",
                "status": "canceled",
                "qty": "1",
                "filled_qty": "0",
                "stop_price": "118",
                "extended_hours": False,
                "legs": [],
            }

        client = AlpacaPaperClient(
            "key", "secret", transport=transport, permit_validator=lambda *_: True
        )
        with self.assertRaisesRegex(AlpacaPaperError, "differs from the managed stop"):
            client.cancel_order("stop-1", Decimal("118"), proposal, permit)
        with self.assertRaisesRegex(AlpacaPaperError, "verified protective-stop"):
            client.close_position(proposal, permit)
        self.assertEqual([call[0] for call in calls], ["DELETE", "GET"])

    def test_cancel_polls_until_terminal_and_partial_cancel_never_unlocks_sell(self) -> None:
        proposal = sample_proposal(action="close_position")
        permit = sample_permit(proposal)
        states = ["pending_cancel", "canceled"]
        sleeps = []
        calls = []

        def transport(method, url, headers, body, timeout):
            calls.append(method)
            if method == "DELETE":
                return None
            status = states.pop(0)
            return {
                "id": "stop-1", "client_order_id": "", "symbol": "SPY",
                "side": "sell", "type": "stop", "time_in_force": "gtc",
                "order_class": "", "status": status, "qty": "1",
                "filled_qty": "0", "stop_price": "118",
                "extended_hours": False, "legs": [],
            }

        client = AlpacaPaperClient(
            "key", "secret", transport=transport, permit_validator=lambda *_: True,
            cancel_verification_attempts=3,
            cancel_verification_interval_seconds=0.01,
            sleep=sleeps.append,
        )
        stop = client.cancel_order("stop-1", Decimal("118"), proposal, permit)
        self.assertEqual(stop.status, "canceled")
        self.assertEqual(calls, ["DELETE", "GET", "GET"])
        self.assertEqual(sleeps, [0.01])

        partial_calls = []

        def partial_transport(method, url, headers, body, timeout):
            partial_calls.append(method)
            if method == "DELETE":
                return None
            if method == "GET":
                return {
                    "id": "stop-1", "client_order_id": "", "symbol": "SPY",
                    "side": "sell", "type": "stop", "time_in_force": "gtc",
                    "order_class": "", "status": "canceled", "qty": "1",
                    "filled_qty": "0.5", "filled_avg_price": "118",
                    "filled_at": NOW.isoformat(), "stop_price": "118",
                    "extended_hours": False, "legs": [],
                }
            raise AssertionError(method)

        partial = AlpacaPaperClient(
            "key", "secret", transport=partial_transport,
            permit_validator=lambda *_: True,
        )
        observed = partial.cancel_order(
            "stop-1", Decimal("118"), proposal, permit
        )
        self.assertEqual(observed.filled_quantity, Decimal("0.5"))
        with self.assertRaisesRegex(AlpacaPaperError, "verified protective-stop"):
            partial.close_position(proposal, permit)
        self.assertEqual(partial_calls, ["DELETE", "GET"])

    def test_production_transport_rejects_changed_final_url(self) -> None:
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return None

            def geturl(self):
                return "https://api.alpaca.markets/v2/account"

            def read(self):
                return b"{}"

        class Opener:
            def open(self, *_args, **_kwargs):
                return Response()

        with patch("swingbot.alpaca_paper.urllib.request.build_opener", return_value=Opener()):
            with self.assertRaisesRegex(AlpacaPaperError, "response URL differs"):
                _default_transport(
                    "GET", "https://paper-api.alpaca.markets/v2/account", {}, None, 1
                )

    def test_production_transport_explicitly_disables_environment_proxies(self) -> None:
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return None

            def geturl(self):
                return "https://paper-api.alpaca.markets/v2/account"

            def read(self):
                return b"{}"

        opener = MagicMock()
        opener.open.return_value = Response()
        with patch(
            "swingbot.alpaca_paper.urllib.request.build_opener",
            return_value=opener,
        ) as build_opener:
            _default_transport(
                "GET", "https://paper-api.alpaca.markets/v2/account", {}, None, 1
            )
        handlers = build_opener.call_args.args
        self.assertEqual(len(handlers), 2)
        self.assertEqual(handlers[0].proxies, {})
        self.assertIs(handlers[1], _NoRedirect)

    def test_redirect_handler_rejects_redirect_before_following_it(self) -> None:
        with self.assertRaisesRegex(AlpacaPaperError, "redirects are prohibited"):
            _NoRedirect().redirect_request(
                None,
                None,
                302,
                "redirect",
                {},
                "https://api.alpaca.markets/v2/account",
            )

    def test_production_transport_response_and_failure_contract(self) -> None:
        class Response:
            def __init__(self, raw):
                self.raw = raw

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return None

            def geturl(self):
                return "https://paper-api.alpaca.markets/v2/account"

            def read(self):
                return self.raw

        class Opener:
            def __init__(self, result):
                self.result = result

            def open(self, *_args, **_kwargs):
                if isinstance(self.result, Exception):
                    raise self.result
                return self.result

        url = "https://paper-api.alpaca.markets/v2/account"
        cases = (
            (Response(b""), None, None),
            (Response(b'{"status":"ACTIVE"}'), {"status": "ACTIVE"}, None),
            (Response(b"not-json"), None, "invalid JSON"),
            (
                urllib.error.HTTPError(
                    url, 422, "unprocessable", {}, io.BytesIO(b'{"message":"bad request"}')
                ),
                None,
                "HTTP 422: bad request",
            ),
            (
                urllib.error.HTTPError(
                    url, 500, "error", {}, io.BytesIO(b"not-json")
                ),
                None,
                "HTTP 500: broker request failed",
            ),
            (urllib.error.URLError("offline"), None, "connection failed: offline"),
        )
        for result, expected, error in cases:
            with self.subTest(error=error, expected=expected):
                with patch(
                    "swingbot.alpaca_paper.urllib.request.build_opener",
                    return_value=Opener(result),
                ):
                    if error:
                        with self.assertRaisesRegex(AlpacaPaperError, error):
                            _default_transport("GET", url, {}, None, 1)
                    else:
                        self.assertEqual(
                            _default_transport("GET", url, {}, None, 1), expected
                        )


if __name__ == "__main__":
    unittest.main()
