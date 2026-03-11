# Hybrid Semantic Backend

`hybrid_semantic` is the packaged form of the richer `YClientReddit` memory behavior.

## What it stores

- Event items
- Reflection items
- Social cards per counterparty
- Thread cards per thread root
- Community digest
- Root-post snapshots for style heuristics

## Read-path behavior

### Reply context

The backend builds reply context from:

1. Social-card metrics
2. Social-card summary text
3. Thread-card gist
4. Recent same-thread interaction evidence
5. Cross-thread callback candidates

It suppresses vote artifacts in prompt-visible context when `memory_vote_signal_only` is enabled.

### Browse context

Browse context is thread-local only. It intentionally excludes community digest text to avoid topic leakage.

### Post-style context

Post-style guidance is enabled only after the digest is mature enough. It uses style fields such as `norms` and `memes`, not topic text.

## Write-path behavior

### Comment

- records a memory event
- updates the social card
- updates the thread card
- may refresh community digest
- may generate reflections

### Vote

- always updates social-card relationship deltas
- records no prompt-visible event when `memory_vote_signal_only=true`

### Post

- stores root post material used later for digest maturity and topic freshness checks

## High-affect flow

When enabled, the backend can:

- detect high-affect interactions
- search for recalled memories across interaction/opinion/anecdote/relationship buckets
- validate whether a generated reply references a recalled memory

## Current equivalence target

The implemented behavior is characterized against the upstream `YClientReddit` fixtures covering:

- subtle reply context
- vote-signal-only suppression
- thread browse context
- post-style context
- high-affect fallback behavior
