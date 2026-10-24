"""Read-only independent checks of saved predictions and derived experimental tables."""
from pathlib import Path
import sys,json,re,argparse,datetime,hashlib
sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'_tools/pylibs312'))
import numpy as np,pandas as pd

KEYS=['stage','seed','target','protocol','representation','model']
STAGES={25000:[42,143,244,345,446],100000:[42]}
CATS=['C0','C1','C2','C3','CU']
P=ROOT/'实验12_化学表示与新颖性'

def close(a,b,label):
 assert np.allclose(np.asarray(a,dtype=float),np.asarray(b,dtype=float),rtol=1e-10,atol=1e-12,equal_nan=True),label

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument('--save',action='store_true')
 args=parser.parse_args()
 results=[]
 for scope,reps in [('outputs',['G','B','I','O']),('outputs_mapped_common',['G','B','I','O','T'])]:
  root=P/scope
  tables={path.stem:pd.read_csv(path) for path in root.glob('*.csv') if path.stat().st_size>2}
  indexed={name:tables[name].set_index(KEYS) for name in ['pooled_metrics','per_topology_metrics','C3_subtype_metrics','novelty_error_metrics']}
  count_files=nonempty_files=record_count=fold_count=empty_folds=0
  armkeys=set()
  raw_checked=topo_checked=subtype_checked=0
  max_metric_diff=0.
  stage_info=[]
  for stage,seeds in STAGES.items():
   for seed in seeds:
    for target in ['uptake','selectivity']:
     folder=root/f'n{stage}_seed{seed}_{target}'
     sample=pd.read_csv(folder/'sample.csv.gz')
     sample_by_id=sample.set_index('raw_row_id')
     assert sample.raw_row_id.is_unique
     original=pd.read_csv(folder/'original_sample_coverage.csv.gz') if scope.endswith('mapped_common') else sample
     info=dict(stage=stage,seed=seed,target=target,n_records=len(sample),n_topologies=sample.topology.nunique(),files=0,nonempty_files=0)
     for protocol in ['random','topology','LOTO']:
      nf=5 if protocol!='LOTO' else original.topology.nunique()
      folders=[folder/f'{protocol}_fold{i}' for i in range(nf)]
      actual={f.name for f in folder.glob(protocol+'_fold*') if f.is_dir()}
      assert actual=={f.name for f in folders}
      parts=[];preds={(rep,model):[] for rep in reps for model in ['RF','ET']}
      for fp in folders:
       with np.load(fp/'split.npz') as sp:
        tr,te=sp['train_raw_id'],sp['test_raw_id']
       assert len(np.unique(tr))==len(tr) and len(np.unique(te))==len(te)
       assert not np.intersect1d(tr,te).size
       assert set(tr)|set(te)==set(sample.raw_row_id)
       if protocol!='random':
        assert set(sample_by_id.loc[tr].topology).isdisjoint(set(sample_by_id.loc[te].topology))
       z=pd.read_csv(fp/('novelty_chemistry.csv.gz' if scope.endswith('mapped_common') else 'novelty.csv.gz'))
       assert np.array_equal(z.raw_row_id,te)
       close(z.y_true,sample_by_id.loc[te].y_true,'diagnostic labels')
       assert z.novelty_class.isin(CATS).all()
       fold_count+=1;empty_folds+=int(len(te)==0)
       if len(te):parts.append(z)
       expected={f'prediction_{rep}_{model}.npz' for rep,model in preds}
       actual={v.name for v in fp.glob('prediction_*.npz') if '.tmp.' not in v.name}
       assert actual==expected,(scope,fp,actual^expected)
       for (rep,model),saved in preds.items():
        with np.load(fp/f'prediction_{rep}_{model}.npz') as v:
         assert np.array_equal(v['raw_row_id'],te)
         close(v['y_true'],z.y_true,'prediction labels')
         assert v['prediction'].shape==(len(te),) and np.isfinite(v['prediction']).all()
         if len(te):saved.append(v['prediction'].copy())
        count_files+=1;nonempty_files+=int(len(te)>0);record_count+=len(te)
        info['files']+=1;info['nonempty_files']+=int(len(te)>0)
      z=pd.concat(parts,ignore_index=True)
      assert z.raw_row_id.is_unique and set(z.raw_row_id)==set(sample.raw_row_id)
      y=z.y_true.to_numpy()
      # NumPy logical operations deliberately avoid the production summary code.
      unseen_metal=np.logical_not(z.metal_seen.to_numpy(dtype=bool))
      for (rep,model),saved in preds.items():
       key=(stage,seed,target,protocol,rep,model);armkeys.add(key)
       pred=np.concatenate(saved);error=pred-y
       row=indexed['pooled_metrics'].loc[key]
       assert int(row.n)==len(y)
       direct=[np.abs(error).mean(),np.sqrt(np.mean(error**2)),error.mean(),np.var(y)]
       stored=[row.MAE,row.RMSE,row.bias,row.y_variance]
       close(stored,direct,('pooled',key))
       max_metric_diff=max(max_metric_diff,float(np.max(np.abs(np.asarray(stored)-direct))))
       r2=1-np.square(error).sum()/np.square(y-y.mean()).sum()
       close(row.R2,r2,('R2',key));raw_checked+=1
       topo=indexed['per_topology_metrics'].loc[[key]]
       for t,q in z.groupby('topology'):
        r=topo[topo.topology.eq(t)]
        assert len(r)==1
        ix=q.index.to_numpy();e=error[ix]
        close(r[['MAE','RMSE','bias']].iloc[0],[np.abs(e).mean(),np.sqrt(np.mean(e**2)),e.mean()],('topology metrics',key,t))
        close(r[['coarse_unseen_fraction','building_unit_unseen_fraction','outside_fraction']].iloc[0],
          [np.logical_not(q.coarse_seen.to_numpy(dtype=bool)).mean(),q.novelty_class.eq('C3').mean(),q.scalar_outside.to_numpy(dtype=bool).mean()],('topology support',key,t))
        topo_checked+=1
       subs=indexed['C3_subtype_metrics'].loc[[key]]
       for m in [False,True]:
        for n in [0,1,2]:
         mask=z.novelty_class.eq('C3').to_numpy() & (unseen_metal==m) & z.n_unseen_linkers.eq(n).to_numpy()
         r=subs[subs.unseen_metal.eq(m)&subs.n_unseen_linker_slots.eq(n)]
         assert len(r)==1 and int(r.iloc[0].n)==int(mask.sum()),('C3 counts',key,m,n)
         if mask.any():
          close(r[['MAE','RMSE','bias']].iloc[0],[np.abs(error[mask]).mean(),np.sqrt(np.mean(error[mask]**2)),error[mask].mean()],('C3 errors',key,m,n))
         else:assert r[['MAE','RMSE','bias']].isna().all().all()
         subtype_checked+=1
     stage_info.append(info)
  pooled=tables['pooled_metrics'].set_index(KEYS)
  assert set(pooled.index)==armkeys and not pooled.index.duplicated().any()
  # Reconcile every partition and its weighted errors against the pooled results.
  def partition(frame,extra):
   for _,part in frame.groupby(extra) if extra else [(None,frame)]:
    sums=part.groupby(KEYS).n.sum().sort_index()
    assert sums.equals(pooled.n.sort_index()),('partition counts',extra)
    for col,power in [('MAE',1),('RMSE',2),('bias',1)]:
     weighted=part.assign(_weighted=part[col].pow(power).fillna(0)*part.n).groupby(KEYS)._weighted.sum()/pooled.n
     close(weighted.sort_index(),pooled[col].pow(power).sort_index(),('weighted partition',extra,col))
  cats=tables['novelty_error_metrics']
  partition(cats[cats.scalar_domain.eq('all')],[])
  for name,extra in [('per_topology_metrics',[]),('C3_subtype_metrics',None),('seen_unseen_error_metrics',['identity_field']),('novelty_distance_sensitivity',['distance_rule'])]:
   if extra is not None:partition(tables[name],extra)
  classkeys=KEYS+['novelty_class']
  for col in ['n']:
   close(cats[cats.scalar_domain.ne('all')].groupby(classkeys)[col].sum().sort_index(),
     cats[cats.scalar_domain.eq('all')].set_index(classkeys)[col].sort_index(),'inside/outside counts')
  for _,q in tables['paired_representation_differences'].query("novelty_class == 'ALL'").groupby('contrast'):
   left,right=q.contrast.iloc[0].split('-')
   base=['stage','seed','target','protocol','model']
   l=tables['pooled_metrics'].query('representation == @left').set_index(base)
   r=tables['pooled_metrics'].query('representation == @right').set_index(base)
   d=q.set_index(base)
   close(d.delta_MAE.sort_index(),(l.MAE-r.MAE).sort_index(),'paired MAE')
   close(d.delta_R2.sort_index(),(l.R2-r.R2).sort_index(),'paired R2')
  rank=tables['novelty_ranking_contributions']
  for _,q in rank[rank.ranking_scope.eq('global_pooled_OOF')].groupby(KEYS+['budget_fraction']):
   assert q.n_true_topk.sum()==q.k.iloc[0] and q.n_predicted_topk.sum()==q.k.iloc[0]
   assert (q.n_hits<=q.n_true_topk).all() and (q.n_hits<=q.n_predicted_topk).all()
  # Main and complete manuscript tables must be exact scoped copies.
  copied=0
  for label,scope_table in [('main','paper_tables_main'),('all','paper_tables')]:
   prefix='mapped_common' if scope.endswith('mapped_common') else 'full'
   for name,frame in tables.items():
    dst=P/scope_table/f'{prefix}_{name}.csv'
    if not dst.exists() or dst.stat().st_size<=2:continue
    expected=frame[frame.stage.eq(25000)] if label=='main' and 'stage' in frame else frame
    actual=pd.read_csv(dst)
    assert actual.shape==expected.shape,(dst,'shape')
    # CSV reserialization can change a last floating-point bit.
    for col in expected:
     if pd.api.types.is_numeric_dtype(expected[col]) and not pd.api.types.is_bool_dtype(expected[col]):
      close(actual[col],expected[col],(dst,col))
     else:
      assert actual[col].fillna('__NA__').astype(str).tolist()==expected[col].fillna('__NA__').astype(str).tolist(),(dst,col)
    copied+=1
  results.append(dict(scope=scope,status='passed',n_complete_arms=len(armkeys),n_prediction_files=count_files,
   n_nonempty_prediction_files=nonempty_files,n_empty_prediction_files=count_files-nonempty_files,
   n_prediction_records=record_count,n_fold_directories=fold_count,n_empty_test_folds=empty_folds,
   n_raw_pooled_metric_checks=raw_checked,n_raw_topology_checks=topo_checked,n_raw_C3_subtype_checks=subtype_checked,
   max_pooled_metric_abs_difference=max_metric_diff,n_manuscript_table_copies_checked=copied,samples=stage_info))
 report=dict(status='passed',checked_at=datetime.datetime.now().astimezone().isoformat(),results=results,
  scope='Saved predictions, IDs, labels, fold separation and derived tables; no model refitting or new chemistry validation',
  checks=['complete planned matrix with no missing or extra prediction files','unique row coverage and topology isolation',
   'finite saved predictions and original sample labels','pooled and per-topology errors independently recomputed',
   'Boolean topology fractions and all C3 subtype counts/errors independently recomputed',
   'all novelty, identity and distance partitions reconcile','paired representation differences reconcile',
   'global top-k counts reconcile','main-only and complete manuscript copies match their scopes'])
 if args.save:(P/'summary_repair_verification_20261023.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
 print(json.dumps(report,indent=2,ensure_ascii=False))
if __name__=='__main__':main()
