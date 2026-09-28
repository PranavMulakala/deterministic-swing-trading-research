"""Fixed-scope GET-only SIP tick collection. Can resume immutable verified files."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time

from swingbot.alpaca_paper import AlpacaPaperClient
from swingbot.paper_cli import _load_env
from .common import ROOT,PARENT,NS,nanos,iso,save,sha,inputs,signals,key,Quotes,screen


class Client(AlpacaPaperClient):
    def _request(self, method,path,*,data_api=False,query=None,**kwargs):
        allowed={f"/v2/stocks/{s}/{kind}" for s in ("LITE","COHR","CIEN","FN","AAOI") for kind in ("quotes","trades")}
        if method!="GET" or not data_api or path not in allowed or kwargs:
            raise ValueError("Only scoped stock quote/trade GETs permitted")
        return super()._request(method,path,data_api=True,query=query)


def fetch(client,symbol,kind,start,end,cfg,pause=time.sleep):
    path=f"/v2/stocks/{symbol}/{kind}"
    query={"feed":"sip","asof":"2026-09-04","start":iso(start),"end":iso(end),"sort":"asc","limit":10000}
    rows,token,seen=[],None,set()
    previous=None
    for page in range(1,cfg["max_pages_per_request"]+1):
        pause(.35)
        reply=client._request("GET",path,data_api=True,query={**query,**({"page_token":token} if token else {})})
        if not isinstance(reply,dict) or reply.get("symbol")!=symbol or kind not in reply:
            raise ValueError("Invalid tick response")
        chunk=reply[kind]
        token=reply.get("next_page_token")
        if chunk is None and token is None: chunk=[]
        if not isinstance(chunk,list): raise ValueError("Invalid tick rows")
        for row in chunk:
            t=nanos(row["t"])
            if not start<=t<=end or (previous is not None and t<previous): raise ValueError("Invalid tick order/window")
            previous=t
        rows.extend(chunk)
        if token is None:
            return {"complete":True,"path":path,"query":query,"rows":rows,"pages":page,
                    "fetched_at":datetime.now(timezone.utc).isoformat()}
        if not isinstance(token,str) or not token or token in seen or not chunk: raise ValueError("Stalled pagination")
        seen.add(token)
    raise ValueError("Tick pagination incomplete")


def plans(stage, prepared, entry_folder, spec, cfg):
    jobs=[]
    for f in signals(prepared):
        t=nanos(f["pattern"]["time"])
        if stage=="entry":
            jobs.append((key(f)+"_quotes.json",f["symbol"],"quotes",t-NS,t+2*NS))
        else:
            p=read_file(entry_folder/key(f).__add__("_quotes.json"))
            quotes=Quotes(p["rows"])
            passed=any(screen(f,quotes.at(t+d*NS,cfg),bps,spec,cfg)["status"]=="pass" for d in (1,2) for bps in cfg["extra_adverse_slippage_bps_per_side"])
            if passed:
                end=nanos(f["day"]+"T15:56:00"+f["pattern"]["time"][-6:])
                jobs.extend((key(f)+f"_{kind}.json",f["symbol"],kind,t-NS,end) for kind in ("quotes","trades"))
    return jobs


def read_file(path):
    pin=json.loads(path.with_suffix(".sha.json").read_text())
    if sha(path)!=pin["sha256"]: raise ValueError("Tick file hash mismatch")
    payload=json.loads(path.read_text())
    if payload.get("complete") is not True: raise ValueError("Incomplete tick file")
    return payload


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",choices=("entry","exit"))
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--entries",type=Path)
    args=parser.parse_args()
    spec,cfg,prepared=inputs()
    if args.stage=="exit" and args.entries is None: parser.error("Exit stage needs --entries")
    jobs=plans(args.stage,prepared,args.entries,spec,cfg)
    args.output.mkdir(parents=True,exist_ok=True)
    if (args.output/"manifest.json").exists(): raise ValueError("Completed snapshot already exists")
    _load_env(PARENT.parents[1]/".env")
    client=Client(os.environ.get("ALPACA_PAPER_API_KEY",""),os.environ.get("ALPACA_PAPER_API_SECRET",""),timeout=30)
    manifest={"stage":args.stage,"files":[],"collector_sha256":sha(__file__),"freeze_sha256":sha(ROOT/"FREEZE.json"),"expected_jobs":len(jobs)}
    try:
        for index,(name,symbol,kind,start,end) in enumerate(jobs,1):
            path=args.output/name
            if path.exists(): payload=read_file(path)
            else:
                payload=fetch(client,symbol,kind,start,end,cfg)
                pin=save(path,payload)
                save(path.with_suffix(".sha.json"),pin)
            if payload["path"]!=f"/v2/stocks/{symbol}/{kind}" or payload["query"]["start"]!=iso(start) or payload["query"]["end"]!=iso(end):
                raise ValueError("Existing window differs from plan")
            manifest["files"].append({"file":name,"sha256":sha(path),"bytes":path.stat().st_size})
            if sum(p["bytes"] for p in manifest["files"])>cfg["max_snapshot_total_bytes"]: raise ValueError("Storage budget exceeded")
            if index%10==0 or args.stage=="exit": print(f"{args.stage} {index}/{len(jobs)} complete",flush=True)
    except Exception as exc:
        print(json.dumps({"complete":False,"error_type":type(exc).__name__,"completed_files":len(manifest["files"]),"provider_body":"suppressed"}))
        return 1
    manifest["complete"]=True
    print(json.dumps(save(args.output/"manifest.json",manifest)))
    return 0


if __name__=="__main__": raise SystemExit(main())
