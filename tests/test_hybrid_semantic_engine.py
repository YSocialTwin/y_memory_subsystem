from yclient_memory.backends.hybrid_semantic.engine import HybridSemanticMemoryEngine, _StoredItem
from yclient_memory.config import MemoryConfig
from yclient_memory.contracts import BrowseMemoryRequest, PostMemoryEvent, PostStyleRequest, ReplyMemoryRequest, VoteMemoryEvent


class RuntimeStub:
    def __init__(self):
        self.posts = []
        self.logs = []
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
        self.logs.append(payload)


def _engine(**kwargs):
    runtime = kwargs.pop("runtime", RuntimeStub())
    config = MemoryConfig.from_mapping(kwargs)
    return HybridSemanticMemoryEngine(config=config, runtime=runtime), runtime


def test_build_reply_context_filters_vote_language_and_limits_cross_thread_callbacks():
    engine, _ = _engine(memory_vote_signal_only=True)
    engine._social_cards[55] = {
        "affinity": 0.8,
        "conflict": 0.2,
        "humor": 0.1,
        "trust": 0.4,
        "summary_text": "usually argue about finales. I upvoted their post once.",
        "last_round_id": 11,
        "last_thread_root_id": 900,
    }
    engine._thread_cards[900] = {"gist_text": "debating whether trauma excuses what Wanda did", "my_role": "skeptic"}
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
    engine._reflections.append(
        _StoredItem(
            item_id=99,
            item_type="reflection",
            round_id=10,
            text="last week you two argued about whether Wanda's ending was deserved",
            text_humanized="last week you two argued about whether Wanda's ending was deserved",
            thread_root_id=777,
            other_user_id=55,
            importance=0.9,
        )
    )
    engine._reflections.append(
        _StoredItem(
            item_id=100,
            item_type="reflection",
            round_id=10,
            text="you upvoted @alice after that meme thread",
            text_humanized="you upvoted @alice after that meme thread",
            thread_root_id=666,
            other_user_id=55,
            importance=0.9,
        )
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

    assert "affinity=0.80" in result.rendered_text
    assert "upvoted" not in result.rendered_text.lower()
    assert "trauma excuses" in result.continuity_text
    assert "grief excuses harm" in result.continuity_text
    assert "wanda's ending" in result.continuity_text.lower()
    assert result.diagnostics.metadata["cross_thread_callback_candidate"] is True
    assert result.diagnostics.top_score >= 0.8


def test_record_vote_hides_vote_events_from_prompt_visible_memory():
    engine, _ = _engine(memory_vote_signal_only=True)

    engine.record_vote(VoteMemoryEvent(round_id=12, post_id=99, vote_type="like"))

    assert engine._events == []
    assert 55 in engine._social_cards
    card = engine._social_cards[55]
    assert card["event_count"] == 0
    reply = engine.build_reply_context(
        ReplyMemoryRequest(query_text="reply", other_user_id=55, other_username="alice", thread_root_id=900)
    )
    assert "upvote" not in reply.rendered_text.lower()


def test_validate_structured_post_text_requires_title_and_body():
    engine, _ = _engine()

    valid = engine.validate_structured_post_text(
        "TITLE: wanda was still wrong\n\ntrauma explains it, it does not excuse it."
    )
    missing_title = engine.validate_structured_post_text("trauma explains it, it does not excuse it.")
    missing_body = engine.validate_structured_post_text("TITLE: wanda was still wrong")

    assert valid["valid"] is True
    assert valid["title"] == "wanda was still wrong"
    assert valid["body"] == "trauma explains it, it does not excuse it."
    assert missing_title["valid"] is False
    assert "missing_title" in missing_title["reasons"]
    assert missing_body["valid"] is False
    assert "missing_body" in missing_body["reasons"]


def test_post_style_context_uses_style_fields_only_when_digest_is_mature():
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

    assert result.diagnostics.metadata["mature"] is True
    assert result.diagnostics.usage == "style_digest_only"
    assert "short snarky complaint posts" in result.rendered_text
    assert "question bait titles" in result.rendered_text
    assert "the nanny" not in result.rendered_text.lower()


def test_post_style_context_stays_off_before_digest_maturity():
    engine, runtime = _engine()
    engine._community_digest = {
        "norms": ["short snarky complaint posts"],
        "memes": ["sleeping-on takes"],
    }
    runtime.posts = [
        {"id": 1, "user_id": 1, "tweet": "TITLE: one\n\nbody", "round": 1},
        {"id": 2, "user_id": 2, "tweet": "TITLE: two\n\nbody", "round": 2},
        {"id": 3, "user_id": 1, "tweet": "TITLE: three\n\nbody", "round": 3},
    ]

    result = engine.build_post_style_context(PostStyleRequest(round_id=3))

    assert result.rendered_text == ""
    assert result.diagnostics.metadata["mature"] is False
    assert result.diagnostics.usage == "none"


def test_thread_browse_context_ignores_community_digest():
    engine, _ = _engine()
    engine._community_digest = {"digest_text": "the nanny dominates everything here"}
    engine._thread_cards[9] = {
        "gist_text": "people are arguing about whether the merger will ruin discovery",
        "my_role": "skeptic",
    }

    result = engine.build_browse_context(BrowseMemoryRequest(thread_root_id=9, round_id=5))

    assert result.diagnostics.usage == "thread_local"
    assert "thread gist" in result.rendered_text
    assert "the nanny" not in result.rendered_text.lower()


def test_post_topic_freshness_matches_recent_text_roots():
    engine, runtime = _engine()
    runtime.posts = [
        {
            "id": 7,
            "round": 4,
            "user_id": 101,
            "news_id": None,
            "image_post_id": None,
            "image_id": None,
            "tweet": "TITLE: The Nanny reboot is a hot mess\n\nThe reboot is a disaster waiting to happen.",
        },
        {
            "id": 8,
            "round": 4,
            "user_id": 102,
            "news_id": 55,
            "image_post_id": None,
            "image_id": None,
            "tweet": "TITLE: streaming merger news\n\nHuge content bundle coming.",
        },
    ]

    fingerprint, matches = engine.post_find_recent_topic_matches(
        text_value="TITLE: why the nanny reboot is a disaster\n\nThis reboot is still a hot mess.",
        round_id=9,
    )

    assert fingerprint["title"] == "why the nanny reboot is a disaster"
    assert matches
    assert matches[0]["post_id"] == 7


def test_detect_high_affect_rules_for_criticism_and_conflict():
    engine, _ = _engine(memory_high_affect_enabled=True, memory_high_affect_llm_fallback=False)
    signal = engine.detect_high_affect_signal(
        incoming_text="you are wrong, source for that claim?",
        thread_context="thread",
        other_user_id=202,
        thread_root_id=303,
        round_id=9,
        target_username="alice",
    )

    assert signal["is_high_affect"] is True
    assert signal["triggers"]["criticism_or_challenge"] is True
    assert signal["triggers"]["conflict_or_argument"] is True


def test_detect_high_affect_uses_llm_fallback_in_uncertain_band():
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

    assert signal["source"] == "hybrid"
    assert signal["used_llm_fallback"] is True
    assert signal["is_high_affect"] is True


def test_collect_high_affect_recall_caps_and_dedupes():
    engine, _ = _engine(memory_high_affect_enabled=True)

    def fake_search(**kwargs):
        query = kwargs.get("query_text", "")
        if "back and forth" in query:
            items = [
                {"item_id": 1, "text_humanized": "argued about benchmark results", "score": 0.91, "round_id": 4},
                {"item_id": 2, "text_humanized": "called out missing evidence", "score": 0.87, "round_id": 5},
            ]
        elif "previously stated opinion" in query:
            items = [
                {"item_id": 2, "text_humanized": "duplicate id should dedupe", "score": 0.86, "round_id": 5},
                {"item_id": 3, "text_humanized": "said nerf was unnecessary", "score": 0.80, "round_id": 3},
            ]
        elif "personal experience anecdote" in query:
            items = [
                {"item_id": 4, "text_humanized": "once tested this in ranked and lost", "score": 0.76, "round_id": 2},
            ]
        else:
            items = [
                {"item_id": 5, "text_humanized": "history with @alice is conflict heavy", "score": 0.70, "round_id": 6},
            ]
        return {"items": items}

    engine._search = fake_search

    pack = engine.collect_high_affect_recall(
        incoming_text="you are wrong",
        thread_context="thread",
        other_user_id=202,
        thread_root_id=303,
        round_id=9,
        target_username="alice",
    )

    assert pack["has_usable_memories"] is True
    assert len(pack["items"]) == 5
    assert pack["counts_by_bucket"]["interaction"] <= 2
    assert pack["counts_by_bucket"]["opinion"] <= 2
    assert "[RECALLED MEMORIES]" in pack["prompt_block"]


def test_memory_callback_check_marker_or_overlap():
    engine, _ = _engine()
    memories = [{"text": "argued about benchmark evidence quality"}]

    ok_marker, _ = engine.reply_references_recalled_item(
        "I remember that benchmark argument and your evidence was still weak.",
        memories,
    )
    ok_overlap, _ = engine.reply_references_recalled_item(
        "Your benchmark evidence quality is still weak.",
        memories,
    )
    ok_none, _ = engine.reply_references_recalled_item("cool story bro", memories)

    assert ok_marker is True
    assert ok_overlap is True
    assert ok_none is False
