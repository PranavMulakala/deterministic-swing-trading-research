"""Offline v2 run, accounting verification, and declared comparisons."""
import argparse
from collections import Counter,defaultdict
import json
from pathlib import Path

from research.orb_comparison_v1.run import paired
from .common import ROOT,PARENT,D,NS,nanos,key,sha,save,inputs,signals,Quotes,screen
from .engine import replay


def load_snapshot(folder,stage,spec,cfg,prepared,entry_data=None):
    manifest=json.loads((folder/"manifest.json").read_text())
    if manifest.get("complete") is not True or manifest.get("stage")!=stage or manifest.get("freeze_sha256")!=sha(ROOT/"FREEZE.json"):
        raise ValueError("Unverified tick snapshot")
    expected={}
    for f in signals(prepared):
        t=nanos(f["pattern"]["time"])
        if stage=="entry":
            expected[key(f)+"_quotes.json"]=(f,"quotes",t-NS,t+2*NS)
        else:
            idx=Quotes(entry_data[key(f)]["rows"])
            if any(screen(f,idx.at(t+delay*NS,cfg),bps,spec,cfg)["status"]=="pass" for delay in (1,2) for bps in (10,25)):
                end=nanos(f["day"]+"T15:56:00"+f["pattern"]["time"][-6:])
                for kind in ("quotes","trades"): expected[key(f)+f"_{kind}.json"]=(f,kind,t-NS,end)
    names=[x["file"] for x in manifest["files"]]
    if len(names)!=len(expected) or set(names)!=set(expected) or manifest["expected_jobs"]!=len(expected):
        raise ValueError("Snapshot does not contain exact planned file set")
    data={}
    for entry in manifest["files"]:
        path=folder/entry["file"]
        if path.is_symlink() or sha(path)!=entry["sha256"] or path.stat().st_size!=entry["bytes"]: raise ValueError("Tick integrity failed")
        payload=json.loads(path.read_text())
        f,kind,start,end=expected[path.name]
        q=payload.get("query",{})
        if payload.get("complete") is not True or payload["path"]!=f"/v2/stocks/{f['symbol']}/{kind}": raise ValueError("Tick provenance mismatch")
        if q.get("feed")!="sip" or q.get("asof")!="2026-09-04" or q.get("sort")!="asc" or nanos(q["start"])!=start or nanos(q["end"])!=end:
            raise ValueError("Tick query differs from freeze")
        previous=None
        for row in payload["rows"]:
            stamp=nanos(row["t"])
            if not start<=stamp<=end or (previous is not None and stamp<previous): raise ValueError("Tick order or interval invalid")
            previous=stamp
        if stage=="entry": data[key(f)]=payload
        else: data.setdefault(key(f),{})[kind]=payload
    if stage=="exit":
        for k,payload in data.items():
            end=nanos(entry_data[k]["query"]["end"])
            overlap=[r for r in payload["quotes"]["rows"] if nanos(r["t"])<=end]
            if overlap!=entry_data[k]["rows"]: raise ValueError("Entry and continuation quote snapshots disagree")
    return data,manifest


def audit(run,spec,cfg):
    cash=D(spec["portfolio"]["initial_cash"])
    unsettled=D(0)
    positions={}
    prior_time=None
    last_sale_day=None
    realized=D(0)
    slip=D(run["slippage_bps"])/10000
    fee=D(cfg["extra_fee_bps_per_side"])/10000
    for event in run["events"]:
        t=nanos(event["time"])
        if prior_time is not None and t<prior_time: raise AssertionError("Noncausal ledger")
        prior_time=t
        if event["type"]=="settle":
            if event["amount"]!=unsettled or (last_sale_day is not None and event["time"][:10]<=last_sale_day): raise AssertionError("Invalid settlement")
            cash+=unsettled; unsettled=D(0)
        elif event["type"]=="entry":
            s=event["symbol"]; qty=event["qty"]
            if s in positions or type(qty) is not int or not 0<qty<=event["requested_qty"] or qty>event["ask_size"]: raise AssertionError("Invalid entry qty")
            if event["entry"]!=event["quote_ask"]*(1+slip): raise AssertionError("Entry fill price mismatch")
            if event["entry_fee"]!=qty*event["entry"]*fee: raise AssertionError("Entry fee mismatch")
            if not 0<=t-nanos(event["quote_time"])<=cfg["max_quote_age_seconds"]*NS: raise AssertionError("Invalid entry quote time")
            if event["spread_bps"]>cfg["max_spread_bps"]: raise AssertionError("Spread gate bypassed")
            stop_fill=event["stop"]*(1-slip)
            risk=event["entry"]-stop_fill+fee*(event["entry"]+stop_fill)
            if risk!=event["risk_per_share"]: raise AssertionError("Risk calculation mismatch")
            if qty*risk>event["entry_equity"]*D(spec["portfolio"]["risk_fraction_per_entry"]): raise AssertionError("Entry risk exceeded")
            cost=qty*event["entry"]+event["entry_fee"]
            if abs(cost-event["cost"])>D("1e-20"): raise AssertionError("Entry cost mismatch")
            cash-=cost
            positions[s]={"qty":qty,"unit_cost":event["entry"]*(1+fee),"risk":risk,"target":event["target"]}
            if len(positions)>spec["portfolio"]["max_positions"]: raise AssertionError("Position limit exceeded")
            if sum(p["qty"]*p["risk"] for p in positions.values())>event["entry_equity"]*D(spec["portfolio"]["max_aggregate_planned_risk_fraction"]): raise AssertionError("Aggregate risk exceeded")
        elif event["type"]=="exit":
            s=event["symbol"]; p=positions[s]; qty=event["qty"]
            if type(qty) is not int or not 0<qty<=p["qty"] or qty>event["displayed_capacity_before"]: raise AssertionError("Invalid exit qty")
            if not 0<=t-nanos(event["quote_time"])<=cfg["max_quote_age_seconds"]*NS: raise AssertionError("Stale exit quote")
            reference=min(event["quote_bid"],p["target"]) if event["reason"]=="target" else event["quote_bid"]
            if event["price"]!=reference*(1-slip): raise AssertionError("Exit price mismatch")
            if event["fee"]!=qty*event["price"]*fee: raise AssertionError("Exit fee mismatch")
            proceeds=qty*event["price"]-event["fee"]
            basis=qty*p["unit_cost"]
            if event["proceeds"]!=proceeds or event["basis"]!=basis or event["pnl"]!=proceeds-basis: raise AssertionError("Partial exit accounting mismatch")
            unsettled+=proceeds; realized+=proceeds-basis; p["qty"]-=qty
            last_sale_day=event["time"][:10]
            if p["qty"]==0: del positions[s]
        else: raise AssertionError("Unknown event")
        if cash < -D("1e-20"): raise AssertionError("Cash spent before settlement")
    if abs(cash-run["settled_cash"])>D("1e-20") or abs(unsettled-run["unsettled_cash"])>D("1e-20"): raise AssertionError("Cash reconciliation mismatch")
    if {s:p["qty"] for s,p in positions.items()}!={s:p["qty"] for s,p in run["open_positions"].items()}: raise AssertionError("Lost open position")
    if run["complete"]:
        if positions or abs(cash+unsettled-run["terminal_equity"])>D("1e-20"): raise AssertionError("Terminal ledger mismatch")
        if abs(run["initial_cash"]+realized-run["terminal_equity"])>D("1e-20"): raise AssertionError("Realized PnL mismatch")
    return {"status":"passed","events":len(run["events"]),"realized_pnl":realized,"positions_preserved":len(positions)}


def summary(run):
    pnls=[t["pnl"] for t in run["trades"]]
    by_symbol=defaultdict(lambda:{"trades":0,"pnl":D(0)})
    by_month=defaultdict(lambda:{"trades":0,"pnl":D(0)})
    for t in run["trades"]:
        for group,k in ((by_symbol,t["symbol"]),(by_month,t["day"][:7])):
            group[k]["trades"]+=1; group[k]["pnl"]+=t["pnl"]
    wins=[p for p in pnls if p>0]; losses=[p for p in pnls if p<0]
    return {"complete":run["complete"],"terminal_equity":run["terminal_equity"],"net_return":run["net_return"],
            "trades":len(pnls),"mean_closed_pnl":sum(pnls,D(0))/len(pnls) if pnls else None,
            "win_rate":len(wins)/len(pnls) if pnls else None,"average_win":sum(wins,D(0))/len(wins) if wins else None,
            "average_loss":sum(losses,D(0))/len(losses) if losses else None,"worst_closed_trade":min(pnls) if pnls else None,
            "fresh_mark_drawdown":run["fresh_mark_drawdown"],"partial_entries":run["partial_entry_count"],
            "partial_exit_fills":run["partial_exit_fill_count"],"stale_mark_intervals":len(run["stale_mark_intervals"]),
            "status_counts":run["status_counts"],"by_symbol":dict(by_symbol),"by_month":dict(by_month),"unresolved":run["unresolved"]}


def run_all(entry_folder,exit_folder,output):
    spec,cfg,prepared=inputs()
    entries,em=load_snapshot(entry_folder,"entry",spec,cfg,prepared)
    streams,xm=load_snapshot(exit_folder,"exit",spec,cfg,prepared,entries)
    output.mkdir(parents=True,exist_ok=False)
    results={}; reports={}; audits={}; contrasts={}; screen_counts={}
    for delay in (1,2):
        for bps in cfg["extra_adverse_slippage_bps_per_side"]:
            counts=Counter()
            for f in signals(prepared):
                q=Quotes(entries[key(f)]["rows"]).at(nanos(f["pattern"]["time"])+delay*NS,cfg)
                counts[screen(f,q,bps,spec,cfg)["status"]]+=1
            screen_counts[f"{delay}s_{bps}bps"]=dict(counts)
            cases=[("primary",spec["symbols"])]
            if delay==1: cases += [("omit_"+s,[x for x in spec["symbols"] if x!=s]) for s in spec["symbols"]]
            for name,symbols in cases:
                pair=[]
                for arm in ("A","B"):
                    label=f"{name}_{delay}s_{bps}bps_{arm}"
                    result=replay(spec,cfg,prepared,entries,streams,arm,bps,delay,symbols)
                    audits[label]=audit(result,spec,cfg)
                    results[label]=result
                    reports[label]=summary(result)
                    pair.append(result)
                contrasts[f"{name}_{delay}s_{bps}bps"]=paired(*pair,spec) if name=="primary" else {
                    "net_return_difference":pair[1]["net_return"]-pair[0]["net_return"] if all(x["complete"] for x in pair) else None}
                print(f"Completed {name} {delay}s {bps}bps",flush=True)
    reasons=[]
    for bps in (10,25):
        c=contrasts[f"primary_1s_{bps}bps"]
        if c["net_return_difference"] is None or c["net_return_difference"]<=0: reasons.append(f"{bps}bps_no_positive_primary_contrast")
        if c["mean_daily_difference_ci"] is None or c["mean_daily_difference_ci"][0]<=0: reasons.append(f"{bps}bps_uncertainty_not_favorable")
        if not reports[f"primary_1s_{bps}bps_B"]["trades"]: reasons.append(f"{bps}bps_no_filtered_arm_trades")
        for s in spec["symbols"]:
            contrast=contrasts[f"omit_{s}_1s_{bps}bps"]["net_return_difference"]
            if contrast is None or contrast<=0: reasons.append(f"{bps}bps_omit_{s}_not_robust")
        if any(k.startswith("unknown") for k in screen_counts[f"1s_{bps}bps"]): reasons.append(f"{bps}bps_entry_quote_unknowns")
    report={"verdict":"NOT_ESTABLISHED" if reasons else "DEVELOPMENT_CRITERIA_MET_ONLY","reasons":reasons,
            "screen_counts":screen_counts,"summaries":reports,"contrasts":contrasts,"audits":audits,
            "signal_count":len(signals(prepared)),"continuation_stock_days":len(streams),"models_run":len(results),
            "provenance":{"entry_manifest_sha256":sha(entry_folder/"manifest.json"),"exit_manifest_sha256":sha(exit_folder/"manifest.json"),
                          "freeze_sha256":sha(ROOT/"FREEZE.json"),"engine_sha256":sha(ROOT/"engine.py"),"runner_sha256":sha(__file__),"common_sha256":sha(ROOT/"common.py")},
            "limitations":["finalized_bar_signals_not_original_receipt","top_of_book_not_queue_or_broker_fills","conservative_quote_size_units",
                           "no_halt_message_feed","2026_development_not_holdout","no_news_filter"]}
    save(output/"results.json",results); save(output/"report.json",report)
    print(json.dumps({"verdict":report["verdict"],"primary":{k:v for k,v in reports.items() if k.startswith("primary")}},default=str,indent=2))
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entries",type=Path,default=ROOT/"runs/entry-01")
    parser.add_argument("--exits",type=Path,default=ROOT/"runs/exit-01")
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    run_all(args.entries,args.exits,args.output)
