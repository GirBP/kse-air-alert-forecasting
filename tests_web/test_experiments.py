import io,csv,hashlib,importlib.util,json,os,subprocess,unittest
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[1]
class ExperimentsTests(unittest.TestCase):
 def test_saved_results_complete_and_exact(self):
  d=json.loads((ROOT/'web/assets/experiments.json').read_text());source=ROOT/'reports/website-experiments'
  expected={r['family_key']:r for r in csv.DictReader(io.StringIO((source/'v3-selected.csv').read_text())) if r['headline_eligible']=='True'}
  displayed={r['id']:r for g in d['groups'] if g['study']=='v3' for r in g['rows'] if not r['id'].startswith('fixed30-')}
  self.assertEqual(set(displayed),set(expected));self.assertEqual(len(displayed),87)
  for key,r in displayed.items():
   self.assertEqual(r['mae'],float(expected[key]['MAE']));self.assertEqual(r['rmse'],float(expected[key]['RMSE']))
  for g in d['groups']:
   self.assertEqual([r['mae'] for r in g['rows']],sorted(r['mae'] for r in g['rows']))
   self.assertTrue(g['events']>0)
   if g['target']=='T0':self.assertEqual(g['events'],g['predictions'])
  self.assertEqual(len(d['blocked']),2);self.assertFalse(d['new_model_selected'])
  incomplete=[g for g in d['groups'] if g.get('incomplete')];self.assertEqual(len(incomplete),1);self.assertEqual(incomplete[0]['predictions'],815)
 def test_spatial_rows_and_seed_means_preserved(self):
  d=json.loads((ROOT/'web/assets/experiments.json').read_text());source=ROOT/'reports/website-experiments'
  primary={r['run_id']:r for r in csv.DictReader(io.StringIO((source/'v4-primary.csv').read_text())) if r['family']!='NN'}
  neural=list(csv.DictReader(io.StringIO((source/'v4-neural-means.csv').read_text())))
  displayed=[r for g in d['groups'] if g['study']=='v4' for r in g['rows']]
  for r in displayed:
   if r['method']!='NN':self.assertEqual(r['mae'],float(primary.pop(r['id'])['mae']))
   else:
    group=next(g for g in d['groups'] if r in g['rows']);matches=[v for v in neural if v['target']==group['target'] and v['fold']==group['fold'] and v['view']==r['features'] and v['transfer']==r['transfer'] and v['delay']=='0' and v['s1']=='False']
    self.assertEqual(len(matches),1);self.assertEqual(r['seeds'],3);self.assertEqual(r['mae'],float(matches[0]['mae']))
  self.assertFalse(primary)
 def test_builder_reproducible(self):
  spec=importlib.util.spec_from_file_location('experiments',ROOT/'scripts/build_pages_experiments.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  before=(ROOT/'web/assets/experiments.json').read_bytes();m.build(ROOT);self.assertEqual(before,(ROOT/'web/assets/experiments.json').read_bytes())
 def test_complete_static_translations(self):
  translations=json.loads((ROOT/'web/assets/translations.json').read_text());keys=[]
  class Parser(HTMLParser):
   def handle_starttag(self,tag,attrs):
    a=dict(attrs)
    if 'data-i18n' in a:keys.append(a['data-i18n'])
  Parser().feed((ROOT/'web/index.html').read_text())
  for key in keys:self.assertEqual(len(translations[key]),2);self.assertTrue(all(translations[key]))
 def test_date_and_remaining_contracts_across_timezones(self):
  for zone in ['UTC','America/New_York','Asia/Tokyo']:
   p=subprocess.run(['node',str(ROOT/'tests_web/ux_contracts.mjs')],capture_output=True,text=True,env={**os.environ,'TZ':zone});self.assertEqual(p.returncode,0,p.stdout+p.stderr)
if __name__=='__main__':unittest.main()
