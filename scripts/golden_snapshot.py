"""Golden snapshot of the English texts rendered by yclient_memory.

`--write` records the current output, `--check` compares against it (CI check).
The English snapshot must stay byte-identical across the i18n work.
"""
from __future__ import annotations

import itertools
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
GOLDEN = ROOT / "tests" / "golden" / "en_snapshot.json"

from yclient_memory.backends.simple_recent.engine import SimpleRecentMemoryEngine  # noqa: E402
from yclient_memory.config import MemoryConfig  # noqa: E402
from yclient_memory.contracts import CommentMemoryEvent, ReplyMemoryRequest  # noqa: E402
from yclient_memory.policies.prompt_policy import (  # noqa: E402
    build_conversation_cues,
    format_conversation_cues,
)


class _Runtime:
    def llm_json(self, *a, **k):
        return {}

    def llm_text(self, *a, **k):
        return ""

    def get_author_id_and_username(self, post_id):
        return 55, "alice"

    def get_thread_root_id(self, post_id):
        return 900

    def get_recent_root_posts(self, *a, **k):
        return []

    def get_post_text(self, post_id):
        return "you are wrong"

    def persona_snapshot(self):
        return {}

    def decision_log(self, payload):
        pass


def render() -> dict:
    out: dict = {}
    metas = {
        "degraded": {"embedding_degraded": True, "retrieved_item_count": 0},
        "cold": {"no_ready_candidates": True, "retrieved_item_count": 0},
        "strong": {"retrieved_item_count": 3, "top_score": 0.9,
                   "cross_thread_callback_candidate": True, "continuity_text": "with @bob: x"},
        "partial": {"retrieved_item_count": 1, "top_score": 0.1},
        "degraded_mode": {"degraded_mode": True, "retrieved_item_count": 1, "top_score": 0.5},
        "none": {},
    }
    metrics = {
        "neutral": "",
        "clash": "affinity=0.00, conflict=0.60, humor=0.00, trust=-0.30",
        "align": "affinity=0.60, conflict=0.00, humor=0.30, trust=0.20",
    }
    for (mk, meta), (tk, text), subtle, target in itertools.product(
        metas.items(), metrics.items(), (False, True), (None, "@Bob")
    ):
        random.seed(7)
        cues = build_conversation_cues(
            memory_text=text, memory_meta=meta, subtle_mode=subtle, target_username=target
        )
        out[f"cues|{mk}|{tk}|{subtle}|{target}"] = format_conversation_cues(cues)

    rt = _Runtime()
    engine = SimpleRecentMemoryEngine(config=MemoryConfig(backend="simple_recent"), runtime=rt)
    for rnd, thread in ((2, 900), (3, 901)):
        engine.record_comment(CommentMemoryEvent(
            round_id=rnd, target_post_id=10 + rnd, thread_root_id=thread, other_user_id=55,
            other_username="alice", other_text="that benchmark is weak",
            my_text="nah your benchmark evidence is weak", conv_text="thread"))
    for key, thread in (("same", 900), ("other", 777)):
        random.seed(7)
        ctx = engine.build_reply_context(ReplyMemoryRequest(
            round_id=4, thread_root_id=thread, other_user_id=55,
            other_username="alice", query_text="benchmark"))
        out[f"simple_recent|{key}"] = {
            "rendered": ctx.rendered_text,
            "continuity": ctx.continuity_text,
            "cues": format_conversation_cues(ctx.cues),
        }
    return out


def main(argv: list[str]) -> int:
    data = json.dumps(render(), indent=1, sort_keys=True, ensure_ascii=False, default=str)
    if "--write" in argv:
        GOLDEN.write_text(data + "\n", encoding="utf-8")
        print(f"written {GOLDEN}")
        return 0
    if GOLDEN.read_text(encoding="utf-8") != data + "\n":
        print("English snapshot CHANGED")
        return 1
    print("English snapshot identical")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
