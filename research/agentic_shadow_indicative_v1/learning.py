"""Write-only suggestion archive; intentionally never imported by the engine."""
from datetime import datetime, timezone
from pathlib import Path
from .engine import canonical, digest
from swingbot.safe_paths import private_parent
import os


def propose(ledger, directory, text, event_ids):
    known={row['event_id'] for row in ledger.history()}
    if not isinstance(text,str) or not 0<len(text)<=4000 or not event_ids or not set(event_ids)<=known:
        raise ValueError('suggestion_requires_existing_evidence')
    suggestion={'created_at':datetime.now(timezone.utc).isoformat(),'suggestion':text,'evidence':event_ids,
                'status':'PROPOSED_ONLY','promotion_requires':'separate_version_evaluation_and_owner_approval'}
    path=Path(directory)/(digest(suggestion)+'.json')
    with private_parent(path,label='shadow suggestions') as parent:
        fd=parent.open_file(path.name,os.O_WRONLY|os.O_CREAT|os.O_EXCL)
        with os.fdopen(fd,'w') as f:
            f.write(canonical(suggestion)+'\n');f.flush();os.fsync(f.fileno())
    return path
