from pathlib import Path
import sys,os,json,time,argparse
os.environ.setdefault('OMP_NUM_THREADS','1');os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
from run_experiments import ROOT,P,OUT,DATA,CONFIG,norm,atomic_json,NUMERIC_FEATURES,diagnostics
import numpy as np,pandas as pd
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestRegressor,ExtraTreesRegressor

def run():
 parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['all','25000','100000'],default='all');args=parser.parse_args()
 mapping=json.loads((P/'sources/validated_linker_mapping.json').read_text());bits=np.load(P/'sources/morgan_parent_fingerprints.npz');sim=np.load(P/'sources/parent_tanimoto_matrix.npz');ids=bits['linker_id'].tolist();lookup={v:i for i,v in enumerate(ids)};smiles=[mapping[v]['smiles'] for v in ids];bm=bits['bits'];sm=sim['similarity']
 raw=pd.read_csv(DATA);observed={norm(v) for c in ['organic_linker1','organic_linker2'] for v in raw[c].unique()}
 # Strict graph-consistent subset; never infer unresolved IDs from neighbors or numbering.
 commonroot=P/'outputs_mapped_common';commonroot.mkdir(exist_ok=True)
 cfg=dict(representation='T',definition='G plus train-onehot metal/functional_groups plus role-specific concatenated Morgan parent-linker bits',fingerprint=dict(radius=2,n_bits_per_linker=2048,chirality=False),feature_filter='training-only remove constant fingerprint bits, including all-one bits; numerical and onehot unchanged',models=CONFIG['models'],n_estimators=120,max_features='sqrt',n_jobs=6,mapping_sha256=__import__('hashlib').sha256((P/'sources/validated_linker_mapping.json').read_bytes()).hexdigest(),decision='Morgan config fixed before inspecting predictive results; strict 33-ID subset selected solely by graph consistency; common G/B/I/O refitted; no outer-test tuning',limitation='fingerprints represent unfunctionalized parent chemistry; missing FG remains explicit; feature dimension changes tree feature-sampling opportunities')
 cp=commonroot/'frozen_T_config.json'
 if cp.exists():assert json.loads(cp.read_text())==cfg
 else:atomic_json(cp,cfg)
 for size,seeds in CONFIG['sample_stages'].items():
  if args.stage!='all' and args.stage!=size:continue
  for seed in seeds:
   for target in CONFIG['targets']:
    folder=OUT/f'n{size}_seed{seed}_{target}'
    while not (folder/'sample.csv.gz').exists():time.sleep(10)
    sample=pd.read_csv(folder/'sample.csv.gz');d=raw.iloc[sample.raw_row_id.to_numpy()].copy().reset_index(drop=True)
    for c in ['metal_linker','functional_groups','organic_linker1','organic_linker2','topology']:d[c]=d[c].map(norm)
    d['raw_row_id']=sample.raw_row_id.to_numpy();keep=d.organic_linker1.isin(mapping)&d.organic_linker2.isin(mapping);destfolder=commonroot/folder.name;destfolder.mkdir(exist_ok=True);sample.assign(mapped_eligible=keep.to_numpy()).to_csv(destfolder/'original_sample_coverage.csv.gz',index=False);sample.loc[keep].to_csv(destfolder/'sample.csv.gz',index=False);atomic_json(destfolder/'mapping_exclusion.json',dict(n_original=len(d),n_mapped=int(keep.sum()),excluded_fraction=float((~keep).mean()),by_topology={str(k):dict(n_original=len(v),n_mapped=int(keep.loc[v.index].sum())) for k,v in d.groupby('topology')}));d=d.loc[keep].reset_index(drop=True);sample=sample.loc[keep].reset_index(drop=True)
    num=d[NUMERIC_FEATURES].to_numpy(np.float32);y=sample.y_true.to_numpy();li=np.column_stack([d[c].map(lookup).to_numpy() for c in ['organic_linker1','organic_linker2']]);assert np.isfinite(li).all()
    for protocol in CONFIG['protocols']:
     nf=5 if protocol!='LOTO' else pd.read_csv(folder/'sample.csv.gz').topology.nunique()
     for fold in range(nf):
      fp=folder/f'{protocol}_fold{fold}'
      while not (fp/'novelty.csv.gz').exists():time.sleep(10)
      originalsplit=np.load(fp/'split.npz');tr=np.flatnonzero(sample.raw_row_id.isin(originalsplit['train_raw_id']).to_numpy());te=np.flatnonzero(sample.raw_row_id.isin(originalsplit['test_raw_id']).to_numpy());fp=destfolder/fp.name;fp.mkdir(exist_ok=True);np.savez_compressed(fp/'split.npz',train_index=tr,test_index=te,train_raw_id=sample.raw_row_id.to_numpy()[tr],test_raw_id=sample.raw_row_id.to_numpy()[te]);assert len(tr)>0
      if not (fp/'novelty.csv.gz').exists():
       z,meta=diagnostics(d,num,tr,te);z['y_true']=y[te];z.to_csv(fp/'novelty.csv.gz',index=False);atomic_json(fp/'distance_and_support.json',meta)
      if not (fp/'novelty_chemistry.csv.gz').exists():
       z=pd.read_csv(fp/'novelty.csv.gz');trainunique=np.unique(li[tr]);smax=sm[:,trainunique].max(1);seenstructures={smiles[i] for i in trainunique}
       for slot in range(2):
        z[f'linker{slot+1}_smax']=smax[li[te,slot]];z[f'linker{slot+1}_structure_seen']=[smiles[i] in seenstructures for i in li[te,slot]]
       z['linker_smin']=z[['linker1_smax','linker2_smax']].min(axis=1);z['linker_smean']=z[['linker1_smax','linker2_smax']].mean(axis=1);z['mapping_status']='validated_parent_graph';z['both_parent_structures_seen']=z.linker1_structure_seen&z.linker2_structure_seen
       z['chemical_similarity_bin']=pd.cut(z.linker_smin,[-np.inf,.5,.7,.9,1.0000001],labels=['<0.5','0.5-0.7','0.7-0.9','0.9-1.0'],right=False).astype(str)
       z['parent_structure_status']=np.where(z.both_parent_structures_seen,'both_seen','at_least_one_unseen')
       tmp=fp/'novelty_chemistry.tmp.csv.gz';z.to_csv(tmp,index=False);tmp.replace(fp/'novelty_chemistry.csv.gz')
       atomic_json(fp/'chemical_mapping_coverage.json',dict(n_train=len(tr),n_test=len(te),train_row_coverage=1.,test_row_coverage=1.,n_unique_train_ids=len(trainunique),n_unique_train_structures=len(seenstructures),similarity_reference='union of both train roles; unique standardized parent structures; exact structures allowed',test_both_structure_seen_fraction=float(z.both_parent_structures_seen.mean()),similarity_bin_rule='predefined descriptive [0,.5),[.5,.7),[.7,.9),[.9,1]; no calibration or universal boundary claim'))
      for rep,cats0 in CONFIG['representations'].items():
       needed0=[m for m in CONFIG['models'] if not (fp/f'prediction_{rep}_{m}.npz').exists()]
       if not needed0:continue
       aa=num[tr];bb=num[te];fields={}
       if cats0:
        en=OneHotEncoder(handle_unknown='ignore',sparse_output=False,dtype=np.float32);aa=np.c_[aa,en.fit_transform(d.iloc[tr][cats0])];bb=np.c_[bb,en.transform(d.iloc[te][cats0]) if len(te) else np.empty((0,aa.shape[1]-num.shape[1]),dtype=np.float32)];fields={c:dict(vocabulary=v.tolist(),unknown_test_fraction=float((~d.iloc[te][c].isin(v)).mean()) if len(te) else None) for c,v in zip(cats0,en.categories_)}
       atomic_json(fp/f'encoding_{rep}.json',dict(n_features=aa.shape[1],fields=fields))
       for mn in needed0:
        start=time.monotonic();cls=RandomForestRegressor if mn=='RF' else ExtraTreesRegressor;mod=cls(n_estimators=120,max_features='sqrt',random_state=seed,n_jobs=6);mod.fit(aa,y[tr]);pred=mod.predict(bb) if len(te) else np.array([]);tmp=fp/f'prediction_{rep}_{mn}.tmp.npz';np.savez_compressed(tmp,raw_row_id=sample.raw_row_id.to_numpy()[te],y_true=y[te],prediction=pred);tmp.replace(fp/f'prediction_{rep}_{mn}.npz');atomic_json(fp/f'model_{rep}_{mn}.json',dict(parameters=mod.get_params(),elapsed_seconds=time.monotonic()-start));print('common',size,seed,target,protocol,fold,rep,mn,'n',len(tr),len(te),flush=True);del mod
      needed=[m for m in CONFIG['models'] if not (fp/f'prediction_T_{m}.npz').exists()]
      if not needed:continue
      enc=OneHotEncoder(handle_unknown='ignore',sparse_output=False,dtype=np.float32);cats=['metal_linker','functional_groups'];ac=enc.fit_transform(d.iloc[tr][cats]);bc=enc.transform(d.iloc[te][cats]) if len(te) else np.empty((0,ac.shape[1]),dtype=np.float32);blocks_a=[];blocks_b=[];kept=[]
      for slot in range(2):
       trainbits=bm[li[tr,slot]];s=trainbits.sum(0);mask=(s>0)&(s<len(tr));kept.append(np.flatnonzero(mask).tolist());blocks_a.append(trainbits[:,mask]);blocks_b.append(bm[li[te,slot]][:,mask])
      a=np.column_stack([num[tr],ac,*blocks_a]).astype(np.float32);b=np.column_stack([num[te],bc,*blocks_b]).astype(np.float32)
      atomic_json(fp/'encoding_T.json',dict(n_features=a.shape[1],fingerprint_kept_bit_indices=kept,fields={c:dict(vocabulary=v.tolist(),unknown_test_fraction=float((~d.iloc[te][c].isin(v)).mean())) for c,v in zip(cats,enc.categories_)}))
      for modelname in needed:
       start=time.monotonic();cls=RandomForestRegressor if modelname=='RF' else ExtraTreesRegressor;model=cls(n_estimators=120,max_features='sqrt',random_state=seed,n_jobs=6);model.fit(a,y[tr]);pred=model.predict(b) if len(te) else np.array([])
       tmp=fp/f'prediction_T_{modelname}.tmp.npz';np.savez_compressed(tmp,raw_row_id=sample.raw_row_id.to_numpy()[te],y_true=y[te],prediction=pred);tmp.replace(fp/f'prediction_T_{modelname}.npz');atomic_json(fp/f'model_T_{modelname}.json',dict(parameters=model.get_params(),elapsed_seconds=time.monotonic()-start));print('T',size,seed,target,protocol,fold,modelname,'p',a.shape[1],'sec',round(time.monotonic()-start,1),flush=True);del model
 print('ALL T FITS AND CHEMICAL NOVELTY COMPLETE',flush=True)
if __name__=='__main__':run()
