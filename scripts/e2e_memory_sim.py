"""Deterministic end-to-end run of the memory engines, English vs Italian (step M7).

Same seed, same agents, same interaction schedule; only the language of the
messages and of the memory pack changes. No LLM and no server are involved: it
exercises the real engines (record_comment -> build_reply_context ->
high-affect detection) the way a client does, and compares what the agents get.

    python scripts/e2e_memory_sim.py [--json] [--write-golden | --check-golden]
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from yclient_memory import build_memory_engine, i18n  # noqa: E402
from yclient_memory.config import MemoryConfig  # noqa: E402
from yclient_memory.contracts import CommentMemoryEvent, ReplyMemoryRequest  # noqa: E402

CORPUS = json.loads((ROOT / "tests" / "data" / "heuristics_corpus.json").read_text(encoding="utf-8"))
GOLDEN = ROOT / "tests" / "golden" / "e2e_en.sha256"
AGENTS = 12
ROUNDS = 30
SEED = 20261017
PROTOCOL = ("affinity", "conflict", "humor", "trust")


class _Runtime:
    def llm_json(self, *a, **k):
        return {}

    def llm_text(self, *a, **k):
        return ""

    def get_author_id_and_username(self, post_id):
        return 1, "agent1"

    def get_thread_root_id(self, post_id):
        return post_id

    def get_recent_root_posts(self, *a, **k):
        return []

    def get_post_text(self, post_id):
        return ""

    def persona_snapshot(self):
        return {}

    def decision_log(self, payload):
        pass


def _messages(index: int, language: str) -> list[str]:
    """All sentences of the parallel corpus in one language, in a fixed order."""
    column = 0 if language == "en" else 1
    out = []
    for name in sorted(CORPUS):
        for kind in ("pos", "neg"):
            out.extend(pair[column] for pair in CORPUS[name][kind])
    return out


def run(language: str, backend: str) -> dict:
    rng = random.Random(SEED)  # agents and schedule do not depend on the language
    random.seed(SEED)  # the package draws callbacks from the global generator
    sentences = _messages(0, language)
    engines = {
        a: build_memory_engine(
            backend=backend,
            config=MemoryConfig(backend=backend, language=language, high_affect_enabled=True),
            runtime=_Runtime(),
        )
        for a in range(AGENTS)
    }
    transcript, stats = [], {
        "replies": 0, "callbacks": 0, "nonempty_memory": 0, "nonempty_cues": 0, "high_affect": 0,
        "errors": 0, "scopes": {},
    }
    for rnd in range(1, ROUNDS + 1):
        for me in range(AGENTS):
            other = rng.choice([a for a in range(AGENTS) if a != me])
            thread = rng.randrange(1, 6)
            their_text = sentences[rng.randrange(len(sentences))]
            my_text = sentences[rng.randrange(len(sentences))]
            engine = engines[me]
            try:
                ctx = engine.build_reply_context(ReplyMemoryRequest(
                    query_text=their_text, other_user_id=other, other_username=f"agent{other}",
                    thread_root_id=thread, round_id=rnd, incoming_text=their_text))
                signal = engine.detect_high_affect_signal(
                    incoming_text=their_text, thread_context="", other_user_id=other,
                    thread_root_id=thread, round_id=rnd, target_username=f"agent{other}") \
                    if hasattr(engine, "detect_high_affect_signal") else {}
                engine.record_comment(CommentMemoryEvent(
                    round_id=rnd, target_post_id=rnd * 100 + me, thread_root_id=thread,
                    other_user_id=other, other_username=f"agent{other}",
                    other_text=their_text, my_text=my_text, conv_text=their_text))
            except Exception as exc:  # pragma: no cover - reported, not hidden
                stats["errors"] += 1
                transcript.append(f"ERROR {type(exc).__name__}: {exc}")
                continue
            cues_text = getattr(ctx.cues, "rendered_text", "") or ""
            stats["replies"] += 1
            stats["nonempty_memory"] += bool(ctx.rendered_text.strip())
            stats["nonempty_cues"] += bool(cues_text.strip())
            stats["high_affect"] += bool(signal.get("is_high_affect"))
            stats["callbacks"] += bool(ctx.cues.should_callback)
            stats["scopes"][ctx.cues.scope] = stats["scopes"].get(ctx.cues.scope, 0) + 1
            transcript.append(f"{rnd}|{me}|{ctx.rendered_text}|{cues_text}|{signal.get('is_high_affect')}")
    stats["digest"] = hashlib.sha256("\n".join(transcript).encode("utf-8")).hexdigest()
    stats["_transcript"] = transcript
    return stats


def english_leak(transcript: list[str], language: str) -> int:
    """Count packs lines of an Italian run that still hold an English template sentence."""
    en = i18n._load("en")
    sentences = [
        v for k, v in en.items()
        if isinstance(v, str) and k.startswith(("cue__callback", "cue__argument", "cue__tone", "cue__anecdote", "cue__footer"))
        and "{" not in v
    ]
    return sum(any(s in line for s in sentences) for line in transcript)


def main(argv: list[str]) -> int:
    report = {}
    failures = []
    for backend in ("simple_recent", "hybrid_semantic"):
        en, it = run("en", backend), run("it", backend)
        ratio = (it["nonempty_cues"] / en["nonempty_cues"]) if en["nonempty_cues"] else 1.0
        ratio_mem = (it["nonempty_memory"] / en["nonempty_memory"]) if en["nonempty_memory"] else 1.0
        leak = english_leak(it["_transcript"], "it")
        proto_ok = all(
            ("affinity=" in line) for line in it["_transcript"]
            if "Storia con" in line
        )
        report[backend] = {
            "en": {k: v for k, v in en.items() if k != "_transcript"},
            "it": {k: v for k, v in it.items() if k != "_transcript"},
            "ratio_nonempty_cues": round(ratio, 3),
            "ratio_nonempty_memory": round(ratio_mem, 3),
            "english_sentences_in_italian_run": leak,
            "protocol_tokens_kept": proto_ok,
        }
        if ratio < 0.90 or ratio_mem < 0.90:
            failures.append(f"{backend}: Italian share of memory blocks below 90% of English")
        if leak:
            failures.append(f"{backend}: English template sentences found in the Italian run")
        if not proto_ok or en["errors"] or it["errors"]:
            failures.append(f"{backend}: protocol tokens lost or engine errors")
        if backend == "simple_recent":
            digest = en["digest"]
    if "--write-golden" in argv:
        GOLDEN.write_text(digest + "\n", encoding="utf-8")
    if "--check-golden" in argv and GOLDEN.read_text(encoding="utf-8").strip() != digest:
        failures.append("English end-to-end digest changed")
    if "--json" in argv:
        print(json.dumps(report, indent=1, ensure_ascii=False))
    else:
        for backend, r in report.items():
            print(f"[{backend}] replies EN {r['en']['replies']} / IT {r['it']['replies']}; "
                  f"non-empty cues IT/EN {r['ratio_nonempty_cues']}; memory IT/EN {r['ratio_nonempty_memory']}; "
                  f"high-affect EN {r['en']['high_affect']} IT {r['it']['high_affect']}; "
                  f"callbacks EN {r['en']['callbacks']} IT {r['it']['callbacks']}; "
                  f"English leaks {r['english_sentences_in_italian_run']}; errors EN {r['en']['errors']} IT {r['it']['errors']}")
            print(f"           scopes EN {r['en']['scopes']}  IT {r['it']['scopes']}")
    for failure in failures:
        print("FAIL:", failure)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
