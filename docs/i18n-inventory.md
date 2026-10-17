# i18n inventory (step M0)

Baseline: branch `prompts-i18n` from `main` @ 5fe85eb, 22 tests passing,
version 0.1.0, no runtime dependencies, no package-data declared.

## Texts that reach the LLM (to externalize in M3)

| Where | What | Notes |
|---|---|---|
| `policies/prompt_policy.py` | cue hints: callback (5), argument (3), tone (4), anecdote (4); header `[MEMORY CONVERSATION CUES]`; field labels `scope/callback/continuity/argument/tone/anecdote`; closing "Never invent..." line; `this user` fallback | truncation at 900 chars: check in IT |
| `backends/hybrid_semantic/engine.py` | `History with @u: affinity=..` line, `with @u:`, `this thread:`, `earlier here:`, `if clearly relevant:`; recall pack `- [M{n}] (...)` lines; vote/comment event summaries (`upvote on @u: ..`) | |
| `backends/simple_recent/engine.py` | `History with`, `Continuity:`, `earlier here:`, `if clearly relevant:`, `- r{n}:` lines, `commented with @u`, vote summaries | |

## Protocol tokens (never translated)

`affinity`, `conflict`, `humor`, `trust` (parsed back from text by
`_extract_metric`), `[M{n}]` markers, `@username`, `r{n}`, `s=` scores.

## English heuristics (decision D5, measure in M6)

Keyword lists used to classify events (`hybrid_semantic/engine.py` ~l.803,
`simple_recent/engine.py` ~l.56, `affect_policy.py`, `safety_policy.py`).

## Outside this package

- `memory_high_affect_classifier` prompt: rendered by the clients
  (`YClient`/`YClientReddit` `memory_runtime.py` -> `agent._memory_llm_high_affect_classifier`),
  not by this package: handled with the client packs in M5.
- Install points of `yclient-memory`: `requirements/base.in|txt`, `requirements.lock`
  (0.1.0), `external/{YClient,YClientReddit}/requirements_client.txt`,
  `external/YSimulator/requirements.txt` (>=0.1.0). Consumers:
  `y_client/memory_runtime.py`, `classes/base_agent.py` (YClient, YClientReddit,
  YSimulator copy).

## Golden snapshot

`scripts/golden_snapshot.py --check` compares `tests/golden/en_snapshot.json`
(cues grid 6x3x2x2 + simple_recent reply contexts). The hybrid backend is added
in M3 together with its extraction. `--write` only on the baseline.
