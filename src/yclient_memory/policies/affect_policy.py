from __future__ import annotations

import re

from .. import i18n


def detect_high_affect_signal(
    *,
    incoming_text: str,
    prior_match: bool = False,
    llm_classifier: callable | None = None,
    rule_threshold: float = 0.55,
    uncertain_low: float = 0.35,
    uncertain_high: float = 0.70,
    language: str | None = None,
) -> dict:
    text = str(incoming_text or "").lower()
    triggers = {
        "criticism_or_challenge": i18n.contains_any(text, "lex__criticism", language),
        "conflict_or_argument": i18n.contains_any(text, "lex__conflict", language),
        "incoming_anecdote": i18n.contains_any(text, "lex__anecdote", language),
        "defending_prior_opinion": prior_match or i18n.contains_any(text, "lex__prior", language),
    }
    score = (
        0.40 * triggers["criticism_or_challenge"]
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
