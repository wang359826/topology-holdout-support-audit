from pathlib import Path
import subprocess,sys,time,json
p=Path(__file__).resolve().parents[1]
start=time.monotonic()
try:
 cp=subprocess.run([sys.executable,str(p/'scripts/probe_rdkit.py'),'DAKVUI_clean.cif'],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
 r={'file':'DAKVUI_clean.cif','timeout_seconds':180,'elapsed_seconds':time.monotonic()-start,'returncode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr}
 try:r['result']=json.loads(cp.stdout.strip().splitlines()[-1])
 except (ValueError,IndexError):pass
except subprocess.TimeoutExpired as e:
 def decode(s):return s.decode('utf-8',errors='replace') if isinstance(s,bytes) else s
 r={'file':'DAKVUI_clean.cif','timeout_seconds':180,'elapsed_seconds':time.monotonic()-start,'error':'timeout_180s','stdout':decode(e.stdout),'stderr':decode(e.stderr)}
out=p/'outputs/DAKVUI_retry_180s.json'
out.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(r,ensure_ascii=True,indent=2))
