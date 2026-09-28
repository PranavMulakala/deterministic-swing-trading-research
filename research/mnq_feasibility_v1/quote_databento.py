"""Authenticate and estimate the fixed pilot. No billable data endpoints."""
import base64
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler


ROOT = Path(__file__).resolve().parents[2]
DAYS = ('2026-08-31', '2026-09-01', '2026-09-02', '2026-09-03', '2026-09-04')
ALLOWED = frozenset(('metadata.list_datasets', 'metadata.get_cost'))


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def load_key():
    # Parse just this variable as data: never source .env or expand shell syntax.
    values = []
    for line in (ROOT / '.env').read_text().splitlines():
        match = re.match(r'^\s*(?:export\s+)?MNQ_RESEARCH_KEY\s*=\s*(.*?)\s*$', line)
        if match:
            value = match.group(1)
            if value.startswith(('"', "'")):
                quote = value[0]
                end = value.find(quote, 1)
                if end < 0 or (value[end + 1:].strip() and not value[end + 1:].strip().startswith('#')):
                    raise ValueError('Invalid key assignment format; value suppressed')
                value = value[1:end]
            else:
                value = value.split(' #', 1)[0].strip()
            values.append(value)
    if len(values) != 1 or not re.fullmatch(r'db-[A-Za-z0-9_-]+', values[0]):
        raise ValueError('Expected one nonempty Databento key; value suppressed')
    return values[0]


def metadata(endpoint, params, key):
    if endpoint not in ALLOWED:
        raise ValueError('Endpoint is not allowed by this quote-only helper')
    auth = base64.b64encode((key + ':').encode()).decode()
    request = Request('https://hist.databento.com/v0/' + endpoint + '?' + urlencode(params),
                      headers={'Authorization': 'Basic ' + auth, 'Accept': 'application/json'})
    with build_opener(NoRedirect()).open(request, timeout=30) as response:
        return json.loads(response.read())


def main():
    output = ROOT / 'research/mnq_feasibility_v1/runs/databento-quote-20260908.json'
    if output.exists():
        raise ValueError('Quote artifact already exists; refusing to overwrite')
    key = load_key()
    datasets = metadata('metadata.list_datasets', {}, key)
    if not isinstance(datasets, list) or 'GLBX.MDP3' not in datasets:
        raise ValueError('CME dataset was not returned; stopping')
    print('Authenticated successfully; CME dataset listed.', flush=True)
    quotes = []
    ranges = [('mbp-1', day + 'T13:30:00Z', day + 'T20:00:00Z') for day in DAYS]
    ranges.append(('definition', '2026-08-31T00:00:00Z', '2026-09-05T00:00:00Z'))
    for schema, start, end in ranges:
        params = dict(dataset='GLBX.MDP3', symbols='MNQU6', stype_in='raw_symbol',
                      schema=schema, start=start, end=end)
        cost = metadata('metadata.get_cost', params, key)
        if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not Decimal(str(cost)).is_finite() or cost < 0:
            raise ValueError('Unexpected cost response; response suppressed')
        quotes.append(dict(request=params, estimated_usd=str(cost)))
        print(json.dumps(quotes[-1]), flush=True)
    result = dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),
                  status='AUTHENTICATED_QUOTE_ONLY', quotes=quotes,
                  estimated_total_usd=str(sum(Decimal(q['estimated_usd']) for q in quotes)),
                  credits_not_verified=True, billable_data_requested=False,
                  note='Estimates are not charges. Instrument definitions and data completeness remain unverified.')
    with output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print('Estimated total USD:', result['estimated_total_usd'])
    print('Saved:', output)


if __name__ == '__main__':
    try:
        main()
    except HTTPError as error:
        print('Databento request failed: HTTP', error.code, '(response suppressed for credential safety)', file=sys.stderr)
        sys.exit(1)
    except URLError:
        print('Network/TLS connection failed; details suppressed for credential safety', file=sys.stderr)
        sys.exit(1)
    except Exception as error:
        print('Quote stopped:', type(error).__name__, '(details suppressed for credential safety)', file=sys.stderr)
        sys.exit(1)
