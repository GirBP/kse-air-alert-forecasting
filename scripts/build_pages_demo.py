"""Build licensed synthetic UX fixtures using the unchanged default predictor.

Real aggregates are copied from retained verified reports; no historical inference,
selection, training, source download or private interval publication occurs here.
"""
import argparse
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from kse_latest.forecast import predict_at_start, stamp

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def synthetic_examples():
    cases = [('typical', 'Типовий сценарій', 8, 24, 'Невелика різниця між типовою оцінкою та завершенням.'),
             ('long', 'Довгий інтервал', 81, 180, 'Тривалий інтервал навіть за довшої попередньої історії.'),
             ('failure', 'Велика помилка', 5, 240, 'Коротка попередня історія не попереджає про довгий епізод.')]
    examples = []
    for index, (key, title, base, actual, note) in enumerate(cases):
        origin = datetime(2026, 9, 20 + index, 9, tzinfo=timezone.utc)
        rows = []
        for i in range(30):
            start = origin - timedelta(hours=4 * (31 - i))
            rows.append(dict(id=str(i+1), location_uid='31', location_title='м. Київ',
                location_oblast='м. Київ', location_type='oblast', location_raion='',
                alert_type='air_raid', started_at=stamp(start),
                finished_at=stamp(start + timedelta(minutes=base+i))))
        forecast = predict_at_start(rows, stamp(origin))
        assert forecast['status'] == 'predicted'
        # Outcome is deliberately attached only AFTER inference.
        examples.append(dict(id=key, title=title, note=note, synthetic=True,
            origin_local=forecast['forecast_origin_local'],
            prediction_minutes=forecast['prediction_minutes'],
            actual_minutes=actual, history_n=forecast['completed_history_n'],
            used_n=forecast['used_history_n'], history_base_minutes=base,
            absolute_error_minutes=abs(forecast['prediction_minutes'] - actual)))
    return examples

def build(root):
    root = Path(root)
    diagnostic = root / 'reports/ml-diagnostics/diagnostic-evidence.json'
    evidence = json.loads(diagnostic.read_text())
    m = evidence['overall_rolling']
    with (root/'reports/ml-diagnostics/large-underpredictions.csv').open() as stream:
        tails=list(csv.DictReader(stream))
    tail=next(row for row in tails if float(row['underprediction_more_than_minutes'])==60)
    assert m['n'] == 84 and evidence['original_predictions_recomputed_without_model_import']
    protocol = json.loads((root/'protocol/latest-v1.json').read_text())
    source = protocol['source']
    data = dict(schema_version=1, mode='historical_demo_with_explicitly_synthetic_ux_examples',
        method='median_last_30_completed', target='total_registered_duration_at_start',
        source=dict(name='alerts.in.ua через JustJimer mirror', location_uid='31',
            snapshot_sha256=source['snapshot_sha256'],
            version='7abc556ba5a0ff47a9e33c6abc136b8da3a9feb8',
            evaluation_end_utc_exclusive=protocol['evaluation_end_utc_exclusive'],
            observation_completeness_proven=False, historical_publication_availability_proven=False),
        primary84=dict(n=84, MAE=m['MAE'], RMSE=m['RMSE'], median_AE=m['median_AE'],
            p90_AE=m['p90_AE'], within30_n=m['within30_n'], within60_n=m['within60_n'],
            under60_n=int(tail['n']), largest_AE=float(tail['max_shortfall_minutes']), long_n=7,
            long_sse_share=evidence['long_sse_share'], evaluation_excluded=0,
            status='previously_exposed_retrospective_evaluation'),
        latest91=None,
        examples=synthetic_examples(),
        selection_rule='Авторські синтетичні сценарії: typical=(8..37 хв, факт24); long=(81..110, факт180); failure=(5..34, факт240). Історія кожного містить30 завершень; медіана обчислена unchanged kse_latest. Дати та факти вигадані. Жодного відбору реальних рядків за помилкою.',
        licensing='Mirror redistribution rights not established; no real event-level records are included.',
        evidence=dict(path='reports/ml-diagnostics/diagnostic-evidence.json', sha256=sha(diagnostic),
            forecast_code_sha256=sha(root/'src/kse_latest/forecast.py')))
    # The auditor owns current-source acquisition/diagnostics; integrate only explicit handoff.
    handoff = root/'reports/latest91/aggregate.json'
    if handoff.exists():
        data['latest91'] = json.loads(handoff.read_text())
    out=root/'web/assets/demo-data.json'
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    return out

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=ROOT)
    args=parser.parse_args()
    print(build(args.project_root))
