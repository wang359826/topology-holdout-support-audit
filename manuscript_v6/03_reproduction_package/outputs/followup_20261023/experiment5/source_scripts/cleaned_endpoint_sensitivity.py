from pathlib import Path
import sys,json
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'_tools/pylibs312'));sys.path.insert(0,str(root/'03_投稿专用包/03_reproduction_package/scripts'))
import numpy as np,pandas as pd
from scipy.stats import t
from sklearn.ensemble import RandomForestRegressor
from diversity_control import load_and_build,NUMERIC_FEATURES
p=Path(__file__).resolve().parents[1];out=p/'outputs';X,y,top,ck,lp,metal=load_and_build(str(root/'03_投稿专用包/03_reproduction_package/data/all_MOFs_screening_data.csv'),42);xx=X.to_numpy(np.float32);yy=y.to_numpy();legal=(X[NUMERIC_FEATURES]>=0).all(axis=1).to_numpy();design=json.loads((out/'design.json').read_text());rows=[];audit=[]
for target,d in design.items():
 te=np.array(d['te']);bg=np.array(d['bg']);s=np.array(d['shared']);n=np.array(d['nonshared']);keep=legal[s]&legal[n];s=s[keep];n=n[keep];bg=bg[legal[bg]];te=te[legal[te]]
 audit.append(dict(target=target,n_test=len(te),n_background=len(bg),n_pairs=len(s),n_train=len(bg)+len(s)))
 for seed in [42,143,244,345,446]:
  order=np.random.default_rng(seed+5000).permutation(len(s))
  for dose,partner in [(0,n[order]),(1,s[order])]:
   train=np.r_[bg,partner];model=RandomForestRegressor(n_estimators=120,random_state=seed,n_jobs=4);model.fit(xx[train],yy[train]);pred=model.predict(xx[te]);rows.append(dict(target=target,seed=seed,dose=dose,n_train=len(train),n_test=len(te),MAE=float(abs(pred-yy[te]).mean())));print('clean endpoint',target,seed,dose,flush=True)
f=pd.DataFrame(rows);f.to_csv(out/'cleaned_endpoint_metrics.csv',index=False);summ=[]
for target,g in f.groupby('target'):
 v=g.pivot(index='seed',columns='dose',values='MAE');delta=v[1]-v[0];half=t.ppf(.975,4)*delta.std(ddof=1)/np.sqrt(5);summ.append(dict(target=target,MAE_0=float(v[0].mean()),MAE_100=float(v[1].mean()),delta=float(delta.mean()),CI95_low=float(delta.mean()-half),CI95_high=float(delta.mean()+half)))
pd.DataFrame(summ).to_csv(out/'cleaned_endpoint_summary.csv',index=False);pd.DataFrame(audit).to_csv(out/'cleaned_endpoint_counts.csv',index=False);print(pd.DataFrame(summ).to_string(index=False))
