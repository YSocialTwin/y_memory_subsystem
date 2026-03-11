from __future__ import annotations

from .backends.hybrid_semantic.engine import HybridSemanticMemoryEngine
from .backends.simple_recent.engine import SimpleRecentMemoryEngine
from .config import MemoryConfig
from .errors import UnsupportedBackendError


def build_memory_engine(*, backend: str, config: MemoryConfig | dict, runtime):
    resolved = config if isinstance(config, MemoryConfig) else MemoryConfig.from_mapping(config)
    if backend == "hybrid_semantic":
        return HybridSemanticMemoryEngine(config=resolved, runtime=runtime)
    if backend == "simple_recent":
        return SimpleRecentMemoryEngine(config=resolved, runtime=runtime)
    raise UnsupportedBackendError(f"Unsupported memory backend: {backend}")
