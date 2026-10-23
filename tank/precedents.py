"""Find past pitches a Shark saw that resemble a new one, and what the Shark did.

Plain TF-IDF cosine over industry + anonymized description, nudged by valuation closeness.
In a backtest, pass only training-split records as the pool so no test answer leaks in.
"""

import hashlib
import math
import re
from collections import Counter

from .data import seen_by

TOKEN = re.compile(r"[a-z]{3,}")
DROP = {"company", "founder", "website", "product", "products", "that", "with", "their", "which", "from", "this", "they"}


def _tokens(card):
    text = f"{card.get('industry') or ''} {card.get('industry') or ''} {card.get('description') or ''}".lower()
    return [t for t in TOKEN.findall(text) if t not in DROP]


def _vector(tokens, idf):
    tf = Counter(tokens)
    vec = {t: c * idf.get(t, 0.0) for t, c in tf.items()}
    norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
    return {t: v / norm for t, v in vec.items()}


def opaque_id(pitch_id):
    """Pitch ids encode season and episode, which a model could use to recall the real episode."""
    return "P-" + hashlib.sha1(pitch_id.encode()).hexdigest()[:6]


def describe_outcome(record, slug):
    s = record["outcome"]["per_shark"][slug]
    if not s["invested"]:
        return "passed"
    parts = []
    if s["amount"]:
        parts.append(f"${s['amount']:,.0f}")
    if s["equity_pct"]:
        parts.append(f"for {s['equity_pct']:g}%")
    others = sum(1 for k, v in record["outcome"]["per_shark"].items() if k != slug and v["invested"])
    if others:
        parts.append(f"alongside {others} other Shark{'s' if others > 1 else ''}")
    if record["outcome"]["royalty"]:
        parts.append("(deal included a royalty)")
    return "invested " + " ".join(parts) if parts else "invested"


def retrieve(card, pool, slug, k=6, exclude_ids=()):
    candidates = [r for r in seen_by(pool, slug) if r["pitch_id"] not in set(exclude_ids)]
    if not candidates:
        return []
    docs = [_tokens(r["card"]) for r in candidates]
    df = Counter(t for d in docs for t in set(d))
    n = len(docs)
    idf = {t: math.log((1 + n) / (1 + c)) + 1 for t, c in df.items()}
    q = _vector(_tokens(card), idf)
    qv = card.get("implied_valuation")

    scored = []
    for rec, toks in zip(candidates, docs):
        dv = _vector(toks, idf)
        sim = sum(w * dv.get(t, 0.0) for t, w in q.items())
        rv = rec["card"].get("implied_valuation")
        if qv and rv and qv > 0 and rv > 0:
            sim += 0.15 * math.exp(-abs(math.log(qv / rv)))
        scored.append((sim, rec))
    scored.sort(key=lambda x: x[0], reverse=True)

    # Keep both outcomes in view: a list of only passes teaches nothing about what wins this Shark over.
    top = [r for _, r in scored[: k * 3]]
    ins = [r for r in top if r["outcome"]["per_shark"][slug]["invested"]][: max(1, k // 3)]
    rest = [r for r in top if r not in ins][: k - len(ins)]
    picked = sorted(ins + rest, key=top.index)

    return [
        {
            "precedent_id": opaque_id(r["pitch_id"]),
            "industry": r["card"]["industry"],
            "description": r["card"]["description"],
            "ask_amount": r["card"]["ask_amount"],
            "ask_equity_pct": r["card"]["ask_equity_pct"],
            "implied_valuation": r["card"]["implied_valuation"],
            "shark_decision": describe_outcome(r, slug),
        }
        for r in picked
    ]
