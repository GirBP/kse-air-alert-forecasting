import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest
from kse_latest.duration import aware, select, forecasts, metrics, quantile, run

PROTOCOL={'source':{'location_uid':'31','location_title':'м. Київ','location_type':'oblast'},
          'history_start_local_inclusive':'2026-09-01T00:00:00+03:00',
          'evaluation_start_local_inclusive':'2026-10-01T00:00:00+03:00',
          'evaluation_end_utc_exclusive':'2026-10-11T10:07:59Z'}

def row(event_id='1',start='2026-09-10T00:00:00Z',end='2026-09-10T01:00:00Z',**extra):
    return {'id':event_id,'location_uid':'31','location_title':'м. Київ','location_type':'oblast',
            'location_oblast':'м. Київ','location_raion':'','alert_type':'air_raid',
            'started_at':start,'finished_at':end,'alert_level':'yellow',**extra}

def events(n=32):
    start=datetime(2026,9,1,tzinfo=timezone.utc)
    return [{'id':str(i+1),'start':start+timedelta(hours=2*i),'end':start+timedelta(hours=2*i,minutes=10+i),
             'duration':float(10+i),'phase':'history','row_number':i+1,'level':'yellow'} for i in range(n)]

class DurationTests(unittest.TestCase):
    def test_utc_is_required(self):
        with self.assertRaises(ValueError):aware('2026-09-10 00:00:00')
        accepted,excluded,_,_=select([row(start='2026-09-10 00:00:00')],PROTOCOL)
        self.assertFalse(accepted);self.assertEqual(excluded[0]['reason'],'unresolved_start')

    def test_location_and_type_are_not_blended(self):
        accepted,excluded,_,n=select([row(location_uid='14'),row(event_id='2',location_title='Київська область'),row(event_id='3',alert_type='artillery_shelling')],PROTOCOL)
        self.assertEqual(n,2);self.assertFalse(accepted)
        self.assertEqual({r['reason'] for r in excluded},{'wrong_territory','wrong_alert_type'})

    def test_closed_actual_positive_only(self):
        accepted,excluded,_,_=select([row(end=''),row(event_id='2',end='2026-09-10T00:00:00Z')],PROTOCOL)
        self.assertFalse(accepted);self.assertEqual({r['reason'] for r in excluded},{'open_or_invalid_clear','nonpositive_duration'})

    def test_boundary_clear_is_excluded(self):
        accepted,excluded,_,_=select([row(start='2026-10-11T10:00:00Z',end=PROTOCOL['evaluation_end_utc_exclusive'])],PROTOCOL)
        self.assertFalse(accepted);self.assertEqual(excluded[0]['reason'],'clear_at_or_after_snapshot_boundary')

    def test_october_is_defined_in_kyiv_not_utc(self):
        accepted,excluded,_,_=select([row(start='2026-09-30T23:50:00Z',end='2026-10-01T00:20:00Z')],PROTOCOL)
        self.assertEqual(accepted[0]['phase'],'evaluation');self.assertFalse(excluded)

    def test_duplicates_and_conflicts_are_audited(self):
        accepted,excluded,duplicates,_=select([row(),row()],PROTOCOL)
        self.assertEqual(len(accepted),1);self.assertEqual(duplicates,1);self.assertFalse(excluded)
        accepted,excluded,_,_=select([row(),row(end='2026-09-10T02:00:00Z')],PROTOCOL)
        self.assertFalse(accepted);self.assertEqual(len(excluded),2)

    def test_both_overlapping_events_are_excluded(self):
        accepted,excluded,_,_=select([row(),row(event_id='2',start='2026-09-10T00:30:00Z')],PROTOCOL)
        self.assertFalse(accepted);self.assertEqual({r['reason'] for r in excluded},{'overlap'})

    def test_red_and_yellow_accepted_without_features(self):
        accepted,excluded,_,_=select([row(alert_level='red')],PROTOCOL)
        self.assertEqual(len(accepted),1);self.assertFalse(excluded)

    def test_history_warmup_and_exact_window(self):
        predictions,warmup=forecasts(events())
        self.assertEqual(len(warmup),30);self.assertEqual(len(predictions),2)
        self.assertEqual(predictions[0]['completed_history_n'],30)
        self.assertEqual(predictions[0]['prediction_minutes'],24.5)
        self.assertEqual(json.loads(predictions[1]['used_history_ids'])[0],'2')

    def test_current_target_cannot_change_its_forecast(self):
        a=events();b=[dict(e) for e in a];b[30]['duration']=9999;b[30]['end']+=timedelta(days=3)
        first=forecasts(a)[0][0];changed=forecasts(b)[0][0]
        self.assertEqual(first['prediction_minutes'],changed['prediction_minutes'])
        self.assertNotIn('31',json.loads(changed['used_history_ids']))

    def test_completion_order_and_only_cleared_are_used(self):
        a=events(33)
        a[0]['end']=a[31]['start']+timedelta(seconds=1)
        a[0]['duration']=(a[0]['end']-a[0]['start']).total_seconds()/60
        predictions,warmup=forecasts(a)
        self.assertNotIn('1',json.loads(predictions[0]['used_history_ids']))
        self.assertIn('1',json.loads(predictions[-1]['used_history_ids']))
        for p in predictions:
            self.assertTrue(all(aware(e)<=aware(p['forecast_origin_utc']) for e in json.loads(p['used_history_clears_utc'])))

    def test_clear_at_origin_is_available(self):
        a=events(31);a[29]['end']=a[30]['start'];a[29]['duration']=120
        predictions,_=forecasts(a)
        self.assertEqual(len(predictions),1);self.assertIn('30',json.loads(predictions[0]['used_history_ids']))

    def test_metrics_do_not_drop_long_errors(self):
        value=metrics([{'absolute_error_minutes':1},{'absolute_error_minutes':999}])
        self.assertEqual(value['n'],2);self.assertEqual(value['MAE_minutes'],500)
        self.assertAlmostEqual(quantile([10,20],.9),19)
        self.assertIsNone(metrics([])['MAE_minutes'])

    def test_output_cannot_overwrite_old_experiments(self):
        for folder in ['data/pilot','data/duration-pilot-v2','data/duration-final','research/raw','data/derived']:
            with self.assertRaises(ValueError):run(Path('/tmp/kse-check'),Path('/tmp/kse-check/data/latest/inputs/a.csv'),Path('/tmp/kse-check')/folder)

if __name__=='__main__':unittest.main()
