import csv
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import tempfile
import unittest
from kse_latest.forecast import InputError,predict_at_start,stamp
from kse_latest.evaluation import evaluate_rows,write_results,read_input,run
from test_duration import PROTOCOL

def history(n=30):
    start=datetime(2026,9,1,tzinfo=timezone.utc)
    return [{'id':str(i+1),'location_uid':'31','location_type':'oblast','location_title':'м. Київ',
             'location_oblast':'м. Київ','location_raion':'','alert_type':'air_raid','alert_level':'yellow',
             'started_at':stamp(start+timedelta(hours=2*i)),
             'finished_at':stamp(start+timedelta(hours=2*i,minutes=10+i))} for i in range(n)]

ORIGIN='2026-09-04T00:00:00Z'
def value(result):
    return {k:result[k] for k in ('prediction_minutes','completed_history_n','used_history_ids','used_history_clears_utc','completed_ids_sha256')}

class ForecastApiTests(unittest.TestCase):
    def test_new_start_requires_no_current_target_or_clear(self):
        result=predict_at_start(history(),ORIGIN)
        self.assertEqual(result['status'],'predicted');self.assertEqual(result['prediction_minutes'],24.5)
        self.assertNotIn('actual_duration_minutes',result)
        self.assertEqual(len(result['used_history_durations_minutes']),30)
        self.assertEqual(sum(result['used_history_durations_minutes'][14:16])/2,result['prediction_minutes'])

    def test_append_future_events_cannot_change_past_prediction(self):
        rows=history();future={**rows[-1],'id':'500','started_at':'2026-10-20T00:00:00Z','finished_at':'2026-10-21T00:00:00Z'}
        self.assertEqual(value(predict_at_start(rows,ORIGIN)),value(predict_at_start(rows+[future],ORIGIN)))

    def test_future_invalid_target_is_not_inspected(self):
        rows=history();future={**rows[-1],'id':None,'started_at':'2026-10-20T00:00:00Z','finished_at':object()}
        self.assertEqual(value(predict_at_start(rows,ORIGIN)),value(predict_at_start(rows+[future],ORIGIN)))

    def test_current_clear_can_be_absent_or_changed_arbitrarily(self):
        rows=history();current={**rows[-1],'id':'900','started_at':ORIGIN,'finished_at':None}
        a=predict_at_start(rows+[current],ORIGIN);current['finished_at']='invalid future target'
        self.assertEqual(value(a),value(predict_at_start(rows+[current],ORIGIN)))

    def test_unordered_history_cannot_leak_future_values(self):
        rows=history();future={**rows[-1],'id':'500','started_at':'2026-10-20T00:00:00Z','finished_at':'2026-10-21T00:00:00Z'}
        self.assertEqual(value(predict_at_start(rows,ORIGIN)),value(predict_at_start(list(reversed(rows))+[future],ORIGIN)))
        for t in predict_at_start(list(reversed(rows)),ORIGIN)['used_history_clears_utc']:self.assertLessEqual(t,ORIGIN)

    def test_each_origin_is_independent_of_previous_future_query(self):
        rows=history();a=predict_at_start(rows,'2026-10-01T00:00:00Z')
        b=predict_at_start(rows,'2026-09-02T00:00:00Z')
        self.assertEqual(b['status'],'insufficient_completed_history');self.assertLess(b['completed_history_n'],a['completed_history_n'])

    def test_empty_and_29_completed_do_not_fabricate_zero(self):
        for rows in ([],history(29)):
            r=predict_at_start(rows,ORIGIN);self.assertIsNone(r['prediction_minutes']);self.assertEqual(r['status'],'insufficient_completed_history')

    def test_open_and_not_yet_completed_events_are_not_history(self):
        rows=history();rows[0]['finished_at']='';rows[1]['finished_at']='2026-10-20T00:00:00Z'
        r=predict_at_start(rows,ORIGIN);self.assertEqual(r['completed_history_n'],28);self.assertIsNone(r['prediction_minutes'])

    def test_exact_clear_time_is_available(self):
        rows=history();origin=rows[-1]['finished_at']
        self.assertEqual(predict_at_start(rows,origin)['completed_history_n'],30)

    def test_late_record_availability_is_enforced(self):
        rows=history();rows[0]['available_at_utc']='2026-09-05T00:00:00Z'
        self.assertEqual(predict_at_start(rows,ORIGIN)['completed_history_n'],29)
        self.assertEqual(predict_at_start(rows,'2026-09-06T00:00:00Z')['completed_history_n'],30)

    def test_future_correction_cannot_change_historical_prediction(self):
        rows=history();rows[0]['available_at_utc']='2026-09-01T00:11:00Z'
        correction={**rows[0],'finished_at':'2026-09-01T01:00:00Z','available_at_utc':'2026-09-05T00:00:00Z'}
        self.assertEqual(value(predict_at_start(rows,ORIGIN)),value(predict_at_start(rows+[correction],ORIGIN)))

    def test_available_correction_overrides_old_clear_before_filtering(self):
        rows=history();rows[0]['available_at_utc']='2026-09-01T00:11:00Z'
        correction={**rows[0],'finished_at':'2026-09-05T00:00:00Z','available_at_utc':'2026-09-03T00:00:00Z'}
        self.assertEqual(predict_at_start(rows+[correction],ORIGIN)['completed_history_n'],29)

    def test_known_type_correction_supersedes_old_air_raid_version(self):
        rows=history();rows[0]['available_at_utc']='2026-09-01T00:11:00Z'
        correction={**rows[0],'alert_type':'artillery_shelling','available_at_utc':'2026-09-03T00:00:00Z'}
        self.assertEqual(predict_at_start(rows+[correction],ORIGIN)['completed_history_n'],29)

    def test_known_start_correction_supersedes_old_completed_version(self):
        rows=history();rows[0]['available_at_utc']='2026-09-01T00:11:00Z'
        correction={**rows[0],'started_at':'2026-09-05T00:00:00Z',
                    'finished_at':'future end must not be inspected','available_at_utc':'2026-09-03T00:00:00Z'}
        self.assertEqual(predict_at_start(rows+[correction],ORIGIN)['completed_history_n'],29)

    def test_conflicts_without_availability_are_errors(self):
        rows=history();correction={**rows[0],'finished_at':'2026-09-01T01:00:00Z'}
        with self.assertRaises(InputError):predict_at_start(rows+[correction],ORIGIN)

    def test_duplicates_are_one_completion(self):
        rows=history();self.assertEqual(value(predict_at_start(rows+[dict(rows[0])],ORIGIN)),value(predict_at_start(rows,ORIGIN)))

    def test_bad_past_history_never_silently_forecasts(self):
        for edits in ({'finished_at':'NaN'},{'finished_at':'2026-08-01T00:00:00Z'},
                      {'started_at':'2026-09-01 00:00:00'},{'id':'²'}, {'location_title':'Київська область'}):
            rows=history();rows[0].update(edits)
            with self.assertRaises(InputError):predict_at_start(rows,ORIGIN)

    def test_overlaps_are_an_explicit_history_error(self):
        rows=history();rows[0]['finished_at']='2026-09-01T03:00:00Z'
        with self.assertRaises(InputError):predict_at_start(rows,ORIGIN)

    def test_empty_evaluation_writes_valid_header_and_unknown_metrics(self):
        result=evaluate_rows([],PROTOCOL)
        with tempfile.TemporaryDirectory() as temp:
            summary=write_results(Path(temp),result,{**PROTOCOL,'version':'test'}, {})
            self.assertEqual(summary['metrics']['n'],0);self.assertIsNone(summary['metrics']['MAE_minutes'])
            self.assertIsNone(json.loads((Path(temp)/'demo-example.json').read_text()))
            with (Path(temp)/'evaluation-predictions.csv').open() as f:self.assertEqual(list(csv.DictReader(f)),[])

    def test_short_history_is_warmup_not_output_crash(self):
        result=evaluate_rows(history(29),PROTOCOL);self.assertEqual(len(result['warmup']),29)
        with tempfile.TemporaryDirectory() as temp:write_results(Path(temp),result,{**PROTOCOL,'version':'test'}, {})

    def test_malformed_csv_schema_has_actionable_error(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'bad.csv';p.write_text('id\n1\n')
            with self.assertRaisesRegex(InputError,'schema'):read_input(p)
        with self.assertRaises(InputError):evaluate_rows([{'id':None}],PROTOCOL)

    def test_saved_results_cannot_be_overwritten(self):
        for output in ('data/latest/results','research/raw','protocol'):
            with self.assertRaises(InputError):run(Path('/tmp/audit-test'),Path('/tmp/audit-test/data/latest/inputs/a.csv'),Path('/tmp/audit-test')/output)

if __name__=='__main__':unittest.main()
