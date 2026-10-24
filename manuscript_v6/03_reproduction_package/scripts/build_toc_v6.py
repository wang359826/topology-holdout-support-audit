#!/usr/bin/env python
"""Build a qualitative ACS TOC graphic: 3.25 by 1.75 inches, RGB, 300 dpi.
No specific study results are printed. Shapes denote topology groups; letters
denote illustrative composition keys, not measured observations.
"""
from pathlib import Path
import argparse

def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from PIL import Image
    ap=argparse.ArgumentParser()
    ap.add_argument('--width',type=int,default=975)
    ap.add_argument('--height',type=int,default=525)
    ap.add_argument('--dpi',type=int,default=300)
    ap.add_argument('--out',default=str(Path(__file__).resolve().parents[2]/'01_manuscript/figures/TOC_graphic.png'))
    args=ap.parse_args()
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':7.0})
    f=plt.figure(figsize=(args.width/args.dpi,args.height/args.dpi),dpi=args.dpi,facecolor='white')
    a=f.add_axes([0,0,1,1]);a.set_xlim(0,1);a.set_ylim(0,1);a.axis('off')
    ink='#19334B';blue='#237CAC';gray='#CBD5DD';orange='#D76B36'
    a.text(.5,.94,'Topology hold-out',ha='center',va='top',fontsize=10,fontweight='bold',color=ink)
    a.text(.245,.77,'Training topologies',ha='center',fontsize=7.2,color=ink)
    a.text(.755,.77,'Held-out topology',ha='center',fontsize=7.2,color=ink)
    for y,marker in [(.60,'o'),(.42,'^')]:
        for x,key,col in [(.11,'A',blue),(.245,'B',gray),(.38,'C',gray)]:
            a.scatter([x],[y],s=190,marker=marker,c=[col],edgecolors='white',linewidths=.7)
            a.text(x,y-.006 if marker=='^' else y,key,ha='center',va='center',fontsize=7,color='white' if col==blue else ink,fontweight='bold')
    a.plot([.50,.50],[.34,.71],color='#9CAEBB',lw=.8,ls=(0,(2,2)))
    for x,key,col in [(.62,'A',blue),(.755,'D',orange),(.89,'E',orange)]:
        a.scatter([x],[.51],s=190,marker='s',c=[col],edgecolors='white',linewidths=.7)
        a.text(x,.51,key,ha='center',va='center',fontsize=7,color='white',fontweight='bold')
    a.text(.5,.26,'Shared keys  |  Unseen keys',ha='center',fontsize=7,color=ink)
    a.plot([.06,.94],[.20,.20],color='#D9E0E5',lw=.8)
    a.text(.5,.105,'Chemical support ≠ error attribution',ha='center',va='center',fontsize=8,fontweight='bold',color=ink)
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    f.savefig(out,dpi=args.dpi,facecolor='white');plt.close(f)
    im=Image.open(out).convert('RGB');im.save(out,dpi=(args.dpi,args.dpi));im.save(out.with_suffix('.tiff'),compression='tiff_lzw',dpi=(args.dpi,args.dpi))
    print(str(out));print(str(out.with_suffix('.tiff')));print('RGB 975x525 at 300 dpi; minimum text 7 pt')
    return 0
if __name__=='__main__':raise SystemExit(main())
