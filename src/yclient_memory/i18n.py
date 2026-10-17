"""Texts that yclient_memory shows to the language model, one pack per language.

Packs live in ``prompts/<language>.json`` and are plain ``str.format`` templates.
Protocol tokens (``affinity``, ``conflict``, ``humor``, ``trust``, ``[M1]`` markers,
``@username``, ``r<N>``) are never translated: other code parses them back.
A missing language or key falls back to English with a single warning.
"""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path

DEFAULT_LANGUAGE = "en"
_PACK_DIR = Path(__file__).with_name("prompts")
_logger = logging.getLogger("yclient_memory")
_warned: set[tuple[str, str]] = set()


def normalize_language(language: str | None) -> str:
    """Return a bare lowercase code (``"it-IT"`` -> ``"it"``); empty means English."""
    code = re.split(r"[-_]", str(language or "").strip().lower())[0]
    return code or DEFAULT_LANGUAGE


@lru_cache(maxsize=None)
def _load(language: str) -> dict[str, str] | None:
    path = _PACK_DIR / f"{language}.json"
    if not re.fullmatch(r"[a-z]{2,3}", language) or not path.is_file():
        return None
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _warn_once(kind: str, name: str) -> None:
    if (kind, name) not in _warned:
        _warned.add((kind, name))
        _logger.warning("yclient_memory: %s %r not found, using English", kind, name)


def available_languages() -> list[str]:
    return sorted(p.stem for p in _PACK_DIR.glob("*.json"))


def has_key(key: str, language: str | None = None) -> bool:
    pack = _load(normalize_language(language))
    return bool(pack) and key in pack


def get(key: str, language: str | None = None) -> str:
    """Return the raw template for ``key`` (English fallback, one warning)."""
    code = normalize_language(language)
    pack = _load(code)
    if pack is None:
        _warn_once("language", code)
        pack = _load(DEFAULT_LANGUAGE)
    if key not in pack:
        if code != DEFAULT_LANGUAGE:
            _warn_once("key", f"{code}:{key}")
        english = _load(DEFAULT_LANGUAGE)
        if key not in english:
            raise KeyError(key)
        return english[key]
    return pack[key]


def text(key: str, language: str | None = None, **fields) -> str:
    template = get(key, language)
    return template.format(**fields) if fields else template


def label(key: str, raw: str, language: str | None = None) -> str:
    """Translate a stored internal value when the pack knows it, else keep it."""
    return get(key, language) if has_key(key, language) else raw
