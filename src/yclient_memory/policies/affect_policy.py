from __future__ import annotations

import re


def detect_high_affect_signal(
    *,
    incoming_text: str,
    prior_match: bool = False,
    llm_classifier: callable | None = None,
    rule_threshold: float = 0.55,
    uncertain_low: float = 0.35,
    uncertain_high: float = 0.70,
) -> dict:
    text = str(incoming_text or "").lower()
    triggers = {
        "criticism_or_challenge": any(token in text for token in ("wrong", "source", "evidence", "prove", "?")),
        "conflict_or_argument": any(token in text for token in ("wrong", "bullshit", "nonsense", "cope", "argue")),
        "incoming_anecdote": any(token in text for token in ("i had", "i was", "my experience", "once")),
        "defending_prior_opinion": prior_match or any(
            token in text for token in ("last time", "again", "you said this", "same take")
        ),
    }
    score = (
        0.30 * triggers["criticism_or_challenge"]
        + 0.35 * triggers["conflict_or_argument"]
        + 0.15 * triggers["incoming_anecdote"]
        + 0.30 * triggers["defending_prior_opinion"]
    )
    source = "rules"
    used_llm_fallback = False

    if uncertain_low <= score <= uncertain_high and llm_classifier is not None:
        llm_result = dict(llm_classifier(incoming_text=incoming_text) or {})
        if llm_result:
            used_llm_fallback = True
            source = "hybrid"
            for key in triggers:
                if key in llm_result:
                    triggers[key] = bool(llm_result[key])
            score = max(score, float(llm_result.get("confidence", 0.0) or 0.0))

    return {
        "is_high_affect": score >= rule_threshold,
        "confidence": round(score, 2),
        "source": source,
        "used_llm_fallback": used_llm_fallback,
        "prior_match": prior_match,
        "triggers": triggers,
    }
