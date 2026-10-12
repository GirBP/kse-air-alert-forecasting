"""Independent arithmetic/history verification for the corrected implementation."""
import argparse
import csv
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
from statistics import median

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dt(s):return datetime.fromisoformat(s.replace('Z','+00:00'))
def read(p):
    with p.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))

def verify(root,output=None,verify_previous=False):
    root=Path(root);output=Path(output) if output else root/'data/latest/implementation-v2'
    summary=json.loads((output/'summary.json').read_text());protocol=json.loads((root/'protocol/latest-v1.json').read_text())
    assert sha(root/'protocol/latest-v1.json')==summary['protocol_sha256']
    assert sha(root/'data/latest/inputs/alerts_in_ua.csv')==summary['input_sha256']
    for name,digest in summary['implementation_code_sha256'].items():assert sha(root/'src/kse_latest'/name)==digest
    for item in json.loads((output/'checksums.json').read_text()):assert sha(output/item['path'])==item['sha256']
    opening=json.loads((root/'protocol/latest-opening.json').read_text());assert sha(root/'src/kse_latest/duration.py')==opening['method_code_sha256']
    raw=[r for r in read(root/'data/latest/inputs/alerts_in_ua.csv') if r['location_uid']=='31']
    assert len({r['id'] for r in raw})==len(raw)
    events=[(dt(r['started_at']),dt(r['finished_at']),r['id']) for r in raw]
    assert all(dt(protocol['history_start_local_inclusive'])<=s<f<dt(protocol['evaluation_end_utc_exclusive']) for s,f,id in events)
    events.sort()
    for a,b in zip(events,events[1:]):assert a[1]<=b[0]
    expected={}
    for start,finish,id in events:
        history=sorted([e for e in events if e[0]<start and e[1]<=start],key=lambda e:(e[1],int(e[2])))
        if len(history)>=30:expected[id]=(start,finish,history)
    rows=read(output/'all-forecasts.csv');assert set(expected)=={r['event_id'] for r in rows}
    for row in rows:
        start,finish,history=expected[row['event_id']];used=history[-30:]
        prediction=median((e[1]-e[0]).total_seconds()/60 for e in used)
        assert math.isclose(prediction,float(row['prediction_minutes']),abs_tol=1e-10)
        assert json.loads(row['used_history_ids'])==[e[2] for e in used]
        assert [dt(t) for t in json.loads(row['used_history_clears_utc'])]==[e[1] for e in used]
        assert int(row['completed_history_n'])==len(history)
        actual=(finish-start).total_seconds()/60;error=prediction-actual
        for name,value in [('actual_duration_minutes',actual),('signed_error_minutes',error),('absolute_error_minutes',abs(error)),('squared_error_minutes',error**2)]:
            assert math.isclose(value,float(row[name]),abs_tol=1e-8)
    final=read(output/'evaluation-predictions.csv');assert final==[r for r in rows if dt(r['forecast_origin_utc'])>=dt(protocol['evaluation_start_local_inclusive'])]
    errors=sorted(float(r['absolute_error_minutes']) for r in final);n=len(errors);x=(n-1)*.9;lo=math.floor(x);hi=math.ceil(x)
    metrics={'n':n,'MAE_minutes':math.fsum(errors)/n,'RMSE_minutes':math.sqrt(math.fsum(e*e for e in errors)/n),
             'median_absolute_error_minutes':median(errors),'p90_absolute_error_minutes':errors[lo]+(errors[hi]-errors[lo])*(x-lo)}
    for key,value in metrics.items():assert math.isclose(value,summary['metrics'][key],abs_tol=1e-10)
    original=root/'data/latest/results';identical=0
    if original.exists():
        for name in ['all-forecasts.csv','evaluation-predictions.csv','metrics.csv','exclusions.csv','exclusion-counts.csv','largest-errors.csv','demo-example.json']:
            assert sha(original/name)==sha(output/name),name;identical+=1
    protected=0
    if verify_previous:
        for name,digest in json.loads((root/'audit/preserved-before.json').read_text()).items():assert sha(root/name)==digest,name;protected+=1
    return {'version':'implementation-v2-audit','forecast_values_and_history_independently_checked':len(rows),
            'evaluation_forecasts_checked':n,'each_history_clear_available_by_event_clock':True,'original_data_artifacts_byte_identical':identical,
            'previous_files_verified':protected,'numerical_results_changed':False,'historical_publication_availability_proven':False,
            'method':'median_last_30_completed','script_sha256':sha(Path(__file__))}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project-root',type=Path,default=Path.cwd());p.add_argument('--results-dir',type=Path)
    p.add_argument('--verify-previous',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args();v=verify(a.project_root,a.results_dir,a.verify_previous)
    text=json.dumps(v,sort_keys=True,indent=2)+'\n'
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(text)
    print(text,end='')
