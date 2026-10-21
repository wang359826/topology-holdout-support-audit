#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build the four main figures for Manuscript_v6 from archived CSVs.
Self-contained matplotlib; no pubfig dependency. Outputs PNG into
../01_manuscript/figures/ (relative to this file's package root)."""
import os
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

plt.rcParams.update({"font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150})


def save(fig, stem):
    p = os.path.join(DEST, stem)
    fig.savefig(p + ".png", bbox_inches="tight", dpi=150)
    fig.savefig(p + ".pdf", bbox_inches="tight")
    plt.close(fig)
    print("wrote", p + ".png")


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

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11, 4.4))
    x = np.arange(len(order))
    colors = ["#d62728" if v >= 99.9 else "#1f77b4" for v in vals]
    ax.bar(x, vals, color=colors, edgecolor="white", linewidth=0.5)
    for xi, v, t in zip(x, vals, order):
        n = int(frac_n.get(t, 0))
        nlab = f"{n/1000:.0f}k" if n >= 1000 else str(n)
        ax.text(xi, v + 1.5, f"{v:.0f}\nn={nlab}", ha="center", fontsize=6)
    ax.set_xticks(x); ax.set_xticklabels(order, rotation=45, ha="right")
    ax.set_ylabel("structures unseen after hold-out  [%]")
    ax.set_title("(a) per-topology chemical-support loss", loc="left", fontsize=10)
    ax.set_ylim(0, 125)
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


# ---------------- Figure 2: intervention ----------------
def figure2():
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

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10, 4.4))
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
    save(fig, "Fig2_intervention")


# ---------------- Figure 3: screening ----------------
def figure3():
    seeds = [42, 143, 244, 345, 446]
    strat_names = {"random": "random", "topology": "topology",
                   "chemistry": "chemistry key", "linker_pair": "linker pair",
                   "metal": "metal"}
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

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10, 4.4))
    x = np.arange(len(order))
    m = [ov[k][0] * 100 for k in order]
    sd = [ov[k][1] * 100 for k in order]
    ax.bar(x, m, yerr=sd, capsize=3, color="#1f77b4", edgecolor="white", linewidth=0.5)
    # per-seed paired points (same five seeds for every strategy)
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
    ax.set_title("(a) five-seed top-1% recovery", loc="left", fontsize=10)
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
    ax2.set_ylabel("mean uptake of selected top-1%  [mmol/g]")
    ax2.set_title("(b) selected vs oracle uptake (mean ± SD over seeds)", loc="left", fontsize=10)
    ax2.grid(axis="y", alpha=0.3)
    save(fig, "Fig3_screening")


# ---------------- Figure 4: ARC-MOF ----------------
def figure4():
    null = pd.read_csv(os.path.join(OUT, "common_support", "null_topology_cardinality.csv"))
    # exclude the degenerate single-topology source (DB6)
    null = null[null["n_topologies"] > 1]

    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2))
    ax, ax2, ax3 = axes

    # (a) single-topology fraction: full/non-singleton x coarse/fine (four bars).
    # Every value is read from the two archived audit tables; none is hard-coded,
    # so a change in the input propagates into the panel.
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

    # (b) leave-one-source-out: two point series (coarse/fine), one point per removed source
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
    # the DB0 removal is the lowest coarse point, so the legend goes to the
    # lower-right corner where the series are above it
    ax2.legend(fontsize=6, loc="lower right", frameon=True, framealpha=0.95)
    ax2.grid(axis="y", alpha=0.3)

    # (c) observed vs within-source permutation null (common support set, DB6 excluded)
    ax3.errorbar(null["null_mean"] * 100, null["observed"] * 100,
                 xerr=null["null_sd"] * 100, fmt="o", ms=4, color="#1f77b4", capsize=2)
    ax3.plot([50, 100], [50, 100], color="gray", lw=0.7, ls="--")
    ax3.set_xlabel("within-source permutation-null mean  [%]")
    ax3.set_ylabel("observed exclusivity  [%]")
    ax3.set_title("(c) observed vs null (DB6 excluded)", loc="left", fontsize=9)
    ax3.grid(alpha=0.3)
    save(fig, "Fig4_arcmof")


# ---------------- Figure S7: S_g curve (SI) ----------------
def figureS7():
    sg = pd.read_csv(os.path.join(OUT, "s_g_curve.csv"))
    a = sg[sg.n_test >= 100].copy()

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10, 4.2))
    # (a) S_miss vs held-out R2, restricted to n_test >= 100 (10 topologies)
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
    ax.set_title("(a) S_g curve (n_test ≥ 100, 10 topologies)", loc="left", fontsize=9)
    ax.grid(alpha=0.3)

    # (b) target variation within held-out topologies (all 11, by n_test desc)
    b = sg.sort_values("n_test", ascending=False).reset_index(drop=True)
    xb = np.arange(len(b))
    ax2.bar(xb, b.sd_y_test, color="#2ca02c", edgecolor="white", linewidth=0.5)
    ax2.set_xticks(xb)
    ax2.set_xticklabels(b.held_out_topology, rotation=45, ha="right", fontsize=6.5)
    ax2.set_ylabel("sd(y) in fold  [mmol/g]")
    ax2.set_title("(b) target variation within held-out topologies", loc="left", fontsize=9)
    ax2.grid(axis="y", alpha=0.3)
    save(fig, "figS7_sg_curve")


# ---------------- Figure S4: across-seed dispersion (SI) ----------------
def figureS4():
    d = pd.read_csv(os.path.join(OUT, "multi_seed_uptake25k_fix.csv"))
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10, 4.2))
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
    ax2.set_title("(b) across-seed dispersion by aggregation rule", loc="left", fontsize=9)
    ax2.grid(axis="x", alpha=0.3)
    fig.text(0.01, 0.01, "Five seeds, 25,000 samples each.", fontsize=6.5,
             color="#555555")
    save(fig, "figS4_aggregation_stability")


# ---------------- Figure S3: within vs cross R2 (SI) ----------------
def figureS3():
    d = pd.read_csv(os.path.join(OUT, "within_vs_cross_final.csv"))
    d = d.sort_values("n", ascending=False).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
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
    figureS3()
    figureS4()
    figureS7()
    print("done")
