"""Independently compare JS forecasts to unchanged Python on pinned real history.

Input stays private. Output includes aggregates/hashes only, not raw or event IDs.
"""
import argparse,csv,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from kse_latest.forecast import predict_at_start,parse
EXPECTED='fe79c5726a1a9db9f560d6dad1de1b46f16d93b9b44ff54a2078228cf56cbc0d'

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();body=a.input.read_bytes();assert hashlib.sha256(body).hexdigest()==EXPECTED
 rows=list(csv.DictReader(body.decode('utf-8-sig').splitlines()));origins=[r['started_at'] for r in rows if r['location_uid']=='31' and r['alert_type']=='air_raid']+['2026-10-12T10:51:36Z']
 # Real input isn't written into the public package; pass via stdin to Node.
 module=(ROOT/'web/assets/forecast-core.mjs').as_uri()
 code="import fs from 'node:fs'; import {predictAtStart} from "+json.dumps(module)+"; const x=JSON.parse(fs.readFileSync(0,'utf8')); console.log(JSON.stringify(x.origins.map(origin=>predictAtStart(x.rows,origin))));"
 proc=subprocess.run(['node','--input-type=module','-e',code],input=json.dumps(dict(rows=rows,origins=origins)),text=True,capture_output=True,check=True)
 js=json.loads(proc.stdout);maxdiff=0.;predicted=0
 for origin,actual in zip(origins,js,strict=True):
  reference=predict_at_start(rows,origin)
  for key in ('status','completed_history_n','used_history_n','used_history_ids','ignored_record_counts'):assert actual[key]==reference[key],(origin,key)
  for k in ('used_history_durations_minutes',):
   for u,v in zip(actual[k],reference[k],strict=True):maxdiff=max(maxdiff,abs(u-v))
  assert [parse(t) for t in actual['used_history_clears_utc']]==[parse(t) for t in reference['used_history_clears_utc']]
  if reference['prediction_minutes'] is not None:
   predicted+=1;maxdiff=max(maxdiff,abs(reference['prediction_minutes']-actual['prediction_minutes']))
  else:assert actual['prediction_minutes'] is None
 assert maxdiff<1e-10,maxdiff
 result=dict(status='PASS',input_sha256=EXPECTED,origins_checked=len(origins),predicted=predicted,insufficient=len(origins)-predicted,last30_ids_and_clears_exact=True,max_absolute_numeric_difference_minutes=maxdiff,python_forecast_code_sha256=hashlib.sha256((ROOT/'src/kse_latest/forecast.py').read_bytes()).hexdigest(),js_core_sha256=hashlib.sha256((ROOT/'web/assets/forecast-core.mjs').read_bytes()).hexdigest(),no_raw_in_report=True)
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
