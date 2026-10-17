from __future__ import annotations

import re

from .. import i18n

CALLBACK_STOPWORDS = {
    "about",
    "again",
    "always",
    "because",
    "every",
    "maybe",
    "still",
    "their",
    "there",
    "thing",
    "this",
    "those",
    "where",
    "which",
    "while",
    "would",
}

HIGH_AFFECT_CALLBACK_MARKERS = {
    "i remember",
    "last time",
    "again with",
    "you said this",
    "same argument",
    "we already did this",
}


def truncate(text: str, max_chars: int) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def sanitize_prompt_memory_text(text: str, max_chars: int = 120) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if not text:
        return ""
    text = re.sub(r"\bI (?:upvoted|downvoted|liked)\b.*?(?:[.!?]|$)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:upvote|downvote|like|vote)\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip(" |,.-")
    return truncate(text, max_chars)


def is_vote_artifact(
    *,
    text_value: str = "",
    event_type: str = "",
    relation_label: str = "",
    metadata: dict | None = None,
) -> bool:
    haystack = " ".join(
        [
            str(text_value or ""),
            str(event_type or ""),
            str(relation_label or ""),
            str((metadata or {}).get("source_event") or ""),
        ]
    ).lower()
    return any(token in haystack for token in ("upvote", "downvote", "liked", "vote"))


def reply_references_recalled_item(
    reply_text: str, recalled_items: list[dict], language: str | None = None
) -> tuple[bool, str]:
    if not isinstance(reply_text, str) or not reply_text.strip():
        return False, "empty_reply"
    if not isinstance(recalled_items, list) or not recalled_items:
        return False, "no_recalled_items"

    normalized_reply = re.sub(r"\s+", " ", reply_text).strip().lower()
    if i18n.contains_any(normalized_reply, "lex__callback_markers", language):
        return True, "callback_marker"

    stopwords = i18n.stopwords(language)

    reply_tokens = {
        token
        for token in i18n.tokens_of(normalized_reply, language)
        if len(token) >= 4 and token not in stopwords
    }
    if not reply_tokens:
        return False, "no_reply_tokens"

    for item in recalled_items:
        memory_text = str(item.get("text") or "").strip().lower()
        if not memory_text:
            continue
        memory_tokens = {
            token
            for token in i18n.tokens_of(memory_text, language)
            if len(token) >= 4 and token not in stopwords
        }
        if len(reply_tokens.intersection(memory_tokens)) >= 2:
            return True, "keyword_overlap"
    return False, "missing_callback"
