"""Recorded post-evaluation diagnostic plan; three fixed methods, no selection.

CSV/JSON use stdlib. The three scientific plots require Matplotlib only.
Historical exports use retained artifacts when available; a clean clone reuses
the published aggregate evidence, without pretending to re-audit absent files.
"""
import argparse
from collections import Counter,defaultdict
import csv
from datetime import datetime,timedelta
import gzip
import hashlib
import json
import math
from pathlib import Path
from statistics import median,pstdev
from zoneinfo import ZoneInfo

TZ=ZoneInfo('Europe/Kyiv')
METHODS=('median_last_30_completed','historical_median','last_completed_alert')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dt(s):return datetime.fromisoformat(s.replace('Z','+00:00'))
def read(p):
    op=gzip.open if str(p).endswith('.gz') else open
    with op(p,'rt',newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def save(p,value):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def table(p,rows):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n");w.writeheader();w.writerows(rows)
def q(values,prob):
    a=sorted(values);x=(len(a)-1)*prob;lo=math.floor(x);hi=math.ceil(x)
    return a[lo]+(a[hi]-a[lo])*(x-lo)
def metric(rows):
    if not rows:return dict(n=0,MAE=None,RMSE=None,median_AE=None,p90_AE=None,mean_signed_error=None,median_signed_error=None,
        under_n=0,over_n=0,within15_n=0,within30_n=0,within60_n=0,within15_fraction=None,within30_fraction=None,within60_fraction=None)
    errors=[r['error'] for r in rows];a=[abs(e) for e in errors];n=len(rows)
    return dict(n=n,MAE=math.fsum(a)/n,RMSE=math.sqrt(math.fsum(e*e for e in errors)/n),median_AE=median(a),p90_AE=q(a,.9),
        mean_signed_error=math.fsum(errors)/n,median_signed_error=median(errors),under_n=sum(e<0 for e in errors),over_n=sum(e>0 for e in errors),
        **{f'within{x}_n':sum(v<=x for v in a) for x in (15,30,60)},
        **{f'within{x}_fraction':sum(v<=x for v in a)/n for x in (15,30,60)})

def historical(root,out):
    folder=root/'data/duration-pilot-v2'
    if not (folder/'validation-metrics.csv').exists():return {'mode':'published_aggregate_evidence_only; retained historical inputs not present'}
    model=json.loads((folder/'frozen-model.json').read_text());protocol=json.loads((folder/'protocol-used.json').read_text())
    # Reuse verified artifact chains instead of refitting models or new bootstraps.
    checked=[]
    for name in ('data/pilot','data/duration-pilot-v2','data/latest/results'):
        for item in json.loads((root/name/'checksums.json').read_text()):
            assert sha(root/name/item['path'])==item['sha256'],item['path'];checked.append(str(Path(name)/item['path']))
    validation=read(folder/'validation-metrics.csv');table(out/'historical-method-metrics.csv',validation)
    cv=read(folder/'cv-metrics.csv');table(out/'historical-cv-metrics.csv',cv)
    boot=read(folder/'block-bootstrap-summary.csv');table(out/'historical-bootstrap.csv',boot)
    blocks=read(folder/'bootstrap-calendar-blocks.csv');table(out/'historical-bootstrap-blocks.csv',blocks)
    train=read(folder/'training-features.csv.gz');byid={r['event_id']:r for r in train}
    audits=json.loads((folder/'cv-fit-audits.json').read_text());fitchecks=[]
    for a in audits:
        start=datetime.fromisoformat(a['fold_start_local']).replace(tzinfo=TZ);end=datetime.fromisoformat(a['fold_end_local_exclusive']).replace(tzinfo=TZ)
        fit=[byid[eid] for eid in a['fit_event_ids']];score=[byid[eid] for eid in a['validation_event_ids']]
        assert len(fit)==a['fit_n'] and set(a['fit_event_ids']).isdisjoint(a['validation_event_ids'])
        assert all(dt(r['forecast_origin_utc'])<start and dt(r['actual_finish_utc'])<start for r in fit)
        assert all(start<=dt(r['forecast_origin_utc'])<end and dt(r['actual_finish_utc'])<end for r in score)
        for j,feature in enumerate(model['features']):
            values=[float(r[feature]) for r in fit];mean=math.fsum(values)/len(values);variance=math.fsum((v-mean)**2 for v in values)/len(values)
            assert math.isclose(mean,a['scaler_mean'][j],rel_tol=1e-9,abs_tol=1e-10)
            assert math.isclose(variance,a['scaler_var'][j],rel_tol=1e-9,abs_tol=1e-10)
        fitchecks.append({'fold_start':a['fold_start_local'],'fold_end':a['fold_end_local_exclusive'],'alpha':a['alpha'],
            'fit_n':len(fit),'score_n':len(score),'actual_latest_fit_clear_utc':max(r['actual_finish_utc'] for r in fit),
            'training_only_scaler_verified':True})
    table(out/'historical-cv-fit-checks.csv',fitchecks)
    pooled=[r for r in cv if r['method']=='quantile_l1' and r['period']=='cv_2025_all']
    best=min(float(r['mae_minutes']) for r in pooled);alpha=max(float(r['alpha']) for r in pooled if float(r['mae_minutes'])<=best+1e-10)
    assert alpha==model['alpha']==.01
    replicas=read(folder/'bootstrap-replicates.csv.gz')
    groups=defaultdict(list)
    for r in replicas:groups[(r['candidate'],r['reference'],r['block_days'])].append(r)
    predictions=read(folder/'validation-predictions.csv.gz');sets={m:{r['event_id'] for r in predictions if r['method']==m} for m in (*METHODS,'quantile_l1')}
    assert all(s==next(iter(sets.values())) for s in sets.values()) and len(next(iter(sets.values())))==277
    for r in boot:
        g=groups[(r['candidate'],r['reference'],r['block_days'])];assert len(g)==5000
        for prefix in ('mae','rmse'):
            deltas=[float(x[prefix+'_difference_minutes']) for x in g]
            for prob,side in [(.025,'lower'),(.975,'upper')]:
                assert math.isclose(q(deltas,prob),float(r[prefix+'_difference_ci95_'+side]),abs_tol=1e-10)
    evidence={'mode':'retained_artifacts_checked_no_refit_or_new_bootstrap','artifact_files_checked':len(checked),
        'cv_fit_scalers_checked':len(fitchecks),'paired_support_n':277,'existing_bootstrap_replicates_audited':len(replicas),
        'selected_alpha':alpha,'feature_names':model['features'],'protocol':protocol,
        'sources':[{'path':str(p.relative_to(root)),'sha256':sha(p)} for p in [folder/'validation-metrics.csv',folder/'cv-metrics.csv',folder/'block-bootstrap-summary.csv',folder/'frozen-model.json',folder/'training-features.csv.gz',folder/'validation-predictions.csv.gz']],
        'interpretation':'conditional paired calendar-cluster bootstrap, not proof of model equivalence or practical gain'}
    valfeatures=read(folder/'validation-features.csv.gz')
    spans=[(dt(r['forecast_origin_utc'])-dt(json.loads(r['recent_history_finishes_json'])[0])).total_seconds()/86400 for r in valfeatures]
    evidence['historical_rolling30_calendar_span_days']={'min':min(spans),'median':median(spans),'max':max(spans)}
    save(out/'historical-evidence.json',evidence)
    # Model weights are our learned artifact, not a redistributed raw dataset.
    save(root/'audit/legacy-frozen-model.json',model)
    return {k:evidence[k] for k in ['mode','artifact_files_checked','cv_fit_scalers_checked','paired_support_n','existing_bootstrap_replicates_audited','selected_alpha']}

def generate(root,out,plots=True):
    root,out=Path(root),Path(out);out.mkdir(parents=True,exist_ok=True)
    plan=json.loads((root/'audit/diagnostic-plan.json').read_text());assert plan['methods']==list(METHODS)
    input_path=root/'data/latest/inputs/alerts_in_ua.csv';assert sha(input_path)==plan['input_sha256']
    protocol=json.loads((root/'protocol/latest-v1.json').read_text());lower=dt(protocol['history_start_local_inclusive']);boundary=dt(protocol['evaluation_end_utc_exclusive'])
    allrows=read(input_path);city=[r for r in allrows if r['location_uid']=='31'];assert len({r['id'] for r in city})==len(city)
    events=[]
    for r in city:
        start,end=dt(r['started_at']),dt(r['finished_at']);assert lower<=start<end<boundary
        assert start.utcoffset().total_seconds()==end.utcoffset().total_seconds()==0
        events.append({'id':r['id'],'start':start,'end':end,'duration':(end-start).total_seconds()/60,'level':r['alert_level']})
    events.sort(key=lambda r:r['start'])
    for a,b in zip(events,events[1:]):assert a['end']<=b['start']
    results_dir=root/'data/latest/results' if (root/'data/latest/results/evaluation-predictions.csv').exists() else root/'data/latest/implementation-v2'
    saved=read(results_dir/'evaluation-predictions.csv');savedids=[r['event_id'] for r in saved]
    byid={e['id']:e for e in events};comparison=[]
    for s in saved:
        event=byid[s['event_id']]
        history=sorted([e for e in events if e['id']!=event['id'] and e['start']<event['start'] and e['end']<=event['start']],key=lambda e:(e['end'],int(e['id'])))
        assert len(history)>=30
        estimates=[median(e['duration'] for e in history[-30:]),median(e['duration'] for e in history),history[-1]['duration']]
        assert math.isclose(estimates[0],float(s['prediction_minutes']),abs_tol=1e-10)
        assert [e['id'] for e in history[-30:]]==json.loads(s['used_history_ids'])
        for method,prediction in zip(METHODS,estimates):
            comparison.append({'id':event['id'],'method':method,'start':event['start'],'actual':event['duration'],
                'prediction':prediction,'error':prediction-event['duration'],'level':event['level']})
    chosen=[r for r in comparison if r['method']==METHODS[0]]
    overall=[{'method':m,**metric([r for r in comparison if r['method']==m])} for m in METHODS]
    table(out/'method-comparison-posthoc.csv',overall)
    paired=[]
    for method in METHODS[1:]:
        other=[r for r in comparison if r['method']==method];assert [r['id'] for r in other]==savedids
        diffs=[abs(a['error'])-abs(b['error']) for a,b in zip(chosen,other)]
        paired.append({'candidate':METHODS[0],'reference':method,'n_pairs':len(diffs),'mean_AE_difference_minutes':math.fsum(diffs)/len(diffs),
                       'median_AE_difference_minutes':median(diffs),'candidate_smaller_AE_n':sum(d<0 for d in diffs),
                       'interpretation':'post-evaluation descriptive; no new winner or valid independent CI'})
    table(out/'paired-comparison-posthoc.csv',paired)
    periods=[]
    for key,fun in [('local_day',lambda r:r['start'].astimezone(TZ).date().isoformat()),
                    ('local_week_monday',lambda r:(r['start'].astimezone(TZ).date()-timedelta(days=r['start'].astimezone(TZ).weekday())).isoformat())]:
        for datekey in sorted({fun(r) for r in chosen}):
            group=[r for r in chosen if fun(r)==datekey]
            periods.append({'group_type':key,'period':datekey,'edge_note':'both weekly blocks are truncated by the evaluation window' if 'week' in key else '11 October is a partial snapshot day',**metric(group)})
    table(out/'calendar-errors.csv',periods)
    bands=[]
    edges=plan['diagnostic_groups']['actual_duration_bands_minutes']+[math.inf]
    for a,b in zip(edges,edges[1:]):
        group=[r for r in chosen if a<=r['actual']<b]
        bands.append({'actual_duration_band':f'[{a},{b})','use':'post-outcome diagnosis only; unavailable at forecast start',**metric(group)})
    table(out/'duration-errors.csv',bands)
    levels=[{'group':'stored_level_'+level,'availability_note':'final archive value, not proven level at start',**metric([r for r in chosen if r['level']==level])} for level in sorted({r['level'] for r in chosen})]
    for a,b in zip([0,6,12,18],[6,12,18,24]):
        levels.append({'group':f'local_start_hour_[{a},{b})','availability_note':'event-clock start hour; no feature selection',**metric([r for r in chosen if a<=r['start'].astimezone(TZ).hour<b])})
    table(out/'group-errors.csv',levels)
    under=[]
    for limit in (30,60,120):
        group=[r for r in chosen if r['error'] < -limit]
        under.append({'underprediction_more_than_minutes':limit,'n':len(group),'fraction':len(group)/len(chosen),
                      'mean_shortfall_minutes':-math.fsum(r['error'] for r in group)/len(group) if group else None,
                      'max_shortfall_minutes':-min(r['error'] for r in group) if group else None})
    table(out/'large-underpredictions.csv',under)
    distributions=[]
    split=dt(protocol['evaluation_start_local_inclusive'])
    for name,group in [('September_history',[e for e in events if e['start']<split]),('October_opened_evaluation',[e for e in events if e['start']>=split])]:
        vals=[e['duration'] for e in group]
        distributions.append({'period':name,'n':len(vals),'duration_mean':math.fsum(vals)/len(vals),'duration_median':median(vals),
            'duration_p90':q(vals,.9),'duration_ge120_n':sum(v>=120 for v in vals),'stored_red_n':sum(e['level']=='red' for e in group),'stored_yellow_n':sum(e['level']=='yellow' for e in group),
            'interpretation':'same-source descriptive shift; source selection/coverage and levels may change; no stationarity assertion'})
    table(out/'source-distribution.csv',distributions)
    dependency=[]
    for variable in ('error','absolute_error'):
        values=[r['error'] if variable=='error' else abs(r['error']) for r in chosen]
        for lag in range(1,6):
            x,y=values[:-lag],values[lag:];mx,my=math.fsum(x)/len(x),math.fsum(y)/len(y)
            denom=math.sqrt(math.fsum((v-mx)**2 for v in x)*math.fsum((v-my)**2 for v in y))
            corr=math.fsum((a-mx)*(b-my) for a,b in zip(x,y))/denom if denom else None
            dependency.append({'variable':variable,'event_lag':lag,'n_pairs':len(x),'pearson_correlation':corr,'interpretation':'irregular event lag, descriptive, not daily ACF or significance test'})
    table(out/'error-dependence.csv',dependency)
    long=[r for r in chosen if r['actual']>=120];sse=math.fsum(r['error']**2 for r in chosen)
    evidence={'diagnosis_status':'post_evaluation; not new heldout confirmation','plan_sha256':sha(root/'audit/diagnostic-plan.json'),
        'input_sha256':sha(input_path),'prediction_artifact_sha256':sha(results_dir/'evaluation-predictions.csv'),
        'prediction_artifact_path':str((results_dir/'evaluation-predictions.csv').relative_to(root)),
        'scored_events':len(chosen),'original_predictions_recomputed_without_model_import':True,
        'overall_rolling':metric(chosen),'long_ge120_n':len(long),'long_sse_share':math.fsum(r['error']**2 for r in long)/sse,
        'weekly_nonempty_blocks':len([r for r in periods if r['group_type']=='local_week_monday']),
        'latest_bootstrap_CI_reported':False,'bootstrap_reason':'only two partial weekly clusters; too little evidence for stable temporal uncertainty',
        'history_median_lag_span_days_median':None,
        'raw_city_open_n':sum(not r['finished_at'] for r in city),'all_source_open_n':sum(not r['finished_at'] for r in allrows),
        'city_conflicting_ids_n':0,'city_overlap_n':0,'city_missing_required_n':0,
        'archive_complete_days_proven':False,'publication_and_correction_times_proven':False,'new_final_winner_selected':False,
        'prediction_intervals_provided':False,'historical_evidence':historical(root,out)}
    spans=[]
    for r in chosen:
        history=sorted([e for e in events if e['end']<=r['start'] and e['start']<r['start']],key=lambda e:(e['end'],int(e['id'])))
        spans.append((r['start']-history[-30]['end']).total_seconds()/86400)
    evidence['history_median_lag_span_days_median']=median(spans)
    evidence['rolling30_calendar_span_days_min']=min(spans);evidence['rolling30_calendar_span_days_max']=max(spans)
    save(out/'diagnostic-evidence.json',evidence)
    if plots:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
        actual=[r['actual'] for r in chosen];pred=[r['prediction'] for r in chosen]
        fig,ax=plt.subplots(figsize=(7,5),layout='constrained')
        for mask,label,color in [(False,'Actual duration <120 min','#246b86'),(True,'Actual duration >=120 min (posthoc)','#cb6741')]:
            group=[r for r in chosen if (r['actual']>=120)==mask]
            ax.scatter([r['actual'] for r in group],[r['prediction'] for r in group],label=label,color=color,alpha=.8,s=30)
        cap=max(actual+pred)*1.05;ax.plot([0,cap],[0,cap],ls='--',color='#555',label='Perfect point forecast')
        ax.set(xlim=(0,cap),ylim=(0,cap),xlabel='Actual registered duration (minutes)',ylabel='Rolling median 30 (minutes)',title='Kyiv: actual vs forecast, n=84\nOpened October period; no long-event trimming')
        ax.legend(loc='upper left',fontsize=8);ax.grid(alpha=.2);fig.savefig(out/'actual-vs-prediction.png',dpi=170);plt.close(fig)
        fig,ax=plt.subplots(figsize=(10,4),layout='constrained')
        ax.scatter([r['start'] for r in chosen],[r['error'] for r in chosen],s=22,color='#246b86')
        ax.axhline(0,color='#555',lw=1);ax.axhline(-60,color='#b77950',ls=':',label='-60 min: diagnostic threshold')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d Oct',tz=TZ));ax.xaxis.set_major_locator(mdates.DayLocator(interval=1,tz=TZ))
        ax.set(xlabel='Forecast start date (Europe/Kyiv); 11 Oct partial',ylabel='Forecast minus actual (minutes)',title='Signed errors in calendar time, n=84\nNegative values are underestimates; post-evaluation diagnosis')
        ax.set_xlim(datetime(2026,10,1,tzinfo=TZ),boundary)
        ax.grid(alpha=.2);ax.legend(fontsize=8);fig.savefig(out/'errors-in-time.png',dpi=170);plt.close(fig)
        fig,ax=plt.subplots(figsize=(8,4.5),layout='constrained')
        for method,label in zip(METHODS,['Rolling median 30 (retained)','All-history median','Last completed duration']):
            errors=sorted(abs(r['error']) for r in comparison if r['method']==method)
            ax.step([0,*errors],[0,*[(i+1)/len(errors) for i in range(len(errors))]],where='post',label=label)
        ax.set(xlabel='Absolute error (minutes)',ylabel='Fraction of same 84 events',ylim=(0,1.02),title='Three fixed methods: empirical error distribution\nPost-evaluation comparison; no new model selection')
        ax.legend(fontsize=8);ax.grid(alpha=.2);fig.savefig(out/'absolute-error-ecdf.png',dpi=170);plt.close(fig)
    save(out/'checksums.json',[{'path':p.name,'sha256':sha(p)} for p in sorted(out.iterdir()) if p.is_file() and p.name!='checksums.json'])
    return evidence

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project-root',type=Path,default=Path.cwd());p.add_argument('--output-dir',type=Path);p.add_argument('--no-plots',action='store_true')
    a=p.parse_args();v=generate(a.project_root,a.output_dir or a.project_root/'reports/ml-diagnostics',not a.no_plots)
    print(json.dumps({'scored_events':v['scored_events'],'rolling_MAE':v['overall_rolling']['MAE'],'within30_fraction':v['overall_rolling']['within30_fraction'],'weekly_blocks':v['weekly_nonempty_blocks'],'historical':v['historical_evidence']},ensure_ascii=False))
