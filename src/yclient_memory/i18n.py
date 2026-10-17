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


_EN_TOKEN = re.compile(r"[a-z0-9']+")
_WORD_TOKEN = re.compile(r"[a-zà-öø-ÿ0-9']+")
_EN_PLAIN = re.compile(r"[a-z0-9]+")
_WORD_PLAIN = re.compile(r"[a-zà-öø-ÿ0-9]+")


def lexicon(key: str, language: str | None = None) -> tuple[str, ...]:
    """Word list of a keyword heuristic (English fallback, one warning)."""
    value = get_value(key, language)
    return tuple(value)


def get_value(key: str, language: str | None = None):
    code = normalize_language(language)
    pack = _load(code)
    if pack is None:
        _warn_once("language", code)
        pack = _load(DEFAULT_LANGUAGE)
    if key not in pack:
        if code != DEFAULT_LANGUAGE:
            _warn_once("key", f"{code}:{key}")
        pack = _load(DEFAULT_LANGUAGE)
    return pack[key]


def contains_any(text: str, key: str, language: str | None = None) -> bool:
    """True when ``text`` (already lowercase) holds one of the lexicon entries.

    English keeps the plain substring test it always had. Other languages match
    entries that start with a letter at a word start, so a stem such as ``sbagliat``
    covers its inflections without firing in the middle of an unrelated word;
    entries made of symbols (``?``) stay plain substrings.
    """
    tokens = lexicon(key, language)
    if normalize_language(language) == DEFAULT_LANGUAGE:
        return any(token in text for token in tokens)
    for token in tokens:
        if token[:1].isalpha():
            if re.search(r"(?<!\w)" + re.escape(token), text):
                return True
        elif token in text:
            return True
    return False


def tokens_of(text: str, language: str | None = None, *, apostrophe: bool = True) -> list[str]:
    english = normalize_language(language) == DEFAULT_LANGUAGE
    if apostrophe:
        pattern = _EN_TOKEN if english else _WORD_TOKEN
    else:
        pattern = _EN_PLAIN if english else _WORD_PLAIN
    return pattern.findall(text)


def stopwords(language: str | None = None) -> frozenset[str]:
    return frozenset(lexicon("lex__stopwords", language))
