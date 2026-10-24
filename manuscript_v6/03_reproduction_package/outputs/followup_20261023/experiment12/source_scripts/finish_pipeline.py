from pathlib import Path
import sys,time,subprocess,json
p=Path('实验12_化学表示与新颖性');script=p/'scripts';log=p/'completion_pipeline.log'
def call(args):
 with log.open('a',encoding='utf-8') as f:
  f.write('\nSTART '+repr(args)+'\n');f.flush();subprocess.run([sys.executable,*map(str,args)],stdout=f,stderr=subprocess.STDOUT,check=True)
# This companion runs only the 100k mapped scope; 25k mapped and the full matrix run separately.
call([script/'run_transferable.py','--stage','100000'])
while True:
 ready=True
 for size,seeds in {'25000':[42,143,244,345,446],'100000':[42]}.items():
  for seed in seeds:
   for target in ['uptake','selectivity']:
    for root,nrep in [('outputs',8),('outputs_mapped_common',10)]:
     folder=p/root/f'n{size}_seed{seed}_{target}'
     for protocol,nf in [('random',5),('topology',5),('LOTO',11)]:
      for fold in range(nf):
       fp=folder/f'{protocol}_fold{fold}';count=len([v for v in fp.glob('prediction_*.npz') if '.tmp.' not in v.name])
       if count!=nrep:ready=False
 if ready:break
 time.sleep(20)
call([script/'summarize_results.py'])
call([script/'summarize_results.py','--mapped'])
call([script/'final_report.py'])
with log.open('a',encoding='utf-8') as f:f.write('\nPIPELINE COMPLETED\n')
print('PIPELINE COMPLETED',flush=True)
