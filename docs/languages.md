# Languages

Every sentence that `yclient_memory` shows to a language model lives in a language
pack, `src/yclient_memory/prompts/<language>.json`. English (`en`) and Italian (`it`)
ship with the package. The language is chosen with `MemoryConfig.language`
(`memory_language` in a mapping); the default is `en`.

```python
from yclient_memory import build_memory_engine
from yclient_memory.config import MemoryConfig

engine = build_memory_engine(
    backend="hybrid_semantic",
    config=MemoryConfig(language="it"),
    runtime=runtime,
)
```

Inside YWeb the language is the prompt language of the experiment: the clients pass it
for you, so nothing has to be configured.

## Guarantees

- English output is byte-identical to version 0.1.x (checked by
  `python scripts/golden_snapshot.py --check`).
- A language or a key that is missing falls back to English and logs one warning.
- Protocol tokens are never translated: `affinity`, `conflict`, `humor`, `trust`, the
  `[M1]` markers, `@username` and `r<N>`. Other code parses them back from the text.
- Stored internal values keep their canonical form (for example the vote summaries
  `upvote on @user: ...`); they are filtered before they reach a prompt.

## Two kinds of entries

Texts are `str.format` templates, for example `"with @{username}: {text}"`. A
translation must keep the same `{fields}`.

Lexicons (keys starting with `lex__`) are word lists used by the keyword heuristics
that read the *incoming* messages: affect triggers, interaction notes, callback markers
and stop words. English keeps its historic plain substring match. Other languages match
an entry at the start of a word, so a stem such as `sbagliat` covers `sbagliato` and
`sbagliata` without firing inside unrelated words; entries made of symbols (`?`) stay
plain substrings. Write entries in lowercase.

## Add a language

No code change is needed.

1. Copy `prompts/en.json` to `prompts/<code>.json` (two or three letters, for example `fr`).
2. Translate every value. Keep the `{fields}`, the protocol tokens and the leading `[`
   of the block headers. Lexicons are lists of lowercase words and stems.
3. Run the checks:

   ```bash
   python -m pytest                       # same keys and fields as English, block limits
   python scripts/measure_heuristics.py   # recall of the lexicons on the EN/IT corpus
   ```

   `tests/test_i18n.py` already runs for every pack it finds. The cue block must stay
   within 900 characters, the thread block within 220 and the style block within 280:
   longer translations are cut by the engines. To measure a new lexicon, add the language
   column to `tests/data/heuristics_corpus.json`.
4. Have the translation read by a native speaker before using it in an experiment.

## Measuring the heuristics

`scripts/measure_heuristics.py` compares recall and false positives of each keyword
heuristic on a parallel English/Italian corpus (rule: the language is acceptable when its
recall is at least 80% of English and false positives stay within ten points). A small
Italian hold-out written after the lexicons reports how well they generalise.

`scripts/e2e_memory_sim.py` runs both backends over the same seed, agents and schedule in
English and Italian, and compares the share of replies that get a memory block, the
callbacks, the high-affect signals and the absence of English sentences in the Italian run.
