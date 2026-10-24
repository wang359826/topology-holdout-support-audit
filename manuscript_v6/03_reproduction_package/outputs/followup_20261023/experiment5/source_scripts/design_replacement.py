from pathlib import Path
import sys,json
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'_tools/pylibs312'))
import numpy as np,pandas as pd
from scipy.spatial import cKDTree
from scipy.stats import t
p=Path(__file__).resolve().parents[1];out=p/'outputs';out.mkdir(exist_ok=True)
src=root/'03_投稿专用包/03_reproduction_package/scripts';sys.path.insert(0,str(src))
from diversity_control import load_and_build,NUMERIC_FEATURES
csv=root/'03_投稿专用包/03_reproduction_package/data/all_MOFs_screening_data.csv'
X,y,top,ck,lp,metal=load_and_build(str(csv),42);tv=top.to_numpy();cv=ck.to_numpy();audit=[];design={};matches=[]
for target,partner in [('nbo','pcu'),('pcu','nbo')]:
 te=np.flatnonzero(tv==target);pool=np.flatnonzero(tv==partner);shared=pool[np.isin(cv[pool],cv[te])];non=pool[~np.isin(cv[pool],cv[te])]
 train=np.flatnonzero(tv!=target);geom=X[NUMERIC_FEATURES].to_numpy();mu=geom[train].mean(0);sd=geom[train].std(0);sd[sd==0]=1;z=(geom-mu)/sd
 # Outcome-blind greedy no-replacement matching, max standardized Euclidean distance .5.
 tree=cKDTree(z[non]);dd,ii=tree.query(z[shared],k=min(20,len(non)));edges=[]
 if dd.ndim==1:dd=dd[:,None];ii=ii[:,None]
 for j in range(len(shared)):
  for dist,k in zip(dd[j],ii[j]):
   if dist<=.5:edges.append((float(dist),int(shared[j]),int(non[k])))
 edges.sort();useds=set();usedn=set();pairs=[]
 for dist,s,n in edges:
  if s not in useds and n not in usedn:pairs.append((s,n,dist));useds.add(s);usedn.add(n)
 rng=np.random.default_rng(42);rng.shuffle(pairs);pairs=pairs[:min(1000,len(pairs))]
 if not pairs:raise RuntimeError('No matched common support')
 ss=np.array([v[0] for v in pairs]);nn=np.array([v[1] for v in pairs]);smd=np.abs((geom[ss].mean(0)-geom[nn].mean(0))/sd)
 bgpool=np.flatnonzero((tv!=target)&(tv!=partner));bg=rng.choice(bgpool,min(4000,len(bgpool)),replace=False)
 audit.append(dict(target=target,partner=partner,n_test=len(te),shared_candidates=len(shared),nonshared_candidates=len(non),caliper=.5,n_feasible_pairs=len(useds),n_selected_pairs=len(pairs),n_background=len(bg),n_train=len(bg)+len(pairs),partner_fraction=len(pairs)/(len(bg)+len(pairs)),max_abs_mean_difference_training_SD=float(smd.max()),pair_distance_mean=float(np.mean([v[2] for v in pairs])),pair_distance_max=float(max(v[2] for v in pairs))))
 for j,(s,n,dist) in enumerate(pairs):matches.append(dict(target=target,pair=j,shared_row_index=s,nonshared_row_index=n,distance=dist))
 design[target]=dict(te=te.tolist(),bg=bg.tolist(),shared=ss.tolist(),nonshared=nn.tolist(),training_sd=sd.tolist())
 # Save every feature, including remaining variance discrepancies.
 pd.DataFrame(dict(feature=NUMERIC_FEATURES,shared_mean=geom[ss].mean(0),nonshared_mean=geom[nn].mean(0),abs_mean_diff_training_SD=smd,shared_std=geom[ss].std(0),nonshared_std=geom[nn].std(0))).to_csv(out/f'matching_features_{target}.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(audit).to_csv(out/'feasibility_matching.csv',index=False,encoding='utf-8-sig');pd.DataFrame(matches).to_csv(out/'matched_pairs.csv',index=False);(out/'design.json').write_text(json.dumps(design),encoding='utf-8')
# Paired intervals over archived five sampling seeds, not independent test rows.
old=root/'03_投稿专用包_v6压缩/03_reproduction_package/outputs';e=pd.read_csv(old/'arm_e_partner_coverage.csv');g=pd.read_csv(old/'partner_random_g.csv');records=[];diffs=[]
for target in ['nbo','pcu']:
 ee=e[(e.test_topo==target)&(e.regime=='e_shared_only_removed')];gg=g[g.test_topo==target];a=e[(e.test_topo==target)&(e.regime=='a_with_partner')]
 v=ee[['seed','MAE']].merge(gg[['seed','MAE']],on='seed',suffixes=('_e','_g'));v['e_minus_g']=v.MAE_e-v.MAE_g;v['target']=target;diffs.append(v)
 delta=v.e_minus_g.to_numpy();half=t.ppf(.975,len(delta)-1)*delta.std(ddof=1)/np.sqrt(len(delta))
 records.append(dict(target=target,n_seeds=len(delta),MAE_a=float(a.MAE.mean()),MAE_e=float(ee.MAE.mean()),MAE_g=float(gg.MAE.mean()),e_minus_g=float(delta.mean()),CI95_low=float(delta.mean()-half),CI95_high=float(delta.mean()+half),method='paired seed differences; t interval df=4; overlapping samples, not external CI'))
pd.DataFrame(records).to_csv(out/'main_a_e_g_paired.csv',index=False);pd.concat(diffs).to_csv(out/'e_g_seed_differences.csv',index=False)
print(pd.DataFrame(audit).to_string(index=False));print(pd.DataFrame(records).to_string(index=False))
