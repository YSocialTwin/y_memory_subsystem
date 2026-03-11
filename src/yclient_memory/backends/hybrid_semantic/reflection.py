def reflection_should_run(*, round_id: int, last_round_id: int | None, cadence: int) -> bool:
    if cadence <= 0:
        return False
    if last_round_id is None:
        return True
    return int(round_id) - int(last_round_id) >= int(cadence)
