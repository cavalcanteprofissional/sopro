# -*- mode: python ; coding: utf-8 -*-
"""Build do Sopro em modo *onedir* (docs/09 §3.1–§3.2).

Embutimos o código, os dados (catálogo de modelos + pacotes de domínio) e as
dependências nativas. Os **modelos** ficam de fora: são baixados no primeiro uso
com verificação de sha256 (docs/08 §3–§4).
"""

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_dynamic_libs

DATAS = [
    ("data/models.json", "data"),
    ("data/domains", "data/domains"),
    ("src/sopro/platform/popup/assets", "sopro/platform/popup/assets"),
]
BINARIES = []
HIDDENIMPORTS = []

# Dependências com importação dinâmica (DLLs/criptografias que o analisador não vê).
NATIVE_PACKAGES = (
    "faster_whisper",
    "ctranslate2",
    "tokenizers",
    "onnxruntime",
    "av",
    "pyaudiowpatch",
    "openwakeword",
    "numpy",
)
for _package in NATIVE_PACKAGES:
    try:
        _datas, _binaries, _hidden = collect_all(_package)
    except Exception:
        continue
    DATAS += _datas
    BINARIES += _binaries
    HIDDENIMPORTS += _hidden

for _package in ("ctranslate2", "onnxruntime"):
    BINARIES += collect_dynamic_libs(_package)

DATAS += collect_data_files("PySide6", includes=["**/translations/*.qm"])

a = Analysis(
    ["src/sopro/app/__main__.py"],
    pathex=["src"],
    datas=DATAS,
    binaries=BINARIES,
    hiddenimports=HIDDENIMPORTS,
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
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="Sopro",
)
