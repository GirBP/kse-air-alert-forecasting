"""Retrieve pinned input atomically; report source failures without substitution."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request
import urllib.error
import tempfile

class DownloadError(ValueError):pass

def fetch_input(root,opener=None):
    root=Path(root);source=json.loads((root/'protocol/latest-v1.json').read_text())['source']
    destination=root/'data/latest/inputs/alerts_in_ua.csv'
    if destination.exists():
        if hashlib.sha256(destination.read_bytes()).hexdigest()!=source['snapshot_sha256']:
            raise DownloadError('Existing input differs from pinned checksum; it was left unchanged')
        return {'status':'verified_existing_pinned_input','path':str(destination),'sha256':source['snapshot_sha256']}
    request=urllib.request.Request(source['url'],headers={'User-Agent':'KSE-duration-research/1.0'})
    try:
        with (opener or urllib.request.urlopen)(request,timeout=60) as response:
            body=response.read();resolved_url=response.url
    except (urllib.error.URLError,TimeoutError,OSError) as exc:
        raise DownloadError('Pinned source unavailable; no input or substitute saved: '+str(exc)) from exc
    digest=hashlib.sha256(body).hexdigest()
    if digest!=source['snapshot_sha256']:raise DownloadError('Downloaded checksum mismatch; no input saved')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent,delete=False) as tmp:
        tmp.write(body);temporary=Path(tmp.name)
    try:temporary.replace(destination)
    finally:temporary.unlink(missing_ok=True)
    receipt={'url':source['url'],'resolved_url':resolved_url,'sha256':digest,'size_bytes':len(body),
             'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),'github_commit':source['github_commit']}
    (destination.parent/'retrieval-receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    return receipt

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--project-root',type=Path,default=Path.cwd())
    args=parser.parse_args()
    try:print(json.dumps(fetch_input(args.project_root),sort_keys=True))
    except (DownloadError,OSError,KeyError,ValueError) as exc:parser.exit(2,'Input download error: '+str(exc)+'\n')

if __name__=='__main__':main()
