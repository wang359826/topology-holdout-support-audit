from pathlib import Path
import json,csv,collections,traceback
from ase.io import read
from mofstructure import mofdeconstructor as md
p=Path(__file__).resolve().parents[1]; out=p/'outputs'
meta=list(csv.DictReader(open(p/'data/2019-07-01-ASR-public_12020.csv',encoding='utf-8-sig')))
counts={'rows':len(meta),'unique_filenames':len({r['filename'] for r in meta}),'disorder':dict(collections.Counter(r['DISORDER'].strip() or 'unmarked' for r in meta)),'from_CSD':dict(collections.Counter(r['from_CSD'] for r in meta)),'all_metals':dict(collections.Counter(r['All_Metals'] for r in meta))}
(out/'metadata_census.json').write_text(json.dumps(counts,indent=2),encoding='utf-8')
manifest=json.loads((out/'sample_manifest.json').read_text())
f=p/'data/pilot_cifs'/manifest[0]['file']
try:
 a=read(f); comps,bonds,por,regions,_=md.ligands_and_metal_clusters(a);md.find_unique_building_units(comps,bonds,a,por,regions,wrap_system=False,cheminfo=True)
 result='success'
except Exception:result=traceback.format_exc()
(out/'chemical_identifier_probe.txt').write_text(result,encoding='utf-8')
review=[]
frags=json.loads((out/'fragment_details.json').read_text())
for rec in frags:
 review.append({'file':rec['file'],'metal_fragment_formula':';'.join(x['formula'] for x in rec['fragments'] if x['type']=='metal'),'linker_fragment_formula':';'.join(x['formula'] for x in rec['fragments'] if x['type']=='linker'),'node_correct':'pending','linker_correct':'pending','periodic_boundary_checked':'pending','interpenetration_checked':'pending','original_publication_checked':'pending','notes':''})
with open(out/'expert_review_sheet.csv','w',newline='',encoding='utf-8-sig') as h:
 w=csv.DictWriter(h,fieldnames=list(review[0]));w.writeheader();w.writerows(review)
print(json.dumps({k:v for k,v in counts.items() if k!='all_metals'},indent=2));print(result[-1600:])

