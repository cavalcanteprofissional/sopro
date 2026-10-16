"""Camada de plataforma para áudio: captura concreta por sistema operacional.

O núcleo (`sopro.core.audio`) define apenas contratos; aqui ficam as amarras a
bibliotecas nativas/pesadas (hoje PyAudioWPatch no Windows), importadas de forma
preguiçosa para não quebrar quando o extra ``audio`` não está instalado.
"""

from sopro.platform.audio.windows import WindowsAudioSource

__all__ = ["WindowsAudioSource"]
