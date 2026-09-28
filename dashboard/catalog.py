"""Allowlisted local research notes, never broker account files or credentials."""
from pathlib import Path
import hashlib
import json
REPO=Path(__file__).resolve().parents[1]
NOTES={
 'orb-quote':'research/orb_quote_v2/README.md',
 'orb-bar':'research/orb_comparison_v1/README.md',
 'lite-reversal':'research/lite_reversal_v1/README.md',
 'lite-execution':'research/lite_execution_data/README.md',
 'lite-profile':'research/lite_2026/README.md',
 'lite-movement':'research/lite_ytd_movement/README.md',
 'operations':'cloud/RESEARCH_OPERATIONS.md',
}
DESCRIPTIONS={
 'orb-quote':('ORB quote/trade execution','Frozen historical replay','A/B arms, 1/2-second delays, both costs and stock-omission sensitivity. No established edge.'),
 'orb-bar':('ORB bar comparison','Historical diagnostic','Earlier bar-based model; kept separate from quote/trade execution.'),
 'lite-reversal':('LITE dip and VWAP retest','Historical experiment','Original $500 study. Whole-share and fractional diagnostics; IEX data version.'),
 'lite-execution':('LITE data and execution follow-up','Historical diagnostic','SIP/raw comparison, quote availability, sizing and broker-feasibility limitations.'),
 'lite-profile':('Opening-reversal profile','Exploratory description','Price patterns and news availability. Descriptive movement is not a simulated return.'),
 'lite-movement':('LITE year-to-date movement','Exploratory description','Session ranges and data-source coverage. No executable strategy P&L.'),
 'operations':('Forward research operations','Operating guide','Collection, scheduled replay, evidence review and deliberate exclusions.'),
}

def catalog():
 snapshot=Path(__file__).resolve().parent/'catalog_snapshot.json'
 if snapshot.exists():
  return json.loads(snapshot.read_text())
 rows=[]
 for key,path in NOTES.items():
  file=REPO/path
  rows.append(dict(id=key,title=DESCRIPTIONS[key][0],stage=DESCRIPTIONS[key][1],description=DESCRIPTIONS[key][2],source=path,sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
 pins_ok=True; checked=0
 for folder in ('orb_comparison_v1','orb_quote_v2'):
  base=REPO/'research'/folder
  for file,digest in json.loads((base/'RESULT_PINS.json').read_text())['files'].items():
   checked+=1; pins_ok &= hashlib.sha256((base/file).read_bytes()).hexdigest()==digest
 historical=[]
 if pins_ok:
  result=json.loads((REPO/'research/orb_quote_v2/runs/replay-01/results.json').read_text())
  for key,run in result.items():
   if key.startswith('primary_'):
    historical.append({'scenario':key.removeprefix('primary_'),'initial':run['initial_cash'],'final':run['terminal_equity'],'return':run['net_return'],'trades':len(run['trades'])})
 tracks=REPO/'research/new_tracks_20260908/tracks.json'
 return {'notes':rows,'historical_orb':historical,'protected_hashes_checked':checked,'protected_hashes_match':pins_ok,'checked_at':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(), 'new_tracks':json.loads(tracks.read_text()) if tracks.exists() else None}
