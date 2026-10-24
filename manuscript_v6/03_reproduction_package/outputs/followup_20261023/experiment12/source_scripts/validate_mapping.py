from pathlib import Path
import sys,json,tarfile,hashlib,time
from extract_linker_chemistry import extract,S
from rdkit import Chem,rdBase,DataStructs
from rdkit.Chem import rdFingerprintGenerator
import numpy as np

def main():
 archive=S/'MOF_database.tar.gz'
 if not archive.exists():raise RuntimeError('Verified archive not yet ready')
 primary=json.loads((S/'mapping_validation_targets.json').read_text())
 secondary=json.loads((S/'mapping_validation_secondary.json').read_text())
 wanted={v['filename'] for refs in [primary,secondary] for v in refs.values()}
 dest=S/'linker_validation_cifs';dest.mkdir(exist_ok=True)
 missing=wanted-{p.name for p in dest.glob('*.cif')}
 if missing:
  with tarfile.open(archive,'r|gz') as tar:
   for m in tar:
    name=Path(m.name).name
    if name in missing:
     (dest/name).write_bytes(tar.extractfile(m).read());missing.remove(name)
    if not missing:break
 assert not missing,missing
 records=[];mapping={};gen=rdFingerprintGenerator.GetMorganGenerator(radius=2,fpSize=2048,includeChirality=False)
 for lid,ref in primary.items():
  checks=[]
  for role,refs in [('primary',primary),('secondary',secondary)]:
   if lid not in refs:continue
   f=dest/refs[lid]['filename']
   try:
    out=extract(f);ok=len(out['unique_smiles'])==1
    check=dict(role=role,file=f.name,sha256=hashlib.sha256(f.read_bytes()).hexdigest(),status='unique_parent' if ok else 'ambiguous',**out)
   except Exception as e:check=dict(role=role,file=f.name,status='failed',error=repr(e))
   checks.append(check)
  smiles={c['unique_smiles'][0] for c in checks if c['status']=='unique_parent'}
  ok=all(c['status']=='unique_parent' for c in checks) and len(smiles)==1
  rec=dict(linker_id=lid,status='validated_cross_reference' if ok and len(checks)>1 else 'validated_single_reference' if ok else 'unresolved',checks=checks)
  if ok:
   smi=next(iter(smiles));mapping[lid]=dict(smiles=smi,n_references=len(checks),validation=rec['status']);rec['smiles']=smi
  records.append(rec)
 audit=dict(rdkit=rdBase.rdkitVersion,source_doi='10.24435/materialscloud:2018.0016/v3',archive_md5='eeca5ea239f13e25ab11af385fdd2b53',definition='parent organic heavy-atom graphs from explicit original CIF bonds; remove metal; normalize terminal carboxylates as neutral acid; no stereochemical inference; FG retained separately',records=records,n_ids_requested=len(primary),n_ids_validated=len(mapping),n_cross_reference=sum(v['n_references']>1 for v in mapping.values()),validation='automated graph checks, not expert manual validation')
 (S/'validated_linker_mapping_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
 (S/'validated_linker_mapping.json').write_text(json.dumps(mapping,indent=2),encoding='utf-8')
 ids=sorted(mapping,key=int);bits=np.asarray([gen.GetFingerprintAsNumPy(Chem.MolFromSmiles(mapping[i]['smiles'])) for i in ids],dtype=np.uint8)
 np.savez_compressed(S/'morgan_parent_fingerprints.npz',linker_id=np.array(ids),bits=bits)
 sims=np.array([DataStructs.BulkTanimotoSimilarity(gen.GetFingerprint(Chem.MolFromSmiles(mapping[i]['smiles'])),[gen.GetFingerprint(Chem.MolFromSmiles(mapping[j]['smiles'])) for j in ids]) for i in ids])
 np.savez_compressed(S/'parent_tanimoto_matrix.npz',linker_id=np.array(ids),similarity=sims)
 print('Mapping validated',len(mapping),'of',len(primary),'cross references',audit['n_cross_reference'],flush=True)
 for r in records:
  if r['status']=='unresolved':print(json.dumps(r),flush=True)
if __name__=='__main__':main()
