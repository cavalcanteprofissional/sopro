"""Trava de instância única e ativação da janela já aberta.

A trava é um ``QLockFile`` na pasta de dados: a segunda execução não abre banco,
não carrega modelo e não cria bandeja — apenas avisa a instância existente para
trazer o hub para frente (via ``QLocalServer``) e encerra.

O modo ``--demo`` usa uma trava separada (decisão D4.2): a demonstração pode
rodar ao lado do app principal, mas não duplicada.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from PySide6.QtCore import QLockFile, QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

SHOW_MESSAGE = b"show"
ACK_MESSAGE = b"ok"
LOCK_FILENAME = "sopro.lock"
DEMO_LOCK_FILENAME = "sopro-demo.lock"


def instance_key(home: str | Path, demo: bool = False) -> str:
    """Nome estável (e específico do usuário/pasta) do canal de ativação."""
    mode = "demo" if demo else "app"
    resolved = str(Path(home).resolve())
    digest = hashlib.sha256(resolved.encode("utf-8")).hexdigest()[:16]
    return f"sopro-{mode}-{digest}"


def lock_path(home: str | Path, demo: bool = False) -> Path:
    return Path(home) / (DEMO_LOCK_FILENAME if demo else LOCK_FILENAME)


class InstanceLock:
    """Trava de instância única (pode ser usada antes do ``QApplication``)."""

    def __init__(self, home: str | Path, demo: bool = False) -> None:
        self.name = instance_key(home, demo)
        self._lock = QLockFile(str(lock_path(home, demo)))

    def acquire(self) -> bool:
        """Tenta adquirir a trava; ``True`` se esta é a instância principal."""
        return self._lock.tryLock(0)

    def release(self) -> None:
        self._lock.unlock()

    def notify_active(self) -> bool:
        """Pede à instância existente para mostrar o hub; ``False`` se sumiu."""
        socket = QLocalSocket()
        connected = False
        for _attempt in range(5):
            socket.connectToServer(self.name)
            if socket.waitForConnected(400):
                connected = True
                break
            socket.abort()
        if not connected:
            return False
        socket.write(SHOW_MESSAGE)
        socket.flush()
        socket.waitForBytesWritten(400)
        socket.waitForReadyRead(300)
        socket.disconnectFromServer()
        return True


class ActivationServer(QObject):
    """Escuta o canal local e emite ``activated`` quando outra instância chega."""

    activated = Signal()

    def __init__(self, name: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._name = name
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._accept)

    def start(self) -> bool:
        QLocalServer.removeServer(self._name)
        return self._server.listen(self._name)

    def stop(self) -> None:
        self._server.close()

    def _accept(self) -> None:
        while self._server.hasPendingConnections():
            connection = self._server.nextPendingConnection()
            connection.readyRead.connect(
                lambda conn=connection: self._read(conn)
            )
            connection.disconnected.connect(connection.deleteLater)
            if connection.bytesAvailable():
                self._read(connection)

    def _read(self, connection: QLocalSocket) -> None:
        if SHOW_MESSAGE in bytes(connection.readAll()):
            self.activated.emit()
            connection.write(ACK_MESSAGE)
            connection.flush()
