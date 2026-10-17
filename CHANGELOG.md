# Changelog

Todas as mudanças relevantes deste projeto serão documentadas neste arquivo.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o projeto
adota [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Unreleased]

### Added
- Estrutura inicial do repositório de código em Python (núcleo portável em `src/sopro/core`,
  camadas de plataforma em `src/sopro/platform` e orquestração em `src/sopro/app`).
- Contratos de captura de áudio independentes de SO (`core/audio`): `AudioSource`,
  `AudioFrame`, `DeviceInfo`, `CaptureConfig` e utilidades de PCM (downmix, reamostragem,
  RMS/pico).
- Captura no Windows via WASAPI com PyAudioWPatch (`platform/audio`): loopback do sistema e
  microfone simultâneos, convertidos a PCM 16-bit mono 16 kHz por *callback*, etiquetados
  por fonte. Dependência opcional no extra `audio`.
- Sonda `sopro-capture-probe` (docs/05 A2): mede o nível RMS/pico por fonte mantendo o áudio
  apenas em memória, sem gravar em disco.
- Persistência local em SQLite (`core/repo`): esquema de docs/02 §6 com migrações versionadas,
  índice FTS5 de termos/aliases, repositório de domínios/termos/sessões/detecções/configurações
  e exportação do histórico em CSV e Markdown (contexto oculto por padrão).
- Configurações validadas (`core/config.settings`) persistidas na tabela `setting`, com
  carga/gravação via `Repository`; cofre de segredos (`core/config.secrets`) com backend do SO
  opcional via `keyring` e alternativa em memória.
- Importação/exportação de pacotes de domínio (`core/repo.importer`): carrega um pacote de
  docs/07 para o SQLite, exporta um domínio de volta para JSON e reconstrói um
  `DomainPackage` a partir do banco (para o matcher rodar offline), incluindo a stoplist
  por domínio (migração v2).
- Fila de cartões de pop-up (`platform/popup.queue`): limite de cartões simultâneos (novos
  substituem o mais antigo), fechamento/expiração e tempo injetável para testes (RF-20,
  docs/02 §8). A política de exibição (cooldown/orçamento) permanece no `Matcher`.
- Serviço de detecção (`app/detection`): liga transcrição → `Matcher` → persistência no
  `Repository` (sessão/detecção, contexto opcional por privacidade) → fila de pop-ups,
  com `STTProvider` e relógio injetáveis.
- Dica de vocabulário compartilhada (`core/stt/vocabulary`) entre o benchmark e o serviço
  de detecção.
- Segmentação incremental (`core/vad.streaming`): `StreamingSegmenter` consome PCM em
  fluxo e emite trechos de fala (finaliza por silêncio, descarta fala curta, divide
  trechos longos com sobreposição), reaproveitando o `VadConfig`.
- Pipeline em tempo real (`app/realtime`): `RealtimePipeline` mantém um segmentador por
  fonte (sistema/microfone), alimenta o `DetectionService` e expõe `run` sobre uma
  `AudioSource`, com drenagem dos trechos em andamento.
- Overlay de pop-up em PySide6 (`platform/popup`): cartão sem borda, sempre no topo e sem
  roubar foco, empilhado a partir do canto configurado, com tema claro/escuro, pausa no
  hover, fechamento por clique e ação "fixar" (docs/02 §8). Dependência opcional no extra
  `ui`.
- Bandeja/systray em PySide6 (`platform/popup.tray`): ícone com estado (escutando, pausado,
  erro), menu de alternar/execução/configurações/sair e sinais acopláveis.
- Tela de configurações (`platform/popup.settings_window`): diálogo com fontes de áudio,
  domínios ativos, idioma, provedores/modelo STT, pop-up, tema e atalho, devolvendo um
  `Settings` validado.
- Ponto de entrada do aplicativo (`app/run`, `python -m sopro` / script `sopro`): abre o
  banco local, carrega as configurações e o pacote de domínio ativo, e liga captura +
  pipeline em tempo real + overlay + bandeja; `--demo` roda o pipeline com áudio/transcrição
  falsos (docs/05 A3) e `--home`/`SOPRO_HOME` isolam a pasta de dados (docs/08 §5).
- Resolução da pasta de dados (`app/home`) e pacote de demonstração (`app/demo`): provedor
  e fonte de áudio sintética que acionam o VAD e casam com o glossário.
- Empacotamento em executável standalone (`sopro.spec`, docs/09): PyInstaller *onedir* com
  dados (catálogo + domínios) e dependências nativas embutidas, excluindo os modelos; script
  `scripts/build-windows.ps1` (build + zip portátil + `SHA256SUMS.txt`), `installer.iss`
  (Inno Setup per-user) e workflow de release em `.github/workflows/release.yml` (tag `v*`).
  Novo extra `packaging`.
- Resolução de recursos no modo dev e no modo congelado (`core/paths`): `is_frozen`,
  `resource_root`, `data_path`; o catálogo de modelos e os pacotes de domínio passam a ser
  localizados por ela. No executável do Windows a pasta de dados vira `%LOCALAPPDATA%\Sopro`
  (docs/09 §5).
- Contrato `STTProvider` (`core/stt/provider.py`), adapter `LocalWhisperProvider` com engine
  injetável e catálogo de modelos com verificação de integridade sha256 e cache local
  (`core/stt/registry.py`).
- Contrato de VAD/segmentação (`core/vad`): `VadConfig` e `SpeechSegment`.
- Segmentador de fala por energia (`core/vad/energy.py`): RMS por quadro, fusão por
  silêncio mínimo, descarte por fala mínima, folga nas bordas e divisão de trechos longos
  com sobreposição; sem dependências externas.
- Catálogo inicial `data/models.json` (placeholders a verificar).
- Download sob demanda com verificação de integridade (`core/stt/download.py`): busca em
  streaming para `.tmp`, confere sha256 (e tamanho) e promove ao cache; reutiliza o local
  via `ensure_model`.
- Binding `faster-whisper` na camada de plataforma (`platform/stt`), carregando o modelo
  sob demanda, e fábrica de provider que resolve o modelo no catálogo com download
  verificado. Dependência opcional no extra `stt`.
- Catálogo com o primeiro modelo STT verificado (`whisper-tiny-en`, CTranslate2, MIT) com
  url, sha256 e tamanho; download e verificação validados ponta a ponta.
- Dica de vocabulário por segmento (`AudioSegment.vocabulary_hint`) usada na decodificação,
  com termo de maior prioridade do domínio; decodificação gulosa (`temperature=0`) para
  reprodutibilidade do benchmark.
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
- Especificação de empacotamento, release e compatibilidade de Windows
  (`docs/09-empacotamento-e-release.md`): PyInstaller *onedir*, Inno Setup, CI de release,
  assinatura de código e seção de download do README.
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
