import runpy
from pathlib import Path

import pytest

from yclient_memory.backends.hybrid_semantic.engine import HybridSemanticMemoryEngine, _StoredItem
from yclient_memory.config import MemoryConfig
from yclient_memory.contracts import ReplyMemoryRequest

ROOT = Path(__file__).resolve().parents[1]


class _RT:
    def llm_json(self, *a, **k):
        return {}

    def llm_text(self, *a, **k):
        return ""

    def get_recent_root_posts(self, *a, **k):
        return []

    def decision_log(self, payload):
        pass


def test_italian_retrieval_finds_the_right_memory_as_often_as_english():
    module = runpy.run_path(str(ROOT / "scripts" / "measure_retrieval.py"))
    en, it = module["measure"]("en"), module["measure"]("it")
    assert it["top1"] >= 0.8 * en["top1"], (en, it)


@pytest.mark.parametrize(
    "language,stored,query",
    [
        ("en", "last week you two argued about whether the finale was deserved", "the finale was deserved, really"),
        ("it", "la settimana scorsa avete discusso se il finale fosse meritato", "il finale meritato, davvero"),
    ],
)
def test_cross_thread_callback_candidate_works_in_every_language(language, stored, query):
    engine = HybridSemanticMemoryEngine(config=MemoryConfig(language=language), runtime=_RT())
    engine._reflections.append(
        _StoredItem(
            item_id=1, item_type="reflection", round_id=3, text=stored, text_humanized=stored,
            thread_root_id=777, other_user_id=55, importance=0.9,
        )
    )
    result = engine.build_reply_context(
        ReplyMemoryRequest(query_text=query, other_user_id=55, other_username="alice",
                           thread_root_id=900, round_id=5, incoming_text=query)
    )
    assert result.diagnostics.metadata.get("cross_thread_callback_candidate") is True
