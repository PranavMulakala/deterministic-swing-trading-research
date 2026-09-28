import base64
from decimal import Decimal
import json
from unittest import TestCase, mock

from . import quote_only as q

KEY = 'db-' + 'x' * 29  # Invented fixture, not a real credential.


class QuoteOnlyTests(TestCase):
    def test_fixed_scope(self):
        self.assertEqual(len(q.plan()), 5)
        for params in q.plan():
            self.assertEqual(params['symbols'], 'MNQU6')
            self.assertEqual(params['schema'], 'mbp-1')
            self.assertEqual(params['start'][11:], '13:30:00Z')
            self.assertEqual(params['end'][11:], '20:00:00Z')

    def test_rejects_downloads_and_broader_requests(self):
        with self.assertRaises(ValueError):
            q.build_request('batch.submit_job', q.plan()[0], KEY)
        with self.assertRaises(ValueError):
            q.build_request('get_cost', dict(q.plan()[0], symbols='ALL_SYMBOLS'), KEY)

    def test_key_only_in_auth_header(self):
        path, body, headers = q.build_request('get_cost', q.plan()[0], KEY)
        self.assertNotIn(KEY, path)
        self.assertNotIn(KEY.encode(), body)
        self.assertEqual(base64.b64decode(headers['Authorization'].split()[1]), (KEY+':').encode())

    def test_numeric_report_contains_no_key(self):
        calls = []
        def fake(method, params, key):
            calls.append(method)
            return 123 if method == 'get_record_count' else Decimal('0.125')
        with mock.patch('builtins.print'):
            r = q.collect_quotes(KEY, fake)
        self.assertEqual(r['total_quoted_usd'], '0.625')
        self.assertEqual(calls, ['get_record_count', 'get_cost']*5)
        self.assertNotIn(KEY, json.dumps(r))

    def test_redirect_not_followed(self):
        connection = mock.MagicMock()
        connection.getresponse.return_value.status = 302
        with mock.patch.object(q.http.client, 'HTTPSConnection', return_value=connection):
            with self.assertRaises(RuntimeError):
                q.metadata('get_cost', q.plan()[0], KEY)
        self.assertEqual(connection.request.call_count, 1)
        connection.close.assert_called_once()

    def test_non_numeric_and_empty_records_rejected(self):
        for method, raw in [('get_cost', b'NaN'), ('get_cost', b'true'),
                            ('get_cost', b'{"unexpected":"value"}'), ('get_record_count', b'0')]:
            connection = mock.MagicMock()
            response = connection.getresponse.return_value
            response.status = 200
            response.read.return_value = raw
            with mock.patch.object(q.http.client, 'HTTPSConnection', return_value=connection):
                with self.assertRaises(RuntimeError):
                    q.metadata(method, q.plan()[0], KEY)

    def test_noninteractive_input_refused(self):
        with mock.patch.object(q.sys.stdin, 'isatty', return_value=False), mock.patch('builtins.print'), mock.patch.object(q.getpass, 'getpass') as prompt:
            self.assertEqual(q.main(), 1)
            prompt.assert_not_called()

    def test_error_output_does_not_echo_secret(self):
        with mock.patch.object(q.sys.stdin, 'isatty', return_value=True), mock.patch.object(q.sys.stdout, 'isatty', return_value=True), mock.patch.object(q.getpass, 'getpass', return_value=KEY), mock.patch.object(q, 'collect_quotes', side_effect=RuntimeError(KEY)), mock.patch('builtins.print') as output:
            self.assertEqual(q.main(), 1)
            self.assertNotIn(KEY, str(output.call_args_list))
