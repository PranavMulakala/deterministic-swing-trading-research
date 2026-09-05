from __future__ import annotations

import csv
import hashlib
import json
import math
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

from .models import Bar


YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"


class DataError(RuntimeError):
    pass


def _epoch(day: str) -> int:
    parsed = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(parsed.timestamp())


def fetch_adjusted_daily(symbol: str, start_date: str, end_date: str) -> list[dict[str, object]]:
    # Yahoo treats period2 as exclusive.
    end_epoch = _epoch(end_date) + 86400
    params = urllib.parse.urlencode(
        {
            "period1": _epoch(start_date),
            "period2": end_epoch,
            "interval": "1d",
            "events": "div,splits",
            "includeAdjustedClose": "true",
        }
    )
    url = f"{YAHOO_CHART_URL.format(symbol=urllib.parse.quote(symbol))}?{params}"
    request = urllib.request.Request(url, headers={"User-Agent": "swing-research/0.1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    result = payload.get("chart", {}).get("result")
    if not result:
        raise DataError(f"no chart result for {symbol}: {payload.get('chart', {}).get('error')}")
    chart = result[0]
    timestamps = chart.get("timestamp", [])
    quote = chart.get("indicators", {}).get("quote", [{}])[0]
    adjusted = chart.get("indicators", {}).get("adjclose", [{}])[0].get("adjclose", [])
    rows: list[dict[str, object]] = []
    for i, timestamp in enumerate(timestamps):
        raw_close = _at(quote.get("close", []), i)
        adj_close = _at(adjusted, i)
        raw_open = _at(quote.get("open", []), i)
        raw_high = _at(quote.get("high", []), i)
        raw_low = _at(quote.get("low", []), i)
        if any(value is None for value in (raw_open, raw_high, raw_low, raw_close, adj_close)):
            continue
        assert raw_close is not None and adj_close is not None
        if raw_close <= 0 or adj_close <= 0:
            continue
        factor = adj_close / raw_close
        values = [raw_open * factor, raw_high * factor, raw_low * factor, adj_close]
        if not all(math.isfinite(value) and value > 0 for value in values):
            continue
        rows.append(
            {
                "date": datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat(),
                "open": values[0],
                "high": values[1],
                "low": values[2],
                "close": values[3],
                "volume": float(_at(quote.get("volume", []), i) or 0.0),
            }
        )
    if len(rows) < 200:
        raise DataError(f"insufficient rows for {symbol}: {len(rows)}")
    return rows


def _at(values: list[object], index: int) -> float | None:
    if index >= len(values) or values[index] is None:
        return None
    return float(values[index])


def write_symbol_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["date", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "date": row["date"],
                    "open": f"{float(row['open']):.8f}",
                    "high": f"{float(row['high']):.8f}",
                    "low": f"{float(row['low']):.8f}",
                    "close": f"{float(row['close']):.8f}",
                    "volume": f"{float(row['volume']):.0f}",
                }
            )


def download_universe(config: dict[str, object], data_dir: Path) -> dict[str, object]:
    data_cfg = config["data"]
    assert isinstance(data_cfg, dict)
    manifest: dict[str, object] = {
        "schema_version": 1,
        "source": data_cfg["source"],
        "adjustment": "OHLC multiplied by Yahoo adjusted-close/raw-close factor",
        "start_date_requested": data_cfg["start_date"],
        "end_date_requested": data_cfg["end_date"],
        "files": {},
    }
    for symbol in config["universe"]:
        rows = fetch_adjusted_daily(str(symbol), str(data_cfg["start_date"]), str(data_cfg["end_date"]))
        destination = data_dir / f"{symbol}.csv"
        write_symbol_csv(destination, rows)
        raw = destination.read_bytes()
        manifest["files"][symbol] = {
            "path": destination.name,
            "rows": len(rows),
            "first_date": rows[0]["date"],
            "last_date": rows[-1]["date"],
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
        time.sleep(0.15)
    manifest_path = data_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def load_universe(config: dict[str, object], data_dir: Path) -> dict[str, list[Bar]]:
    manifest_path = data_dir / "manifest.json"
    if not manifest_path.exists():
        raise DataError("data/manifest.json is missing; run the explicit fetch-data command")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bars_by_symbol: dict[str, list[Bar]] = {}
    for symbol_value in config["universe"]:
        symbol = str(symbol_value)
        metadata = manifest.get("files", {}).get(symbol)
        if not metadata:
            raise DataError(f"manifest lacks {symbol}")
        source = data_dir / metadata["path"]
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest != metadata["sha256"]:
            raise DataError(f"checksum mismatch for {symbol}")
        bars: list[Bar] = []
        previous_day: date | None = None
        with source.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                day = date.fromisoformat(row["date"])
                if previous_day is not None and day <= previous_day:
                    raise DataError(f"dates are not strictly increasing for {symbol}")
                values = {name: float(row[name]) for name in ("open", "high", "low", "close", "volume")}
                if not all(math.isfinite(value) for value in values.values()):
                    raise DataError(f"non-finite value for {symbol} on {day}")
                if min(values[name] for name in ("open", "high", "low", "close")) <= 0:
                    raise DataError(f"non-positive price for {symbol} on {day}")
                if values["volume"] < 0:
                    raise DataError(f"negative volume for {symbol} on {day}")
                if values["high"] < max(values["open"], values["close"], values["low"]):
                    raise DataError(f"invalid high for {symbol} on {day}")
                if values["low"] > min(values["open"], values["close"], values["high"]):
                    raise DataError(f"invalid low for {symbol} on {day}")
                bars.append(Bar(symbol=symbol, date=day, **values))
                previous_day = day
        if len(bars) != int(metadata["rows"]):
            raise DataError(f"row-count mismatch for {symbol}")
        if bars and (
            bars[0].date.isoformat() != metadata["first_date"]
            or bars[-1].date.isoformat() != metadata["last_date"]
        ):
            raise DataError(f"date coverage mismatch for {symbol}")
        bars_by_symbol[symbol] = bars
    return bars_by_symbol
