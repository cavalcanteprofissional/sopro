"""Host de diálogo que delega atributos para uma página embutida.

As telas de Configurações e Glossários foram divididas em *páginas* reutilizáveis
(usadas também no hub) e *diálogos* finos que apenas hospedam uma página. Este host
mantém a compatibilidade da API antiga: acessar/atribuir atributos no diálogo
(``dialog._list``, ``dialog._choose``, ``dialog.commit()``) recai sobre a página.
"""

from __future__ import annotations

from PySide6.QtWidgets import QDialog


class PageHost(QDialog):
    """Diálogo que reencaminha atributos desconhecidos para ``self._page``."""

    _page = None

    def __getattr__(self, name: str):
        page = self.__dict__.get("_page")
        if page is not None:
            try:
                return getattr(page, name)
            except AttributeError:
                pass
        raise AttributeError(name)

    def __setattr__(self, name: str, value) -> None:
        if name != "_page":
            page = self.__dict__.get("_page")
            if page is not None and hasattr(page, name):
                setattr(page, name, value)
                return
        super().__setattr__(name, value)
