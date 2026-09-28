"""Offline pinned inputs and quote semantics, shared by research stages."""
from bisect import bisect_right
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from research.lite_execution_data.quotes import nanos

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent/"orb_comparison_v1"
D = lambda x: Decimal(str(x))
NS = 1000000000


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def iso(stamp):
    seconds, remainder = divmod(stamp, NS)
    return datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")+f".{remainder:09d}Z"


def encode(x):
    if isinstance(x, Decimal): return str(x)
    raise TypeError(type(x).__name__)


def save(path, value):
    raw = (json.dumps(value, default=encode, sort_keys=True, separators=(",", ":"), allow_nan=False)+"\n").encode()
    with Path(path).open("xb") as handle: handle.write(raw)
    return {"file":Path(path).name,"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw)}


def inputs():
    freeze = json.loads((ROOT/"FREEZE.json").read_text())
    prepared_path = PARENT/"runs/comparison-02/prepared.json"
    for path, key in ((ROOT/"execution.json","execution_sha256"),(ROOT/"PROTOCOL.md","protocol_sha256"),
                      (PARENT/"spec.json","parent_spec_sha256"),(prepared_path,"parent_prepared_sha256"),
                      (PARENT/"runs/sip-20260907-02/actions.json","parent_actions_sha256")):
        if sha(path) != freeze[key]: raise ValueError("Frozen input changed")
    return json.loads((PARENT/"spec.json").read_text()), json.loads((ROOT/"execution.json").read_text()), json.loads(prepared_path.read_text())


def signals(prepared):
    return sorted([f for day in prepared.values() for f in day.values() if f.get("pattern",{}).get("status")=="signal"],
                  key=lambda f:(f["day"],f["symbol"]))


def key(f): return f["day"]+"_"+f["symbol"]


class Quotes:
    def __init__(self, rows):
        self.groups={}
        previous=None
        for row in rows:
            stamp=nanos(row["t"])
            if previous is not None and stamp<previous: raise ValueError("Unordered quotes")
            self.groups.setdefault(stamp,[]).append(row)
            previous=stamp
        self.times=list(self.groups)

    def at(self, stamp, cfg):
        index=bisect_right(self.times,stamp)-1
        if index<0: return {"status":"unknown_no_quote"}
        t=self.times[index]
        if stamp-t>cfg["max_quote_age_seconds"]*NS: return {"status":"unknown_stale_quote"}
        rows=self.groups[t]
        if len({json.dumps({k:r.get(k) for k in ("bp","ap","bs","as","c")},sort_keys=True) for r in rows}) != 1:
            return {"status":"unknown_same_timestamp_conflict"}
        r=rows[0]
        if r.get("c") != cfg["quote_conditions"]: return {"status":"unknown_quote_condition"}
        if any(type(r.get(k)) not in (int,float) or not D(r[k]).is_finite() or D(r[k])<=0 for k in ("bp","ap","bs","as")):
            return {"status":"unknown_invalid_quote"}
        bid,ask=D(r["bp"]),D(r["ap"])
        if bid>ask: return {"status":"unknown_crossed_quote"}
        return {"status":"valid","time":t,"bid":bid,"ask":ask,"bid_size":int(D(r["bs"])),"ask_size":int(D(r["as"])),
                "spread_bps":10000*(ask-bid)/((ask+bid)/2)}


def screen(feature, q, bps, spec, cfg):
    if q["status"]!="valid": return {"status":q["status"]}
    if q["spread_bps"]>D(cfg["max_spread_bps"]): return {"status":"reject_spread","spread_bps":q["spread_bps"]}
    slip,fee=D(bps)/10000,D(cfg["extra_fee_bps_per_side"])/10000
    stop=D(feature["pattern"]["stop"])
    entry=q["ask"]*(1+slip)
    if stop<=0 or q["ask"]<=stop: return {"status":"reject_geometry"}
    if entry>D(feature["pattern"]["confirmation_close"])*(1+D(spec["pattern"]["entry_limit_fraction_above_confirmation_close"])):
        return {"status":"reject_entry_limit"}
    cost=q["ask"]-q["bid"]+(q["ask"]+q["bid"])*(slip+fee)
    if cost>D(spec["bar_proxy"]["max_modeled_round_trip_cost_to_stop_distance"])*(entry-stop):
        return {"status":"reject_cost_to_stop"}
    if q["ask_size"]<1: return {"status":"reject_displayed_size"}
    stop_fill=stop*(1-slip)
    return {"status":"pass","entry":entry,"stop":stop,"risk_per_share":entry-stop_fill+fee*(entry+stop_fill),
            "target":entry+D(spec["pattern"]["target_r_multiple"])*(entry-stop),"modeled_cost":cost}
