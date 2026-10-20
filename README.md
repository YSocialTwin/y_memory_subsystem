# y_memory_subsystem

> Gives simulated agents a memory of past interactions: relationship history, thread continuity and conversation cues used when they reply.

## Overview

This repository is the YSocial plugin **y_memory_subsystem**, published as the `yclient-memory` Python package. In [YSocial](https://github.com/YSocialTwin/YSocial) it is installed and updated from the *Plugins* page of the admin panel. It is an in-tree implementation of the external memory package described in [`external_memory_package_pipeline.md`](external_memory_package_pipeline.md).

## Features

- a stable `yclient_memory` import surface
- shared contracts and runtime protocols
- a `build_memory_engine()` factory
- two interchangeable backends: `hybrid_semantic` and `simple_recent`
- language packs for the texts shown to the language model (`en`, `it`)

**`hybrid_semantic`**

- preserves the richer Reddit-style behavior
- tracks social cards, thread cards, community digest, and reflections
- supports semantic-style lexical retrieval, high-affect recall, and post-style guidance

**`simple_recent`**

- keeps deterministic recent interaction state only
- exposes the same engine signature with fewer capabilities
- is suitable for lower-dependency adoption in other clients

## Requirements

- Python 3.9 or later
- A runtime adapter provided by the client that uses the package (see [Runtime adapter](#runtime-adapter))

## Installation

From PyPI, once published:

```bash
pip install yclient-memory
```

From a checkout:

```bash
git clone https://github.com/YSocialTwin/y_memory_subsystem.git
cd y_memory_subsystem
python -m pip install .
```

## Usage

```python
from yclient_memory import build_memory_engine
from yclient_memory.config import MemoryConfig

memory = build_memory_engine(
    backend="hybrid_semantic",
    config=MemoryConfig.from_mapping({"memory_vote_signal_only": True}),
    runtime=my_runtime_adapter,
)
```

### Public API

```python
from yclient_memory import build_memory_engine
from yclient_memory.contracts import (
    CommentMemoryEvent,
    PostStyleRequest,
    ReplyMemoryRequest,
)
```

Core operations:

- `build_reply_context()`
- `build_browse_context()`
- `build_post_style_context()`
- `record_comment()`
- `record_vote()`
- `record_post()`
- `relationship_signal()`
- `maintenance_tick()`

### Runtime adapter

The package expects a runtime object with the methods documented in
[`docs/runtime_adapter.md`](docs/runtime_adapter.md).

At minimum, backends depend on:

- `get_author_id_and_username(post_id)`
- `get_thread_root_id(post_id)`
- `get_recent_root_posts(round_id, limit, rounds_back)`
- `get_post_text(post_id)`
- `llm_json(prompt_key, variables, config=None)`
- `llm_text(prompt_key, variables, config=None)`
- `decision_log(payload)`

### Notebooks

Example walkthroughs live in:

- [`output/jupyter-notebook/hybrid-semantic-memory-walkthrough.ipynb`](output/jupyter-notebook/hybrid-semantic-memory-walkthrough.ipynb)
- [`output/jupyter-notebook/simple-recent-memory-walkthrough.ipynb`](output/jupyter-notebook/simple-recent-memory-walkthrough.ipynb)

## Configuration

Engines are configured with `MemoryConfig`, for instance `MemoryConfig.from_mapping({"memory_vote_signal_only": True})`.

### Languages

The texts shown to the language model come from language packs (`en` and `it`):
`MemoryConfig(language="it")`. English is the default and is unchanged; a missing
language or key falls back to English with one warning. See [docs/languages.md](docs/languages.md),
including how to add a language.

## Documentation

- Repository documentation (MkDocs) in [`docs/`](docs): [API](docs/api.md), [backends matrix](docs/backend_matrix.md), [runtime adapter](docs/runtime_adapter.md), [languages](docs/languages.md), [release pipeline](docs/release_pipeline.md)
- Preview it with `uv run --with mkdocs-material mkdocs serve`; strict build with `uv run --with mkdocs-material mkdocs build --strict`

## Testing

```bash
python -m pytest
```

## Packaging and release

Build locally:

```bash
python -m pip install .[release]
python -m build
python -m twine check dist/*
```

The repository also includes GitHub Actions workflows for package validation and PyPI publishing:

- [package.yml](.github/workflows/package.yml)
- [publish-pypi.yml](.github/workflows/publish-pypi.yml)

Release details are documented in [docs/release_pipeline.md](docs/release_pipeline.md).

## Contributing

Contributions are welcome. Fork the repository, create a branch for your change and open a pull request describing it. Run the tests before opening a pull request.

## Citation

If you use YSocial in your research, please cite:

```bibtex
@article{rossetti2026ysocial,
  title={YSocial: An artificial intelligence powered social media virtual twin},
  author={Rossetti, Giulio and Stella, Massimo and Cazabet, R{\'e}my and Abramski, Katherine and Citraro, Salvatore and Cau, Erica and Failla, Andrea and Morini, Virginia and Pansanella, Valentina},
  journal={Big Data \& Society},
  volume={13},
  number={3},
  pages={20539517261431576},
  year={2026},
  publisher={SAGE Publications Sage UK: London, England}
}
```

## License

Released under the GNU General Public License v3.0. See [LICENSE](LICENSE) for details.
