from __future__ import annotations

import html
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def write_paper_dashboard(
    status: dict[str, Any], events: list[dict[str, Any]], destination: Path
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(destination.parent, 0o700)
    if destination.is_symlink():
        raise PermissionError("paper dashboard may not be a symbolic link")
    safe_status = html.escape(json.dumps(_redact(status), indent=2, sort_keys=True))
    rows = []
    for event in reversed(events):
        payload = html.escape(json.dumps(_redact(event["payload"]), sort_keys=True))
        rows.append(
            "<tr>"
            f"<td>{event['seq']}</td>"
            f"<td>{html.escape(str(event['occurred_at']))}</td>"
            f"<td>{html.escape(str(event['event_type']))}</td>"
            f"<td><code>{payload}</code></td>"
            "</tr>"
        )
    body = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Swingbot Paper Status</title>
<style>
body {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; margin: 2rem; color: #17202a; }}
h1 {{ margin-bottom: .25rem; }}
.warning {{ padding: 1rem; background: #fff4d6; border-left: .35rem solid #d68910; }}
pre {{ background: #f4f6f7; padding: 1rem; overflow: auto; }}
table {{ width: 100%; border-collapse: collapse; font-size: .85rem; }}
th, td {{ border: 1px solid #d5d8dc; padding: .5rem; text-align: left; vertical-align: top; }}
th {{ background: #eaf2f8; position: sticky; top: 0; }}
code {{ white-space: pre-wrap; word-break: break-word; }}
</style>
</head>
<body>
<h1>Paper-only swingbot</h1>
<p class="warning">Point-in-time local report. It does not monitor after the process exits and it never authorizes an order.</p>
<h2>Current broker reconciliation</h2>
<pre>{safe_status}</pre>
<h2>Append-only event journal ({len(events)} events)</h2>
<table>
<thead><tr><th>Seq</th><th>Timestamp</th><th>Event</th><th>Payload</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
</body>
</html>
"""
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_name = temporary.name
            os.fchmod(temporary.fileno(), 0o600)
            temporary.write(body)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, destination)
        os.chmod(destination, 0o600)
    finally:
        if temporary_name is not None and os.path.exists(temporary_name):
            os.unlink(temporary_name)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for key, item in value.items():
            if key == "account_id":
                rendered = str(item)
                output[key] = f"[REDACTED]...{rendered[-4:]}"
            elif key == "session_id":
                output[key] = "[REDACTED]"
            else:
                output[key] = _redact(item)
        return output
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value
