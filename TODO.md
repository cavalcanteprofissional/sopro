# TODO

Backlog de trabalho derivado do [roadmap](docs/04-roadmap.md). Marque itens concluídos e
mova-os para o [CHANGELOG](CHANGELOG.md) no momento da entrega.

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
- [ ] Detecção de candidatos fora do glossário no pipeline (raridade + limite de taxa próprio)
- [x] Provedor Groq de STT (agrupamento ≥ ~10 s, backoff em limite, fallback ao local) e
  fábrica de STT por preferência (`platform/stt/groq_stt`, `factory.create_provider`)
- [ ] Aviso de privacidade + confirmação antes de ativar o Groq (STT/LLM) e indicador na bandeja

## Fase 4 — Empacotamento

- [x] Especificação de empacotamento, release e compatibilidade (`docs/09`)
- [x] Executável standalone (PyInstaller onedir): `sopro.spec`, `scripts/build-windows.ps1`,
  zip portátil e `SHA256SUMS.txt` (build local validado com `--demo` em pasta arbitrária)
- [x] Download de modelos no primeiro uso (via fábrica do catálogo, com verificação sha256)
- [x] Instalador Inno Setup (`installer.iss`, per-user) e workflow de release em tag `v*`
  (`.github/workflows/release.yml`)
- [ ] Compilar e testar o instalador com Inno Setup (instalar, abrir, desinstalar)
- [ ] Primeira execução: consentimento (LGPD), domínio, idioma e fontes de áudio
- [ ] Tratamento de erros amigável; logs sem conteúdo de fala
- [ ] Tela de gerenciamento de glossários

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
