"""Offline consumer. The indicative inbox is an external read-only input."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from .engine import Ledger, canonical
from .fixtures import scenario
from .report import build, html_report
from swingbot.safe_paths import private_parent, require_no_symlink_components


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state',type=Path,required=True)
    p.add_argument('--kind',choices=('fixture','indicative'),default='fixture')
    p.add_argument('--input',type=Path,help='JSON array of normalized packets; indicative accepts one current packet per invocation')
    p.add_argument('--demo',action='store_true')
    args=p.parse_args()
    if args.demo and (args.kind!='fixture' or args.input):
        p.error('--demo requires fixture mode without --input')
    args.state=require_no_symlink_components(args.state,label='shadow state')
    ledger=Ledger(args.state/'ledger.sqlite',args.kind)
    try:
        error=None
        packets=[]
        def missing(reason):
            at=datetime.now(timezone.utc).isoformat()
            result={'event_id':'unavailable-'+at,'observed_at':at,'kind':args.kind,
                    'ingestion_error':reason}
            if args.kind=='indicative':
                result.update({'purpose':'plumbing_only','orders_enabled':False})
            return result
        try:
            if args.demo:
                packets=scenario()
            elif args.input and args.input.exists():
                path=require_no_symlink_components(args.input,label='shadow input')
                if path.stat().st_size>10*1024*1024:
                    raise ValueError('input_too_large')
                packets=json.loads(path.read_text())
                if type(packets) is not list or (args.kind=='indicative' and len(packets)!=1):
                    raise ValueError('invalid_input_batch')
            else:
                packets=[missing('missing_input')]
            for packet in packets:
                ledger.step(packet)
        except (ValueError,KeyError,TypeError,OSError) as exc:
            if args.kind=='fixture':
                raise
            # Malformed/stale input cannot prevent scheduled time/expiry management.
            error=type(exc).__name__
            ledger.step(missing('input_rejected_'+error))
        report=build(ledger)
        report['ingestion_error']=error or (packets[-1].get('ingestion_error') if packets else 'empty_input')
        for name,content in [('report.json',json.dumps(report,indent=2)+'\n'),('report.html',html_report(report))]:
            path=args.state/name
            with private_parent(path,label='shadow report') as directory:
                directory.replace(name,content.encode())
        print(canonical({'observations':report['observations'],'evidence_kind':args.kind,
                         'real_data_readiness':report['real_data_readiness'],'orders':False}))
    finally:
        ledger.close()


if __name__=='__main__':
    main()
