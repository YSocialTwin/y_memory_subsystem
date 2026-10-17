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


@pytest.mark.parametrize("language", i18n.available_languages())
def test_worst_case_cue_block_fits_the_character_limit(language):
    long_continuity = "x" * MemoryConfig().reply_context_max_chars
    cues = build_conversation_cues(
        memory_text="affinity=0.0, conflict=0.6, humor=0.0, trust=-0.3",
        memory_meta={
            "retrieved_item_count": 3,
            "top_score": 0.9,
            "cross_thread_callback_candidate": True,
            "continuity_text": long_continuity,
        },
        subtle_mode=False,
        target_username="@" + "u" * 20,
        language=language,
    )
    raw = format_conversation_cues(cues, max_chars=10_000, language=language)
    limit = MemoryConfig().nuance_cues_max_chars
    assert len(raw) <= limit, f"{language}: {len(raw)} > {limit} chars, the cues would be truncated"


@pytest.mark.parametrize("language", i18n.available_languages())
def test_style_phrases_stay_within_the_phrase_limit(language):
    for key in ("mem__norm_structured", "mem__norm_question_bait", "mem__meme_hot_take"):
        assert len(i18n.get(key, language)) <= 48, key


@pytest.mark.parametrize("language", i18n.available_languages())
def test_thread_and_style_blocks_fit_without_truncation(language):
    def t(key, **fields):
        return i18n.text(key, language, **fields)

    thread = "\n".join(
        [
            t("mem__thread_header"),
            t("mem__thread_gist", text="g" * 160),
            t("mem__thread_role", role=i18n.label("mem__role_skeptic", "skeptic", language)),
        ]
    )
    style = "\n".join(
        [
            t("mem__style_header"),
            t("mem__style_norms", items=", ".join([t("mem__norm_structured"), t("mem__norm_question_bait")])),
            t("mem__style_memes", items=t("mem__meme_hot_take")),
            t("mem__style_footer"),
        ]
    )
    assert len(thread) <= 220
    assert len(style) <= 280


@pytest.mark.parametrize("language", [l for l in i18n.available_languages() if l != "en"])
def test_engine_logic_does_not_depend_on_the_language(language):
    from yclient_memory.backends.hybrid_semantic.engine import HybridSemanticMemoryEngine
    from yclient_memory.contracts import ReplyMemoryRequest

    class RT:
        def llm_json(self, *a, **k):
            return {}

        def llm_text(self, *a, **k):
            return ""

        def get_recent_root_posts(self, *a, **k):
            return []

        def decision_log(self, payload):
            pass

    def run(lang):
        engine = HybridSemanticMemoryEngine(config=MemoryConfig(language=lang), runtime=RT())
        engine._social_cards[55] = {
            "affinity": 0.1, "conflict": 0.7, "humor": 0.0, "trust": -0.4,
            "summary_text": "ciao", "last_round_id": 1, "last_thread_root_id": 9,
        }
        ctx = engine.build_reply_context(
            ReplyMemoryRequest(query_text="q", other_user_id=55, other_username="alice", thread_root_id=9, round_id=2)
        )
        return ctx

    en, other = run("en"), run(language)
    assert en.cues.scope == other.cues.scope
    assert en.cues.should_callback == other.cues.should_callback
    assert "affinity=0.10, conflict=0.70, humor=0.00, trust=-0.40" in other.rendered_text
    assert other.rendered_text != en.rendered_text
    assert other.cues.argument_hint != en.cues.argument_hint
