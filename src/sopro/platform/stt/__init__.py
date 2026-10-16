"""Camada de plataforma para transcrição: bindings concretos de engine.

O núcleo (`sopro.core.stt`) define apenas contratos; aqui ficam as amarras a
bibliotecas nativas/pesadas, importadas de forma preguiçosa para não pesar o
import do pacote nem quebrar quando o extra não está instalado.
"""
