"""Independent JS port versus actual Python default, across timezone environments."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import os
import subprocess
import unittest
from kse_latest.forecast import InputError,predict_at_start,parse,stamp
ROOT=Path(__file__).resolve().parents[1]

def history(n=30):
    start=datetime(2026,9,1,tzinfo=timezone.utc)
    return [dict(id=str(i+1),location_uid='31',location_type='oblast',location_title='м. Київ',location_oblast='м. Київ',location_raion='',alert_type='air_raid',alert_level='yellow',started_at=stamp(start+timedelta(hours=2*i)),finished_at=stamp(start+timedelta(hours=2*i,minutes=10+i))) for i in range(n)]

def fixtures():
    base=history();origin='2026-09-04T00:00:00Z';items=[]
    def add(name,rows):items.append(dict(name=name,rows=rows,origin=origin))
    add('base',base);add('empty',[]);add('29',history(29));add('rolling-last-30',history(34));add('reordered',list(reversed(history(34))));add('duplicates',base+[base[0]])
    add('future-suffix',base+[{**base[0],'id':'900','started_at':'2026-10-20T00:00:00Z','finished_at':'invalid future target'}])
    add('current-end-ignored',base+[{**base[0],'id':'900','started_at':origin,'finished_at':'invalid current target'}])
    late=deepcopy(base);late[0]['available_at_utc']='2026-09-05T00:00:00Z';add('late-receipt',late)
    known=deepcopy(base);known[0]['available_at_utc']='2026-09-01T00:11:00Z'
    correction={**known[0],'finished_at':'2026-09-01T01:00:00Z','available_at_utc':'2026-09-03T00:00:00Z'};add('known-correction',known+[correction])
    moved={**correction,'started_at':'2026-09-05T00:00:00Z','finished_at':'not inspected'};add('future-start-known-correction',known+[moved])
    add('unknown-conflict',base+[{**base[0],'finished_at':'2026-09-01T01:00:00Z'}])
    opened=deepcopy(base);opened[0]['finished_at']='';add('open-not-zero',opened)
    notclear=deepcopy(base);notclear[-1]['finished_at']='2026-09-05T00:00:00Z';add('uncompleted-clear',notclear)
    other=[{**row,'location_uid':'32'} for row in base];add('other-territory-not-kyiv',other)
    bad=deepcopy(base);bad[0]['finished_at']='2026-09-01T03:00:00Z';add('overlap-rejected',bad)
    return items

class CalculatorTests(unittest.TestCase):
    def test_python_reference_and_timezones(self):
        items=fixtures();expected={}
        for f in items:
            try:expected[f['name']]=predict_at_start(f['rows'],f['origin'])
            except InputError:expected[f['name']]=None
        node_runs=[]
        for tz in ('UTC','America/New_York','Asia/Tokyo'):
            p=subprocess.run(['node',str(ROOT/'tests_web/calculator_contracts.mjs')],input=json.dumps({'fixtures':items}),text=True,capture_output=True,env={**os.environ,'TZ':tz},check=True)
            result=json.loads(p.stdout);node_runs.append(result)
            for actual in result['results']:
                ref=expected[actual['name']]
                if ref is None:self.assertIn('error',actual);continue
                self.assertNotIn('error',actual)
                v=actual['result']
                for key in ('status','prediction_minutes','completed_history_n','used_history_n','used_history_ids','used_history_durations_minutes','ignored_record_counts'):
                    self.assertEqual(v[key],ref[key],(tz,actual['name'],key))
                self.assertEqual([parse(t) for t in v['used_history_clears_utc']],[parse(t) for t in ref['used_history_clears_utc']])
        for r in node_runs:self.assertEqual(r['kyiv_origin'],node_runs[0]['kyiv_origin'])

if __name__=='__main__':unittest.main()
