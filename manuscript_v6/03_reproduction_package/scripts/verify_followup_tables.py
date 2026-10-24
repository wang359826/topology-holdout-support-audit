#!/usr/bin/env python
"""Recompute SI S19-S24 from archived follow-up metrics; no model fitting.
This verifies table arithmetic and designs, not raw-data/model provenance.
Uses only the Python standard library. Run from any working directory.
"""
from pathlib import Path
import csv, json, math, re, statistics, sys
from collections import defaultdict

PKG = Path(__file__).resolve().parents[1]
ARC = PKG / "outputs" / "followup_20261023"
SI = PKG.parent / "02_supplementary" / "SI_v6.md"
SEEDS = {"42", "143", "244", "345", "446"}
T4 = 2.7764451051977987

def read_csv(rel):
    with (ARC / rel).open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert rows, f"empty: {rel}"
    return rows

def read_json(rel):
    return json.loads((ARC / rel).read_text(encoding="utf-8-sig"))

def one(rows, **filters):
    matches = [r for r in rows if all(str(r[k]) == str(v) for k,v in filters.items())]
    assert len(matches) == 1, (filters, len(matches))
    return matches[0]

def close(a,b,tol=1e-11):
    assert math.isfinite(float(a)) and math.isfinite(float(b)), (a,b)
    assert abs(float(a)-float(b)) <= tol, (a,b)

def stats(values):
    v = [float(x) for x in values]
    return statistics.mean(v), statistics.stdev(v)

def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |",
                      "| " + " | ".join("---" for _ in headers) + " |"] +
                     ["| " + " | ".join(str(x) for x in row) + " |" for row in rows])

def ranks(v):
    order = sorted(range(len(v)), key=lambda i:v[i])
    out = [0.] * len(v)
    i = 0
    while i < len(v):
        j=i+1
        while j<len(v) and v[order[j]]==v[order[i]]: j+=1
        for k in range(i,j): out[order[k]]=(i+j-1)/2+1
        i=j
    return out

def spearman(rows, field):
    x=ranks([float(r[field]) for r in rows])
    y=ranks([float(r["MAE"]) for r in rows])
    mx,my=statistics.mean(x),statistics.mean(y)
    return sum((a-mx)*(b-my) for a,b in zip(x,y))/math.sqrt(
        sum((a-mx)**2 for a in x)*sum((b-my)**2 for b in y))

def make_tables():
    result={}
    # S19: recompute paired seed differences, check both archived derived tables.
    derived=read_csv("experiment12/paper_tables/primary_LOTO_paired_directions.csv")
    size=read_csv("experiment12/paper_tables/size_sensitivity_LOTO_paired.csv")
    rows=[]
    for scope,contrast in [("full","I-B"),("mapped_common","T-I")]:
        pooled=read_csv(f"experiment12/{scope}/pooled_metrics.csv")
        a,b=contrast.split("-")
        for target in ["uptake","selectivity"]:
            for model in ["RF","ET"]:
                diffs=[]
                for seed in sorted(SEEDS,key=int):
                    common=dict(stage="25000",seed=seed,target=target,protocol="LOTO",model=model)
                    ra=one(pooled,representation=a,**common)
                    rb=one(pooled,representation=b,**common)
                    assert ra["n"]==rb["n"]
                    diffs.append(float(ra["MAE"])-float(rb["MAE"]))
                mean,sd=stats(diffs)
                dr=one(derived,scope=scope,target=target,model=model,contrast=contrast)
                close(mean,dr["mean_delta_MAE"]);close(sd,dr["SD"])
                assert int(dr["n_seeds"])==5
                assert sum(x<0 for x in diffs)==int(dr["n_negative"])
                common=dict(stage="100000",seed="42",target=target,protocol="LOTO",model=model)
                ra=one(pooled,representation=a,**common);rb=one(pooled,representation=b,**common)
                assert ra["n"]==rb["n"]
                delta=float(ra["MAE"])-float(rb["MAE"])
                close(delta,one(size,scope=scope,target=target,model=model,contrast=contrast)["delta_MAE"])
                rows.append(["Full" if scope=="full" else "Mapped",contrast,
                             "Uptake" if target=="uptake" else "Log-selectivity",model,
                             f"{mean:+.6f} ± {sd:.6f}",f"{delta:+.6f}"])
    assert len(derived)==len(size)==8
    result[19]=table(["Population","Contrast","Target","Model","25k ΔMAE, mean ± SD","100k ΔMAE"],rows)
    # S20: seed42 role-specific novelty; classes partition the scored uptake rows.
    novel=read_csv("experiment12/full/novelty_error_metrics.csv")
    rows=[]; totals={}
    for c in ["C0","C1","C2","C3"]:
        cells=[c]
        for stage in ["25000","100000"]:
            r=one(novel,stage=stage,seed="42",target="uptake",protocol="LOTO",
                  representation="I",model="RF",novelty_class=c,scalar_domain="all")
            cells += [f"{int(r['n']):,}",f"{float(r['MAE']):.6f}"]
            totals[stage]=totals.get(stage,0)+int(r["n"])
        rows.append(cells)
    full=read_csv("experiment12/full/pooled_metrics.csv")
    for stage,total in totals.items():
        assert total==int(one(full,stage=stage,seed="42",target="uptake",
                              protocol="LOTO",representation="I",model="RF")["n"])
    result[20]=table(["Class","25k n","25k MAE","100k n","100k MAE"],rows)
    # S21: technically returned results, without treating them as validated identities.
    summary=read_json("experiment3/summary.json")
    pilot=read_json("experiment3/topology_pilot.json")
    outputs=[]
    for record in pilot:
        try: outputs.append(json.loads(record.get("stdout","")))
        except (ValueError,TypeError): outputs.append({})
    keys=sum(bool(x.get("key")) for x in outputs)
    named=sum(x.get("status")=="ok" and str(x.get("topology","")).lower()
              not in {"","unknown","error","none"} for x in outputs)
    experts=read_csv("experiment3/expert_review_sheet.csv")
    fields=["node_correct","linker_correct","periodic_boundary_checked",
            "interpenetration_checked","original_publication_checked"]
    completed=sum(all(r[f].strip().lower() not in {"","pending"} for f in fields) for r in experts)
    assert len(experts)==int(summary["sample_n"])==40
    assert completed==int(summary["human_review_completed"])==0
    assert len(outputs)==10 and keys==9 and named==6
    result[21]=table(["Pilot measure","Returned / completed"],
        [["CIFs in source archive",f"{int(summary['archive_cifs']):,}"],
         ["Sampled CIFs parsed",f"{summary['parsed']} / {summary['sample_n']}"],
         ["Metal + organic candidates with bond cuts",f"{summary['candidate_usable']} / {summary['sample_n']}"],
         ["Topology pilot: net key",f"{keys} / {len(outputs)}"],
         ["Topology pilot: named-net match",f"{named} / {len(outputs)}"],
         ["Independent expert checks completed",f"{completed} / {len(experts)}"]])
    # S22: rank correlations, with average ranks for tied diagnostic values.
    diagnostic=read_csv("experiment4/fold_diagnostics.csv")
    eleven=[r for r in diagnostic if r["size"]=="100000" and r["seed"]=="42"]
    ten=[r for r in eleven if int(r["n_test"])>=100]
    assert len(eleven)==11 and len({r["group"] for r in eleven})==11
    assert len(ten)==10 and sum(int(r["n_test"]) for r in ten)==99995
    fields=[("exact_mismatch","Exact-key mismatch"),("unit_novelty","Any building-unit novelty"),
            ("metal_novelty","Metal-node novelty"),("linker_novelty","Linker novelty (union)"),
            ("geometry_mean","Mean numerical distance"),("geometry_far_fraction","Numerically far fraction"),
            ("novel_and_far","Novel and numerically far")]
    result[22]=table(["Diagnostic","ρ, 11 topologies","ρ, 10 topologies (n ≥ 100)"],
         [[label,f"{spearman(eleven,key):+.6f}",f"{spearman(ten,key):+.6f}"] for key,label in fields])
    # S23: paired differences within each fixed-pool learner seed.
    original=read_csv("experiment5/curve_metrics.csv")
    clean=read_csv("experiment5/cleaned_endpoint_metrics.csv")
    endpoints=read_csv("experiment5/paired_endpoints.csv")
    clean_summary=read_csv("experiment5/cleaned_endpoint_summary.csv")
    rows=[]
    for label,data in [("Historical rows",original),("Negative descriptors removed",clean)]:
        for target in ["nbo","pcu"]:
            rr=[r for r in data if r["target"]==target and
                (label!="Historical rows" or r["subset"]=="all")]
            d={}
            for r in rr:
                if float(r["dose"]) in {0.,1.}:
                    key=(r["seed"],float(r["dose"]))
                    assert key not in d
                    d[key]=float(r["MAE"])
            assert len(d)==10 and {x[0] for x in d}==SEEDS
            a=statistics.mean(d[(s,0.)] for s in SEEDS)
            b=statistics.mean(d[(s,1.)] for s in SEEDS)
            delta,sd=stats(d[(s,1.)]-d[(s,0.)] for s in SEEDS)
            lo,hi=delta-T4*sd/math.sqrt(5),delta+T4*sd/math.sqrt(5)
            if label=="Historical rows":
                ref=one(endpoints,target=target,subset="all")
                close(delta,ref["MAE_100_minus_0"])
            else:
                ref=one(clean_summary,target=target)
                close(a,ref["MAE_0"]);close(b,ref["MAE_100"]);close(delta,ref["delta"])
            close(lo,ref["CI95_low"]);close(hi,ref["CI95_high"])
            rows.append([label,target,f"{a:.6f}",f"{b:.6f}",f"{delta:+.6f}",
                         f"[{lo:+.6f}, {hi:+.6f}]"])
    result[23]=table(["Row policy","Test","MAE, 0%","MAE, 100%","ΔMAE","Paired 95% t interval"],rows)
    # S24: all RF/5% rows; also check the complete 480-row metric-summary archive.
    metrics=read_csv("experiment6/screening_metrics.csv")
    summary=read_csv("experiment6/screening_summary.csv")
    pools=read_csv("experiment6/pool_audit.csv")
    grouped=defaultdict(list)
    dims=["target","support","representation","model","budget_fraction"]
    for r in metrics:
        assert r["target"] in {"nbo","pcu"} and r["support"] in {"0","1"}
        assert r["representation"] in {"G","B","I"} and r["model"] in {"RF","ET"}
        assert float(r["budget_fraction"]) in {.01,.05,.1,.2}
        assert int(r["k"])==math.ceil(int(r["n_candidates"])*float(r["budget_fraction"]))
        close(float(r["oracle_mean"])-float(r["selected_mean"]),r["regret"])
        grouped[tuple(r[x] for x in dims)].append(r)
    assert len(metrics)==480 and len(grouped)==len(summary)==96
    assert len({tuple(r[x] for x in dims) for r in summary})==96
    for key,rr in grouped.items():
        assert len(rr)==5 and {r["seed"] for r in rr}==SEEDS
        ref=one(summary,**dict(zip(dims,key)))
        for field in ["recovery","selected_mean","oracle_mean","regret","random_mean","lift","gain","MAE"]:
            mean,sd=stats(r[field] for r in rr)
            close(mean,ref[field+"_mean"]);close(sd,ref[field+"_std"])
    rows=[]
    for target in ["nbo","pcu"]:
        for support in ["0","1"]:
            for representation in ["G","B","I"]:
                ref=one(summary,target=target,support=support,representation=representation,
                        model="RF",budget_fraction="0.05")
                pool=one(pools,target=target,support=support,representation=representation)
                assert int(pool["n_candidates"])=={"nbo":7663,"pcu":31682}[target]
                assert int(pool["n_train"])=={"nbo":4991,"pcu":4719}[target]
                rows.append([target,f"{100*int(support)}%",representation,ref["k"],
                    f"{100*float(ref['recovery_mean']):.2f} ± {100*float(ref['recovery_std']):.2f}",
                    f"{float(ref['selected_mean_mean']):.6f}",f"{float(ref['regret_mean']):.6f}"])
    result[24]=table(["Test","Shared partners","Representation","k","Recovery (%), mean ± SD",
                      "Selected mean","Regret"],rows)
    return result

def verify():
    text=SI.read_text(encoding="utf-8")
    tabs=make_tables()
    for n,expected in tabs.items():
        label=f"**Table S{n}.**"
        assert text.count(label)==1, f"missing/duplicate S{n}"
        tail=text.split(label,1)[1]
        lines=tail.splitlines()
        start=next(i for i,l in enumerate(lines) if l.startswith("|"))
        block=[]
        for line in lines[start:]:
            if not line.startswith("|"):break
            block.append(line.rstrip())
        assert "\n".join(block)==expected, f"S{n}: rendered cells differ from recomputed values"
    print("PASS: SI S19-S24, paired directions/intervals, novelty totals, pilot counts,")
    print("rank correlations, and all 480 screening-metric / 96 summary records.")
    print("Scope: archived-metric arithmetic and manuscript tables; no raw-data refit,")
    print("external validation, identity validation or prospective screening claimed.")

if __name__=="__main__":
    try:
        if "--render" in sys.argv:
            for n,t in make_tables().items():print(f"\nTable S{n}\n{t}")
        else:verify()
    except (AssertionError,ValueError,KeyError,StopIteration) as exc:
        print(f"FAIL: {exc}",file=sys.stderr)
        raise SystemExit(1)
