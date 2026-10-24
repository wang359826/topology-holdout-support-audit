#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build the four main figures and the SI figures for Manuscript_v6 from archived CSVs.

Figure order follows the argument of the paper:
  Fig 1  what the split removes (support)
  Fig 2  how support change relates to measured performance (protocols + representation)
  Fig 3  what the interventions allow one to interpret (removal arms + matched replacement)
  Fig 4  what it means for screening (OOF rankings + fixed candidate pool)
  figS8  the ARC-MOF support audit (moved out of the main figures)

Self-contained matplotlib; outputs PNG/PDF into ../01_manuscript/figures/.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..", "_tools", "pylibs312")))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
OUT = os.path.join(PKG, "outputs")
DEST = os.path.abspath(os.path.join(PKG, os.pardir, "01_manuscript", "figures"))
os.makedirs(DEST, exist_ok=True)

plt.rcParams.update({
    'font.size': 7, 'axes.labelsize': 7, 'axes.titlesize': 8,
    'xtick.labelsize': 6.5, 'ytick.labelsize': 6.5,
    'axes.spines.top': False, 'axes.spines.right': False,
    'figure.dpi': 150, 'pdf.fonttype': 42, 'ps.fonttype': 42,
    'svg.fonttype': 'none',
})


def save(fig, stem):
    from matplotlib.text import Text
    # Keep text legible at the manuscript's actual 492-point printed width.
    for item in fig.findobj(Text):
        if item.get_text().strip():
            item.set_fontsize(max(6.2, min(item.get_fontsize(), 8.0)))
    target = 492 / 72
    for _ in range(18):
        fig.tight_layout(pad=0.7, w_pad=1.1, h_pad=1.6)
        fig.canvas.draw()
        width = fig.get_tightbbox(fig.canvas.get_renderer()).width + 0.02
        if abs(width - target) < 0.005:
            break
        w, h = fig.get_size_inches()
        fig.set_size_inches(w * (1 + 0.65 * (target / width - 1)), h)
    p = os.path.join(DEST, stem)
    fig.savefig(p + '.png', bbox_inches='tight', pad_inches=0.01, dpi=600)
    fig.savefig(p + '.pdf', bbox_inches='tight', pad_inches=0.01)
    plt.close(fig)
    print('wrote', p + '.png')


# ---------------- Figure 1: support structure ----------------
def figure1():
    seen = pd.read_csv(os.path.join(OUT, "chemistry_seen_by_topology.csv"))
    c = seen[seen["granularity"].str.startswith("coarse")]
    order = ["pcu", "nbo", "sra", "etb", "acs", "bcu", "pts", "fof", "tbo", "the", "rht"]
    frac = {r.held_out_topology: r.unseen_fraction for _, r in c.iterrows()}
    frac_n = {r.held_out_topology: r.n_samples for _, r in c.iterrows()}
    vals = [frac[t] * 100 for t in order]

    jac = pd.read_csv(os.path.join(OUT, "topology_pair_overlap.csv"))
    jc = jac[jac["granularity"].str.startswith("coarse")]
    topos = sorted(set(jc["topo_a"]) | set(jc["topo_b"]))
    M = np.zeros((len(topos), len(topos)))
    idx = {t: i for i, t in enumerate(topos)}
    for _, r in jc.iterrows():
        M[idx[r.topo_a], idx[r.topo_b]] = r.jaccard
        M[idx[r.topo_b], idx[r.topo_a]] = r.jaccard
    offmax = M[~np.eye(len(topos), dtype=bool)].max()
    Mm = M.copy()
    np.fill_diagonal(Mm, np.nan)  # diagonal is self-overlap, not zero

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(6.85, 3.5), gridspec_kw={"width_ratios": [1, 1.18]})
    x = np.arange(len(order))
    colors = ["#d62728" if v >= 99.9 else "#1f77b4" for v in vals]
    ax.bar(x, vals, color=colors, edgecolor="white", linewidth=0.5)
    for xi, v, t in zip(x, vals, order):
        n = int(frac_n.get(t, 0))
        nlab = f"{n/1000:.0f}k" if n >= 1000 else str(n)
        ax.text(xi, v + 1.5, f"{v:.0f}", ha="center", fontsize=6.5)
        ax.text(xi, v + 8, f"n={nlab}", ha="center", va="bottom", rotation=90, fontsize=6.2)
    ax.set_xticks(x); ax.set_xticklabels(order, rotation=45, ha="right")
    ax.set_ylabel("structures unseen after hold-out  [%]")
    ax.set_title("(a) per-topology chemical-support loss", loc="left", fontsize=10)
    ax.set_ylim(0, 140)
    ax.grid(axis="y", alpha=0.3)

    im = ax2.imshow(Mm, cmap="Blues", vmin=0, vmax=offmax)
    ax2.set_xticks(range(len(topos))); ax2.set_yticks(range(len(topos)))
    ax2.set_xticklabels(topos, rotation=45, ha="right"); ax2.set_yticklabels(topos)
    for i in range(len(topos)):
        for j in range(len(topos)):
            if i == j:
                continue
            v = M[i, j]
            ax2.text(j, i, f"{v:.3f}" if v > 0 else "0", ha="center", va="center",
                     fontsize=5.5, color="white" if v > offmax * 0.6 else "black")
    cb = fig.colorbar(im, ax=ax2, fraction=0.046, pad=0.04)
    cb.set_label("Jaccard overlap (diagonal masked)")
    ax2.set_title("(b) pairwise composition overlap", loc="left", fontsize=10)
    save(fig, "Fig1_support_structure")


# ---------------- Figure 2: protocol contrasts and representation ----------------
def figure2():
    fin = pd.read_csv(os.path.join(OUT, "leakage_results_final.csv"))
    chem = pd.read_csv(os.path.join(OUT, "leakage_results_chemistry.csv"))
    notopo = pd.read_csv(os.path.join(OUT, "leakage_results_notopo100k.csv"))

    def r2(df, prefix):
        row = df[df.strategy.str.startswith(prefix)]
        return float(row.R2.iloc[0]) if len(row) else np.nan

    schemes = [("random", "随机划分（多数文献做法）", "random"),
               ("chemistry key", "按化学组成分组（metal+2 linkers）", "chemistry key"),
               ("linker pair", "按有机连接体分组", "linker pair"),
               ("metal", "按金属中心分组", "metal"),
               ("topology", "按拓扑分组", "topology")]
    vals, vals415 = [], []
    for _, f426, f415 in schemes:
        src = chem if "化学组成" in f426 else fin
        vals.append(100 * r2(src, f426))
        vals415.append(100 * r2(notopo, f426))

    fig, axes = plt.subplots(2, 2, figsize=(6.85, 5.8))
    ax, ax2, ax3, ax4 = axes.ravel()
    x = np.arange(len(schemes))
    ax.bar(x, vals, color=["#1f77b4"] * 4 + ["#d62728"], edgecolor="white", linewidth=0.5)
    ax.scatter(x, vals415, marker="D", s=20, facecolors="white", edgecolors="#222222",
               linewidths=0.8, zorder=6, label="415 features\n(topology block removed)")
    for xi, v, v415 in zip(x, vals, vals415):
        ax.text(xi, v + 1.2, f"{v:.1f}", ha="center", fontsize=7)
    ax.set_xticks(x); ax.set_xticklabels([s[0] for s in schemes], rotation=20, ha="right", fontsize=7)
    ax.set_ylabel("pooled R²  [%]")
    ax.set_ylim(0, 85)
    ax.set_title("(a) five validation schemes, 100k", loc="left", fontsize=9)
    ax.legend(fontsize=6, loc="upper right")
    ax.grid(axis="y", alpha=0.3)

    agg = pd.read_csv(os.path.join(OUT, "loto_aggregates_100k.csv")).iloc[0]
    rules = [("pooled", agg.pooled, "#1f77b4"), ("weighted", agg.weighted, "#ff7f0e"),
             ("macro", agg.macro, "#d62728"), ("median", agg["median"], "#2ca02c")]
    xb = np.arange(len(rules))
    ax2.bar(xb, [100 * r[1] for r in rules], color=[r[2] for r in rules],
            edgecolor="white", linewidth=0.5)
    per = pd.read_csv(os.path.join(OUT, "loto_per_topology_metrics_100k.csv"))
    per = per[per.valid_R2.astype(str).str.lower() == "true"]
    rng = np.random.default_rng(0)
    for i in range(len(rules)):
        ax2.scatter(i + rng.uniform(-0.18, 0.18, len(per)), 100 * per.R2.to_numpy(),
                    s=9, color="#333333", zorder=5, alpha=0.8)
    for xi, r in zip(xb, rules):
        ax2.annotate(f"{100*r[1]:+.1f}", xy=(xi, 100 * r[1]),
                     xytext=(0, 5 if r[1] >= 0 else -5), textcoords="offset points",
                     ha="center", va="bottom" if r[1] >= 0 else "top",
                     fontsize=7, bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.85))
    ax2.axhline(0, color="gray", lw=0.7, ls="--")
    ax2.set_xticks(xb); ax2.set_xticklabels([r[0] for r in rules], fontsize=7)
    ax2.set_ylabel("leave-one-topology-out R²  [%]")
    fold_values = 100 * per.R2.to_numpy()
    aggregate_values = np.array([100 * r[1] for r in rules])
    plotted_values = np.r_[fold_values, aggregate_values]
    value_min = min(0.0, float(np.min(plotted_values)))
    value_max = max(0.0, float(np.max(plotted_values)))
    value_pad = 0.08 * max(value_max - value_min, 1.0)
    ax2.set_ylim(value_min - value_pad, value_max + value_pad)
    ax2.set_title("(b) one LOTO run:\nfour aggregation rules", loc="left", fontsize=9)
    ax2.grid(axis="y", alpha=0.3)

    pt = pd.read_csv(os.path.join(OUT, "finish_20261023", "per_topology_paired_deltas.csv"))
    for axx, scope, title in [(ax3, "full", "(c) I − B, full sample"),
                              (ax4, "mapped_common", "(d) T − I, mapped subset")]:
        d = pt[(pt.scope == scope) & (pt.target == "uptake") & (pt.model == "RF")
               & (pt.contrast.isin(["I-B", "T-I"]))].sort_values("mean_delta")
        y = np.arange(len(d))
        colors = ["#1f77b4" if v < 0 else "#d62728" for v in d.mean_delta]
        axx.barh(y, 1000 * d.mean_delta.to_numpy(), color=colors, edgecolor="white", linewidth=0.4)
        axx.axvline(0, color="gray", lw=0.7)
        axx.set_yticks(y); axx.set_yticklabels(d.topology, fontsize=6.5)
        axx.set_xlabel("ΔMAE, first − second  [10⁻³ mmol/g]")
        axx.set_title(title, loc="left", fontsize=9)
        axx.grid(axis="x", alpha=0.3)
        axx.text(0.98, 0.02, "blue = first representation better\nn = %d topologies" % len(d),
                 transform=axx.transAxes, fontsize=6, color="#444444", ha="right", va="bottom")
    save(fig, "Fig2_protocol_support")


# ---------------- Figure 3: interventions ----------------
def figure3():
    s = pd.read_csv(os.path.join(OUT, "isoreticular_control_seeds.csv"))
    e = pd.read_csv(os.path.join(OUT, "arm_e_partner_coverage.csv"))

    def mean_sd(df, topo, regime, col):
        sub = df[(df.test_topo == topo) & (df.regime == regime)][col]
        return sub.mean(), sub.std()

    nbo_a = mean_sd(s, "nbo", "with_pair", "MAE")
    nbo_b = mean_sd(s, "nbo", "without_pair", "MAE")
    pcu_a = mean_sd(s, "pcu", "with_pair", "MAE")
    pcu_b = mean_sd(s, "pcu", "without_pair", "MAE")
    nbo_e = mean_sd(e, "nbo", "e_shared_only_removed", "MAE")
    nbo_f = mean_sd(e, "nbo", "f_size_matched_from_e", "MAE")
    pcu_e = mean_sd(e, "pcu", "e_shared_only_removed", "MAE")
    pcu_f = mean_sd(e, "pcu", "f_size_matched_from_e", "MAE")
    # size-matched (c): 5 outer seeds x 5 draws, SD across seed means (nested)
    nbo_c = (0.1071, 0.0048)
    pcu_c = (0.2364, 0.0031)

    fig = plt.figure(figsize=(6.85, 5.2))
    gs = fig.add_gridspec(2, 2)
    ax, ax2, ax3 = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, :])
    arms = ["a", "b", "c", "e", "f"]
    nbo_m = [nbo_a[0], nbo_b[0], nbo_c[0], nbo_e[0], nbo_f[0]]
    nbo_s = [nbo_a[1], nbo_b[1], nbo_c[1], nbo_e[1], nbo_f[1]]
    pcu_m = [pcu_a[0], pcu_b[0], pcu_c[0], pcu_e[0], pcu_f[0]]
    pcu_s = [pcu_a[1], pcu_b[1], pcu_c[1], pcu_e[1], pcu_f[1]]

    for axx, m, sd, ttl in [(ax, nbo_m, nbo_s, "(a) nbo test set"),
                            (ax2, pcu_m, pcu_s, "(b) pcu test set")]:
        x = np.arange(len(arms))
        axx.bar(x, m, yerr=sd, capsize=3, color="#1f77b4", edgecolor="white",
                linewidth=0.5)
        for xi, v in zip(x, m):
            axx.text(xi, v + sd[xi] + 0.004, f"{v:.4f}", ha="center", fontsize=7)
        axx.set_xticks(x); axx.set_xticklabels(arms)
        axx.set_xlabel("arm")
        axx.set_ylabel("MAE  [mmol/g]")
        axx.set_title(ttl, loc="left", fontsize=10)
        axx.grid(axis="y", alpha=0.3)

    pe = pd.read_csv(os.path.join(OUT, "followup_20261023", "experiment5", "paired_endpoints.csv"))
    cl = pd.read_csv(os.path.join(OUT, "followup_20261023", "experiment5",
                                  "cleaned_endpoint_summary.csv"))
    rows = [("nbo, historical", float(pe[(pe.target == "nbo") & (pe.subset == "all")].MAE_100_minus_0.iloc[0]),
             float(pe[(pe.target == "nbo") & (pe.subset == "all")].CI95_low.iloc[0]),
             float(pe[(pe.target == "nbo") & (pe.subset == "all")].CI95_high.iloc[0])),
            ("nbo, negatives removed", float(cl[cl.target == "nbo"].delta.iloc[0]),
             float(cl[cl.target == "nbo"].CI95_low.iloc[0]), float(cl[cl.target == "nbo"].CI95_high.iloc[0])),
            ("pcu, historical", float(pe[(pe.target == "pcu") & (pe.subset == "all")].MAE_100_minus_0.iloc[0]),
             float(pe[(pe.target == "pcu") & (pe.subset == "all")].CI95_low.iloc[0]),
             float(pe[(pe.target == "pcu") & (pe.subset == "all")].CI95_high.iloc[0])),
            ("pcu, negatives removed", float(cl[cl.target == "pcu"].delta.iloc[0]),
             float(cl[cl.target == "pcu"].CI95_low.iloc[0]), float(cl[cl.target == "pcu"].CI95_high.iloc[0]))]
    y = np.arange(len(rows))
    vals = [1000 * r[1] for r in rows]
    lo = [1000 * (r[1] - r[2]) for r in rows]
    hi = [1000 * (r[3] - r[1]) for r in rows]
    ax3.errorbar(vals, y, xerr=[lo, hi], fmt="o", ms=5, color="#d62728", capsize=3)
    ax3.axvline(0, color="gray", lw=0.8, ls="--")
    ax3.set_yticks(y); ax3.set_yticklabels([r[0] for r in rows], fontsize=7)
    ax3.set_xlabel("ΔMAE, 100% − 0% shared partner rows  [10⁻³ mmol/g]")
    ax3.set_title("(c) separate follow-up: replacement", loc="left", fontsize=9)
    ax3.grid(axis="x", alpha=0.3)
    save(fig, "Fig3_intervention")


# ---------------- Figure 4: screening ----------------
def figure4():
    seeds = [42, 143, 244, 345, 446]
    order = ["random", "chemistry", "linker_pair", "metal", "topology"]
    frames = []
    for sd in seeds:
        df = pd.read_csv(os.path.join(OUT, f"screening_utility_seed{sd}.csv"))
        df = df[df.k_frac == 0.01][["strategy", "overlap_at_k", "topk_true_mean", "oracle_topk_mean"]]
        frames.append(df.assign(seed=sd))
    allf = pd.concat(frames)
    g = allf.groupby("strategy")
    ov = {k: (g.get_group(k).overlap_at_k.mean(), g.get_group(k).overlap_at_k.std())
          for k in order}
    up = {k: g.get_group(k).topk_true_mean.mean() for k in order}
    up_sd = {k: g.get_group(k).topk_true_mean.std() for k in order}
    oracle_vals = allf.groupby("seed")["oracle_topk_mean"].first()
    oracle_mean, oracle_sd = float(oracle_vals.mean()), float(oracle_vals.std())

    fig = plt.figure(figsize=(6.85, 5.2))
    gs = fig.add_gridspec(2, 2)
    ax, ax2, ax3 = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, :])
    x = np.arange(len(order))
    m = [ov[k][0] * 100 for k in order]
    sd = [ov[k][1] * 100 for k in order]
    ax.bar(x, m, yerr=sd, capsize=3, color="#1f77b4", edgecolor="white", linewidth=0.5)
    rng = np.random.default_rng(0)
    tops = []
    for i, k in enumerate(order):
        vals_k = g.get_group(k).overlap_at_k.to_numpy() * 100
        jitter = rng.uniform(-0.12, 0.12, size=len(vals_k))
        ax.scatter(i + jitter, vals_k, s=10, color="#222222", zorder=5, alpha=0.85)
        tops.append(max(m[i] + sd[i], float(vals_k.max())))
    for xi, v, t in zip(x, m, tops):
        ax.text(xi, t + 2.0, f"{v:.1f}", ha="center", fontsize=7)
    ax.set_xticks(x); ax.set_xticklabels(order, rotation=20, ha="right")
    ax.set_ylabel("top-1% overlap  [%]")
    ax.set_title("(a) out-of-fold top-1% recovery", loc="left", fontsize=10)
    ax.grid(axis="y", alpha=0.3)

    ax2.bar(x, [up[k] for k in order], yerr=[up_sd[k] for k in order], capsize=3,
            color="#2ca02c", edgecolor="white", linewidth=0.5)
    ax2.axhline(oracle_mean, color="red", lw=1, ls="--")
    ax2.axhspan(oracle_mean - oracle_sd, oracle_mean + oracle_sd, color="red", alpha=0.12)
    ax2.text(len(order) - 0.5, oracle_mean + oracle_sd + 0.02,
             f"oracle {oracle_mean:.2f} ± {oracle_sd:.2f} (across seeds)",
             ha="right", fontsize=6.5, color="red")
    for xi, v in zip(x, [up[k] for k in order]):
        ax2.text(xi, v + up_sd[order[xi]] + 0.03, f"{v:.2f}", ha="center", fontsize=7)
    ax2.set_xticks(x); ax2.set_xticklabels(order, rotation=20, ha="right")
    ax2.set_ylabel("selected top-1% uptake\n[mmol/g]")
    ax2.set_title("(b) selected vs oracle uptake", loc="left", fontsize=10)
    ax2.grid(axis="y", alpha=0.3)

    # (c) fixed candidate pool, 5% budget, RF
    fs = pd.read_csv(os.path.join(OUT, "followup_20261023", "experiment6", "screening_summary.csv"))
    fs = fs[(fs.budget_fraction == 0.05) & (fs.model == "RF")]
    labels, vals, errs = [], [], []
    for target in ("nbo", "pcu"):
        for supp, slab in ((0, "0%"), (1, "100%")):
            for rep in ("G", "B", "I"):
                r = fs[(fs.target == target) & (fs.support == supp) & (fs.representation == rep)]
                if not len(r):
                    continue
                labels.append(f"{target}\n{rep}·{slab}")
                vals.append(100 * float(r.recovery_mean.iloc[0]))
                errs.append(100 * float(r.recovery_std.iloc[0]))
    xb = np.arange(len(labels))
    ax3.bar(xb, vals, yerr=errs, capsize=2, color="#9467bd", edgecolor="white", linewidth=0.4)
    for xi, v in zip(xb, vals):
        ax3.text(xi, v + 1.2, f"{v:.1f}", ha="center", fontsize=6.5, rotation=0)
    ax3.set_xticks(xb); ax3.set_xticklabels(labels, fontsize=6.5, rotation=0, ha="center")
    ax3.set_ylabel("recovery at 5%  [%]")
    ax3.set_ylim(0, 72)
    ax3.set_title("(c) fixed pool, 5% budget, RF", loc="left", fontsize=10)
    ax3.grid(axis="y", alpha=0.3)
    save(fig, "Fig4_screening")


# ---------------- Figure S8: ARC-MOF (SI) ----------------
def figureS8():
    null = pd.read_csv(os.path.join(OUT, "common_support", "null_topology_cardinality.csv"))
    # exclude the degenerate single-topology source (DB6)
    null = null[null["n_topologies"] > 1]

    fig = plt.figure(figsize=(6.85, 5.0))
    gs = fig.add_gridspec(2, 2)
    ax, ax2, ax3 = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, :])

    audit = pd.read_csv(os.path.join(OUT, "singleton_audit.csv"))
    nss = pd.read_csv(os.path.join(OUT, "arcmof_non_singleton_summary.csv"))
    a_arc = audit[audit["dataset"] == "ARC-MOF"].set_index("granularity")
    coarse_key = "metal_linker+organic_linker1"
    fine_key = "metal_linker+organic_linker1+functional_groups"
    s_arc = nss.set_index("key_definition")
    rows = [("coarse", "all", None), ("coarse", "non-sing.", coarse_key),
            ("fine", "all", None), ("fine", "non-sing.", fine_key)]
    vals = []
    for granularity, subset, key in rows:
        if key is None:
            v = 100.0 * float(a_arc.loc[granularity, "single_topology_all"])
        else:
            r = s_arc.loc[key]
            n_num = int(r["single_topology_non_singleton_count"])
            n_den = int(r["non_singleton_count"])
            assert n_num <= n_den, (key, n_num, n_den)
            assert abs(float(r["fraction"]) - n_num / n_den) < 1e-6, key
            v = 100.0 * n_num / n_den
        vals.append(v)
    labels = ["coarse\n(all)", "coarse\n(non-sing.)", "fine\n(all)", "fine\n(non-sing.)"]
    ax.bar(range(4), vals, color="#1f77b4", edgecolor="white", linewidth=0.5)
    for xi, v in zip(range(4), vals):
        ax.text(xi, v + 0.3, f"{v:.1f}", ha="center", fontsize=7)
    ax.set_xticks(range(4)); ax.set_xticklabels(labels)
    ax.tick_params(axis="x", labelsize=6.5)
    ax.set_ylabel("single-topology fraction  [%]")
    ax.set_ylim(0, 108)
    ax.set_title("(a) exclusivity by granularity", loc="left", fontsize=9)
    ax.grid(axis="y", alpha=0.3)

    ex = pd.read_csv(os.path.join(OUT, "confound_arcmof_excl_derived.csv"))
    base = ex[ex["subset"] == "全部（未剔除）"].set_index("granularity")
    rem = ex[ex["subset"].str.startswith("剔除")].copy()
    rem["db"] = rem["subset"].str.replace("剔除", "", regex=False).str.strip()
    rem = rem[rem["db"].str.match(r"^DB\d+$")]
    piv = rem.pivot(index="db", columns="granularity", values="frac_single_topology")
    piv = piv.dropna(subset=["coarse", "fine"]).sort_values("coarse")
    dbs = piv.index.tolist()
    xb = np.arange(len(dbs))
    base_c = float(base.loc["coarse", "frac_single_topology"]) * 100
    base_f = float(base.loc["fine", "frac_single_topology"]) * 100
    ax2.plot(xb, piv["coarse"].values * 100, "o-", color="#1f77b4", ms=4, lw=1, label="coarse")
    ax2.plot(xb, piv["fine"].values * 100, "s-", color="#ff7f0e", ms=4, lw=1, label="fine")
    ax2.axhline(base_c, color="#1f77b4", lw=0.7, ls="--")
    ax2.axhline(base_f, color="#ff7f0e", lw=0.7, ls="--")
    ax2.set_xticks(xb); ax2.set_xticklabels(dbs, rotation=45, ha="right", fontsize=6)
    ax2.set_ylabel("single-topology fraction  [%]")
    ax2.set_title("(b) leave-one-source-out", loc="left", fontsize=9)
    ax2.legend(fontsize=6, loc="lower right", frameon=True, framealpha=0.95)
    ax2.grid(axis="y", alpha=0.3)

    ax3.errorbar(null["null_mean"] * 100, null["observed"] * 100,
                 xerr=null["null_sd"] * 100, fmt="o", ms=4, color="#1f77b4", capsize=2)
    ax3.plot([50, 100], [50, 100], color="gray", lw=0.7, ls="--")
    ax3.set_xlabel("within-source permutation-null mean  [%]")
    ax3.set_ylabel("observed exclusivity  [%]")
    ax3.set_title("(c) observed vs null (DB6 excluded)", loc="left", fontsize=9)
    ax3.grid(alpha=0.3)
    save(fig, "figS8_arcmof")


# ---------------- Figure S7: S_g curve (SI) ----------------
def figureS7():
    sg = pd.read_csv(os.path.join(OUT, "s_g_curve.csv"))
    a = sg[sg.n_test >= 100].copy()

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(6.85, 3.4))
    ax.scatter(a.S_miss_unseen, a.R2_pooled, s=28, color="#1f77b4", zorder=3)
    saturated = a[a.S_miss_unseen >= 0.999]
    upper = saturated[saturated.R2_pooled >= 0].sort_values("R2_pooled")
    lower = saturated[saturated.R2_pooled < 0]
    for rank, (_, r) in enumerate(upper.iterrows()):
        ax.annotate(r.held_out_topology, (r.S_miss_unseen, r.R2_pooled),
                    textcoords="offset points",
                    xytext=(14, -12 + 9 * rank), fontsize=6.5,
                    arrowprops=dict(arrowstyle="-", lw=0.4, color="0.55",
                                    shrinkA=0, shrinkB=2))
    for _, r in lower.iterrows():
        ax.annotate(r.held_out_topology, (r.S_miss_unseen, r.R2_pooled),
                    textcoords="offset points", xytext=(10, 4), fontsize=6.5,
                    arrowprops=dict(arrowstyle="-", lw=0.4, color="0.55",
                                    shrinkA=0, shrinkB=2))
    for _, r in a[a.S_miss_unseen < 0.999].iterrows():
        ax.annotate(r.held_out_topology, (r.S_miss_unseen, r.R2_pooled),
                    textcoords="offset points", xytext=(5, 4), fontsize=6.5)
    ax.set_xlabel("S_miss (unseen-chemistry fraction)")
    ax.set_ylabel("held-out R²")
    ax.set_title("(a) S_g curve\n(n_test ≥ 100, 10 topologies)", loc="left", fontsize=9)
    ax.grid(alpha=0.3)

    b = sg.sort_values("n_test", ascending=False).reset_index(drop=True)
    xb = np.arange(len(b))
    ax2.bar(xb, b.sd_y_test, color="#2ca02c", edgecolor="white", linewidth=0.5)
    ax2.set_xticks(xb)
    ax2.set_xticklabels(b.held_out_topology, rotation=45, ha="right", fontsize=6.5)
    ax2.set_ylabel("sd(y) in fold  [mmol/g]")
    ax2.set_title("(b) target variation\nwithin held-out topologies", loc="left", fontsize=9)
    ax2.grid(axis="y", alpha=0.3)
    save(fig, "figS7_sg_curve")


# ---------------- Figure S4: across-seed dispersion (SI) ----------------
def figureS4():
    d = pd.read_csv(os.path.join(OUT, "multi_seed_uptake25k_fix.csv"))
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(6.85, 3.4))
    x = np.arange(len(d))
    w = 0.26
    rules = [("loto_pooled", "pooled (all folds merged)", "#1f77b4"),
             ("loto_median", "median over folds", "#2ca02c"),
             ("loto_macro", "macro (mean over folds)", "#d62728")]
    for i, (col, lab, c) in enumerate(rules):
        ax.bar(x + (i - 1) * w, d[col], w, color=c, edgecolor="white",
               linewidth=0.4, label=lab)
    ax.axhline(0.0, color="gray", lw=0.7, ls="--")
    ax.set_xticks(x)
    ax.set_xticklabels([f"seed {int(s)}" for s in d.seed])
    ax.set_ylim(-1.75, 0.62)
    ax.set_ylabel("leave-one-topology-out R²")
    ax.legend(loc="lower left", fontsize=6)
    ax.set_title("(a) same run, three aggregation rules", loc="left", fontsize=9)
    ax.grid(axis="y", alpha=0.3)

    spread = []
    for col, lab, c in rules:
        v = d[col].to_numpy(float)
        spread.append((lab, 100 * v.std(ddof=1) / abs(v.mean()), c))
    yb = np.arange(len(spread))
    ax2.barh(yb, [s[1] for s in spread], color=[s[2] for s in spread],
             edgecolor="white", linewidth=0.5)
    for yi, s in zip(yb, spread):
        ax2.text(s[1] + 2, yi, f"{s[1]:.0f}%", va="center", fontsize=7)
    ax2.set_yticks(yb)
    ax2.set_yticklabels(["pooled", "median\nover folds", "macro"], fontsize=6.5)
    ax2.set_xlim(0, 118)
    ax2.set_xlabel("across-seed dispersion  (sd / |mean|, %)")
    ax2.set_title("(b) across-seed dispersion\nby aggregation rule", loc="left", fontsize=9)
    ax2.grid(axis="x", alpha=0.3)
    fig.text(0.01, 0.01, "Five seeds, 25,000 samples each.", fontsize=6.5,
             color="#555555")
    save(fig, "figS4_aggregation_stability")


# ---------------- Figure S3: within vs cross R2 (SI) ----------------
def figureS3():
    d = pd.read_csv(os.path.join(OUT, "within_vs_cross_final.csv"))
    d = d.sort_values("n", ascending=False).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(6.85, 3.8))
    y = np.arange(len(d))[::-1]
    for yi, r in zip(y, d.itertuples()):
        ax.plot([r.R2_cross, r.R2_within], [yi, yi], color="#cfcfcf", lw=1.8, zorder=1)
        ax.scatter(r.R2_within, yi, s=34, color="#1f77b4", zorder=3)
        ax.scatter(r.R2_cross, yi, s=34, color="#c0392b", zorder=3)
    ax.axvline(0, color="gray", lw=0.7, ls=":")
    ax.set_yticks(y)
    ax.set_yticklabels([f"{r.topology} (n = {r.n:,})" for r in d.itertuples()],
                       fontsize=7)
    ax.set_xlabel("R² with the same eight geometric descriptors")
    ax.set_title("Within- versus cross-topology R²", loc="left", fontsize=9)
    ax.scatter([], [], s=34, color="#1f77b4", label="trained within the same topology")
    ax.scatter([], [], s=34, color="#c0392b", label="trained on other topologies")
    ax.legend(fontsize=6.5, loc="lower left")
    ax.grid(axis="x", alpha=0.3)
    save(fig, "figS3_within_vs_cross")


if __name__ == "__main__":
    figure1()
    figure2()
    figure3()
    figure4()
    figureS8()
    figureS3()
    figureS4()
    figureS7()
