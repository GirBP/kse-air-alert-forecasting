"""Independent direct-history recomputation. Does not import the forecast package."""
import argparse
import csv
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
from statistics import median

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dt(s):
    t=datetime.fromisoformat(s.replace('Z','+00:00'))
    assert t.tzinfo is not None
    return t
def read(path):
    with Path(path).open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def close(a,b):assert math.isclose(float(a),float(b),rel_tol=1e-11,abs_tol=1e-8),(a,b)

def verify(root,output,verify_previous=False):
    root,output=Path(root),Path(output)
    protocol=json.loads((root/'protocol/latest-v1.json').read_text())
    lock=json.loads((root/'protocol/latest-lock.json').read_text())
    opening=json.loads((root/'protocol/latest-opening.json').read_text())
    summary=json.loads((output/'summary.json').read_text())
    assert digest(root/'protocol/latest-v1.json')==lock['protocol_sha256']==summary['protocol_sha256']
    assert dt(lock['locked_at_utc'])<=dt(opening['opened_at_utc'])
    assert digest(root/'src/kse_latest/duration.py')==opening['method_code_sha256']==summary['method_code_sha256']
    path=root/'data/latest/inputs/alerts_in_ua.csv'
    assert digest(path)==protocol['source']['snapshot_sha256']==summary['input_sha256']
    for item in json.loads((output/'checksums.json').read_text()):assert digest(output/item['path'])==item['sha256']
    raw=[r for r in read(path) if r['location_uid']=='31']
    assert len({r['id'] for r in raw})==len(raw),'Pinned cohort contains duplicate ids; audit required'
    lower=dt(protocol['history_start_local_inclusive']);cut=dt(protocol['evaluation_start_local_inclusive']);end=dt(protocol['evaluation_end_utc_exclusive'])
    events=[]
    for r in raw:
        assert r['id'].isdigit()
        assert r['location_title']==r['location_oblast']=='м. Київ' and r['location_type']=='oblast' and not r['location_raion']
        assert r['alert_type']=='air_raid'
        start,finish=dt(r['started_at']),dt(r['finished_at'])
        assert start.utcoffset().total_seconds()==finish.utcoffset().total_seconds()==0
        assert lower<=start<finish<end,'Pinned cohort has a quality exclusion; independently audit it'
        events.append((start,finish,int(r['id']),(finish-start).total_seconds()/60))
    events.sort()
    for prev,nxt in zip(events,events[1:]):assert prev[1]<=nxt[0],'Overlap in pinned cohort'
    available={str(e[2]):e for e in events}
    rows=read(output/'all-forecasts.csv');expected=[];warmup=[]
    for e in events:
        history=sorted([h for h in events if h[0]<e[0] and h[1]<=e[0] and h[2]!=e[2]],key=lambda h:(h[1],h[2]))
        if len(history)<30:warmup.append(str(e[2]));continue
        expected.append((e,history))
    assert len(rows)==len(expected)
    for row,(event,history) in zip(rows,expected):
        assert row['event_id']==str(event[2]) and dt(row['forecast_origin_utc'])==event[0]
        assert row['phase']==('evaluation' if event[0]>=cut else 'history')
        used=history[-30:]
        assert json.loads(row['used_history_ids'])==[str(e[2]) for e in used]
        assert [dt(t) for t in json.loads(row['used_history_clears_utc'])]==[e[1] for e in used]
        assert all(e[1]<=event[0] for e in used)
        assert int(row['completed_history_n'])==len(history) and int(row['used_history_n'])==30
        assert row['completed_ids_sha256']==hashlib.sha256('\n'.join(str(e[2]) for e in history).encode()).hexdigest()
        assert dt(row['latest_available_clear_utc'])==used[-1][1]
        prediction=median(e[3] for e in used)
        close(row['prediction_minutes'],prediction);close(row['actual_duration_minutes'],event[3])
        assert dt(row['actual_clear_utc'])==event[1]
        close(row['signed_error_minutes'],prediction-event[3]);close(row['absolute_error_minutes'],abs(prediction-event[3]))
        close(row['squared_error_minutes'],(prediction-event[3])**2)
    final=read(output/'evaluation-predictions.csv')
    assert final==[r for r in rows if r['phase']=='evaluation']
    errors=sorted(float(r['absolute_error_minutes']) for r in final)
    position=(len(errors)-1)*.9;lo=math.floor(position);hi=math.ceil(position)
    metric={'n':len(errors),'MAE_minutes':math.fsum(errors)/len(errors),
            'RMSE_minutes':math.sqrt(math.fsum(e**2 for e in errors)/len(errors)),
            'median_absolute_error_minutes':median(errors),'p90_absolute_error_minutes':errors[lo]+(errors[hi]-errors[lo])*(position-lo)}
    csv_metric=read(output/'metrics.csv')[0]
    for name,value in metric.items():close(summary['metrics'][name],value);close(csv_metric[name],value)
    exclusions=read(output/'exclusions.csv')
    assert {r['event_id'] for r in exclusions}==set(warmup)
    assert all(r['reason']=='insufficient_completed_history' and r['phase']=='history' for r in exclusions)
    assert summary['evaluation_excluded']==summary['quality_exclusions']==0
    counts=read(output/'exclusion-counts.csv')
    for c in counts:assert int(c['n'])==sum(e['phase']==c['phase'] and e['reason']==c['reason'] for e in exclusions)
    assert summary['source_records']==summary['accepted_events']==len(raw)
    assert summary['accepted_history_events']==sum(e[0]<cut for e in events)
    assert summary['accepted_evaluation_events']==len(final)
    largest=read(output/'largest-errors.csv')
    assert largest==sorted(final,key=lambda r:float(r['absolute_error_minutes']),reverse=True)[:10]
    demo=json.loads((output/'demo-example.json').read_text())
    chosen=next(r for r in rows if dt(r['forecast_origin_utc'])>=dt('2026-09-20T00:00:00+03:00'))
    assert dt(demo['forecast_origin_utc'])<cut and demo['event_id']==chosen['event_id']
    close(demo['prediction_minutes'],chosen['prediction_minutes'])
    assert summary['long_events_120min_n']==sum(float(r['actual_duration_minutes'])>=120 for r in final)
    close(summary['long_events_sse_share'],math.fsum(float(r['squared_error_minutes']) for r in final if float(r['actual_duration_minutes'])>=120)/math.fsum(float(r['squared_error_minutes']) for r in final))
    protected_n=0
    if verify_previous:
        for name,value in json.loads((root/'protocol/preserved-previous-files.json').read_text()).items():
            assert digest(root/name)==value,name
            protected_n+=1
    return {'version':protocol['version'],'source_sha256_verified':True,'original_kyiv_rows_checked':len(raw),
            'all_forecasts_independently_recomputed':len(rows),'evaluation_forecasts_checked':len(final),
            'every_used_clear_at_or_before_origin':True,'current_event_excluded_from_every_history':True,
            'protocol_locked_before_opening':True,'method_unchanged_since_first_opening':True,
            'long_events_kept':True,'previous_files_verified':protected_n,
            'historical_publication_time_proven':False,'script_sha256':digest(Path(__file__))}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project-root',type=Path,default=Path.cwd())
    p.add_argument('--results-dir',type=Path);p.add_argument('--verify-previous',action='store_true');p.add_argument('--output',type=Path)
    a=p.parse_args();result=verify(a.project_root,a.results_dir or a.project_root/'data/latest/results',a.verify_previous)
    text=json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n'
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(text)
    print(text,end='')
