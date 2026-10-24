from pathlib import Path
import sys,json,hashlib,importlib.util
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'_tools/pylibs312'))
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from scipy.stats import spearmanr
root=Path(__file__).resolve().parents[2]
p=Path(__file__).resolve().parents[1];out=p/'outputs';out.mkdir(exist_ok=True)
pkg=root/'03_投稿专用包_v6压缩/03_reproduction_package'
spec=importlib.util.spec_from_file_location('loto',pkg/'scripts/loto_full_metrics.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
raw_path=root/'03_投稿专用包/03_reproduction_package/data/all_MOFs_screening_data.csv'
raw=pd.read_csv(raw_path)
rows=[];sample_rows=[]
for size,seeds in [(100000,[42]),(25000,[42,143,244,345,446])]:
 metrics=pd.read_csv(pkg/f'outputs/loto_per_topology_metrics_{"100k" if size==100000 else "25k"}.csv')
 for seed in seeds:
  d=raw.sample(size,random_state=seed).copy()
  X,y,top=m.build_xy(raw,size,seed)
  # Exact archived valid-row rule: numeric features/target; categorical missing is stringified.
  mask=pd.to_numeric(d[m.TARGET],errors='coerce').notna() & d[m.NUMERIC].astype(float).notna().all(axis=1)
  d=d.loc[mask].copy();d['raw_row_index']=d.index;d=d.reset_index(drop=True)
  assert len(d)==len(y) and np.array_equal(d.topology.astype(str).to_numpy(),top.to_numpy())
  assert not d[['metal_linker','organic_linker1','organic_linker2']].isna().any().any(), 'Missing chemistry needs separate handling'
  for group in sorted(top.unique()):
   te=top.to_numpy()==group;tr=~te;a=d.loc[tr];b=d.loc[te]
   mm=metrics[(metrics.seed==seed)&(metrics.group==group)].iloc[0]
   assert int(mm.n_test)==te.sum() and int(mm.n_train)==tr.sum()
   coarse=set(map(tuple,a[['metal_linker','organic_linker1','organic_linker2']].to_numpy()))
   exact=np.array([tuple(v) not in coarse for v in b[['metal_linker','organic_linker1','organic_linker2']].to_numpy()])
   metals=set(a.metal_linker);links=set(a.organic_linker1)|set(a.organic_linker2)
   mn=~b.metal_linker.isin(metals).to_numpy();l1=~b.organic_linker1.isin(links).to_numpy();l2=~b.organic_linker2.isin(links).to_numpy();novel=mn|l1|l2
   # Keep ordered pair to match historical coarse key; also save unordered sensitivity.
   unordered=set((v[0],*sorted(v[1:])) for v in a[['metal_linker','organic_linker1','organic_linker2']].to_numpy())
   ux=np.array([(v[0],*sorted(v[1:])) not in unordered for v in b[['metal_linker','organic_linker1','organic_linker2']].to_numpy()])
   train=a[m.NUMERIC].to_numpy(float);test=b[m.NUMERIC].to_numpy(float)
   mean=train.mean(axis=0);scale=train.std(axis=0);scale[scale==0]=1
   z=(train-mean)/scale;zt=(test-mean)/scale;tree=cKDTree(z)
   dist=tree.query(zt,k=1,workers=1)[0]
   # Train-only calibration, deterministic reference sample; k=2 excludes self.
   rng=np.random.default_rng(seed);ix=rng.choice(len(z),min(5000,len(z)),replace=False)
   ref=tree.query(z[ix],k=2,workers=1)[0][:,1];threshold=float(np.quantile(ref,.95))
   far=dist>threshold
   r=dict(size=size,seed=seed,group=group,n_train=int(tr.sum()),n_test=int(te.sum()),MAE=float(mm.MAE),RMSE=float(mm.RMSE),R2=float(mm.R2),exact_mismatch=float(exact.mean()),unordered_mismatch=float(ux.mean()),unit_novelty=float(novel.mean()),metal_novelty=float(mn.mean()),linker_novelty=float((l1|l2).mean()),geometry_mean=float(dist.mean()),geometry_median=float(np.median(dist)),geometry_far_fraction=float(far.mean()),train_distance_q95=threshold,novel_and_far=float((novel&far).mean()),novel_only=float((novel&~far).mean()),geometry_only=float((~novel&far).mean()),neither=float((~novel&~far).mean()))
   rows.append(r)
   sample_rows.append(pd.DataFrame(dict(size=size,seed=seed,group=group,raw_row_index=b.raw_row_index.to_numpy(),exact_mismatch=exact,unit_novelty=novel,metal_novelty=mn,linker1_novelty=l1,linker2_novelty=l2,geometry_distance=dist,geometry_far=far)))
  print('completed',size,seed,flush=True)
f=pd.DataFrame(rows);f.to_csv(out/'fold_diagnostics.csv',index=False,encoding='utf-8-sig')
pd.concat(sample_rows,ignore_index=True).to_csv(out/'sample_diagnostics.csv.gz',index=False,compression='gzip')
cols=['exact_mismatch','unit_novelty','metal_novelty','linker_novelty','geometry_mean','geometry_far_fraction','novel_and_far']
corr=[]
for (size,seed),g in f.groupby(['size','seed']):
 for col in cols:
  rho=float(spearmanr(g[col],g.MAE).statistic) if g[col].nunique()>1 else None
  loo=[]
  for i in g.index:
   h=g.drop(i)
   if h[col].nunique()>1:loo.append(float(spearmanr(h[col],h.MAE).statistic))
  corr.append(dict(size=int(size),seed=int(seed),diagnostic=col,n_groups=len(g),rho_MAE=rho,leave_one_group_min=min(loo) if loo else None,leave_one_group_max=max(loo) if loo else None))
pd.DataFrame(corr).to_csv(out/'descriptive_correlations.csv',index=False,encoding='utf-8-sig')
g=f[f['size']==100000].copy()
# Outcome-blind diagnostic medians used only as descriptive cross-group cut points.
cut1=float(g.unit_novelty.median());cut2=float(g.geometry_far_fraction.median())
g['novelty_high']=g.unit_novelty>cut1;g['geometry_high']=g.geometry_far_fraction>cut2
strata=[]
for (n,h),v in g.groupby(['novelty_high','geometry_high']):
 strata.append(dict(novelty_high=bool(n),geometry_high=bool(h),n_groups=len(v),groups=';'.join(v.group),n_test=int(v.n_test.sum()),macro_MAE=float(v.MAE.mean()),weighted_MAE=float(np.average(v.MAE,weights=v.n_test)),min_MAE=float(v.MAE.min()),max_MAE=float(v.MAE.max())))
pd.DataFrame(strata).to_csv(out/'joint_group_strata.csv',index=False,encoding='utf-8-sig')
meta={'raw_sha256':hashlib.sha256(raw_path.read_bytes()).hexdigest(),'n_raw':len(raw),'folds':len(f),'independent_topology_groups':int(f.group.nunique()),'cut_novelty':cut1,'cut_geometry_far':cut2,'no_fitted_risk_model':True,'chem_similarity':'unavailable: no validated linker structure mapping','outcomes':'archived absolute fold MAE, not matched random-split performance loss; per-row LOTO predictions unavailable'}
(out/'analysis_metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
print(g[['group','MAE']+cols].to_string(index=False));print(pd.DataFrame(corr).query('size==100000').to_string(index=False));print(pd.DataFrame(strata).to_string(index=False))

