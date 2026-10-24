from pathlib import Path
import sys,json,re,hashlib,warnings,argparse
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'_tools/pylibs312'))
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import r2_score,mean_absolute_error,mean_squared_error
P=ROOT/'实验12_化学表示与新颖性';O=P/'outputs';CATS=['C0','C1','C2','C3','CU']
def stats(y,p):
 e=p-y
 return dict(n=len(y),R2=float(r2_score(y,p)) if len(y)>=2 and np.var(y)>0 else np.nan,MAE=float(np.abs(e).mean()) if len(y) else np.nan,RMSE=float(np.sqrt(np.mean(e**2))) if len(y) else np.nan,bias=float(e.mean()) if len(y) else np.nan,spearman=float(spearmanr(y,p).statistic) if len(y)>=30 and np.ptp(y)>0 and np.ptp(p)>0 else np.nan,y_median=float(np.median(y)) if len(y) else np.nan,y_IQR=float(np.quantile(y,.75)-np.quantile(y,.25)) if len(y) else np.nan,y_variance=float(np.var(y)) if len(y) else np.nan)
def bootstrap_cluster(df,values,seed=42):
 # Conditional on saved fitted models; resample coarse-composition clusters, not rows.
 g=pd.DataFrame({'key':df.coarse_key.to_numpy(),'value':values}).groupby('key').value.agg(['sum','count']);n=len(g)
 if len(df)<30 or n<5:return np.nan,np.nan
 rng=np.random.default_rng(seed);v=[]
 for j in range(400):
  ix=rng.integers(0,n,n);v.append(g['sum'].to_numpy()[ix].sum()/g['count'].to_numpy()[ix].sum())
 return tuple(np.quantile(v,[.025,.975]))

BOOL_COLUMNS = [
 'metal_seen','linker1_seen','linker2_seen','linker1_union_seen','linker2_union_seen',
 'pair_seen','coarse_seen','fine_seen','functional_group_seen','pair_unordered_seen',
 'coarse_unordered_seen','scalar_outside','scalar_outside_q90','scalar_outside_q95',
 'scalar_outside_q99','scalar_unique_outside','scalar_k5_outside','pore_outside',
 'constant_column_exceeded','linker1_structure_seen','linker2_structure_seen',
 'both_parent_structures_seen',
]

def normalize_support_booleans(frame):
 # Empty CSV folds have object columns; never apply bitwise inversion to objects.
 for col in BOOL_COLUMNS:
  if col not in frame:
   continue
  values=frame[col].map({True:True,False:False,'True':True,'False':False})
  if values.isna().any():
   raise ValueError(f'Invalid or missing Boolean support flag: {col}')
  frame[col]=values.astype(bool)
 assert frame.novelty_class.isin(CATS).all()
 assert frame.n_unseen_linkers.isin([0,1,2]).all()
 assert np.array_equal(frame.n_unseen_linkers.to_numpy(),frame.linker1_seen.eq(False).astype(int).to_numpy()+frame.linker2_seen.eq(False).astype(int).to_numpy())
 assert not (frame.coarse_seen & frame.pair_seen.eq(False)).any()
 assert not (frame.pair_seen & (frame.linker1_seen.eq(False)|frame.linker2_seen.eq(False))).any()
 assert (frame.loc[frame.novelty_class.eq('C3'),'metal_seen'].eq(False) | frame.loc[frame.novelty_class.eq('C3'),'n_unseen_linkers'].gt(0)).all()
 return frame

def validate_derived_tables(tables):
 keys=['stage','seed','target','protocol','representation','model']
 pooled=tables['pooled_metrics'].set_index(keys)
 topo=tables['per_topology_metrics']
 for col in ['coarse_unseen_fraction','building_unit_unseen_fraction','outside_fraction']:
  assert topo[col].between(0,1).all(), col
 assert topo.groupby(keys).n.sum().sort_index().equals(pooled.n.sort_index())
 cats=tables['novelty_error_metrics']
 allcats=cats[cats.scalar_domain.eq('all')]
 assert allcats.groupby(keys).n.sum().sort_index().equals(pooled.n.sort_index())
 classkeys=keys+['novelty_class']
 totals=allcats.set_index(classkeys).n.sort_index()
 assert cats[cats.scalar_domain.ne('all')].groupby(classkeys).n.sum().sort_index().equals(totals)
 c3=allcats[allcats.novelty_class.eq('C3')].set_index(keys).n.sort_index()
 assert tables['C3_subtype_metrics'].groupby(keys).n.sum().sort_index().equals(c3), 'C3 subtype counts do not sum to C3'
 seen=tables['seen_unseen_error_metrics']
 for _,q in seen.groupby('identity_field'):
  assert q.groupby(keys).n.sum().sort_index().equals(pooled.n.sort_index())
 distance=tables['novelty_distance_sensitivity']
 for _,q in distance.groupby('distance_rule'):
  assert q.groupby(keys).n.sum().sort_index().equals(pooled.n.sort_index())
 for name in ['novelty_category_counts','role_and_key_sensitivity']:
  frame=tables[name]
  for col in frame.columns:
   if col.startswith('n_') or col.endswith('_unseen') or col.endswith('_unseen_linker'):
    assert frame[col].ge(0).all(), (name,col)
 return dict(status='passed',n_complete_arms=len(pooled),checks=[
  'all topology fractions within [0,1]',
  'topology and novelty counts sum to pooled counts',
  'inside plus outside counts equal all-domain counts',
  'C3 subtypes exhaust C3 exactly',
  'seen/unseen and each distance rule partition every pooled arm',
  'fold-level support counts are nonnegative',
 ])


def main():
 global O
 parser=argparse.ArgumentParser();parser.add_argument('--mapped',action='store_true');parser.add_argument('--stage',choices=['all','25000','100000'],default='all');args=parser.parse_args()
 if args.mapped:O=P/'outputs_mapped_common'
 pooled=[];foldrows=[];toporows=[];categories=[];noveltycounts=[];distance=[];paired=[];ranking=[];unknown=[];foldaudit=[];completeness=[];role=[];chemistry=[];subtypes=[];seenrows=[];topopaired=[]
 for folder in sorted(O.glob('n*_seed*_*')):
  if not folder.is_dir():continue
  match=re.fullmatch(r'n(\d+)_seed(\d+)_(uptake|selectivity)',folder.name)
  if not match:continue
  size,seed,target=match.groups()
  if args.stage!='all' and args.stage!=size:continue
  base=dict(stage=int(size),seed=int(seed),target=target);sample=pd.read_csv(folder/'sample.csv.gz');N=len(sample)
  for protocol in ['random','topology','LOTO']:
   fps=sorted(folder.glob(f'{protocol}_fold*'),key=lambda x:int(x.name.split('fold')[-1]));expected=5 if protocol!='LOTO' else (pd.read_csv(folder/'original_sample_coverage.csv.gz').topology.nunique() if (folder/'original_sample_coverage.csv.gz').exists() else sample.topology.nunique());complete=len(fps)==expected
   repmodels={};complete_keys=set();expected_repmodels=[(r,m) for r in (['G','B','I','O','T'] if args.mapped else ['G','B','I','O']) for m in ['RF','ET']]
   for fp in fps:
    if not (fp/'novelty.csv.gz').exists():complete=False;continue
    fidx=int(fp.name.split('fold')[-1]);b=dict(**base,protocol=protocol,fold=fidx);z=pd.read_csv(fp/('novelty_chemistry.csv.gz' if (fp/'novelty_chemistry.csv.gz').exists() else 'novelty.csv.gz'));z=normalize_support_booleans(z);z['fold']=fidx
    split=np.load(fp/'split.npz');assert np.array_equal(split['test_raw_id'],z.raw_row_id);assert not np.intersect1d(split['test_raw_id'],split['train_raw_id']).size
    for cls in CATS:
     q=z[z.novelty_class==cls];noveltycounts.append(dict(**b,novelty_class=cls,n=len(q),unique_coarse=q.coarse_key.nunique(),n_outside=int(q.scalar_outside.sum()),n_unseen_metal=int(q.metal_seen.eq(False).sum()),n_one_unseen_linker=int((q.n_unseen_linkers==1).sum()),n_two_unseen_linkers=int((q.n_unseen_linkers==2).sum())))
    role.append(dict(**b,n=len(z),ordered_coarse_unseen=int(z.coarse_seen.eq(False).sum()),unordered_coarse_unseen=int(z.coarse_unordered_seen.eq(False).sum()),role_specific_any_unseen_linker=int((z.n_unseen_linkers>0).sum()),union_any_unseen_linker=int((z.linker1_union_seen.eq(False)|z.linker2_union_seen.eq(False)).sum())))
    meta=json.loads((fp/'distance_and_support.json').read_text());foldaudit.append(dict(**b,**{k:v for k,v in meta.items() if not isinstance(v,(list,dict))}))
    for path in fp.glob('prediction_*.npz'):
     if '.tmp.' in path.name:continue
     rep,model=path.stem.split('_')[1:];assert (rep,model) in expected_repmodels;v=np.load(path);assert v['prediction'].shape==v['y_true'].shape==(len(z),);assert np.isfinite(v['prediction']).all();assert np.array_equal(v['raw_row_id'],z.raw_row_id);assert np.array_equal(v['y_true'],z.y_true.to_numpy()) or np.allclose(v['y_true'],z.y_true.to_numpy(),atol=1e-14,rtol=1e-14)
     w=z.copy();w['y_true']=v['y_true'];w['prediction']=v['prediction'];repmodels.setdefault((rep,model),[]).append(w)
     foldrows.append(dict(**b,representation=rep,model=model,**stats(v['y_true'],v['prediction'])))
    for path in fp.glob('encoding_*.json'):
     rep=path.stem.split('_')[1];info=json.loads(path.read_text())
     for field,m in info.get('fields',{}).items():unknown.append(dict(**b,representation=rep,field=field,unknown_fraction=m['unknown_test_fraction'],train_vocabulary_size=len(m['vocabulary'])))
   for rep,model in expected_repmodels:
    parts=repmodels.get((rep,model),[])
    b=dict(**base,protocol=protocol,representation=rep,model=model);w=normalize_support_booleans(pd.concat(parts,ignore_index=True)) if parts else sample.iloc[:0].copy();done=complete and len(parts)==expected and len(w)==N and w.raw_row_id.nunique()==N and set(w.raw_row_id)==set(sample.raw_row_id);completeness.append(dict(**b,expected_folds=int(expected),saved_folds=len(parts),expected_records=N,saved_records=len(w),complete=bool(done)))
    if not done:continue
    complete_keys.add((rep,model))
    assert len(w)==N and w.raw_row_id.is_unique
    met=stats(w.y_true.to_numpy(),w.prediction.to_numpy());tops=[]
    for topo,q in w.groupby('topology'):
     tmet=stats(q.y_true.to_numpy(),q.prediction.to_numpy());tops.append((tmet['R2'],len(q)));toporows.append(dict(**b,topology=topo,**tmet,coarse_unseen_fraction=float(q.coarse_seen.eq(False).mean()),building_unit_unseen_fraction=float((q.novelty_class=='C3').mean()),outside_fraction=float(q.scalar_outside.mean())))
    valid=[v for v in tops if np.isfinite(v[0])];met.update(macro_topology_R2=float(np.mean([v[0] for v in valid])) if valid else np.nan,weighted_topology_R2=float(np.average([v[0] for v in valid],weights=[v[1] for v in valid])) if valid else np.nan,median_topology_R2=float(np.median([v[0] for v in valid])) if valid else np.nan,n_defined_topology_R2=len(valid))
    pooled.append(dict(**b,**met))
    for cls in CATS:
     for domain in ['all','inside','outside']:
      mask=w.novelty_class==cls
      if domain!='all':mask &= w.scalar_outside==(domain=='outside')
      q=w[mask];u=q.coarse_key.nunique();r=stats(q.y_true.to_numpy(),q.prediction.to_numpy());ci=(np.nan,np.nan)
      if int(size)==25000 and int(seed)==42 and protocol=='LOTO' and domain=='all':ci=bootstrap_cluster(q,abs(q.prediction.to_numpy()-q.y_true.to_numpy()))
      categories.append(dict(**b,novelty_class=cls,scalar_domain=domain,unique_coarse=u,n_folds=q.fold.nunique(),sparse=len(q)<30 or u<5,MAE_cluster_CI95_low=ci[0],MAE_cluster_CI95_high=ci[1],CI_scope='conditional coarse-cluster bootstrap seed42 LOTO only; sparse unavailable',**r))
    for seen_col in ['coarse_seen','fine_seen','pair_seen','metal_seen','linker1_seen','linker2_seen']:
     for seen in [False,True]:
      q=w[w[seen_col]==seen];seenrows.append(dict(**b,identity_field=seen_col,seen=seen,unique_coarse=q.coarse_key.nunique(),**stats(q.y_true.to_numpy(),q.prediction.to_numpy())))
    for unseen_metal in [False,True]:
     for n_unseen in [0,1,2]:
      q=w[(w.novelty_class=='C3')&(w.metal_seen.eq(False)==unseen_metal)&(w.n_unseen_linkers==n_unseen)];u=q.coarse_key.nunique();subtypes.append(dict(**b,unseen_metal=unseen_metal,n_unseen_linker_slots=n_unseen,unique_coarse=u,sparse=len(q)<30 or u<5,**stats(q.y_true.to_numpy(),q.prediction.to_numpy())))
    if 'chemical_similarity_bin' in w:
     for typ in ['chemical_similarity_bin','parent_structure_status']:
      for val,q0 in w.groupby(typ):
       for domain in ['all','inside','outside']:
        q=q0 if domain=='all' else q0[q0.scalar_outside==(domain=='outside')];u=q.coarse_key.nunique();ci=(np.nan,np.nan)
        if int(size)==25000 and int(seed)==42 and protocol=='LOTO' and domain=='all':ci=bootstrap_cluster(q,abs(q.prediction.to_numpy()-q.y_true.to_numpy()))
        chemistry.append(dict(**b,stratifier=typ,stratum=val,scalar_domain=domain,unique_coarse=u,sparse=len(q)<30 or u<5,MAE_cluster_CI95_low=ci[0],MAE_cluster_CI95_high=ci[1],**stats(q.y_true.to_numpy(),q.prediction.to_numpy())))
    for flag in ['scalar_outside_q90','scalar_outside_q95','scalar_outside_q99','scalar_unique_outside','scalar_k5_outside','pore_outside']:
     for outside in [False,True]:
      q=w[w[flag]==outside];distance.append(dict(**b,distance_rule=flag,outside=outside,unique_coarse=q.coarse_key.nunique(),**stats(q.y_true.to_numpy(),q.prediction.to_numpy())))
    yt=w.y_true.to_numpy();pr=w.prediction.to_numpy();ids=w.raw_row_id.to_numpy()
    for frac in [.01,.05,.10]:
     k=int(np.ceil(N*frac));trueix=np.lexsort((ids,-yt))[:k];predix=np.lexsort((ids,-pr))[:k];hit=set(trueix)&set(predix)
     for cls in CATS:
      c=set(np.flatnonzero(w.novelty_class.to_numpy()==cls));nt=len(c&set(trueix));ranking.append(dict(**b,budget_fraction=frac,k=k,ranking_scope='global_pooled_OOF',novelty_class=cls,n_candidates=len(c),n_true_topk=nt,n_predicted_topk=len(c&set(predix)),n_hits=len(c&hit),within_global_true_topk_recall=len(c&hit)/nt if nt else np.nan,candidate_fraction=len(c)/N,true_topk_fraction=nt/k,predicted_topk_fraction=len(c&set(predix))/k,hit_fraction=len(c&hit)/len(hit) if hit else np.nan))
    # Within-class ranking needs at least 100 observations for a 1% budget.
    for cls,q in w.groupby('novelty_class'):
     if len(q)<100:continue
     kk=int(np.ceil(len(q)*.01));yi=q.y_true.to_numpy();pi=q.prediction.to_numpy();ri=q.raw_row_id.to_numpy();rec=len(set(np.lexsort((ri,-yi))[:kk])&set(np.lexsort((ri,-pi))[:kk]))/kk
     ranking.append(dict(**b,budget_fraction=.01,k=kk,novelty_class=cls,n_candidates=len(q),ranking_scope='within_class',within_class_recovery=rec))
   for model in ['RF','ET']:
    for left,right in [('I','B'),('I','G'),('T','I'),('B','O')]:
     if (left,model) not in complete_keys or (right,model) not in complete_keys:continue
     a=pd.concat(repmodels[(left,model)],ignore_index=True);bb=pd.concat(repmodels[(right,model)],ignore_index=True)
     if len(a)!=N or len(bb)!=N:continue
     bb=bb.set_index('raw_row_id').loc[a.raw_row_id].reset_index();assert np.allclose(a.y_true,bb.y_true)
     delta=abs(a.prediction.to_numpy()-a.y_true.to_numpy())-abs(bb.prediction.to_numpy()-bb.y_true.to_numpy())
     for topo,ii in a.groupby('topology').groups.items():
      ix=np.asarray(list(ii),dtype=int);topopaired.append(dict(**base,protocol=protocol,model=model,contrast=left+'-'+right,topology=topo,n=len(ix),delta_MAE=float(delta[ix].mean()),delta_bias=float((a.prediction.to_numpy()[ix]-bb.prediction.to_numpy()[ix]).mean()),delta_R2=stats(a.y_true.to_numpy()[ix],a.prediction.to_numpy()[ix])['R2']-stats(bb.y_true.to_numpy()[ix],bb.prediction.to_numpy()[ix])['R2']))
     for cls in ['ALL']+CATS:
      mask=np.ones(N,bool) if cls=='ALL' else a.novelty_class.to_numpy()==cls;q=a.loc[mask];v=delta[mask];ci=(np.nan,np.nan)
      if int(size)==25000 and int(seed)==42 and protocol=='LOTO':ci=bootstrap_cluster(q,v)
      paired.append(dict(**base,protocol=protocol,model=model,contrast=left+'-'+right,novelty_class=cls,n=len(q),unique_coarse=q.coarse_key.nunique(),delta_MAE=float(v.mean()) if len(v) else np.nan,delta_R2=stats(a.y_true.to_numpy()[mask],a.prediction.to_numpy()[mask])['R2']-stats(bb.y_true.to_numpy()[mask],bb.prediction.to_numpy()[mask])['R2'],delta_MAE_cluster_CI95_low=ci[0],delta_MAE_cluster_CI95_high=ci[1]))
 tables={'chemical_similarity_error_metrics':chemistry,'C3_subtype_metrics':subtypes,'seen_unseen_error_metrics':seenrows,'per_topology_paired_differences':topopaired,'pooled_metrics':pooled,'fold_metrics':foldrows,'per_topology_metrics':toporows,'novelty_category_counts':noveltycounts,'novelty_error_metrics':categories,'novelty_distance_sensitivity':distance,'paired_representation_differences':paired,'novelty_ranking_contributions':ranking,'unknown_identity_audit':unknown,'fold_support_audit':foldaudit,'completion_audit':completeness,'role_and_key_sensitivity':role}
 tables={name:pd.DataFrame(rows) for name,rows in tables.items()}
 verification=validate_derived_tables(tables) if pooled else dict(status='no_complete_arms')
 for name,frame in tables.items():frame.to_csv(O/(name+'.csv'),index=False)
 (O/'derived_table_verification.json').write_text(json.dumps(verification,indent=2),encoding='utf-8')
 f=pd.DataFrame(pooled)
 if not f.empty:
  vals=['R2','MAE','RMSE','bias','macro_topology_R2','weighted_topology_R2','median_topology_R2'];s=f.groupby(['stage','target','protocol','representation','model'])[vals].agg(['mean','std','count']);s.columns=['_'.join(c) for c in s.columns];s.reset_index().to_csv(O/'representation_summary.csv',index=False)
 print('saved',len(pooled),'pooled results;',sum(x['complete'] for x in completeness),'complete arms of',len(completeness),flush=True)
if __name__=='__main__':main()
