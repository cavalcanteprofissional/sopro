# Changelog

Todas as mudanças relevantes deste projeto serão documentadas neste arquivo.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o projeto
adota [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Unreleased]

### Added
- **Trilhas de glossário (A7.4)**: UI em árvore domínio → trilhas nos "Glossários", seletor de trilhas em Configurações e na primeira execução. Marcar uma trilha ativa o pai `tech` automaticamente; desmarcar o pai desmarca as filhas. Adicionado `docs/trilhas/README.md`. As regras de agregação já existentes (`active_tracks`) agora ficam expostas na UI.
- **Sobre Nós (A6.5)**: nova aba no Hub com informações do projeto, desenvolvedor (Lucas Cavalcante dos Santos), links para repositório/perfil GitHub e privacidade/licença.
- Detecção tolerante a fala real: siglas soletradas (`A P I`, `A.I.`, `ai pi ai`) e aliases
  fonéticos, flexões `-ing/-ed/-er` (exceto siglas) e **fuzzy opt-in** com limiar alto e
  comprimento mínimo. O glossário base ganhou `AI` (distinto de `API`) e aliases falados em
  `API`, `IDE`, `SDK`, `RAG`, `HTTP` e `SQL`.

### Changed
- **Pop-up**: som padrão alterado para **bolha de sabão suave** (síntese em memória).
- **Ativação/desativação**: sons de ligar/desligar mais simples e suaves (sweep curto).
- **Indicador flutuante**: já suporta clique para ativar/desativar e arrastar com threshold (B4). Mantido e validado.
- **Empacotamento (v0.1.0)**: portátil (`Sopro-0.1.0-portable.zip`) e instalador (`Sopro-Setup-0.1.0.exe`) refeitos com o código atual; `SHA256SUMS.txt` atualizado com ambos os artefatos.
- Confiança de transcrição no faster-whisper (`avg_logprob` + `no_speech_prob`); o serviço de
  detecção descarta transcrições abaixo de `0.25` antes de consultar o matcher.
- Indicador circular: **clique único** pausa/retoma e **arraste** (acima de 5 px) move e
  persiste a posição sem alternar; tooltip e cursor refletem o estado.
- Planejamento da **Fase 7 — conta, dados em nuvem e backup**: Clerk (GitHub ativo, demais
  provedores desabilitados), Neon Postgres, Cloudflare R2, Worker e GitHub Actions para
  backup diário de 30 dias. Inclui isolamento por `user_id`, sync/outbox offline, migração
  idempotente do SQLite e áudio sempre local. Detalhes em `TODO.md`.
- Mapa de fluxos em `docs/roadmap/`: 14 documentos com diagramas Mermaid para usuário,
  sistema, glossários/trilhas, dados, modelos, build e qualidade, complementando o roadmap
  cronológico de `docs/04-roadmap.md`.
- Seção de arquitetura no README com fluxo geral e fluxo de glossário/trilhas; guia detalhado
  de criação de glossários no `CONTRIBUTING.md`, incluindo a futura curadoria assistida por
  IA (Fase 6).
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
- Atalhos globais de teclado (`core/hotkeys` + `platform/hotkey`): parser e contrato de
  combinação (`Ctrl+Shift+Space`) e registro no Windows via `RegisterHotKey` com thread de
  mensagens, injetável para testes; acionam pausar/continuar e são editáveis nas
  configurações (campo validado, degradação graciosa quando indisponível).
- Task runner `scripts/tasks.py` (sem exigir `make`/`just`/`uv`) com alvos `dev`, `demo`,
  `test`, `bench`, `validate`, `build` e `install`; documentação do fluxo local em
  `docs/10-dev-workflow.md`, com apoio em `CONTRIBUTING.md` e no README (inclui o
  suporte opcional a `uv` e a distinção entre dev do fonte e portátil).
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
- RAG e desambiguação de acepções (`core/rag`): embeddings locais offline por padrão
  (`HashingEmbedder`, com `SentenceTransformerEmbedder` opcional no extra `rag`), índice
  vetorial persistido em `sense_vec` (migração v3), `SenseResolver` em cascata
  (acepção única → `domain_tag` → vetor → LLM) com limiar configurável, janela de contexto
  e conjunto de casos ambíguos com medição de acurácia; integrado ao `DetectionService` e
  ao histórico (`detection.method`).
- Camada de LLM (`core/llm`): `LLMProvider`, prompt B1 em JSON validado, `LLMSenseChooser`
  como passo `llm` da cascata e geração de termos fora do glossário com cache e fila de
  aprovação (`generated_entry`, migração v4 com `translation`/`confidence`); provedores
  local (OpenAI-compatível) e Groq (`platform/llm`) com backoff em limite.
- Detecção de termos fora do glossário no pipeline (`core/llm/candidates`): extração por
  maior casamento com stoplist de palavras comuns, `RateLimiter` com limite de taxa próprio,
  e enfileiramento de detecções geradas (`resolve_method="llm"`) no `DetectionService`.
- Provedor Groq de STT (`platform/stt/groq_stt`) com agrupamento de segmentos (≥ ~10 s),
  backoff em limite, *timeout* e fallback automático ao provedor local; fábrica de STT por
  preferência (`platform/stt/factory`).
- Aviso de privacidade e confirmação explícita antes de ativar provedores em nuvem, com
  consentimento persistido (`remote_consent`) e indicador permanente de "Nuvem ativa" na
  bandeja (`config.cloud_providers`, `tray.set_remote`).
- Assistente de primeira execução (`platform/popup.first_run`): consentimento LGPD, escolha
  de domínio, idioma de saída e fontes de áudio, gravando `first_run_done` (ignorado em
  `--demo`).
- Logging em arquivo com rotação e sem conteúdo de fala (`app/logging_setup`): filtro que
  descarta registros marcados como fala, em `logs/sopro.log` na pasta de dados.
- Erros amigáveis (`platform/popup.errors`): `friendly_message` (dicas por tipo de exceção)
  e diálogo `show_error`, usados na inicialização e em falhas de pipeline.
- Tela de gerenciamento de glossários (`platform/popup.glossary_window`): lista domínios,
  importa/exporta pacotes e ativa/desativa domínios, com ação "Glossários…" na bandeja e
  `Repository.set_domain_active` (RF-23).
- Listagem de pacotes de domínio disponíveis (`core/glossary.package.list_package_slugs`).
- Hub/janela principal (`platform/popup.hub`): `HubWindow` com navegação lateral entre
  páginas (Status, Configurações, Glossários, Termos, Histórico, Demonstração) e botão
  "Aplicar" por página; a bandeja e o menu "Abrir Sopro…" abrem o hub em cada seção.
- Páginas reutilizáveis (`platform/popup.pages`): `StatusPage` (estado + atalhos),
  `HistoryPage` (tabela com busca, filtro por aprendido e período, exportar CSV/Markdown),
  `DemoPage` e `TermsPage` (editar/criar/excluir termos com acepções).
- Indicador de estado com glow (`platform/popup.status_indicator`): bolinha flutuante
  frameless, sempre no topo, sem foco e **arrastável** (posição lembrada), com estados
  `loading`/`listening`/`analyzing`/`paused`/`error` e pulso em tempo real pelo nível de
  áudio; opção de ocultar (`Settings.indicator_enabled`). No demo o nível é simulado.
- Demonstração embutida (`platform/popup.demo_player`): monta `Detection` reais a partir do
  glossário ativo e injeta no overlay ("Ver exemplo de pop-up"), sem áudio nem modelo.
- Histórico com filtros (`Repository.history(..., query, learned, since, until)`) e
  `Repository.delete_term` (cascata, preservando o histórico).
- Segundo atalho global para o histórico (`Settings.shortcut_history`) com campo nas
  Configurações e listener dedicado.
- Progresso de inicialização (RNF-08): download/warmup do modelo roda fora da UI; o indicador
  e a bandeja mostram `Carregando…` com a fração baixada; falha vai para `ERROR` com
  "Tentar de novo" (a bandeja permanece viva).
- Erro amigável para `ImportError` (dependências do extra `ui`) em `platform/popup.errors`.
- Efeito sonoro opcional ao exibir um pop-up (`Settings.popup_sound`): bipe curto de duas
  notas sintetizado em memória (`core/audio/chime`, sem arquivos de mídia), reproduzido de
  forma assíncrona via `winsound` no Windows e com fallback para o beep do sistema.
- Instância única (`app/single_instance`): `QLockFile` na pasta de dados + `QLocalServer`;
  a segunda execução não abre banco nem carrega modelo, apenas ativa o hub da instância
  existente e encerra. O modo `--demo` usa trava separada (pode rodar ao lado do app real).

### Changed
- `matcher_fuzzy` passa a valer de ponta a ponta e fica **desligado por padrão** (opt-in),
  com checkbox em Configurações e repasse ao `MatcherConfig`. Pacotes de domínio atualizados:
  `tech-en-pt` 0.3.0; trilhas backend e data-science 0.1.1.
- Decisões registradas em `docs/02 §13`, `docs/01` (RNF-08) e README: modelos **on-demand**
  com verificação de integridade, **motor de STT por benchmark** e **Windows** como alvo do
  protótipo.
- Documentação de produto/engenharia (01–07) movida para [`docs/`](docs/); README
  reorganizado como porta de entrada do projeto (único README do repositório).
- Tela de configurações passa a preservar campos não expostos ao editar (usa
  `dataclasses.replace` sobre o `Settings` original em vez de recriá-lo).
- Instalador Inno Setup grava a saída em `dist/` (`OutputDir`), alinhado ao que o workflow
  de release publica, e usa a arquitetura `x64compatible` (sem aviso de deprecação). Ganhou
  um segundo atalho no Menu Iniciar, `Sopro (demonstração)` → `Sopro.exe --demo`.
- Configurações e Glossários foram divididos em *páginas* reutilizáveis (`SettingsPage`,
  `GlossaryPage`) e *diálogos* finos (`PageHost`) que as hospedam — as mesmas páginas aparecem
  no hub. `QApplication.setQuitOnLastWindowClosed(False)` evita que fechar uma tela encerre o
  app (que vive na bandeja).
- Pop-ups redesenhados para **alta legibilidade**: superfície própria 100% opaca pintada à
  mão (a translucidez da janela serve só para cantos/sombra), cartão mais largo (380 px),
  tipografia maior, divisória, botão de fechar explícito e contraste reforçado nos temas
  claro/escuro.

### Fixed
- Indicador circular não alternava pausa/retomada por clique: agora diferencia clique de
  arraste por limiar de movimento, só persiste a posição após arraste real e não dispara o
  toggle duas vezes.
- **Inicialização do executável congelado (`--demo`)**: `app_stylesheet` passou a existir em
  `platform/popup/theme.py` (tema global de hub/diálogos) e `MatcherConfig` não recebe mais o
  argumento inexistente `fuzzy`. Sem isso, o app encerrava com `ImportError`/`TypeError` antes
  de abrir o pipeline.
- **Erro de SQLite ao iniciar a captura real** (`SQLite objects created in a thread can only
  be used in that same thread`): o banco em arquivo passou a usar uma conexão por thread
  (`threading.local`), com WAL e `busy_timeout`, permitindo que a thread de áudio grave
  detecções enquanto a UI lê o histórico. Bancos `:memory:` continuam compartilhados e
  serializados por lock.
- Execuções duplicadas do app (cliques repetidos no atalho) agora são bloqueadas; a segunda
  instância ativa a existente em vez de abrir outra bandeja e disputar o mesmo banco.

### Notas de retomada
- Estado: **Fase 4 concluída** (instalador compilado e testado, primeira execução, logs e
  gestão de glossários) + **terceira rodada de ajustes A4.0–A4.7 implementada** (hub/páginas,
  indicador com glow, demo embutido, histórico com filtros, edição de termos, 2º atalho,
  progresso de inicialização, correção do encerramento). **392 testes passando**; `--demo`
  smoke OK. Rebuild feito (`dist/Sopro-0.1.0-portable.zip` + `dist/Sopro-Setup-0.1.0.exe`) e
  ciclo instalar → abrir → desinstalar validado (dados em `%LOCALAPPDATA%\Sopro` preservados;
  2º atalho de demonstração). Ainda **sem release marcada** — tudo acima segue em `Unreleased`.
- **Pendência:** reteste manual do mantenedor (pop-ups, hub, indicador arrastável, histórico,
  termos).
- Detalhes e checklist em [TODO.md](TODO.md) → seções "Retomada" e "Ajustes pós-Fase 4
  (terceira rodada)".

## [0.0.0] - 2026-10-07

### Added
- Documentação inicial: visão e requisitos (`01`), arquitetura e especificações (`02`),
  estado da arte (`03`), roadmap (`04`), prompts (`05`), referências (`06`) e formato do
  glossário seed (`07`).

[Unreleased]: https://example.com/sopro/compare/v0.0.0...HEAD
[0.0.0]: https://example.com/sopro/releases/tag/v0.0.0
