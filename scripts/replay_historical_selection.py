"""Verify historical selection evidence from pinned raw and frozen coefficients.

No regression fitting, alpha selection or access to July–October outcomes.
The learned-model artifact and aggregate metrics carry their original hashes.
"""
import argparse
import csv
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
from statistics import median,pstdev
import urllib.request
from zoneinfo import ZoneInfo

TZ=ZoneInfo('Europe/Kyiv')
START=datetime(2022,2,24,tzinfo=TZ)
TRAIN_END=datetime(2026,1,1,tzinfo=TZ)
END=datetime(2026,7,1,tzinfo=TZ)

def q(values,p):
    a=sorted(values);x=(len(a)-1)*p;lo=math.floor(x);hi=math.ceil(x)
    return a[lo]+(a[hi]-a[lo])*(x-lo)
def feature(origin,history):
    local=origin.astimezone(TZ);hour=local.hour+local.minute/60+local.second/3600
    recent=[r[2] for r in history[-30:]];values=[r[2] for r in history]
    numeric=[(origin-history[-1][1]).total_seconds()/60,values[-1],values[-2],values[-3],median(recent[-5:]),
             median(recent),median(values),math.fsum(recent)/30,pstdev(recent),q(recent,.25),q(recent,.75)]
    return [math.sin(2*math.pi*hour/24),math.cos(2*math.pi*hour/24),math.sin(2*math.pi*local.weekday()/7),
            math.cos(2*math.pi*local.weekday()/7),*[math.log1p(x) for x in numeric]]

def replay(root,input_path=None):
    root=Path(root);source=json.loads((root/'audit/historical-input.json').read_text())
    path=Path(input_path) if input_path else root/'data/ml-audit/legacy-official.csv'
    if not path.exists():
        with urllib.request.urlopen(urllib.request.Request(source['url'],headers={'User-Agent':'KSE-ML-audit/1.0'}),timeout=60) as response:body=response.read()
        if hashlib.sha256(body).hexdigest()!=source['sha256']:raise ValueError('Pinned historical input checksum mismatch')
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=source['sha256']:raise ValueError('Pinned historical input changed')
    model_path=root/'audit/legacy-frozen-model.json'
    if hashlib.sha256(model_path.read_bytes()).hexdigest()!=source['frozen_model_sha256']:raise ValueError('Historical model artifact changed')
    model=json.loads(model_path.read_text());events=set()
    with path.open(newline='',encoding='utf-8') as stream:
        for row in csv.DictReader(stream):
            if row['oblast']!='м. Київ' or row['level']!='oblast' or row['raion'] or row['hromada'] or row['source']!='official':continue
            start=datetime.fromisoformat(row['started_at'])
            if not START<=start<END:continue  # Do not inspect final-period clear values.
            if not row['finished_at']:continue
            end=datetime.fromisoformat(row['finished_at'])
            if start<end<END:events.add((start,end,(end-start).total_seconds()/60))
    events=sorted(events)
    for a,b in zip(events,events[1:]):assert a[1]<=b[0]
    train_vectors=[];feature_rows=[];errors={m:[] for m in ('last_completed_alert','historical_median','median_last_30_completed','quantile_l1')}
    n=0
    for start,end,duration in events:
        history=sorted([r for r in events if r[0]<start and r[1]<=start],key=lambda r:r[1])
        if len(history)<30:continue
        vector=feature(start,history)
        feature_rows.append((start,end,duration,vector))
        if start<TRAIN_END and end<TRAIN_END:train_vectors.append(vector)
        if start<TRAIN_END:continue
        prediction=max(0,math.fsum(c*(x-mu)/scale for x,mu,scale,c in zip(vector,model['scaler_mean'],model['scaler_scale'],model['coef']))+model['intercept'])
        predictions=[history[-1][2],median(r[2] for r in history),median(r[2] for r in history[-30:]),prediction]
        for method,p in zip(errors,predictions):errors[method].append(p-duration)
        n+=1
    assert len(train_vectors)==model['fit_n']==1789 and n==277
    for j in range(15):
        values=[v[j] for v in train_vectors];mean=math.fsum(values)/len(values);var=math.fsum((v-mean)**2 for v in values)/len(values)
        assert math.isclose(mean,model['scaler_mean'][j],rel_tol=1e-9,abs_tol=1e-10)
        assert math.isclose(var,model['scaler_var'][j],rel_tol=1e-9,abs_tol=1e-10)
    expected=[]
    with (root/'reports/ml-diagnostics/historical-method-metrics.csv').open(newline='') as f:expected=[r for r in csv.DictReader(f) if r['period']=='validation_all']
    metrics=[]
    for method,values in errors.items():
        mae=math.fsum(abs(e) for e in values)/n;rmse=math.sqrt(math.fsum(e*e for e in values)/n)
        row=next(r for r in expected if r['method']==method)
        assert math.isclose(mae,float(row['mae_minutes']),abs_tol=1e-7) and math.isclose(rmse,float(row['rmse_minutes']),abs_tol=1e-7)
        metrics.append({'method':method,'n':n,'MAE':mae,'RMSE':rmse})
    # Reproduce already saved CV fits' predictions, with no fitting or search.
    cv_models=json.loads((root/'audit/legacy-cv-models.json').read_text())
    with (root/'reports/ml-diagnostics/historical-cv-metrics.csv').open(newline='') as f:cv_metrics=list(csv.DictReader(f))
    cv_predictions=0
    for m in cv_models:
        left=datetime.fromisoformat(m['fold_start_local']).replace(tzinfo=TZ)
        right=datetime.fromisoformat(m['fold_end_local_exclusive']).replace(tzinfo=TZ)
        fit=[r for r in feature_rows if r[0]<left and r[1]<left]
        score=[r for r in feature_rows if left<=r[0]<right and r[1]<right]
        assert len(fit)==m['fit_n']
        for j in range(15):
            vals=[r[3][j] for r in fit];mu=math.fsum(vals)/len(vals);var=math.fsum((v-mu)**2 for v in vals)/len(vals)
            assert math.isclose(mu,m['scaler_mean'][j],abs_tol=1e-8) and math.isclose(var,m['scaler_var'][j],abs_tol=1e-8)
        errors_cv=[]
        for start,end,y,x in score:
            p=max(0,math.fsum(c*(v-mu)/scale for v,mu,scale,c in zip(x,m['scaler_mean'],m['scaler_scale'],m['coef']))+m['intercept'])
            errors_cv.append(p-y)
        expected=next(r for r in cv_metrics if r['method']=='quantile_l1' and r['period']==m['fold_start_local'] and float(r['alpha'])==m['alpha'])
        assert len(errors_cv)==int(expected['n'])
        assert math.isclose(math.fsum(abs(e) for e in errors_cv)/len(errors_cv),float(expected['mae_minutes']),abs_tol=1e-7)
        assert math.isclose(math.sqrt(math.fsum(e*e for e in errors_cv)/len(errors_cv)),float(expected['rmse_minutes']),abs_tol=1e-7)
        cv_predictions+=len(errors_cv)
    return {'historical_raw_sha256_verified':True,'training_only_scaler_recomputed_n':len(train_vectors),
            'validation_events_replayed':n,'metrics':metrics,'models_refitted':False,'hyperparameters_searched':False,
            'post_June_targets_used':False,'source_sha256':source['sha256'],
            'saved_cv_models_verified':len(cv_models),'saved_cv_prediction_values_verified':cv_predictions}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project-root',type=Path,default=Path.cwd())
    p.add_argument('--input',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    value=replay(a.project_root,a.input);text=json.dumps(value,sort_keys=True,indent=2)+'\n'
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(text)
    print(text,end='')
