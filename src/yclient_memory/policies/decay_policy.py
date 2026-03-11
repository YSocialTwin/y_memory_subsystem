from __future__ import annotations


def apply_decay(value: float, *, rounds_elapsed: int, per_round: float = 0.03) -> float:
    rounds_elapsed = max(0, int(rounds_elapsed))
    factor = max(0.0, 1.0 - (per_round * rounds_elapsed))
    return round(float(value) * factor, 4)
