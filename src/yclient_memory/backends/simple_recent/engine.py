from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from ...capabilities import MemoryCapabilities
from ...logging import emit_decision_log
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
from ...policies.decay_policy import apply_decay
from ... import i18n
from ...policies.prompt_policy import build_conversation_cues, format_conversation_cues
from ...policies.safety_policy import sanitize_prompt_memory_text, truncate


@dataclass
class _RelationshipState:
    affinity: float = 0.0
    conflict: float = 0.0
    humor: float = 0.0
    trust: float = 0.0
    summary_text: str = ""
    last_round_id: int | None = None
    event_count: int = 0


@dataclass
class _RecentItem:
    round_id: int
    thread_root_id: int | None
    other_user_id: int | None
    text: str
    kind: str


def _clip(items: list[_RecentItem], limit: int) -> list[_RecentItem]:
    if len(items) <= limit:
        return items
    return items[-limit:]


def _relationship_deltas_from_comment(
    my_text: str, other_text: str, language: str | None = None
) -> tuple[float, float, float, float]:
    text = f"{my_text} {other_text}".lower()
    affinity = 0.15 if i18n.contains_any(text, "lex__s_affinity", language) else 0.0
    conflict = 0.25 if i18n.contains_any(text, "lex__s_conflict", language) else 0.0
    humor = 0.15 if i18n.contains_any(text, "lex__s_humor", language) else 0.0
    trust = 0.10 if i18n.contains_any(text, "lex__s_trust", language) else 0.0
    if conflict > 0.0:
        affinity -= 0.05
        trust -= 0.05
    return affinity, conflict, humor, trust


class SimpleRecentMemoryEngine:
    def __init__(self, *, config, runtime):
        self.config = config
        self.runtime = runtime
        self._pair_history: dict[int, list[_RecentItem]] = defaultdict(list)
        self._thread_history: dict[int, list[_RecentItem]] = defaultdict(list)
        self._relationships: dict[int, _RelationshipState] = defaultdict(_RelationshipState)
        self._posts: list[PostMemoryEvent] = []
        self._last_decay_round: int | None = None

    def _t(self, key: str, **fields) -> str:
        return i18n.text(key, self.config.language, **fields)

    def capabilities(self) -> MemoryCapabilities:
        return MemoryCapabilities(
            relationship_memory=True,
            thread_memory=True,
        )

    def build_reply_context(self, request: ReplyMemoryRequest) -> ReplyMemoryContext:
        diagnostics = MemoryDiagnostics(usage="recent_only")
        lines = []
        other_user_id = request.other_user_id
        if other_user_id is not None and other_user_id in self._relationships:
            state = self._relationships[other_user_id]
            lines.append(
                self._t(
                    "mem__history_line",
                    username=(request.other_username or self._t("mem__user_fallback")).lstrip("@"),
                    affinity=f"{state.affinity:.2f}",
                    conflict=f"{state.conflict:.2f}",
                    humor=f"{state.humor:.2f}",
                    trust=f"{state.trust:.2f}",
                )
            )
            if state.summary_text:
                lines.append(self._t("mem__continuity_label", text=state.summary_text))

        pair_lines = []
        if other_user_id is not None:
            for item in reversed(self._pair_history.get(other_user_id, [])):
                if request.thread_root_id is not None and item.thread_root_id == request.thread_root_id:
                    pair_lines.append(self._t("mem__continuity_earlier", text=item.text))
                    break
            if not pair_lines:
                for item in reversed(self._pair_history.get(other_user_id, [])):
                    if request.thread_root_id is None or item.thread_root_id != request.thread_root_id:
                        pair_lines.append(self._t("mem__continuity_callback", text=item.text))
                        diagnostics.metadata["cross_thread_callback_candidate"] = True
                        break
        lines.extend(pair_lines)

        rendered = truncate("\n".join(lines).strip(), self.config.reply_context_max_chars * 2)
        diagnostics.retrieved_item_count = len(pair_lines) + (1 if other_user_id in self._relationships else 0)
        diagnostics.top_score = 0.85 if pair_lines else (0.6 if lines else None)
        meta = {
            "retrieved_item_count": diagnostics.retrieved_item_count,
            "top_score": diagnostics.top_score,
            "continuity_text": sanitize_prompt_memory_text(" | ".join(lines), self.config.reply_context_max_chars),
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
            language=self.config.language,
        )
        cues.rendered_text = format_conversation_cues(
            cues, self.config.nuance_cues_max_chars, language=self.config.language
        )
        return ReplyMemoryContext(
            rendered_text=rendered,
            cues=cues,
            diagnostics=diagnostics,
            continuity_text=meta["continuity_text"],
        )

    def build_browse_context(self, request: BrowseMemoryRequest) -> BrowseMemoryContext:
        diagnostics = MemoryDiagnostics(usage="thread_local")
        if request.thread_root_id is None:
            diagnostics.usage = "none"
            return BrowseMemoryContext(diagnostics=diagnostics)

        items = self._thread_history.get(request.thread_root_id, [])
        if not items:
            diagnostics.usage = "none"
            return BrowseMemoryContext(diagnostics=diagnostics)

        latest = items[-3:]
        lines = [self._t("mem__thread_header")]
        for item in latest:
            lines.append(f"- r{item.round_id}: {item.text}")
        diagnostics.retrieved_item_count = len(latest)
        return BrowseMemoryContext(rendered_text=truncate("\n".join(lines), 220), diagnostics=diagnostics)

    def build_post_style_context(self, request: PostStyleRequest) -> PostStyleContext:
        return PostStyleContext(diagnostics=MemoryDiagnostics(usage="none"))

    def record_comment(self, event: CommentMemoryEvent) -> None:
        if event.other_user_id is None:
            return
        summary = sanitize_prompt_memory_text(
            event.my_text
            or event.other_text
            or self._t("mem__commented_with", username=event.other_username or "user"),
            120,
        )
        item = _RecentItem(
            round_id=event.round_id,
            thread_root_id=event.thread_root_id,
            other_user_id=event.other_user_id,
            text=summary,
            kind="comment",
        )
        self._pair_history[event.other_user_id] = _clip(
            self._pair_history[event.other_user_id] + [item],
            self.config.pair_history_limit,
        )
        self._thread_history[event.thread_root_id] = _clip(
            self._thread_history[event.thread_root_id] + [item],
            self.config.thread_history_limit,
        )

        state = self._relationships[event.other_user_id]
        affinity, conflict, humor, trust = _relationship_deltas_from_comment(
            event.my_text, event.other_text, self.config.language
        )
        state.affinity += affinity
        state.conflict += conflict
        state.humor += humor
        state.trust += trust
        state.event_count += 1
        state.last_round_id = event.round_id
        state.summary_text = summary
        emit_decision_log(
            self.runtime,
            {
                "decision_type": "memory_record_comment",
                "backend": "simple_recent",
                "other_user_id": event.other_user_id,
                "thread_root_id": event.thread_root_id,
            },
        )

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

        state = self._relationships[other_user_id]
        delta = 0.5 if event.vote_type == "like" else -0.3
        state.affinity += delta
        state.conflict += 0.6 if event.vote_type != "like" else -0.1
        state.trust += 0.2 if event.vote_type == "like" else -0.2
        state.event_count += 1
        state.last_round_id = event.round_id
        if not self.config.vote_signal_only:
            text = sanitize_prompt_memory_text(
                event.post_text or self.runtime.get_post_text(int(event.post_id)),
                120,
            )
            item = _RecentItem(
                round_id=event.round_id,
                thread_root_id=thread_root_id,
                other_user_id=other_user_id,
                text=f"{event.vote_type} on @{(other_username or 'user').lstrip('@')}: {text}".strip(": "),
                kind="vote",
            )
            self._pair_history[other_user_id] = _clip(
                self._pair_history[other_user_id] + [item],
                self.config.pair_history_limit,
            )

    def record_post(self, event: PostMemoryEvent) -> None:
        self._posts.append(event)

    def relationship_signal(self, request: RelationshipSignalRequest) -> RelationshipSignal:
        if request.other_user_id is None or request.other_user_id not in self._relationships:
            return RelationshipSignal()
        state = self._relationships[request.other_user_id]
        return RelationshipSignal(
            affinity=round(state.affinity, 2),
            conflict=round(state.conflict, 2),
            humor=round(state.humor, 2),
            trust=round(state.trust, 2),
            summary_text=state.summary_text,
            metadata={"event_count": state.event_count},
        )

    def maintenance_tick(self, request: MaintenanceTickRequest) -> MaintenanceTickResult:
        actions = []
        if self._last_decay_round is None:
            self._last_decay_round = request.round_id
            return MaintenanceTickResult(performed_actions=actions)
        rounds_elapsed = request.round_id - self._last_decay_round
        if rounds_elapsed <= 0:
            return MaintenanceTickResult(performed_actions=actions)
        for state in self._relationships.values():
            state.affinity = apply_decay(state.affinity, rounds_elapsed=rounds_elapsed)
            state.conflict = apply_decay(state.conflict, rounds_elapsed=rounds_elapsed)
            state.humor = apply_decay(state.humor, rounds_elapsed=rounds_elapsed)
            state.trust = apply_decay(state.trust, rounds_elapsed=rounds_elapsed)
        self._last_decay_round = request.round_id
        actions.append("decayed_relationships")
        return MaintenanceTickResult(performed_actions=actions, diagnostics={"rounds_elapsed": rounds_elapsed})
