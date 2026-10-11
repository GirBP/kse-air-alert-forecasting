"""Retrieve the pinned public input; never silently substitute today's branch."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--project-root',type=Path,default=Path.cwd())
a=p.parse_args();root=a.project_root
protocol=json.loads((root/'protocol/latest-v1.json').read_text());source=protocol['source']
destination=root/'data/latest/inputs/alerts_in_ua.csv'
if destination.exists():
    if hashlib.sha256(destination.read_bytes()).hexdigest()!=source['snapshot_sha256']:
        raise SystemExit('Existing input differs from pinned checksum; leave it unchanged')
    print('Verified existing pinned input: '+str(destination))
else:
    request=urllib.request.Request(source['url'],headers={'User-Agent':'KSE-duration-research/1.0'})
    with urllib.request.urlopen(request,timeout=60) as response:
        body=response.read();resolved_url=response.url
    digest=hashlib.sha256(body).hexdigest()
    if digest!=source['snapshot_sha256']:raise SystemExit('Downloaded checksum mismatch; no input saved')
    destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(body)
    receipt={'url':source['url'],'resolved_url':resolved_url,'sha256':digest,'size_bytes':len(body),
             'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),'github_commit':source['github_commit']}
    (destination.parent/'retrieval-receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps(receipt,sort_keys=True))
