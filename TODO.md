# TODO

Backlog de trabalho derivado do [roadmap](docs/04-roadmap.md). Marque itens concluídos e
mova-os para o [CHANGELOG](CHANGELOG.md) no momento da entrega.

## Retomada — onde paramos (próxima sessão)

A **Fase 4 — Empacotamento** foi concluída: instalador Inno Setup compilado e testado
(instalar/abrir/desinstalar, per-user, preservando `%LOCALAPPDATA%\Sopro`), assistente de
primeira execução (consentimento LGPD + domínio/idioma/fontes), logs rotativos sem conteúdo
de fala, erros amigáveis e tela de gerenciamento de glossários (importar/exportar/ativar).

**Terceira rodada de ajustes (A4.0–A4.7) implementada** — ver a seção **"Ajustes pós-Fase 4
(terceira rodada)"** abaixo, já marcada.

**Quarta rodada — correções do reteste do mantenedor (implementada):**

- Corrigido o **erro de SQLite ao iniciar** (`SQLite objects created in a thread…`): conexão
  por thread com WAL/`busy_timeout`, fechada ao fim da thread de áudio.
- **Pop-ups redesenhados** para alta legibilidade (superfície opaca, cartão maior, contraste
  reforçado) e **som opcional** ao exibir.
- **Instância única**: segunda execução ativa o hub existente e encerra (`--demo` tem trava
  separada).

**Estado:** código, testes e documentação prontos — **403 testes passando**, validador sem
erros, `--demo` smoke OK. Build/instalador (`dist/Sopro-0.1.0-portable.zip` +
`dist/Sopro-Setup-0.1.0.exe`) do ciclo anterior validado (instalar → abrir → desinstalar,
dados em `%LOCALAPPDATA%\Sopro` preservados); **falta reempacotar** com estas correções.

> **Falta o novo reteste manual do mantenedor** (pop-ups/som, hub, indicador arrastável,
> histórico, edição de termos, abertura repetida do app). Se algo falhar, aplicar os ajustes
> antes de seguir. A Fase 5 (escala e portabilidade) **não** começa até esse reteste.

**Tarefa inicial da próxima sessão — revisar antes de avançar:**

1. Reempacotar (`scripts/build-windows.ps1` + `iscc`) e rodar `pytest -q`,
   `sopro-validate-glossary data/domains/tech-en-pt` e
   `SOPRO_SMOKE_MS=1500 python -m sopro --demo` (confira `logs/sopro.log`).
2. Coletar o resultado do reteste manual; corrigir o que for apontado.
3. Conferir este `TODO`, o checkpoint de release em `docs/09` §9 e os prompts `docs/05` A9/A10.
4. Decidir as questões em aberto da seção "Decisões" (embedding, LLM local, UI, licença do
   glossário) antes de fechar a v0.1.

**Depois:** seguir para a **Fase 5 — Escala e portabilidade** (camadas Linux/macOS, outros
pacotes de domínio, feedback "irrelevante").

## Fase 0 — Validação

- [x] Estrutura inicial do projeto em Python
- [x] Pacote de domínio `tech-en-pt` v0.1.0 (manifesto + primeiro lote de ~50 termos)
- [x] Stoplist inicial (`docs/07` §4)
- [x] Validador do checklist do pacote (`docs/07` §6)
- [x] Template do conjunto de teste anotado (CSV)
- [ ] Ampliar o glossário para ~200 termos (lotes de ~50 via prompts `A1`/`B2`)
- [ ] Revisar amostra de ≥20 termos (`needs_review=false`) até o checklist `docs/07` §6 passar
- [ ] Definir licença e autores do pacote `tech-en-pt`
- [ ] Gravar 3 aulas/vídeos de ~10 min (IA/tecnologia) e anotar termos falados com timestamp
- [ ] Transcrever com Whisper local e medir taxa de acerto dos termos
- [ ] Escolher a máquina de referência (CPU, RAM) para as metas de desempenho

## Fase 1 — Pipeline em linha de comando

- [x] Captura de loopback e microfone no Windows com etiquetas de fonte (`system`/`mic`)
  (`platform/audio` com PyAudioWPatch, contrato `AudioSource` e sonda `sopro-capture-probe`)
- [x] VAD + segmentação (máx. 8–12 s, sobreposição 0,3–0,5 s)
- [x] Contrato `STTProvider` + adapter local com engine injetável
- [x] Catálogo de modelos com verificação de integridade (sha256) e cache local
- [x] Download sob demanda com verificação sha256 e cache local (`core/stt/download`)
- [x] Binding `faster-whisper` (extra `stt`) por trás de `STTProvider` + fábrica do catálogo
- [x] Catálogo verificado com modelo STT real (`whisper-tiny-en`: url/sha256/tamanho)
- [ ] Verificar `whisper-small-en` (modelo principal) e o candidato whisper.cpp (prompt `A9`)
- [ ] Escolher o motor (faster-whisper vs whisper.cpp) por benchmark
- [x] `matcher`: n-gramas de 1–4 tokens, aliases, stoplist com regra de contexto, cooldown
- [x] Métricas de benchmark (recall/precisão/F1 por termo) e leitor do CSV anotado
- [x] Modo benchmark: processar WAV ponta a ponta (VAD + STT injetável + matcher + métricas),
  com leitor de WAV e console script `sopro-benchmark`

## Fase 2 — Overlay e persistência

- [x] Pop-up sem foco, sempre no topo, com fila e cooldown (overlay + fila; cooldown no `Matcher`)
- [x] Fila de cartões de pop-up com limite de simultâneos (política no `Matcher`)
- [x] Serviço de detecção: transcrição → matcher → histórico (SQLite) → pop-up (`app/detection`)
- [x] Pipeline em tempo real: VAD incremental por fonte → detecção (`app/realtime`, `core/vad.streaming`)
- [x] Overlay do pop-up em PySide6 (docs/02 §8): sem borda/sem foco, sempre no topo,
  empilhado por canto, tema claro/escuro, hover pausa, clique fecha, "fixar"
- [x] SQLite com esquema e migrações; histórico por sessão (`core/repo`)
- [x] Configurações validadas com persistência (`core/config`); segredos via cofre do SO
- [x] Importador/exportador de pacotes de domínio (JSON)
- [x] Tela mínima de configurações (`platform/popup.settings_window`)
- [x] Ícone na bandeja com estado e menu (`platform/popup.tray`)
- [x] Atalhos globais de teclado (pausar/fechar) — `core/hotkeys` + `platform/hotkey`
  (Windows `RegisterHotKey`), com degradação graciosa e atalho editável nas configurações

## Fase 3 — RAG e desambiguação

- [x] Embeddings locais e índice vetorial das acepções (`core/rag`, tabela `sense_vec`, migração v3)
- [x] `SenseResolver` em cascata (acepção única → domínio → vetor → LLM), janela de contexto
  e limiar configurável; integrado ao serviço de detecção
- [x] Conjunto de casos ambíguos e medição de acurácia (`core/rag/evaluate`)
- [x] Camada de LLM: prompt B1 com JSON validado, `LLMSenseChooser` (passo `llm` da cascata)
  e geração fora do glossário com cache e fila de aprovação (`core/llm`, `generated_entry`,
  migração v4); provedores local (OpenAI-compatível) e Groq (LLM) com backoff em limite
- [x] Detecção de candidatos fora do glossário no pipeline (maior casamento + limite de taxa próprio,
  `core/llm/candidates`, `extract_candidates`, `RateLimiter`)
- [x] Provedor Groq de STT (agrupamento ≥ ~10 s, backoff em limite, fallback ao local) e
  fábrica de STT por preferência (`platform/stt/groq_stt`, `factory.create_provider`)
- [x] Aviso de privacidade + confirmação antes de ativar o Groq (STT/LLM) e indicador na bandeja
  (`settings_window` com `remote_consent`; `tray.set_remote`; `config.cloud_providers`)

## Fase 4 — Empacotamento

- [x] Especificação de empacotamento, release e compatibilidade (`docs/09`)
- [x] Executável standalone (PyInstaller onedir): `sopro.spec`, `scripts/build-windows.ps1`,
  zip portátil e `SHA256SUMS.txt` (build local validado com `--demo` em pasta arbitrária)
- [x] Download de modelos no primeiro uso (via fábrica do catálogo, com verificação sha256)
- [x] Instalador Inno Setup (`installer.iss`, per-user) e workflow de release em tag `v*`
  (`.github/workflows/release.yml`)
- [x] Compilar e testar o instalador com Inno Setup (instalar, abrir, desinstalar;
  per-user, sem admin, preservando `%LOCALAPPDATA%\Sopro`); `OutputDir=dist` alinhado ao CI
- [x] Primeira execução: consentimento (LGPD), domínio, idioma e fontes de áudio
  (`platform/popup/first_run.py`, `Settings.first_run_done`)
- [x] Tratamento de erros amigável; logs sem conteúdo de fala (`app/logging_setup.py`,
  `platform/popup/errors.py`)
- [x] Tela de gerenciamento de glossários: importar/exportar/ativar
  (`platform/popup/glossary_window.py`, `Repository.set_domain_active`, menu da bandeja)

## Ajustes pós-Fase 4 (terceira rodada) — IMPLEMENTADO

Escopo e decisões confirmados pelo mantenedor. Implementação feita em módulos
consolidados (a estrutura original previa arquivos separados; ver notas "desvio").
Pendente: rebuild do instalador e reteste manual do mantenedor.

### Decisões confirmadas

- [x] **D4.1** Falha na inicialização: manter a bandeja viva em `ERROR` com "Tentar de novo"
  (não sai com código 2).
- [x] **D4.2** "Abrir demonstração": **nova instância** `Sopro.exe --demo`.
- [x] **D4.3** RF-25: **segundo atalho global** dedicado ao histórico.
- [x] **D4.4** Histórico: filtrar por texto, **aprendido e data**.
- [x] **D4.5** Hub: **refatorar** os diálogos em páginas reutilizáveis.
- [x] **D4.6** Indicador: widget flutuante **independente e arrastável**, com opção de ocultar.
- [x] **D4.7** Pulso **em tempo real** (nível de áudio; simulado no demo embutido).
- [x] **D4.8** Demo embutido usa os **termos reais do glossário ativo**.

### A4.0 — Corrigir encerramento ao abrir/fechar telas (P0)

- [x] `app/run.py`: `_configure_app` chama `app.setQuitOnLastWindowClosed(False)`; só "Sair"
  e o smoke chamam `quit()`.
- [x] Teste: `test_configure_app_disables_quit_on_last_window_closed` (`tests/test_app_run.py`).

### A4.1 — Progresso de download + feedback de inicialização (RNF-08, docs/08 §4, docs/09 §5)

- [x] `platform/stt/factory.py`: `faster_whisper`/`create_provider`/`_resolve_spec` aceitam
  `progress` e repassam a `ensure_model` (`ProgressFn` em `core/stt/download.py:28`).
- [x] `app/run.py`: na inicialização real, `_build_provider(..., on_progress=...)` roda no
  **thread de áudio**; `StatusBridge.progress` atualiza o indicador em `LOADING` (nível =
  fração baixada); `ready` → `LISTENING`; `failed` → `ERROR` + balão; `retry_requested`
  reconstrói (`on_retry`).
- [x] `platform/popup/tray.py`: `TrayState.LOADING` (cor ciano + "Carregando…") e `notify()`.
- [x] `platform/popup/errors.py`: hint para `ImportError` (dependências do extra `ui`).
- [*] **Desvio:** não foi criado `model_progress.py`/`ModelProgressDialog`; o progresso é
  refletido no **indicador/tray** (estado `LOADING` + nível), sem barra modal.

### A4.2 — Janela de histórico/revisão (RF-22) + atalho (RF-25)

- [x] Core: `Repository.history(..., *, query, learned, since, until)` com filtros por
  texto (LIKE em termo/tradução/contexto), aprendido e período.
- [x] `platform/popup/pages.py`: `HistoryPage` (tabela Quando/Termo/Tradução/Fonte/
  Aprendido, busca, filtro aprendido, período com QDateEdit, exportar CSV/Markdown).
- [x] `platform/popup/tray.py` + `app/run.py`: sinal/ação "Histórico…" → abre o hub na página.
- [x] RF-25: `Settings.shortcut_history` + segundo `create_listener` (`_start_hotkey_for`),
  campo "Atalho do histórico" nas Configurações.
- [*] **Desvio:** página embutida no hub (não `history_window.py`/`HistoryDialog`); a coluna
  Sessão e o combo de sessões foram omitidos (filtro por período/texto cobriu a RF).

### A4.3 — Glossário: editar/adicionar termos (RF-23)

- [x] Core: `Repository.delete_term(term_id)` (cascata sense_vec/sense/alias/FTS; nulifica
  referências em `detection` preservando o histórico); `add_term` faz *upsert* por canônico.
- [x] `platform/popup/pages.py`: `TermsPage` (busca, lista, domínio, canônico, classe,
  aliases, prioridade, ambíguo, tabela de acepções, Salvar/Novo/Excluir).
- [x] Aba "Termos" no hub (`HubWindow`).
- [*] **Desvio:** `TermEditorDialog` não foi criado; a edição vive na página do hub.

### A4.4 — Polimento da bandeja/demo

- [x] Ação "Abrir demonstração" (nova instância) e "Ver exemplo de pop-up" na bandeja.
- [x] `TrayState.ERROR` ligado a falha de pipeline (`on_failed`) + "Tentar de novo" (`on_retry`).
- [x] 2º atalho no `installer.iss`: `Sopro (demonstração)` → `Sopro.exe --demo`.
- [x] "Assistente inicial…" reiniciável via menu (`on_assistant`) e no hub (`StatusPage`).
- [x] "Abrir Sopro…"/clique abre o hub; fechar o hub mantém o app rodando (A4.0).

### A4.5 — Hub/janela principal (refatorar diálogos em páginas)

- [x] `platform/popup/pages.py`: `StatusPage`, `HistoryPage`, `DemoPage`, `TermsPage`.
- [x] `platform/popup/settings_window.py`: `SettingsPage` (diálogo virou wrapper fino).
- [x] `platform/popup/glossary_window.py`: `GlossaryPage` (diálogo virou wrapper fino).
- [x] `platform/popup/host.py`: `PageHost` mantém compatibilidade dos diálogos (`__getattr__`).
- [x] `platform/popup/hub.py`: `HubWindow` com navegação lateral (Status/Configurações/
  Glossários/Termos/Histórico/Demonstração) e botão "Aplicar" por página.
- [*] **Desvio:** `AboutPage` não foi criada (fora do escopo confirmado).

### A4.6 — Indicador de estado com glow (tempo real)

- [x] `platform/popup/status_indicator.py`: `StatusIndicator` frameless/always-on-top/sem
  foco/**arrastável** (posição em `settings.indicator_x/y`), `StatusDot` embutível e
  `paint_status_dot` (testável). Estados `loading/listening/analyzing/paused/error` + pulso.
- [x] `Settings.indicator_enabled` (opção de ocultar) e checkbox nas Configurações.
- [x] Nível real: `RealtimePipeline.handle_frame` → `on_level(0..1, speaking)` e
  `on_analyzing(bool)`; `StatusBridge` marshala para a UI.
- [x] Refletido na `StatusPage` (dot + Pausar/Retomar).

### A4.7 — Demo embutido no produto

- [x] `platform/popup/demo_player.py`: `build_demo_detections` monta `Detection` reais do
  **glossário ativo** (termo/classe/tradução/definição) e `DemoPlayer` injeta no overlay.
- [x] Página "Demonstração" no hub + ação na bandeja "Ver exemplo de pop-up".
- [x] `--demo`: `cooldown_s=0`/`budget=120` (via `dataclasses.replace`) para não estacar.
- [*] **Desvio:** módulo chamado `demo_player.py` (não `demo.py`), para não colidir com
  `app/demo.py` (dados falsos do `--demo`).

### Testes adicionados nesta rodada

- `tests/test_popup_demo_player.py` (5), `tests/test_popup_status_indicator.py` (5),
  `tests/test_popup_hub.py` (5); extensões em `test_repo_repository.py` (filtros de histórico
  + `delete_term`) e `test_app_run.py`.

### Pendências desta rodada

- [x] Rebuild PyInstaller (`scripts/build-windows.ps1 -SkipTests`) → `dist/Sopro-0.1.0-portable.zip`
  (+ `SHA256SUMS.txt`).
- [x] Recompilar `installer.iss` → `dist/Sopro-Setup-0.1.0.exe`.
- [x] Reteste instalado/frozen: `--demo` no `Sopro.exe` portátil e no instalado retornaram
  exit 0 (log sem conteúdo de fala); ciclo instalar → abrir → desinstalar verde, com
  `%LOCALAPPDATA%\Sopro` preservado e 2º atalho de demonstração criado/removido.
- [ ] Reteste manual do mantenedor: pop-ups, hub, indicador arrastável, histórico, termos.

## Fase 5 — Escala e portabilidade

- [ ] Pacotes de domínio adicionais (direito, saúde, finanças)
- [ ] Camadas de plataforma para Linux e macOS
- [ ] Avaliar versão mobile (microfone) reutilizando o núcleo
- [ ] Botão "irrelevante" alimentando a lista de exclusão

## DX — execução local e modo demo (implementar no final, após as fases)

Objetivo: rodar o app localmente **sem build e sem instalador** (equivalente a `npm run dev`),
em ambiente isolado, e testar sem hardware/modelos.

- [x] Entrypoint do app (`python -m sopro` + script `sopro` em `[project.scripts]`)
- [x] Suporte a **uv** (`uv run sopro`, `uv sync`; `uv.lock` opcional e não mantido)
- [x] Task runner com alvos `dev`, `test`, `demo`, `bench`, `validate`, `build`, `install`
  (`scripts/tasks.py`, sem exigir `make`/`just`/`uv`)
- [x] Modo **demo/mock**: `DemoAudioSource` e `DemoProvider` (`app/demo`) ligados via `--demo` no `app/run`, para rodar o pipeline + UI sem microfone e sem baixar modelos
- [x] Isolamento de dados via `--home` / `SOPRO_HOME` temporário (`app/home`, não toca no histórico/config reais)
- [x] Documentar: seção no `README` ("Rodar localmente"), `docs/10-dev-workflow.md` e
  `CONTRIBUTING.md`; e o **portável sem instalador** (`docs/09`)
- [x] Distinguir os dois "sem instalar": (a) dev a partir do fonte; (b) portável `.zip` (Fase 4)

## Decisões (docs/02 §13)

### Fechadas
- [x] Distribuição dos modelos: on-demand com verificação de integridade (docs/08)
- [x] Motor de STT local: decidido por benchmark (faster-whisper vs whisper.cpp)
- [x] Sistema do protótipo: Windows (Linux/macOS na Fase 5)
- [x] Captura de áudio no Windows: PyAudioWPatch (loopback WASAPI + microfone), atrás de `AudioSource` (docs/05 A2)

### Em aberto
- [ ] Modelo de embedding exato (tamanho vs. qualidade em inglês técnico + português)
- [ ] LLM local mínimo viável (no instalador ou sob demanda)
- [ ] Estratégia de lematização leve sem dependências pesadas
- [ ] Distribuição/licença do glossário seed
- [ ] Framework de UI definitivo se o instalador ficar grande
