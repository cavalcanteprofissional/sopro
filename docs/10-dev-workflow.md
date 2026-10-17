# 10 — Fluxo de execução e desenvolvimento local

Define como rodar o Sopro **a partir do código-fonte**, sem build e sem instalador, e como
gerar o executável portátil. É o equivalente a `npm run dev`, porém em Python e isolado por
ambiente virtual. Complementa o `09` (empacotamento) e antecipa a Fase 4 do `04`.

> Status: **especificação executável**. O task runner (`scripts/tasks.py`), o modo
> demonstração e o build portátil já existem e estão validados.

## 1. Ambiente

Requisitos: Python 3.11+ (protótipo em 3.12). Tudo roda dentro de um ambiente virtual; o
`.venv/` fica versionado como ignorado.

```bash
python -m venv .venv
. .venv/Scripts/activate        # Windows (Git Bash)
# source .venv/bin/activate     # Linux/macOS

# dependências completas (dev + UI + áudio + STT)
python scripts/tasks.py install
# equivalente a: python -m pip install -e ".[dev,ui,audio,stt]"
```

Extras disponíveis (`pyproject.toml`):

| Extra | Para quê | Peso |
|---|---|---|
| `dev` | testes (pytest) | leve |
| `ui` | overlay, bandeja, configurações (PySide6) | ~150 MB |
| `audio` | captura WASAPI + microfone (PyAudioWPatch) | ~1 MB |
| `stt` | transcrição local (faster-whisper) | ~30 MB + modelos |
| `packaging` | gerar o executável (PyInstaller) | ~10 MB |

## 2. Task runner

`scripts/tasks.py` unifica os comandos (não exige `make`, `just` ou `uv`) e usa o Python do
ambiente corrente. Argumentos extras são repassados ao comando.

| Tarefa | Comando equivalente |
|---|---|
| `dev` | `python -m sopro` |
| `demo` | `python -m sopro --demo` |
| `test` | `python -m pytest -q` |
| `bench` | `python -m sopro.app.benchmark_cli ...` |
| `validate` | `python -m sopro.core.glossary.validate ...` |
| `build` | `scripts/build-windows.ps1` (executável portátil) |
| `install` | `pip install -e ".[dev,ui,audio,stt]"` |

```bash
python scripts/tasks.py test
python scripts/tasks.py demo --home "%TEMP%/sopro-demo"
python scripts/tasks.py validate data/domains/tech-en-pt
```

## 3. Rodar o aplicativo

```bash
python scripts/tasks.py dev            # precisa de 'ui' e, para áudio real, 'audio' + 'stt'
python scripts/tasks.py demo           # sem microfone e sem baixar modelos
```

- `--demo` usa áudio e transcrições sintéticos (`app/demo`), casando com o glossário, e
  exibe pop-ups fictícios no overlay.
- `--home <pasta>` (ou `SOPRO_HOME`) isola banco, modelos e logs — use para testar sem
  tocar no histórico real.
- `--domains-root <pasta>` aponta para outro diretório de pacotes de domínio.

A pasta de dados padrão é `~/.sopro` no código-fonte e `%LOCALAPPDATA%\Sopro` no executável
do Windows (docs/09 §5).

## 4. Modo demonstração e testes

O modo demo é a forma de exercitar o pipeline completo (VAD → STT → matcher → pop-up →
SQLite) **sem hardware nem rede**. Os testes cobrem cada camada isoladamente:

```bash
python scripts/tasks.py test            # toda a suíte
python -m pytest tests/test_app_demo.py  # só o pipeline de demonstração
```

Para validar o app congelado sem reabrir o build, o modo demo aceita o truque de fumaça
`SOPRO_SMOKE_MS=<ms>`, que encerra o loop de eventos sozinho (útil em CI/headless).

## 5. Empacotamento local

```powershell
python -m pip install -e ".[packaging]"
python scripts/tasks.py build            # gera dist/Sopro/, dist/Sopro-<v>-portable.zip e SHA256SUMS.txt
```

O build é *onedir*: embute código, dados e dependências nativas, **não** embute os modelos
(baixados no 1º uso). Detalhes, instalador (Inno Setup) e CI de release: [docs/09](09-empacotamento-e-release.md).

## 6. Dois "sem instalar"

Há duas coisas distintas que não exigem instalador, e não devem ser confundidas:

1. **Desenvolver a partir do fonte** — `python -m sopro` dentro do `.venv` (§3). Requer
   Python e as dependências instaladas localmente.
2. **Executável portátil** — extrair `Sopro-<v>-portable.zip` e rodar `Sopro/Sopro.exe`
   (§5). Não exige Python, não escreve no registro e pode rodar de um pendrive.

## 7. uv (opcional)

O `pyproject.toml` já é compatível com [uv](https://docs.astral.sh/uv/). Se você usa `uv`:

```bash
uv sync --extra dev --extra ui --extra audio --extra stt
uv run sopro --demo
uv run pytest -q
```

O `uv.lock` é opcional e não é mantido pelo protótipo; quando quiser travar o grafo, rode
`uv lock` e versione o arquivo.

## 8. Integração contínua

O workflow [`.github/workflows/release.yml`](../.github/workflows/release.yml) dispara em
tag `v*`: instala os extras, roda `pytest` e `sopro-validate-glossary`, gera o build
PyInstaller, o instalador Inno Setup, o zip portátil e o `SHA256SUMS.txt`, e publica tudo
numa GitHub Release.
