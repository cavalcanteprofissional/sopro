"""Erros amigáveis (RNF-10): mensagens em pt-BR e degradação graciosa (docs/05 A9).

Traduz exceções conhecidas (áudio, STT, modelo, pacote, configuração) para uma
mensagem curta para o usuário e mostra um ``QMessageBox``. Nunca inclui conteúdo de
fala nas mensagens.
"""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget

DEFAULT_TITLE = "Sopro"

_HINTS: dict[str, str] = {
    "AudioUnavailable": (
        "Não foi possível acessar o áudio do sistema. Verifique se há um dispositivo "
        "de saída ativo e se o extra de áudio está instalado."
    ),
    "DeviceNotFound": (
        "O dispositivo de áudio selecionado não foi encontrado. Reconecte-o ou "
        "escolha outra fonte nas configurações."
    ),
    "ModelUnavailable": (
        "O modelo de transcrição não está disponível. Verifique a conexão e tente "
        "baixá-lo novamente."
    ),
    "RegistryError": (
        "Não foi possível ler o catálogo de modelos. Reinstale o Sopro se o problema "
        "persistir."
    ),
    "PackageError": (
        "O pacote de glossário é inválido ou está incompleto. Confira os arquivos "
        "manifest.json e terms.json."
    ),
    "ConfigError": (
        "Há uma configuração inválida. Abra as configurações e revise os campos."
    ),
    "STTError": (
        "A transcrição falhou. O Sopro continua escutando; tente novamente."
    ),
    "ImportError": (
        "Uma dependência opcional do Sopro não está instalada. Reinstale o "
        "aplicativo ou instale os extras necessários."
    ),
}


def friendly_message(exc: BaseException | str) -> str:
    """Devolve uma mensagem amigável para a exceção (ou o próprio texto)."""
    if isinstance(exc, str):
        return exc
    for klass in type(exc).__mro__:
        hint = _HINTS.get(klass.__name__)
        if hint:
            return hint
    return f"Ocorreu um erro inesperado: {exc}"


def show_error(
    message: BaseException | str,
    parent: QWidget | None = None,
    title: str = DEFAULT_TITLE,
) -> None:
    """Mostra uma mensagem de erro amigável sem derrubar o aplicativo."""
    QMessageBox.warning(parent, title, friendly_message(message))
