"""The dumb baselines every Shark model has to beat. No API calls, no cost.

    python eval/baselines.py --shark cuban

  always_out  - predicts "out" every time (p = 0). High accuracy, zero usefulness.
  base_rate   - p = the Shark's training-split offer rate, for every pitch.
  logistic    - logistic regression on the structured card only (industry, ask, equity,
                valuation, team, revenue if present). No text, no LLM.

Trains on earlier seasons and predicts the held-out later seasons.
"""

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tank import PROCESSED, ROOT  # noqa: E402
from tank.data import load_jsonl, parse_seasons, seen_by, split  # noqa: E402
from tank.metrics import summarize  # noqa: E402

RESULTS = ROOT / "eval" / "results"
MIN_INDUSTRY = 5


def label(r, slug):
    return 1 if r["outcome"]["per_shark"][slug]["invested"] else 0


class CardFeatures:
    def __init__(self, train):
        counts = Counter(r["card"]["industry"] for r in train)
        self.industries = sorted(i for i, n in counts.items() if i and n >= MIN_INDUSTRY)
        self.has_revenue = any(r["card"].get("yearly_revenue") is not None for r in train)
        raw = [self._numeric(r["card"]) for r in train]
        cols = list(zip(*raw)) if raw else []
        self.mean = [sum(c) / len(c) for c in cols]
        self.std = [math.sqrt(sum((x - m) ** 2 for x in c) / len(c)) or 1.0 for c, m in zip(cols, self.mean)]

    def _numeric(self, card):
        lg = lambda v: math.log1p(v) if v and v > 0 else 0.0  # noqa: E731
        team = {"multiple founders": 1.0, "solo founder": 0.0}.get(card.get("team"), 0.5)
        feats = [lg(card.get("ask_amount")), (card.get("ask_equity_pct") or 0) / 100, lg(card.get("implied_valuation")), team]
        if self.has_revenue:
            rev = card.get("yearly_revenue")
            feats += [lg(rev), 1.0 if rev else 0.0]
        return feats

    def __call__(self, card):
        num = [(x - m) / s for x, m, s in zip(self._numeric(card), self.mean, self.std)]
        ind = [1.0 if card.get("industry") == i else 0.0 for i in self.industries]
        return [1.0] + num + ind


def fit_logistic(X, y, l2=1.0, lr=0.1, iters=800):
    w = [0.0] * len(X[0])
    n = len(X)
    for _ in range(iters):
        grad = [0.0] * len(w)
        for xi, yi in zip(X, y):
            z = sum(a * b for a, b in zip(w, xi))
            p = 1 / (1 + math.exp(-max(min(z, 30), -30)))
            for j, xj in enumerate(xi):
                grad[j] += (p - yi) * xj
        for j in range(len(w)):
            reg = l2 * w[j] if j else 0.0
            w[j] -= lr * (grad[j] + reg) / n
    return w


def predict(w, x):
    z = sum(a * b for a, b in zip(w, x))
    return 1 / (1 + math.exp(-max(min(z, 30), -30)))


def run(records, slug, test_seasons, test_on=None):
    train, test = split(seen_by(records, slug), test_seasons, test_on)
    y_train = [label(r, slug) for r in train]
    rate = sum(y_train) / len(y_train) if y_train else 0.0
    feats = CardFeatures(train)
    w = fit_logistic([feats(r["card"]) for r in train], y_train)

    preds = {
        r["pitch_id"]: {
            "always_out": 0.0,
            "base_rate": rate,
            "logistic": predict(w, feats(r["card"])),
        }
        for r in test
    }
    y_test = [label(r, slug) for r in test]
    report = {
        "shark": slug,
        "train_seasons": sorted({r["season"] for r in train}),
        "test_seasons": sorted({r["season"] for r in test}),
        "train_n": len(train),
        "test_n": len(test),
        "train_invest_rate": rate,
        "metrics": {
            name: summarize(y_test, [preds[r["pitch_id"]][name] for r in test], threshold=rate)
            for name in ("always_out", "base_rate", "logistic")
        } if test else {},
        "predictions": preds,
    }
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shark", required=True)
    ap.add_argument("--test-seasons", type=int, default=3)
    ap.add_argument("--test-on", help="Hold out these seasons instead, e.g. 7,8 or 7-8")
    ap.add_argument("--data", default=str(PROCESSED))
    args = ap.parse_args()

    report = run(load_jsonl(args.data), args.shark, args.test_seasons, parse_seasons(args.test_on))
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / f"baselines_{args.shark}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"train seasons {report['train_seasons']}  test seasons {report['test_seasons']}")
    print(f"train n={report['train_n']}  test n={report['test_n']}  train offer rate={report['train_invest_rate']:.1%}")
    for name, m in report["metrics"].items():
        print(f"  {name:10s} acc {m['accuracy']:.3f}  bal_acc {m['balanced_accuracy']:.3f}  "
              f"f1_in {m['f1_in']:.3f}  brier {m['brier']:.4f}")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
