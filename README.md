# Sopro (nome provisório)

**Um companheiro discreto que explica termos técnicos em inglês no momento exato em que eles são falados.**

> Status: **protótipo funcional**. Captura → VAD → transcrição → matcher → pop-up +
> histórico (SQLite) já rodam de ponta a ponta; overlay, bandeja e tela de configurações
> estão prontos e há um executável portátil. RAG/desambiguação (Fase 3) e instalador
> (Fase 4) em andamento.

Você está vendo uma aula, palestra ou call técnica em inglês e ouve *"fairness"* ou *"backlog"* passar rápido. Pesquisar quebra a atenção. Legenda automática não explica o termo nem escolhe o sentido certo para a área.

O Sopro resolve assim: escuta o áudio do seu PC (ou do microfone), detecta o termo quando é falado e mostra um cartão curto com o termo, a tradução e a definição no contexto da área — sem interromper a aula e sem roubar o foco da janela.

## Destaques

- **Pop-up por termo, não legenda corrida** — cartão temporário, sempre no topo, sem roubar foco do Teams/Meet/Zoom.
- **Local primeiro** — roda 100% offline por padrão; nuvem (Groq) é opcional e só com aviso explícito.
- **Definição certa para a área** — recuperação semântica escolhe a acepção correta (ex.: *fairness* = "equidade" em IA, não "justiça" genérica).
- **Privacidade** — áudio não é gravado em disco; sem telemetria; dados não saem do computador.
- **Só free tier** — Whisper local, SQLite, ferramentas gratuitas.
- **Escalável** — glossários por domínio: tecnologia hoje, direito/saúde/finanças depois.

## Como funciona (resumo)

```
Áudio (saída do PC / microfone)
   → detecção de fala (VAD)
   → transcrição em tempo real (Whisper local)
   → busca no glossário do domínio ativo
   → escolha da acepção pelo contexto (RAG)
   → pop-up com termo, tradução e definição
   → registro no histórico local (SQLite)
```

O LLM **não** processa toda frase: o caminho rápido é busca em glossário local. RAG/LLM só entra para resolver ambiguidade ou termos fora do glossário — isso mantém latência, CPU e custo baixos.

## Início rápido (desenvolvimento)

Requisitos: Python 3.11+.

```bash
# criar e ativar ambiente virtual
python -m venv .venv
. .venv/Scripts/activate        # Windows (Git Bash)
# source .venv/bin/activate     # Linux/macOS

# instalar em modo editável com dependências de desenvolvimento
python -m pip install -e ".[dev]"

# (opcional) motor de STT local — dependência pesada, baixa ~75–460 MB de modelos
python -m pip install -e ".[stt]"

# (opcional) captura de áudio no Windows (loopback WASAPI + microfone)
python -m pip install -e ".[audio]"

# (opcional) overlay, bandeja e tela de configurações (PySide6)
python -m pip install -e ".[ui]"

# rodar o app (precisa de 'ui' e, para áudio real, de 'audio' + 'stt')
python -m sopro

# modo demonstração: pipeline + UI sem microfone e sem baixar modelos
# (pop-ups fictícios; os dados vão para uma pasta isolada com --home/SOPRO_HOME)
python -m sopro --demo

# sonda de captura: mede o nível por fonte sem gravar em disco (10 s)
sopro-capture-probe --seconds 10

# rodar os testes
pytest -q

# validar o pacote de domínio seed (checklist do docs/07 §6)
sopro-validate-glossary data/domains/tech-en-pt

# benchmark offline (requer o extra 'stt'); o modelo é baixado e verificado no 1º uso
sopro-benchmark aula.wav anotacao.csv --provider sopro.platform.stt.factory:faster_whisper
```

## Estrutura do repositório

```
docs/                         Documentação de produto e engenharia (01–09)
data/domains/                 Pacotes de domínio (glossários)
  └─ tech-en-pt/              Pacote seed: Tecnologia e IA (EN→PT)
src/sopro/
  ├─ core/                    Núcleo portável (text, glossary, matcher, rag, llm, repo, config)
  ├─ platform/                Camadas dependentes de SO/UI (audio, popup)
  └─ app/                     Orquestração, ciclo de vida, bandeja, atalhos
tests/                        Testes automatizados (pytest)
fixtures/                     Dados de apoio (ex.: template do conjunto de teste)
```

**Regra de arquitetura:** `core` não depende de SO nem de UI; `platform` isola isso. Isso viabiliza portar para Linux, macOS e mobile sem reescrever o núcleo.

## Roadmap em 5 fases

1. **Validação** — glossário seed e conjunto de teste anotado
2. **Pipeline em CLI** — captura, VAD, transcrição e matcher medidos
3. **Overlay e persistência** — pop-up, SQLite, configurações
4. **RAG e desambiguação** — acepção contextual + provedor Groq opcional
5. **Empacotamento** — instalador Windows e primeira execução

Detalhes e definições de pronto em [docs/04-roadmap.md](docs/04-roadmap.md).

## Distribuição e downloads

Ainda **não há release publicada**. Quando a Fase 4 chegar, cada versão será publicada em
**[Releases](../../releases)** com:

- `Sopro-Setup-x.y.z.exe` — instalador Windows (per-user, sem administrador);
- `Sopro-x.y.z-portable.zip` — versão portátil;
- `SHA256SUMS.txt` — hashes para verificação.

Requisitos do executável: **Windows 10 (build 1809+) ou Windows 11, 64-bit**, CPU com AVX2
recomendada. Os modelos são baixados na primeira execução (instalador enxuto). O guia
completo de empacotamento, assinatura e CI está em
[docs/09-empacotamento-e-release.md](docs/09-empacotamento-e-release.md).

### Build local do executável portátil

Gera um `.exe` **standalone** (não exige Python instalado) e um zip portátil:

```powershell
# instala o ferramental de empacotamento no ambiente (uma vez)
python -m pip install -e ".[packaging]"

# build + zip + SHA256SUMS.txt em dist/ (roda os testes antes; use -SkipTests para pular)
powershell -ExecutionPolicy Bypass -File scripts/build-windows.ps1
```

Saída em `dist/`: `Sopro/` (pasta *onedir* com `Sopro.exe`), `Sopro-<versão>-portable.zip` e
`SHA256SUMS.txt`. Para rodar a versão portátil, basta extrair o zip e executar
`Sopro/Sopro.exe` (`--demo` funciona sem áudio nem modelos). Para gerar o instalador com o
Inno Setup, compile `installer.iss` com `iscc /DVersion=<versão> installer.iss`. O workflow
`.github/workflows/release.yml` automatiza build, instalador e publicação em uma tag `v*`.


## Documentação

Toda a documentação de produto e engenharia está em [`docs/`](docs/). Leia na ordem:

| Arquivo | O que tem |
|---|---|
| [01-visao-e-requisitos.md](docs/01-visao-e-requisitos.md) | O problema, a visão, requisitos (RF/RNF/RN), critérios de aceite e notas legais |
| [02-arquitetura-e-especificacoes.md](docs/02-arquitetura-e-especificacoes.md) | Pipeline, módulos, contratos, modelo de dados e especificação do pop-up |
| [03-estado-da-arte.md](docs/03-estado-da-arte.md) | Pesquisa de soluções existentes e a lacuna que o Sopro preenche |
| [04-roadmap.md](docs/04-roadmap.md) | Fases de implementação, métricas, riscos e marcos |
| [05-prompts.md](docs/05-prompts.md) | Prompts de desenvolvimento (por fase) e de runtime do app |
| [06-referencias.md](docs/06-referencias.md) | Links, bibliotecas, limites de free tier e notas legais |
| [07-glossario-seed-modelo.md](docs/07-glossario-seed-modelo.md) | Formato do pacote de domínio (JSON/CSV), manifesto e entradas de exemplo |
| [08-distribuicao-e-offline.md](docs/08-distribuicao-e-offline.md) | Modelos sob demanda, verificação de integridade, cache local e o que roda sem internet |
| [09-empacotamento-e-release.md](docs/09-empacotamento-e-release.md) | Executável standalone, instalador, CI de release e compatibilidade de Windows |

Convenções de leitura: **RF-xx** requisito funcional, **RNF-xx** requisito não funcional,
**RN-xx** regra de negócio; itens **(verificar)** dependem de confirmação em fonte oficial;
metas numéricas são **hipóteses iniciais** a calibrar no protótipo.

## Decisões já tomadas

| Tema | Decisão |
|---|---|
| Plataforma do protótipo | Windows (arquitetura deve permitir Linux, macOS e, no futuro, mobile) |
| Idioma do áudio | Inglês |
| Idioma de saída | Escolhido pelo usuário (padrão: português do Brasil) |
| Transcrição | Híbrida: **local por padrão** (Whisper), Groq **opcional** |
| Área inicial | Tecnologia (com arquitetura de "pacotes de domínio" para outras áreas) |
| Custo | Somente free tier / open source |
| Dados | Tudo local (SQLite); áudio não é gravado por padrão |
| Distribuição de modelos | **On-demand**: instalador enxuto; download na 1ª execução com verificação de integridade (sha256) |
| Motor de STT local | Decidido por **benchmark** (faster-whisper vs whisper.cpp), isolado pela interface `STTProvider` |
| Nome | Provisório. Candidatos: **Sopro**, Tip Fellow, Jargonaut, TermoPop, Glossa Live (verificar INPI, GitHub e domínio) |

## Contribuindo

Veja [CONTRIBUTING.md](CONTRIBUTING.md) e o [Código de Conduta](CODE_OF_CONDUCT.md). O trabalho segue as regras do **Prompt-mestre** em [docs/05-prompts.md](docs/05-prompts.md).

## Segurança e privacidade

Processamento local por padrão; áudio em memória e descartado. Provedor em nuvem só com opt-in, aviso e indicador permanente. Gravar/transcrever reuniões pode exigir consentimento dos participantes (LGPD — Lei 13.709/2018). Veja [SECURITY.md](SECURITY.md).

## Licença

A definir — pendente de revisão das licenças dos glossários e fontes (ver [docs/06-referencias.md](docs/06-referencias.md)). Ver [LICENSE](LICENSE).
