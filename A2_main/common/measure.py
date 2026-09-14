"""
A2_main - TOKEN AND SIZE MEASUREMENT
=====================================================================
One place that counts tokens, so every deliverable counts them the
same way and the report cannot contain two different numbers for the
same thing.

HONESTY RULE, and D6 marks it: `approx_tokens` is an ESTIMATE
(chars / 4). It is fine for comparing v1 against v2, or sequential
against parallel, because both sides are estimated the same way and
the RATIO is what those experiments claim.

It is NOT fine as the headline token count in D6. That number must
come from the usage block the API returns on a live run. Estimating
and calling it measured is exactly what D6 punishes. Anything derived
from this function carries estimated=True so the report can label it.
=====================================================================
"""
import json

CHARS_PER_TOKEN = 4


def approx_tokens(value):
    """Rough token count. See the honesty rule above."""
    if value is None:
        return 0
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False, default=str)
    return len(value) // CHARS_PER_TOKEN


def context_tokens(base_prompt_tokens, per_turn_tokens, turns):
    """Class 5's formula for the input tokens a whole run costs.

        input ~ B*T + D*T(T-1)/2

    B is the prefix re-sent every turn - the tool block, the routing
    rules, the answer format. D is what each turn ADDS to the history.
    The second term is quadratic in T, which is why "doubling the turns
    from eight to sixteen does not double the bill; it nearly triples
    it."

    Returns the total. Both forms in the brief agree to within one D;
    this is the one that drops the 1.
    """
    B, D, T = float(base_prompt_tokens), float(per_turn_tokens), float(turns)
    return B * T + D * (T * (T - 1) / 2.0)


def usd(tokens_in, tokens_out, price_in_per_m, price_out_per_m):
    """Cost of one run at list price, in US dollars."""
    return (tokens_in / 1e6) * price_in_per_m + \
           (tokens_out / 1e6) * price_out_per_m


def observation_tokens(record):
    """Tokens the tool observations added on one run, estimated.

    The decision record keeps `evidence` (which tools ran) but not the
    payloads, so this re-reads nothing: it is here so callers have one
    obvious place to look when they want D rather than B.
    """
    return approx_tokens(record.get("evidence"))


def summarise_runs(results):
    """turns / tokens / cost / pass rate across a list of harness rows."""
    import statistics
    if not results:
        return {"trials": 0}
    turns = [r["record"]["turns"] for r in results]
    tin = sum(r["record"]["tokens_in"] for r in results)
    tout = sum(r["record"]["tokens_out"] for r in results)
    passed = sum(1 for r in results if r["passed"])
    return {
        "trials": len(results),
        "passed": passed,
        "pass_rate": passed / len(results),
        "total_turns": sum(turns),
        "median_turns": statistics.median(turns),
        "max_turns": max(turns),
        "tokens_in": tin,
        "tokens_out": tout,
        "cost_usd": sum(r["record"]["cost_usd"] for r in results),
    }
