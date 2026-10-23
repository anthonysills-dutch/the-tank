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


def summarize(y, p, threshold=0.5):
    yhat = [pi >= threshold for pi in p]
    return {
        "n": len(y),
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
