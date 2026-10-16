"""Validação de um pacote de domínio contra o checklist de docs/07 §6.

Uso::

    sopro-validate-glossary data/domains/tech-en-pt
    sopro-validate-glossary data/domains/tech-en-pt --json --strict

O código de saída é ``0`` quando não há erros, ``1`` quando há erros (ou avisos,
com ``--strict``) e ``2`` quando o pacote não pôde ser lido.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from sopro.core.glossary.package import (
    VALID_POS,
    DomainPackage,
    PackageError,
    Sense,
    Term,
    load_package,
)

MAX_DEFINITION_WORDS = 25
MIN_REVIEWED_TERMS = 20
DEFAULT_PACKAGE_PATH = "data/domains/tech-en-pt"
LICENSE_PLACEHOLDERS = {"", "definir", "a definir", "to define", "tbd", "n/a"}

ERROR = "error"
WARNING = "warning"


@dataclass(frozen=True)
class Issue:
    """Um achado da validação."""

    level: str
    code: str
    message: str
    term: str | None = None

    def format(self) -> str:
        prefix = "ERRO " if self.level == ERROR else "AVISO"
        location = f" [{self.term}]" if self.term else ""
        return f"{prefix}{location} {self.message}"


@dataclass(frozen=True)
class Report:
    """Resultado da validação de um pacote."""

    issues: tuple[Issue, ...]
    stats: dict

    @property
    def errors(self) -> tuple[Issue, ...]:
        return tuple(i for i in self.issues if i.level == ERROR)

    @property
    def warnings(self) -> tuple[Issue, ...]:
        return tuple(i for i in self.issues if i.level == WARNING)

    @property
    def ok(self) -> bool:
        return not self.errors

    def format(self) -> str:
        lines: list[str] = []
        s = self.stats
        lines.append(
            f"Pacote: {s.get('slug', '?')} v{s.get('version', '?')} "
            f"({s.get('term_count', 0)} termos, {s.get('sense_count', 0)} acepções)"
        )
        lines.append(
            f"Revisados: {s.get('reviewed', 0)} | a revisar: "
            f"{s.get('needs_review', 0)} | ambíguos: {s.get('ambiguous', 0)} | "
            f"stoplisted: {s.get('stoplisted', 0)}"
        )
        if s.get("priority_histogram"):
            hist = ", ".join(f"p{k}={v}" for k, v in sorted(s["priority_histogram"].items()))
            lines.append(f"Prioridades: {hist}")
        lines.append("")
        if not self.issues:
            lines.append("OK: nenhum problema encontrado.")
        for issue in self.issues:
            lines.append(issue.format())
        lines.append("")
        lines.append(f"Total: {len(self.errors)} erro(s), {len(self.warnings)} aviso(s).")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "stats": self.stats,
            "errors": [
                {"code": i.code, "message": i.message, "term": i.term}
                for i in self.errors
            ],
            "warnings": [
                {"code": i.code, "message": i.message, "term": i.term}
                for i in self.warnings
            ],
        }


def _word_count(text: str) -> int:
    return len(text.split())


def _check_manifest(package: DomainPackage, issues: list[Issue], stats: dict) -> None:
    m = package.manifest
    if not m.slug:
        issues.append(Issue(ERROR, "E_MANIFEST_SLUG", "manifesto sem 'slug'."))
    if not m.name:
        issues.append(Issue(ERROR, "E_MANIFEST_NAME", "manifesto sem 'name'."))
    if not m.version:
        issues.append(Issue(ERROR, "E_MANIFEST_VERSION", "manifesto sem 'version'."))
    if not m.source_lang:
        issues.append(Issue(ERROR, "E_MANIFEST_SOURCE_LANG", "manifesto sem 'source_lang'."))
    if not m.output_langs:
        issues.append(Issue(ERROR, "E_MANIFEST_OUTPUT_LANGS", "manifesto sem 'output_langs'."))
    if not m.authors:
        issues.append(Issue(ERROR, "E_MANIFEST_AUTHORS", "manifesto sem 'authors'."))
    if not m.license:
        issues.append(Issue(ERROR, "E_MANIFEST_LICENSE", "manifesto sem 'license'."))
    elif m.license.strip().lower() in LICENSE_PLACEHOLDERS:
        issues.append(
            Issue(
                WARNING,
                "W_LICENSE_PLACEHOLDER",
                f"licença do pacote ainda não definida ('{m.license}').",
            )
        )
    stats["slug"] = m.slug
    stats["version"] = m.version
    stats["domain_tag"] = m.domain_tag


def _check_term(term: Term, package: DomainPackage, issues: list[Issue], stats: dict) -> None:
    name = term.canonical_en

    if term.pos not in VALID_POS:
        issues.append(
            Issue(ERROR, "E_INVALID_POS", f"'pos' inválido: '{term.pos}'.", name)
        )
    if not 1 <= term.priority <= 5:
        issues.append(
            Issue(ERROR, "E_PRIORITY_RANGE", f"'priority' fora de 1..5: {term.priority}.", name)
        )
    if not term.senses:
        issues.append(Issue(ERROR, "E_NO_SENSES", "termo sem acepções.", name))

    ordinals = [s.ordinal for s in term.senses]
    if len(ordinals) != len(set(ordinals)):
        issues.append(Issue(ERROR, "E_DUPLICATE_ORDINAL", "acepções com 'ordinal' repetido.", name))

    if term.is_ambiguous and not term.domain_senses(package.domain_tag):
        issues.append(
            Issue(
                ERROR,
                "E_AMBIGUOUS_WITHOUT_DOMAIN_SENSE",
                f"termo ambíguo sem acepção com domain_tag='{package.domain_tag}'.",
                name,
            )
        )

    if (term.stoplisted or term.is_ambiguous) and not term.context_hints:
        issues.append(
            Issue(
                WARNING,
                "W_NO_CONTEXT_HINTS",
                "termo stoplisted/ambíguo sem 'context_hints'.",
                name,
            )
        )

    if term.source == "gerado" and term.needs_review is False:
        issues.append(
            Issue(
                ERROR,
                "E_GENERATED_NOT_REVIEWED",
                "entrada 'gerado' não pode ser promovida sem revisão (needs_review=false).",
                name,
            )
        )

    for alias in term.aliases:
        if alias.lower() in package.stoplist and not term.stoplisted:
            issues.append(
                Issue(
                    WARNING,
                    "W_ALIAS_STOPLIST",
                    f"alias '{alias}' colide com a stoplist sem stoplisted=true.",
                    name,
                )
            )

    for sense in term.senses:
        _check_sense(sense, issues)


def _check_sense(sense: Sense, issues: list[Issue]) -> None:
    if not sense.definition_pt.strip():
        issues.append(
            Issue(ERROR, "E_EMPTY_DEFINITION", f"acepção {sense.ordinal} sem definição.")
        )
    elif _word_count(sense.definition_pt) > MAX_DEFINITION_WORDS:
        issues.append(
            Issue(
                ERROR,
                "E_DEFINITION_TOO_LONG",
                f"acepção {sense.ordinal} excede {MAX_DEFINITION_WORDS} palavras "
                f"({_word_count(sense.definition_pt)}).",
            )
        )
    if not sense.translation_pt.strip():
        issues.append(
            Issue(ERROR, "E_EMPTY_TRANSLATION", f"acepção {sense.ordinal} sem tradução.")
        )


def validate_package(package: DomainPackage) -> Report:
    """Aplica o checklist de docs/07 §6 e as regras de qualidade de §5."""
    issues: list[Issue] = []
    stats: dict = {}

    _check_manifest(package, issues, stats)

    seen: dict[str, str] = {}
    priority_histogram: dict[int, int] = {}
    sense_count = 0
    for term in package.terms:
        key = term.canonical_en.strip().lower()
        if key in seen:
            issues.append(
                Issue(
                    ERROR,
                    "E_DUPLICATE_TERM",
                    f"'canonical_en' duplicado (também em '{seen[key]}').",
                    term.canonical_en,
                )
            )
        else:
            seen[key] = term.canonical_en

        priority_histogram[term.priority] = priority_histogram.get(term.priority, 0) + 1
        sense_count += len(term.senses)
        _check_term(term, package, issues, stats)

    reviewed = sum(1 for t in package.terms if not t.needs_review)
    stats.update(
        {
            "term_count": len(package.terms),
            "sense_count": sense_count,
            "reviewed": reviewed,
            "needs_review": len(package.terms) - reviewed,
            "ambiguous": sum(1 for t in package.terms if t.is_ambiguous),
            "stoplisted": sum(1 for t in package.terms if t.stoplisted),
            "priority_histogram": priority_histogram,
            "stoplist_size": len(package.stoplist),
        }
    )

    if reviewed < MIN_REVIEWED_TERMS:
        issues.append(
            Issue(
                WARNING,
                "W_REVIEW_PENDING",
                f"apenas {reviewed} termo(s) revisado(s); o checklist pede >= "
                f"{MIN_REVIEWED_TERMS}.",
            )
        )

    return Report(issues=tuple(issues), stats=stats)


def _resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.exists():
        return candidate
    return Path.cwd() / candidate


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        prog="sopro-validate-glossary",
        description="Valida um pacote de domínio (checklist de docs/07 §6).",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=DEFAULT_PACKAGE_PATH,
        help=f"diretório do pacote (padrão: {DEFAULT_PACKAGE_PATH}).",
    )
    parser.add_argument("--json", action="store_true", help="emite o relatório em JSON.")
    parser.add_argument(
        "--strict", action="store_true", help="trata avisos como falha."
    )
    args = parser.parse_args(argv)

    try:
        package = load_package(_resolve_path(args.path))
    except PackageError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2

    report = validate_package(package)

    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(report.format())

    failed = bool(report.errors) or (args.strict and bool(report.warnings))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
