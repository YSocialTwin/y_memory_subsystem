from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from ...capabilities import MemoryCapabilities
from ...contracts import (
    BrowseMemoryContext,
    BrowseMemoryRequest,
    CommentMemoryEvent,
    MaintenanceTickRequest,
    MaintenanceTickResult,
    MemoryDiagnostics,
    PostMemoryEvent,
    PostStyleContext,
    PostStyleRequest,
    RelationshipSignal,
    RelationshipSignalRequest,
    ReplyMemoryContext,
    ReplyMemoryRequest,
    VoteMemoryEvent,
)
from ...logging import emit_decision_log
from ...policies.affect_policy import detect_high_affect_signal as detect_high_affect_signal_policy
from ...policies.prompt_policy import build_conversation_cues, format_conversation_cues
from ...policies.safety_policy import (
    CALLBACK_STOPWORDS,
    is_vote_artifact,
    reply_references_recalled_item,
    sanitize_prompt_memory_text,
    truncate,
)


@dataclass
class _StoredItem:
    item_id: int
    item_type: str
    round_id: int | None
    text: str
    text_humanized: str
    thread_root_id: int | None = None
    other_user_id: int | None = None
    relation_label: str | None = None
    tone_label: str | None = None
    score: float = 0.0
    importance: float = 0.0
    metadata: dict[str, Any] | None = None


class HybridSemanticMemoryEngine:
    def __init__(self, *, config, runtime):
        self.config = config
        self.runtime = runtime
        self._item_id = 0
        self._events: list[_StoredItem] = []
        self._reflections: list[_StoredItem] = []
        self._social_cards: dict[int, dict[str, Any]] = {}
        self._thread_cards: dict[int, dict[str, Any]] = {}
        self._community_digest: dict[str, Any] | None = None
        self._recent_root_posts: list[dict[str, Any]] = []
        self._thread_event_counts: dict[int, int] = defaultdict(int)
        self._last_digest_round: int | None = None
        self._last_reflection_round: int | None = None

    def capabilities(self) -> MemoryCapabilities:
        return MemoryCapabilities(
            semantic_search=True,
            relationship_memory=True,
            thread_memory=True,
            community_digest=True,
            reflections=True,
            high_affect_recall=self.config.high_affect_enabled,
            post_style_context=True,
        )

    def build_reply_context(self, request: ReplyMemoryRequest) -> ReplyMemoryContext:
        diagnostics = MemoryDiagnostics()
        if not self.config.enabled:
            return ReplyMemoryContext(diagnostics=diagnostics)

        ctx = self._fetch_context(other_user_id=request.other_user_id, thread_root_id=request.thread_root_id)
        username = str(request.other_username or "").strip().lstrip("@") or "this user"

        metrics_line = ""
        continuity_parts = []
        local_signal_count = 0

        social_card = ctx.get("social_card")
        if isinstance(social_card, dict):
            metrics_line = (
                f"History with @{username}: affinity={float(social_card.get('affinity') or 0.0):.2f}, "
                f"conflict={float(social_card.get('conflict') or 0.0):.2f}, "
                f"humor={float(social_card.get('humor') or 0.0):.2f}, "
                f"trust={float(social_card.get('trust') or 0.0):.2f}"
            )
            summary_text = sanitize_prompt_memory_text(social_card.get("summary_text") or "", 120)
            if summary_text:
                continuity_parts.append(f"with @{username}: {summary_text}")
                local_signal_count += 1

        thread_card = ctx.get("thread_card")
        if isinstance(thread_card, dict):
            gist_text = sanitize_prompt_memory_text(thread_card.get("gist_text") or "", 120)
            if gist_text:
                continuity_parts.append(f"this thread: {gist_text}")
                local_signal_count += 1

        for event in reversed(ctx.get("recent_pair_events") or []):
            if request.thread_root_id is not None and event.get("thread_root_id") != request.thread_root_id:
                continue
            if is_vote_artifact(
                text_value=event.get("salient_claim") or "",
                event_type=event.get("event_type") or "",
                relation_label=event.get("relation_label") or "",
            ):
                continue
            claim = sanitize_prompt_memory_text(event.get("salient_claim") or "", 100)
            if claim:
                continuity_parts.append(f"earlier here: {claim}")
                local_signal_count += 1
                break

        callback_text = ""
        callback_score = None
        if request.other_user_id is not None:
            search_res = self._search(
                query_text=request.query_text,
                other_user_id=request.other_user_id,
                thread_root_id=None,
                types=["summary", "reflection"],
                round_id=request.round_id,
                k=4,
                max_chars=420,
            )
            diagnostics.search_used = True
            items = search_res.get("items") or []
            for item in items:
                score = float(item.get("score") or 0.0)
                if diagnostics.top_score is None:
                    diagnostics.top_score = score
                if request.thread_root_id is not None and item.get("thread_root_id") == request.thread_root_id:
                    continue
                if item.get("other_user_id") not in (None, request.other_user_id):
                    continue
                if score < self.config.cross_thread_callback_min_score:
                    continue
                if is_vote_artifact(
                    text_value=item.get("text_humanized") or item.get("text") or "",
                    relation_label=item.get("relation_label") or "",
                    metadata=item.get("metadata") or {},
                ):
                    continue
                clean = sanitize_prompt_memory_text(item.get("text_humanized") or item.get("text") or "", 110)
                if clean:
                    callback_text = clean
                    callback_score = score
                    break

        if callback_text:
            continuity_parts.append(f"if clearly relevant: {callback_text}")
            diagnostics.metadata["cross_thread_callback_candidate"] = True
            diagnostics.metadata["cross_thread_callback_score"] = callback_score
            diagnostics.top_score = callback_score

        continuity_text = truncate(" | ".join(continuity_parts), self.config.reply_context_max_chars)
        diagnostics.retrieved_item_count = local_signal_count + (1 if callback_text else 0)
        if diagnostics.top_score is None and local_signal_count > 0:
            diagnostics.top_score = 0.72 if local_signal_count >= 2 else 0.58

        lines = []
        if metrics_line:
            lines.append(metrics_line)
        if continuity_text:
            lines.append("Continuity: " + continuity_text)
        rendered = "\n".join(lines).strip()

        meta = {
            "retrieved_item_count": diagnostics.retrieved_item_count,
            "top_score": diagnostics.top_score,
            "continuity_text": continuity_text,
            "cross_thread_callback_candidate": diagnostics.metadata.get("cross_thread_callback_candidate", False),
        }
        cues = build_conversation_cues(
            memory_text=rendered,
            memory_meta=meta,
            subtle_mode=self.config.prompt_mode == "subtle_forum",
            target_username=request.other_username,
            nuance_enabled=self.config.nuance_enabled,
            min_score=self.config.nuance_min_score,
            callback_probability=self.config.nuance_callback_probability,
        )
        cues.rendered_text = format_conversation_cues(cues, self.config.nuance_cues_max_chars)
        return ReplyMemoryContext(
            rendered_text=rendered,
            cues=cues,
            diagnostics=diagnostics,
            continuity_text=continuity_text,
        )

    def build_browse_context(self, request: BrowseMemoryRequest) -> BrowseMemoryContext:
        return self.build_thread_browse_context(thread_root_id=request.thread_root_id, round_id=request.round_id)

    def build_thread_browse_context(self, *, thread_root_id: int | None, round_id: int | None = None) -> BrowseMemoryContext:
        diagnostics = MemoryDiagnostics(usage="none")
        if thread_root_id is None:
            return BrowseMemoryContext(diagnostics=diagnostics)
        ctx = self._fetch_context(other_user_id=None, thread_root_id=thread_root_id)
        thread_card = ctx.get("thread_card")
        if not isinstance(thread_card, dict):
            return BrowseMemoryContext(diagnostics=diagnostics)
        lines = []
        gist = sanitize_prompt_memory_text(thread_card.get("gist_text") or "", 160)
        if gist:
            lines.append("[THREAD MEMORY]")
            lines.append("thread gist: " + gist)
        role = str(thread_card.get("my_role") or "").strip().lower()
        if role:
            lines.append("my role here: " + role)
        if not lines:
            return BrowseMemoryContext(diagnostics=diagnostics)
        diagnostics.usage = "thread_local"
        return BrowseMemoryContext(rendered_text=self._truncate_block("\n".join(lines), 220), diagnostics=diagnostics)

    def build_post_style_context(self, request: PostStyleRequest) -> PostStyleContext:
        diagnostics = MemoryDiagnostics(metadata={"root_count": 0, "distinct_author_count": 0, "mature": False})
        if not self.config.enabled:
            return PostStyleContext(diagnostics=diagnostics)

        root_posts = self._get_recent_root_posts(request.round_id)
        maturity = self._digest_maturity_meta(root_posts)
        diagnostics.metadata.update(maturity)
        if not maturity["mature"]:
            return PostStyleContext(diagnostics=diagnostics)

        digest = self._community_digest or {}
        norms = self._json_list_maybe(digest.get("norms"))
        memes = self._json_list_maybe(digest.get("memes"))
        norm_lines = [self._style_phrase(item) for item in norms if self._style_phrase_ok(item)][:4]
        meme_lines = [self._style_phrase(item) for item in memes if self._style_phrase_ok(item)][:3]
        if not norm_lines and not meme_lines:
            return PostStyleContext(diagnostics=diagnostics)

        lines = ["[COMMUNITY STYLE GUIDE]"]
        if norm_lines:
            lines.append("posting style lately: " + ", ".join(norm_lines[:3]))
        if meme_lines:
            lines.append("recurring formats: " + ", ".join(meme_lines[:2]))
        lines.append("use this only for tone and structure, not as a topic list")
        diagnostics.usage = "style_digest_only"
        return PostStyleContext(rendered_text=self._truncate_block("\n".join(lines), 280), diagnostics=diagnostics)

    def record_comment(self, event: CommentMemoryEvent) -> None:
        note = self._heuristic_interaction_note(event.other_text, event.my_text)
        salient_claim = note.get("salient_claim") or sanitize_prompt_memory_text(event.my_text, 140)
        self._record_event(
            round_id=event.round_id,
            item_type="event",
            text=salient_claim,
            text_humanized=salient_claim,
            thread_root_id=event.thread_root_id,
            other_user_id=event.other_user_id,
            relation_label=note.get("relation_label"),
            tone_label=note.get("tone_label"),
            importance=0.65,
        )
        if event.other_user_id is not None:
            self._upsert_social_card(
                other_user_id=event.other_user_id,
                round_id=event.round_id,
                thread_root_id=event.thread_root_id,
                salient_claim=salient_claim,
                deltas=note,
            )
        self._maybe_update_thread_card(
            thread_root_id=event.thread_root_id,
            round_id=event.round_id,
            conv_text=event.conv_text,
        )
        self._maybe_update_community_digest(round_id=event.round_id)
        self._maybe_generate_reflections(round_id=event.round_id)

    def record_vote(self, event: VoteMemoryEvent) -> None:
        other_user_id = event.other_user_id
        other_username = event.other_username
        thread_root_id = event.thread_root_id
        if other_user_id is None:
            other_user_id, other_username = self.runtime.get_author_id_and_username(int(event.post_id))
        if thread_root_id is None:
            thread_root_id = self.runtime.get_thread_root_id(int(event.post_id))

        if other_user_id is None:
            return

        deltas = {
            "affinity_delta": 0.5 if event.vote_type == "like" else -0.3,
            "conflict_delta": -0.1 if event.vote_type == "like" else 0.6,
            "humor_delta": 0.0,
            "trust_delta": 0.2 if event.vote_type == "like" else -0.2,
        }

        if not self.config.vote_signal_only:
            snippet = sanitize_prompt_memory_text(event.post_text or self.runtime.get_post_text(int(event.post_id)), 120)
            salient_claim = (
                f"{'upvote' if event.vote_type == 'like' else 'downvote'} on @{(other_username or 'user').lstrip('@')}: {snippet}"
                if snippet
                else f"{'upvote' if event.vote_type == 'like' else 'downvote'} on a comment by @{(other_username or 'user').lstrip('@')}"
            )
            self._record_event(
                round_id=event.round_id,
                item_type="event",
                text=salient_claim,
                text_humanized=salient_claim,
                thread_root_id=thread_root_id,
                other_user_id=other_user_id,
                relation_label=None,
                tone_label=None,
                importance=0.3,
                metadata={"source_event": "vote"},
            )

        self._upsert_social_card(
            other_user_id=other_user_id,
            round_id=event.round_id,
            thread_root_id=thread_root_id,
            salient_claim=None if self.config.vote_signal_only else "",
            deltas=deltas,
            include_evidence=not self.config.vote_signal_only,
            count_as_event=not self.config.vote_signal_only,
        )

        if not self.config.vote_signal_only:
            self._maybe_update_community_digest(round_id=event.round_id)
            self._maybe_generate_reflections(round_id=event.round_id)

    def record_post(self, event: PostMemoryEvent) -> None:
        row = {
            "id": event.post_id,
            "round": event.round_id,
            "user_id": event.user_id,
            "tweet": event.text,
            "news_id": None,
            "image_post_id": None,
            "image_id": None,
        }
        if event.origin_kind == "share_link":
            row["news_id"] = 1
        if event.origin_kind == "share_image":
            row["image_id"] = 1
        self._recent_root_posts.append(row)

    def relationship_signal(self, request: RelationshipSignalRequest) -> RelationshipSignal:
        if request.other_user_id is None:
            return RelationshipSignal()
        card = self._social_cards.get(request.other_user_id)
        if not isinstance(card, dict):
            return RelationshipSignal()
        return RelationshipSignal(
            affinity=float(card.get("affinity") or 0.0),
            conflict=float(card.get("conflict") or 0.0),
            humor=float(card.get("humor") or 0.0),
            trust=float(card.get("trust") or 0.0),
            summary_text=str(card.get("summary_text") or ""),
            metadata={"event_count": int(card.get("event_count") or 0)},
        )

    def maintenance_tick(self, request: MaintenanceTickRequest) -> MaintenanceTickResult:
        actions = []
        if self._should_run_digest(request.round_id):
            self._maybe_update_community_digest(round_id=request.round_id)
            actions.append("community_digest")
        if self._should_run_reflections(request.round_id):
            self._maybe_generate_reflections(round_id=request.round_id)
            actions.append("reflections")
        return MaintenanceTickResult(performed_actions=actions, diagnostics={"round_id": request.round_id})

    def detect_high_affect_signal(
        self,
        *,
        incoming_text: str,
        thread_context: str,
        other_user_id: int | None,
        thread_root_id: int | None,
        round_id: int | None,
        target_username: str,
    ) -> dict[str, Any]:
        prior_match, prior_item = self._detect_prior_opinion_match(
            incoming_text=incoming_text,
            other_user_id=other_user_id,
            thread_root_id=thread_root_id,
            round_id=round_id,
        )
        llm_fallback = None
        if self.config.high_affect_llm_fallback:
            llm_fallback = lambda incoming_text: self.runtime.llm_json(
                "memory_high_affect_classifier",
                {
                    "incoming_text": incoming_text,
                    "thread_context": thread_context,
                    "target_username": target_username,
                },
            )
        signal = detect_high_affect_signal_policy(
            incoming_text=incoming_text,
            prior_match=prior_match,
            llm_classifier=llm_fallback,
            rule_threshold=self.config.high_affect_rule_threshold,
            uncertain_low=self.config.high_affect_uncertain_low,
            uncertain_high=self.config.high_affect_uncertain_high,
        )
        signal["prior_item"] = prior_item
        return signal

    def collect_high_affect_recall(
        self,
        *,
        incoming_text: str,
        thread_context: str,
        other_user_id: int | None,
        thread_root_id: int | None,
        round_id: int | None,
        target_username: str,
    ) -> dict[str, Any]:
        pack = {
            "items": [],
            "counts_by_bucket": {},
            "has_usable_memories": False,
            "prompt_block": "",
        }
        buckets = [
            {
                "name": "interaction",
                "cap": 2,
                "search_kwargs": {
                    "query_text": self._build_query_text("recent back and forth argument with this user", incoming_text, thread_context),
                    "other_user_id": other_user_id,
                    "thread_root_id": thread_root_id,
                    "types": ["event", "summary"],
                    "round_id": round_id,
                    "k": self.config.high_affect_search_k,
                },
            },
            {
                "name": "opinion",
                "cap": 2,
                "search_kwargs": {
                    "query_text": self._build_query_text("my previously stated opinion or claim", incoming_text),
                    "thread_root_id": thread_root_id,
                    "types": ["event", "reflection", "summary"],
                    "round_id": round_id,
                    "k": self.config.high_affect_search_k,
                },
            },
            {
                "name": "personal_experience",
                "cap": 1,
                "search_kwargs": {
                    "query_text": self._build_query_text("my personal experience anecdote related to this topic", incoming_text),
                    "types": ["event", "reflection"],
                    "round_id": round_id,
                    "k": self.config.high_affect_search_k,
                },
            },
            {
                "name": "relationship",
                "cap": 1,
                "search_kwargs": {
                    "query_text": self._build_query_text("relationship history trust conflict humor with this user", target_username),
                    "other_user_id": other_user_id,
                    "types": ["summary", "reflection"],
                    "round_id": round_id,
                    "k": self.config.high_affect_search_k,
                },
            },
        ]
        seen_ids = set()
        ordered_items = []
        counts = {}
        for bucket in buckets:
            counts[bucket["name"]] = 0
            result = self._search(**bucket["search_kwargs"])
            for item in result.get("items") or []:
                if counts[bucket["name"]] >= bucket["cap"] or len(ordered_items) >= self.config.high_affect_max_items:
                    break
                item_id = item.get("item_id")
                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)
                text = str(item.get("text_humanized") or item.get("text") or "").strip()
                if not text:
                    continue
                ordered_items.append(
                    {
                        "item_id": item_id,
                        "bucket": bucket["name"],
                        "score": float(item.get("score") or 0.0),
                        "round_id": item.get("round_id"),
                        "text": truncate(text, 180),
                    }
                )
                counts[bucket["name"]] += 1
        if not ordered_items:
            return pack
        lines = ["[RECALLED MEMORIES]"]
        for index, item in enumerate(ordered_items[: self.config.high_affect_max_items], start=1):
            lines.append(
                f"- [M{index}] ({item['bucket']}, r{item.get('round_id')}, s={float(item.get('score') or 0.0):.2f}) {item['text']}"
            )
        lines.append("- Reference memory naturally. Never invent events not listed above.")
        pack["items"] = ordered_items[: self.config.high_affect_max_items]
        pack["counts_by_bucket"] = counts
        pack["has_usable_memories"] = bool(pack["items"])
        pack["prompt_block"] = truncate("\n".join(lines), self.config.high_affect_max_chars)
        return pack

    def reply_references_recalled_item(self, reply_text: str, recalled_items: list[dict]) -> tuple[bool, str]:
        return reply_references_recalled_item(reply_text, recalled_items)

    def validate_structured_post_text(self, text_value: str) -> dict[str, Any]:
        parsed = self._parse_root_post_text(text_value)
        reasons = []
        if not parsed["title"]:
            reasons.append("missing_title")
        if not parsed["body"]:
            reasons.append("missing_body")
        return {
            "valid": not reasons,
            "title": parsed["title"],
            "body": parsed["body"],
            "reasons": reasons,
        }

    def post_find_recent_topic_matches(self, *, text_value: str, round_id: int):
        fingerprint = self._post_topic_fingerprint(text_value)
        matches = []
        for row in self._get_recent_root_posts(round_id, limit=30, rounds_back=12):
            if self._post_root_origin_kind(row) != "text_post":
                continue
            recent_fp = self._post_topic_fingerprint(row.get("tweet") or "")
            score = self._post_topic_overlap_score(fingerprint, recent_fp)
            if score < 0.58:
                continue
            matches.append(
                {
                    "post_id": row.get("id"),
                    "round": row.get("round"),
                    "score": round(score, 3),
                    "title": recent_fp.get("title") or "",
                }
            )
        matches.sort(key=lambda item: (-float(item.get("score") or 0.0), -int(item.get("round") or 0)))
        return fingerprint, matches[:3]

    def _fetch_context(self, *, other_user_id: int | None, thread_root_id: int | None) -> dict[str, Any]:
        recent_pair_events = []
        if other_user_id is not None:
            for item in self._events[-10:]:
                if item.other_user_id == other_user_id:
                    recent_pair_events.append(
                        {
                            "thread_root_id": item.thread_root_id,
                            "event_type": item.item_type,
                            "relation_label": item.relation_label,
                            "salient_claim": item.text_humanized,
                        }
                    )
        payload = {
            "social_card": self._social_cards.get(other_user_id) if other_user_id is not None else None,
            "thread_card": self._thread_cards.get(thread_root_id) if thread_root_id is not None else None,
            "community_digest": self._community_digest,
            "recent_pair_events": recent_pair_events,
        }
        return payload

    def _search(
        self,
        *,
        query_text: str,
        other_user_id: int | None = None,
        thread_root_id: int | None = None,
        types: list[str] | None = None,
        round_id: int | None = None,
        k: int = 8,
        max_chars: int = 900,
        include_evidence_tail: bool = False,
        time_window_rounds: int | None = None,
    ) -> dict[str, Any]:
        query_tokens = self._search_tokens(query_text)
        wanted_types = set(types or ["event", "summary", "reflection"])
        candidates: list[_StoredItem] = []
        if "event" in wanted_types:
            candidates.extend(self._events)
        if "reflection" in wanted_types:
            candidates.extend(self._reflections)
        if "summary" in wanted_types:
            for other_id, card in self._social_cards.items():
                candidates.append(
                    _StoredItem(
                        item_id=100000 + int(other_id),
                        item_type="summary",
                        round_id=card.get("last_round_id"),
                        text=str(card.get("summary_text") or ""),
                        text_humanized=str(card.get("summary_text") or ""),
                        thread_root_id=card.get("last_thread_root_id"),
                        other_user_id=other_id,
                    )
                )

        results = []
        for item in candidates:
            if item.item_type not in wanted_types:
                continue
            if other_user_id is not None and item.other_user_id not in (None, other_user_id):
                continue
            if thread_root_id is not None and item.thread_root_id not in (None, thread_root_id):
                continue
            if round_id is not None and time_window_rounds is not None and item.round_id is not None:
                if int(round_id) - int(item.round_id) > int(time_window_rounds):
                    continue
            score = self._score_item(query_tokens, item, other_user_id=other_user_id, thread_root_id=thread_root_id)
            if score <= 0:
                continue
            results.append(
                {
                    "item_id": item.item_id,
                    "item_type": item.item_type,
                    "round_id": item.round_id,
                    "thread_root_id": item.thread_root_id,
                    "other_user_id": item.other_user_id,
                    "relation_label": item.relation_label,
                    "metadata": item.metadata or {},
                    "score": round(score, 3),
                    "importance": item.importance,
                    "text": truncate(item.text, max_chars),
                    "text_humanized": truncate(item.text_humanized, max_chars),
                }
            )
        results.sort(key=lambda item: (-float(item.get("score") or 0.0), -(int(item.get("round_id") or 0))))
        payload = {
            "retrieval_meta": {
                "degraded_mode": False,
                "embedding_degraded": False,
                "no_ready_candidates": not bool(results),
            },
            "items": results[:k],
        }
        if include_evidence_tail:
            payload["evidence_tail"] = results[: min(6, len(results))]
        return payload

    def _score_item(
        self,
        query_tokens: set[str],
        item: _StoredItem,
        *,
        other_user_id: int | None,
        thread_root_id: int | None,
    ) -> float:
        if float(item.score or 0.0) > 0.0:
            return float(item.score)
        text_tokens = self._search_tokens(item.text_humanized or item.text)
        if not text_tokens:
            return 0.0
        overlap = len(query_tokens.intersection(text_tokens))
        score = overlap / max(1, min(len(query_tokens) or 1, len(text_tokens)))
        if other_user_id is not None and item.other_user_id == other_user_id:
            score += 0.70 if item.item_type in {"summary", "reflection"} else 0.25
        if thread_root_id is not None and item.thread_root_id == thread_root_id:
            score += 0.20
        score += min(0.20, float(item.importance or 0.0) * 0.2)
        return score

    def _search_tokens(self, text: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-z0-9']+", str(text or "").lower())
            if len(token) >= 3 and token not in CALLBACK_STOPWORDS
        }

    def _record_event(
        self,
        *,
        round_id: int,
        item_type: str,
        text: str,
        text_humanized: str,
        thread_root_id: int | None,
        other_user_id: int | None,
        relation_label: str | None,
        tone_label: str | None,
        importance: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._item_id += 1
        self._events.append(
            _StoredItem(
                item_id=self._item_id,
                item_type=item_type,
                round_id=round_id,
                text=text,
                text_humanized=text_humanized,
                thread_root_id=thread_root_id,
                other_user_id=other_user_id,
                relation_label=relation_label,
                tone_label=tone_label,
                importance=importance,
                metadata=metadata,
            )
        )

    def _upsert_social_card(
        self,
        *,
        other_user_id: int,
        round_id: int,
        thread_root_id: int | None,
        salient_claim: str | None,
        deltas: dict[str, Any],
        include_evidence: bool = True,
        count_as_event: bool = True,
    ) -> None:
        card = dict(self._social_cards.get(other_user_id) or {})
        card["affinity"] = float(card.get("affinity") or 0.0) + float(deltas.get("affinity_delta") or 0.0)
        card["conflict"] = float(card.get("conflict") or 0.0) + float(deltas.get("conflict_delta") or 0.0)
        card["humor"] = float(card.get("humor") or 0.0) + float(deltas.get("humor_delta") or 0.0)
        card["trust"] = float(card.get("trust") or 0.0) + float(deltas.get("trust_delta") or 0.0)
        card["last_round_id"] = round_id
        card["last_thread_root_id"] = thread_root_id
        card["event_count"] = int(card.get("event_count") or 0)
        if count_as_event:
            card["event_count"] += 1
        if include_evidence and salient_claim:
            card["summary_text"] = sanitize_prompt_memory_text(salient_claim, 400)
        self._social_cards[other_user_id] = card

    def _maybe_update_thread_card(self, *, thread_root_id: int, round_id: int, conv_text: str) -> None:
        self._thread_event_counts[thread_root_id] += 1
        parsed = self._parse_root_post_text(conv_text)
        gist_text = parsed["combined"] or sanitize_prompt_memory_text(conv_text, 220)
        participants = sorted(set(re.findall(r"@([A-Za-z0-9_]+)", conv_text or "")))[:6]
        self._thread_cards[thread_root_id] = {
            "gist_text": truncate(gist_text, 500),
            "my_role": "skeptic" if "wrong" in (conv_text or "").lower() else "neutral",
            "participants_top": participants,
            "entry_points": [],
            "last_seen_round_id": round_id,
        }

    def _maybe_update_community_digest(self, *, round_id: int) -> None:
        if not self._should_run_digest(round_id):
            return
        root_posts = self._get_recent_root_posts(round_id)
        maturity = self._digest_maturity_meta(root_posts)
        norms = []
        if maturity["mature"]:
            norms.append("structured title-plus-body posts")
            if any("?" in str((row.get("tweet") or "")).split("\n", 1)[0] for row in root_posts):
                norms.append("question bait titles")
        memes = []
        if any("hot take" in str(row.get("tweet") or "").lower() for row in root_posts):
            memes.append("hot take framing")
        self._community_digest = {
            "digest_text": "forum style favors compact title/body text posts",
            "norms": norms,
            "memes": memes,
            "top_topics": [],
            "polarizing_issues": [],
            "round_id": round_id,
        }
        self._last_digest_round = round_id

    def _maybe_generate_reflections(self, *, round_id: int) -> None:
        if not self._should_run_reflections(round_id):
            return
        if len(self._events) < self.config.reflection_min_events:
            return
        self._item_id += 1
        self._reflections.append(
            _StoredItem(
                item_id=self._item_id,
                item_type="reflection",
                round_id=round_id,
                text="the agent keeps returning to recurring disagreements in this community",
                text_humanized="the agent keeps returning to recurring disagreements in this community",
                importance=0.8,
            )
        )
        self._last_reflection_round = round_id

    def _should_run_digest(self, round_id: int) -> bool:
        if self._last_digest_round is None:
            return True
        return int(round_id) - int(self._last_digest_round) >= int(self.config.digest_update_cadence_rounds)

    def _should_run_reflections(self, round_id: int) -> bool:
        if self._last_reflection_round is None:
            return True
        return int(round_id) - int(self._last_reflection_round) >= int(self.config.reflection_cadence_rounds)

    def _heuristic_interaction_note(self, other_text: str, my_text: str) -> dict[str, Any]:
        text = f"{other_text} {my_text}".lower()
        return {
            "relation_label": "disagree" if any(token in text for token in ("wrong", "nah", "disagree")) else "neutral",
            "tone_label": "angry" if any(token in text for token in ("wrong", "bullshit")) else "curious",
            "affinity_delta": -0.05 if "wrong" in text else 0.05,
            "conflict_delta": 0.30 if any(token in text for token in ("wrong", "nah", "disagree")) else 0.0,
            "humor_delta": 0.1 if "lol" in text else 0.0,
            "trust_delta": 0.1 if "source" in text or "evidence" in text else 0.0,
            "salient_claim": sanitize_prompt_memory_text(my_text or other_text, 200),
        }

    def _detect_prior_opinion_match(
        self,
        *,
        incoming_text: str,
        other_user_id: int | None,
        thread_root_id: int | None,
        round_id: int | None,
    ) -> tuple[bool, dict[str, Any] | None]:
        result = self._search(
            query_text=self._build_query_text("my previously stated opinion or claim", incoming_text),
            other_user_id=other_user_id,
            thread_root_id=thread_root_id,
            types=["event", "reflection", "summary"],
            round_id=round_id,
            k=1,
        )
        items = result.get("items") or []
        if not items:
            return False, None
        top = items[0]
        return float(top.get("score") or 0.0) >= 0.55, top

    def _build_query_text(self, *parts: Any) -> str:
        return " ".join(str(part).strip() for part in parts if str(part or "").strip())

    def _get_recent_root_posts(self, round_id: int, limit: int = 24, rounds_back: int = 18) -> list[dict[str, Any]]:
        runtime_posts = self.runtime.get_recent_root_posts(round_id, limit=limit, rounds_back=rounds_back) or []
        if runtime_posts:
            return list(runtime_posts)
        rows = [
            row
            for row in self._recent_root_posts
            if row.get("round") is None or int(round_id) - int(row.get("round") or 0) <= rounds_back
        ]
        return rows[-limit:]

    def _digest_maturity_meta(self, root_posts: list[dict[str, Any]]) -> dict[str, Any]:
        authors = {row.get("user_id") for row in root_posts if row.get("user_id") is not None}
        return {
            "root_count": len(root_posts),
            "distinct_author_count": len(authors),
            "mature": len(root_posts) >= 6 and len(authors) >= 4,
        }

    def _json_list_maybe(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value]
        return []

    def _style_phrase_ok(self, value: Any) -> bool:
        phrase = self._style_phrase(value)
        return bool(phrase) and len(phrase) <= 48

    def _style_phrase(self, value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "").strip().lower())

    def _parse_root_post_text(self, text_value: str) -> dict[str, str]:
        text_value = str(text_value or "").strip()
        title = ""
        body = text_value
        if text_value.lower().startswith("title:"):
            head, _, tail = text_value.partition("\n")
            title = head[6:].strip()
            body = tail.strip()
        combined = " ".join(part for part in (title, body) if part).strip()
        return {"title": title, "body": body, "combined": combined}

    def _post_root_origin_kind(self, row: dict[str, Any]) -> str:
        if (row.get("news_id") or -1) not in (-1, 0, None):
            return "share_link"
        if (row.get("image_post_id") or -1) not in (-1, 0, None) or (row.get("image_id") or -1) not in (-1, 0, None):
            return "share_image"
        return "text_post"

    def _post_topic_fingerprint(self, text_value: str) -> dict[str, Any]:
        parsed = self._parse_root_post_text(text_value)
        combined = (parsed.get("combined") or "").lower()
        entity_matches = re.findall(r"'([^']+)'|\"([^\"]+)\"", text_value or "")
        entities = []
        for left, right in entity_matches:
            value = re.sub(r"\s+", " ", (left or right or "").strip().lower())
            if value:
                entities.append(value)
        title = (parsed.get("title") or "").lower()
        tokens = [
            token
            for token in re.findall(r"[a-z0-9]+", combined)
            if len(token) >= 3 and token not in CALLBACK_STOPWORDS
        ]
        return {"title": title, "tokens": tokens[:24], "entities": entities[:4], "combined": combined}

    def _post_topic_overlap_score(self, left: dict[str, Any], right: dict[str, Any]) -> float:
        if left.get("title") and right.get("title") and left.get("title") == right.get("title"):
            return 1.0
        left_entities = set(left.get("entities") or [])
        right_entities = set(right.get("entities") or [])
        if left_entities and right_entities and left_entities.intersection(right_entities):
            return 0.95
        left_tokens = set(left.get("tokens") or [])
        right_tokens = set(right.get("tokens") or [])
        if not left_tokens or not right_tokens:
            return 0.0
        return len(left_tokens.intersection(right_tokens)) / max(1, min(len(left_tokens), len(right_tokens)))

    def _truncate_block(self, text: str, max_chars: int) -> str:
        text = str(text or "").strip()
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 3].rstrip() + "..."
