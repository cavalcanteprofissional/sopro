"""Conjunto de casos ambíguos e medição de acurácia do resolvedor (docs/05 A7).

Fornece um mini-glossário sintético com termo ambíguos típicos (``fairness``,
``bias``, ``model``, ``token``, ``kernel``, ``pipeline``), frases de teste com a
acepção esperada e :func:`evaluate`, que roda o :class:`SenseResolver` e devolve a
acurácia. O objetivo é medir a cascata sem depender de LLM nem de rede.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from sopro.core.glossary.package import Sense, Term
from sopro.core.rag.resolver import SenseResolver


@dataclass(frozen=True)
class Case:
    """Um caso de desambiguação: termo, frase e ordinal esperado."""

    term: str
    context: str
    expected_ordinal: int


@dataclass(frozen=True)
class Miss:
    """Um caso em que o resolvedor errou a acepção."""

    term: str
    context: str
    expected_ordinal: int
    got_ordinal: int | None
    method: str


@dataclass(frozen=True)
class EvalResult:
    """Resultado agregado da avaliação."""

    total: int
    correct: int
    misses: tuple[Miss, ...] = field(default_factory=tuple)

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0


def _senses(*rows: tuple[int, str, str, str, str]) -> tuple[Sense, ...]:
    return tuple(
        Sense(
            ordinal=ordinal,
            domain_tag=tag,
            translation_pt=translation,
            definition_pt=definition,
            example_en=example,
        )
        for ordinal, tag, translation, definition, example in rows
    )


def ambiguous_glossary() -> tuple[Term, ...]:
    """Mini-glossário sintético com termos ambíguos e acepções discrimináveis."""
    return (
        Term(
            canonical_en="fairness",
            pos="noun",
            is_ambiguous=True,
            senses=_senses(
                (
                    1,
                    "tech",
                    "equidade (de modelo)",
                    "Equitable treatment of groups by a machine learning model.",
                    "We measured fairness of the model across demographic groups.",
                ),
                (
                    2,
                    "general",
                    "justiça, imparcialidade",
                    "The quality of being just and impartial in judgment.",
                    "The judge was praised for her fairness and impartial judgment.",
                ),
            ),
        ),
        Term(
            canonical_en="bias",
            pos="noun",
            is_ambiguous=True,
            senses=_senses(
                (
                    1,
                    "tech",
                    "viés (sistemático)",
                    "A systematic distortion in data or a model that skews predictions.",
                    "The dataset introduced a selection bias that skewed predictions.",
                ),
                (
                    2,
                    "general",
                    "preconceito, preferência",
                    "An unfair preference for or against a person or group.",
                    "The report revealed a personal preference and unfair bias against the proposal.",
                ),
            ),
        ),
        Term(
            canonical_en="model",
            pos="noun",
            is_ambiguous=True,
            senses=_senses(
                (
                    1,
                    "tech",
                    "modelo (de aprendizado)",
                    "A trained representation that maps inputs to outputs for predictions.",
                    "The model predicts the price from the input features.",
                ),
                (
                    2,
                    "general",
                    "modelo, padrão",
                    "An example or reference to be followed or imitated.",
                    "She was a role model of good behavior for the students.",
                ),
            ),
        ),
        Term(
            canonical_en="token",
            pos="noun",
            is_ambiguous=True,
            senses=_senses(
                (
                    1,
                    "tech",
                    "token (unidade de texto)",
                    "A piece of text that a language model processes as a unit.",
                    "The prompt is about two hundred tokens long for the language model.",
                ),
                (
                    2,
                    "general",
                    "credencial de acesso",
                    "A code used for authentication in digital systems.",
                    "Enter the access token to authenticate your session.",
                ),
                (
                    3,
                    "general",
                    "ficha",
                    "A piece used as a value or control in games and machines.",
                    "Insert a token into the slot to start the arcade machine.",
                ),
            ),
        ),
        Term(
            canonical_en="kernel",
            pos="noun",
            is_ambiguous=True,
            senses=_senses(
                (
                    1,
                    "tech",
                    "kernel (núcleo do SO)",
                    "The core of an operating system that manages hardware and processes.",
                    "The operating system kernel manages memory and process scheduling.",
                ),
                (
                    2,
                    "general",
                    "caroço, núcleo",
                    "The edible seed inside a nut or fruit.",
                    "She cracked the shell to eat the kernel of the walnut.",
                ),
            ),
        ),
        Term(
            canonical_en="pipeline",
            pos="noun",
            is_ambiguous=True,
            senses=_senses(
                (
                    1,
                    "tech",
                    "pipeline (fluxo de dados)",
                    "A sequence of processing stages that transform data.",
                    "The data pipeline cleans and loads the records in stages.",
                ),
                (
                    2,
                    "general",
                    "duto, encanamento",
                    "A tube that transports fluids.",
                    "The oil pipeline transports crude fluid across the country.",
                ),
            ),
        ),
    )


def ambiguous_cases() -> tuple[Case, ...]:
    """Frases de teste com a acepção esperada (ordinal)."""
    return (
        Case("fairness", "we measured fairness of the model across demographic groups", 1),
        Case("fairness", "the judge was praised for her fairness and impartial judgment", 2),
        Case("bias", "the dataset introduced a selection bias that skewed predictions", 1),
        Case(
            "bias",
            "the report showed a personal preference and unfair bias against the proposal",
            2,
        ),
        Case("model", "the model predicts the price from the input features", 1),
        Case("model", "she was a role model of good behavior for the students", 2),
        Case("token", "the prompt is about two hundred tokens long for the language model", 1),
        Case("token", "enter the access token to authenticate your session", 2),
        Case("token", "insert a token into the slot to start the arcade machine", 3),
        Case("kernel", "the operating system kernel manages memory and process scheduling", 1),
        Case("kernel", "she cracked the shell to eat the kernel of the walnut", 2),
        Case("pipeline", "the data pipeline cleans and loads the records in stages", 1),
        Case("pipeline", "the oil pipeline transports crude fluid across the country", 2),
    )


def evaluate(
    resolver: SenseResolver,
    glossary: Sequence[Term] | None = None,
    cases: Sequence[Case] | None = None,
) -> EvalResult:
    """Roda o resolvedor nos casos e devolve a acurácia."""
    terms = {t.canonical_en: t for t in (glossary or ambiguous_glossary())}
    cases = cases or ambiguous_cases()
    correct = 0
    misses: list[Miss] = []
    for case in cases:
        resolution = resolver.resolve(terms[case.term], case.context)
        got = resolution.sense.ordinal if resolution else None
        if got == case.expected_ordinal:
            correct += 1
        else:
            misses.append(
                Miss(
                    term=case.term,
                    context=case.context,
                    expected_ordinal=case.expected_ordinal,
                    got_ordinal=got,
                    method=resolution.method if resolution else "",
                )
            )
    return EvalResult(total=len(cases), correct=correct, misses=tuple(misses))
