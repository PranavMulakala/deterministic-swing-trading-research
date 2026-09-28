"""Separate raw-source execution check for every recorded fill, offline."""
from bisect import bisect_left,bisect_right
import json
from pathlib import Path
import re

from .common import ROOT,D,NS,nanos,key,sha,save,inputs
from .run import audit


def decimals(obj):
    if isinstance(obj,dict): return {k:decimals(v) for k,v in obj.items()}
    if isinstance(obj,list): return [decimals(v) for v in obj]
    if isinstance(obj,str) and re.fullmatch(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?",obj): return D(obj)
    return obj


class Source:
    def __init__(self,quotes,trades,cfg):
        self.rows=quotes; self.trades=trades; self.cfg=cfg
        self.ts=[nanos(r["t"]) for r in quotes]
        self.trade_ts=[nanos(r["t"]) for r in trades]
        self.cache={}
        self.triggers={}

    def quote(self,t):
        i=bisect_right(self.ts,t)-1
        if i<0 or t-self.ts[i]>NS: return None
        stamp=self.ts[i]
        if stamp in self.cache: return self.cache[stamp]
        same=self.rows[bisect_left(self.ts,stamp):i+1]
        fields=("bp","ap","bs","as","c")
        first=same[0]
        if any(any(r.get(k)!=first.get(k) for k in fields) for r in same): value=None
        elif first.get("c")!=["R"] or any(type(first.get(k)) not in (int,float) or not D(first[k]).is_finite() or D(first[k])<=0 for k in fields[:4]): value=None
        elif D(first["bp"])>D(first["ap"]): value=None
        else: value={"bid":D(first["bp"]),"ask":D(first["ap"]),"bs":int(first["bs"]),"as":int(first["as"]),"t":stamp}
        self.cache[stamp]=value
        return value

    def first_trigger(self,entry,stop,target,time_exit):
        cache_key=(entry,stop,target,time_exit)
        if cache_key in self.triggers: return self.triggers[cache_key]
        candidates=[(time_exit,2,"time")]
        q=self.quote(entry)
        if q and q["bid"]<=stop: candidates.append((entry,0,"stop"))
        seen=set()
        for t in self.ts[bisect_right(self.ts,entry):bisect_right(self.ts,time_exit)]:
            if t in seen: continue
            seen.add(t); q=self.quote(t)
            if q and q["bid"]<=stop: candidates.append((t,0,"stop"))
            elif q and q["bid"]>=target: candidates.append((t,1,"target"))
        allowed=set(self.cfg["stop_trade_conditions_allowed"])
        for i in range(bisect_right(self.trade_ts,entry),bisect_right(self.trade_ts,time_exit)):
            r=self.trades[i]
            if isinstance(r.get("c"),list) and set(r["c"])<=allowed and type(r.get("p")) in (int,float) and D(r["p"]).is_finite() and 0<D(r["p"])<=stop:
                candidates.append((self.trade_ts[i],0,"stop"))
        result=min(candidates)
        self.triggers[cache_key]=result
        return result


def verify(folder,exit_folder):
    spec,cfg,prepared=inputs()
    results=decimals(json.loads((folder/"results.json").read_text()))
    manifest=json.loads((exit_folder/"manifest.json").read_text())
    pins={x["file"]:x["sha256"] for x in manifest["files"]}
    sources={}; checked=0; triggers_checked=0
    ledger_checks={}
    for label,result in results.items():
        ledger_checks[label]=audit(result,spec,cfg)
        active={}
        for event in result["events"]:
            if event["type"]=="settle": continue
            s=event["symbol"]; stamp=nanos(event["time"]); day=event["time"][:10]
            source_key=day+"_"+s
            if source_key not in sources:
                payloads={}
                for kind in ("quotes","trades"):
                    name=source_key+"_"+kind+".json"; path=exit_folder/name
                    if sha(path)!=pins[name]: raise AssertionError("Underlying ticks changed")
                    payloads[kind]=json.loads(path.read_text())["rows"]
                sources[source_key]=Source(payloads["quotes"],payloads["trades"],cfg)
            source=sources[source_key]; quote=source.quote(stamp)
            if quote is None or nanos(event["quote_time"])!=quote["t"]: raise AssertionError("Fill has no matching fresh raw quote")
            f=prepared[day][s]
            if event["type"]=="entry":
                if stamp!=nanos(f["pattern"]["time"])+result["signal_delay_seconds"]*NS: raise AssertionError("Wrong signal latency")
                if quote["ask"]!=event["quote_ask"] or event["qty"]>quote["as"]: raise AssertionError("Entry not supported by raw ask")
                if event["stop"]!=D(f["pattern"]["stop"]): raise AssertionError("Stop changed")
                if result["arm"]=="B" and D(f["rvol"])<2: raise AssertionError("RVOL filter bypassed")
                time_exit=nanos(day+"T15:55:00"+f["pattern"]["time"][-6:])
                trigger=source.first_trigger(stamp,event["stop"],event["target"],time_exit)
                active[s]={"trigger":trigger,"exit_fills":0,"qty":event["qty"]}
            else:
                p=active[s]; trigger=p["trigger"]; due=trigger[0]+cfg["exit_latency_ms"]*1000000
                if event["reason"]!=trigger[2] or not due<=stamp<=trigger[0]+cfg["max_exit_wait_seconds"]*NS: raise AssertionError("Exit differs from earliest raw trigger")
                if quote["bid"]!=event["quote_bid"]: raise AssertionError("Exit not supported by raw bid")
                if p["exit_fills"]==0:
                    earliest=due
                    first=source.quote(due)
                    if first is None or first["bs"]<1:
                        found=[t for t in source.ts[bisect_left(source.ts,due):bisect_right(source.ts,stamp)] if (source.quote(t) or {}).get("bs",0)>0]
                        if not found: raise AssertionError("No executable first exit quote")
                        earliest=found[0]
                    if stamp!=earliest: raise AssertionError("Exit did not use first executable quote")
                    triggers_checked+=1
                p["exit_fills"]+=1; p["qty"]-=event["qty"]
                if not p["qty"]: del active[s]
            checked+=1
    return {"status":"passed","ledger_variants":len(results),"fill_events_checked_against_raw_ticks":checked,
            "first_exit_triggers_checked":triggers_checked,"unique_stock_days":len(sources),"ledger_checks":ledger_checks,
            "results_sha256":sha(folder/"results.json"),"verifier_sha256":sha(__file__),
            "scope":"every actual fill and first exit trigger; partial-fill mechanics additionally tested with synthetic fixtures"}


if __name__=="__main__":
    result=verify(ROOT/"runs/replay-01",ROOT/"runs/exit-01")
    save(ROOT/"runs/replay-01/source_verification.json",result)
    print(json.dumps({k:v for k,v in result.items() if k!="ledger_checks"}))
