from yclient_memory.backends.simple_recent.engine import SimpleRecentMemoryEngine
from yclient_memory.config import MemoryConfig
from yclient_memory.contracts import (
    BrowseMemoryRequest,
    CommentMemoryEvent,
    MaintenanceTickRequest,
    RelationshipSignalRequest,
    ReplyMemoryRequest,
    VoteMemoryEvent,
)


class RuntimeStub:
    def __init__(self):
        self.logs = []

    def llm_json(self, prompt_key, variables, config=None):
        return {}

    def llm_text(self, prompt_key, variables, config=None):
        return ""

    def get_author_id_and_username(self, post_id):
        return 55, "alice"

    def get_thread_root_id(self, post_id):
        return 900

    def get_recent_root_posts(self, round_id, limit=24, rounds_back=18):
        return []

    def get_post_text(self, post_id):
        return "you are wrong about the benchmark results"

    def persona_snapshot(self):
        return {}

    def decision_log(self, payload):
        self.logs.append(payload)


def test_simple_recent_reply_context_uses_recent_pair_memory():
    runtime = RuntimeStub()
    engine = SimpleRecentMemoryEngine(config=MemoryConfig(backend="simple_recent"), runtime=runtime)
    engine.record_comment(
        CommentMemoryEvent(
            round_id=2,
            target_post_id=10,
            thread_root_id=900,
            other_user_id=55,
            other_username="alice",
            other_text="that benchmark is weak",
            my_text="nah your benchmark evidence is weak",
            conv_text="thread",
        )
    )
    engine.record_comment(
        CommentMemoryEvent(
            round_id=3,
            target_post_id=11,
            thread_root_id=777,
            other_user_id=55,
            other_username="alice",
            other_text="same take again",
            my_text="you said this last time too",
            conv_text="thread",
        )
    )

    result = engine.build_reply_context(
        ReplyMemoryRequest(
            query_text="compose a reply",
            other_user_id=55,
            other_username="alice",
            thread_root_id=900,
        )
    )

    assert "History with @alice" in result.rendered_text
    assert "earlier here:" in result.rendered_text
    assert result.cues.scope in {"partial", "strong"}


def test_simple_recent_browse_context_is_thread_local():
    runtime = RuntimeStub()
    engine = SimpleRecentMemoryEngine(config=MemoryConfig(backend="simple_recent"), runtime=runtime)
    engine.record_comment(
        CommentMemoryEvent(
            round_id=4,
            target_post_id=12,
            thread_root_id=901,
            other_user_id=56,
            other_username="bob",
            other_text="first point",
            my_text="second point",
            conv_text="thread",
        )
    )

    result = engine.build_browse_context(BrowseMemoryRequest(thread_root_id=901, round_id=4))

    assert "[THREAD MEMORY]" in result.rendered_text
    assert result.diagnostics.usage == "thread_local"


def test_simple_recent_vote_signal_only_updates_relationship_without_visible_history():
    runtime = RuntimeStub()
    engine = SimpleRecentMemoryEngine(config=MemoryConfig(backend="simple_recent", vote_signal_only=True), runtime=runtime)

    engine.record_vote(VoteMemoryEvent(round_id=5, post_id=99, vote_type="like"))

    signal = engine.relationship_signal(RelationshipSignalRequest(other_user_id=55))
    reply = engine.build_reply_context(
        ReplyMemoryRequest(query_text="reply", other_user_id=55, other_username="alice", thread_root_id=900)
    )

    assert signal.affinity > 0
    assert "like on" not in reply.rendered_text.lower()


def test_simple_recent_maintenance_tick_decays_relationship_values():
    runtime = RuntimeStub()
    engine = SimpleRecentMemoryEngine(config=MemoryConfig(backend="simple_recent"), runtime=runtime)
    engine.record_comment(
        CommentMemoryEvent(
            round_id=2,
            target_post_id=10,
            thread_root_id=900,
            other_user_id=55,
            other_username="alice",
            other_text="wrong",
            my_text="wrong again",
            conv_text="thread",
        )
    )
    before = engine.relationship_signal(RelationshipSignalRequest(other_user_id=55))
    engine.maintenance_tick(MaintenanceTickRequest(round_id=2))
    result = engine.maintenance_tick(MaintenanceTickRequest(round_id=5))
    after = engine.relationship_signal(RelationshipSignalRequest(other_user_id=55))

    assert "decayed_relationships" in result.performed_actions
    assert after.conflict < before.conflict
