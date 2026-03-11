from yclient_memory.backends.hybrid_semantic.engine import HybridSemanticMemoryEngine, _StoredItem
from yclient_memory.config import MemoryConfig
from yclient_memory.contracts import BrowseMemoryRequest, PostStyleRequest, ReplyMemoryRequest, VoteMemoryEvent


class RuntimeStub:
    def __init__(self):
        self.posts = []
        self.llm_json_result = {}

    def llm_json(self, prompt_key, variables, config=None):
        return self.llm_json_result

    def llm_text(self, prompt_key, variables, config=None):
        return ""

    def get_author_id_and_username(self, post_id):
        return 55, "alice"

    def get_thread_root_id(self, post_id):
        return 900

    def get_recent_root_posts(self, round_id, limit=24, rounds_back=18):
        return list(self.posts)

    def get_post_text(self, post_id):
        return "that benchmark evidence is weak"

    def persona_snapshot(self):
        return {}

    def decision_log(self, payload):
        return None


def _engine(**kwargs):
    runtime = kwargs.pop("runtime", RuntimeStub())
    config = MemoryConfig.from_mapping(kwargs)
    return HybridSemanticMemoryEngine(config=config, runtime=runtime), runtime


def test_characterization_reply_context_matches_upstream_fixture():
    engine, _ = _engine(memory_prompt_mode="subtle_forum", memory_vote_signal_only=True)
    engine._social_cards[55] = {
        "affinity": 0.8,
        "conflict": 0.2,
        "humor": 0.1,
        "trust": 0.4,
        "summary_text": "usually argue about finales. I upvoted their post once.",
    }
    engine._thread_cards[900] = {"gist_text": "debating whether trauma excuses what Wanda did"}
    engine._record_event(
        round_id=11,
        item_type="event",
        text="upvote on @alice: strong point",
        text_humanized="upvote on @alice: strong point",
        thread_root_id=900,
        other_user_id=55,
        relation_label="upvote",
        tone_label=None,
        importance=0.3,
    )
    engine._record_event(
        round_id=11,
        item_type="event",
        text="pushed back on the idea that grief excuses harm",
        text_humanized="pushed back on the idea that grief excuses harm",
        thread_root_id=900,
        other_user_id=55,
        relation_label="disagree",
        tone_label="curious",
        importance=0.7,
    )
    engine._reflections.extend(
        [
            _StoredItem(
                item_id=1,
                item_type="reflection",
                round_id=10,
                text="last week you two argued about whether Wanda's ending was deserved",
                text_humanized="last week you two argued about whether Wanda's ending was deserved",
                thread_root_id=777,
                other_user_id=55,
                score=0.92,
                importance=0.9,
            ),
            _StoredItem(
                item_id=2,
                item_type="reflection",
                round_id=10,
                text="you upvoted @alice after that meme thread",
                text_humanized="you upvoted @alice after that meme thread",
                thread_root_id=666,
                other_user_id=55,
                score=0.99,
                importance=0.9,
            ),
        ]
    )

    result = engine.build_reply_context(
        ReplyMemoryRequest(
            query_text="compose a reply",
            other_user_id=55,
            other_username="alice",
            thread_root_id=900,
            round_id=12,
        )
    )

    assert result.rendered_text == (
        "History with @alice: affinity=0.80, conflict=0.20, humor=0.10, trust=0.40\n"
        "Continuity: with @alice: usually argue about finales | this thread: debating whether trauma excuses what Wanda did | "
        "earlier here: pushed back on the idea that grief excuses harm | if clearly relevant: last week you two argued about "
        "whether Wanda's ending was deserved"
    )
    assert result.continuity_text.endswith("whether Wanda's ending was deserved")
    assert result.diagnostics.top_score == 0.92
    assert result.diagnostics.metadata["cross_thread_callback_candidate"] is True


def test_characterization_vote_signal_only_keeps_vote_out_of_visible_memory():
    engine, _ = _engine(memory_vote_signal_only=True)
    engine.record_vote(VoteMemoryEvent(round_id=12, post_id=99, vote_type="like"))

    assert engine._events == []
    assert engine._social_cards[55]["event_count"] == 0
    reply = engine.build_reply_context(
        ReplyMemoryRequest(query_text="reply", other_user_id=55, other_username="alice", thread_root_id=900)
    )
    assert "upvote" not in reply.rendered_text.lower()


def test_characterization_post_style_context_matches_upstream_fixture():
    engine, runtime = _engine()
    engine._community_digest = {
        "digest_text": "the nanny dominates everything here",
        "norms": ["short snarky complaint posts", "question bait titles"],
        "memes": ["sleeping-on takes"],
        "top_topics": ["the nanny reboot"],
    }
    runtime.posts = [
        {"id": 1, "user_id": 1, "tweet": "TITLE: one\n\nbody", "round": 1},
        {"id": 2, "user_id": 2, "tweet": "TITLE: two\n\nbody", "round": 2},
        {"id": 3, "user_id": 3, "tweet": "TITLE: three\n\nbody", "round": 3},
        {"id": 4, "user_id": 4, "tweet": "TITLE: four\n\nbody", "round": 4},
        {"id": 5, "user_id": 1, "tweet": "TITLE: five\n\nbody", "round": 5},
        {"id": 6, "user_id": 2, "tweet": "TITLE: six\n\nbody", "round": 6},
    ]

    result = engine.build_post_style_context(PostStyleRequest(round_id=6))

    assert result.rendered_text == (
        "[COMMUNITY STYLE GUIDE]\n"
        "posting style lately: short snarky complaint posts, question bait titles\n"
        "recurring formats: sleeping-on takes\n"
        "use this only for tone and structure, not as a topic list"
    )
    assert result.diagnostics.usage == "style_digest_only"
    assert result.diagnostics.metadata["mature"] is True


def test_characterization_thread_browse_context_matches_upstream_fixture():
    engine, _ = _engine()
    engine._thread_cards[9] = {
        "gist_text": "people are arguing about whether the merger will ruin discovery",
        "my_role": "skeptic",
    }

    result = engine.build_browse_context(BrowseMemoryRequest(thread_root_id=9, round_id=5))

    assert result.rendered_text == (
        "[THREAD MEMORY]\n"
        "thread gist: people are arguing about whether the merger will ruin discovery\n"
        "my role here: skeptic"
    )
    assert result.diagnostics.usage == "thread_local"


def test_characterization_high_affect_llm_fallback_matches_upstream_fixture():
    runtime = RuntimeStub()
    runtime.llm_json_result = {
        "criticism_or_challenge": False,
        "conflict_or_argument": True,
        "incoming_anecdote": False,
        "defending_prior_opinion": False,
        "confidence": 0.82,
    }
    engine, _ = _engine(
        runtime=runtime,
        memory_high_affect_enabled=True,
        memory_high_affect_llm_fallback=True,
    )

    signal = engine.detect_high_affect_signal(
        incoming_text="you sure, source?",
        thread_context="thread",
        other_user_id=202,
        thread_root_id=303,
        round_id=9,
        target_username="alice",
    )

    assert signal == {
        "is_high_affect": True,
        "confidence": 0.82,
        "source": "hybrid",
        "used_llm_fallback": True,
        "prior_match": False,
        "prior_item": None,
        "triggers": {
            "criticism_or_challenge": False,
            "conflict_or_argument": True,
            "incoming_anecdote": False,
            "defending_prior_opinion": False,
        },
    }
