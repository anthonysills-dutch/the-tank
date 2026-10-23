"""Score a Shark model against the baselines and apply the pass gate. No API calls.

    python eval/baselines.py --shark cuban
    python eval/score.py --shark cuban --model claude-opus-5-5

Pass gate (judged on pitches the model did NOT recognize in the memorization probe):
  1. Brier score beats the best baseline, with the 95% bootstrap CI of the difference below zero
  2. F1 on "in" beats both the logistic baseline and random guessing at the offer rate
If no probe has been run, the gate is reported as UNVERIFIED: a pass there may just be recall.
"""

import argparse
import json
import math
import sys
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tank import PROCESSED, ROOT  # noqa: E402
from tank.data import load_jsonl  # noqa: E402
from tank.metrics import bootstrap_diff, brier, f1_in, summarize  # noqa: E402

RESULTS = ROOT / "eval" / "results"
MIN_N = 30


def read_jsonl(path):
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()] if Path(path).exists() else []


def table(y, preds):
    rows = ["| model | n | acc | bal. acc | F1 (in) | Brier | log loss |", "|---|---|---|---|---|---|---|"]
    for name, p in preds.items():
        m = summarize(y, p)
        rows.append(f"| {name} | {m['n']} | {m['accuracy']:.3f} | {m['balanced_accuracy']:.3f} | "
                    f"{m['f1_in']:.3f} | {m['brier']:.4f} | {m['log_loss']:.3f} |")
    return "\n".join(rows)


def gate(y, preds):
    if len(y) < MIN_N or sum(y) < 5:
        return "INSUFFICIENT DATA", f"need >= {MIN_N} pitches and >= 5 real offers; have {len(y)} / {sum(y)}"
    best = min(("base_rate", "logistic"), key=lambda k: brier(y, preds[k]))
    lo, hi = bootstrap_diff(y, preds["llm"], preds[best])
    f1_llm = f1_in(y, [p >= 0.5 for p in preds["llm"]])
    f1_log = f1_in(y, [p >= 0.5 for p in preds["logistic"]])
    # Saying "in" at random, at the true offer rate, scores an expected F1 equal to that rate.
    f1_bar = max(f1_log, sum(y) / len(y))
    ok = hi < 0 and f1_llm > f1_bar
    detail = (f"Brier(llm) - Brier({best}) 95% CI [{lo:+.4f}, {hi:+.4f}] "
              f"({'reliably better' if hi < 0 else 'not reliably better'}); "
              f"F1 in: llm {f1_llm:.3f} vs bar {f1_bar:.3f} (max of logistic, random at the offer rate)")
    return ("PASS" if ok else "FAIL"), detail


def offer_error(rows, truth, slug):
    eq_err, amt_err = [], []
    for row in rows:
        v, actual = row["verdict"], truth[row["pitch_id"]]["outcome"]["per_shark"][slug]
        if v["decision"] != "in" or not actual["invested"]:
            continue
        if v["offer"]["equity_pct"] is not None and actual["equity_pct"]:
            eq_err.append(abs(v["offer"]["equity_pct"] - actual["equity_pct"]))
        if v["offer"]["amount_usd"] and actual["amount"]:
            amt_err.append(abs(math.log(v["offer"]["amount_usd"] / actual["amount"])))
    if not eq_err and not amt_err:
        return "No overlapping 'in' predictions and real offers to compare terms on."
    parts = []
    if eq_err:
        parts.append(f"median equity error {median(eq_err):.1f} points (n={len(eq_err)})")
    if amt_err:
        parts.append(f"median check-size error x{math.exp(median(amt_err)):.2f} (n={len(amt_err)})")
    return "On pitches where both the model and the real Shark made an offer: " + "; ".join(parts) + "."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shark", required=True)
    ap.add_argument("--model", default="claude-opus-5-5")
    ap.add_argument("--data", default=str(PROCESSED))
    args = ap.parse_args()
    slug = args.shark

    base_path = RESULTS / f"baselines_{slug}.json"
    if not base_path.exists():
        raise SystemExit(f"Run eval/baselines.py --shark {slug} first.")
    base = json.loads(base_path.read_text(encoding="utf-8"))["predictions"]
    truth = {r["pitch_id"]: r for r in load_jsonl(args.data)}
    rows = [r for r in read_jsonl(RESULTS / f"llm_{slug}_{args.model}.jsonl") if r.get("verdict")]
    errors = [r for r in read_jsonl(RESULTS / f"llm_{slug}_{args.model}.jsonl") if r.get("error")]
    probe = {r["pitch_id"]: r.get("match", False) for r in read_jsonl(RESULTS / f"memorization_{args.model}.jsonl") if not r.get("error")}
    if not rows:
        raise SystemExit("No LLM predictions yet. Run eval/run_llm.py.")

    llm = {r["pitch_id"]: min(max(float(r["verdict"]["p_invest"]), 0.0), 1.0) for r in rows}
    ids = [i for i in llm if i in base]
    strata = {"all scored pitches": ids}
    if probe:
        strata["not recognized by the model"] = [i for i in ids if i in probe and not probe[i]]
        strata["recognized by the model"] = [i for i in ids if probe.get(i)]

    out = [f"# Backtest: {slug} on {args.model}", "",
           f"{len(rows)} verdicts scored, {len(errors)} calls errored and are excluded.", ""]
    verdict_line = None
    for title, subset in strata.items():
        if not subset:
            continue
        y = [1 if truth[i]["outcome"]["per_shark"][slug]["invested"] else 0 for i in subset]
        preds = {name: [base[i][name] for i in subset] for name in ("always_out", "base_rate", "logistic")}
        preds["llm"] = [llm[i] for i in subset]
        result, detail = gate(y, preds)
        out += [f"## {title}", "", table(y, preds), "", f"Gate: **{result}**. {detail}", ""]
        if title == "not recognized by the model":
            verdict_line = f"{result} (judged on unrecognized pitches)"
        elif verdict_line is None and not probe:
            verdict_line = f"UNVERIFIED {result} (no memorization probe run; may be recall)"
    out += ["## Offer terms", "", offer_error(rows, truth, slug), ""]
    if probe:
        rec = sum(1 for i in ids if probe.get(i))
        out.insert(3, f"Memorization: model named {rec} of {len([i for i in ids if i in probe])} probed test pitches.")
    out.insert(2, f"**Verdict: {verdict_line}**")

    report = "\n".join(out)
    path = RESULTS / f"report_{slug}_{args.model}.md"
    path.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nWrote {path}")


if __name__ == "__main__":
    main()
