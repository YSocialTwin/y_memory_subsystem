# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

## [0.2.0] - 2026-10-20

### Added
- Texts shown to the language model moved from the code to `prompts/<language>.json`
  (`yclient_memory.i18n`), with English and Italian packs. English output is byte-identical to 0.1.x.
- `MemoryConfig.language` (`memory_language`), default `en`; missing language or key falls back to English with one warning.
- `scripts/golden_snapshot.py`, `scripts/measure_heuristics.py`, `scripts/e2e_memory_sim.py` and the parallel EN/IT corpus.
- Plugin manifest `meta/info.json` for YWeb ("Agent Memory").

### Changed
- Keyword heuristics (affect triggers, interaction notes, callback markers, stop words, tokenization) read language lexicons.
- Package data declared: `prompts/*.json` is included in the wheel.
- License: GPL-3.0-only (was MIT), declared in `LICENSE`, `pyproject.toml`, `meta/info.json` and the README.
- README restructured on the common layout; citation updated to the published YSocial reference (Big Data & Society, 2026).

## 0.1.0

- First PyPI release.

[Unreleased]: https://github.com/YSocialTwin/y_memory_subsystem/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/YSocialTwin/y_memory_subsystem/releases/tag/v0.2.0
