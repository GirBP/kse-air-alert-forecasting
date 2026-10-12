"""Implementation v2: separate as-of prediction from scoring; retain frozen v1.

This is a bug-fix replay, not a new independent evaluation or a model change.
"""
import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from . import duration as frozen
from .forecast import InputError, parse, predict_at_start, stamp

FIELDS=('event_id','phase','forecast_origin_utc','forecast_origin_local','prediction_minutes',
        'completed_history_n','used_history_n','used_history_ids','used_history_clears_utc',
        'completed_ids_sha256','latest_available_clear_utc','actual_duration_minutes','actual_clear_utc',
        'signed_error_minutes','absolute_error_minutes','squared_error_minutes','registered_alert_level')
EXCLUSION_FIELDS=('event_id','reason','phase','kyiv_row_number')
REQUIRED=('id','location_uid','location_type','location_title','location_oblast','location_raion',
          'started_at','finished_at','alert_type','alert_level')

def read_input(path):
    with Path(path).open(newline='',encoding='utf-8-sig') as stream:
        reader=csv.DictReader(stream)
        if not reader.fieldnames or not set(REQUIRED)<=set(reader.fieldnames):
            raise InputError('CSV requires the documented mirror schema: '+', '.join(REQUIRED))
        rows=list(reader)
    return rows

def evaluate_rows(rows,protocol):
    """Structured empty/insufficient-history results, never a zero-filled target."""
    for row in rows:
        if not isinstance(row,dict) or not set(REQUIRED)<=set(row) or None in row:
            raise InputError('Missing or malformed CSV fields')
        if any(not isinstance(row[k],str) for k in REQUIRED):
            raise InputError('CSV fields must be strings; empty finished_at denotes an open event')
    # Numeric API IDs are ASCII. Prevent isdigit()/int() inconsistencies in v1.
    sanitized=[{**r,'id':''} if r['id'] and not r['id'].isascii() else r for r in rows]
    events,excluded,duplicates,n=frozen.select(sanitized,protocol)
    city_rows=[r for r in rows if r['location_uid']==protocol['source']['location_uid']]
    for item in excluded:
        if item['reason']=='missing_or_invalid_id':
            item['event_id']=city_rows[item['kyiv_row_number']-1]['id']
    pool=[{'id':e['id'],'location_uid':'31','location_title':'м. Київ','location_oblast':'м. Київ',
           'location_type':'oblast','location_raion':'','alert_type':'air_raid',
           'started_at':stamp(e['start']),'finished_at':stamp(e['end'])} for e in events]
    predictions=[];warmup=[]
    for event in events:
        prediction=predict_at_start(pool,stamp(event['start']))
        if prediction['status']!='predicted':
            warmup.append({'event_id':event['id'],'reason':'insufficient_completed_history',
                           'phase':event['phase'],'kyiv_row_number':event['row_number']})
            continue
        estimate=prediction['prediction_minutes'];error=estimate-event['duration']
        predictions.append({'event_id':event['id'],'phase':event['phase'],
            **{k:prediction[k] for k in ('forecast_origin_utc','forecast_origin_local','prediction_minutes',
               'completed_history_n','used_history_n','completed_ids_sha256','latest_available_clear_utc')},
            'used_history_ids':json.dumps(prediction['used_history_ids']),
            'used_history_clears_utc':json.dumps(prediction['used_history_clears_utc']),
            'actual_duration_minutes':event['duration'],'actual_clear_utc':stamp(event['end']),
            'signed_error_minutes':error,'absolute_error_minutes':abs(error),'squared_error_minutes':error**2,
            'registered_alert_level':event['level']})
    final=[p for p in predictions if p['phase']=='evaluation']
    return {'events':events,'predictions':predictions,'evaluation':final,'warmup':warmup,
            'quality_exclusions':excluded,'source_n':n,'duplicates':duplicates,'metrics':frozen.metrics(final)}

def write_results(output,result,protocol,metadata):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    forecasts=result['predictions'];final=result['evaluation']
    # Fixed headers are required when there are no forecasts or no test examples.
    frozen.table(output/'all-forecasts.csv',forecasts,list(FIELDS))
    frozen.table(output/'evaluation-predictions.csv',final,list(FIELDS))
    frozen.table(output/'largest-errors.csv',sorted(final,key=lambda p:p['absolute_error_minutes'],reverse=True)[:10],list(FIELDS))
    exclusions=result['quality_exclusions']+result['warmup']
    frozen.table(output/'exclusions.csv',exclusions,list(EXCLUSION_FIELDS))
    counts=[{'phase':phase,'reason':reason,'n':sum(e['phase']==phase and e['reason']==reason for e in exclusions)}
            for phase in ('history','evaluation','outside','unassigned') for reason in frozen.REASONS]
    frozen.table(output/'exclusion-counts.csv',counts)
    frozen.table(output/'metrics.csv',[{'period':'2026-10-partial',**result['metrics']}])
    demo=next((p for p in forecasts if p['phase']=='history' and parse(p['forecast_origin_utc'])>=parse('2026-09-20T00:00:00+03:00')),None)
    frozen.dump(output/'demo-example.json',demo)
    summary={'version':'latest-implementation-v2','experiment_protocol_version':protocol['version'],
             'method':'median_last_30_completed','purpose':'post-evaluation implementation correction replay, not a new test',
             'source_records':result['source_n'],'accepted_events':len(result['events']),
             'exact_duplicate_rows':result['duplicates'],'quality_exclusions':len(result['quality_exclusions']),
             'history_warmup_excluded':sum(r['phase']=='history' for r in result['warmup']),
             'evaluation_excluded':sum(r['phase']=='evaluation' for r in exclusions),
             'metrics':result['metrics'],'no_scored_examples_metrics_unknown':not final,
             'historical_publication_availability_proven':False,'original_results_overwritten':False,**metadata}
    frozen.dump(output/'summary.json',summary)
    frozen.dump(output/'checksums.json',[{'path':p.name,'sha256':frozen.sha(p)} for p in sorted(output.iterdir()) if p.is_file() and p.name!='checksums.json'])
    return summary

def check_output(root,input_path,output):
    root,input_path,output=Path(root),Path(input_path),Path(output)
    protected=('research/raw','data/derived','data/pilot','data/duration-pilot-v2','data/duration-final',
               'data/duration-final-first-run','data/latest/results','data/latest/inputs','data/latest/source-review','protocol','provenance')
    if output.resolve().is_relative_to(input_path.resolve().parent) or any(output.resolve().is_relative_to((root/p).resolve()) for p in protected):
        raise InputError('Use a separate output directory; original inputs/protocols/results are protected')

def run(root,input_path,output):
    root,input_path,output=Path(root),Path(input_path),Path(output)
    check_output(root,input_path,output)
    protocol=json.loads((root/'protocol/latest-v1.json').read_text())
    lock=json.loads((root/'protocol/latest-lock.json').read_text())
    opening=json.loads((root/'protocol/latest-opening.json').read_text())
    if frozen.sha(root/'protocol/latest-v1.json')!=lock['protocol_sha256'] or frozen.sha(input_path)!=lock['snapshot_sha256']:
        raise InputError('Frozen protocol or input differs; no silent dataset substitution')
    if frozen.sha(Path(frozen.__file__))!=opening['method_code_sha256']:
        raise InputError('Original frozen implementation changed')
    result=evaluate_rows(read_input(input_path),protocol)
    hashes={name:frozen.sha(Path(__file__).parent/name) for name in ('evaluation.py','forecast.py')}
    return write_results(output,result,protocol,{'input_sha256':frozen.sha(input_path),
         'protocol_sha256':lock['protocol_sha256'],'original_frozen_method_code_sha256':opening['method_code_sha256'],
         'implementation_code_sha256':hashes})

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('evaluate','evaluate-frozen-v1','demo','predict'))
    parser.add_argument('--project-root',type=Path,default=Path.cwd());parser.add_argument('--input',type=Path)
    parser.add_argument('--output-dir',type=Path);parser.add_argument('--show-actual',action='store_true')
    parser.add_argument('--start',help='New alert START with explicit timezone; no clear required')
    args=parser.parse_args();input_path=args.input or args.project_root/'data/latest/inputs/alerts_in_ua.csv'
    try:
        if args.command=='evaluate-frozen-v1':
            # Opt-in historical replay; require separate output to retain originals.
            output=args.output_dir or args.project_root/'work/frozen-v1-replay'
            check_output(args.project_root,input_path,output)
            result=frozen.run(args.project_root,input_path,output)
        elif args.command=='evaluate':
            result=run(args.project_root,input_path,args.output_dir or args.project_root/'data/latest/implementation-v2')
        elif args.command=='predict':
            if not args.start:raise InputError('--start is required; it is the new alert start, not elapsed time')
            result=predict_at_start(read_input(input_path),args.start)
            result['input_sha256']=frozen.sha(input_path)
            result['forecast_code_sha256']=frozen.sha(Path(__file__).parent/'forecast.py')
            result['input_path']=str(input_path.resolve())
            result['source_location_uid']='31'
            result['computed_at_utc']=datetime.now(timezone.utc).isoformat()
            protocol=json.loads((args.project_root/'protocol/latest-v1.json').read_text())
            pinned=result['input_sha256']==protocol['source']['snapshot_sha256']
            result['pinned_snapshot_boundary_utc']=protocol['evaluation_end_utc_exclusive'] if pinned else None
            result['origin_after_pinned_snapshot']=parse(args.start)>parse(protocol['evaluation_end_utc_exclusive']) if pinned else None
            result['source_mode']='provided archive/history; no live source or publication guarantee'
        else:
            protocol=json.loads((args.project_root/'protocol/latest-v1.json').read_text())
            result_rows=evaluate_rows(read_input(input_path),protocol)
            row=next((p for p in result_rows['predictions'] if p['phase']=='history' and parse(p['forecast_origin_utc'])>=parse('2026-09-20T00:00:00+03:00')),None)
            if row is None:
                print('Історичний приклад недоступний: немає достатньої завершеної історії.');return
            text=['ВІДТВОРЕННЯ ІСТОРИЧНОГО ПРИКЛАДУ — не поточний прогноз.',
                  'Прогноз повної тривалості зареєстрованої події при її початку.',
                  'Початок Europe/Kyiv: '+row['forecast_origin_local'],
                  f"Прогноз: {row['prediction_minutes']:.3f} хв; завершень в історії: {row['completed_history_n']}; використано 30."]
            if args.show_actual:text.extend(['','ОКРЕМИЙ ФАКТ ПІСЛЯ ВІДБОЮ:',f"Тривалість: {row['actual_duration_minutes']:.3f} хв; AE: {row['absolute_error_minutes']:.3f} хв."])
            text.append('Це не залишкова тривалість і не вимір фактичного переривання діяльності; історична публікація невідома.')
            print('\n'.join(text));return
        print(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2))
    except (InputError,ValueError,KeyError,OSError) as exc:
        parser.exit(2,'Input/evaluation error: '+str(exc)+'\n')
