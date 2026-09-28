"""Injectable HTTPS email transport. No credential source or automatic sending."""
from __future__ import annotations

import json
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

ENDPOINT = "https://api.resend.com/emails"


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ValueError("email_redirect_blocked")


def strict_opener():
    """For authorized delivery only; prevents API-key forwarding on redirects."""
    return build_opener(ProxyHandler({}), _NoRedirect())


class ResendTransport:
    def __init__(self, *, api_key: str, sender: str, recipient: str, opener):
        if not isinstance(api_key,str) or not api_key.startswith("re_"):
            raise ValueError("invalid_email_api_key")
        if not sender or not recipient or "\n" in sender+recipient or "\r" in sender+recipient:
            raise ValueError("invalid_email_route")
        if opener is None or not callable(getattr(opener,"open",None)):
            raise ValueError("explicit_https_opener_required")
        self._api_key = api_key
        self._sender = sender
        self._recipient = recipient
        self._opener = opener

    def __call__(self, subject: str, body: str, idempotency_key: str) -> str:
        if not subject.startswith("[PAPER STOCK] ") or not body or not idempotency_key.startswith("paper-stock-"):
            raise ValueError("invalid_stock_email")
        payload = json.dumps({"from": self._sender, "to": [self._recipient],
                              "subject": subject, "text": body}, sort_keys=True).encode()
        request = Request(ENDPOINT, data=payload, method="POST", headers={
            "Authorization": "Bearer " + self._api_key,
            "Content-Type": "application/json",
            "User-Agent": "personal-stock-paper-research/1.0",
            "Idempotency-Key": idempotency_key,
        })
        with self._opener.open(request, timeout=20) as response:
            reply = json.loads(response.read(16384))
        provider_id = reply.get("id")
        if not isinstance(provider_id,str) or not provider_id:
            raise ValueError("missing_email_provider_receipt")
        return provider_id
