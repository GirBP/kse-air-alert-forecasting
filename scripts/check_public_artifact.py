"""Scan exact tracked release tree and Pages artifact without printing secrets."""
import hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
patterns=[rb'(?:ghp|gho|github_pat)_[A-Za-z0-9_]{20,}',rb'AKIA[0-9A-Z]{16}',rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',rb'sk-(?:proj-)?[A-Za-z0-9_-]{32,}']
blocked=('data/','research/','submission/','ai_logs/','work/','outputs/','.env')
def check():
    files=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    failures=[];scanned=[]
    for name in sorted(set(files)-{''}):
        p=ROOT/name
        if name.startswith(blocked):failures.append({'path':name,'reason':'private or input path'})
        body=p.read_bytes()
        if any(re.search(pattern,body) for pattern in patterns):failures.append({'path':name,'reason':'credential/private-key pattern'})
        scanned.append({'path':name,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()})
    web=[]
    for p in sorted((ROOT/'web').rglob('*')):
        if p.is_file():
            if p.suffix not in ('.html','.css','.js','.json','.svg'):failures.append({'path':str(p.relative_to(ROOT)),'reason':'unplanned artifact type'})
            body=p.read_bytes()
            if any(re.search(pattern,body) for pattern in patterns):failures.append({'path':str(p.relative_to(ROOT)),'reason':'credential/private-key pattern'})
            web.append(str(p.relative_to(ROOT)))
    result={'status':'PASS' if not failures else 'FAIL','tracked_files_scanned':len(scanned),'web_files':web,'credential_patterns_only_not_absolute_secret_guarantee':True,'private_path_check':True,'failures':failures,'tracked_manifest':scanned}
    print(json.dumps(result,indent=2))
    return bool(failures)
if __name__=='__main__':raise SystemExit(check())
