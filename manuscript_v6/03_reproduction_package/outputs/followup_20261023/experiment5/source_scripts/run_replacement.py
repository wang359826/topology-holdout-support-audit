from pathlib import Path
import sys,json,time
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'_tools/pylibs312'));sys.path.insert(0,str(root/'03_投稿专用包/03_reproduction_package/scripts'))
import numpy as np,pandas as pd
from scipy.stats import spearmanr,t
from scipy.spatial import cKDTree
from sklearn.ensemble import RandomForestRegressor
from diversity_control import load_and_build,NUMERIC_FEATURES
p=Path(__file__).resolve().parents[1];out=p/'outputs';design=json.loads((out/'design.json').read_text());X,y,top,ck,lp,metal=load_and_build(str(root/'03_投稿专用包/03_reproduction_package/data/all_MOFs_screening_data.csv'),42)
xx=X.to_numpy(np.float32);yy=y.to_numpy();cv=ck.to_numpy();geom=X[NUMERIC_FEATURES].to_numpy();rows=[];balance=[];training=[]
for target,des in design.items():
 te=np.array(des['te']);bg=np.array(des['bg']);ss=np.array(des['shared']);nn=np.array(des['nonshared']);sd=np.array(des['training_sd']);M=len(ss)
 # Outcome-blind geometric support flag for a secondary fixed test subset.
 pool=np.concatenate([ss,nn]);tree=cKDTree(geom[pool]/sd);supported=tree.query(geom[te]/sd,k=1)[0]<=.5
 for repeat,seed in enumerate([42,143,244,345,446]):
  rng=np.random.default_rng(seed+5000);order=rng.permutation(M);s=ss[order];n=nn[order];ref=np.r_[bg,n];predictions=[]
  for dose in [0,.25,.5,.75,1]:
   k=int(round(dose*M));partner=np.r_[s[:k],n[k:]];train=np.r_[bg,partner]
   assert len(train)==len(ref) and len(np.unique(train))==len(train) and not np.intersect1d(train,te).size
   start=time.monotonic();model=RandomForestRegressor(n_estimators=120,random_state=seed,n_jobs=4);model.fit(xx[train],yy[train]);pred=model.predict(xx[te]);predictions.append(pred)
   support=np.isin(cv[te],cv[train]);diff=(geom[train].mean(0)-geom[ref].mean(0))/sd;partnerdiff=(geom[partner].mean(0)-geom[n].mean(0))/sd
   for j,name in enumerate(NUMERIC_FEATURES):balance.append(dict(target=target,seed=seed,dose=dose,feature=name,full_mean_shift_training_SD=float(diff[j]),partner_mean_shift_training_SD=float(partnerdiff[j]),partner_std=float(geom[partner,j].std()),reference_partner_std=float(geom[n,j].std())))
   for subset,mask in [('all',np.ones(len(te),bool)),('matched_geometry',supported)]:
    yt=yy[te][mask];pr=pred[mask];err=pr-yt
    rows.append(dict(target=target,seed=seed,dose=dose,actual_partner_shared_fraction=k/M,n_shared=k,n_partner=M,n_train=len(train),partner_fraction=M/len(train),subset=subset,n_test=int(mask.sum()),test_row_composition_coverage=float(support[mask].mean()),test_unique_composition_coverage=len(set(cv[te][mask])&set(cv[train]))/len(set(cv[te][mask])),MAE=float(np.abs(err).mean()),bias=float(err.mean()),RMSE=float(np.sqrt(np.mean(err**2))),rank_spearman=float(spearmanr(yt,pr).statistic),max_abs_full_mean_shift=float(abs(diff).max()),max_abs_partner_mean_shift=float(abs(partnerdiff).max()),seconds=time.monotonic()-start))
   training.extend(dict(target=target,seed=seed,dose=dose,row_index=int(i),role='background' if j<len(bg) else 'partner') for j,i in enumerate(train))
   pd.DataFrame(rows).to_csv(out/'curve_metrics.csv',index=False,encoding='utf-8-sig')
   print(target,seed,dose,'MAE',rows[-2]['MAE'],'seconds',round(time.monotonic()-start,1),flush=True)
  np.savez_compressed(out/f'predictions_{target}_{seed}.npz',test_row_index=te,y_true=yy[te],predictions=np.array(predictions),doses=np.array([0,.25,.5,.75,1]),matched_geometry=supported)
pd.DataFrame(balance).to_csv(out/'balance_all_doses.csv',index=False,encoding='utf-8-sig');pd.DataFrame(training).to_csv(out/'training_membership.csv.gz',index=False,compression='gzip')
f=pd.DataFrame(rows);summary=[];endpoints=[]
for key,g in f.groupby(['target','subset','dose']):
 vals=g.MAE.to_numpy();half=t.ppf(.975,4)*vals.std(ddof=1)/np.sqrt(5)
 summary.append(dict(target=key[0],subset=key[1],dose=key[2],n_test=int(g.n_test.iloc[0]),MAE_mean=float(vals.mean()),MAE_CI95_low=float(vals.mean()-half),MAE_CI95_high=float(vals.mean()+half),coverage_mean=float(g.test_row_composition_coverage.mean()),bias_mean=float(g.bias.mean()),rank_mean=float(g.rank_spearman.mean())))
for (target,subset),g in f.groupby(['target','subset']):
 v=g.pivot(index='seed',columns='dose',values='MAE');delta=(v[1]-v[0]).to_numpy();half=t.ppf(.975,4)*delta.std(ddof=1)/np.sqrt(5)
 endpoints.append(dict(target=target,subset=subset,n_repeats=5,MAE_100_minus_0=float(delta.mean()),CI95_low=float(delta.mean()-half),CI95_high=float(delta.mean()+half)))
pd.DataFrame(summary).to_csv(out/'curve_summary.csv',index=False);pd.DataFrame(endpoints).to_csv(out/'paired_endpoints.csv',index=False)
print(pd.DataFrame(endpoints).to_string(index=False),flush=True)
