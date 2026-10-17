"""Testes do task runner (scripts/tasks.py)."""

import importlib.util
import sys
from pathlib import Path

_TASKS = Path(__file__).resolve().parents[1] / "scripts" / "tasks.py"


def _load_tasks():
    spec = importlib.util.spec_from_file_location("sopro_tasks", _TASKS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_command_test_uses_pytest_quiet():
    tasks = _load_tasks()
    assert tasks.build_command("test", [])[:3] == [sys.executable, "-m", "pytest"]


def test_build_command_demo_forces_demo_flag():
    tasks = _load_tasks()
    command = tasks.build_command("demo", [])
    assert command[-2:] == ["sopro", "--demo"]


def test_build_command_forwards_extra_args():
    tasks = _load_tasks()
    command = tasks.build_command("bench", ["aula.wav", "notas.csv"])
    assert command[-2:] == ["aula.wav", "notas.csv"]


def test_build_command_build_calls_powershell_script():
    tasks = _load_tasks()
    command = tasks.build_command("build", ["-Version", "1.2.3"])
    assert command[0] == "powershell.exe"
    assert "build-windows.ps1" in " ".join(command)
    assert command[-2:] == ["-Version", "1.2.3"]


def test_build_command_rejects_unknown_task():
    tasks = _load_tasks()
    try:
        tasks.build_command("nope", [])
    except SystemExit as exc:
        assert "nope" in str(exc)
    else:
        raise AssertionError("tarefa desconhecida deveria falhar")
