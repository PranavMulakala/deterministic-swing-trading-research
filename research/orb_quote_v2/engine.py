"""Nanosecond event replay with partial fills; no network or broker imports."""
from collections import Counter
from datetime import datetime, timedelta
from decimal import ROUND_FLOOR
import heapq
from zoneinfo import ZoneInfo

from .common import D,NS,nanos,iso,key,Quotes,screen

ZERO=D(0)


def event_stream(feature, payload):
    """Return quote index and trade groups. Window/hash verification is upstream."""
    q=Quotes(payload["quotes"]["rows"])
    trades={}
    previous=None
    for r in payload["trades"]["rows"]:
        stamp=nanos(r["t"])
        if previous is not None and stamp<previous: raise ValueError("Unordered trades")
        trades.setdefault(stamp,[]).append(r)
        previous=stamp
    return q,trades


def trade_stop(rows, stop, cfg):
    for r in rows:
        conditions=r.get("c")
        if not isinstance(conditions,list) or any(c not in cfg["stop_trade_conditions_allowed"] for c in conditions): continue
        if type(r.get("p")) not in (int,float) or not D(r["p"]).is_finite() or D(r["p"])<=0: continue
        if D(r["p"])<=stop: return True
    return False


def replay(spec,cfg,prepared,entries,streams,arm,bps,delay,symbols=None):
    if arm not in ("A","B") or bps not in cfg["extra_adverse_slippage_bps_per_side"] or delay not in (1,2):
        raise ValueError("Undeclared scenario")
    symbols=list(spec["symbols"] if symbols is None else symbols)
    cash=D(spec["portfolio"]["initial_cash"])
    receivables=ZERO
    positions={}
    events,trades,records,daily=[],[],[],[]
    unresolved=None
    slip,fee=D(bps)/10000,D(cfg["extra_fee_bps_per_side"])/10000
    pcfg=spec["portfolio"]
    peak=cash
    drawdown=ZERO
    unknown_mark_events=0
    halt_count=0
    partial_entries=0
    partial_exits=0
    stale_intervals=[]
    stale_start=None
    for day,features in prepared.items():
        rec={s:{"day":day,"symbol":s,"status":"not_evaluated_after_unresolved" if unresolved else "pending"} for s in symbols}
        records.extend(rec.values())
        if unresolved: continue
        daystart=datetime.fromisoformat(day+"T09:30").replace(tzinfo=ZoneInfo(spec["timezone"]))
        time_exit=nanos((daystart.replace(hour=15,minute=55)).isoformat())
        start_ns=nanos(daystart.isoformat())
        if receivables: events.append({"type":"settle","time":iso(start_ns),"amount":receivables})
        cash+=receivables
        receivables=ZERO
        start_equity=cash
        realized=ZERO
        halted=False
        selected=[s for s in symbols if features[s]["status"]=="eligible"]
        if arm=="B":
            selected=sorted([s for s in selected if D(features[s]["rvol"])>=D(spec["selection"]["rvol_min"])],
                            key=lambda s:(-D(features[s]["rvol"]),-D(features[s]["dollar_volume"]),s))[:spec["selection"]["max_candidates"]]
        attempts={}
        books={}
        trade_groups={}
        times={time_exit}
        for symbol in symbols:
            f=features[symbol]
            if f["status"]!="eligible": rec[symbol]["status"]="ineligible"; continue
            if symbol not in selected: rec[symbol]["status"]="rvol_filter"; continue
            p=f["pattern"]
            if p["status"]!="signal": rec[symbol]["status"]=p["status"]; continue
            stamp=nanos(p["time"])+delay*NS
            attempts.setdefault(stamp,[]).append(symbol)
            times.add(stamp)
            books[symbol]=Quotes(entries[key(f)]["rows"])
        queue=list(times)
        heapq.heapify(queue)
        queued=set(times)
        def schedule(t):
            if t not in queued: heapq.heappush(queue,t); queued.add(t)
        while queue:
            stamp=heapq.heappop(queue)
            current={s:books[s].at(stamp,cfg) for s in positions}
            # All quote/trade updates at this timestamp precede fills and entries.
            for s,p in list(positions.items()):
                q=current[s]
                if q["status"]=="valid":
                    schedule(q["time"]+cfg["max_quote_age_seconds"]*NS+1)
                    state=(q["bid"],q["bid_size"])
                    if state!=p["book_state"]:
                        p["book_state"]=state
                        p["capacity"]=q["bid_size"]
                    p["mark"]=q["bid"]
                if p["pending"] is None:
                    reason=None
                    if (q["status"]=="valid" and q["bid"]<=p["stop"]) or trade_stop(trade_groups.get(s,{}).get(stamp,[]),p["stop"],cfg): reason="stop"
                    elif q["status"]=="valid" and q["bid"]>=p["target"]: reason="target"
                    elif stamp>=time_exit: reason="time"
                    if reason:
                        p["pending"]={"reason":reason,"trigger":stamp,"due":stamp+cfg["exit_latency_ms"]*1000000,
                                      "deadline":stamp+cfg["max_exit_wait_seconds"]*NS}
                        schedule(p["pending"]["due"])
                        schedule(p["pending"]["deadline"])
            for s,p in list(positions.items()):
                pending=p["pending"]
                if pending is None or stamp<pending["due"]: continue
                q=current[s]
                if q["status"]=="valid" and p["capacity"]>0:
                    qty=min(p["qty"],p["capacity"])
                    reference=min(q["bid"],p["target"]) if pending["reason"]=="target" else q["bid"]
                    price=reference*(1-slip)
                    exit_fee=qty*price*fee
                    proceeds=qty*price-exit_fee
                    basis=qty*p["unit_cost"]
                    pnl=proceeds-basis
                    receivables+=proceeds
                    realized+=pnl
                    events.append({"type":"exit","time":iso(stamp),"symbol":s,"qty":qty,"price":price,"fee":exit_fee,
                                   "proceeds":proceeds,"basis":basis,"pnl":pnl,"reason":pending["reason"],"quote_time":iso(q["time"]),
                                   "quote_bid":q["bid"],"displayed_capacity_before":p["capacity"]})
                    if qty<p["qty"]: partial_exits+=1
                    p["qty"]-=qty
                    p["capacity"]-=qty
                    p["pnl"]+=pnl
                    p["exit_count"]+=1
                    if p["qty"]==0:
                        trades.append({"symbol":s,"day":day,"entry_time":p["entry_time"],"exit_time":iso(stamp),"qty":p["original_qty"],
                                       "entry":p["entry"],"pnl":p["pnl"],"reason":pending["reason"],"exit_fills":p["exit_count"]})
                        del positions[s]
                if s in positions and stamp>=pending["deadline"]:
                    unresolved={"time":iso(stamp),"symbol":s,"reason":"exit_unfilled_at_deadline"}
                    rec[s]["status"]="unresolved_exit"
                    break
            if unresolved: break
            if not halted and realized<=-start_equity*D(pcfg["daily_realized_loss_halt_fraction"]): halted=True; halt_count+=1
            for s in sorted(attempts.get(stamp,[]),key=lambda s:(-D(features[s]["dollar_volume"]),s)):
                f=features[s]
                if halted: rec[s]["status"]="daily_loss_halt"; continue
                if len(positions)>=pcfg["max_positions"]: rec[s]["status"]="position_capacity"; continue
                q=books[s].at(stamp,cfg)
                choice=screen(f,q,bps,spec,cfg)
                if choice["status"]!="pass": rec[s]["status"]=choice["status"]; continue
                if key(f) not in streams: raise ValueError("Passing entry lacks mandatory continuation ticks")
                marks={name:books[name].at(stamp,cfg) for name in positions}
                if any(v["status"]!="valid" for v in marks.values()): rec[s]["status"]="unknown_equity_mark"; continue
                equity=cash+receivables+sum((marks[name]["bid"]*p["qty"] for name,p in positions.items()),ZERO)
                risk_remaining=equity*D(pcfg["max_aggregate_planned_risk_fraction"])-sum((p["risk_per_share"]*p["qty"] for p in positions.values()),ZERO)
                limits={"cash":cash/(choice["entry"]*(1+fee)),"risk":equity*D(pcfg["risk_fraction_per_entry"])/choice["risk_per_share"],
                        "aggregate":max(ZERO,risk_remaining)/choice["risk_per_share"]}
                requested=int(min(limits.values()).to_integral_value(rounding=ROUND_FLOOR))
                if requested<1: rec[s]["status"]="zero_quantity_"+min(limits,key=limits.get); continue
                qty=min(requested,q["ask_size"])
                if qty<1: rec[s]["status"]="reject_displayed_size"; continue
                books[s],trade_groups[s]=event_stream(f,streams[key(f)])
                horizon=time_exit+cfg["max_exit_wait_seconds"]*NS
                extra={t for t in books[s].times if stamp<t<=horizon}
                extra.update(t for t in trade_groups[s] if stamp<t<=horizon)
                queue.extend(extra-queued)
                queued.update(extra)
                heapq.heapify(queue)
                if qty<requested: partial_entries+=1
                unit_cost=choice["entry"]*(1+fee)
                cost=qty*unit_cost
                cash-=cost
                entry_fee=qty*choice["entry"]*fee
                p={**choice,"qty":qty,"original_qty":qty,"entry_time":iso(stamp),"unit_cost":unit_cost,"pnl":ZERO,
                   "exit_count":0,"mark":q["bid"],"book_state":(q["bid"],q["bid_size"]),"capacity":q["bid_size"],"pending":None}
                positions[s]=p
                schedule(q["time"]+cfg["max_quote_age_seconds"]*NS+1)
                rec[s]["status"]="filled_partial_entry" if qty<requested else "filled"
                events.append({"type":"entry","time":iso(stamp),"symbol":s,"qty":qty,"requested_qty":requested,"entry":choice["entry"],
                               "entry_fee":entry_fee,"cost":cost,"stop":choice["stop"],"target":choice["target"],
                               "risk_per_share":choice["risk_per_share"],"entry_equity":equity,"quote_time":iso(q["time"]),"quote_ask":q["ask"],
                               "ask_size":q["ask_size"],"spread_bps":q["spread_bps"]})
                # Only the contemporaneous entry quote may trigger a new position;
                # preceding same-timestamp trade events are not replayed onto it.
                if q["bid"]<=p["stop"]:
                    p["pending"]={"reason":"stop","trigger":stamp,"due":stamp+cfg["exit_latency_ms"]*1000000,"deadline":stamp+cfg["max_exit_wait_seconds"]*NS}
                    schedule(p["pending"]["due"]); schedule(p["pending"]["deadline"])
            if cash<0: raise AssertionError("Negative settled cash")
            marks={s:books[s].at(stamp,cfg) for s in positions}
            if all(q["status"]=="valid" for q in marks.values()):
                if stale_start is not None:
                    stale_intervals.append({"start":iso(stale_start),"end":iso(stamp)})
                    stale_start=None
                value=cash+receivables+sum((marks[s]["bid"]*p["qty"] for s,p in positions.items()),ZERO)
                peak=max(peak,value)
                drawdown=max(drawdown,1-value/peak)
            else:
                unknown_mark_events+=1
                if stale_start is None: stale_start=stamp
            if not positions and all(t<=stamp for t in attempts): break
        if positions and unresolved is None: unresolved={"time":iso(time_exit+cfg["max_exit_wait_seconds"]*NS),"reason":"position_remains_without_exit"}
        if unresolved:
            for r in rec.values():
                if r["status"]=="pending": r["status"]="not_evaluated_after_unresolved"
            daily.append({"day":day,"start_equity":start_equity,"end_equity":None,"return":None})
        else:
            end_equity=cash+receivables
            daily.append({"day":day,"start_equity":start_equity,"end_equity":end_equity,"return":end_equity/start_equity-1})
    final=cash+receivables if unresolved is None else None
    initial=D(pcfg["initial_cash"])
    if stale_start is not None: stale_intervals.append({"start":iso(stale_start),"end":None})
    return {"arm":arm,"slippage_bps":bps,"signal_delay_seconds":delay,"complete":unresolved is None,"unresolved":unresolved,
            "initial_cash":initial,"terminal_equity":final,"net_return":final/initial-1 if final is not None else None,
            "settled_cash":cash,"unsettled_cash":receivables,"open_positions":{s:{k:v for k,v in p.items() if k!="book_state"} for s,p in positions.items()},
            "events":events,"trades":trades,"daily":daily,"symbol_days":records,"status_counts":dict(Counter(r["status"] for r in records)),
            "halt_count":halt_count,"partial_entry_count":partial_entries,"partial_exit_fill_count":partial_exits,
            "fresh_mark_drawdown":drawdown,"unknown_mark_event_count":unknown_mark_events,
            "stale_mark_intervals":stale_intervals,
            "label":"historical_top_of_book_model_not_broker_fill_proof"}
