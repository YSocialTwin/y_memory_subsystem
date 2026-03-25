# yclient-memory

`yclient-memory` is an in-tree implementation of the external memory package described in
[`external_memory_package_pipeline.md`](https://github.com/YSocialTwin/y_memory_subsystem/blob/main/external_memory_package_pipeline.md).

It provides:

- a stable `yclient_memory` import surface
- shared contracts and runtime protocols
- a `build_memory_engine()` factory
- two interchangeable backends:
  - `hybrid_semantic`
  - `simple_recent`

## Installation

From PyPI, once published:

```bash
pip install yclient-memory
```

## Quick Start

```python
from yclient_memory import build_memory_engine
from yclient_memory.config import MemoryConfig

memory = build_memory_engine(
    backend="hybrid_semantic",
    config=MemoryConfig.from_mapping({"memory_vote_signal_only": True}),
    runtime=my_runtime_adapter,
)
```

## Public API

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

## Backends

`hybrid_semantic`

- preserves the richer Reddit-style behavior
- tracks social cards, thread cards, community digest, and reflections
- supports semantic-style lexical retrieval, high-affect recall, and post-style guidance

`simple_recent`

- keeps deterministic recent interaction state only
- exposes the same engine signature with fewer capabilities
- is suitable for lower-dependency adoption in other clients

## Runtime Adapter

The package expects a runtime object with the methods documented in
[`docs/runtime_adapter.md`](https://github.com/YSocialTwin/y_memory_subsystem/blob/main/docs/runtime_adapter.md).

At minimum, backends depend on:

- `get_author_id_and_username(post_id)`
- `get_thread_root_id(post_id)`
- `get_recent_root_posts(round_id, limit, rounds_back)`
- `get_post_text(post_id)`
- `llm_json(prompt_key, variables, config=None)`
- `llm_text(prompt_key, variables, config=None)`
- `decision_log(payload)`

## Notebooks

Example walkthroughs live in:

- [`output/jupyter-notebook/hybrid-semantic-memory-walkthrough.ipynb`](https://github.com/YSocialTwin/y_memory_subsystem/blob/main/output/jupyter-notebook/hybrid-semantic-memory-walkthrough.ipynb)
- [`output/jupyter-notebook/simple-recent-memory-walkthrough.ipynb`](https://github.com/YSocialTwin/y_memory_subsystem/blob/main/output/jupyter-notebook/simple-recent-memory-walkthrough.ipynb)

## Development

```bash
python -m pytest
```

## Packaging And Release

Build locally:

```bash
python -m pip install .[release]
python -m build
python -m twine check dist/*
```

The repository also includes GitHub Actions workflows for package validation and PyPI publishing:

- [package.yml](https://github.com/YSocialTwin/y_memory_subsystem/blob/main/.github/workflows/package.yml)
- [publish-pypi.yml](https://github.com/YSocialTwin/y_memory_subsystem/blob/main/.github/workflows/publish-pypi.yml)

Release details are documented in [docs/release_pipeline.md](https://github.com/YSocialTwin/y_memory_subsystem/blob/main/docs/release_pipeline.md).

## MkDocs

```bash
uv run --with mkdocs-material mkdocs serve
```

Strict build:

```bash
uv run --with mkdocs-material mkdocs build --strict
```
