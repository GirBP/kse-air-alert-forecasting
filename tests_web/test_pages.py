"""Release-path contracts; independent checks of the static presentation boundary."""
import importlib.util
import json
from pathlib import Path
import unittest
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('builder',ROOT/'scripts/build_pages_demo.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

class Resources(HTMLParser):
    def __init__(self):super().__init__();self.local=[];self.ids=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        for name in ('href','src'):
            url=a.get(name,'')
            if url and not url.startswith(('http:','https:','mailto:','#')):self.local.append(url)

class PagesTests(unittest.TestCase):
    def setUp(self):self.data=json.loads((ROOT/'web/assets/demo-data.json').read_text())
    def test_saved_fixtures_match_actual_target_free_default(self):
        self.assertEqual(self.data['examples'],builder.synthetic_examples())
        for row in self.data['examples']:
            self.assertTrue(row['synthetic']);self.assertEqual(row['history_n'],30)
            self.assertEqual(row['prediction_minutes'],row['history_base_minutes']+14.5)
        self.assertEqual({r['id'] for r in self.data['examples']},{'typical','long','failure'})
    def test_aggregate_numbers_and_source_binding(self):
        evidence=json.loads((ROOT/'reports/ml-diagnostics/diagnostic-evidence.json').read_text())
        self.assertEqual(self.data['evidence']['sha256'],builder.sha(ROOT/'reports/ml-diagnostics/diagnostic-evidence.json'))
        self.assertEqual(self.data['evidence']['forecast_code_sha256'],builder.sha(ROOT/'src/kse_latest/forecast.py'))
        for k in ('MAE','RMSE','median_AE','p90_AE','n'):
            self.assertEqual(self.data['primary84'][k],evidence['overall_rolling'][k])
        latest=json.loads((ROOT/'reports/latest91/aggregate.json').read_text())
        self.assertEqual(self.data['latest91'],latest)
        self.assertEqual(latest['n'],91);self.assertFalse(latest['independent_test'])
    def test_static_paths_and_outcome_separation(self):
        p=Resources();p.feed((ROOT/'web/index.html').read_text())
        self.assertEqual(len(p.ids),len(set(p.ids)))
        for local in p.local:
            self.assertFalse(local.startswith('/'));self.assertTrue((ROOT/'web'/local).is_file())
        html=(ROOT/'web/index.html').read_text()
        self.assertIn('id="outcome" class="outcome" hidden',html)
        self.assertIn('aria-controls="outcome"',html)
        self.assertIn('Синтетичні UX-приклади',html)
    def test_no_research_or_prospective_inference_on_public_route(self):
        for p in (ROOT/'web').rglob('*'):
            if p.is_file():
                text=p.read_text()
                for forbidden in ('forecast_once','collect_once','kse_spatial_v4','model.pkl','model.pt'):
                    self.assertNotIn(forbidden,text)
        self.assertNotIn('used_history_ids',json.dumps(self.data))
        self.assertNotIn('finished_at',json.dumps(self.data))
    def test_release_manifest_binds_served_files(self):
        release=json.loads((ROOT/'web/release.json').read_text())
        self.assertEqual(release['version'],'pages-v1.1')
        self.assertIn('data-release-version="pages-v1.1"',(ROOT/'web/index.html').read_text())
        for item in release['artifact_files']:
            self.assertEqual(item['sha256'],builder.sha(ROOT/'web'/item['path']))

    def test_build_is_deterministic_and_preserves_science(self):
        before=(ROOT/'web/assets/demo-data.json').read_bytes()
        builder.build(ROOT)
        self.assertEqual(before,(ROOT/'web/assets/demo-data.json').read_bytes())

if __name__=='__main__':unittest.main()
