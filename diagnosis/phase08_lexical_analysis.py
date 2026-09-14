#!/usr/bin/env python
"""Phase 08 -- word-level lexical dependence. Measurement only.

Pre-registered in `phases/08_lexical_analysis.md` (commit b127d44), written
before any token count existed. Constants below carry their C8-x tag so a
reader can check the code against the declaration rather than trusting it.

No training, no GPU, no forward pass, no intervention. Token-label statistics
come from the TRAINING split only (C8-1); dev supplies error row ids already
tagged in phase 02 and nothing else; the official test set is not touched.

Usage:
    python phase08_lexical_analysis.py [--n_boot N]
"""

import argparse
import json
import math
import random
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from src import augment, data_io, lexicon

# --- pre-registered constants (phases/08_lexical_analysis.md) ----------------
TOP_N = 200                 # C8-3: candidate pool size
ALPHA = 0.05                # C8-5: family-wise, two-sided
EFFECT_RATIO = 1.5          # C8-5: effect floor, multiplicative on the base rate
WIDE_DF_MIN = 30            # C8-8.1: wider-pool sensitivity
N_BOOT = 10000              # C8-7
BOOT_SEED = 42              # C8-7
N_QUANTILES = 4             # C8-7: token-count quartiles for matching


# --------------------------------------------------------------------------
# statistics
# --------------------------------------------------------------------------

def _norm_ppf(p):
    """Inverse standard normal CDF (Acklam's rational approximation).

    Used once, to turn the Bonferroni-corrected alpha into a z threshold. Hard
    coding 3.66 would hide where the number came from; stdlib has no ppf.
    Accurate to ~1.15e-9 over the open interval, far beyond what is needed here.
    """
    if not 0.0 < p < 1.0:
        raise ValueError(f"p must be in (0, 1), got {p!r}")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
               ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
                ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r + a[1])*r + a[2])*r + a[3])*r + a[4])*r + a[5])*q / \
           (((((b[0]*r + b[1])*r + b[2])*r + b[3])*r + b[4])*r + 1)


def binomial_z(off_df, df, p0):
    """C8-4 primary ranking. Deviation from the base rate, sqrt(df)-weighted.

    Monotone increasing in df at fixed p_hat, which is the property that keeps
    a low-frequency token off the top of the list unless its skew is extreme.
    """
    if df <= 0:
        return 0.0
    p_hat = off_df / df
    return (p_hat - p0) / math.sqrt(p0 * (1.0 - p0) / df)


def quantile_edges(values, n):
    """Interior cut points splitting sorted `values` into n groups.

    Nearest-rank, so edges are always observed values and no interpolation
    invents a boundary that no row sits at.
    """
    s = sorted(values)
    return [s[min(len(s) - 1, int(round(k * len(s) / n)))] for k in range(1, n)]


def bucket_of(value, edges):
    b = 0
    for e in edges:
        if value >= e:
            b += 1
    return b


def percentile(sorted_vals, q):
    if not sorted_vals:
        return float("nan")
    i = (len(sorted_vals) - 1) * q
    lo, hi = math.floor(i), math.ceil(i)
    if lo == hi:
        return sorted_vals[int(i)]
    return sorted_vals[lo] * (hi - i) + sorted_vals[hi] * (i - lo)


# --------------------------------------------------------------------------
# the matched comparison (C8-7)
# --------------------------------------------------------------------------

def stratum_weighted_rate(a_cells, b_cells):
    """Mean of X over B, reweighted to A's stratum distribution.

    a_cells: {cell: [x, ...]} for group A, b_cells: same for group B.
    Returns (rate, unsupported_share) where unsupported_share is the fraction of
    A's mass sitting in strata B cannot cover -- reported, never silently
    dropped, because a large value means the matching failed rather than held.
    """
    n_a = sum(len(v) for v in a_cells.values())
    if n_a == 0:
        return float("nan"), 1.0
    supported = {c: v for c, v in a_cells.items() if b_cells.get(c)}
    mass = sum(len(v) for v in supported.values())
    if mass == 0:
        return float("nan"), 1.0
    rate = sum(
        (len(v) / mass) * (sum(b_cells[c]) / len(b_cells[c]))
        for c, v in supported.items()
    )
    return rate, 1.0 - mass / n_a


def matched_comparison(a_rows, b_rows, edges, n_boot=N_BOOT, seed=BOOT_SEED):
    """Difference in P(row contains a group-2 token), A minus matched B.

    a_rows / b_rows are lists of (x, in_lex, ntok). Strata are
    (in_lex, token-count quartile); the quartile edges are fixed at A's
    observed values and are NOT recomputed inside the bootstrap -- the estimator
    being resampled is the one defined on the observed strata.
    """
    def cells(rows):
        d = defaultdict(list)
        for x, in_lex, ntok in rows:
            d[(in_lex, bucket_of(ntok, edges))].append(x)
        return d

    a_cells, b_cells = cells(a_rows), cells(b_rows)
    rate_a = sum(x for x, _, _ in a_rows) / len(a_rows)
    rate_b_raw = sum(x for x, _, _ in b_rows) / len(b_rows)
    rate_b_matched, unsupported = stratum_weighted_rate(a_cells, b_cells)

    rng = random.Random(seed)
    diffs_matched, diffs_raw = [], []
    for _ in range(n_boot):
        ra = [a_rows[rng.randrange(len(a_rows))] for _ in range(len(a_rows))]
        rb = [b_rows[rng.randrange(len(b_rows))] for _ in range(len(b_rows))]
        m, _ = stratum_weighted_rate(cells(ra), cells(rb))
        ma = sum(x for x, _, _ in ra) / len(ra)
        if not math.isnan(m):
            diffs_matched.append(ma - m)
        diffs_raw.append(ma - sum(x for x, _, _ in rb) / len(rb))

    def ci(vals):
        s = sorted(vals)
        return {"ci_low": percentile(s, 0.025), "ci_high": percentile(s, 0.975),
                "n_resamples": len(s)}

    return {
        "n_a": len(a_rows), "n_b": len(b_rows),
        "rate_a": rate_a,
        "rate_b_unmatched": rate_b_raw,
        "rate_b_matched": rate_b_matched,
        "diff_matched": rate_a - rate_b_matched,
        "diff_matched_ci": ci(diffs_matched),
        "diff_unmatched": rate_a - rate_b_raw,
        "diff_unmatched_ci": ci(diffs_raw),
        "a_mass_in_unsupported_strata": unsupported,
    }


def verdict(diff, ci):
    """C8-7: the interpretation was fixed before the number existed."""
    if diff > 0 and ci["ci_low"] > 0:
        return "SUPPORT"
    return "NO SUPPORT"


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def build_token_table(rows, p0, lex_list, lex_set, df_min=None, top_n=None):
    """Per-token document-frequency statistics over `rows` (C8-2)."""
    df, off_df, occ = Counter(), Counter(), Counter()
    for r in rows:
        toks = lexicon.tokens(r["text"])
        occ.update(toks)
        seen = set(toks)
        df.update(seen)
        if r["label"] == "OFF":
            off_df.update(seen)

    if top_n is not None:
        pool = [t for t, _ in df.most_common(top_n)]
    else:
        pool = [t for t, c in df.items() if c >= df_min]

    table = []
    for t in pool:
        d, o = df[t], off_df[t]
        p_hat = o / d
        in_lex = lexicon.hit_root(t, lex_list)
        matched = [rt for rt in lex_list
                   if len(rt) >= lexicon.MIN_ROOT_LEN and t.startswith(rt)]
        table.append({
            "token": t,
            "df": d,
            "occurrences": occ[t],
            "off_rows": o,
            "not_rows": d - o,
            "p_off_given_token": round(p_hat, 6),
            "lift": round(p_hat / p0, 4),
            "excess_off_rows": round(o - d * p0, 2),
            "z": round(binomial_z(o, d, p0), 4),
            "in_lexicon_hit_root": in_lex,
            "in_lexicon_exact": t in lex_set,
            "suspect_root_only": bool(matched) and all(r in augment.SUSPECT_ROOTS
                                                       for r in matched),
        })
    table.sort(key=lambda r: -r["z"])
    return table, df, off_df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n_boot", type=int, default=N_BOOT)
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    out_dir = config.RESULTS_DIR / "08_lexical_analysis"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 96)
    print("PHASE 08 -- word-level lexical dependence (measurement only)")
    print("=" * 96)

    # --- inputs ------------------------------------------------------------
    train_sha = data_io.sha256(config.COLTEKIN_TRAIN)
    all_rows = data_io.load_coltekin_train(config.COLTEKIN_TRAIN)
    split_path = config.SPLITS_DIR / "split_seed42.json"
    train_rows, dev_rows, meta = data_io.get_split(
        all_rows, split_path, train_sha, seed=config.SEED,
        dev_fraction=config.DEV_FRACTION)
    if not meta["reused_existing_file"]:
        raise SystemExit("ABORT: the split was CREATED, not loaded.")
    lex_list = lexicon.load_lexicon(config.LEXICON_PATH)
    lex_set = set(lex_list)

    print(f"\ncorpus            : {len(all_rows):,} rows, sha {train_sha[:16]}")
    print(f"train / dev       : {len(train_rows):,} / {len(dev_rows):,}")
    print(f"dev fingerprint   : {meta['dev_fingerprint'][:16]}  (loaded)")
    print(f"lexicon           : {len(lex_list)} entries, "
          f"sha {data_io.sha256(config.LEXICON_PATH)[:16]}")

    # --- C8-9 class balance ------------------------------------------------
    def balance(rows, label):
        n_off = sum(1 for r in rows if r["label"] == "OFF")
        hit = [r for r in rows if lexicon.hit_root(r["text"], lex_list)]
        # Partition by row id: `r in hit` would compare dicts by value, and two
        # distinct rows with identical text and label are equal that way.
        hit_ids = {str(r["id"]) for r in hit}
        free = [r for r in rows if str(r["id"]) not in hit_ids]
        def frac(rs):
            n = len(rs)
            o = sum(1 for r in rs if r["label"] == "OFF")
            return {"n": n, "off": o, "not": n - o,
                    "off_rate": round(o / n, 6) if n else None,
                    "off_to_not_ratio": round(o / (n - o), 4) if n - o else None}
        return {"split": label, "overall": frac(rows),
                "lexicon_hit": frac(hit), "lexicon_free": frac(free)}

    print("\n" + "-" * 96)
    print("C8-9  CLASS BALANCE")
    print("-" * 96)
    balances = {}
    for rows, name in ((train_rows, "train"), (dev_rows, "dev")):
        b = balance(rows, name)
        balances[name] = b
        print(f"\n  [{name}]  n={b['overall']['n']:,}")
        print(f"    {'slice':<16}{'n':>8}{'OFF':>8}{'NOT':>8}{'OFF rate':>11}{'OFF:NOT':>10}")
        for k in ("overall", "lexicon_hit", "lexicon_free"):
            f = b[k]
            print(f"    {k:<16}{f['n']:>8,}{f['off']:>8,}{f['not']:>8,}"
                  f"{f['off_rate']:>11.4f}{'  1:%.2f' % (f['not']/f['off']) if f['off'] else '':>10}")

    p0 = balances["train"]["overall"]["off_rate"]
    print(f"\n  base rate p0 (TRAIN, computed) : {p0:.6f}")
    print(f"  advisor's stated value          : 0.193   "
          f"-> {'matches' if abs(p0 - 0.193) < 5e-4 else 'DIFFERS'}")

    # --- C8-3/4/5 the ranked table ----------------------------------------
    z_thresh = _norm_ppf(1.0 - ALPHA / (2.0 * TOP_N))
    print("\n" + "-" * 96)
    print("C8-3..6  TOKEN FREQUENCY AND LABEL SKEW  (training split only)")
    print("-" * 96)
    print(f"  pool              : top {TOP_N} tokens by document frequency")
    print(f"  ranking           : binomial z (primary), excess OFF rows (secondary)")
    print(f"  |z| threshold     : {z_thresh:.4f}  (Bonferroni, alpha={ALPHA}, {TOP_N} tests)")
    print(f"  effect floor      : p_hat >= {EFFECT_RATIO * p0:.4f} (OFF) / "
          f"<= {p0 / EFFECT_RATIO:.4f} (NOT)")

    table, df_all, off_df_all = build_token_table(
        train_rows, p0, lex_list, lex_set, top_n=TOP_N)

    hi = EFFECT_RATIO * p0
    lo = p0 / EFFECT_RATIO
    for r in table:
        p = r["p_off_given_token"]
        r["group"] = ("lexicon" if r["in_lexicon_hit_root"] else
                      "off_skew_nonlex" if r["z"] >= z_thresh and p >= hi else
                      "not_skew" if r["z"] <= -z_thresh and p <= lo else
                      "unremarkable")

    groups = defaultdict(list)
    for r in table:
        groups[r["group"]].append(r)

    def show(rows, title, n=None):
        print(f"\n  {title}  ({len(rows)} tokens)")
        print(f"    {'token':<16}{'df':>7}{'OFF':>7}{'NOT':>7}{'P(OFF|t)':>10}"
              f"{'lift':>7}{'z':>8}{'excess':>9}  flags")
        for r in rows[:n] if n else rows:
            flags = []
            if r["in_lexicon_exact"]:
                flags.append("exact")
            if r["suspect_root_only"]:
                flags.append("suspect-only")
            print(f"    {r['token']:<16}{r['df']:>7,}{r['off_rows']:>7,}{r['not_rows']:>7,}"
                  f"{r['p_off_given_token']:>10.4f}{r['lift']:>7.2f}{r['z']:>8.2f}"
                  f"{r['excess_off_rows']:>9.1f}  {','.join(flags)}")

    show(groups["lexicon"], "GROUP 1 -- in the frozen karaliste (hit_root)")
    show(groups["off_skew_nonlex"], "GROUP 2 -- NOT in the lexicon, skew strongly OFF")
    show(sorted(groups["not_skew"], key=lambda r: r["z"]),
         "GROUP 3 -- skew strongly NOT", n=25)
    print(f"\n  GROUP 0 -- unremarkable (within the thresholds): "
          f"{len(groups['unremarkable'])} tokens")
    print("\n  Top 15 by the SECONDARY weighting (excess OFF rows), for contrast:")
    for r in sorted(table, key=lambda r: -r["excess_off_rows"])[:15]:
        print(f"    {r['token']:<16} excess {r['excess_off_rows']:>8.1f}  "
              f"z {r['z']:>7.2f}  df {r['df']:>6,}  group {r['group']}")

    group2 = {r["token"] for r in groups["off_skew_nonlex"]}
    group3 = {r["token"] for r in groups["not_skew"]}

    # --- C8-7 the step-3 test ---------------------------------------------
    print("\n" + "-" * 96)
    print("C8-7  DO THE 118 NO-PROFANITY FALSE POSITIVES CARRY GROUP-2 TOKENS?")
    print("-" * 96)

    tags = json.loads((config.RESULTS_DIR / "02_failure_analysis" /
                       "fp_function_tags.json").read_text(encoding="utf-8"))
    if not tags["dev_fingerprint"].startswith(meta["dev_fingerprint"][:16]):
        raise SystemExit("ABORT: FP tag file is from a different dev split.")
    fp_ids = [str(i) for i in tags["ids"]]
    noprof_ids = {i for i, t in zip(fp_ids, tags["tags"]) if t == "NOPROF"}
    fp_id_set = set(fp_ids)

    by_id = {str(r["id"]): r for r in dev_rows}
    missing = [i for i in fp_id_set if i not in by_id]
    if missing:
        raise SystemExit(f"ABORT: {len(missing)} FP ids are not in dev.")

    dev_not = [r for r in dev_rows if r["label"] == "NOT"]
    tn_rows = [r for r in dev_not if str(r["id"]) not in fp_id_set]
    a_src = [by_id[i] for i in sorted(noprof_ids)]
    print(f"  A = NOPROF false positives        : {len(a_src)}")
    print(f"  dev gold-NOT rows                 : {len(dev_not):,}")
    print(f"  B = true negatives (NOT minus FP) : {len(tn_rows):,}")
    if len(dev_not) - len(tn_rows) != len(fp_id_set):
        raise SystemExit("ABORT: FP ids do not all carry gold NOT.")

    def featurise(rows, vocab):
        out = []
        for r in rows:
            toks = lexicon.tokens(r["text"])
            out.append((1 if (set(toks) & vocab) else 0,
                        lexicon.hit_root(r["text"], lex_list),
                        len(toks)))
        return out

    a_feat = featurise(a_src, group2)
    b_feat = featurise(tn_rows, group2)
    edges = quantile_edges([n for _, _, n in a_feat], N_QUANTILES)
    print(f"  token-count quartile edges (from A): {edges}")
    print(f"  A rows on lexicon-hit rows        : "
          f"{sum(1 for _, h, _ in a_feat if h)} of {len(a_feat)}")

    primary = matched_comparison(a_feat, b_feat, edges, n_boot=args.n_boot)
    v = verdict(primary["diff_matched"], primary["diff_matched_ci"])

    def report_cmp(c, title):
        print(f"\n  [{title}]")
        print(f"    rate in A (118 NOPROF FPs)      : {c['rate_a']:.4f}  "
              f"({round(c['rate_a'] * c['n_a'])} of {c['n_a']})")
        print(f"    rate in B, unmatched            : {c['rate_b_unmatched']:.4f}  "
              f"(n={c['n_b']:,})")
        print(f"    rate in B, matched to A         : {c['rate_b_matched']:.4f}")
        print(f"    difference (matched)            : {c['diff_matched']:+.4f}  "
              f"[{c['diff_matched_ci']['ci_low']:+.4f}, {c['diff_matched_ci']['ci_high']:+.4f}]")
        print(f"    difference (unmatched)          : {c['diff_unmatched']:+.4f}  "
              f"[{c['diff_unmatched_ci']['ci_low']:+.4f}, {c['diff_unmatched_ci']['ci_high']:+.4f}]")
        print(f"    A mass in unsupported strata    : "
              f"{c['a_mass_in_unsupported_strata']:.4f}")

    report_cmp(primary, f"PRIMARY -- group 2, {len(group2)} tokens")
    print(f"\n    VERDICT (pre-registered rule C8-7): {v}")

    # which group-2 tokens actually appear in A
    a_tok_counts = Counter()
    for r in a_src:
        for t in set(lexicon.tokens(r["text"])) & group2:
            a_tok_counts[t] += 1
    print(f"\n    group-2 tokens present in A, by row count:")
    for t, c in a_tok_counts.most_common():
        print(f"      {t:<16}{c:>4} of {len(a_src)} rows   "
              f"(train P(OFF|t)={next(x['p_off_given_token'] for x in table if x['token']==t):.4f})")
    if not a_tok_counts:
        print("      (none)")

    # --- C8-8 sensitivities ------------------------------------------------
    print("\n" + "-" * 96)
    print("C8-8  PRE-PLANNED SENSITIVITIES")
    print("-" * 96)

    wide_table, _, _ = build_token_table(
        train_rows, p0, lex_list, lex_set, df_min=WIDE_DF_MIN)
    z_wide = _norm_ppf(1.0 - ALPHA / (2.0 * len(wide_table)))
    wide_group2 = {r["token"] for r in wide_table
                   if not r["in_lexicon_hit_root"] and r["z"] >= z_wide
                   and r["p_off_given_token"] >= hi}
    print(f"\n  1. WIDER POOL: df >= {WIDE_DF_MIN} -> {len(wide_table):,} candidate tokens, "
          f"|z| >= {z_wide:.4f}")
    print(f"     non-lexicon strong-OFF tokens : {len(wide_group2)}")
    print(f"     top 25 by z: " + ", ".join(
        r["token"] for r in sorted(
            [x for x in wide_table if x["token"] in wide_group2],
            key=lambda r: -r["z"])[:25]))
    wide_cmp = matched_comparison(
        featurise(a_src, wide_group2), featurise(tn_rows, wide_group2),
        edges, n_boot=args.n_boot)
    report_cmp(wide_cmp, f"wider pool -- {len(wide_group2)} tokens")
    print(f"\n    VERDICT: {verdict(wide_cmp['diff_matched'], wide_cmp['diff_matched_ci'])}")

    print(f"\n  2. NO MATCHING: reported as the 'unmatched' line in every block above.")

    print(f"\n  3. GROUP-3 CONTROL: strong-NOT tokens ({len(group3)})")
    g3_cmp = matched_comparison(featurise(a_src, group3), featurise(tn_rows, group3),
                                edges, n_boot=args.n_boot)
    report_cmp(g3_cmp, f"control -- strong-NOT, {len(group3)} tokens")

    # --- POST-HOC (not pre-registered) ------------------------------------
    # Everything below was decided AFTER seeing the ranked list. It is exploratory
    # and cannot confirm anything; it is here because the composition of group 2
    # turned out to be the substantive result and refusing to describe it would be
    # worse than describing it with the right caveat attached. The subsets are the
    # assistant's semantic judgment of Turkish tokens, not a measurement, and no
    # verdict from this block is reported as a finding.
    print("\n" + "-" * 96)
    print("POST-HOC -- composition of group 2 (exploratory, decided after seeing the list)")
    print("-" * 96)

    SECOND_PERSON = {"sen", "senin", "siz", "sizin", "sizi", "sana", "size", "seni",
                     "bak", "bakın", "hepiniz", "yapıyorsunuz"}
    PERSON_DEIXIS = SECOND_PERSON | {"lan", "ulan", "git", "gidin", "adam", "adamı",
                                     "adamın", "adamlar", "herif", "bunlar", "bunları",
                                     "bunların", "bunlara", "onlar", "denen", "cahil"}
    POLITICAL_ID = {"akp", "chp", "hdp", "pkk", "fetö", "atatürk", "islam", "türk",
                    "din", "israil", "vatan", "parti", "abd", "oy", "ak", "kürt",
                    "müslüman", "rte", "tayyip", "bahçeli", "terör", "terörist",
                    "şehit", "millet", "demokrasi", "ülke"}

    posthoc = {}
    for pool_name, vocab_all in (("top200", group2),
                                 ("wide", wide_group2)):
        for sub_name, sub in (("person_deixis", PERSON_DEIXIS),
                              ("political_religious_identity", POLITICAL_ID)):
            vocab = vocab_all & sub
            if not vocab:
                continue
            c = matched_comparison(featurise(a_src, vocab), featurise(tn_rows, vocab),
                                   edges, n_boot=args.n_boot)
            key = f"{pool_name}__{sub_name}"
            posthoc[key] = {"tokens": sorted(vocab), "comparison": c}
            print(f"\n  [{pool_name}] {sub_name}: {len(vocab)} tokens")
            print(f"    {', '.join(sorted(vocab))}")
            print(f"    A {round(c['rate_a']*c['n_a'])}/{c['n_a']}  "
                  f"B {round(c['rate_b_unmatched']*c['n_b'])}/{c['n_b']:,}   "
                  f"matched diff {c['diff_matched']:+.4f} "
                  f"[{c['diff_matched_ci']['ci_low']:+.4f}, "
                  f"{c['diff_matched_ci']['ci_high']:+.4f}]")

    # The MIN_ROOT_LEN blind spot, found while checking why `aq` landed in group 2.
    # Five lexicon entries are shorter than MIN_ROOT_LEN, so hit_root can never
    # fire on them and rows carrying them are filed as lexicon_free. This is the
    # OPPOSITE leak to the one phase 02's slice_sensitivity measured.
    short_entries = sorted(w for w in lex_list if len(w) < lexicon.MIN_ROOT_LEN)
    short_set = set(short_entries)
    dev_free_off = [r for r in dev_rows if r["label"] == "OFF"
                    and not lexicon.hit_root(r["text"], lex_list)]
    leak = [r for r in dev_free_off
            if set(lexicon.tokens(r["text"])) & short_set]
    reported_recall = 0.5628318584070796   # results/02_failure_analysis/slice_sensitivity.json
    n_free_off = len(dev_free_off)
    n_correct = round(reported_recall * n_free_off)
    bound = ((n_correct - len(leak)) / (n_free_off - len(leak))) if leak else reported_recall
    print(f"\n  MIN_ROOT_LEN blind spot: lexicon entries shorter than "
          f"{lexicon.MIN_ROOT_LEN}: {short_entries}")
    print(f"    gold-OFF lexicon_free dev rows carrying one : {len(leak)} of {n_free_off} "
          f"({len(leak)/n_free_off:.4f})")
    print(f"    reported lexicon_free OFF-recall            : {reported_recall:.4f} "
          f"= {n_correct}/{n_free_off}")
    print(f"    UPPER BOUND if every leaked row is correct  : {bound:.4f} "
          f"-> gap widens to {0.8929577464788733 - bound:.4f}")
    print("    (a bound, not a measurement -- the per-row outcome needs the "
          "prediction dump)")

    min_root_leak = {
        "lexicon_entries_below_min_root_len": short_entries,
        "n_gold_off_lexicon_free_dev_rows": n_free_off,
        "n_carrying_a_short_entry": len(leak),
        "share": round(len(leak) / n_free_off, 6),
        "reported_lexicon_free_off_recall": reported_recall,
        "upper_bound_recall_if_all_leaked_rows_correct": round(bound, 6),
        "upper_bound_gap": round(0.8929577464788733 - bound, 6),
        "is_a_bound_not_a_measurement": True,
    }

    # length context, since it is the obvious confound
    a_len = sorted(n for _, _, n in a_feat)
    b_len = sorted(n for _, _, n in b_feat)
    print(f"\n  token-count context: A median {percentile(a_len, 0.5):.1f}, "
          f"mean {sum(a_len)/len(a_len):.2f}  |  "
          f"B median {percentile(b_len, 0.5):.1f}, mean {sum(b_len)/len(b_len):.2f}")

    # --- write -------------------------------------------------------------
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True).stdout.strip()
    except Exception:
        sha = "?"

    payload = {
        "run_id": "08_lexical_analysis",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "git_sha": sha,
        "preregistration": "phases/08_lexical_analysis.md",
        "scope": "measurement only; no training, no intervention",
        "inputs": {
            "corpus_sha256": train_sha,
            "lexicon_sha256": data_io.sha256(config.LEXICON_PATH),
            "lexicon_entries": len(lex_list),
            "dev_fingerprint": meta["dev_fingerprint"],
            "split_loaded_not_created": meta["reused_existing_file"],
            "statistics_computed_on": "train split only (C8-1)",
            "n_train": len(train_rows), "n_dev": len(dev_rows),
            "test_set_touched": False,
        },
        "base_rate": {
            "p_off_train_computed": p0,
            "advisor_stated": 0.193,
            "agrees": abs(p0 - 0.193) < 5e-4,
        },
        "class_balance": balances,
        "thresholds": {
            "top_n": TOP_N, "alpha_familywise": ALPHA, "n_tests": TOP_N,
            "z_threshold": round(z_thresh, 6),
            "effect_ratio": EFFECT_RATIO,
            "p_hat_floor_off": round(hi, 6), "p_hat_ceiling_not": round(lo, 6),
        },
        "ranked_table_top200": table,
        "group_sizes": {k: len(v) for k, v in groups.items()},
        "group2_tokens": sorted(group2),
        "group3_tokens": sorted(group3),
        "step3": {
            "n_noprof_fp": len(a_src),
            "n_true_negatives": len(tn_rows),
            "quartile_edges": edges,
            "primary": primary,
            "verdict": v,
            "group2_token_row_counts_in_A": dict(a_tok_counts.most_common()),
        },
        "sensitivities": {
            "wider_pool": {
                "df_min": WIDE_DF_MIN, "n_candidates": len(wide_table),
                "z_threshold": round(z_wide, 6),
                "n_group2": len(wide_group2),
                "group2_tokens": sorted(wide_group2),
                "comparison": wide_cmp,
                "verdict": verdict(wide_cmp["diff_matched"],
                                   wide_cmp["diff_matched_ci"]),
            },
            "group3_control": g3_cmp,
            "token_count": {
                "a_mean": sum(a_len) / len(a_len), "a_median": percentile(a_len, 0.5),
                "b_mean": sum(b_len) / len(b_len), "b_median": percentile(b_len, 0.5),
            },
        },
        "posthoc_exploratory": {
            "WARNING": ("Decided after seeing the ranked list. Exploratory, not "
                        "confirmatory; subsets are the assistant's semantic judgment "
                        "of Turkish tokens, not a measurement. No verdict field is "
                        "emitted for these deliberately."),
            "subsets": posthoc,
            "min_root_len_blind_spot": min_root_leak,
        },
        "limitations_declared_in_advance": "phases/08_lexical_analysis.md C8-10",
    }

    out = out_dir / "token_stats.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwritten -> {out}  ({out.stat().st_size:,} bytes)")
    # No Drive mirror: this phase runs locally on CPU, writes one small JSON of
    # aggregates, and that file is committed. The mirror exists for outputs that
    # are gitignored or born in a Colab session that gets wiped; neither applies.
    print("=" * 96)


if __name__ == "__main__":
    main()
