"""Top-1 retrieval of the right memory among distractors, English vs Italian.

The hybrid backend scores items by token overlap. This measures whether a query about
the same topic (different words, same content words) finds its memory in each language.

    python scripts/measure_retrieval.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from yclient_memory.backends.hybrid_semantic.engine import HybridSemanticMemoryEngine, _StoredItem  # noqa: E402
from yclient_memory.config import MemoryConfig  # noqa: E402

DATA = json.loads((ROOT / "tests" / "data" / "retrieval_pairs.json").read_text(encoding="utf-8"))


class _RT:
    def llm_json(self, *a, **k):
        return {}

    def llm_text(self, *a, **k):
        return ""

    def get_recent_root_posts(self, *a, **k):
        return []

    def decision_log(self, payload):
        pass


def measure(language: str, seed: int = 11) -> dict:
    rng = random.Random(seed)
    column = (0, 1) if language == "en" else (2, 3)
    distractors = DATA["distractors_en" if language == "en" else "distractors_it"]
    hits = 0
    margins = []
    for stored, query in ((p[column[0]], p[column[1]]) for p in DATA["pairs"]):
        engine = HybridSemanticMemoryEngine(config=MemoryConfig(language=language), runtime=_RT())
        texts = [stored] + rng.sample(distractors, len(distractors))
        for index, text in enumerate(texts, start=1):
            engine._events.append(_StoredItem(
                item_id=index, item_type="event", round_id=1, text=text, text_humanized=text,
                thread_root_id=None, other_user_id=None, importance=0.0))
        tokens = engine._search_tokens(query.lower())
        scored = sorted(
            ((engine._score_item(tokens, item, other_user_id=None, thread_root_id=None), item.item_id)
             for item in engine._events), reverse=True)
        best_score, best_id = scored[0]
        hits += best_id == 1 and best_score > 0
        margins.append(scored[0][0] - (scored[1][0] if len(scored) > 1 else 0))
    return {"top1": hits / len(DATA["pairs"]), "pairs": len(DATA["pairs"])}


def main() -> int:
    en, it = measure("en"), measure("it")
    print(f"top-1 retrieval  EN {en['top1']:.2f}   IT {it['top1']:.2f}   ({en['pairs']} pairs, {len(DATA['distractors_en'])} distractors)")
    return 0 if it["top1"] >= 0.8 * en["top1"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
