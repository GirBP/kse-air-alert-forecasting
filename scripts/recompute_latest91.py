"""Fixed-median30 current-snapshot retrospective diagnostic; stdlib only.

Run with PYTHONPATH=src against the public project's kse_latest.forecast API.
No raw input or detailed rows are embedded/redistributed. Output is aggregate.
"""
import argparse,csv,hashlib,json,math,statistics
from pathlib import Path
from kse_latest.forecast import parse,predict_at_start

EXPECTED_SHA='fe79c5726a1a9db9f560d6dad1de1b46f16d93b9b44ff54a2078228cf56cbc0d'
INPUT_URL='https://raw.githubusercontent.com/JustJimer/ukraine-air-alert-stats/c5b3bd012c7694e63115999a7bbd0b683eaa8d24/archive/alerts_in_ua.csv'
LEFT='2026-10-01T00:00:00+03:00'
RIGHT='2026-10-12T10:51:36Z'
PRIMARY_EDGE='2026-10-11T10:07:59Z'

def summarize(errors):
 ordered=sorted(map(abs,errors));n=len(ordered)
 def quantile(q):
  k=(n-1)*q;i=int(k);j=min(i+1,n-1);return ordered[i]+(ordered[j]-ordered[i])*(k-i)
 return {'n':n,'MAE_minutes':statistics.mean(ordered),'RMSE_minutes':math.sqrt(statistics.mean(x*x for x in errors)),'signed_bias_minutes':statistics.mean(errors),'median_AE_minutes':quantile(.5),'p90_AE_minutes':quantile(.9),'under60_n':sum(x<-60 for x in errors)}

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
 body=args.input.read_bytes();sha=hashlib.sha256(body).hexdigest()
 if sha!=EXPECTED_SHA:raise ValueError('Input checksum differs; no silent current-snapshot substitution')
 rows=list(csv.DictReader(body.decode('utf-8-sig').splitlines()));errors=[];extra=[]
 for row in rows:
  if row['location_uid']!='31' or row['alert_type']!='air_raid':continue
  start=parse(row['started_at']);end=parse(row['finished_at']) if row['finished_at'] else None
  if not (parse(LEFT)<=start<parse(RIGHT)) or end is None or end>=parse(RIGHT):continue
  if end<=start:raise ValueError('Nonpositive evaluated target')
  # Current/future end is not an input required by this forecast API; it skips
  # starts at/after origin before inspecting the end. Outcome attaches below.
  forecast=predict_at_start(rows,row['started_at'])
  if forecast['status']!='predicted':raise ValueError('Missing prediction must not disappear')
  target=(end-start).total_seconds()/60;error=forecast['prediction_minutes']-target;errors.append(error)
  if start>=parse(PRIMARY_EDGE):extra.append(error)
 result={'mode':'EXPLORATORY_RETROSPECTIVE_EVENT_CLOCK_DIAGNOSTIC','method':'unchanged median last30 completed registered Kyiv intervals','source_url':INPUT_URL,'input_sha256':sha,'evaluation_start_local_inclusive':LEFT,'evaluation_end_utc_exclusive':RIGHT,'all_October_matured':summarize(errors),'additional_events_after_primary_edge':summarize(extra),'historical_publication_availability_proven':False,'independent_test':False,'replaces_primary84':False}
 if len(errors)!=91 or len(extra)!=7:raise ValueError('Declared cohort support differs')
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
