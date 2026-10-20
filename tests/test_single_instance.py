"""Testes da trava de instância única e do canal de ativação."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from sopro.app.single_instance import (  # noqa: E402
    SHOW_MESSAGE,
    ActivationServer,
    InstanceLock,
    instance_key,
    lock_path,
)


def test_instance_key_is_stable_and_mode_specific(tmp_path):
    first = instance_key(tmp_path)
    second = instance_key(tmp_path)

    assert first == second
    assert first != instance_key(tmp_path, demo=True)
    assert instance_key(tmp_path) != instance_key(tmp_path / "outro")
    assert lock_path(tmp_path).name == "sopro.lock"
    assert lock_path(tmp_path, demo=True).name == "sopro-demo.lock"


def test_only_one_instance_can_hold_the_lock(tmp_path):
    first = InstanceLock(tmp_path)
    second = InstanceLock(tmp_path)

    assert first.acquire() is True
    assert second.acquire() is False
    first.release()

    third = InstanceLock(tmp_path)
    assert third.acquire() is True
    third.release()


def test_notify_active_returns_false_without_server(tmp_path):
    assert InstanceLock(tmp_path).notify_active() is False


def test_activation_server_receives_message(tmp_path):
    from PySide6.QtNetwork import QLocalSocket
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication([])
    name = instance_key(tmp_path)
    server = ActivationServer(name)
    assert server.start() is True
    received: list[bool] = []
    server.activated.connect(lambda: received.append(True))

    client = QLocalSocket()
    client.connectToServer(name)
    assert client.state() == QLocalSocket.LocalSocketState.ConnectedState
    client.write(SHOW_MESSAGE)
    client.flush()
    QTest.qWait(200)
    QApplication.processEvents()

    assert received == [True]
    server.stop()
