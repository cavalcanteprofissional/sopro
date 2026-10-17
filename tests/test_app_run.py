"""Testes do ponto de entrada (sopro.app.run): parser e sem Qt."""

from sopro.app.run import build_parser, main


def test_parser_defaults():
    args = build_parser().parse_args([])
    assert args.demo is False
    assert args.home is None
    assert args.domains_root is None


def test_parser_flags():
    args = build_parser().parse_args(["--demo", "--home", "C:/tmp/h"])
    assert args.demo is True
    assert args.home == "C:/tmp/h"


def test_main_reports_missing_ui_extra(monkeypatch, tmp_path):
    def boom(*_args, **_kwargs):
        raise ImportError("PySide6")

    monkeypatch.setattr("sopro.app.run._run", boom)
    code = main(["--demo", "--home", str(tmp_path)])
    assert code == 2
