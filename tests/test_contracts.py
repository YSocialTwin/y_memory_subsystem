from yclient_memory import build_memory_engine
from yclient_memory.config import MemoryConfig
from yclient_memory.contracts import ReplyMemoryRequest


class DummyRuntime:
    def llm_json(self, prompt_key, variables, config=None):
        return {}

    def llm_text(self, prompt_key, variables, config=None):
        return ""

    def get_author_id_and_username(self, post_id):
        return None, None

    def get_thread_root_id(self, post_id):
        return None

    def get_recent_root_posts(self, round_id, limit=24, rounds_back=18):
        return []

    def get_post_text(self, post_id):
        return ""

    def persona_snapshot(self):
        return {}

    def decision_log(self, payload):
        return None


def test_factory_builds_supported_backends():
    runtime = DummyRuntime()
    hybrid = build_memory_engine(
        backend="hybrid_semantic",
        config=MemoryConfig(),
        runtime=runtime,
    )
    recent = build_memory_engine(
        backend="simple_recent",
        config=MemoryConfig(backend="simple_recent"),
        runtime=runtime,
    )

    assert hybrid.capabilities().semantic_search is True
    assert recent.capabilities().semantic_search is False


def test_reply_context_contract_is_returned():
    runtime = DummyRuntime()
    engine = build_memory_engine(
        backend="simple_recent",
        config=MemoryConfig(backend="simple_recent"),
        runtime=runtime,
    )

    result = engine.build_reply_context(ReplyMemoryRequest(query_text="reply"))

    assert result.rendered_text == ""
    assert result.cues.scope == "none"
