from pathlib import Path
import sys,json,hashlib
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'_tools/pylibs312'))
sys.path.insert(0,str(root/'03_投稿专用包/03_reproduction_package/scripts'))
import numpy as np,pandas as pd
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestRegressor,ExtraTreesRegressor
from diversity_control import NUMERIC_FEATURES,TARGET
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=Path(__file__).resolve().parents[1];out=p/'outputs'
config=dict(design='retrospective cleaned experiment5 endpoints',representations={'G':[],'B':['metal_linker','functional_groups'],'I':['metal_linker','functional_groups','organic_linker1','organic_linker2']},seeds=[42,143,244,345,446],models=['RF','ET'],trees=120,budget_fractions=[.01,.05,.1,.2],support=[0,1],selection='all prespecified arms reported; no candidate-label tuning',transferable_chemistry='unavailable: no validated structure mapping')
(out/'frozen_config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
df=pd.read_csv(root/'03_投稿专用包/03_reproduction_package/data/all_MOFs_screening_data.csv')
raw=np.load(root/'实验5_伙伴组成替换/outputs/sample_to_raw_index.npy');df=df.iloc[raw].reset_index(drop=True)
num=df[NUMERIC_FEATURES].to_numpy(float);y=df[TARGET].to_numpy(float);legal=np.isfinite(num).all(1)&(num>=0).all(1)&np.isfinite(y)
design=json.loads((root/'实验5_伙伴组成替换/outputs/design.json').read_text())
metrics=[];audits=[];unknown=[];members=[];selected=[]
for target,d in design.items():
 te=np.array(d['te']);te=te[legal[te]];bg=np.array(d['bg']);bg=bg[legal[bg]];s=np.array(d['shared']);n=np.array(d['nonshared']);keep=legal[s]&legal[n];s=s[keep];n=n[keep]
 yt=y[te];ids=raw[te];N=len(te);poolhash=hashlib.sha256(ids.astype('<i8').tobytes()).hexdigest();oracle=np.lexsort((ids,-yt));base=yt.mean()
 pd.DataFrame({'raw_row_id':ids,'y_true':yt}).to_csv(out/f'candidates_{target}.csv',index=False)
 for dose,partner in [(0,n),(1,s)]:
  tr=np.r_[bg,partner];assert not np.intersect1d(tr,te).size;assert not (df.iloc[tr].topology.astype(str)==target).any()
  for row in tr:members.append(dict(target=target,support=dose,raw_row_id=int(raw[row])))
  for rep,cats in config['representations'].items():
   a=num[tr];b=num[te]
   if cats:
    cat=df[cats].fillna('__MISSING__').astype(str);enc=OneHotEncoder(handle_unknown='ignore',sparse_output=False,dtype=np.float32);at=enc.fit_transform(cat.iloc[tr]);bt=enc.transform(cat.iloc[te]);a=np.c_[a,at];b=np.c_[b,bt]
    for j,c in enumerate(cats):unknown.append(dict(target=target,support=dose,representation=rep,feature=c,unknown_fraction=float((~cat.iloc[te][c].isin(enc.categories_[j])).mean())))
    (out/f'vocabulary_{target}_{dose}_{rep}.json').write_text(json.dumps({c:v.tolist() for c,v in zip(cats,enc.categories_)},indent=2),encoding='utf-8')
   audits.append(dict(target=target,support=dose,representation=rep,n_train=len(tr),n_candidates=N,n_features=a.shape[1],candidate_sha256=poolhash))
   for modelname in config['models']:
    cls=RandomForestRegressor if modelname=='RF' else ExtraTreesRegressor
    for seed in config['seeds']:
     model=cls(n_estimators=120,random_state=seed,n_jobs=4);model.fit(a,y[tr]);pred=model.predict(b);rank=np.lexsort((ids,-pred))
     np.savez_compressed(out/f'scores_{target}_{dose}_{rep}_{modelname}_{seed}.npz',raw_row_id=ids,y_true=yt,prediction=pred)
     for frac in config['budget_fractions']:
      k=int(np.ceil(N*frac));pick=rank[:k];best=oracle[:k];recovery=len(np.intersect1d(pick,best))/k;mean=yt[pick].mean();optimal=yt[best].mean();regret=optimal-mean
      assert regret>=-1e-10
      random_sd=yt.std(ddof=1)/np.sqrt(k)*np.sqrt((N-k)/N)
      metrics.append(dict(target=target,support=dose,representation=rep,model=modelname,seed=seed,budget_fraction=frac,k=k,n_candidates=N,recovery=recovery,selected_mean=mean,oracle_mean=optimal,regret=regret,random_mean=base,random_recovery=k/N,lift=mean/base,gain=mean-base,recovery_enrichment=recovery/(k/N),random_selection_mean_sd=random_sd,MAE=np.abs(pred-yt).mean()))
      for position,j in enumerate(pick):selected.append(dict(target=target,support=dose,representation=rep,model=modelname,seed=seed,budget_fraction=frac,rank=position+1,raw_row_id=int(ids[j])))
     print(target,dose,rep,modelname,seed,flush=True)
f=pd.DataFrame(metrics);f.to_csv(out/'screening_metrics.csv',index=False)
pd.DataFrame(audits).to_csv(out/'pool_audit.csv',index=False);pd.DataFrame(unknown).to_csv(out/'unknown_category_audit.csv',index=False);pd.DataFrame(members).to_csv(out/'training_membership.csv.gz',index=False);pd.DataFrame(selected).to_csv(out/'selected_materials.csv.gz',index=False)
keys=['target','support','representation','model','budget_fraction','k'];values=['recovery','selected_mean','oracle_mean','regret','random_mean','lift','gain','MAE']
summary=f.groupby(keys)[values].agg(['mean','std']).reset_index();summary.columns=['_'.join(c).rstrip('_') if isinstance(c,tuple) else c for c in summary.columns];summary.to_csv(out/'screening_summary.csv',index=False)
# Independent recomputation of selected means, overlap and pool identity from saved scores.
for row in metrics:
 z=np.load(out/f"scores_{row['target']}_{row['support']}_{row['representation']}_{row['model']}_{row['seed']}.npz");ix=np.lexsort((z['raw_row_id'],-z['prediction']))[:row['k']];assert np.isclose(z['y_true'][ix].mean(),row['selected_mean'])
assert pd.DataFrame(audits).groupby('target').candidate_sha256.nunique().eq(1).all()
fig,axes=plt.subplots(2,2,figsize=(10,7))
colors={'G':'#4477aa','B':'#ee7733','I':'#228833'}
for i,target in enumerate(design):
 for (dose,rep),g in summary[(summary.target==target)&(summary.model=='RF')].groupby(['support','representation']):
  for j,metric in enumerate(['recovery','regret']):axes[i,j].errorbar(g.budget_fraction*100,g[metric+'_mean'],yerr=g[metric+'_std'],label=f'{rep}, shared {dose*100}%',color=colors[rep],linestyle='-' if dose else '--',capsize=2)
 axes[i,0].plot([1,5,10,20],[.01,.05,.1,.2],':',color='gray',label='Random expectation')
 for j in range(2):axes[i,j].set_title(target);axes[i,j].set_xlabel('Candidate budget (%)');axes[i,j].set_ylabel('Top-k recovery' if j==0 else 'Regret (mmol/g)')
axes[0,0].legend(fontsize=7,ncol=2);fig.tight_layout();fig.savefig(out/'fixed_pool_screening.png',dpi=200);fig.savefig(out/'fixed_pool_screening.pdf');plt.close(fig)
lines=['# 固定候选池单模型筛选实验','', '## 设计与边界','本实验是回顾性部署模拟，复用实验5已评价过的固定候选池，并非从未接触的确认性测试。所有配置在本轮评分前写入 frozen_config.json；不依据候选标签选择表示、调参或校准，也不宣布胜出方案可泛化。每一方法、每一随机种子均用一个模型统一预测同一候选池，未汇总折外预测。','', 'G：八项结构数值描述符（含质量及质量归一化量，不能全称纯几何）；B：G+金属/官能团身份；I：B+两个linker身份。身份采用仅训练集拟合的独热编码，未见类别全零；保留原始linker槽位，未验证交换对称性。拓扑不输入模型。缺失官能团显式编码。可迁移指纹/RAC因缺少可靠ID到结构映射，仍未完成。','', '训练支持0/100%指伙伴子集的共享组成比例，不是全部训练集的覆盖率。背景、训练规模及伙伴比例固定，成对删除负数描述符行；几何匹配为近似匹配，官能团等残余差异仍在，不能视为纯化学因果效应。','', '随机森林与ExtraTrees各120棵树；5个种子仅改变模型随机性，固定训练和候选行。预算为候选池1%、5%、10%、20%，向上取整。同分按原CSV行号排序。','', '## 结果（5种子均值）','单位：吸附量和regret均为 mmol/g。±仅表示模型随机性标准差，不代表独立数据库或材料总体的不确定性。','']
for target in design:
 a=pd.DataFrame(audits);v=a[a.target==target].iloc[0];lines += [f"### {target}: 候选 {v.n_candidates}，训练 {v.n_train}", '|模型|支持|表示|预算/k|recovery|所选真实均值|regret|随机提升倍数|','|---|---|---|---|---|---|---|---|']
 for _,r in summary[summary.target==target].iterrows():lines.append(f"|{r.model}|{int(r.support)*100}%|{r.representation}|{r.budget_fraction:.0%}/{int(r.k)}|{r.recovery_mean:.3f}±{r.recovery_std:.3f}|{r.selected_mean_mean:.3f}|{r.regret_mean:.3f}|{r.lift_mean:.2f}|")
 lines += ['']
lines += ['## 指标与核验','Recovery=所选与真实top-k交集/k；regret=真实oracle top-k均值−所选真实均值；lift=所选均值/全候选池均值。随机选择的期望真实均值等于全池均值，期望recovery=k/N。详细表另含绝对提升、oracle均值及有限总体随机抽样均值标准差；这不是模型置信区间。','所有方法的候选ID哈希按拓扑一致；训练与候选无行重叠，训练拓扑均不含目标拓扑。保存全部分数、原始行号、训练成员、每预算所选材料、训练类别词表和未见类别比例。已从保存分数重新计算所选真实均值并检查regret非负。','', '## 可写入论文的范围','可作为局部hMOF家族对的部署模拟与表示敏感性证据；不构成独立外部验证，不完成可迁移化学表示对照，也不能据此证明某诊断具有普适预警能力。报告所有预定方案，避免以测试结果挑选最佳方案后当作已验证部署模型。','', '![筛选响应](outputs/fixed_pool_screening.png)']
(p/'实验报告_固定候选池筛选.md').write_text('\n'.join(lines),encoding='utf-8')
print(summary[(summary.budget_fraction==.05)&(summary.model=='RF')].to_string(index=False));print('ALL CHECKS PASSED',flush=True)
