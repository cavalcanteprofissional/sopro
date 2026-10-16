# Changelog

Todas as mudanças relevantes deste projeto serão documentadas neste arquivo.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o projeto
adota [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Unreleased]

### Added
- Estrutura inicial do repositório de código em Python (núcleo portável em `src/sopro/core`,
  camadas de plataforma em `src/sopro/platform` e orquestração em `src/sopro/app`).
- Contrato `STTProvider` (`core/stt/provider.py`), adapter `LocalWhisperProvider` com engine
  injetável e catálogo de modelos com verificação de integridade sha256 e cache local
  (`core/stt/registry.py`).
- Contrato de VAD/segmentação (`core/vad`): `VadConfig` e `SpeechSegment`.
- Segmentador de fala por energia (`core/vad/energy.py`): RMS por quadro, fusão por
  silêncio mínimo, descarte por fala mínima, folga nas bordas e divisão de trechos longos
  com sobreposição; sem dependências externas.
- Catálogo inicial `data/models.json` (placeholders a verificar).
- Pacote de domínio seed `tech-en-pt` v0.1.0 (Tecnologia e IA, EN→PT): manifesto, primeiro
  lote de termos, stoplist e README do pacote.
- Validador de pacote de domínio com o checklist de `docs/07` §6 e console script
  `sopro-validate-glossary`.
- Núcleo de texto (`core/text`): normalização (minúsculas, hífens/espaços, remoção de
  pontuação) e tokenização com deslocamentos.
- `matcher` (`core/matcher`): casamento por n-gramas de 1–4 tokens com maior primeiro,
  aliases, flexão de plural por regra, regra de contexto para a stoplist e política de
  exibição (cooldown por termo e orçamento por minuto).
- Modo benchmark (métricas) em `app/benchmark.py`: leitor do conjunto anotado (CSV),
  recall/precisão/F1 no agregado e por termo, e resumo de latências (p50/p95).
- Leitor de WAV para PCM 16-bit mono 16 kHz (`app/wav.py`, só biblioteca padrão) e
  orquestração offline do benchmark (`app/benchmark_cli.py`) com motor de STT injetável
  (`--provider modulo:fabrica`); console script `sopro-benchmark`.
- Testes automatizados (pytest) para o validador, o pacote seed, o núcleo de texto, o
  matcher, o segmentador de fala e as métricas de benchmark.
- Template do conjunto de teste anotado (`fixtures/testset-template.csv`).
- Especificação de distribuição e offline (`docs/08-distribuicao-e-offline.md`).
- Documentação padrão de projeto: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`,
  `CHANGELOG.md`, `TODO.md`, `LICENSE` e `.editorconfig`.

### Changed
- Decisões registradas em `docs/02 §13`, `docs/01` (RNF-08) e README: modelos **on-demand**
  com verificação de integridade, **motor de STT por benchmark** e **Windows** como alvo do
  protótipo.
- Documentação de produto/engenharia (01–07) movida para [`docs/`](docs/); README
  reorganizado como porta de entrada do projeto (único README do repositório).

## [0.0.0] - 2026-10-07

### Added
- Documentação inicial: visão e requisitos (`01`), arquitetura e especificações (`02`),
  estado da arte (`03`), roadmap (`04`), prompts (`05`), referências (`06`) e formato do
  glossário seed (`07`).

[Unreleased]: https://example.com/sopro/compare/v0.0.0...HEAD
[0.0.0]: https://example.com/sopro/releases/tag/v0.0.0
