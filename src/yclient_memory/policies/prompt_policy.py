from __future__ import annotations

import random
import re

from .. import i18n
from ..contracts import MemoryCueSet


def _extract_metric(memory_text: str, name: str, default: float = 0.0) -> float:
    match = re.search(rf"{name}\s*=\s*([-+]?\d+(?:\.\d+)?)", memory_text or "", flags=re.IGNORECASE)
    if not match:
        return default
    try:
        return float(match.group(1))
    except ValueError:
        return default


def build_conversation_cues(
    *,
    memory_text: str,
    memory_meta: dict,
    subtle_mode: bool,
    target_username: str | None = None,
    nuance_enabled: bool = True,
    min_score: float = 0.35,
    callback_probability: float = 0.55,
    language: str | None = None,
) -> MemoryCueSet:
    if not nuance_enabled:
        return MemoryCueSet()

    retrieved = int(memory_meta.get("retrieved_item_count", 0) or 0)
    top_score = memory_meta.get("top_score")
    degraded_mode = bool(memory_meta.get("degraded_mode", False))
    embedding_degraded = bool(memory_meta.get("embedding_degraded", False))
    no_ready_candidates = bool(memory_meta.get("no_ready_candidates", False))
    continuity_text = str(memory_meta.get("continuity_text") or "").strip()
    cross_thread_callback_candidate = bool(memory_meta.get("cross_thread_callback_candidate", False))

    if subtle_mode:
        callback_probability = min(callback_probability, 0.12)
        min_score = max(min_score, 0.80)

    scope = "none"
    if embedding_degraded and retrieved <= 0:
        scope = "degraded"
    elif no_ready_candidates and retrieved <= 0:
        scope = "cold_start"
    elif retrieved > 0 and top_score is not None and float(top_score) >= min_score:
        scope = "strong"
    elif retrieved > 0:
        scope = "partial"

    affinity = _extract_metric(memory_text, "affinity")
    conflict = _extract_metric(memory_text, "conflict")
    humor = _extract_metric(memory_text, "humor")
    trust = _extract_metric(memory_text, "trust")

    def t(key: str, **fields) -> str:
        return i18n.text(key, language, **fields)

    target = f"@{str(target_username or '').lstrip('@')}" if target_username else t("cue__target_fallback")
    should_callback = False
    if scope == "strong" and cross_thread_callback_candidate:
        should_callback = random.random() <= callback_probability
    elif scope == "partial" and not subtle_mode:
        should_callback = random.random() <= min(0.25, callback_probability * 0.4)

    if scope == "degraded":
        callback_hint = t("cue__callback_degraded")
    elif scope == "cold_start":
        callback_hint = t("cue__callback_cold_start")
    elif subtle_mode and cross_thread_callback_candidate:
        callback_hint = t("cue__callback_subtle", target=target)
    elif should_callback:
        callback_hint = t("cue__callback_natural", target=target)
    elif scope == "partial":
        callback_hint = t("cue__callback_partial")
    else:
        callback_hint = t("cue__callback_none")

    if conflict - affinity >= 0.2:
        argument_hint = t("cue__argument_clash")
    elif affinity - conflict >= 0.2:
        argument_hint = t("cue__argument_align")
    else:
        argument_hint = t("cue__argument_balance")

    if degraded_mode:
        tone_hint = t("cue__tone_degraded")
    elif trust <= -0.2 or conflict >= 0.55:
        tone_hint = t("cue__tone_skeptical")
    elif humor >= 0.25 and trust >= 0.0:
        tone_hint = t("cue__tone_banter")
    else:
        tone_hint = t("cue__tone_default")

    if subtle_mode:
        anecdote_hint = t("cue__anecdote_subtle")
    elif should_callback and (trust >= 0.15 or humor >= 0.25):
        anecdote_hint = t("cue__anecdote_supported")
    elif conflict >= 0.5:
        anecdote_hint = t("cue__anecdote_argument")
    else:
        anecdote_hint = t("cue__anecdote_default")

    return MemoryCueSet(
        scope=scope,
        callback_hint=callback_hint,
        continuity_hint=continuity_text,
        argument_hint=argument_hint,
        tone_hint=tone_hint,
        anecdote_hint=anecdote_hint,
        should_callback=should_callback,
        extra={
            "retrieved_item_count": retrieved,
            "top_score": top_score,
            "degraded_mode": degraded_mode,
        },
    )


def format_conversation_cues(cues: MemoryCueSet, max_chars: int = 900, language: str | None = None) -> str:
    if cues.scope == "none" and not cues.extra.get("retrieved_item_count") and not cues.extra.get("degraded_mode"):
        return ""
    def t(key: str, **fields) -> str:
        return i18n.text(key, language, **fields)

    lines = [
        t("cue__header"),
        t("cue__line_scope", value=cues.scope),
    ]
    if cues.callback_hint:
        lines.append(t("cue__line_callback", value=cues.callback_hint))
    if cues.continuity_hint:
        lines.append(t("cue__line_continuity", value=cues.continuity_hint))
    if cues.argument_hint:
        lines.append(t("cue__line_argument", value=cues.argument_hint))
    if cues.tone_hint:
        lines.append(t("cue__line_tone", value=cues.tone_hint))
    if cues.anecdote_hint:
        lines.append(t("cue__line_anecdote", value=cues.anecdote_hint))
    lines.append(t("cue__footer"))
    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[: max_chars - 3].rstrip() + "..."
    return text
