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

**Estado (2026-10-22):** código, testes e documentação prontos — **416 testes passando**,
validador sem erros (avisos de revisão humana pendentes), `--demo` smoke OK (fonte e
portátil). O portátil foi reempacotado em 2026-10-22 com os seis pacotes de domínio
(`tech-en-pt` + cinco trilhas): `dist/Sopro/`, `dist/Sopro-0.1.0-portable.zip` e
`SHA256SUMS.txt`. O `dist/Sopro-Setup-0.1.0.exe` ainda é o antigo; o Setup e os hashes
completos precisam ser refeitos.

> **Reteste manual (4ª rodada):** o mantenedor validou o *demo* ("tudo ok") e pediu uma nova
> rodada — ver a seção **"Quinta rodada — UI/UX, fonte de captura e glossário"** abaixo.
> **A quinta rodada está concluída** (A5.0–A5.6); falta apenas a confirmação de campo do
> loopback/microfone com uma aula real.

**Tarefa inicial da próxima sessão — revisar antes de avançar:**

1. Executar o **backlog de campo B1–B5** (seção própria após a Fase 7), começando por
   B1/B2/B4 (P0); B3/B5 ficam em seguida.
2. Fechar A7.4 (seletor visual de trilhas), criar `docs/trilhas/` e refazer Setup + hashes.
3. Validar o portátil manualmente e confirmar em campo o loopback/microfone (A5.1).
4. Iniciar a **Fase 7** pelo F7.0 (Clerk, Neon, R2 e Worker) após revisar o plano abaixo;
   a Fase 6 (curadoria) continua planejada.

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

### A6.3 — Matcher tolerante (P0) · REABERTO em 2026-10-22

> Reaberto na auditoria do backlog de campo. O código atual não tem `MatcherConfig.fuzzy`,
> `_term_keys` só gera plural (não gera `-ing/-ed/-er`) e `Settings.matcher_fuzzy` não tem
> efeito. Ver **B1**.

- [ ] Gerar variantes `-ing/-ed/-er` além do plural.
- [ ] Fuzzy opt-in (`MatcherConfig.fuzzy`, limiar alto + comprimento mínimo; setting + checkbox).
- [ ] Testes: `deployed`→`deploy`; typo `transfomer`→`transformer` (fuzzy); termo curto não
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
- [ ] **Reabertura parcial A6.6 (2026-10-22):** validar no código atual o que foi anunciado
  na rodada extra. O hotword não está garantido no executável e o indicador só arrasta, sem
  alternar por clique; rastrear em **B2** e **B4**.

## Sétima rodada — Nichos/trilhas do glossário `tech` (EM ANDAMENTO)

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

### A7.1 — Modelo de dados (P0) · concluído

- [x] `Manifest`: `parent_slug`, `track`, `track_label`, `track_order`; `Term.tracks`;
  `Sense.track`; `DomainPackage.track`/`is_track` (`core/glossary/package.py`).
- [x] Migração **v6** (`core/repo/migrations.py`): `domain.parent_slug`, `domain.track`,
  `term.tracks`, `sense.track`.
- [x] `Repository.upsert_domain(..., parent_slug, track)`, `add_term(..., tracks)`,
  `SenseInput.track`; `DomainRecord`/`TermRecord`/`SenseRecord` com os campos novos.
- [x] `core/repo/importer.py`: import/export preservando os campos novos (hoje o export é lossy).

### A7.2 — Agregação em runtime (P0) · concluído

- [x] `core/glossary/aggregate.py`: `aggregate_packages(packages, active_tracks)` → um
  `DomainPackage` unificado (dedup por `canonical_en`, senses com ordinals finais únicos,
  stoplist unificada) + `build_aggregate_from_repo` (modo offline/SQLite).

### A7.3 — Runtime (P0) · concluído

- [x] `app/run.py`: `_load_active_package` → `_load_active_packages` (base + trilhas ativas).
- [x] `app/detection.py`: `_persist` busca o termo em todos os domínios ativos.
- [x] `Settings.active_tracks` (vazio = todas) e correção do `indicator_enabled` duplicado.
- [x] `core/stt/vocabulary.py`: hint aceita vários pacotes (base → trilhas ativas) no limite
  de ~220 tokens.

### A7.4 — UI (P1)

- [ ] `GlossaryPage`: lista agrupada (domínio → trilhas) com checkbox por trilha.
- [ ] `SettingsPage`: seletor de trilhas ativas; `FirstRunDialog`: checkboxes aninhados.

### A7.5 — Curadoria (P1)

- [x] Base recuperada do banco (99 termos).
- [ ] Redistribuir a base entre termos genéricos e trilhas.
- [x] 5 trilhas geradas com 60–90 termos cada.
- [ ] Revisar ao menos 20 termos por trilha e marcar `needs_review=false`.
- [x] `sopro-validate-glossary --all`: 0 erros; restam avisos de revisão humana.

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

## Fase 6 — Curadoria assistida por IA (futura)

- [ ] Registrar proveniência de fontes: obra, edição, página/capítulo, licença e hash.
- [ ] Extrair candidatos com BoW/TF-IDF e n-gramas.
- [ ] Agrupar candidatos com embeddings e clusters (BERTopic/HDBSCAN).
- [ ] Usar LLM para propor rótulos, traduções e definições curtas.
- [ ] Exigir revisão humana antes de `needs_review=false`.
- [ ] Publicar pacote com página de fontes e rastreabilidade.
- [ ] Detalhar o fluxo em `docs/roadmap/` e no `CONTRIBUTING.md`.

## Fase 7 — Conta, dados em nuvem e backup (PLANEJADA)

**Objetivo:** substituir o SQLite local como fonte da verdade por uma conta de usuário e
armazenamento em nuvem, mantendo cache/outbox local apenas para funcionar offline. Áudio
continua **nunca** sendo gravado ou enviado.

### Stack escolhida (free tier verificado em 2026-10-22)

- **Neon Free** — Postgres: 1 GB por projeto, 100 CU-hours/mês, 5 GB de egress, scale-to-zero.
- **Clerk Hobby** — até 50.000 MRU, magic link e até **3 conexões sociais** no plano free.
- **Cloudflare R2** — 10 GB, 1 milhão de Class A e 10 milhões de Class B por mês, egress grátis.
- **Cloudflare Workers** — API; 100 mil requisições/dia e 10 ms de CPU por invocação no free tier.
- **GitHub Actions** — executor do backup diário (free), porque 10 ms de CPU no Worker não é
  adequado para `pg_dump`/compactação.
- **Sem credenciais de banco/bucket no cliente.** O desktop fala apenas com o Worker, que
  valida o JWT do Clerk e aplica o escopo do usuário.

O Clerk free atende a opção 2 (Neon + Clerk + R2); só o GitHub fica ativo agora. Google,
Microsoft, Discord e magic link ficam na UI como opções desabilitadas. **Quatro conexões
sociais simultâneas exigiriam plano pago**, então a ativação futura deve respeitar o limite de
3 ou revisar o provedor.

### Arquitetura alvo

```mermaid
flowchart LR
    APP["Sopro desktop"] -->|PKCE + loopback 127.0.0.1| CLERK["Clerk\nlogin e JWT"]
    APP -->|token no cofre do SO| APP
    APP -->|HTTPS + Bearer JWT| API["Cloudflare Worker\nAPI e validação do JWT"]
    API -->|SQL parametrizado\nuser_id obrigatório| NEON[("Neon Postgres\ndados relacionais do usuário")]
    API -->|objetos privados\nusers/{user_id}/...| R2[("Cloudflare R2\nglossários, snapshots e backups")]
    GHA["GitHub Actions\ncron diário"] -->|pg_dump comprimido| R2
    CATALOG["Catálogo oficial\nglossários versionados"] -->|download + SHA-256| APP
```

### Segregação por usuário

- Um único bucket privado no R2, com prefixos imutáveis por `clerk_user_id`:
  `users/{user_id}/glossaries/` e `users/{user_id}/exports/`.
- Backups: `backups/database/YYYY-MM-DD/` para o dump completo e
  `backups/users/{user_id}/YYYY-MM-DD/` para exportações pontuais.
- Glossários oficiais em prefixo separado e somente leitura; não contêm dados de usuário.
- No Neon, todas as tabelas de dados do usuário recebem `user_id` e são filtradas no Worker.
  RLS no Postgres entra como defesa em profundidade, com `app.user_id` definido pelo Worker.
- Nenhum objeto é público. Downloads usam URL assinada de curta duração via Worker.
- Teste obrigatório: usuário A não consegue ler, alterar, listar ou restaurar dados do B.

### Conta e autenticação

- Fluxo OAuth 2.0 Authorization Code + PKCE (RFC 8252), navegador do sistema e callback
  efêmero em `http://127.0.0.1:{porta}/callback`; validar `state`.
- Tokens no cofre do SO via `core/config/secrets.py` (keyring); nunca em JSON ou SQLite.
- Logout limpa tokens, cache local e dados sensíveis em memória.
- UI: tela de conta, “Entrar com GitHub”, status conectado/offline, “Sair”, “Excluir conta”.
- Provedores futuros: Google, Microsoft e Discord desabilitados com tooltip “em breve”;
  magic link desabilitado pelo mesmo mecanismo. O registry de provedores deve ligar/desligar
  sem recompilar o app.

### O que vai para a nuvem

| Dado | Destino | Observação |
|---|---|---|
| Histórico e detecções | Neon | Fonte da verdade; necessário para sync |
| Configurações | Neon | Inclui trilhas ativas, fontes e preferências |
| Glossários próprios | Neon + R2 | Metadados relacionais e pacote JSON versionado |
| Termos gerados/candidatos | Neon + R2 | Fila de aprovação e proveniência |
| Transcrições e contexto | Neon/R2 | Só se `save_transcript`/`save_context`; retenção padrão 30 dias |
| Áudio | Nunca | Permanece em memória e é descartado |
| Glossários oficiais | R2 | Versionados por manifesto + SHA-256; cacheados localmente |

### Offline, cache e sincronização

- A nuvem é a **fonte da verdade**. O SQLite local passa a ser cache + outbox, nunca o banco
  definitivo do usuário.
- Ao abrir: carrega cache, tenta `GET /sync/pull?cursor=...`; se falhar, continua offline com
  aviso visível.
- Escritas offline entram em `outbox` com UUID/ULID, `idempotency_key`, `created_at` e
  `updated_at`; upload em lote com retry exponencial.
- Conflitos: last-write-wins por registro, com `updated_at` do servidor e tombstones para
  exclusões. Glossários publicados são versionados e imutáveis; edição cria nova versão.
- Após sync confirmado, o cache é compactado; “limpar cache local” remove cópias sem apagar a
  nuvem. Migração inicial não mantém o banco antigo como fonte concorrente.
- Pull delta por cursor, sem polling agressivo; backoff e sincronização ao voltar a conexão.

### Migração no primeiro login

1. Detectar dados locais e mostrar resumo (domínios, termos, histórico, configurações).
2. Migrar automaticamente com chaves estáveis e `idempotency_key` para evitar duplicatas.
3. Enviar primeiro glossários/configurações, depois histórico e transcrições autorizadas.
4. Só marcar `migrated_at` após confirmação do servidor; então o SQLite vira cache/outbox.
5. Oferecer exportação local antes da migração e “tentar de novo” em caso de falha.

### Backup e restauração

- GitHub Actions diário às 03:00 UTC executa `pg_dump` comprimido e envia para
  `backups/database/YYYY-MM-DD/sopro.dump.gz` + `manifest.json` com tamanho, SHA-256 e versão
  do schema. O dump não fica no repositório nem em artifacts públicos.
- Exportação por usuário (`backups/users/{user_id}/`) é gerada sob demanda para portabilidade,
  exclusão de conta e restauração pontual.
- Retenção de **30 dias** via lifecycle rule do R2; backups não contam como cache local.
- Neon mantém o instant restore/point-in-time do free tier como segunda camada (6 horas).
- Restauração total: baixar o dump, restaurar em uma branch Neon isolada, validar e promover.
  Restauração de um usuário: extrair do dump/exportação por `user_id` para uma branch temporária.
- Monitorar o tamanho: 30 dumps precisam caber nos 10 GB do R2. Se chegar a 70%, reduzir
  retenção ou implementar dump incremental, sem apagar o histórico do usuário.
- Teste de restauração pelo menos uma vez por release; backup não testado não conta como
  entregue.

### Free tier e limites

- Orçamento inicial: 1 GB no Neon, 10 GB no R2, 100 mil requisições/dia e 10 ms de CPU por
  invocação no Worker, 50 mil MRU no Clerk. Monitorar tamanho por usuário e alertar antes do
  limite.
- Compactar JSONL, usar deltas, evitar indexar transcrição completa e limitar anexos.
- Backup não roda no Worker: GitHub Actions faz o dump, e o R2 guarda o resultado.
- Se o Neon ou R2 atingir o limite: modo somente leitura/offline com fila, **nunca** apagar
  dados do usuário para “liberar espaço”.
- Transcrições/contexto são o maior risco de custo e privacidade; manter compressão,
  retenção curta e opção de desligar.

### Entregáveis

- [ ] **F7.0** Criar app OAuth no Clerk, projeto Neon, bucket R2 privado, Worker e secrets.
- [ ] **F7.1** Login GitHub com PKCE/loopback, cofre do SO, tela de conta e logout.
- [ ] **F7.2** Schema Neon com `user_id`, RLS, índices, migrações e Worker com JWT/escopo.
- [ ] **F7.3** Sync pull/push, outbox, idempotência, conflitos e indicador online/offline.
- [ ] **F7.4** Glossários oficiais na nuvem + cache local com SHA-256 e catálogo de versões.
- [ ] **F7.5** Glossários próprios e pacotes do usuário no R2, com versionamento e exportação.
- [ ] **F7.6** Migração automática do SQLite local no primeiro login, com deduplicação.
- [ ] **F7.7** Backup diário via GitHub Actions no R2, lifecycle de 30 dias, restauração e
  teste de restore.
- [ ] **F7.8** Exclusão de conta, exportação LGPD, rate limit, logs sem conteúdo e testes A/B.
- [ ] **F7.9** Documentar fluxo em `docs/roadmap/`, README, CONTRIBUTING, CHANGELOG e build.

### Critérios de aceite

- [ ] Login GitHub funciona no executável congelado e sobrevive a reinício.
- [ ] Usuário A não acessa dados de B por API, R2 ou URL assinada.
- [ ] Histórico e glossários sobrevivem a limpar cache e reinstalar o app.
- [ ] Sem internet, o app abre com cache e enfileira escritas; ao voltar, sincroniza.
- [ ] Migração local → nuvem não duplica registros e pode ser repetida com segurança.
- [ ] Backup diário é criado, retido por 30 dias e restaurável em conta limpa.
- [ ] Nenhum token, credencial de banco ou áudio aparece em logs, SQLite ou R2.
- [ ] Uso cabe no free tier com os limites e alertas documentados.

### Riscos e decisões em aberto

- **Clerk free:** 3 conexões sociais; ativar Google/Microsoft/Discord exigirá escolher até 3
  ou migrar de plano.
- **Neon free:** scale-to-zero e 1 GB; sincronização precisa tolerar cold start e volume.
- **Workers free:** 10 ms de CPU por invocação; processamento pesado fica no GitHub Actions,
  e a API deve usar consultas curtas.
- **Backup no R2:** 30 dumps precisam caber em 10 GB; medir compressão e planejar retenção
  antes do primeiro release em produção.
- **Transcrições:** maior custo/risco; decidir retenção final e se haverá criptografia
  adicional no cliente antes do upload.
- **Multi-dispositivo:** LWW por registro é o padrão; colaboração em tempo real fica fora do
  escopo desta fase.
- **Custo:** se o free tier deixar de bastar, priorizar exportação/portabilidade e degradação
  graciosa antes de qualquer cobrança.

## Backlog de campo — melhorias e correções (pós-Fase 7)

Itens levantados no reteste do mantenedor em **2026-10-22**. Não são uma fase nova: entram
antes ou junto da Fase 7 conforme a prioridade. Ordem sugerida: **B1 → B2 → B4 → B3 → B5**.
Cada item deve sair com teste automatizado, atualização do CHANGELOG e, quando aplicável,
rebuild do portátil/Setup. Nada aqui autoriza gravar ou enviar áudio.

> **Auditoria:** esta seção reabre A6.3 (fuzzy/inflexões não existem no código atual) e
> A6.6 (hotword não garantido no executável e indicador sem clique). Os itens antigos foram
> anotados; a correção real é rastreada em B1/B2/B4.

### B1 — STT: fonética pt-BR, siglas e alucinações (P0)

**Sintoma de campo**
- Inglês técnico falado com sotaque brasileiro é transcrito de forma fonética e erra termos.
- Às vezes aparecem palavras que não foram ditas; outras vezes a palavra só coincide na
  pronúncia.
- Siglas faladas como letras se perdem: “API” pode chegar como “A P I” em português ou
  “ai pi ai” em inglês; “AI” e “API” não podem ser confundidos.

**Evidência no código atual**
- `core/text/normalize.py` apenas normaliza caixa/pontuação e tokeniza; não expande letras
  faladas nem variantes fonéticas.
- `core/matcher/matcher.py:_term_keys` casa canônica + aliases + plural; não há `-ing/-ed/-er`
  nem fuzzy. `MatcherConfig` não tem `fuzzy`.
- `Settings.matcher_fuzzy=True` existe, mas é inerte: não há checkbox nem uso no matcher.
- `core/stt/vocabulary.py` já monta um hint de ~220 tokens para o Whisper; é o ponto natural
  para incluir formas faladas de siglas e termos difíceis.

**Direção**
- Criar um conjunto de fixtures com inglês técnico falado por brasileiro (áudio ou transcrição
  anotada) e uma lista de erros esperados/observados.
- Normalizar siglas faladas por letra: `A P I`, `a-p-i`, `ai pi ai`, `A.I.` → `API`; criar
  testes para não converter `AI` em `API`.
- Adicionar aliases fonéticos/candidatos por termo (ex.: formas comuns geradas por pronúncia
  brasileira) e/ou uma camada de similaridade fonética conservadora, sempre com limiar alto e
  comprimento mínimo para não aumentar falsos positivos.
- Melhorar o `initial_prompt` do STT com termos, siglas e formas faladas; manter o limite de
  tokens e priorizar trilhas ativas.
- Religar o fuzzy de verdade (`MatcherConfig.fuzzy` + setting + checkbox + testes) ou remover
  `matcher_fuzzy`; não deixar opção sem efeito.
- Para alucinações: usar confiança/segmento, stoplist/contexto e não casar termos curtos por
  aproximação. Registrar os falsos positivos em teste de regressão.

**Aceite**
- “API” é reconhecida a partir de “A P I” e “ai pi ai”; “AI” continua distinto.
- Um conjunto fixo de falas com sotaque melhora sem aumentar falsos positivos além do limite
  acordado no teste.
- `matcher_fuzzy` funciona de ponta a ponta ou deixa de existir.
- Testes cobrem normalização de siglas, aliases fonéticos, fuzzy e falsos positivos.

**Arquivos prováveis:** `core/text/normalize.py`, `core/stt/vocabulary.py`,
`core/matcher/matcher.py`, `app/detection.py`, `platform/stt/faster_whisper_engine.py`,
`platform/stt/groq_stt.py`, `tests/test_matcher.py`, `tests/test_text.py`.

### B2 — Hotword “sopro”, ativação/desativação e sons (P0)

**Sintoma de campo**
- O comando por voz “sopro” deveria pausar/retomar o app, mas não foi observado funcionando.
- Faltam sons suaves ao ativar/desativar (ou eles nunca são ouvidos porque o hotword não
  dispara).

**Evidência no código atual**
- Existe `core/hotword/` com `OpenWakeWordDetector` e `SttShortHotwordDetector`; `app/run.py`
  cria o detector, registra `on_toggle`, toca `play_hotword_on/off` e o mantém ativo enquanto o
  app está pausado.
- `openwakeword` não está declarado no `pyproject.toml` nem garantido no `sopro.spec`
  (modelos/ONNX podem ficar fora do build). O fallback importa `sounddevice`, que não está
  instalado nem declarado; `create_hotword_detector()` engole a exceção e devolve `None`.
- No `.venv` há `openwakeword 0.6.0`, mas não há modelo customizado “sopro”. O código atual
  dispara com **qualquer** modelo default quando `phrase == "sopro"`
  (`self._phrase in name.lower() or self._phrase == "sopro"`), o que não é um hotword real.
- Não há controles de hotword em `platform/popup/settings_window.py`: só pop-up e indicador.

**Direção — registrar as duas opções (decisão do mantenedor)**
- **Opção A (ideal):** modelo openWakeWord customizado para “sopro”, empacotado com o app e
  versionado; se o modelo não existir, falhar de forma visível em vez de silenciosa.
- **Opção B (contingência):** fallback STT curto usando a captura de áudio já existente
  (evitar `sounddevice` se possível), com modelo carregado uma vez, VAD e limite de CPU;
  detectar a palavra e alternar pausa/retomada.
- Corrigir o matching para comparar com o modelo/frase correta e nunca disparar em qualquer
  palavra; adicionar debounce e log de diagnóstico sem conteúdo de áudio.
- Expor na UI: ativar/desativar, frase, backend, sensibilidade, dispositivo e botão “testar”.
- Manter a escuta durante a pausa para permitir retomar por voz; não encerrar a thread ao
  pausar.
- Sons de ativação/desativação suaves e distintos; manter síntese atual como placeholder e
  permitir substituir por WAV fornecido pelo mantenedor depois.
- Empacotar dependências/modelos no `sopro.spec` e validar no executável congelado, não só no
  ambiente de desenvolvimento.

**Aceite**
- Dizer “sopro” alterna pausa/retomada no executável congelado.
- Nenhum disparo aleatório com fala comum ou com outros modelos default.
- UI permite ligar/desligar, testar e ajustar sensibilidade/dispositivo.
- Sons suaves são audíveis e diferentes do som do pop-up; ausência de áudio não derruba o app.
- Teste de regressão cobre callback, debounce, pausa/retomada e ausência de dependência.

**Arquivos prováveis:** `core/hotword/`, `app/run.py`, `core/config/settings.py`,
`platform/popup/settings_window.py`, `platform/popup/sound.py`, `core/audio/chime.py`,
`pyproject.toml`, `sopro.spec`, `scripts/build-windows.ps1`.

### B3 — Som de bolha no pop-up (P1)

**Sintoma de campo**
- O pop-up usa hoje um chime sintetizado de duas notas; o mantenedor quer um som de bolha
  estourando suavemente.

**Evidência no código atual**
- `core/audio/chime.py:chime_wav` gera o chime; `platform/popup/sound.py:play_popup_sound`
  toca esse WAV via `winsound` e usa `QApplication.beep()` como fallback.

**Direção**
- Criar um WAV curto de bolha (ataque rápido, sweep suave e decaimento exponencial), sem
  arquivos externos obrigatórios e sem clipping.
- Manter volume configurável (`popup_volume`), fallback e reprodução assíncrona.
- Usar placeholder sintetizado agora; se o mantenedor fornecer um WAV, permitir substituição
  sem reescrever a lógica.
- Não confundir com os sons de ativação/desativação do hotword.

**Aceite**
- WAV mono válido, curto e audível; teste de duração/energia/limite de amplitude.
- `popup_sound=False` continua silenciando; falha de áudio não impede o pop-up.
- Som percebido como bolha suave, não como chime de duas notas.

**Arquivos prováveis:** `core/audio/chime.py`, `platform/popup/sound.py`,
`tests/test_popup_sound.py`.

### B4 — Indicador circular: clique para pausar e arraste para mover (P0)

**Sintoma de campo**
- O círculo colorido no canto superior esquerdo deve alternar ativar/desativar com **um
  clique único**, como o comando de voz.
- Ele também precisa continuar **arrastável** pela tela para o usuário posicionar onde quiser.

**Evidência no código atual**
- `platform/popup/status_indicator.py:StatusIndicator` só implementa arraste:
  `mousePressEvent` guarda o offset, `mouseMoveEvent` move e `mouseReleaseEvent` salva a
  posição via `on_moved`. Não existe callback de clique nem `on_toggle`.
- Um clique hoje apenas salva a posição; não pausa/retoma.

**Direção**
- Adicionar `on_click` (ou sinal Qt) e ligar ao `on_toggle` em `app/run.py`.
- Diferenciar clique de arraste por limiar de movimento (ex.: 4–6 px) e botão esquerdo:
  - movimento abaixo do limiar no release → clique → alterna pausa/retomada;
  - movimento acima do limiar → arraste → move e salva posição, sem alternar.
- Preservar `on_moved` apenas quando houve arraste real.
- Atualizar cursor/tooltip conforme o estado (ex.: “Clique para pausar” / “Clique para
  retomar”; “Arraste para mover”) e garantir que o clique não abra o hub nem dispare duas
  vezes.
- Cobrir clique, arraste, clique sem movimento e arraste sem toggle nos testes.

**Aceite**
- Clique único pausa/retoma e altera o estado visual/som.
- Arraste move o indicador e persiste a posição; soltar após arraste não pausa.
- Testes existentes de movimento continuam passando; novos testes cobrem o clique.

**Arquivos prováveis:** `platform/popup/status_indicator.py`, `app/run.py`,
`tests/test_popup_status_indicator.py`, `core/config/settings.py`.

### B5 — Glossário em árvore e ativação automática do pai (P1)

**Sintoma de campo**
- O glossário deve ser uma árvore hierárquica, tanto visualmente quanto na arquitetura.
- Todas as trilhas de tecnologia devem ficar ligadas ao glossário pai `tech`, ativando-o
  automaticamente ao serem marcadas.

**Evidência no código atual**
- O modelo já tem `parent_slug`, `track`, `track_label`, `track_order`, `Term.tracks`,
  `Sense.track` e `aggregate_packages(base, tracks, active_tracks)`.
- `_load_active_glossary` já carrega a base + trilhas e escolhe o pai quando só a trilha está
  configurada, mas isso é implícito e não persistido como árvore.
- `platform/popup/glossary_window.py:GlossaryPage` ainda usa `QListWidget` plano; não há
  árvore, checkbox por trilha nem seletor de trilhas em `SettingsPage`/`FirstRunDialog`.
- `active_tracks=()` significa “todas as trilhas”, então hoje não é possível representar
  “somente a base” de forma explícita. Isso precisa ser corrigido antes da UI em árvore.

**Decisões confirmadas**
- Marcar qualquer trilha tech ativa automaticamente o glossário pai `tech`.
- Desmarcar o glossário pai desmarca todas as trilhas filhas.
- A ativação deve ser persistida de forma explícita, não inferida apenas em runtime.

**Direção**
- Criar uma representação explícita para “todas as trilhas” vs “nenhuma/seleção específica”
  (ex.: `active_tracks: tuple[str, ...] | None`, com `None` = todas e `()` = nenhuma; ou um
  `tracks_mode` equivalente), com migração de leitura e testes.
- Centralizar a regra de fechamento pai/filhas no núcleo (ex.: `resolve_active_tree`) e usar
  em `_load_active_glossary`, `GlossaryPage`, `SettingsPage` e `FirstRunDialog`; a UI não deve
  ser a única dona da regra.
- Trocar a lista plana por `QTreeWidget`: pai `tech` com filhos de trilha, checkbox e estado
  consistente; marcar filha marca o pai; desmarcar o pai desmarca as filhas.
- Exibir contagem de termos e estado de revisão por nó; manter importar/exportar.
- Garantir que a agregação carregue base + trilhas selecionadas, sem duplicar termos, e que
  somente a base não carregue todas as trilhas.
- Atualizar `docs/02 §7/§9`, `docs/07 §7`, README e CONTRIBUTING quando a UI mudar.

**Aceite**
- Árvore consistente em Glossários, Configurações e primeira execução.
- Marcar uma trilha marca o pai; desmarcar o pai desmarca as filhas.
- “Somente base” não carrega trilhas; “todas” carrega todas; seleção explícita persiste após
  reiniciar.
- Agregação e matcher continuam funcionando; testes de árvore/fechamento e UI passam.

**Arquivos prováveis:** `core/glossary/package.py`, `core/glossary/aggregate.py`,
`app/run.py`, `core/config/settings.py`,
`platform/popup/glossary_window.py`, `platform/popup/settings_window.py`,
`platform/popup/first_run.py`, `tests/test_glossary_aggregate.py`,
`tests/test_glossary_window.py`, `tests/test_run_glossary.py`.

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
