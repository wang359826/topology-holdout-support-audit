from pathlib import Path
import csv,hashlib,json,random,tarfile,sys,subprocess,traceback,warnings
ROOT=Path(__file__).resolve().parents[1]
def main():
 data=ROOT/'data'; out=ROOT/'outputs'; out.mkdir(exist_ok=True)
 record=json.loads((data/'record_3370144.json').read_text(encoding='utf-8-sig'))
 checks=[]
 for item in record['files']:
  f=data/item['key']
  if f.exists():
   md5=hashlib.md5(f.read_bytes()).hexdigest(); checks.append({'file':f.name,'size':f.stat().st_size,'md5':md5,'expected_md5':item['checksum'].split(':')[-1],'ok':md5==item['checksum'].split(':')[-1]})
 assert all(c['ok'] for c in checks)
 (out/'checksums.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
 with tarfile.open(data/'2019-07-01-ASR-public_12020.tar') as tf:
  members=[m for m in tf.getmembers() if m.isfile() and m.name.lower().endswith('.cif')]
  chosen=random.Random(20261022).sample(members,40)
  folder=data/'pilot_cifs';folder.mkdir(exist_ok=True)
  for m in chosen:
   (folder/Path(m.name).name).write_bytes(tf.extractfile(m).read())
 manifest=[{'order':i,'member':m.name,'file':Path(m.name).name,'sha256':hashlib.sha256((folder/Path(m.name).name).read_bytes()).hexdigest()} for i,m in enumerate(chosen)]
 (out/'sample_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
 with open(data/'2019-07-01-ASR-public_12020.csv',encoding='utf-8-sig') as h:
  meta=list(csv.DictReader(h))
 byname={r['filename']+'.cif':r for r in meta}
 from ase.io import read
 from mofstructure import mofdeconstructor as md
 from ase.io.cif import parse_cif
 rows=[]; details=[]
 for m in manifest:
  f=folder/m['file']; row={'file':f.name,'archive_member':m['member'],'metadata_disorder':byname.get(f.name,{}).get('DISORDER',''),'metadata_metals':byname.get(f.name,{}).get('All_Metals',''),'human_review':'pending'}
  try:
   with warnings.catch_warnings(record=True) as ws:
    a=read(f)
   row.update(parse_ok=True,n_atoms=len(a),warnings=';'.join(str(w.message) for w in ws))
   metals=sorted(set(a.get_chemical_symbols())&set(md.transition_metals()))
   row.update(metals=','.join(metals),n_metal_elements=len(metals),has_carbon='C' in a.get_chemical_symbols())
   blocks=list(parse_cif(str(f))); occ=blocks[0].get('_atom_site_occupancy',[])
   row['partial_occupancy']=any(float(v)<0.999 for v in occ) if occ else None
   comps,bonds,por,regions,breaking=md.ligands_and_metal_clusters(a)
   mus,lus,bu=md.find_unique_building_units(comps,bonds,a,por,regions,wrap_system=False,cheminfo=False)
   row.update(decomp_returned=True,n_metal_units=len(mus),n_linker_units=len(lus),n_breaks=len(bonds),candidate_usable=bool(mus and lus and bonds))
   details.append({'file':f.name,'fragments':[{'type':typ,'formula':frag.get_chemical_formula(),'info':frag.info} for typ,group in [('metal',mus),('linker',lus)] for frag in group],'bonds_to_break':bonds})
  except Exception as e: row.update(error=repr(e),traceback=traceback.format_exc())
  rows.append(row)
 fields=sorted(set().union(*(r.keys() for r in rows)))
 with open(out/'pilot_structure_audit.csv','w',newline='',encoding='utf-8-sig') as h:
  w=csv.DictWriter(h,fieldnames=fields);w.writeheader();w.writerows(rows)
 (out/'fragment_details.json').write_text(json.dumps(details,indent=2,default=lambda x:x.tolist() if hasattr(x,'tolist') else str(x)),encoding='utf-8')
 # Preselected first 10 in random sample order; separate processes provide Windows timeouts.
 tops=[]
 for m in manifest[:10]:
  try:
   cp=subprocess.run([sys.executable,str(Path(__file__)),'topology',str(folder/m['file'])],capture_output=True,text=True,timeout=25,encoding='utf-8',errors='replace')
   tops.append({'file':m['file'],'returncode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr})
  except subprocess.TimeoutExpired:tops.append({'file':m['file'],'status':'timeout_25s'})
  (out/'topology_pilot.json').write_text(json.dumps(tops,indent=2),encoding='utf-8')
 summary={'seed':20261022,'archive_cifs':len(members),'metadata_rows':len(meta),'metadata_columns':list(meta[0]),'sample_n':len(rows),'parsed':sum(r.get('parse_ok',False) for r in rows),'decomposition_returned':sum(r.get('decomp_returned',False) for r in rows),'candidate_usable':sum(r.get('candidate_usable',False) for r in rows),'zero_linker':[r['file'] for r in rows if r.get('n_linker_units')==0],'multi_metal_n':sum(r.get('n_metal_elements',0)>1 for r in rows),'disorder_marked_n':sum(bool(r['metadata_disorder'].strip()) for r in rows),'partial_occupancy_n':sum(r.get('partial_occupancy') is True for r in rows),'human_review_completed':0}
 (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary,indent=2))
if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='topology':
  from mofstructure.topology import analyse
  print(json.dumps(analyse(sys.argv[2],method='sbus',timeout=None),default=str))
 else:main()
