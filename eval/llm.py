"""Shared Claude API plumbing for the eval scripts: one JSON-schema call, a cost estimate, a spend gate.

Every script that calls the model prints an estimate first and refuses to run without --yes.
"""

import json
import sys

# $ per million tokens (input, output), Anthropic first-party rates as of 2026-10.
PRICES = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-fable-5-1": (10.00, 50.00),
}
# Models that accept the server-side refusal fallback in its "default" form.
FALLBACK_MODELS = {"claude-opus-5-5", "claude-sonnet-5-5", "claude-fable-5-1"}
# Rough output allowance per call, thinking included. Deliberately pessimistic.
EST_OUTPUT_TOKENS = 1500


def estimate(model, prompts):
    """prompts: list of (system, user) strings. Returns (input_tokens, output_tokens, dollars)."""
    tin = sum(len(s) + len(u) for s, u in prompts) / 3.5
    tout = EST_OUTPUT_TOKENS * len(prompts)
    pin, pout = PRICES.get(model, (None, None))
    cost = None if pin is None else tin / 1e6 * pin + tout / 1e6 * pout
    return int(tin), int(tout), cost


def gate(model, prompts, yes, what):
    tin, tout, cost = estimate(model, prompts)
    price = f"~${cost:,.2f}" if cost is not None else "unknown (model not in price table)"
    print(f"{what}: {len(prompts)} calls on {model}, ~{tin:,} input + ~{tout:,} output tokens, {price}")
    if not yes:
        print("Dry run. Re-run with --yes to spend this.")
        sys.exit(0)


def client():
    try:
        import anthropic
    except ImportError:
        raise SystemExit("pip install anthropic")
    return anthropic.Anthropic()


def call_json(c, model, system, user, schema, effort="medium", max_tokens=8000):
    """One structured-output call. Returns (parsed_dict | None, error_string | None, usage)."""
    import anthropic

    kwargs = dict(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        cache_control={"type": "ephemeral"},
    )
    if model in FALLBACK_MODELS:
        kwargs.update(betas=["server-side-fallback-2026-07-01"], fallbacks="default")
    try:
        resp = c.beta.messages.create(**kwargs)
    except anthropic.RateLimitError as e:
        return None, f"rate_limited: {e}", None
    except anthropic.BadRequestError as e:
        return None, f"bad_request: {e}", None
    except anthropic.APIStatusError as e:
        return None, f"api_error {e.status_code}: {e}", None
    except anthropic.APIConnectionError as e:
        return None, f"connection: {e}", None

    usage = {"input": resp.usage.input_tokens, "output": resp.usage.output_tokens}
    if resp.stop_reason == "refusal":
        return None, "refusal", usage
    if resp.stop_reason == "max_tokens":
        return None, "max_tokens", usage
    text = next((b.text for b in resp.content if b.type == "text"), None)
    if text is None:
        return None, "no_text_block", usage
    try:
        return json.loads(text), None, usage
    except json.JSONDecodeError as e:
        return None, f"bad_json: {e}", usage
