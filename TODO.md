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

**Estado:** código, testes e documentação prontos — **410 testes passando**, validador sem
erros (2 avisos: licença do pacote e 0 termos revisados), `--demo` smoke OK (fonte e
portátil). **Reempacotado em 2026-10-20** com as correções da quinta rodada:
`dist/Sopro-0.1.0-portable.zip` e `dist/Sopro-Setup-0.1.0.exe` (+ `SHA256SUMS.txt` com os dois).

> **Reteste manual (4ª rodada):** o mantenedor validou o *demo* ("tudo ok") e pediu uma nova
> rodada — ver a seção **"Quinta rodada — UI/UX, fonte de captura e glossário"** abaixo
> (UI/pop-up mais tecnológico, registro da fonte de captura, diagnóstico do loopback e
> ampliação do glossário). **A quinta rodada está concluída** (A5.0–A5.6 abaixo); falta apenas
> a confirmação de campo do loopback/microfone com uma aula real. A Fase 5 (escala e
> portabilidade) pode começar.

**Tarefa inicial da próxima sessão — revisar antes de avançar:**

1. Confirmar em campo (aula real) a captura do loopback e o nível/fala do microfone (A5.1).
2. Conferir este `TODO`, o checkpoint de release em `docs/09` §9 e os prompts `docs/05` A9/A10.
3. Decidir as questões em aberto da seção "Decisões" (embedding, LLM local, UI, licença do
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
- [ ] Reteste manual do mantenedor: ver a seção **"Reteste manual do mantenedor"** abaixo
  (instalador de 2026-10-20).

## Reteste manual do mantenedor (4ª rodada) — 2026-10-20

Executar com `dist/Sopro-Setup-0.1.0.exe` (build de 2026-10-20, com as correções da quarta
rodada). Marque cada item; se algo falhar, anotar o sintoma e corrigir antes da Fase 5.

- [ ] **M1 Instalação** — instalar (per-user, sem admin), abrir; assistente de primeira
  execução aparece (consentimento LGPD, domínio, idioma, fontes de áudio).
- [ ] **M2 Pop-ups** — bandeja → "Ver exemplo de pop-up"; cartão opaco e legível (contraste
  reforçado), som opcional ao exibir, hover pausa, clique fecha, "fixar" funciona, fila
  empilha por canto.
- [ ] **M3 Indicador arrastável** — arrastar o dot; posição persiste após reiniciar
  (`indicator_x/y`); opção nas Configurações o oculta; pulso em tempo real
  (LOADING → LISTENING com o nível do áudio).
- [ ] **M4 Hub** — bandeja → "Abrir Sopro…"; 6 páginas (Status/Configurações/Glossários/
  Termos/Histórico/Demonstração); botão "Aplicar" por página; fechar o hub mantém o app
  rodando; "Assistente inicial…" reiniciável.
- [ ] **M5 Histórico** — busca por texto, filtro "aprendido", período com datas, exportar
  CSV/Markdown; segundo atalho global abre o histórico.
- [ ] **M6 Termos** — editar termo existente, adicionar novo, excluir; acepções editáveis;
  exclusão não apaga o histórico.
- [ ] **M7 Instância única** — abrir o Sopro uma segunda vez: ativa o hub existente e a
  segunda execução encerra; `--demo` tem trava separada ("Abrir demonstração" abre nova
  instância sem disputar a trava).
- [ ] **M8 Demo** — demonstração usa os termos reais do glossário ativo.
- [ ] **M9 Falha/retry** — se o pipeline falhar, bandeja fica em ERROR com "Tentar de novo"
  (não sai com código 2).
- [ ] **M10 Privacidade** — `logs/sopro.log` sem conteúdo de fala; sem chaves em texto puro;
  ativação do Groq pede confirmação e mostra indicador na bandeja.

## Quinta rodada — UI/UX, fonte de captura e glossário (CONCLUÍDA)

Derivada do reteste do mantenedor: demo OK, mas pediu (a) UI/pop-up mais "tecnológico e
atrativo", com UI/UX ideal para a ferramenta; (b) **registrar a fonte** de cada detecção
(microfone vs. áudio do sistema); (c) verificar a captura do loopback e por que termos como
"framework" não foram detectados.

### Diagnóstico (causas-raiz identificadas)

- **`context_hints` se perdem no app** (P0): `importer.build_domain_package` reconstrói
  `Term(... context_hints=())` (`core/repo/importer.py:157`) e a tabela `term` não tem coluna
  para eles (`core/repo/migrations.py:19-28`). Todo termo `stoplisted` (pipeline, model,
  layer, kernel, bug, cloud, token) tem hints vazios → `_context_confirms` sempre falso →
  **nunca dispara pop-up** no app real (nos testes passa, pois carregam o JSON direto).
- **"framework" não existe no glossário** (66 termos): só há `docs/06` citando a palavra.
- **Nível do indicador sempre baixo** (P2): `app/realtime.py:58` usa
  `max(1.0, energy_threshold)` → `speaking` sempre `False` e `level` ≤ ~0,25.
- **Loopback pode estar mudo**: volume do app/mixer/dispositivo de saída errado; validar com
  `sopro-capture-probe`.

### Decisões confirmadas

- [x] **Estética:** *dark tecnológico* como padrão (fundo `#0B1120`/`#0F172A`, accent
  ciano/violeta estilo ferramenta de dev), tema claro preservado como opção, com **detecção
  real de `theme=system`** (hoje cai sempre no claro).
- [x] **Glossário:** ampliar ~35 termos ausentes nesta rodada + corrigir os `context_hints`.
- [x] **Ícone:** gerar ícone de marca (SVG→ICO) para janela/bandeja/instalador agora.
- [ ] **Pendência futura:** o mantenedor criará o ícone definitivo no Illustrator e
  solicitaremos a substituição do ícone gerado (registrar ao fim da rodada).

### A5.0 — Correção da detecção (P0)

- [x] Migração v5: coluna `context_hints TEXT NOT NULL DEFAULT '[]'` na tabela `term`.
- [x] `Repository.add_term`/upsert e `list_terms` gravam/leem `context_hints` (JSON).
- [x] `importer.build_domain_package` reconstrói `context_hints` do banco (sem `()` fixo);
  `import_package`/`export_package_json` também preservam os hints.
- [x] Testes: round-trip de hints no repo (`test_repo_repository.py`), rebuild preservando
  hints (`test_repo_importer.py`) e disparo end-to-end do `pipeline` via banco
  (`test_matcher.py::test_seed_stoplisted_term_fires_after_db_round_trip`).

### A5.1 — Captura (diagnóstico)

- [x] `sopro-capture-probe --seconds 6` (durante áudio no PC): **system rms=0.0219,
  pico=0.2178** (loopback OK, acima do limiar 0.01); **mic rms=0.0000** (microfone
  do headset mudo/selecionado errado). Loopback padrão = "FxSound Speakers".
  **A confirmar com uma aula real** ao vivo pelo mantenedor.

### A5.2 — Glossário

- [x] 33 termos novos adicionados (framework, library, runtime, compiler, interpreter,
  debug, callback, thread, concurrency, middleware, container, microservice, database,
  query, schema, index, cache, server, client, protocol, gateway, websocket, load
  balancer, SDK, IDE, branch, CI/CD, DevOps, downtime, scalability, refactor, unit test,
  code review). Total: **99 termos**.
- [x] `sopro-validate-glossary` sem novos erros (2 avisos pré-existentes: licença e 0
  revisados).

### A5.3 — Design tokens e tema (C1)

- [x] Ampliar `Palette` (accent_soft, success/warning/danger, surface_elevated, shadow,
  `font_family`) e criar a paleta **dark tecnológica** (padrão) + clara.
- [x] Resolver `theme="system"` de verdade (detectar dark do SO via `winreg`); font-family real.
- [ ] Centralizar cores hoje espalhadas: `status_indicator.py`, `tray.py`, `pages.py:66`.
  (STATE_COLORS do indicador/bandeja mantidos de propósito — testes fixam os valores.)

### A5.4 — Pop-up e fonte (B1/B2/B3 + C2)

- [x] Chip de fonte no cartão ("Áudio do sistema" / "Microfone") via `Detection.source` +
  setting `show_source` (checkbox nas Configurações).
- [x] Badge de classe (pos), hierarquia tipográfica.
- [x] **Animações de entrada/saída** (fade + slide ≤ 200 ms via `QPropertyAnimation`).
- [x] Histórico/export: `source_label` rotula `system`/`mic` como "Sistema"/"Microfone".

### A5.5 — Hub, ícones e microinterações (C3/C4/C5)

- [x] Hub e páginas com o novo tema; navegação lateral estilizada; botões com hierarquia.
- [x] Ícone de marca (SVG→ICO) + `setWindowIcon` + bandeja + `sopro.spec`/`installer.iss`.
- [x] Corrigir nível/fala do indicador (`realtime.py` usava `max(1.0, threshold)` numa
  escala `rms` 0..1 → `speaking` sempre falso; agora usa o `energy_threshold` direto).

### A5.6 — Testes, docs e release (D1–D3)

- [x] Preservar atributos privados testados; cores do indicador mantidas.
- [x] Novos testes: chip de fonte, `context_hints`, label de fonte, `theme=system`, `brand_icon`.
- [x] Atualizar `docs/02 §8`, README e `TODO`; rebuild + instalador.
  - `410 passed`; build portátil `dist/Sopro-0.1.0-portable.zip` e instalador
    `dist/Sopro-Setup-0.1.0.exe` regerados; `dist/SHA256SUMS.txt` com os dois arquivos.
  - Smoke do `.exe` empacotado OK (modo demo, sem traceback).

## Sexta rodada — Detecção (glossário/modelo/matcher) e aba Sobre (CONCLUÍDA)

Derivada do reteste do mantenedor: "algumas palavras ainda não estão sendo identificadas" —
melhorar o glossário e refinar/trocar o modelo STT; e adicionar uma **aba de disclaimer**
com licença do software + "about me" do dev (analisado o GitHub `cavalcanteprofissional`).

### Diagnóstico (causas-raiz — da análise do pipeline)

- **STT fraco (P0)**: default é `whisper-tiny-en` (~74 MB, o pior modelo EN); `whisper-small-en`
  existe no catálogo mas `verified:false` (não baixa). Decodificação `beam_size=1`,
  `temperature=0` (`platform/stt/faster_whisper_engine.py:23-26`).
- **Matcher rígido (P0)**: casa por igualdade exata de tokens após normalização, só com plural
  (`core/matcher/matcher.py:52-80`); sem fuzzy, sem `-ing/-ed`. Qualquer erro do Whisper
  ("imbeddings") falha.
- **Bias do Whisper truncado (P1)**: `vocabulary_hint` limita aos **50** termos de maior
  prioridade (`core/stt/vocabulary.py:11-21`) → os 25 termos priority-3 (bug, cloud, thread,
  unit test…) nunca entram no `initial_prompt`.
- **Glossário pequeno (P1)**: 99 termos.
- **Divergência de config (P2)**: `settings.groq_stt_model="whisper-large-v3-turbo"` vs
  `factory.DEFAULT_GROQ_STT_MODEL="whisper-large-v3"`.
- **Licença "a definir"**: `LICENSE`, `pyproject.toml`, `README` e `manifest.json` sem licença
  concreta; não há superfície "Sobre".

### Decisões confirmadas (mantenedor)

- [x] **Detecção:** ampliar glossário + variantes, melhorar o bias do Whisper, matcher tolerante
  (fuzzy) e **trocar o modelo STT padrão**.
- [x] **Licença:** **MIT**.
- [x] **About:** resumo + links do GitHub (nome + bio curta + LinkedIn/portfolio/e-mail).

### A6.0 — Registrar plano (antes)

- [x] Plano registrado neste TODO e em `docs/02 §8` / `docs/06` antes de implementar.

### A6.1 — Modelo STT padrão (P0)

- [x] Preencher `whisper-small-en` no `data/models.json` (url/sha256/size, `verified:true`).
- [x] Tornar `whisper-small-en` o default (`settings.py`, `factory.py`, fallbacks em `run.py`).
- [x] Trocar o campo livre de `stt_model` por combo populado do catálogo (evita typo que
  derruba o pipeline).

### A6.2 — Bias do Whisper (P1)

- [x] Subir o limite do `vocabulary_hint` (todos os termos, truncando por tokens ~224) e
  incluir siglas/aliases curtos.

### A6.3 — Matcher tolerante (P0)

- [x] Gerar variantes `-ing/-ed/-er` além do plural.
- [x] Fuzzy opt-in (`MatcherConfig.fuzzy`, limiar alto + comprimento mínimo; setting + checkbox).
- [x] Testes: `deployed`→`deploy`; typo `transfomer`→`transformer` (fuzzy); termo curto não
  casa por fuzzy.

### A6.4 — Glossário (P1)

- [x] Ampliar o glossário em ~80–100 termos (IA/dev) + enriquecer aliases (formas verbais).
- [x] `sopro-validate-glossary` sem erros; meta > 180 termos.

### A6.5 — Aba Sobre / Licença (P0)

- [x] `AboutPage` (Sobre, Licença MIT + terceiros, Aviso/LGPD, Sobre o desenvolvedor com links)
  + item "Sobre" no Hub; `_apply` desabilitado nessa aba.
- [x] Definir MIT: `LICENSE`, `pyproject.toml`, `README`, `manifest.json` (licença + autores).

### A6.6 — Testes, docs e release

- [x] Testes: `AboutPage`, aba no Hub, matcher (fuzzy/flexões), glossário, default do modelo.
- [x] Atualizar docs/TODO (depois); `pytest`; rebuild portátil + instalador + `SHA256SUMS.txt`.
  - `410 passed` → glossário com 201 termos (SaaS/PaaS/IaaS, cloud, containers, IAM…), matcher
    com flexões + fuzzy opt-in, modelo padrão `whisper-small-en`, aba "Sobre" com MIT e
    créditos; **rodada extra**: hotword (openWakeWord) com palavra configurável, indicador
    clicável, sons distintos e verificação de conflito I/O de áudio.

## Sétima rodada — Nichos/trilhas do glossário `tech` (PLANEJADA)

O glossário `tech` cresce **em nichos**: a área de tecnologia passa a ter **trilhas**
(programação, ciência de dados, devops, frontend, backend) como sub-pacotes do **mesmo
domínio lógico**, com seleção múltipla simultânea pelo usuário.

### Decisões confirmadas (mantenedor)

- [x] **Slug**: `tech-<trilha>-en-pt` (mantém `domain_tag == "tech"` — o matcher, o resolver e o
  validador seguem funcionando sem reescrita).
- [x] **Escopo**: implementar as 5 trilhas; o usuário pode escolher **várias** trilhas ao mesmo
  tempo (além da base).
- [x] **Tamanho**: 60–90 termos por trilha.
- [x] **Base**: **redistribuir** — termos específicos saem da base e entram na trilha.
- [x] **UI**: agrupamento em árvore no glossário + seletor de trilhas nas configurações.

### A7.0 — Registrar plano (antes)

- [x] Plano registrado neste TODO, em `docs/07 §7` (formato das trilhas) e `docs/02 §7/§9`.

### A7.1 — Modelo de dados (P0)

- [ ] `Manifest`: `parent_slug`, `track`, `track_label`, `track_order`; `Term.tracks`;
  `Sense.track`; `DomainPackage.track`/`is_track` (`core/glossary/package.py`).
- [ ] Migração **v6** (`core/repo/migrations.py`): `domain.parent_slug`, `domain.track`,
  `term.tracks`, `sense.track`.
- [ ] `Repository.upsert_domain(..., parent_slug, track)`, `add_term(..., tracks)`,
  `SenseInput.track`; `DomainRecord`/`TermRecord`/`SenseRecord` com os campos novos.
- [ ] `core/repo/importer.py`: import/export preservando os campos novos (hoje o export é lossy).

### A7.2 — Agregação em runtime (P0)

- [ ] `core/glossary/aggregate.py`: `aggregate_packages(packages, active_tracks)` → um
  `DomainPackage` unificado (dedup por `canonical_en`, senses com ordinals finais únicos,
  stoplist unificada) + `build_aggregate_from_repo` (modo offline/SQLite).

### A7.3 — Runtime (P0)

- [ ] `app/run.py`: `_load_active_package` → `_load_active_packages` (base + trilhas ativas).
- [ ] `app/detection.py`: `_persist` busca o termo em todos os domínios ativos.
- [ ] `Settings.active_tracks` (vazio = todas) e correção do `indicator_enabled` duplicado.
- [ ] `core/stt/vocabulary.py`: hint aceita vários pacotes (base → trilhas ativas) no limite
  de ~220 tokens.

### A7.4 — UI (P1)

- [ ] `GlossaryPage`: lista agrupada (domínio → trilhas) com checkbox por trilha.
- [ ] `SettingsPage`: seletor de trilhas ativas; `FirstRunDialog`: checkboxes aninhados.

### A7.5 — Curadoria (P1)

- [ ] Redistribuir a base (201 termos) entre genérico e trilhas.
- [ ] 5 trilhas × 60–90 termos (programação, data science, devops, frontend, backend).
- [ ] `sopro-validate-glossary` sem erros em todos os pacotes.

### A7.6 — Testes, docs e release (P0)

- [ ] Testes: agregação, migração v6, round-trip import/export, matcher sobre o agregado,
  hint priorizando trilha, UI agrupada.
- [ ] `docs/02 §7/§9`, `docs/07 §7`, README, CHANGELOG; `pytest`; rebuild portátil +
  instalador + `SHA256SUMS.txt`.

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
