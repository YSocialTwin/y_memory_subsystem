# Backend Matrix

| Capability | `hybrid_semantic` | `simple_recent` |
| --- | --- | --- |
| Shared engine signature | Yes | Yes |
| Reply context | Yes | Yes |
| Browse context | Yes | Yes |
| Post-style context | Yes | Empty/default |
| Relationship signal | Yes | Yes |
| Semantic-style retrieval | Yes | No |
| Thread cards | Yes | Recent thread history only |
| Community digest | Yes | No |
| Reflections | Yes | No |
| High-affect recall | Yes | No |
| Vote-signal-only suppression | Yes | Yes |

## Selection guidance

- Choose `hybrid_semantic` when the client can support richer retrieval and memory maintenance.
- Choose `simple_recent` when adoption risk, dependencies, or runtime cost need to stay low.
- Both backends share the same contracts, so switching is a config choice rather than a call-site rewrite.
