"""One prompt, two consumers.

The Claude Code agent files (agents/shark-*.md) and the API backtest (eval/run_llm.py) both
render from here, so the backtest scores the same Shark that users talk to.
"""

import json

CARD_LABELS = {
    "industry": "Industry",
    "description": "What it is",
    "ask_amount": "Ask ($)",
    "ask_equity_pct": "Equity offered (%)",
    "implied_valuation": "Implied valuation ($)",
    "team": "Team",
    "yearly_revenue": "Trailing 12-month sales ($)",
    "monthly_revenue": "Monthly sales ($)",
    "gross_margin": "Gross margin (%)",
    "net_margin": "Net margin (%)",
    "has_patents": "Has patents",
    "bootstrapped": "Bootstrapped",
    "customers": "Customers / traction",
    "founder_background": "Founder background",
    "use_of_funds": "Use of funds",
    "other": "Other facts",
}

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["in", "out"]},
        "p_invest": {"type": "number", "description": "Probability 0-1 that this investor makes an offer."},
        "offer": {
            "type": "object",
            "description": "Terms if decision is 'in'; all fields null if 'out'.",
            "properties": {
                "amount_usd": {"type": ["number", "null"]},
                "equity_pct": {"type": ["number", "null"]},
                "royalty": {"type": ["string", "null"]},
                "loan_usd": {"type": ["number", "null"]},
                "conditions": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["amount_usd", "equity_pct", "royalty", "loan_usd", "conditions"],
            "additionalProperties": False,
        },
        "objections": {"type": "array", "items": {"type": "string"}, "description": "Top three, most damaging first."},
        "grill_question": {"type": "string", "description": "The one question this investor would press hardest."},
        "reasoning": {"type": "string", "description": "Three to five sentences, in this investor's lens."},
        "evidence": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Belief ids and precedent ids that drove the verdict.",
        },
    },
    "required": ["decision", "p_invest", "offer", "objections", "grill_question", "reasoning", "evidence"],
    "additionalProperties": False,
}


def _money(v):
    return f"${v:,.0f}" if isinstance(v, (int, float)) else "unknown"


def system_prompt(profile, stats):
    name = profile["name"]
    lines = [
        f"You are an investor model built from {name}'s public record: interviews, writing, and on-air deal history.",
        "You are a simulation, not the person. Never claim to be them, never imply their endorsement, and never quote them except the verbatim lines below.",
        "",
        f"Mode: investor. Judge the pitch the way {name} says they invest, informed by the deals they actually made.",
        f"Lens: {profile['lens']}.",
        "",
        "## Beliefs (cite these ids in `evidence`)",
        "Quoted lines are verified word for word against the cited source. They are the only lines you may quote.",
    ]
    sources = {s["id"]: s for s in profile.get("sources", [])}
    for b in profile["beliefs"]:
        lines.append(f"- [{b['id']}] ({b['weight']}) {b['claim']}")
        if b.get("applies_as"):
            lines.append(f"  How it shows up: {b['applies_as']}")
        for q in b.get("quotes", [])[:2]:
            date = sources.get(q["source"], {}).get("date", "")
            lines.append(f'  Verbatim: "{q["text"]}" ({q["source"]}{", " + date if date and date != "unknown" else ""})')
    if profile.get("misfires"):
        lines += ["", "## Where this lens misfires (adjust instead of applying the beliefs blindly)"]
        lines += [f"- {m['claim']}" for m in profile["misfires"]]
    if profile.get("dealbreakers"):
        lines += ["", "## Dealbreakers"]
        lines += [f"- {d['claim']}" for d in profile["dealbreakers"]]

    lines += ["", "## What the deal record says"]
    lines.append(
        f"- Made an offer on {stats['deals']} of {stats['pitches_seen']} pitches seen "
        f"({stats['invest_rate']:.0%}). Most pitches get an 'out'. Calibrate p_invest to that base rate."
    )
    if stats.get("median_amount"):
        lines.append(f"- Typical check: {_money(stats['median_amount'])} for a median {stats['median_equity_pct']:g}% stake.")
    if stats.get("solo_deal_share") is not None:
        lines.append(f"- Share of their deals done alone (no other Shark): {stats['solo_deal_share']:.0%}.")
    if stats.get("royalty_deal_share") is not None:
        lines.append(f"- Share of their deals with a royalty component: {stats['royalty_deal_share']:.0%}.")
    for label, key in (("Most receptive", "most_receptive_industries"), ("Least receptive", "least_receptive_industries")):
        if stats.get(key):
            items = ", ".join(f"{d['industry']} {d['invest_rate']:.0%} of {d['seen']}" for d in stats[key])
            lines.append(f"- {label} industries: {items}.")

    lines += [
        "",
        "## How to judge",
        "- Decide independently. You have not heard any other investor's view.",
        "- Missing facts count against the pitch the way they would in the room. Do not assume good numbers.",
        "- Similar past pitches and what this investor did are provided. Weigh them; do not copy them.",
        "- Pick the pitch apart: name the specific weaknesses this investor would see, not generic startup advice.",
        "- Even on an 'out', leave the founder with something useful.",
        "- If 'out', set every offer field to null and conditions to [].",
        "- Reply with JSON matching the verdict schema and nothing else.",
    ]
    return "\n".join(lines)


def card_text(card):
    out = []
    for key, label in CARD_LABELS.items():
        v = card.get(key)
        if v is None or v == "":
            continue
        if key in {"ask_amount", "implied_valuation", "yearly_revenue", "monthly_revenue"}:
            v = _money(v)
        out.append(f"- {label}: {v}")
    missing = [CARD_LABELS[k] for k in ("yearly_revenue", "gross_margin") if card.get(k) is None]
    if missing:
        out.append(f"- Not disclosed: {', '.join(missing)}")
    return "\n".join(out)


def pitch_message(card, precedents):
    parts = ["## The pitch", card_text(card), "", "## Similar pitches this investor heard before"]
    if not precedents:
        parts.append("(none on record)")
    for p in precedents:
        parts.append(
            f"- [{p['precedent_id']}] {p['industry']}: {p['description'][:300]} | asked {_money(p['ask_amount'])} "
            f"for {p['ask_equity_pct']}% | {p['shark_decision']}"
        )
    parts += ["", "Give your verdict as JSON."]
    return "\n".join(parts)


def schema_json():
    return json.dumps(VERDICT_SCHEMA, indent=2)
