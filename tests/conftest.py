import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from montador.motores import Motor, Palavra, Sintese  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
QUADRO_SEG = 1152 / 44100  # duração de um quadro MP3 MPEG-1 camada III a 44,1 kHz


def mp3_falso(segundos: float) -> bytes:
    """MP3 válido (quadros de silêncio, 128 kbps, 44,1 kHz, mono) com a duração pedida."""
    cabecalho = bytes([0xFF, 0xFB, 0x90, 0xC4])
    quadro = cabecalho + bytes(417 - 4)
    n = max(1, round(segundos / QUADRO_SEG))
    return quadro * n


class MotorFalso(Motor):
    """Simula um motor de voz: 0,4 s por palavra, com ou sem tempos por palavra."""

    nome = "falso"

    def __init__(self, com_palavras=True, por_palavra=0.4):
        self.com_palavras = com_palavras
        self.por_palavra = por_palavra
        self.chamadas = []

    def sintetizar(self, texto, cfg):
        self.chamadas.append((texto, cfg))
        palavras = []
        t = 0.1
        for bruta in texto.split():
            limpa = bruta.strip(".,;:!?\"'()—-")
            if limpa:
                palavras.append(Palavra(limpa, t, t + self.por_palavra * 0.8))
            t += self.por_palavra
        duracao = t + 0.1
        return Sintese(mp3_falso(duracao), palavras if self.com_palavras else None)

    def listar_vozes(self):
        return []


@pytest.fixture
def motor_falso():
    return MotorFalso()


@pytest.fixture
def exemplo():
    return RAIZ / "exemplos" / "exemplo-paper-trail.md"


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    """Garante que nenhum teste acesse a internet."""
    import socket

    def bloqueado(*args, **kwargs):
        raise RuntimeError("teste tentou acessar a rede")

    monkeypatch.setattr(socket.socket, "connect", bloqueado)
    monkeypatch.setattr(socket, "create_connection", bloqueado)
