"""Provedor STT via Groq (opcional; docs/02 §5, docs/05 A8).

Envia áudio para o endpoint OpenAI-compatível de transcrição da Groq. Para respeitar
a **cobrança mínima de ~10 s por requisição**, acumula segmentos do VAD numa fonte
até atingir o mínimo (ou o máximo) e só então transcreve o áudio combinado — aceitando
latência maior. Erros de rede/limite viram exceções tipadas (``STTRateLimited`` etc.)
para o orquestrador cair ao provedor local.

A chave vem do cofre do SO e **nunca** entra em log. ``opener``/``sleep`` são
injetáveis para testes.
"""

from __future__ import annotations

import io
import json
import socket
import urllib.error
import urllib.request
import uuid
import wave
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sopro.core.stt import (
    AudioSegment,
    STTRateLimited,
    STTProvider,
    STTTimeout,
    STTUnavailable,
    Transcript,
)

GROQ_TRANSCRIBE_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
DEFAULT_MODEL = "whisper-large-v3"
MIN_SEGMENT_SECONDS = 10.0
MAX_SEGMENT_SECONDS = 30.0

Opener = Callable[..., Any]


@dataclass
class _Buffer:
    """Áudio acumulado de uma fonte à espera de atingir o mínimo de duração."""

    start_ms: int
    sample_rate: int
    chunks: list[bytes] = field(default_factory=list)

    @property
    def samples(self) -> int:
        return sum(len(chunk) for chunk in self.chunks) // 2

    @property
    def duration_s(self) -> float:
        return self.samples / self.sample_rate if self.sample_rate else 0.0

    @property
    def duration_ms(self) -> int:
        return int(self.duration_s * 1000)


class GroqSTTProvider(STTProvider):
    """Cliente de transcrição da Groq com agrupamento de segmentos."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_MODEL,
        language: str = "en",
        min_seconds: float = MIN_SEGMENT_SECONDS,
        max_seconds: float = MAX_SEGMENT_SECONDS,
        timeout: float = 60.0,
        opener: Opener | None = None,
    ) -> None:
        if not api_key:
            raise STTUnavailable("chave da Groq ausente")
        self._api_key = api_key
        self._model = model or DEFAULT_MODEL
        self._language = language
        self._min_seconds = min_seconds
        self._max_seconds = max_seconds
        self._timeout = timeout
        self._opener: Opener = opener or urllib.request.urlopen
        self._buffers: dict[str, _Buffer] = {}
        self._offsets: dict[str, int] = {}
        self._ready = False

    def warmup(self) -> None:
        self._ready = True

    def close(self) -> None:
        self._buffers.clear()
        self._offsets.clear()
        self._ready = False

    def transcribe(self, segment: AudioSegment) -> Transcript:
        buffer = self._buffers.get(segment.source)
        if buffer is None:
            buffer = _Buffer(
                start_ms=self._offsets.get(segment.source, 0),
                sample_rate=segment.sample_rate,
            )
            self._buffers[segment.source] = buffer
        buffer.chunks.append(segment.pcm)
        if buffer.duration_s < self._min_seconds and buffer.duration_s < self._max_seconds:
            return Transcript(
                text="",
                start_ms=buffer.start_ms + buffer.duration_ms,
                end_ms=buffer.start_ms + buffer.duration_ms,
                source=segment.source,
            )

        pcm = b"".join(buffer.chunks)
        start_ms = buffer.start_ms
        end_ms = start_ms + buffer.duration_ms
        self._offsets[segment.source] = end_ms
        buffer.chunks.clear()
        text = self._request(pcm, segment)
        return Transcript(
            text=text, start_ms=start_ms, end_ms=end_ms, source=segment.source
        )

    def _request(self, pcm: bytes, segment: AudioSegment) -> str:
        wav = _to_wav(pcm, segment.sample_rate)
        hints = ", ".join(segment.vocabulary_hint)
        body, content_type = _multipart(
            fields={
                "model": self._model,
                "language": segment.language or self._language,
                "response_format": "json",
                "prompt": hints,
            },
            filename="audio.wav",
            file_bytes=wav,
        )
        request = urllib.request.Request(
            GROQ_TRANSCRIBE_URL,
            data=body,
            headers={
                "Content-Type": content_type,
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )
        try:
            with self._opener(request, timeout=self._timeout) as response:
                payload = response.read()
        except socket.timeout as exc:
            raise STTTimeout("Groq: tempo esgotado na transcrição") from exc
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                raise STTRateLimited("Groq: limite de taxa atingido") from exc
            raise STTUnavailable(f"Groq: HTTP {exc.code}") from exc
        except Exception as exc:  # noqa: BLE001 - rede vira erro tipado
            raise STTUnavailable(f"Groq: falha de rede ({exc})") from exc
        try:
            text = json.loads(payload).get("text", "")
        except (ValueError, AttributeError) as exc:
            raise STTUnavailable(f"Groq: resposta inesperada ({exc})") from exc
        return str(text)


def _to_wav(pcm: bytes, sample_rate: int) -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm)
    return out.getvalue()


def _multipart(
    *, fields: dict[str, str], filename: str, file_bytes: bytes
) -> tuple[bytes, str]:
    boundary = f"----sopro{uuid.uuid4().hex}"
    parts: list[bytes] = []
    for name, value in fields.items():
        if not value:
            continue
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        parts.append(f"{value}\r\n".encode())
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode()
    )
    parts.append(b"Content-Type: audio/wav\r\n\r\n")
    parts.append(file_bytes)
    parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"
