# Changelog

## 0.2.0

- Texts shown to the language model moved from the code to `prompts/<language>.json`
  (`yclient_memory.i18n`), with English and Italian packs. English output is byte-identical to 0.1.x.
- `MemoryConfig.language` (`memory_language`), default `en`; missing language or key falls back to English with one warning.
- Keyword heuristics (affect triggers, interaction notes, callback markers, stop words, tokenization) read language lexicons.
- `scripts/golden_snapshot.py`, `scripts/measure_heuristics.py`, `scripts/e2e_memory_sim.py` and the parallel EN/IT corpus.
- Package data declared: `prompts/*.json` is included in the wheel.
- Plugin manifest `meta/info.json` for YWeb ("Agent Memory").

## 0.1.0

- First PyPI release.
