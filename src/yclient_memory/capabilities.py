from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryCapabilities:
    semantic_search: bool = False
    relationship_memory: bool = False
    thread_memory: bool = False
    community_digest: bool = False
    reflections: bool = False
    high_affect_recall: bool = False
    prompt_cues: bool = True
    post_style_context: bool = False
