"""One fixed method, one source, no feature or parameter search.

Source dates describe events, not when an archived version was published.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import heapq
import json
import math
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo

KYIV = ZoneInfo('Europe/Kyiv')
REASONS = ('missing_or_invalid_id', 'conflicting_duplicate_id', 'wrong_territory',
           'wrong_alert_type', 'unresolved_start', 'open_or_invalid_clear',
           'nonpositive_duration', 'clear_at_or_after_snapshot_boundary',
           'overlap', 'outside_period', 'insufficient_completed_history')

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def stamp(value):
    return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')

def aware(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError('Explicit timezone required')
    return parsed.astimezone(timezone.utc)

def utc(value):
    parsed = aware(value)
    if datetime.fromisoformat(value.replace('Z', '+00:00')).utcoffset().total_seconds() != 0:
        raise ValueError('Source timestamp must explicitly use UTC')
    return parsed

def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')

def table(path, rows, fields=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def read(path):
    with Path(path).open(newline='', encoding='utf-8-sig') as stream:
        return list(csv.DictReader(stream))

def select(rows, protocol):
    """Closed-event cohort, with explicit quality exclusions and no imputation."""
    source = protocol['source']
    rows = [r for r in rows if r.get('location_uid') == source['location_uid']]
    cutoff = aware(protocol['evaluation_end_utc_exclusive'])
    lower = aware(protocol['history_start_local_inclusive'])
    split = aware(protocol['evaluation_start_local_inclusive'])
    groups = {}
    for index, row in enumerate(rows, 1):
        groups.setdefault(row.get('id', ''), []).append((index, row))
    events, excluded = [], []
    duplicates = 0
    def reject(row, reason, index):
        try:
            start = utc(row.get('started_at', ''))
            phase = 'evaluation' if split <= start < cutoff else 'history' if lower <= start < split else 'outside'
        except (ValueError, TypeError):
            phase = 'unassigned'
        excluded.append({'event_id': row.get('id', ''), 'reason': reason, 'phase': phase,
                         'kyiv_row_number': index})
    for event_id, versions in groups.items():
        index, row = versions[0]
        if not event_id.isdigit():
            for i, r in versions: reject(r, 'missing_or_invalid_id', i)
            continue
        if any(r != row for i, r in versions):
            for i, r in versions: reject(r, 'conflicting_duplicate_id', i)
            continue
        duplicates += len(versions) - 1
        if (row.get('location_title') != source['location_title'] or
                row.get('location_type') != source['location_type'] or
                row.get('location_oblast') != source['location_title'] or row.get('location_raion')):
            reject(row, 'wrong_territory', index); continue
        if row.get('alert_type') != 'air_raid':
            reject(row, 'wrong_alert_type', index); continue
        try: start = utc(row.get('started_at', ''))
        except (ValueError, TypeError):
            reject(row, 'unresolved_start', index); continue
        try: end = utc(row.get('finished_at', ''))
        except (ValueError, TypeError):
            reject(row, 'open_or_invalid_clear', index); continue
        if end <= start:
            reject(row, 'nonpositive_duration', index); continue
        if end >= cutoff:
            reject(row, 'clear_at_or_after_snapshot_boundary', index); continue
        if not lower <= start < cutoff:
            reject(row, 'outside_period', index); continue
        events.append({'id': event_id, 'start': start, 'end': end,
                       'duration': (end-start).total_seconds()/60,
                       'phase': 'evaluation' if start >= split else 'history',
                       'level': row.get('alert_level', ''), 'row_number': index})
    events.sort(key=lambda e: (e['start'], int(e['id'])))
    overlapping = set()
    active = []
    for event in events:
        active = [prior for prior in active if prior['end'] > event['start']]
        if active:
            overlapping.add(event['id'])
            overlapping.update(prior['id'] for prior in active)
        active.append(event)
    for event in events:
        if event['id'] in overlapping:
            excluded.append({'event_id': event['id'], 'reason': 'overlap', 'phase': event['phase'],
                             'kyiv_row_number': event['row_number']})
    return [e for e in events if e['id'] not in overlapping], excluded, duplicates, len(rows)

def forecasts(events):
    """Release an earlier result only when its actual clear precedes this origin."""
    completed, pending, predictions, warmup = [], [], [], []
    for event in events:
        while pending and pending[0][0] <= event['start']:
            end, event_id, previous = heapq.heappop(pending)
            completed.append(previous)
        if len(completed) < 30:
            warmup.append({'event_id': event['id'], 'reason': 'insufficient_completed_history',
                           'phase': event['phase'], 'kyiv_row_number': event['row_number']})
        else:
            used = completed[-30:]
            prediction = median(e['duration'] for e in used)
            error = prediction - event['duration']
            predictions.append({'event_id': event['id'], 'phase': event['phase'],
                'forecast_origin_utc': stamp(event['start']), 'forecast_origin_local': event['start'].astimezone(KYIV).isoformat(),
                'prediction_minutes': prediction, 'completed_history_n': len(completed), 'used_history_n': 30,
                'used_history_ids': json.dumps([e['id'] for e in used]),
                'used_history_clears_utc': json.dumps([stamp(e['end']) for e in used]),
                'completed_ids_sha256': hashlib.sha256('\n'.join(e['id'] for e in completed).encode()).hexdigest(),
                'latest_available_clear_utc': stamp(used[-1]['end']),
                'actual_duration_minutes': event['duration'], 'actual_clear_utc': stamp(event['end']),
                'signed_error_minutes': error, 'absolute_error_minutes': abs(error), 'squared_error_minutes': error**2,
                'registered_alert_level': event['level']})
        heapq.heappush(pending, (event['end'], int(event['id']), event))
    return predictions, warmup

def quantile(values, q):
    ordered = sorted(values)
    position = (len(ordered)-1)*q
    lo, hi = math.floor(position), math.ceil(position)
    return ordered[lo] + (ordered[hi]-ordered[lo])*(position-lo)

def metrics(rows):
    errors = [float(r['absolute_error_minutes']) for r in rows]
    if not errors:
        return {'n':0,'MAE_minutes':None,'RMSE_minutes':None,
                'median_absolute_error_minutes':None,'p90_absolute_error_minutes':None}
    return {'n':len(rows),'MAE_minutes':math.fsum(errors)/len(rows),
            'RMSE_minutes':math.sqrt(math.fsum(e*e for e in errors)/len(rows)),
            'median_absolute_error_minutes':median(errors),'p90_absolute_error_minutes':quantile(errors,.9)}

def run(root, input_path, output):
    root, input_path, output = Path(root), Path(input_path), Path(output)
    protected = ('research/raw','data/derived','data/pilot','data/duration-pilot-v2',
                 'data/duration-final','data/duration-final-first-run','data/latest/inputs')
    if output.resolve().is_relative_to(input_path.resolve().parent) or any(
            output.resolve().is_relative_to((root/p).resolve()) for p in protected):
        raise ValueError('Output must not overwrite input storage')
    protocol_path = root/'protocol/latest-v1.json'
    protocol = json.loads(protocol_path.read_text())
    lock = json.loads((root/'protocol/latest-lock.json').read_text())
    if sha(protocol_path) != lock['protocol_sha256'] or sha(input_path) != lock['snapshot_sha256']:
        raise ValueError('Frozen protocol/input checksum differs')
    code = sha(Path(__file__))
    opening_path = root/'protocol/latest-opening.json'
    if opening_path.exists():
        opening = json.loads(opening_path.read_text())
        if opening['method_code_sha256'] != code or opening['protocol_sha256'] != lock['protocol_sha256']:
            raise ValueError('No post-evaluation method/protocol change allowed')
    else:
        opening = {'opened_at_utc':datetime.now(timezone.utc).isoformat(),'method_code_sha256':code,
                   'protocol_sha256':lock['protocol_sha256'],'input_sha256':sha(input_path)}
        dump(opening_path,opening)  # Persistent checkpoint before reading outcome rows.
    if aware(opening['opened_at_utc']) < aware(lock['locked_at_utc']):
        raise ValueError('Opening precedes protocol lock')
    events, exclusions, duplicates, source_n = select(read(input_path), protocol)
    predictions, warmup = forecasts(events)
    evaluation = [p for p in predictions if p['phase']=='evaluation']
    metric = metrics(evaluation)
    source = [r for r in read(input_path) if r['location_uid']=='31']
    summary = {'version':protocol['version'],'method':'median_last_30_completed',
        'source_records':source_n,'exact_duplicate_rows':duplicates,'accepted_events':len(events),
        'accepted_history_events':sum(e['phase']=='history' for e in events),
        'accepted_evaluation_events':sum(e['phase']=='evaluation' for e in events),
        'evaluation_excluded':sum(e['phase']=='evaluation' for e in exclusions+warmup),
        'history_warmup_excluded':sum(e['phase']=='history' for e in warmup),
        'quality_exclusions':len(exclusions),'metrics':metric,
        'first_available_start_utc':min((r['started_at'] for r in source if r['started_at']),default=None),
        'last_available_start_utc':max((r['started_at'] for r in source if r['started_at']),default=None),
        'last_available_clear_utc':max((r['finished_at'] for r in source if r['finished_at']),default=None),
        'evaluation_end_utc_exclusive':protocol['evaluation_end_utc_exclusive'],
        'protocol_sha256':sha(protocol_path),'input_sha256':sha(input_path),'method_code_sha256':code,
        'long_events_120min_n':sum(p['actual_duration_minutes']>=120 for p in evaluation),
        'long_events_sse_share':sum(p['squared_error_minutes'] for p in evaluation if p['actual_duration_minutes']>=120)/sum(p['squared_error_minutes'] for p in evaluation) if evaluation and any(p['squared_error_minutes'] for p in evaluation) else None,
        'historical_publication_availability_proven':False,'daily_observation_completeness_proven':False}
    output.mkdir(parents=True,exist_ok=True)
    table(output/'all-forecasts.csv',predictions)
    table(output/'evaluation-predictions.csv',evaluation,list(predictions[0]) if predictions else ['event_id'])
    table(output/'metrics.csv',[{'period':'2026-10-partial',**metric}])
    table(output/'exclusions.csv',exclusions+warmup,['event_id','reason','phase','kyiv_row_number'])
    table(output/'exclusion-counts.csv',[{'phase':phase,'reason':reason,'n':sum(e['phase']==phase and e['reason']==reason for e in exclusions+warmup)} for phase in ['history','evaluation','outside','unassigned'] for reason in REASONS])
    table(output/'largest-errors.csv',sorted(evaluation,key=lambda p:p['absolute_error_minutes'],reverse=True)[:10])
    demo = next(p for p in predictions if p['phase']=='history' and aware(p['forecast_origin_utc'])>=aware('2026-09-20T00:00:00+03:00'))
    dump(output/'demo-example.json',demo)
    dump(output/'summary.json',summary)
    dump(output/'checksums.json',[{'path':p.name,'sha256':sha(p)} for p in sorted(output.iterdir()) if p.is_file() and p.name!='checksums.json'])
    return summary

def demo(root, show_actual=False):
    root=Path(root)
    protocol=json.loads((root/'protocol/latest-v1.json').read_text())
    events,excluded,duplicates,source_n=select(read(root/'data/latest/inputs/alerts_in_ua.csv'),protocol)
    rows,warmup=forecasts([e for e in events if e['phase']=='history'])
    row=next(p for p in rows if aware(p['forecast_origin_utc'])>=aware('2026-09-20T00:00:00+03:00'))
    text=['ВІДТВОРЕННЯ ІСТОРИЧНОГО ПРИКЛАДУ — не поточний прогноз.',
          'Київ · alerts.in.ua через окреме дзеркало · медіана останніх 30 завершень',
          'Практична ціль: типова тривалість переривання діяльності після оголошення.',
          f"Початок (Europe/Kyiv): {row['forecast_origin_local']}",
          f"Прогноз при початку: {row['prediction_minutes']:.3f} хв",
          f"Завершених в історії: {row['completed_history_n']}; використано: 30"]
    if show_actual:
        text.extend(['','ФАКТ ДЛЯ ОКРЕМОГО ПОРІВНЯННЯ (відомий після відбою):',
                     f"Фактична тривалість: {row['actual_duration_minutes']:.3f} хв",
                     f"Абсолютна помилка: {row['absolute_error_minutes']:.3f} хв"])
    text.append('Час історичної публікації/виправлення невідомий. Це не рекомендація про безпеку.')
    return '\n'.join(text)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['evaluate','demo'])
    parser.add_argument('--project-root',type=Path,default=Path.cwd())
    parser.add_argument('--input',type=Path)
    parser.add_argument('--output-dir',type=Path)
    parser.add_argument('--show-actual',action='store_true')
    args=parser.parse_args()
    if args.command=='demo': print(demo(args.project_root,args.show_actual))
    else:
        value=run(args.project_root,args.input or args.project_root/'data/latest/inputs/alerts_in_ua.csv',args.output_dir or args.project_root/'data/latest/results')
        print(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2))
