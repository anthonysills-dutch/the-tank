"""Consistency: does a Shark model give the same verdict when it judges the same pitch twice? No API calls.

    python eval/claude_code.py prepare repeat --shark cuban --test-on 7-8 --n 45
    ... one subagent per batch (the /tank-eval skill) ...
    python eval/claude_code.py collect repeat --shark cuban
    python eval/consistency.py --shark cuban

A buyer runs a pitch once. If a second run would flip the decision, the first answer was noise.
Gate (all must hold, on pitches with two valid verdicts):
  - decision agreement >= 90%
  - signal agreement (ABOVE / USUAL / BELOW against the Shark's offer rate) >= 80%
  - mean |p1 - p2| <= 0.05
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tank import ROOT  # noqa: E402

RESULTS = ROOT / "eval" / "results"
BARS = {"decision_agreement": 0.90, "signal_agreement": 0.80, "mean_abs_dp": 0.05}
MIN_PAIRS = 20


def signal(p, rate):
    """Same rule as package_src/system/procedures/judge-as-a-shark.md, step 3.7."""
    if p >= 1.5 * rate:
        return "ABOVE"
    if p <= rate * 2 / 3:
        return "BELOW"
    return "USUAL"


def pairs_from(rows):
    by = defaultdict(dict)
    for r in rows:
        if r.get("verdict") and r.get("run") in (1, 2):
            by[r["pitch_id"]][r["run"]] = r["verdict"]
    return [(pid, v[1], v[2]) for pid, v in by.items() if 1 in v and 2 in v]


def consistency(pairs, rate):
    n = len(pairs)
    dps = [abs(float(a["p_invest"]) - float(b["p_invest"])) for _, a, b in pairs]
    both_in = [(a, b) for _, a, b in pairs if a["decision"] == b["decision"] == "in"]
    eq = [abs(a["offer"]["equity_pct"] - b["offer"]["equity_pct"]) for a, b in both_in
          if a["offer"].get("equity_pct") is not None and b["offer"].get("equity_pct") is not None]
    return {
        "pairs": n,
        "decision_agreement": sum(a["decision"] == b["decision"] for _, a, b in pairs) / n,
        "signal_agreement": sum(signal(float(a["p_invest"]), rate) == signal(float(b["p_invest"]), rate)
                                for _, a, b in pairs) / n,
        "mean_abs_dp": sum(dps) / n,
        "max_abs_dp": max(dps),
        "both_in": len(both_in),
        "median_equity_gap": sorted(eq)[len(eq) // 2] if eq else None,
    }


def gate(m):
    if m["pairs"] < MIN_PAIRS:
        return "INSUFFICIENT DATA", [f"need >= {MIN_PAIRS} pairs; have {m['pairs']}"]
    fails = []
    if m["decision_agreement"] < BARS["decision_agreement"]:
        fails.append(f"decision agreement {m['decision_agreement']:.0%} < {BARS['decision_agreement']:.0%}")
    if m["signal_agreement"] < BARS["signal_agreement"]:
        fails.append(f"signal agreement {m['signal_agreement']:.0%} < {BARS['signal_agreement']:.0%}")
    if m["mean_abs_dp"] > BARS["mean_abs_dp"]:
        fails.append(f"mean |dp| {m['mean_abs_dp']:.3f} > {BARS['mean_abs_dp']}")
    return ("PASS" if not fails else "FAIL"), fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shark", required=True)
    ap.add_argument("--model", default="claude-code")
    args = ap.parse_args()
    src = RESULTS / f"repeat_{args.shark}_{args.model}.jsonl"
    base = RESULTS / f"baselines_{args.shark}.json"
    if not src.exists():
        raise SystemExit(f"No repeat results. Run: python eval/claude_code.py prepare repeat --shark {args.shark}")
    if not base.exists():
        raise SystemExit(f"Run eval/baselines.py --shark {args.shark} first (it gives the offer rate).")
    rate = json.loads(base.read_text(encoding="utf-8"))["train_invest_rate"]
    rows = [json.loads(l) for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]
    pairs = pairs_from(rows)
    if not pairs:
        raise SystemExit("No pitch has two valid verdicts yet.")
    m = consistency(pairs, rate)
    result, fails = gate(m)
    gap = "n/a" if m["median_equity_gap"] is None else f"{m['median_equity_gap']:g} points"
    out = [f"# Consistency: {args.shark} on {args.model}", "", f"**Verdict: {result}**", "",
           f"{m['pairs']} pitches judged twice, in separate batches. Offer rate used for the signal: {rate:.3f}.", "",
           "| measure | value | bar |", "|---|---|---|",
           f"| decision agreement | {m['decision_agreement']:.1%} | >= {BARS['decision_agreement']:.0%} |",
           f"| signal agreement | {m['signal_agreement']:.1%} | >= {BARS['signal_agreement']:.0%} |",
           f"| mean abs. change in p | {m['mean_abs_dp']:.3f} | <= {BARS['mean_abs_dp']} |",
           f"| largest change in p | {m['max_abs_dp']:.3f} | |",
           f"| both runs IN | {m['both_in']} | |",
           f"| median equity gap when both IN | {gap} | |",
           ""]
    if fails:
        out += ["Failed: " + "; ".join(fails), ""]
    report = "\n".join(out)
    path = RESULTS / f"consistency_{args.shark}_{args.model}.md"
    path.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {path.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
