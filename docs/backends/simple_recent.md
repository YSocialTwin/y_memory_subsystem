# Simple Recent Backend

`simple_recent` keeps the same external API with a much smaller state model.

## What it stores

- Recent per-user interaction history
- Recent per-thread history
- Lightweight relationship aggregates

## Intended use

Use `simple_recent` when:

- a client needs lower integration risk
- semantic retrieval is not available yet
- community digests and reflections are out of scope

## Behavior

### Reply context

- recent relationship metrics
- recent same-thread interaction snippet
- optional cross-thread callback hint when recent history exists

### Browse context

- latest recent thread snippets only

### Post-style context

- empty/default output

### Maintenance

- relationship counters decay over time

## Tradeoff

The backend is simpler to adopt, but it is intentionally not feature-equivalent with the richer Reddit memory system.
