# 09 — Empacotamento, distribuição e release

Especifica como transformar o Sopro em um **executável standalone** (sem Python instalado)
e como **publicar releases** com download profissional. Complementa o `08` (modelos
on-demand) e antecipa a Fase 4 do `04` (instalador Windows). Este documento é a referência
para a automação de build e para a seção de download do README.

> Status: **especificação**. Nada aqui é embutido no protótipo ainda; serve de guia para a
> Fase 4 e para o workflow de CI.

## 1. Princípios de empacotamento

- **Instalador enxuto** (`08` §1): o executável traz **código e dependências**, mas **não**
  os modelos. O modelo de STT é baixado no primeiro uso, com verificação sha256 (`08` §4).
- **Um só artefato de código para cada SO.** O núcleo é portável; o build é por plataforma.
- **Reprodutível.** O build sai de um *tag* Git e de um `pyproject.toml` travado; o mesmo
  tag gera o mesmo conjunto de arquivos.
- **Verificável.** Toda release publica o instalador, o zip portátil e um `SHA256SUMS.txt`.
- **Sem telemetria e sem áudio em disco** (`08` §2, `01` RNF-09) — nada muda no empacotamento.

## 2. Compatibilidade e retrocompatibilidade

### 2.1 Alvo

| Item | Requisito | Observação |
|---|---|---|
| SO | **Windows 10 64-bit (build 1809/17763+)** e Windows 11 | Protótipo (`04` Fase 1). Windows 7/8 não são alvo. |
| Arquitetura | **x64** | ARM64 não é alvo nesta fase. |
| CPU | **AVX2** recomendado | CTranslate2 (faster-whisper) usa AVX2; sem ele a inferência fica muito lenta. |
| RAM | ≥ 4 GB (recomendado 8 GB) | `small.en` em CPU. |
| GPU | opcional (CUDA) | Não distribuída por padrão; CPU-first. |

### 2.2 Por que Windows 10 1809+ e não versões antigas

- O runtime de build (Python **3.12**) suporta Windows **8.1+**; a 3.12 **encerrou** o
  suporte a Windows 7. Como empacotamos o interpretador embutido, o mínimo prático vira o
  que as *wheels* nativas (CTranslate2, onnxruntime, PyAV, tokenizers) suportam.
- Bibliotecas nativas modernas assumem a API do Windows 10; manter Windows 7 exigiria
  pinar versões antigas de todas elas — inviável e fora do escopo.
- **Decisão:** declarar **Windows 10 1809+ / Windows 11, 64-bit** como suportado.

### 2.3 Matriz de teste (retrocompatibilidade verificável)

Antes de cada release estável, validar o executável em:

| Alvo | O que valida |
|---|---|
| Windows 10 22H2 x64 (build 19045) | Máquina de referência do autor |
| Windows 10 1809 x64 (build 17763) | Piso de compatibilidade |
| Windows 11 23H2/24H2 x64 | Atualidade |

Checagens por alvo: abre sem Python instalado; baixa+verifica o modelo; transcreve; pop-up
(quando houver); desinstala sem deixar lixo (fora de `%LOCALAPPDATA%\Sopro`).

## 3. Ferramentas de build

| Etapa | Ferramenta | Papel |
|---|---|---|
| Congelar código Python | **PyInstaller** | Gera `.exe` + `_internal/` (modo *onedir*). |
| Instalador | **Inno Setup** | Gera `Sopro-Setup-x.y.z.exe` (per-user). |
| Portátil | zip do diretório *onedir* | `Sopro-x.y.z-portable.zip`. |
| Assinatura | **signtool** (Authenticode) | Assina `.exe`/instalador (opcional, §7). |
| Checksums | `sha256sum`/PowerShell | `SHA256SUMS.txt` na release. |
| Orquestração | **GitHub Actions** (`windows-latest`) | Build, testes e publicação. |

### 3.1 PyInstaller: *onedir* e não *onefile*

- **onedir** (recomendado): inicializa rápido, extrai DLLs nativas (CTranslate2/onnxruntime)
  sem o custo de descompressão do *onefile*, e facilita o updater futuro.
- **onefile**: conveniente, porém lento na abertura e propenso a antivírus; usar apenas se
  houver necessidade real de um único arquivo.

### 3.2 O que embutir e o que **não** embutir

**Embutir:** código `src/sopro`, `data/models.json` (catálogo), `data/domains/**` (glossários
seed), DLLs de `ctranslate2`, `numpy`, `onnxruntime`, `tokenizers`, `av`, a DLL do
`pyaudiowpatch` (PortAudio com loopback WASAPI) e o interpretador Python.

**Não embutir:** os **modelos** (§1). O download é on-demand com sha256 (`08` §3–§4).

Esboço de `sopro.spec` (referência):

```python
# sopro.spec
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files

binaries = collect_dynamic_libs("ctranslate2")
datas = (
    collect_data_files("sopro")            # se os dados forem empacotados no pacote
    + [("data/models.json", "data"),
       ("data/domains", "data/domains"),
       ("src/sopro/platform/popup/assets", "sopro/platform/popup/assets")]
)

a = Analysis(
    ["src/sopro/app/__main__.py"],         # entry point da aplicação (Fase 2+)
    datas=datas,
    binaries=binaries,
    hiddenimports=["faster_whisper", "ctranslate2", "tokenizers"],
    excludes=["tkinter", "matplotlib", "pandas"],
)
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="Sopro",
    console=False,
    icon="src/sopro/platform/popup/assets/sopro.ico",
)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, name="Sopro")
```

> O ícone de runtime é gerado a partir do mestre `docs/assets/brand/sopro-icon.png` com
> `python scripts/make-icon.py`; o `sopro.spec` precisa embutir a pasta `assets` e apontar
> `icon=` no `EXE`, senão o `.exe` usa o ícone padrão do PyInstaller.

> Ainda **não existe** `src/sopro/app/__main__.py`; ele entra quando houver app de verdade
> (Fase 2). Até lá, o build pode empacotar apenas o CLI de benchmark.

### 3.3 Descobrir o catálogo em execução

O catálogo é lido por `platform/stt/factory.default_catalog_path()`, que hoje é relativo ao
repositório. No executável, embutir `data/models.json` e resolver via
`sys._MEIPASS`/`importlib.resources` (ou apontar `SOPRO_CATALOG` para o caminho embutido).
Ajustar antes do primeiro build.

### 3.4 Build local (Windows)

```powershell
python -m pip install -e ".[packaging]"
powershell -ExecutionPolicy Bypass -File scripts/build-windows.ps1
```

O script roda os testes, gera o *onedir* com PyInstaller, o zip portátil e, se o Inno Setup 6
estiver instalado, o `Sopro-Setup-<versão>.exe`. O `SHA256SUMS.txt` inclui **ambos** os
artefatos. Use `-SkipTests`, `-SkipInstaller` ou `-Iscc <caminho>` conforme necessário. Se o
Setup antigo existir, ele é removido antes da compilação para evitar artefato obsoleto.

## 4. Versionamento e releases

- **SemVer** (`MAJOR.MINOR.PATCH`) e tag anotada `vX.Y.Z`.
- `CHANGELOG.md` no formato *Keep a Changelog*; a seção `[Unreleased]` vira a versão no tag.
- Releases publicadas em **GitHub Releases** com:

| Asset | Conteúdo |
|---|---|
| `Sopro-Setup-x.y.z.exe` | Instalador (Inno Setup), per-user. |
| `Sopro-x.y.z-portable.zip` | Versão portátil (sem instalar). |
| `SHA256SUMS.txt` | Hashes de todos os assets. |

Modelo de notas de release:

```markdown
## Sopro vX.Y.Z — <título curto>

### Adicionado
- ...

### Corrigido
- ...

### Compatibilidade
- Windows 10 1809+ / Windows 11, 64-bit (x64). CPU com AVX2 recomendada.

### Verificação
sha256: <hash do instalador>
```

## 5. Instalador (Inno Setup)

- **Escopo por usuário** (`PrivilegesRequired=lowest`): instala em
  `%LOCALAPPDATA%\Programs\Sopro` — **não** exige administrador.
- Atalhos no Menu Iniciar: **Sopro** e **Sopro (demonstração)** (este executa `Sopro.exe
  --demo`); a Área de Trabalho é opcional.
- Desinstalador que **preserva** `%LOCALAPPDATA%\Sopro` (dados/modelos) por padrão e remove
  os atalhos criados.
- Primeira execução dispara o assistente de consentimento e o **download de modelos**, com
  progresso no indicador de estado/bandeja (sem diálogo modal — `08` §4).

Esboço `installer.iss` (referência):

```ini
[Setup]
AppName=Sopro
AppVersion={#Version}
DefaultDirName={localappdata}\Programs\Sopro
PrivilegesRequired=lowest
OutputBaseFilename=Sopro-Setup-{#Version}
OutputDir=dist
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2
SolidCompression=yes
SetupIconFile=src\sopro\platform\popup\assets\sopro.ico

[Files]
Source: "dist\Sopro\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{userprograms}\Sopro"; Filename: "{app}\Sopro.exe"
Name: "{userprograms}\Sopro (demonstração)"; Filename: "{app}\Sopro.exe"; \
  Parameters: "--demo"

[Run]
Filename: "{app}\Sopro.exe"; Description: "Abrir o Sopro"; Flags: nowait postinstall
```

## 6. CI/CD (GitHub Actions)

Dispara **no tag** `v*`, roda testes e publica. Esboço:

```yaml
name: release
on:
  push:
    tags: ["v*"]
jobs:
  windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -e ".[dev,stt]" pyinstaller
      - run: pytest -q
      - run: pyinstaller sopro.spec
      - run: iscc /DVersion=${{ github.ref_name }} installer.iss
      - name: Checksums
        run: |
          cd dist
          $lines = Get-FileHash -Algorithm SHA256 Sopro-Setup-*.exe, Sopro-*-portable.zip |
            ForEach-Object { "$($_.Hash.ToLower())  $($_.Path | Split-Path -Leaf)" }
          [System.IO.File]::WriteAllText("SHA256SUMS.txt", ($lines -join "`n") + "`n", [System.Text.Encoding]::ASCII)
      - uses: softprops/action-gh-release@v2
        with:
          files: |
            dist/Sopro-Setup-*.exe
            dist/Sopro-*-portable.zip
            dist/SHA256SUMS.txt
```

## 7. Assinatura de código (opcional, recomendado)

- Sem assinatura, o Windows SmartScreen exibe aviso ("editor desconhecido").
- Opções: **OV** (mais barata; reputação construída com o tempo) ou **EV** (reputação
  imediata, mais cara, às vezes exige token HSM).
- Assinar `Sopro.exe` e o instalador com `signtool sign /fd sha256 /tr <timestamp> /td sha256`.
- Se não houver certificado, publicar na release um aviso de como verificar o `SHA256SUMS.txt`
  e ignorar o aviso com segurança.

## 8. README: seção de download (profissional)

Adicionar no topo do README (quando houver a 1ª release):

```markdown
## Download

[![Release](https://img.shields.io/github/v/release/<owner>/<repo>)](../../releases/latest)
[![Licença](https://img.shields.io/github/license/<owner>/<repo>)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-blue)](pyproject.toml)

Baixe o instalador para Windows em **[Releases](../../releases/latest)**:

| Versão | Instalador | Portátil | Requisitos |
|---|---|---|---|
| x.y.z | `Sopro-Setup-x.y.z.exe` | `Sopro-x.y.z-portable.zip` | Windows 10 1809+/11, x64 |

Verificação (PowerShell):

```powershell
Get-FileHash .\Sopro-Setup-x.y.z.exe -Algorithm SHA256
# compare com o SHA256SUMS.txt anexado à release
```
```

## 9. Checklist de release (DoD)

- [ ] `CHANGELOG.md` atualizado e versão no `pyproject.toml` alinhada ao tag.
- [ ] `pytest` verde e `sopro-validate-glossary` sem erros.
- [ ] Catálogo com os modelos necessários `verified=true` (`08` §3).
- [ ] Build PyInstaller *onedir* gerado; smoke test em máquina **sem** Python; ícone do
      `.exe` conferido.
- [ ] Instalador Inno Setup gerado e testado (instalar, abrir, desinstalar); ícone do Setup e
      atalhos conferidos.
- [ ] Hotword validado no executável: “sopro” pausa e repete retoma; o bipe de pausa **não**
      reverte o estado.
- [ ] Assets + `SHA256SUMS.txt` publicados na release; `sha256sum -c SHA256SUMS.txt` verde.
- [ ] Matriz de compatibilidade (§2.3) verificada.
- [ ] README com seção de download apontando para a release.

## 10. Relação com os requisitos

| Requisito | Como este documento atende |
|---|---|
| RNF-07 (offline) | §1 e §3.2: modelos fora do binário; offline após o 1º download. |
| RNF-08 (instalador + modelos no 1º uso) | §1, §3.2 e §5. |
| RNF-09 (sem gravar áudio) | §1: nada muda no empacotamento. |
| RNF-12 (free tier/open source) | §4: assets e licenças; modelos MIT. |
| RF (download/atualização) | §4, §6 e §8: releases versionadas com download verificável. |
