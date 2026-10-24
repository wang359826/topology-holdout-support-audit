from pathlib import Path
import os,sys,json,time,hashlib,argparse
os.environ.setdefault('OMP_NUM_THREADS','1');os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'_tools/pylibs312'));sys.path.insert(0,str(ROOT/'03_投稿专用包/03_reproduction_package/scripts'))
import numpy as np,pandas as pd
from scipy.spatial import cKDTree
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestRegressor,ExtraTreesRegressor
from sklearn.model_selection import KFold,GroupKFold,LeaveOneGroupOut
from diversity_control import NUMERIC_FEATURES,TARGET
P=Path(__file__).resolve().parents[1];OUT=P/'outputs';DATA=ROOT/'03_投稿专用包/03_reproduction_package/data/all_MOFs_screening_data.csv'
CONFIG=dict(sample_stages={'25000':[42,143,244,345,446],'100000':[42]},targets={'uptake':TARGET,'selectivity':'CO2/N2_selectivity'},representations={'G':[],'B':['metal_linker','functional_groups'],'I':['metal_linker','functional_groups','organic_linker1','organic_linker2'],'O':['metal_linker','functional_groups','topology']},models=['RF','ET'],protocols=['random','topology','LOTO'],n_estimators=120,n_jobs=12,max_features='sqrt',model_defaults='sklearn defaults except n_estimators, max_features=sqrt, random_state, n_jobs; runtime-only preflight amended before performance inspection',distance='train median/IQR Euclidean nearest; IQR=0 falls back train population SD then 1; train LOO q95 linear',threshold_sensitivity=[.90,.95,.99],role_policy='primary role-specific linker vocabularies and ordered keys; union and sorted-key sensitivity, because exchangeability unverified',sparse_category_rule='n<30 or unique ordered coarse<5; descriptive only',fingerprints='not available unless independently validated mapping acquired; never use ID distances',sampling='sample once then filter finite scalar/target and negative scalar values; no refill',screening='pooled OOF retrospective ranking, not single-model deployment',freeze_date='2026-10-22')
def atomic_json(path,obj):
 tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding='utf-8');tmp.replace(path)
def norm(v):
 if pd.isna(v):return '__MISSING__'
 try:
  x=float(v)
  if np.isfinite(x) and x.is_integer():return str(int(x))
 except (ValueError,TypeError):pass
 return str(v)
def tuples(d,cols):return list(d[cols].itertuples(index=False,name=None))
def safe_seen(vals,refs):return np.array([x in refs for x in vals],dtype=bool)
def diagnostics(d,num,tr,te):
 a=d.iloc[tr];b=d.iloc[te];metal=set(a.metal_linker);l1=set(a.organic_linker1);l2=set(a.organic_linker2);union=l1|l2;pair=set(tuples(a,['organic_linker1','organic_linker2']));coarse=set(tuples(a,['metal_linker','organic_linker1','organic_linker2']));fine=set(tuples(a,['metal_linker','organic_linker1','organic_linker2','functional_groups']))
 z=pd.DataFrame({'raw_row_id':b.raw_row_id.to_numpy(),'topology':b.topology.to_numpy()});z['metal_seen']=b.metal_linker.isin(metal).to_numpy();z['linker1_seen']=b.organic_linker1.isin(l1).to_numpy();z['linker2_seen']=b.organic_linker2.isin(l2).to_numpy();z['linker1_union_seen']=b.organic_linker1.isin(union).to_numpy();z['linker2_union_seen']=b.organic_linker2.isin(union).to_numpy();z['n_unseen_linkers']=(~z.linker1_seen).astype(int)+(~z.linker2_seen).astype(int)
 z['n_unique_unseen_linkers']=[len({v for v,seen in zip([x,y],[u,vv]) if not seen}) for x,y,u,vv in zip(b.organic_linker1,b.organic_linker2,z.linker1_seen,z.linker2_seen)]
 z['pair_seen']=safe_seen(tuples(b,['organic_linker1','organic_linker2']),pair);z['coarse_seen']=safe_seen(tuples(b,['metal_linker','organic_linker1','organic_linker2']),coarse);z['fine_seen']=safe_seen(tuples(b,['metal_linker','organic_linker1','organic_linker2','functional_groups']),fine);z['functional_group_seen']=b.functional_groups.isin(set(a.functional_groups)).to_numpy()
 known=~b[['metal_linker','organic_linker1','organic_linker2']].eq('__MISSING__').any(axis=1).to_numpy()
 z['identity_status']=np.where(known,'known','missing_identity');z['novelty_class']=np.select([~known,z.coarse_seen,z.metal_seen&z.pair_seen,z.metal_seen&z.linker1_seen&z.linker2_seen],['CU','C0','C1','C2'],default='C3')
 assert not (z.coarse_seen&~z.pair_seen).any();assert not (z.pair_seen&~(z.linker1_seen&z.linker2_seen)).any()
 assert ((z.novelty_class=='C3')<=((~z.metal_seen)|(z.n_unseen_linkers>0))).all()
 z['coarse_key']=[json.dumps(v,separators=(',',':')) for v in tuples(b,['metal_linker','organic_linker1','organic_linker2'])]
 upair={tuple(sorted(x)) for x in pair};ucoarse={(m,*sorted([x,y])) for m,x,y in coarse};z['pair_unordered_seen']=[tuple(sorted([x,y])) in upair for x,y in zip(b.organic_linker1,b.organic_linker2)];z['coarse_unordered_seen']=[(m,*sorted([x,y])) in ucoarse for m,x,y in tuples(b,['metal_linker','organic_linker1','organic_linker2'])]
 x=num[tr];med=np.median(x,axis=0);iqr=np.quantile(x,.75,axis=0)-np.quantile(x,.25,axis=0);sd=x.std(axis=0);scale=np.where(iqr>0,iqr,np.where(sd>0,sd,1));tx=(x-med)/scale;tt=(num[te]-med)/scale;tree=cKDTree(tx);loo=tree.query(tx,k=2,workers=4)[0][:,1];near=tree.query(tt,k=5,workers=4)[0];z['scalar_support_distance']=near[:,0];z['scalar_k5_mean']=near.mean(axis=1)
 qs=np.quantile(loo,[.9,.95,.99],method='linear');z['scalar_distance_threshold']=qs[1];z['scalar_outside']=near[:,0]>qs[1]
 for q,cut in zip([90,95,99],qs):z[f'scalar_outside_q{q}']=near[:,0]>cut
 unique=np.unique(tx,axis=0);ut=cKDTree(unique);ulo=ut.query(unique,k=2,workers=4)[0][:,1];uq=np.quantile(ulo,.95,method='linear');z['scalar_unique_threshold']=uq;z['scalar_unique_outside']=near[:,0]>uq
 k5cut=np.quantile(tree.query(tx,k=6,workers=4)[0][:,1:].mean(axis=1),.95,method='linear');z['scalar_k5_outside']=near.mean(axis=1)>k5cut
 ix=[3,5,6,7];pt=cKDTree(tx[:,ix]);pq=np.quantile(pt.query(tx[:,ix],k=2,workers=4)[0][:,1],.95,method='linear');z['pore_support_distance']=pt.query(tt[:,ix],k=1,workers=4)[0];z['pore_outside']=z.pore_support_distance>pq
 z['constant_column_exceeded']=np.any((sd==0)&(num[te]!=med),axis=1);z['mapping_status']='no_validated_linker_structure_mapping';z['distance_status']='ok'
 for col in ['linker1_smax','linker2_smax','linker_smin','linker_smean']:z[col]=np.nan
 meta=dict(n_train=len(tr),n_test=len(te),n_metal=len(metal),n_linker_role1=len(l1),n_linker_role2=len(l2),n_linker_union=len(union),n_pair=len(pair),n_coarse=len(coarse),train_scalar_duplicate_fraction=1-len(unique)/len(tr),train_zero_LOO_fraction=float((loo==0).mean()),median=med.tolist(),scale=scale.tolist(),iqr_zero_columns=[NUMERIC_FEATURES[i] for i in np.flatnonzero(iqr==0)],constant_columns=[NUMERIC_FEATURES[i] for i in np.flatnonzero(sd==0)],threshold_q90_q95_q99=qs.tolist(),unique_q95=float(uq),k5_q95=float(k5cut),pore_q95=float(pq))
 return z,meta

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['all','25000','100000'],default='all');parser.add_argument('--seed',type=int);args=parser.parse_args()
 if (OUT/'frozen_config.json').exists():assert json.loads((OUT/'frozen_config.json').read_text(encoding='utf-8'))==CONFIG
 else:atomic_json(OUT/'frozen_config.json',CONFIG)
 raw=pd.read_csv(DATA);source_hash=hashlib.sha256(DATA.read_bytes()).hexdigest();atomic_json(OUT/'source.json',dict(path=str(DATA),sha256=source_hash,rows=len(raw)))
 for size,seeds in CONFIG['sample_stages'].items():
  if args.stage!='all' and args.stage!=size:continue
  for seed in seeds:
   if args.seed is not None and seed!=args.seed:continue
   sample=raw.sample(int(size),random_state=seed).copy();sample['raw_row_id']=sample.index
   scalar=sample[NUMERIC_FEATURES].to_numpy(float);scalar_ok=np.isfinite(scalar).all(1)&(scalar>=0).all(1)
   for target,col in CONFIG['targets'].items():
    yy=pd.to_numeric(sample[col],errors='coerce').to_numpy();ok=scalar_ok&np.isfinite(yy)&((yy>0) if target=='selectivity' else True)
    d=sample.loc[ok].reset_index(drop=True).copy();y=np.log10(yy[ok]) if target=='selectivity' else yy[ok];num=d[NUMERIC_FEATURES].to_numpy(np.float32)
    for c in ['metal_linker','organic_linker1','organic_linker2','functional_groups','topology']:d[c]=d[c].map(norm)
    folder=OUT/f'n{size}_seed{seed}_{target}';folder.mkdir(exist_ok=True)
    d[['raw_row_id','MOFname','topology','metal_linker','organic_linker1','organic_linker2','functional_groups']].assign(y_true=y).to_csv(folder/'sample.csv.gz',index=False)
    atomic_json(folder/'data_audit.json',dict(sample_requested=int(size),n_valid=len(d),invalid_scalar=int((~scalar_ok).sum()),invalid_target=int((~np.isfinite(yy)).sum()),nonpositive_target=int((yy<=0).sum()) if target=='selectivity' else None,missing_fields={c:int((d[c]=='__MISSING__').sum()) for c in ['metal_linker','organic_linker1','organic_linker2','functional_groups']},target=col,log10=target=='selectivity'))
    for protocol in CONFIG['protocols']:
     splitter=KFold(5,shuffle=True,random_state=seed) if protocol=='random' else GroupKFold(5) if protocol=='topology' else LeaveOneGroupOut();splits=list(splitter.split(num,y,groups=d.topology))
     for fold,(tr,te) in enumerate(splits):
      fp=folder/f'{protocol}_fold{fold}';fp.mkdir(exist_ok=True)
      if not (fp/'split.npz').exists():np.savez_compressed(fp/'split.npz',train_raw_id=d.raw_row_id.to_numpy()[tr],test_raw_id=d.raw_row_id.to_numpy()[te],train_index=tr,test_index=te)
      else:
       saved=np.load(fp/'split.npz');assert np.array_equal(saved['test_raw_id'],d.raw_row_id.to_numpy()[te]);assert np.array_equal(saved['train_raw_id'],d.raw_row_id.to_numpy()[tr])
      assert not np.intersect1d(tr,te).size
      if protocol!='random':assert set(d.topology.iloc[tr]).isdisjoint(set(d.topology.iloc[te]))
      if not (fp/'novelty.csv.gz').exists():
       z,meta=diagnostics(d,num,tr,te);z['y_true']=y[te];z.to_csv(fp/'novelty.csv.gz',index=False);atomic_json(fp/'distance_and_support.json',meta)
      for rep,cats in CONFIG['representations'].items():
       needed=[m for m in CONFIG['models'] if not (fp/f'prediction_{rep}_{m}.npz').exists()]
       if not needed:continue
       a=num[tr];b=num[te];encmeta={}
       if cats:
        enc=OneHotEncoder(handle_unknown='ignore',sparse_output=False,dtype=np.float32);at=enc.fit_transform(d.iloc[tr][cats]);bt=enc.transform(d.iloc[te][cats]);a=np.c_[a,at];b=np.c_[b,bt]
        encmeta={c:dict(vocabulary=v.tolist(),unknown_test_fraction=float((~d.iloc[te][c].isin(v)).mean())) for c,v in zip(cats,enc.categories_)}
       atomic_json(fp/f'encoding_{rep}.json',dict(n_features=a.shape[1],fields=encmeta))
       for modelname in needed:
        start=time.monotonic();cls=RandomForestRegressor if modelname=='RF' else ExtraTreesRegressor;model=cls(n_estimators=CONFIG['n_estimators'],max_features=CONFIG['max_features'],random_state=seed,n_jobs=CONFIG['n_jobs']);model.fit(a,y[tr]);pred=model.predict(b)
        tmp=fp/f'prediction_{rep}_{modelname}.tmp.npz';np.savez_compressed(tmp,raw_row_id=d.raw_row_id.to_numpy()[te],y_true=y[te],prediction=pred);tmp.replace(fp/f'prediction_{rep}_{modelname}.npz')
        atomic_json(fp/f'model_{rep}_{modelname}.json',dict(parameters=model.get_params(),elapsed_seconds=time.monotonic()-start))
        print(size,seed,target,protocol,fold,rep,modelname,'n',len(tr),len(te),'sec',round(time.monotonic()-start,1),flush=True)
        del model
 print('ALL REQUESTED EXPERIMENTS FINISHED',flush=True)
if __name__=='__main__':main()
