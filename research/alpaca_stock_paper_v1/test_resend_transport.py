import json
import unittest

from research.alpaca_stock_paper_v1.resend_transport import ENDPOINT, ResendTransport


class Response:
    def __enter__(self):
        return self

    def __exit__(self,*args):
        return False

    def read(self,limit):
        return b'{"id":"fake-provider-id"}'


class FakeOpener:
    def __init__(self):
        self.calls=[]

    def open(self,request,timeout):
        self.calls.append((request,timeout))
        return Response()


class TransportTests(unittest.TestCase):
    def test_requires_explicit_opener(self):
        with self.assertRaises(ValueError):
            ResendTransport(api_key="re_fake",sender="Paper <paper@example.com>",
                            recipient="owner@example.com",opener=None)

    def test_mocked_https_request_only(self):
        opener=FakeOpener()
        send=ResendTransport(api_key="re_fake",sender="Paper <paper@example.com>",
                             recipient="owner@example.com",opener=opener)
        self.assertEqual(send("[PAPER STOCK] Review", "Paper only", "paper-stock-key"),"fake-provider-id")
        request,timeout=opener.calls[0]
        self.assertEqual(request.full_url,ENDPOINT)
        self.assertEqual(timeout,20)
        self.assertEqual(request.get_header("Idempotency-key"),"paper-stock-key")
        self.assertEqual(json.loads(request.data)["to"],["owner@example.com"])


if __name__ == "__main__":
    unittest.main()
