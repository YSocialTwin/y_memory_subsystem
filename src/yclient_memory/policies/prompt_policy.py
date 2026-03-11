from __future__ import annotations

import random
import re

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

    target = f"@{str(target_username or '').lstrip('@')}" if target_username else "this user"
    should_callback = False
    if scope == "strong" and cross_thread_callback_candidate:
        should_callback = random.random() <= callback_probability
    elif scope == "partial" and not subtle_mode:
        should_callback = random.random() <= min(0.25, callback_probability * 0.4)

    if scope == "degraded":
        callback_hint = "Memory retrieval is degraded right now. Do not claim specific past interactions."
    elif scope == "cold_start":
        callback_hint = "You have limited interaction history. Focus on the current content."
    elif subtle_mode and cross_thread_callback_candidate:
        callback_hint = f"If clearly relevant, you may use one brief continuity cue with {target}."
    elif should_callback:
        callback_hint = f"If natural, reference one prior exchange with {target} in one short clause."
    elif scope == "partial":
        callback_hint = "Use only soft continuity and stay anchored to the current thread."
    else:
        callback_hint = "No memory callback needed; focus on the current message."

    if conflict - affinity >= 0.2:
        argument_hint = "You often clash here. It is fine to continue the argument, but stay concrete."
    elif affinity - conflict >= 0.2:
        argument_hint = "You often align here. Start from common ground, then add a fresh point."
    else:
        argument_hint = "Balance agreement and pushback based on the latest claim."

    if degraded_mode:
        tone_hint = "Keep tone grounded in the current thread; avoid certainty from memory."
    elif trust <= -0.2 or conflict >= 0.55:
        tone_hint = "Keep a skeptical tone; ask for specifics or challenge weak claims."
    elif humor >= 0.25 and trust >= 0.0:
        tone_hint = "Light banter is okay if it helps the point land."
    else:
        tone_hint = "Keep it conversational and direct."

    if subtle_mode:
        anecdote_hint = "Do not import unrelated anecdotes from other threads."
    elif should_callback and (trust >= 0.15 or humor >= 0.25):
        anecdote_hint = "A tiny shared-memory anecdote is fine, but only if it is clearly supported."
    elif conflict >= 0.5:
        anecdote_hint = "Prefer argument continuity over personal anecdotes."
    else:
        anecdote_hint = "Use anecdotes sparingly; only when they clarify your point."

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


def format_conversation_cues(cues: MemoryCueSet, max_chars: int = 900) -> str:
    if cues.scope == "none" and not cues.extra.get("retrieved_item_count") and not cues.extra.get("degraded_mode"):
        return ""
    lines = [
        "[MEMORY CONVERSATION CUES]",
        f"- scope: {cues.scope}",
    ]
    if cues.callback_hint:
        lines.append(f"- callback: {cues.callback_hint}")
    if cues.continuity_hint:
        lines.append(f"- continuity: {cues.continuity_hint}")
    if cues.argument_hint:
        lines.append(f"- argument: {cues.argument_hint}")
    if cues.tone_hint:
        lines.append(f"- tone: {cues.tone_hint}")
    if cues.anecdote_hint:
        lines.append(f"- anecdote: {cues.anecdote_hint}")
    lines.append("- Never invent people, comments, or events not present in memory context.")
    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[: max_chars - 3].rstrip() + "..."
    return text
