"""Recall of the keyword heuristics on the parallel EN/IT corpus (step M6).

    python scripts/measure_heuristics.py [--json]

Rule used for the decision: a language is acceptable when its recall is at least
80% of the English recall and its false-positive rate does not exceed English by
more than 10 points.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
CORPUS = ROOT / "tests" / "data" / "heuristics_corpus.json"

from yclient_memory.backends.hybrid_semantic.engine import HybridSemanticMemoryEngine  # noqa: E402
from yclient_memory.backends.simple_recent import engine as simple  # noqa: E402
from yclient_memory.config import MemoryConfig  # noqa: E402
from yclient_memory.policies.affect_policy import detect_high_affect_signal  # noqa: E402
from yclient_memory.policies.safety_policy import reply_references_recalled_item  # noqa: E402


def _lang(fn, language):
    try:
        return fn(language)
    except TypeError:
        return fn(None)


def _trigger(key):
    def run(text, language):
        try:
            result = detect_high_affect_signal(incoming_text=text, language=language)
        except TypeError:
            result = detect_high_affect_signal(incoming_text=text)
        return bool(result["triggers"][key])
    return run


def _note(text, language):
    engine = HybridSemanticMemoryEngine(config=MemoryConfig(language=language), runtime=object())
    return engine._heuristic_interaction_note(text, "")


def _deltas(text, language):
    try:
        return simple._relationship_deltas_from_comment(text, "", language=language)
    except TypeError:
        return simple._relationship_deltas_from_comment(text, "")


def _callback(text, language):
    try:
        ok, why = reply_references_recalled_item(text, [{"text": "x"}], language=language)
    except TypeError:
        ok, why = reply_references_recalled_item(text, [{"text": "x"}])
    return ok and why == "callback_marker"


DETECTORS = {
    "criticism": _trigger("criticism_or_challenge"),
    "conflict": _trigger("conflict_or_argument"),
    "anecdote": _trigger("incoming_anecdote"),
    "prior": _trigger("defending_prior_opinion"),
    "disagree": lambda t, l: _note(t, l)["relation_label"] == "disagree",
    "humor": lambda t, l: _deltas(t, l)[2] > 0,
    "trust": lambda t, l: _deltas(t, l)[3] > 0,
    "affinity": lambda t, l: _deltas(t, l)[0] > 0,
    "callback": _callback,
}


def measure() -> dict:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    out = {}
    for name, sets in corpus.items():
        detect = DETECTORS[name]
        row = {}
        for index, language in enumerate(("en", "it")):
            pos = [detect(pair[index], language) for pair in sets["pos"]]
            neg = [detect(pair[index], language) for pair in sets["neg"]]
            row[language] = {
                "recall": sum(pos) / len(pos),
                "false_positive": sum(neg) / len(neg),
            }
        en, it = row["en"]["recall"], row["it"]["recall"]
        row["ratio"] = (it / en) if en else None
        row["ok"] = bool(en) and it >= 0.8 * en and row["it"]["false_positive"] <= row["en"]["false_positive"] + 0.10
        out[name] = row
    return out


def measure_holdout() -> dict:
    """Italian sentences written after the lexicons, never used to tune them."""
    holdout = json.loads((ROOT / "tests" / "data" / "heuristics_holdout_it.json").read_text(encoding="utf-8"))
    out = {}
    for name, sets in holdout.items():
        detect = DETECTORS[name]
        pos = [detect(t, "it") for t in sets["pos"]]
        neg = [detect(t, "it") for t in sets["neg"]]
        out[name] = {"recall": sum(pos) / len(pos), "false_positive": sum(neg) / len(neg)}
    return out


def main(argv):
    result = measure()
    if "--json" in argv:
        print(json.dumps(result, indent=1))
    else:
        print(f"{'heuristic':10} {'EN rec':>7} {'IT rec':>7} {'IT/EN':>6} {'EN fp':>6} {'IT fp':>6}  ok")
        for name, r in result.items():
            ratio = "-" if r["ratio"] is None else f"{r['ratio']:.2f}"
            print(f"{name:10} {r['en']['recall']:7.2f} {r['it']['recall']:7.2f} {ratio:>6} "
                  f"{r['en']['false_positive']:6.2f} {r['it']['false_positive']:6.2f}  {'yes' if r['ok'] else 'NO'}")
    print("\nitalian hold-out (not used to build the lexicons)")
    for name, r in measure_holdout().items():
        print(f"{name:10} recall {r['recall']:.2f}  false positives {r['false_positive']:.2f}")
    return 0 if all(r["ok"] for r in result.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
