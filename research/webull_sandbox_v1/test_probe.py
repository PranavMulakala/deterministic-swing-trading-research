"""Offline boundary tests: fixtures only; never read credentials or call Webull."""
from contextlib import ExitStack, redirect_stdout
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from research.webull_sandbox_v1 import probe
import check_webull_sandbox as connection


class Response:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status_code = status
        self.content = json.dumps(payload).encode()

    def json(self):
        return self.payload


def request(path="/trading/accounts/list", **changes):
    fields = dict(url=f"https://{probe.HOST}{path}", method="GET", body=None)
    fields.update(changes)
    return SimpleNamespace(**fields)


class RequestBoundaryTests(unittest.TestCase):
    def test_probe_rejects_unsafe_requests_before_transport(self):
        cases = [
            (request(url="https://api.webull.com/trading/accounts/list"), {}),
            (request(url=f"http://{probe.HOST}/trading/accounts/list"), {}),
            (request(url=f"https://{probe.HOST}:443/trading/accounts/list"), {}),
            (request(url=f"https://user@{probe.HOST}/trading/accounts/list"), {}),
            (request(method="POST"), {}),
            (request(body=b"order"), {}),
            (request("/trading/orders/place"), {}),
            (request("/trading/accounts/list#fragment"), {}),
            (request("/trading/accounts/list?unexpected=1"), {}),
            (request(), {"verify": False}),
            (request(), {"verify": None}),
            (request(), {"verify": "/fixture/ca.pem"}),
            (request("/trading/assets/balances/get"), {}),
            (request("/trading/assets/balances/get?account_id=unknown"), {}),
            (request("/trading/assets/balances/get?account_id=known&account_id=known"), {}),
            (request("/market-data/futures/snapshots/list?symbols=MNQZ6&category=US_FUTURES"), {}),
            (request("/market-data/futures/snapshots/list?symbols=MNQU6&category=US_STOCK"), {}),
            (request("/market-data/futures/snapshots/list?symbols=MNQU6,MNQZ6&category=US_FUTURES"), {}),
            (request("/market-data/futures/depths/list?symbol=MNQU6&category=US_FUTURES&depth=2"), {}),
        ]
        for req, options in cases:
            with self.subTest(url=req.url, method=req.method, options=options):
                transport, trace = Mock(), []
                with self.assertRaises(ValueError):
                    probe.guard(transport, trace, {"known"})(None, req, **{"verify": True, **options})
                transport.assert_not_called()
                self.assertEqual(trace, [])

    def test_exact_verified_account_is_allowed_and_redirects_are_disabled(self):
        transport = Mock(return_value=Response({}, 302))
        trace = []
        result = probe.guard(transport, trace, {"known"})(
            None, request("/trading/assets/positions/list?account_id=known"),
            verify=True, allow_redirects=True,
        )
        self.assertEqual(result.status_code, 302)
        self.assertFalse(transport.call_args.kwargs["allow_redirects"])
        self.assertEqual(transport.call_count, 1)
        self.assertNotIn("known", json.dumps(trace))

    def test_probe_request_budget_cannot_be_exceeded(self):
        transport = Mock(return_value=Response([]))
        trace = []
        send = probe.guard(transport, trace, set())
        for _ in range(16):
            send(None, request(), verify=True)
        with self.assertRaisesRegex(ValueError, "request_budget_exceeded"):
            send(None, request(), verify=True)
        self.assertEqual(transport.call_count, 16)

    def test_connection_guard_has_same_transport_fences(self):
        cases = [
            request(url="https://api.webull.com/trading/accounts/list"),
            request(method="POST"), request(body="body"),
            request("/trading/accounts/list?account_id=known"),
        ]
        for req in cases:
            transport = Mock()
            with self.subTest(request=req), self.assertRaises(ValueError):
                connection.guarded_send(transport)(None, req, verify=True)
            transport.assert_not_called()
        for verify in (None, False, "/fixture/ca.pem"):
            with self.subTest(verify=verify), self.assertRaises(ValueError):
                connection.guarded_send(Mock())(None, request(), verify=verify)
        transport = Mock(return_value=Response({}, 302))
        connection.guarded_send(transport)(None, request(), verify=True, allow_redirects=True)
        self.assertFalse(transport.call_args.kwargs["allow_redirects"])


class CredentialAndEvidenceTests(unittest.TestCase):
    def test_credential_aliases_fail_closed(self):
        fixtures = [
            ({}, "missing_credentials"),
            ({"PAPER_TRADING_APP_KEY": "fixture-key"}, "incomplete_credential_pair"),
            ({"PAPER_TRADING_APP_SECRET": "fixture-secret"}, "incomplete_credential_pair"),
            ({"PAPER_TRADING_APP_KEY": "a", "PAPER_TRADING_APP_SECRET": "b",
              "PAPER_TRADING_API_KEY": "c", "PAPER_TRADING_API_SECRET": "d"},
             "conflicting_credential_aliases"),
        ]
        for values, expected in fixtures:
            with self.subTest(values=values), self.assertRaisesRegex(ValueError, expected):
                connection.credentials(values)
        values = {"PAPER_TRADING_APP_KEY": "a", "PAPER_TRADING_APP_SECRET": "b",
                  "PAPER_TRADING_API_KEY": "a", "PAPER_TRADING_API_SECRET": "b"}
        self.assertEqual(connection.credentials(values)[2:], ("a", "b"))

    def test_public_report_excludes_credentials_and_private_identifiers(self):
        payload = [{"account_id": "fixture-account", "account_number": "fixture-number",
                    "user_id": "fixture-user", "account_class": "FUTURES",
                    "x-app-secret": "fixture-secret", "x-access-token": "fixture-token",
                    "data": {"account_id": "nested-account", "symbol": "MNQU6"}}]
        result, raw = probe.request_result(Response(payload))
        self.assertIs(raw, payload)
        serialized = json.dumps(result)
        for forbidden in ("fixture-account", "fixture-number", "fixture-user",
                          "fixture-secret", "fixture-token", "nested-account"):
            self.assertNotIn(forbidden, serialized)
        self.assertEqual(result["public_fields"][0]["account_class"], "FUTURES")
        self.assertEqual(result["row_count"], 1)

    def test_invalid_or_rejected_evidence_is_not_returned_as_payload(self):
        malformed = Mock(status_code=200)
        malformed.json.side_effect = ValueError("fixture-secret")
        result, payload = probe.request_result(malformed)
        self.assertIsNone(payload)
        self.assertEqual(result["result"], "NON_JSON_RESPONSE")
        result, payload = probe.request_result(Response({"message": "fixture-secret"}, 417))
        self.assertIsNone(payload)
        self.assertEqual(result["http_status"], 417)
        self.assertNotIn("public_fields", result)
        self.assertIsNone(probe.rows({"unrelated": []}))
        self.assertEqual(probe.rows({"data": {"accounts": []}}), [])

    def test_http_200_malformed_evidence_still_blocks_access(self):
        malformed = Mock(status_code=200)
        malformed.json.side_effect = ValueError("bad json")
        for response in (malformed, Response(None), Response("not an object")):
            with self.subTest(response=response):
                result, payload = probe.request_result(response)
                self.assertIsNone(payload)
                self.assertIn("SNAPSHOT_UNAVAILABLE", probe.access_blockers({
                    "checks": {"snapshot": result}, "futures_account_count": 1}))

    def test_transport_exception_text_is_never_written_to_trace(self):
        for wrap in (
            lambda transport, trace: probe.guard(transport, trace, set()),
            connection.guarded_send,
        ):
            trace = []
            transport = Mock(side_effect=RuntimeError("fixture-secret signed request"))
            with self.assertRaises(RuntimeError):
                wrap(transport, trace)(None, request(), verify=True)
            self.assertNotIn("fixture-secret", json.dumps(trace))

    def test_validation_error_message_redacts_auth_and_account_values(self):
        key, secret, account = "KeyFixture", "SecretFixture", "AccountFixture"
        opaque = "abcd1234" * 8
        trace = []
        transport = Mock(return_value=Response({
            "error_code": "ILLEGAL_PARAMETER",
            "message": f"only these symbols are supported:[mesmain] {key} {secret} {account} {opaque}",
        }, 417))
        probe.guard(transport, trace, {account}, (key, secret))(
            None, request(), verify=True,
        )
        serialized = json.dumps(trace).lower()
        for private in (key, secret, account, opaque):
            self.assertNotIn(private.lower(), serialized)
        self.assertIn("only these symbols are supported:[mesmain]", trace[0]["error_message"])
        self.assertEqual(trace[0]["error_code"], "ILLEGAL_PARAMETER")
        self.assertFalse(trace[0]["mentions_permission"])
        self.assertFalse(trace[0]["mentions_subscription"])

    def test_main_missing_evidence_remains_not_ready_without_account_calls(self):
        # Imports use installed packages, but every I/O surface is replaced before main.
        for account_payload in ([], [{"account_type": "FUTURES", "account_id": "wrong-field"}]):
            recorded_trace = []
            original_guard = probe.guard

            def capture_guard(original, trace, account_ids, secret_values=()):
                recorded_trace.append(trace)
                return original_guard(original, trace, account_ids, secret_values)

            def account_response():
                # A previous successful endpoint must not become the status of a
                # later SDK/guard failure that occurs before transport is reached.
                recorded_trace[0].append({"path": "/trading/accounts/list", "status": 200})
                return Response(account_payload)

            trade = SimpleNamespace(
                account_v2=SimpleNamespace(get_account_list=Mock(side_effect=account_response),
                    get_account_balance=Mock(), get_account_position=Mock()),
                order_v3=SimpleNamespace(list_order_open=Mock()),
            )
            unavailable = Mock(side_effect=RuntimeError("fixture-secret inaccessible"))
            data = SimpleNamespace(instrument=SimpleNamespace(get_futures_instrument=unavailable),
                futures_market_data=SimpleNamespace(get_futures_snapshot=unavailable,
                                                    get_futures_depth=unavailable))
            with self.subTest(accounts=account_payload), TemporaryDirectory() as directory, ExitStack() as stack:
                stack.enter_context(patch.object(probe, "ROOT", Path(directory)))
                dotenv = stack.enter_context(patch("dotenv.dotenv_values", return_value={
                    "PAPER_TRADING_APP_KEY": "fixture-key", "PAPER_TRADING_APP_SECRET": "fixture-secret"}))
                stack.enter_context(patch("webull.core.client.ApiClient", return_value=Mock()))
                stack.enter_context(patch("webull.trade.trade_client.TradeClient", return_value=trade))
                stack.enter_context(patch("webull.data.data_client.DataClient", return_value=data))
                stack.enter_context(patch.object(probe, "guard", side_effect=capture_guard))
                network = stack.enter_context(patch("requests.Session.send", side_effect=AssertionError("network forbidden")))
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = probe.main()
                report = json.loads(output.getvalue())
                network.assert_not_called()
                dotenv.assert_called_once_with(Path(directory) / ".env", interpolate=False)
                self.assertEqual(report["execution_readiness"], "NOT_READY")
                self.assertEqual(exit_code, 2)
                self.assertEqual(report["result"], "ACCESS_BLOCKED")
                self.assertIn("FUTURES_BALANCE_UNAVAILABLE", report["access_blockers"])
                self.assertIn("SNAPSHOT_UNAVAILABLE", report["access_blockers"])
                self.assertIn("EXACTLY_ONE_FUTURES_ACCOUNT_REQUIRED", report["access_blockers"])
                self.assertEqual(report["futures_account_count"], 0)
                self.assertFalse(report["orders_enabled"])
                self.assertFalse(report["live_trial_authorized"])
                self.assertEqual(report["orders_submitted"], 0)
                self.assertEqual(report["checks"]["snapshot"]["result"], "REQUEST_FAILED")
                for failed_check in ("contract", "snapshot", "depth"):
                    for stale_field in ("status", "error_code", "error_message",
                                        "mentions_permission", "mentions_subscription"):
                        self.assertNotIn(stale_field, report["checks"][failed_check])
                self.assertNotIn("fixture-secret", output.getvalue())
                trade.account_v2.get_account_balance.assert_not_called()
                trade.account_v2.get_account_position.assert_not_called()
                trade.order_v3.list_order_open.assert_not_called()


if __name__ == "__main__":
    unittest.main()
