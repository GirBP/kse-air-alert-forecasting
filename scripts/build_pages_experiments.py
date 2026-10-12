"""Present saved aggregate results. Never train, select a new model or merge cohorts."""
import csv,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def build(root=ROOT):
 source=root/'reports/website-experiments'
 def rows(name):
  with (source/name).open() as f:return list(csv.DictReader(f))
 manifest=json.loads((source/'sources.json').read_text())
 for item in manifest:
  assert hashlib.sha256((source/item['file']).read_bytes()).hexdigest()==item['sha256']
 params=json.loads((source/'v3-selected-parameters.json').read_text())
 groups={};blocked=[]
 def add(key,meta,item):
  if key not in groups:groups[key]={**meta,'id':key,'rows':[]}
  groups[key]['rows'].append(item)
 for r in rows('v3-selected.csv'):
  if r['headline_eligible']!='True':blocked.append({'method':r['method'],'track':r['track'],'reason':r['reason']});continue
  key='v3-'+r['track'];h=r['track']=='H-KYIV'
  add(key,{'study':'v3','track':r['track'],'target':'T0','source':'H' if h else 'N','fold':'H_SHIFT' if h else 'N_REPLAY','events':int(r['n']),'predictions':int(r['n']),'conditional':r['scenario']=='S1'},
   {'id':r['family_key'],'method':r['method'],'features':r['feature_set'],'mae':float(r['MAE']),'rmse':float(r['RMSE']),'seeds':int(r['seed_count']),'params':params.get(r['config_id'],{}),'training_n':float(r['n_fit_mean']) if r['n_fit_mean'] else None,'source_file':'v3-selected.csv'})
 for r in rows('v3-controls.csv'):
  key='v3-H-KYIV' if r['source']=='H' else 'v3-N-KYIV-S0'
  groups[key]['rows'].append({'id':'fixed30-'+r['source'],'method':'M30','features':'history','mae':float(r['MAE']),'rmse':float(r['RMSE']),'seeds':1,'params':{'K':30},'training_n':0,'source_file':'v3-controls.csv'})
 spatial=[r for r in rows('v4-primary.csv') if r['family']!='NN']
 for r in rows('v4-neural-means.csv'):
  if r['fold'] in ('H_REPLAY','H_SHIFT','N_REPLAY') and r['delay']=='0' and r['s1']=='False':
   assert r['seed_n']=='3';spatial.append({**r,'family':'NN','status':'COMPLETED','param':'','run_id':'mean3-'+r['target']+'-'+r['fold']+'-'+r['view']+'-'+r['transfer']})
 for r in spatial:
  assert r['status'] in ('COMPLETED','NOT_IDENTIFIABLE') and r['delay']=='0' and r['s1']=='False'
  n=int(float(r['n_events']));count=int(float(r['n_rows']));key='-'.join(['v4',r['target'],r['fold'],str(count)])
  add(key,{'study':'v4','track':'spatial','source':r['source'],'target':r['target'],'fold':r['fold'],'events':n,'predictions':count,'conditional':False,'incomplete':r['status']!='COMPLETED'},
   {'id':r['run_id'],'method':r['family'],'features':r['view'],'transfer':r['transfer'],'mae':float(r['mae']),'rmse':float(r['rmse']),'seeds':3 if r['family']=='NN' else 1,'params':{'parameter':r['param']} if r['param'] else {},'source_file':'v4-neural-means.csv' if r['family']=='NN' else 'v4-primary.csv'})
 fits=rows('v4-fit-costs.csv')
 for g in groups.values():
  if g['study']!='v4':continue
  g['training_cutoff']={'H_REPLAY':'2025-07-01','H_SHIFT':'2026-01-01','N_REPLAY':'2026-10-01'}[g['fold']]
  for r in g['rows']:
   matches=[f for f in fits if f['target']==g['target'] and f['fold']==g['fold'] and f['family']==r['method'] and f['view']==r['features'] and f['transfer']==r['transfer'] and f['delay']=='0' and f['s1']=='False']
   assert matches
   r['training']={}
   for key in ['train_n_events','train_n_rows','n_completed','n_censored']:
    values={f[key] for f in matches if f[key]!=''}
    assert len(values)<=1
    if values:r['training'][key]=int(float(values.pop()))
 for group in groups.values():
  group['rows'].sort(key=lambda r:(r['mae'],r['id']))
  assert len({r['id'] for r in group['rows']})==len(group['rows'])
 ordered=sorted(groups.values(),key=lambda g:(g['id']!='v3-N-KYIV-S0',g['study'],g['target'],g['fold'],g['id']))
 output={'schema_version':1,'scientific_status':'exploratory_retrospective_previously_exposed','precision':'source values preserved; UI rounds to one decimal','new_model_selected':False,'groups':ordered,'blocked':blocked,'sources':manifest}
 (root/'web/assets/experiments.json').write_text(json.dumps(output,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
 return output
if __name__=='__main__':
 d=build();print(json.dumps({'groups':len(d['groups']),'comparisons':sum(len(g['rows']) for g in d['groups']),'not_evaluated':len(d['blocked'])}))
