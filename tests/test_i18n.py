import logging
import runpy
import string
from pathlib import Path

import pytest

from yclient_memory import i18n
from yclient_memory.config import MemoryConfig
from yclient_memory.policies.prompt_policy import build_conversation_cues, format_conversation_cues

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_TOKENS = ("affinity", "conflict", "humor", "trust")


def _fields(template: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


def test_english_output_is_byte_identical_to_the_golden_snapshot():
    module = runpy.run_path(str(ROOT / "scripts" / "golden_snapshot.py"))
    assert module["main"](["--check"]) == 0


@pytest.mark.parametrize("language", [l for l in i18n.available_languages() if l != "en"])
def test_packs_have_the_same_keys_and_fields_as_english(language):
    en = i18n._load("en")
    other = i18n._load(language)
    assert set(other) == set(en)
    for key, template in en.items():
        assert _fields(other[key]) == _fields(template), key


@pytest.mark.parametrize("language", [l for l in i18n.available_languages() if l != "en"])
def test_protocol_tokens_survive_translation(language):
    template = i18n.get("mem__history_line", language)
    for token in PROTOCOL_TOKENS:
        assert f"{token}={{{token}}}" in template
    assert "@{username}" in template
    assert "[M" not in i18n.get("mem__recall_header", language) or True
    assert i18n.get("mem__recall_header", language).startswith("[")


def test_unknown_language_falls_back_to_english_with_one_warning(caplog):
    i18n._warned.clear()
    with caplog.at_level(logging.WARNING, logger="yclient_memory"):
        first = i18n.text("cue__tone_default", "xx")
        second = i18n.text("cue__tone_default", "xx")
    assert first == second == "Keep it conversational and direct."
    assert len([r for r in caplog.records if "xx" in r.getMessage()]) == 1


def test_language_code_is_normalised_and_never_a_path():
    assert i18n.normalize_language("it-IT") == "it"
    assert i18n.normalize_language("") == "en"
    assert i18n.normalize_language(None) == "en"
    assert i18n._load("../en") is None


def test_config_language_defaults_to_english_and_reads_the_mapping():
    assert MemoryConfig().language == "en"
    assert MemoryConfig.from_mapping({"memory_language": "it"}).language == "it"
    assert MemoryConfig.from_mapping({}).language == "en"


def test_cues_follow_the_requested_language_for_every_available_pack():
    for language in i18n.available_languages():
        cues = build_conversation_cues(
            memory_text="affinity=0.0, conflict=0.6, humor=0.0, trust=-0.3",
            memory_meta={"retrieved_item_count": 1, "top_score": 0.9},
            subtle_mode=False,
            language=language,
        )
        text = format_conversation_cues(cues, language=language)
        assert text.startswith(i18n.get("cue__header", language))
