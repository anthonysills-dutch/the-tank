"""Scoring. Accuracy alone is a trap here: most Sharks pass on most pitches, so "always out" looks great."""

import math
import random


def brier(y, p):
    return sum((pi - yi) ** 2 for yi, pi in zip(y, p)) / len(y)


def log_loss(y, p, eps=1e-6):
    return -sum(yi * math.log(max(pi, eps)) + (1 - yi) * math.log(max(1 - pi, eps)) for yi, pi in zip(y, p)) / len(y)


def confusion(y, yhat):
    tp = sum(1 for a, b in zip(y, yhat) if a and b)
    tn = sum(1 for a, b in zip(y, yhat) if not a and not b)
    fp = sum(1 for a, b in zip(y, yhat) if not a and b)
    fn = sum(1 for a, b in zip(y, yhat) if a and not b)
    return tp, tn, fp, fn


def balanced_accuracy(y, yhat):
    tp, tn, fp, fn = confusion(y, yhat)
    tpr = tp / (tp + fn) if tp + fn else 0.0
    tnr = tn / (tn + fp) if tn + fp else 0.0
    return (tpr + tnr) / 2


def f1_in(y, yhat):
    tp, _, fp, fn = confusion(y, yhat)
    return 2 * tp / (2 * tp + fp + fn) if tp else 0.0


def auc(y, p):
    """Probability that a random real offer ranks above a random pass. 0.5 is a coin flip. None if a class is empty."""
    pos = [pi for yi, pi in zip(y, p) if yi]
    neg = [pi for yi, pi in zip(y, p) if not yi]
    if not pos or not neg:
        return None
    wins = sum((a > b) + 0.5 * (a == b) for a in pos for b in neg)
    return wins / (len(pos) * len(neg))


def calibration_bins(y, p, bins=3):
    """Sort by p, cut into equal-size bins, and compare the mean prediction with the real offer rate in each."""
    order = sorted(range(len(y)), key=lambda i: p[i])
    size = max(1, len(order) // bins)
    out = []
    for b in range(bins):
        idx = order[b * size:] if b == bins - 1 else order[b * size:(b + 1) * size]
        if idx:
            out.append({"n": len(idx), "mean_p": sum(p[i] for i in idx) / len(idx),
                        "offer_rate": sum(y[i] for i in idx) / len(idx)})
    return out


def summarize(y, p, threshold=0.5):
    """p at or above threshold counts as 'in'. Pass the Shark's training offer rate, not 0.5:
    calibrated probabilities for a Shark who invests in 15% of pitches rarely reach 0.5."""
    yhat = [pi >= threshold for pi in p]
    return {
        "n": len(y),
        "threshold": threshold,
        "auc": auc(y, p),
        "positives": sum(y),
        "accuracy": sum(1 for a, b in zip(y, yhat) if a == b) / len(y),
        "balanced_accuracy": balanced_accuracy(y, yhat),
        "f1_in": f1_in(y, yhat),
        "brier": brier(y, p),
        "log_loss": log_loss(y, p),
    }


def bootstrap_diff(y, p_a, p_b, metric=brier, n=2000, seed=7):
    """95% CI for metric(a) - metric(b). For Brier, a negative upper bound means a is reliably better."""
    rng = random.Random(seed)
    idx = list(range(len(y)))
    diffs = []
    for _ in range(n):
        s = [rng.choice(idx) for _ in idx]
        ys = [y[i] for i in s]
        diffs.append(metric(ys, [p_a[i] for i in s]) - metric(ys, [p_b[i] for i in s]))
    diffs.sort()
    return diffs[int(0.025 * n)], diffs[int(0.975 * n)]
