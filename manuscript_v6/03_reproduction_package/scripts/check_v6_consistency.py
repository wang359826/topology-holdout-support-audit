#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""check_v6_consistency.py - pre-submission invariant check for the v6 package.

Run from anywhere; paths are resolved from this file:

    python scripts/check_v6_consistency.py            # failures + summary
    python scripts/check_v6_consistency.py -v         # every individual check
    python scripts/check_v6_consistency.py --no-pdf   # skip PDF-freshness checks

Why the v5 checker does not apply: v5 shipped 8 main figures named fig1..fig8,
a "## 7. Source data" section and no compressed 4-figure layout. This checker
targets the v6 layout (4 main figures named FigN_*, 7 SI figures named figSN_*,
sections up to "## 9. Declarations") and, unlike the v5 checker, it also
re-derives the numbers in Tables 1-3 and in the SI tables from the archived
CSVs. That last part is what catches the class of defect found in review
(Table 1 quoted a stale 0.6720 where the archive has 0.6674).

Exit code 0 means every check passed.
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from pathlib import Path

def _out(s=""):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001 - console may already be UTF-8
        pass
    print(s)


HERE = Path(__file__).resolve().parent
PKG = HERE.parent
ROOT = PKG.parent                     # .../03_投稿专用包_v6压缩
MANU = ROOT / "01_manuscript"
SI_DIR = ROOT / "02_supplementary"
FIGDIR = MANU / "figures"
OUT = PKG / "outputs"
MD = MANU / "Manuscript_v6.md"
SI = SI_DIR / "SI_v6.md"
MD_PDF = MANU / "Manuscript_v6.pdf"
SI_PDF = SI_DIR / "SI_v6.pdf"
BUILD = HERE / "build_pdf_v6.py"
MANIFEST = PKG / "FIGURE_MANIFEST.md"

N_MAIN_FIGS, N_MAIN_TABS = 4, 3
N_SI_FIGS, N_SI_TABS = 8, 25

FAILURES: list[str] = []
CHECKS = 0
VERBOSE = False


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def load_csv(name: str) -> list[dict]:
    """Read outputs/<name> as a list of dicts (utf-8-sig toleranted)."""
    path = OUT / name
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def fnum(cell: str):
    """'0.1065 ± 0.0032' -> (0.1065, 0.0032); '42,381' -> (42381.0, None)."""
    cell = cell.replace("\u2212", "-").replace("**", "").strip()
    nums = re.findall(r"[-+]?\d[\d,]*(?:\.\d+)?", cell)
    vals = [float(n.replace(",", "")) for n in nums]
    if not vals:
        return (float("nan"), None)
    return (vals[0], vals[1] if len(vals) > 1 else None)


def fmt(v: float, nd: int) -> str:
    s = f"{abs(v):.{nd}f}"
    return ("-" if v < 0 else "+") + s if nd == 4 and False else s


def ok(label: str, passed: bool, detail: str = "") -> bool:
    global CHECKS
    CHECKS += 1
    if passed:
        if VERBOSE:
            _out(f"  ok   {label}")
        return True
    FAILURES.append(f"{label}{(' :: ' + detail) if detail else ''}")
    _out(f"  FAIL {label}{(' :: ' + detail) if detail else ''}")
    return False


def close(a, b, tol=5e-4) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


def tables(text: str) -> list[tuple[list[str], list[list[str]]]]:
    """Return [(header_cells, [row_cells, ...]), ...] for every pipe table."""
    lines = text.split("\n")
    out, i = [], 0
    while i < len(lines):
        if lines[i].strip().startswith("|") and i + 1 < len(lines) and set(
                lines[i + 1].strip().replace("|", "").replace(":", "")
                .replace(" ", "")) <= {"-"} and "-" in lines[i + 1]:
            header = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            out.append((header, rows))
        else:
            i += 1
    return out


def find_table(text: str, first_header: str):
    for header, rows in tables(text):
        if header and header[0].lower().startswith(first_header.lower()):
            return header, rows
    return None, None


def section(text: str, start_pat: str, end_pat: str) -> str:
    m = re.search(start_pat, text, re.S | re.M)
    if not m:
        return ""
    tail = text[m.end():]
    m2 = re.search(end_pat, tail, re.S | re.M)
    return tail[: m2.start()] if m2 else tail


# --------------------------------------------------------------------------
# 0. files and PDF freshness
# --------------------------------------------------------------------------
def check_layout(no_pdf: bool):
    _out("\n[0] files and PDF freshness")
    for p in (MD, SI, BUILD, MANIFEST, FIGDIR):
        ok(f"exists {p.name}", p.exists(), str(p))
    if not (MD.exists() and SI.exists()):
        return
    if no_pdf:
        _out("  (skipped by --no-pdf)")
        return
    for src, pdf in ((MD, MD_PDF), (SI, SI_PDF)):
        if not pdf.exists():
            ok(f"{pdf.name} present", False, "rebuild with build_pdf_v6.py")
            continue
        src_m, pdf_m = src.stat().st_mtime, pdf.stat().st_mtime
        ok(f"{pdf.name} newer than {src.name}", pdf_m >= src_m,
           f"PDF {pdf_m:.0f} < MD {src_m:.0f} - rebuild needed")
        ok(f"{pdf.name} size sane", pdf.stat().st_size > 100_000,
           f"{pdf.stat().st_size} bytes")


# --------------------------------------------------------------------------
# 1. abstract, numbering, cross references, citations
# --------------------------------------------------------------------------
def check_text():
    _out("\n[1] abstract, numbering, cross references, citations")
    md, si = read(MD), read(SI)

    m = re.search(r"##\s*Abstract(.*?)\*\*Keywords", md, re.S)
    n_abs = len(re.findall(r"\S+", m.group(1))) if m else 0
    ok(f"abstract words {n_abs} <= 250", 0 < n_abs <= 250, str(n_abs))

    caps = [int(x) for x in re.findall(r"^\*\*Figure (\d+)\.\*\*", md, re.M)]
    ok(f"main figure captions 1..{N_MAIN_FIGS}", caps == list(range(1, N_MAIN_FIGS + 1)),
       str(caps))
    tcaps = [int(x) for x in re.findall(r"^\*\*Table (\d+)\.\*\*", md, re.M)]
    ok(f"main table captions 1..{N_MAIN_TABS}", tcaps == list(range(1, N_MAIN_TABS + 1)),
       str(tcaps))

    body_end = md.find("## 6. Figure captions")
    body = md[:body_end if body_end > 0 else len(md)]
    order = []
    for mm in re.finditer(r"\bFigure\s+(\d+)", body):
        v = int(mm.group(1))
        if v not in order:
            order.append(v)
    ok("first mention of figures is ascending", order == sorted(order), str(order))
    ok("no figure reference beyond the 4-figure set",
       all(1 <= v <= N_MAIN_FIGS for v in order), str(order))
    tabs_used = sorted({int(x) for x in re.findall(r"\bTable\s+(\d+)", body)})
    ok("no table reference beyond Table 3",
       all(1 <= v <= N_MAIN_TABS for v in tabs_used), str(tabs_used))

    # references <-> citations
    ref_start = md.find("## 8. References")
    if ref_start > 0:
        tail = md[ref_start:]
        refs = [int(x) for x in re.findall(r"^(\d+)\.\s", tail, re.M)]
        cited = set()
        for t in re.findall(r"refs?\.\s*[0-9]+(?:\s*[,\u2013-]\s*[0-9]+)*", body):
            # "refs. 18-20" is a range; "refs. 17, 26" is two single citations.
            for part in re.split(r"\s*,\s*", t.split(".", 1)[1].strip()):
                if re.search(r"[\u2013-]", part):
                    a, b = [int(x) for x in re.findall(r"\d+", part)][:2]
                    if b >= a:
                        cited.update(range(a, b + 1))
                    continue
                cited.update(int(x) for x in re.findall(r"\d+", part))
        uncited = sorted(set(refs) - cited)
        dangling = sorted(cited - set(refs))
        ok(f"references closed ({len(refs)} entries)", not uncited and not dangling,
           f"uncited={uncited} dangling={dangling}")
        ok("refs numbered 1..N without gaps", refs == list(range(1, len(refs) + 1)),
           str(refs[:5]))

    # main -> SI cross references
    si_t = {int(x) for x in re.findall(r"\*\*Table S(\d+)\.\*\*", si)}
    si_f = {int(x) for x in re.findall(r"\*\*Figure S(\d+)\.\*\*", si)}
    ok(f"SI tables numbered 1..{N_SI_TABS}", si_t == set(range(1, N_SI_TABS + 1)),
       str(sorted(si_t)))
    ok(f"SI figures numbered 1..{N_SI_FIGS}", si_f == set(range(1, N_SI_FIGS + 1)),
       str(sorted(si_f)))
    used_t = {int(x) for x in re.findall(r"Table S(\d+)", md)}
    used_f = {int(x) for x in re.findall(r"Figure S(\d+)", md)}
    ok("main-text references to SI tables exist", used_t <= si_t, str(sorted(used_t - si_t)))
    ok("main-text references to SI figures exist", used_f <= si_f, str(sorted(used_f - si_f)))
    # every SI table/figure must be reachable from the main text or from the SI itself
    reach = used_t | {int(x) for x in re.findall(r"Table S(\d+)", si)}
    ok("every SI table is referenced", si_t <= reach, str(sorted(si_t - reach)))
    section_refs = {s for s in re.findall(r"SI-[A-I]\b", md)}
    si_sections = {f"SI-{s}" for s in re.findall(r"^##\s*SI-([A-I])\.", si, re.M)}
    ok("SI section references exist", section_refs <= si_sections,
       str(sorted(section_refs - si_sections)))

    # stale numbering: the compressed paper has 4 figures / 3 tables, so any
    # reference to a higher main-text number ("Table 8", "Figure 5") is a
    # leftover of the superseded 8-figure layout
    stale = sorted({int(x) for x in re.findall(r"\bTable (\d+)", md + si)} -
                   set(range(1, N_MAIN_TABS + 1)))
    ok("no reference to a non-existent main-text table", not stale, str(stale))
    stale_f = sorted({int(x) for x in re.findall(r"\bFigure (\d+)", md + si)} -
                     set(range(1, N_MAIN_FIGS + 1)))
    ok("no reference to a non-existent main-text figure", not stale_f, str(stale_f))
    stale_si_t = sorted({int(x) for x in re.findall(r"Table S(\d+)", md + si)} -
                        set(range(1, N_SI_TABS + 1)))
    ok("no reference to a non-existent SI table", not stale_si_t, str(stale_si_t))
    stale_si_f = sorted({int(x) for x in re.findall(r"Figure S(\d+)", md + si)} -
                        set(range(1, N_SI_FIGS + 1)))
    ok("no reference to a non-existent SI figure", not stale_si_f, str(stale_si_f))

    # placeholder / escape litter
    bad = {}
    for name, pat in {"@@": r"@@", "TODO": r"TODO\(", "ellipsis": r"\[\.\.\.\]"}.items():
        n = len(re.findall(pat, md + si))
        if n:
            bad[name] = n
    ok("no placeholder markers", not bad, str(bad))
    # H(T\|C) inside a table cell legitimately escapes the pipe, so only
    # leftover escaped asterisks indicate markdown escaping litter
    ok("no escaped bold markers left", not re.search(r"\\\*\\\*", md + si))


def check_enumeration():
    """Cross-document consistency of the six follow-ups, arm (g) and the deposit.

    Review 2026-10-24: the abstract enumerated seven follow-ups, SI-2.7 six,
    and the cover letter a third set of six; arm (g) was used in 3.3 but never
    defined in 2.4. These checks pin the canonical enumeration in every place
    that states it.
    """
    _out("\n[1b] follow-up enumeration, arm (g), deposit")
    md, si = read(MD), read(SI)
    cl_path = ROOT / "04_cover_letter" / "Cover_Letter_v6.md"
    cl = read(cl_path) if cl_path.exists() else ""
    # the cover letter and SI are hard-wrapped, so match on flattened whitespace
    flat = lambda s: re.sub(r"\s+", " ", s)
    md_s, si_s, cl_s = flat(md), flat(si), flat(cl)
    six = ("(1) representation, (2) constituent novelty, (3) CoRE structural feasibility, "
           "(4) fold-level support diagnostics, (5) matched partner replacement and "
           "(6) fixed-pool screening")
    ok("2.7 enumerates the canonical six", six in md_s)
    ok("2.7 says ARC-MOF is not one of the six",
       "The ARC-MOF audit is not one of the six" in md_s)
    abstract_match = re.search(r"##\s*Abstract(.*?)\*\*Keywords", md, re.S)
    abstract = abstract_match.group(1).strip() if abstract_match else ""
    sentences = [x for x in re.split(r"(?<=[.!?])\s+(?=[A-Z])", abstract) if x.strip()]
    ok("abstract has 3-4 sentences", 3 <= len(sentences) <= 4, str(len(sentences)))
    ok("abstract does not call ARC-MOF independent", not re.search(r"independent\s+(?:ARC-MOF|replication)", abstract, re.I))
    ok("conclusion names the same six",
       "representation, constituent novelty, CoRE feasibility, fold-level diagnostics, "
       "matched replacement and fixed-pool screening (SI-I)" in md_s)
    ok("cover letter names the same six",
       (not cl) or ("representation, constituent novelty, CoRE feasibility, fold-level "
                    "diagnostics, matched replacement and fixed-pool screening" in cl_s),
       "cover letter not shipped in this distribution" if not cl
       else "cover letter missing the canonical list")
    si_intro = re.search(r"## SI-I\..*?(?=### SI-I\.1)", si_s)
    si_intro = si_intro.group(0) if si_intro else ""
    ok("SI-I keeps ARC-MOF outside the six",
       bool(re.search(r"Six follow-up experiments", si_intro, re.I)) and
       bool(re.search(r"ARC-MOF.{0,90}(?:separate|not one of the six).{0,50}SI-H", si_intro, re.I)))
    ok("2.4 defines post hoc arm (g)", "A seventh arm, **(g)**, is post hoc" in md_s)
    ok("SI-C.1 mentions the post hoc arm (g)", "post hoc arm (g)" in si_s)
    ok("Fig. 3 panel (c) labelled a separate design",
       "not an arm of the a–g contrast" in md_s)
    ok("single-pair/single-library limit sits in 3.3",
       "Two boundaries belong to this result" in md_s)
    ok("main and SI name the fixed v1.4 DOI",
       "10.5281/zenodo.23618746" in md_s and "10.5281/zenodo.23618746" in si_s)
    v13_scope = r"v1\.3.{0,90}(?:contain(?:s|ing)?|cover(?:s|ing)?).{0,20}original analyses only"
    ok("v1.3 labelled original-analyses-only in main and SI",
       bool(re.search(v13_scope, md_s, re.I)) and bool(re.search(v13_scope, si_s, re.I)))
    # Public accessibility of this exact commit was checked independently.
    # This assertion checks citation consistency, not live network reachability.
    public_commit = "https://github.com/wang359826/topology-holdout-support-audit/tree/80bd0bc1046cedd3f8eb7069c1bc1acc8b0a5dc7"
    ok("main and SI identify the verified public correction commit",
       public_commit in md_s and public_commit in si_s and
       "not yet archived as a new public release" not in md_s and
       "not yet archived as a new public release" not in si_s)


def check_figures():
    _out("\n[2] figure files, manifest and PDF map")
    build = read(BUILD)
    fmap = {}
    for num, name in re.findall(r"^\s+(\d+):\s+\"([^\"]+)\"", build, re.M):
        # only the main-text FIG_MAP block (SI names start with figS)
        if not name.startswith("figS"):
            fmap[int(num)] = name
    ok(f"build_pdf_v6 FIG_MAP covers 1..{N_MAIN_FIGS}",
       set(fmap) == set(range(1, N_MAIN_FIGS + 1)), str(fmap))
    for num, name in sorted(fmap.items()):
        ok(f"Fig {num} file exists ({name})", (FIGDIR / name).exists())
    fmap_si = {int(n): f for n, f in re.findall(r"^\s+(\d+):\s+\"(figS[^\"]+)\"", build, re.M)}
    ok(f"build_pdf_v6 FIG_MAP_SI covers 1..{N_SI_FIGS}",
       set(fmap_si) == set(range(1, N_SI_FIGS + 1)), str(sorted(fmap_si)))
    for num, name in sorted(fmap_si.items()):
        ok(f"Fig S{num} file exists ({name})", (FIGDIR / name).exists())

    manifest = read(MANIFEST)
    listed = set(re.findall(r"`(Fig\d+_[^`]+\.png|figS\d+_[^`]+\.png)`", manifest))
    on_disk = {p.name for p in FIGDIR.glob("*.png")} - {"TOC_graphic.png"}
    ok("FIGURE_MANIFEST lists every figure PNG", listed == on_disk,
       f"missing={sorted(on_disk - listed)} extra={sorted(listed - on_disk)}")
    toc = FIGDIR / "TOC_graphic.png"
    if not toc.exists():
        ok("TOC graphic present", False)
    else:
        try:
            from PIL import Image  # optional: skip the pixel check without Pillow
        except ImportError:
            if VERBOSE:
                _out("  skip TOC pixel size (Pillow not installed)")
        else:
            with Image.open(toc) as im:
                ok("TOC graphic is 975x525 px", im.size == (975, 525), str(im.size))
    legacy = [p.name for p in FIGDIR.glob("*.png")
              if re.match(r"fig[1-8]_", p.name)]
    ok("no superseded 8-figure main-text files", not legacy, str(legacy))


# --------------------------------------------------------------------------
# 3. numbers: main tables
# --------------------------------------------------------------------------
STRAT = {"random": "随机划分", "topology": "按拓扑分组",
         "metal": "按金属中心", "linker_pair": "按有机连接体",
         "chemistry": "按化学组成"}


def _by_strategy(rows, key="R2", prefix=None):
    out = {}
    for name, short in STRAT.items():
        for r in rows:
            s = r["strategy"]
            if s.startswith(short) and (prefix is None or prefix in s):
                out[name] = float(r[key])
    return out


def check_main_tables():
    _out("\n[3] main-text tables vs archived CSVs")
    md = read(MD)

    final = _by_strategy(load_csv("leakage_results_final.csv"))
    chem = _by_strategy(load_csv("leakage_results_chemistry.csv"))
    notopo = _by_strategy(load_csv("leakage_results_notopo100k.csv"))
    chem.update({k: v for k, v in _by_strategy(load_csv("leakage_results_chemistry.csv")).items()
                 if k == "chemistry"})

    header, rows = find_table(md, "Scheme")
    if header is None:
        ok("Table 1 Panel A found", False)
    else:
        got = {r[0].strip().lower(): (fnum(r[1]), fnum(r[2])) for r in rows if len(r) >= 3}
        want = {
            "random": (final["random"], notopo["random"]),
            "chemistry key": (chem["chemistry"], notopo["chemistry"]),
            "linker pair": (final["linker_pair"], None),
            "metal": (final["metal"], None),
            "topology (groupkfold)": (final["topology"], notopo["topology"]),
        }
        for label, (v426, v415) in want.items():
            g = got.get(label)
            ok(f"Table 1A {label} 426f", g is not None and close(g[0][0], v426, 6e-5),
               f"text={g[0][0] if g else None} csv={v426:.4f}")
            if v415 is not None:
                ok(f"Table 1A {label} 415f", g is not None and close(g[1][0], v415, 6e-5),
                   f"text={g[1][0] if g else None} csv={v415:.4f}")

    agg = load_csv("loto_aggregates_100k.csv")[0]
    header, rows = find_table(md, "Aggregation")
    if header is None:
        ok("Table 1 Panel B found", False)
    else:
        cells = [fnum(c)[0] for c in rows[0][1:]]
        for got, key in zip(cells, ["pooled", "weighted", "macro", "median"]):
            ok(f"Table 1B {key}", close(got, float(agg[key]), 6e-5),
               f"text={got} csv={float(agg[key]):.4f}")

    # ---- Table 2: five-seed means from the three archived arms ----
    iso = load_csv("isoreticular_control_seeds.csv")
    comp = load_csv("composition_matched_control.csv")
    arm_e = load_csv("arm_e_partner_coverage.csv")

    def mean_sd(vals):
        n = len(vals)
        m = sum(vals) / n
        sd = (sum((v - m) ** 2 for v in vals) / (n - 1)) ** 0.5
        return m, sd

    def arms(test):
        out = {}
        for arm, reg in (("a", "with_pair"), ("b", "without_pair")):
            sel = [r for r in iso if r["test_topo"] == test and r["regime"] == reg]
            out[arm] = dict(
                n_train=mean_sd([float(r["n_train"]) for r in sel])[0],
                MAE=mean_sd([float(r["MAE"]) for r in sel]),
                RMSE=mean_sd([float(r["RMSE"]) for r in sel]),
            )
        for arm, reg in (("e", "e_shared_only_removed"), ("f", "f_size_matched_from_e")):
            sel = [r for r in arm_e if r["test_topo"] == test and r["regime"] == reg]
            out[arm] = dict(
                n_train=mean_sd([float(r["n_train"]) for r in sel])[0],
                MAE=mean_sd([float(r["MAE"]) for r in sel]),
                RMSE=mean_sd([float(r["RMSE"]) for r in sel]),
            )
        # nested (c): mean of each seed's five inner draws, then mean/SD over seeds
        per_seed = {}
        for r in comp:
            if r["test_topo"] == test and r["regime"].startswith("size_matched_seed"):
                per_seed.setdefault(r["seed"], []).append(float(r["MAE"]))
        seed_means = [sum(v) / len(v) for v in per_seed.values()]
        out["c"] = dict(
            n_train=mean_sd([float(r["n_train"]) for r in comp
                             if r["test_topo"] == test
                             and r["regime"].startswith("size_matched_seed")])[0],
            MAE=mean_sd(seed_means), RMSE=None)
        return out

    header, rows = find_table(md, "Test")
    if header is None:
        ok("Table 2 found", False)
        return
    for r in rows:
        if len(r) < 5:
            continue
        test, arm_label = r[0].strip(), r[1].strip()
        arm = arm_label.split()[0].strip("(").lower()
        if test not in ("nbo", "pcu") or arm not in "abcef":
            continue
        ref = arms(test)[arm]
        n_txt = fnum(r[2])[0]
        ok(f"Table 2 {test} {arm} n_train", close(n_txt, ref["n_train"], 1.0),
           f"text={n_txt:.0f} csv={ref['n_train']:.1f}")
        mae_txt, mae_sd = fnum(r[3])
        ok(f"Table 2 {test} {arm} MAE", close(mae_txt, ref["MAE"][0], 6e-5)
           and (ref["MAE"][1] is None or close(mae_sd, ref["MAE"][1], 6e-5)),
           f"text={mae_txt}+-{mae_sd} csv={ref['MAE'][0]:.4f}+-{ref['MAE'][1]:.4f}")
        if ref["RMSE"] is not None and r[4].strip() not in ("—", "-", ""):
            rm_txt, rm_sd = fnum(r[4])
            ok(f"Table 2 {test} {arm} RMSE", close(rm_txt, ref["RMSE"][0], 6e-5)
               and (rm_sd is None or close(rm_sd, ref["RMSE"][1], 6e-5)),
               f"text={rm_txt}+-{rm_sd} csv={ref['RMSE'][0]:.4f}+-{ref['RMSE'][1]:.4f}")

    # ---- Table 3 ----
    sa = {(r["dataset"], r["granularity"]): r for r in load_csv("singleton_audit.csv")}
    header, rows = find_table(md, "granularity")
    if header is None:
        ok("Table 3 found", False)
    else:
        for r in rows:
            gran = r[0].strip().lower()
            ref = sa.get(("ARC-MOF", gran))
            if ref is None:
                continue
            ok(f"Table 3 {gran} N", close(fnum(r[1])[0], float(ref["N"]), 0.5),
               f"text={r[1]} csv={ref['N']}")
            ok(f"Table 3 {gran} M", close(fnum(r[2])[0], float(ref["M"]), 0.5),
               f"text={r[2]} csv={ref['M']}")
            ok(f"Table 3 {gran} non-singleton count",
               close(fnum(r[3])[0], float(ref["n_non_singleton"]), 0.5),
               f"text={r[3]} csv={ref['n_non_singleton']}")
            ok(f"Table 3 {gran} single-topology %",
               close(fnum(r[4])[0], 100 * float(ref["single_topology_all"]), 0.06),
               f"text={r[4]} csv={100 * float(ref['single_topology_all']):.2f}")
            ok(f"Table 3 {gran} non-singleton %",
               close(fnum(r[5])[0], 100 * float(ref["single_topology_non_singleton"]), 0.06),
               f"text={r[5]} csv={100 * float(ref['single_topology_non_singleton']):.2f}")


# --------------------------------------------------------------------------
# 4. numbers: SI tables
# --------------------------------------------------------------------------
def check_si_tables():
    _out("\n[4] SI tables vs archived CSVs")
    si = read(SI)

    # Table S1: per-topology support loss
    seen = {(r["granularity"].split("(")[0], r["held_out_topology"]): r
            for r in load_csv("chemistry_seen_by_topology.csv")}
    header, rows = find_table(si, "Held-out topology")
    if header is None:
        ok("Table S1 found", False)
    else:
        for r in rows:
            topo = r[0].strip()
            ref = seen.get(("coarse", topo))
            if ref is None:
                continue
            ok(f"S1 {topo} n", close(fnum(r[1])[0], float(ref["n_samples"]), 0.5))
            ok(f"S1 {topo} seen", close(fnum(r[2])[0], float(ref["S_g_seen_fraction"]), 6e-4),
               f"text={r[2]} csv={float(ref['S_g_seen_fraction']):.3f}")
            ok(f"S1 {topo} unseen", close(fnum(r[3])[0], float(ref["unseen_fraction"]), 6e-4),
               f"text={r[3]} csv={float(ref['unseen_fraction']):.3f}")

    # Table S2: multi-topology arithmetic from confound_full
    cf = {(r["granularity"].split("(")[0], "cf"): r for r in load_csv("confound_full.csv")}
    header, rows = find_table(si, "Granularity")
    if header is None:
        ok("Table S2 found", False)
    else:
        jac = load_csv("jaccard_full.csv")
        for r in rows:
            gran = "coarse" if "coarse" in r[0].lower() else "fine"
            ref = cf[(gran, "cf")]
            M = float(ref["n_chem"])
            frac = float(ref["frac_single_topology"])
            multi = round(M * (1 - frac))
            ok(f"S2 {gran} M", close(fnum(r[1])[0], M, 0.5), f"text={r[1]} csv={M:.0f}")
            ok(f"S2 {gran} multi-topology count", close(fnum(r[2])[0], multi, 0.5),
               f"text={r[2]} csv={multi}")
            ok(f"S2 {gran} share of M", close(fnum(r[3])[0], 100 * (1 - frac), 0.06),
               f"text={r[3]} csv={100 * (1 - frac):.1f}")

    # Table S3: S_g curve
    sg = {r["held_out_topology"]: r for r in load_csv("s_g_curve.csv")}
    header, rows = find_table(si, "Held-out topology")
    # the S1 table also starts that way; pick the one with 6 columns
    header, rows = next(((h, rr) for h, rr in tables(si)
                         if h and h[0].startswith("Held-out topology") and len(h) == 6),
                        (None, None))
    if header is None:
        ok("Table S3 found", False)
    else:
        for r in rows:
            ref = sg.get(r[0].strip())
            if ref is None:
                continue
            ok(f"S3 {r[0]} n_test", close(fnum(r[1])[0], float(ref["n_test"]), 0.5))
            ok(f"S3 {r[0]} S_miss", close(fnum(r[2])[0], float(ref["S_miss_unseen"]), 6e-4),
               f"text={r[2]} csv={float(ref['S_miss_unseen']):.3f}")
            ok(f"S3 {r[0]} r", close(fnum(r[3])[0], float(ref["r_train"]), 0.06))
            ok(f"S3 {r[0]} sd_y", close(fnum(r[4])[0], float(ref["sd_y_test"]), 6e-4))
            ok(f"S3 {r[0]} R2", close(fnum(r[5])[0], float(ref["R2_pooled"]), 6e-3),
               f"text={r[5]} csv={float(ref['R2_pooled']):.3f}")

    # Tables S4/S5: seed-42 arms
    ae42 = [r for r in load_csv("arm_e_partner_coverage.csv") if r["seed"] == "42"]
    h4, r4 = next(((h, rr) for h, rr in tables(si)
                   if h and h[0].startswith("Test topology") and "MAE/sd" in h), (None, None))
    if h4 is None:
        ok("Table S4 found", False)
    else:
        for r in r4:
            test = r[0].split()[0].strip("**(")
            reg = "b_partner_removed" if "removed" in r[1].lower() else "a_with_partner"
            ref = [x for x in ae42 if x["test_topo"] == test and x["regime"] == reg]
            if not ref:
                continue
            ref = ref[0]
            ok(f"S4 {test} {reg} n_train", close(fnum(r[2])[0], float(ref["n_train"]), 0.5))
            ok(f"S4 {test} {reg} MAE", close(fnum(r[4])[0], float(ref["MAE"]), 6e-5),
               f"text={r[4]} csv={float(ref['MAE']):.4f}")

    h5, r5 = next(((h, rr) for h, rr in tables(si) if h and "n_shared_removed" in h),
                  (None, None))
    if h5 is None:
        ok("Table S5 found", False)
    else:
        for r in r5:
            test = r[0].strip().strip("**")
            label = r[1].lower()
            if label.startswith("(a)"):
                reg = "a_with_partner"
            elif label.startswith("(b)"):
                reg = "b_partner_removed"
            elif label.startswith("(e)"):
                reg = "e_shared_only_removed"
            else:
                reg = "f_size_matched_from_e"
            ref = [x for x in ae42 if x["test_topo"] == test and x["regime"] == reg]
            if not ref:
                continue
            ref = ref[0]
            ok(f"S5 {test} {reg} n_train", close(fnum(r[2])[0], float(ref["n_train"]), 0.5),
               f"text={r[2]} csv={ref['n_train']}")
            ok(f"S5 {test} {reg} MAE", close(fnum(r[3])[0], float(ref["MAE"]), 6e-5),
               f"text={r[3]} csv={float(ref['MAE']):.4f}")
            ok(f"S5 {test} {reg} RMSE", close(fnum(r[4])[0], float(ref["RMSE"]), 6e-5),
               f"text={r[4]} csv={float(ref['RMSE']):.4f}")
            ok(f"S5 {test} {reg} R2", close(fnum(r[5])[0], float(ref["R2"]), 6e-4),
               f"text={r[5]} csv={float(ref['R2']):.4f}")
            if r[6].strip() not in ("—", "-", ""):
                ok(f"S5 {test} {reg} rows removed",
                   close(fnum(r[6])[0], float(ref["n_rows_removed_vs_a"]), 0.5),
                   f"text={r[6]} csv={ref['n_rows_removed_vs_a']}")
            ok(f"S5 {test} {reg} n_compositions",
               close(fnum(r[7])[0], float(ref["n_compositions"]), 0.5),
               f"text={r[7]} csv={ref['n_compositions']}")

    # Table S6: per-seed MAE
    iso = load_csv("isoreticular_control_seeds.csv")
    comp = load_csv("composition_matched_control.csv")
    arm_e = load_csv("arm_e_partner_coverage.csv")
    h6, r6 = next(((h, rr) for h, rr in tables(si)
                   if h and "c (nested)" in " ".join(h)), (None, None))
    if h6 is None:
        ok("Table S6 found", False)
    else:
        for r in r6:
            test, seed = r[0].strip(), r[1].strip()
            want = {}
            for arm, reg in (("a", "with_pair"), ("b", "without_pair")):
                sel = [x for x in iso if x["test_topo"] == test
                       and x["seed"] == seed and x["regime"] == reg]
                if sel:
                    want[arm] = float(sel[0]["MAE"])
            for arm, reg in (("e", "e_shared_only_removed"), ("f", "f_size_matched_from_e")):
                sel = [x for x in arm_e if x["test_topo"] == test
                       and x["seed"] == seed and x["regime"] == reg]
                if sel:
                    want[arm] = float(sel[0]["MAE"])
            inner = [float(x["MAE"]) for x in comp if x["test_topo"] == test
                     and x["seed"] == seed and x["regime"].startswith("size_matched_seed")]
            if inner:
                want["c"] = sum(inner) / len(inner)
            for arm, col in (("a", 2), ("b", 3), ("c", 4), ("e", 5), ("f", 6)):
                if arm in want:
                    ok(f"S6 {test} {seed} arm {arm}",
                       close(fnum(r[col])[0], want[arm], 6e-5),
                       f"text={r[col]} csv={want[arm]:.4f}")

    # Table S7: training-mean baseline
    base = {(r["test_topo"], r["arm"]): r
            for r in load_csv("baseline/training_mean_baseline_summary.csv")}
    h7, r7 = next(((h, rr) for h, rr in tables(si)
                   if h and h[0].startswith("Test topology")
                   and "training-mean" in " ".join(h).lower()), (None, None))
    if h7 is None:
        ok("Table S7 found", False)
    else:
        for r in r7:
            test = r[0].strip()
            arm = r[1].strip()[0]
            ref = base.get((test, arm))
            if ref is None:
                continue
            got, got_sd = fnum(r[2])
            ok(f"S7 {test} {arm}", close(got, float(ref["baseline_MAE_over_sd_mean"]), 6e-4)
               and close(got_sd, float(ref["baseline_MAE_over_sd_sd"]), 6e-4),
               f"text={r[2]} csv={float(ref['baseline_MAE_over_sd_mean']):.3f}+-"
               f"{float(ref['baseline_MAE_over_sd_sd']):.3f}")

    # Table S8: per-fold LOTO metrics
    loto = {r["group"]: r for r in load_csv("loto_per_topology_metrics_100k.csv")}
    h8, r8 = next(((h, rr) for h, rr in tables(si)
                   if h and h[0].startswith("Held-out topology") and "per-topology" in " ".join(h)),
                  (None, None))
    if h8 is None:
        ok("Table S8 found", False)
    else:
        for r in r8:
            ref = loto.get(r[0].strip())
            if ref is None:
                continue
            ok(f"S8 {r[0]} n_test", close(fnum(r[1])[0], float(ref["n_test"]), 0.5))
            ok(f"S8 {r[0]} MAE", close(fnum(r[2])[0], float(ref["MAE"]), 6e-5),
               f"text={r[2]} csv={float(ref['MAE']):.4f}")
            ok(f"S8 {r[0]} RMSE", close(fnum(r[3])[0], float(ref["RMSE"]), 6e-5))
            ok(f"S8 {r[0]} R2", close(fnum(r[4])[0], float(ref["R2"]), 6e-4),
               f"text={r[4]} csv={float(ref['R2']):.3f}")

    # Table S9: 25k five-seed aggregates
    a25 = {r["seed"]: r for r in load_csv("loto_aggregates_25k.csv")}
    h9, r9 = next(((h, rr) for h, rr in tables(si)
                   if h and h[0] == "seed" and "covered" in h), (None, None))
    if h9 is None:
        ok("Table S9 found", False)
    else:
        for r in r9:
            ref = a25.get(r[0].strip())
            if ref is None:
                continue
            for col, key, tol in ((1, "design_n", 0.5), (2, "pooled", 6e-4), (3, "weighted", 6e-4),
                                  (4, "macro", 6e-4), (5, "median", 6e-4),
                                  (6, "n_valid_folds", 0.5), (7, "n_covered", 0.5)):
                want = 25000.0 if key == "design_n" else float(
                    ref["n_valid_folds"] if key == "n_valid_folds" else
                    ref["n_covered"] if key == "n_covered" else ref[key])
                ok(f"S9 seed {r[0]} {key}", close(fnum(r[col])[0], want, tol),
                   f"text={r[col]} csv={want}")

    # Table S12: distance bins (bin, n per scheme, R2 per scheme)
    nn = {}
    for r in load_csv("fig7_nn_curve_final.csv"):
        nn.setdefault(r["bin"], {})[r["scheme"]] = r
    h12, r12 = next(((h, rr) for h, rr in tables(si)
                     if h and h[0].lower().startswith("nearest-neighbour")),
                    (None, None))
    if h12 is None:
        ok("Table S12 found", False)
    else:
        ok("S12 has one row per archived bin", len(r12) == len(nn),
           f"table={len(r12)} csv={len(nn)}")
        seen = set()
        for r in r12:
            key = r[0].strip().strip("`")
            seen.add(key)
            row = nn.get(key)
            if row is None:
                ok(f"S12 bin {key!r} exists in the archive", False)
                continue
            ok(f"S12 bin {key!r} n(random)",
               close(fnum(r[1])[0], float(row["random"]["n"]), 0.5),
               f"text={r[1]} csv={row['random']['n']}")
            ok(f"S12 bin {key!r} n(topology)",
               close(fnum(r[2])[0], float(row["unseen_topology"]["n"]), 0.5),
               f"text={r[2]} csv={row['unseen_topology']['n']}")
            ok(f"S12 bin {key!r} random R2",
               close(fnum(r[3])[0], float(row["random"]["R2"]), 6e-4),
               f"text={r[3]} csv={float(row['random']['R2']):.3f}")
            ok(f"S12 bin {key!r} LOTO R2",
               close(fnum(r[4])[0], float(row["unseen_topology"]["R2"]), 6e-4),
               f"text={r[4]} csv={float(row['unseen_topology']['R2']):.3f}")
        ok("S12 covers every archived bin", seen == set(nn),
           f"missing={sorted(set(nn) - seen)}")
        # both schemes must partition their full support set
        for scheme in ("random", "unseen_topology"):
            total = sum(int(float(v[scheme]["n"])) for v in nn.values())
            ok(f"S12 {scheme} rows sum to the support set", total == 25000, str(total))

    # Table S15: five-seed top-k overlap
    seeds = ["42", "143", "244", "345", "446"]
    scr = {s: load_csv(f"screening_utility_seed{s}.csv") for s in seeds}

    def overlap_stats(strategy, kfrac):
        vals = [float(r["overlap_at_k"]) for s in seeds for r in scr[s]
                if r["strategy"] == strategy and abs(float(r["k_frac"]) - kfrac) < 1e-9]
        m = sum(vals) / len(vals)
        sd = (sum((v - m) ** 2 for v in vals) / (len(vals) - 1)) ** 0.5
        return 100 * m, 100 * sd

    h15, r15 = next(((h, rr) for h, rr in tables(si) if h and h[0].startswith("Budget")),
                    (None, None))
    if h15 is None:
        ok("Table S15 found", False)
    else:
        for r in r15:
            k = fnum(r[0])[0] / 100.0
            for col, strat in ((1, "random"), (2, "topology")):
                m, sd = overlap_stats(strat, k)
                got, got_sd = fnum(r[col])
                ok(f"S15 {strat} k={k:.0%}", close(got, m, 0.02) and close(got_sd, sd, 0.02),
                   f"text={r[col]} csv={m:.2f}+-{sd:.2f}")

    # Table S16: ten-target panel
    mt = load_csv("multitarget_confound.csv")
    h16, r16 = next(((h, rr) for h, rr in tables(si)
                     if h and h[0] == "Target"), (None, None))
    if h16 is None:
        ok("Table S16 found", False)
    else:
        for r, ref in zip(r16, mt):
            for col, key, tol in ((1, "R2_random_full", 6e-4),
                                  (2, "R2_topology_full", 6e-4),
                                  (3, "split_effect_full", 6e-4),
                                  (4, "R2_random_geo", 6e-4),
                                  (5, "R2_topology_geo", 6e-4)):
                ok(f"S16 {ref['label'][:24]} {key}", close(fnum(r[col])[0], float(ref[key]), tol),
                   f"text={r[col]} csv={float(ref[key]):.3f}")

    # Table S17: leave-one-source-out
    ex = load_csv("confound_arcmof_excl_derived.csv")
    def excl(sub, gran):
        for r in ex:
            if r["subset"] == sub and r["granularity"] == gran:
                return float(r["frac_single_topology"])
        return None
    h17, r17 = next(((h, rr) for h, rr in tables(si) if h and h[0] == "Removal"), (None, None))
    if h17 is None:
        ok("Table S17 found", False)
    else:
        ok("S17 none coarse", close(fnum(r17[0][1])[0], 100 * excl("全部（未剔除）", "coarse"), 0.02))
        ok("S17 DB0 coarse", close(fnum(r17[1][1])[0], 100 * excl("剔除 DB0", "coarse"), 0.02),
           f"text={r17[1][1]} csv={100 * excl('剔除 DB0', 'coarse'):.2f}")
        ok("S17 none fine", close(fnum(r17[0][2])[0], 100 * excl("全部（未剔除）", "fine"), 0.02))
        ok("S17 DB0 fine", close(fnum(r17[1][2])[0], 100 * excl("剔除 DB0", "fine"), 0.02))

    # Table S18: within-source null
    nul = {r["source"]: r for r in load_csv("common_support/null_topology_cardinality.csv")}
    scg = {r["source"]: r for r in load_csv("source_confound_granularity.csv")}
    h18, r18 = next(((h, rr) for h, rr in tables(si)
                     if h and h[0] == "source" and "null mean" in h), (None, None))
    if h18 is None:
        ok("Table S18 found", False)
    else:
        for r in r18:
            ref = nul.get(r[0].strip())
            if ref is None:
                continue
            n = float(ref["n"])
            ok(f"S18 {r[0]} N", close(fnum(r[1])[0], n, 0.5))
            ok(f"S18 {r[0]} M", close(fnum(r[2])[0], float(ref["M"]), 0.5))
            ok(f"S18 {r[0]} observed", close(fnum(r[4])[0], 100 * float(ref["observed"]), 0.02),
               f"text={r[4]} csv={100 * float(ref['observed']):.2f}")
            ok(f"S18 {r[0]} null mean", close(fnum(r[5])[0], 100 * float(ref["null_mean"]), 0.02),
               f"text={r[5]} csv={100 * float(ref['null_mean']):.2f}")
            ok(f"S18 {r[0]} excess",
               close(fnum(r[7])[0], 100 * (float(ref["observed"]) - float(ref["null_mean"])), 0.06))
            ok(f"S18 {r[0]} H(T)", close(fnum(r[8])[0], float(scg[r[0]]["H_T"]), 6e-3))


# --------------------------------------------------------------------------
# 5. headline numbers stated inline
# --------------------------------------------------------------------------
def check_headline():
    _out("\n[5] headline numbers in prose vs archived CSVs")
    md = read(MD).replace("\u2212", "-")
    si = read(SI).replace("\u2212", "-")
    cf = {r["granularity"].split("(")[0]: r for r in load_csv("confound_full.csv")}
    coarse = cf["coarse"]
    single_all = 100 * float(coarse["frac_single_topology"])
    single_struct = 100 * float(coarse["frac_single_topology_sample_weighted"])
    cond = float(coarse["cond_frac"])
    sa_rows = {(r["dataset"], r["granularity"]): r
               for r in load_csv("singleton_audit.csv")}
    rev = float(sa_rows[("hMOF", "coarse")]["ratio_C_given_T"])
    seen = {(r["granularity"].split("(")[0], r["held_out_topology"]): r
            for r in load_csv("chemistry_seen_by_topology.csv")}
    seven = ["sra", "etb", "acs", "bcu", "pts", "fof", "the"]
    seven_rows = [float(seen[("coarse", t)]["n_samples"]) for t in seven]
    seven_n = int(sum(seven_rows))
    share = 100 * seven_n / float(coarse["n_samples"])

    ok("74.7% single-topology (by composition)", f"{single_all:.1f}" in md,
       f"csv {single_all:.2f}")
    ok("61.3% single-topology (by structure)", f"{single_struct:.1f}" in md,
       f"csv {single_struct:.2f}")
    ok("82.0% of topology entropy removed", f"{100 * (1 - cond):.1f}" in md,
       f"csv {100 * (1 - cond):.2f}")
    ok("18.0% conditional-entropy ratio", f"{100 * cond:.1f}" in md, f"csv {100 * cond:.2f}")
    ok("reverse ratio 0.860", f"{rev:.3f}" in md, f"csv {rev:.3f}")
    ok("7-of-11 structures = 69,224", f"{seven_n:,}" in md, str(seven_n))
    ok("21.3% of structures in exact hold-outs", f"{share:.1f}" in md, f"csv {share:.2f}")
    ok("coarse composition count 1,622", f"{int(float(coarse['n_chem'])):,}" in md)
    ok("single-topology composition count 1,212",
       f"{round(float(coarse['n_chem']) * float(coarse['frac_single_topology'])):,}" in md,
       str(round(float(coarse["n_chem"]) * float(coarse["frac_single_topology"]))))

    jac = load_csv("jaccard_full.csv")
    coarse_pairs = [r for r in jac if r["granularity"].startswith("coarse")]
    shared = int(coarse_pairs[0]["shared_chem"])
    ok("55 topology pairs", str(len(coarse_pairs)) in md + si, str(len(coarse_pairs)))
    ok("pcu<->nbo shared compositions 408", str(shared) in md, str(shared))
    ok("jaccard 0.371", f"{float(coarse_pairs[0]['jaccard']):.3f}" in md,
       coarse_pairs[0]["jaccard"])
    ok("rht<->tbo jaccard 0.061",
       f"{float([r for r in coarse_pairs if 'rht' in r['topo_a'] + r['topo_b']][0]['jaccard']):.3f}"
       in md)

    # protocol ratios
    final = _by_strategy(load_csv("leakage_results_final.csv"))
    chem = _by_strategy(load_csv("leakage_results_chemistry.csv"))
    nt = _by_strategy(load_csv("leakage_results_notopo100k.csv"))
    drop_topo = final["random"] - final["topology"]
    ratio426 = 100 * (final["random"] - chem["chemistry"]) / drop_topo
    drop_topo415 = nt["random"] - nt["topology"]
    ratio415 = 100 * (nt["random"] - nt["chemistry"]) / drop_topo415
    ok("21.1% unmatched ratio", f"{ratio426:.1f}" in md, f"csv {ratio426:.2f}")
    ok("21.5% matched ratio", f"{ratio415:.1f}" in md, f"csv {ratio415:.2f}")
    ok("matched decrease 0.3603", f"{drop_topo415:.4f}" in md, f"csv {drop_topo415:.4f}")
    delta_chem = nt["chemistry"] - chem["chemistry"]
    ok("topology-block removal -0.0065", f"{abs(delta_chem):.4f}" in md,
       f"csv {delta_chem:.5f}")

    # intervention
    iso = load_csv("isoreticular_control_seeds.csv")
    def mean_sd(vals):
        vals = list(vals)
        m = sum(vals) / len(vals)
        sd = 0.0 if len(vals) < 2 else (
            sum((v - m) ** 2 for v in vals) / (len(vals) - 1)) ** 0.5
        return m, sd
    per_seed = {}
    for r in iso:
        per_seed.setdefault((r["test_topo"], r["regime"], r["seed"]), []).append(float(r["MAE"]))
    a_nbo = [mean_sd(per_seed[("nbo", "with_pair", s)])[0] for s in sorted(
        {k[2] for k in per_seed})]
    b_nbo = [mean_sd(per_seed[("nbo", "without_pair", s)])[0] for s in sorted(
        {k[2] for k in per_seed})]
    a_pcu = [mean_sd(per_seed[("pcu", "with_pair", s)])[0] for s in sorted(
        {k[2] for k in per_seed})]
    b_pcu = [mean_sd(per_seed[("pcu", "without_pair", s)])[0] for s in sorted(
        {k[2] for k in per_seed})]
    nbo_up = 100 * (sum(b_nbo) / len(b_nbo)) / (sum(a_nbo) / len(a_nbo)) - 100
    pcu_up = 100 * (sum(b_pcu) / len(b_pcu)) / (sum(a_pcu) / len(a_pcu)) - 100
    ok("nbo +70.0% MAE", f"+{nbo_up:.1f}%" in md, f"csv {nbo_up:.2f}")
    ok("pcu -1.2% MAE", f"{pcu_up:.1f}%" in md, f"csv {pcu_up:.2f}")

    arm_e = load_csv("arm_e_partner_coverage.csv")
    def arm_mean(test, reg, col="MAE"):
        vals = [float(r[col]) for r in arm_e if r["test_topo"] == test and r["regime"] == reg]
        return sum(vals) / len(vals)
    n_e, n_f = arm_mean("nbo", "e_shared_only_removed"), arm_mean("nbo", "f_size_matched_from_e")
    n_b, n_a = arm_mean("nbo", "b_partner_removed"), arm_mean("nbo", "a_with_partner")
    step1 = 100 * (n_e - n_a) / (n_b - n_a)
    ok("34.9% / 65.1% split", f"{step1:.1f}%" in md and f"{100 - step1:.1f}%" in md,
       f"csv {step1:.2f} / {100 - step1:.2f}")
    ok("arm (e) removes 12,342 / 6,689 rows",
       "12,342" in md and "6,689" in md)
    ok("pcu e MAE 0.2293", f"{arm_mean('pcu', 'e_shared_only_removed'):.4f}" in md)
    ok("pcu f MAE 0.2304", f"{arm_mean('pcu', 'f_size_matched_from_e'):.4f}" in md)
    ok("pcu a MAE 0.2424", f"{arm_mean('pcu', 'a_with_partner'):.4f}" in md)
    ok("pcu b MAE 0.2396", f"{arm_mean('pcu', 'b_partner_removed'):.4f}" in md)

    # ---- section-scoped checks: a headline number must sit in the sections that
    # carry the claim, not merely somewhere in the file (review 2026-10-20 §10.5)
    def sec_text(prefix):
        m = re.search(r"^##\s*" + re.escape(prefix) + r".*?(?=^##\s|\Z)", md + "\n## END",
                      re.S | re.M)
        return m.group(0) if m else ""

    scoped = [
        ("Abstract", "74.7", sec_text("Abstract")),
        ("Abstract", "50.4", sec_text("Abstract")),
        ("Abstract", "19.3", sec_text("Abstract")),
        ("Abstract", "70.0", sec_text("Abstract")),
        ("3.1", "74.7", sec_text("3. Results")),
        ("3.2", "21.1", sec_text("3. Results")),
        ("4.1", "21.1", sec_text("4. Discussion")),
        ("3.4", "50.4", sec_text("3. Results")),
    ]
    for where, needle, text in scoped:
        ok(f"{needle} appears in {where}", needle in text,
           "claim present in file but not in this section")

    # screening
    seeds = ["42", "143", "244", "345", "446"]
    scr = {s: load_csv(f"screening_utility_seed{s}.csv") for s in seeds}
    def k_stats(strategy, kfrac, col="overlap_at_k"):
        vals = [float(r[col]) for s in seeds for r in scr[s]
                if r["strategy"] == strategy and abs(float(r["k_frac"]) - kfrac) < 1e-9]
        m = sum(vals) / len(vals)
        sd = (sum((v - m) ** 2 for v in vals) / (len(vals) - 1)) ** 0.5
        return m, sd
    r_m, _ = k_stats("random", 0.01)
    t_m, t_sd = k_stats("topology", 0.01)
    ok("50.4% random top-1%", f"{100 * r_m:.1f}%" in md, f"csv {100 * r_m:.2f}")
    ok("19.3% topology top-1%", f"{100 * t_m:.1f}%" in md, f"csv {100 * t_m:.2f}")
    ok("31.1 pp gap", f"{100 * (r_m - t_m):.1f}" in md, f"csv {100 * (r_m - t_m):.2f}")

    # paired-seed tests quoted in 3.3/3.4 and abstract, recomputed by
    # scripts/screening_paired_tests.py into outputs/paired_tests_20261024.csv
    pt = {row["test"]: row for row in load_csv("paired_tests_20261024.csv")}
    gap = pt["screening top-1% overlap, random minus topology"]
    ok("screening gap interval 24.6 to 37.6",
       f"{float(gap['ci_low']):.1f} to {float(gap['ci_high']):.1f}" in md,
       f"csv {float(gap['ci_low']):.1f} to {float(gap['ci_high']):.1f}")
    ok("screening gap paired t(4) = 13.2",
       f"t(4) = {float(gap['t']):.1f}" in md, f"csv {float(gap['t']):.3f}")
    ok("screening gap p = 1.9e-4", "p = 1.9 × 10⁻⁴" in md)
    ab = pt["nbo MAE, arm (b) minus arm (a)"]
    ok("nbo paired interval +0.0591 to +0.0900",
       f"+{float(ab['ci_low']):.4f} to +{float(ab['ci_high']):.4f}" in md,
       f"csv +{float(ab['ci_low']):.4f} to +{float(ab['ci_high']):.4f}")
    pct = pt["nbo MAE change, arm (a) to (b)"]
    ok("nbo percentage interval +55.5% to +84.5%",
       f"+{float(pct['ci_low']):.1f}% to +{float(pct['ci_high']):.1f}%" in md,
       f"csv +{float(pct['ci_low']):.1f}% to +{float(pct['ci_high']):.1f}%")
    ok("nbo paired t(4) = 13.4, p = 1.8e-4",
       f"t(4) = {float(ab['t']):.1f}, p = 1.8 × 10⁻⁴" in md,
       f"csv t {float(ab['t']):.3f}, p {float(ab['p']):.6f}")
    for strat, lit in (("chemistry", "44.0"), ("linker_pair", "41.1"), ("metal", "29.2")):
        got = k_stats(strat, 0.01)[0]
        ok(f"{lit}% {strat} top-1%", f"{100 * got:.1f}" in md and lit in md,
           f"csv {100 * got:.2f}")
    sel = [float(r["topk_true_mean"]) for s in seeds for r in scr[s]
           if r["strategy"] == "topology" and abs(float(r["k_frac"]) - 0.01) < 1e-9]
    orc = [float(r["oracle_topk_mean"]) for s in seeds for r in scr[s]
           if r["strategy"] == "topology" and abs(float(r["k_frac"]) - 0.01) < 1e-9]
    shortfall = 100 * (1 - (sum(sel) / len(sel)) / (sum(orc) / len(orc)))
    ok("46.3% shortfall", f"{shortfall:.1f}%" in md, f"csv {shortfall:.2f}")
    ok("selected mean 1.742", f"{sum(sel) / len(sel):.3f}" in md,
       f"csv {sum(sel) / len(sel):.3f}")

    # ARC-MOF
    sa = {(r["dataset"], r["granularity"]): r for r in load_csv("singleton_audit.csv")}
    ok("ARC coarse non-singleton 97.3%",
       f"{100 * float(sa[('ARC-MOF', 'coarse')]['single_topology_non_singleton']):.1f}%" in md)
    ok("ARC fine non-singleton 98.2%",
       f"{100 * float(sa[('ARC-MOF', 'fine')]['single_topology_non_singleton']):.1f}%" in md)
    ok("hMOF fine non-singleton 79.1%",
       f"{100 * float(sa[('hMOF', 'fine')]['single_topology_non_singleton']):.1f}%" in md,
       f"csv {100 * float(sa[('hMOF', 'fine')]['single_topology_non_singleton']):.1f}")
    ex = load_csv("confound_arcmof_excl_derived.csv")
    db0 = {(r["granularity"]): float(r["frac_single_topology"]) * 100
           for r in ex if r["subset"] == "剔除 DB0"}
    ok("DB0 removal 98.57 coarse", f"{db0['coarse']:.2f}" in md, f"csv {db0['coarse']:.2f}")
    ok("DB0 removal 98.96 fine", f"{db0['fine']:.2f}" in md, f"csv {db0['fine']:.2f}")
    spread = load_csv("source_spread_test.csv")
    for row in spread:
        ratio = float(row["ratio_obs_over_null"])
        lit = f"{ratio:,.0f}"
        ok(f"between-source spread {row['granularity']}",
           lit in md or lit in si, f"csv ratio {lit}")

    # LOTO / aggregation statements
    ok("pooled without pcu +0.4629", "0.4629" in md)
    ok("macro without rht -0.2948", "0.2948" in md)
    aud = {r["result"]: r for r in load_csv("metrics_audit.csv")}
    for row in load_csv("metrics_audit.csv"):
        if row["result"].startswith("LOTO / topology (100k)  [剔除最大组 pcu]"):
            ok("audit excl-pcu pooled", close(float(row["pooled_as_reported"]), 0.4628955832, 1e-9))

    # model-family contrast
    gb = _by_strategy(load_csv("leakage_results_gb100k.csv"))
    rf = _by_strategy(load_csv("leakage_results_rf100k.csv"))
    rg = _by_strategy(load_csv("leakage_results_ridge100k.csv"))
    ok("RF topology penalty 0.3743", f"{rf['random'] - rf['topology']:.4f}" in md,
       f"csv {rf['random'] - rf['topology']:.4f}")
    ok("GB topology penalty 0.3742", f"{gb['random'] - gb['topology']:.4f}" in md,
       f"csv {gb['random'] - gb['topology']:.4f}")
    ok("ridge random-split R2 0.440", f"{rg['random']:.3f}" in md, f"csv {rg['random']:.3f}")


# --------------------------------------------------------------------------
# 6. word counts
# --------------------------------------------------------------------------
def check_lengths():
    _out("\n[6] length")
    md = read(MD)
    total = len(re.findall(r"\S+", md))
    body = md[: md.find("## 6. Figure captions")]
    ok(f"body (abstract..discussion) present", len(body) > 1000)
    _out(f"  words total            : {total:,}")
    _out(f"  body words (to §5 end): {len(body.split()):,}")
    _out(f"  characters             : {len(md):,}")


def check_si_s25():
    """Rebuild every numeric cell of S25/S25b from the five paired seed metrics."""
    from statistics import mean
    text = read(SI)
    expected_seeds = {'42','143','244','345','446'}
    for scope, table_number, reps, models in (
        ('mapped','25',('I','T'),('RF','ET')),
        ('full','25b',('B','I'),('RF',))):
        rows = [r for r in load_csv(f'sensitivity_mf1/{scope}/mf1_pooled.csv')
                if r['protocol']=='LOTO']
        expected = {(t,m,rep,seed) for t in ('uptake','selectivity') for m in models
                    for rep in reps for seed in expected_seeds}
        keys = [(r['target'],r['model'],r['representation'],r['seed']) for r in rows]
        if not ok(f'S{table_number} complete five-seed design',
                  len(keys)==len(expected) and len(set(keys))==len(keys) and set(keys)==expected):
            continue
        blocks = []
        for target in ('uptake','selectivity'):
            for model in models:
                means = {rep:[] for rep in reps}
                gaps, signs = [], []
                for setting in ('MAE_sqrt','MAE_mf1'):
                    values = {(r['representation'],r['seed']):float(r[setting]) for r in rows
                              if r['target']==target and r['model']==model}
                    for rep in reps:
                        means[rep].append(mean(values[rep,seed] for seed in expected_seeds))
                    d = [values[reps[1],seed]-values[reps[0],seed] for seed in expected_seeds]
                    gaps.append(mean(d))
                    signs.append(sum(x>0 if scope=='mapped' else x<0 for x in d))
                cells = ['Uptake' if target=='uptake' else 'Log-selectivity']
                if scope=='mapped':cells.append(model)
                cells.extend(f'{means[rep][0]:.4f} → {means[rep][1]:.4f}' for rep in reps)
                cells.append(f'{gaps[0]:+.4f} → **{gaps[1]:+.4f}**'.replace('-', '−'))
                cells.append(f'{signs[0]}/5 / {signs[1]}/5')
                blocks.append('| '+' | '.join(cells)+' |')
        marker = f'**Table S{table_number}.**'
        if not ok(f'S{table_number} caption exists', marker in text):continue
        tail = text.split(marker,1)[1].splitlines()
        first = next((i for i,line in enumerate(tail) if line.startswith('|')),None)
        if not ok(f'S{table_number} table exists', first is not None):continue
        actual = []
        for line in tail[first+2:]:
            if not line.startswith('|'):break
            actual.append(line.rstrip())
        ok(f'S{table_number} every numeric cell matches paired CSVs', actual==blocks)


def main() -> int:
    global VERBOSE
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--no-pdf", action="store_true")
    args = ap.parse_args()
    VERBOSE = args.verbose

    for p in (MD, SI, BUILD, MANIFEST):
        if not p.exists():
            _out(f"missing required file: {p}")
            return 2

    check_layout(args.no_pdf)
    if not args.no_pdf:
        from verify_build_manifest import verify as verify_build
        try:
            count = verify_build()
            ok("PDF build manifest matches 18 input/output byte hashes", count == 18)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            ok("PDF build manifest matches 18 input/output byte hashes", False, str(exc))
    check_text()
    check_enumeration()
    check_figures()
    check_main_tables()
    check_si_tables()
    check_si_s25()
    from verify_followup_tables import verify as verify_followup
    try:
        verify_followup()
        ok("SI S19-S24 independently recomputed from archived metrics", True)
    except (AssertionError, ValueError, KeyError, StopIteration, OSError) as exc:
        ok("SI S19-S24 independently recomputed from archived metrics", False, str(exc))
    check_headline()
    check_lengths()

    _out("\n  Coverage note: tables 1-3, SI S1-S9/S12/S15-S25b, the named headline")
    _out("  claims and all numbering/citation/file checks are automated. SI Tables")
    _out("  S10/S11/S13/S14, the prose outside the named claims, and the PDF layout")
    _out("  are NOT verified here; they need a human read before submission.")
    _out("\n" + "=" * 72)
    if FAILURES:
        _out(f"{len(FAILURES)} of {CHECKS} checks FAILED")
        return 1
    _out(f"all {CHECKS} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

