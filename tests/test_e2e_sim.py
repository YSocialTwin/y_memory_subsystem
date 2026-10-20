import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_english_and_italian_runs_pass_the_end_to_end_criteria(capsys):
    module = runpy.run_path(str(ROOT / "scripts" / "e2e_memory_sim.py"))
    assert module["main"](["--check-golden"]) == 0, capsys.readouterr().out
