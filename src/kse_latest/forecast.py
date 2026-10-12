"""Target-free, as-of forecast of TOTAL duration at an alert's new start.

The fixed window is 30. Record availability times, if supplied, are enforced;
without them this is event-clock reconstruction, not proven historical access.
"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from statistics import median
from zoneinfo import ZoneInfo

WINDOW=30
KYIV=ZoneInfo('Europe/Kyiv')

class InputError(ValueError):
    """Actionable invalid-history error, rather than a fabricated forecast."""

def parse(value, require_utc=False):
    if not isinstance(value,str) or not value:
        raise InputError('A nonempty ISO timestamp with explicit timezone is required')
    try:result=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError as exc:raise InputError('Invalid ISO timestamp: '+value) from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise InputError('Explicit timezone required: '+value)
    if require_utc and result.utcoffset().total_seconds()!=0:
        raise InputError('Source event timestamps must explicitly use UTC')
    return result.astimezone(timezone.utc)

def stamp(value):return value.astimezone(timezone.utc).isoformat().replace('+00:00','Z')

def completed_history(rows, origin):
    """Select only earlier clears. Inspect no end of a current/future event."""
    origin=parse(origin) if isinstance(origin,str) else parse(origin.isoformat())
    counts=Counter();groups={};future_versions=[]
    for row in rows:
        if not isinstance(row,dict) or 'location_uid' not in row:
            raise InputError('History row requires location_uid')
        if str(row['location_uid'])!='31':counts['other_location']+=1;continue
        available=row.get('available_at_utc')
        availability=parse(available) if available else None
        if availability is not None and availability>origin:
            counts['not_yet_available']+=1;continue
        start=parse(row.get('started_at'),require_utc=True)
        if start>=origin:
            counts['current_or_future_start']+=1
            # A known correction can move an OLD id's start past this origin.
            # Preserve that version marker without looking at its future end.
            event_id=row.get('id')
            if isinstance(event_id,str) and event_id.isascii() and event_id.isdigit():
                future_versions.append({'id':event_id,'start':start,'end':None,
                    'available':availability,'alert_type':row.get('alert_type')})
            continue
        event_id=row.get('id')
        if not isinstance(event_id,str) or not event_id.isascii() or not event_id.isdigit():
            raise InputError('History event id must be an ASCII numeric string')
        if (row.get('location_title')!='м. Київ' or row.get('location_oblast')!='м. Київ'
                or row.get('location_type')!='oblast' or row.get('location_raion')):
            raise InputError('UID 31 must retain its own Kyiv city identity')
        end=parse(row['finished_at'],require_utc=True) if row.get('finished_at') else None
        item={'id':event_id,'start':start,'end':end,'available':availability,'alert_type':row.get('alert_type')}
        groups.setdefault(event_id,[]).append(item)
    for version in future_versions:
        if version['id'] in groups:groups[version['id']].append(version)
    history=[]
    for event_id,versions in groups.items():
        signatures={(v['start'],v['end'],v['alert_type']) for v in versions}
        if len(signatures)==1:
            chosen=versions[0];counts['identical_repeats']+=len(versions)-1
        else:
            if any(v['available'] is None for v in versions):
                raise InputError('Conflicting versions without record-availability timestamps: '+event_id)
            newest=max(v['available'] for v in versions)
            latest=[v for v in versions if v['available']==newest]
            if len({(v['start'],v['end'],v['alert_type']) for v in latest})!=1:
                raise InputError('Conflicting versions at the same availability time: '+event_id)
            chosen=latest[0];counts['superseded_available_versions']+=len(versions)-1
        if chosen['start']>=origin:continue
        if chosen['alert_type']!='air_raid':
            counts['other_alert_type']+=1;continue
        if chosen['end'] is None:
            counts['open_event']+=1;continue
        if chosen['end']>origin:
            counts['not_yet_cleared']+=1;continue
        if chosen['end']<=chosen['start']:raise InputError('Nonpositive completed duration')
        chosen['duration']=(chosen['end']-chosen['start']).total_seconds()/60
        history.append(chosen)
    by_start=sorted(history,key=lambda v:(v['start'],int(v['id'])))
    for a,b in zip(by_start,by_start[1:]):
        if a['end']>b['start']:
            raise InputError('Overlapping completed Kyiv history: '+a['id']+' / '+b['id'])
    history.sort(key=lambda v:(v['end'],int(v['id'])))
    return history,dict(counts)

def predict_at_start(rows,start):
    """No current event id, duration or future clear is required by this API."""
    origin=parse(start)
    history,counts=completed_history(rows,origin)
    used=history[-WINDOW:] if len(history)>=WINDOW else []
    return {'method':'median_last_30_completed','target':'total_registered_duration_at_new_start',
            'forecast_origin_utc':stamp(origin),'forecast_origin_local':origin.astimezone(KYIV).isoformat(),
            'status':'predicted' if used else 'insufficient_completed_history',
            'prediction_minutes':median(v['duration'] for v in used) if used else None,
            'completed_history_n':len(history),'used_history_n':len(used),
            'used_history_ids':[v['id'] for v in used],'used_history_clears_utc':[stamp(v['end']) for v in used],
            'used_history_durations_minutes':[v['duration'] for v in used],
            'completed_ids_sha256':hashlib.sha256('\n'.join(v['id'] for v in history).encode()).hexdigest(),
            'latest_available_clear_utc':stamp(used[-1]['end']) if used else None,
            'ignored_record_counts':counts,'availability_evidence':'supplied availability times enforced' if used and all(v['available'] is not None for v in used) else 'event-clock only; record publication/correction availability not proven',
            'prediction_interval':None}
