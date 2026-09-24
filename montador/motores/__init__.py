"""Motores de voz (TTS) intercambiáveis."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from montador.config import ConfigVoz, nome_motor


class MotorErro(Exception):
    """Falha ao gerar ou listar vozes, com mensagem pronta para o usuário."""


@dataclass
class Palavra:
    texto: str
    inicio: float  # segundos, relativos ao início do áudio da cena
    fim: float


@dataclass
class Sintese:
    audio: bytes
    palavras: list[Palavra] | None = None  # None quando o motor não informa tempos por palavra


@dataclass
class Voz:
    nome: str
    idioma: str = ""
    genero: str = ""
    descricao: str = ""
    extra: dict = field(default_factory=dict)


class Motor:
    nome = "base"

    def sintetizar(self, texto: str, cfg: ConfigVoz) -> Sintese:
        raise NotImplementedError

    def listar_vozes(self) -> list[Voz]:
        raise NotImplementedError


def obter_motor(nome: str) -> Motor:
    nome = nome_motor(nome)
    if nome == "edge":
        from montador.motores.edge import MotorEdge
        return MotorEdge()
    if nome == "azure":
        from montador.motores.azure import MotorAzure
        return MotorAzure()
    if nome == "elevenlabs":
        from montador.motores.elevenlabs import MotorElevenLabs
        return MotorElevenLabs()
    raise MotorErro(f"Motor de voz desconhecido: '{nome}'. Use edge, azure ou elevenlabs.")


NOMES_MOTORES = ["edge", "azure", "elevenlabs"]


def com_tentativas(funcao, tentativas: int = 3, espera: float = 2.0):
    """Repete chamadas de rede que falharam por instabilidade."""
    ultimo = None
    for n in range(tentativas):
        try:
            return funcao()
        except MotorErro:
            raise
        except Exception as erro:  # noqa: BLE001 - qualquer falha de rede merece nova tentativa
            ultimo = erro
            if n < tentativas - 1:
                time.sleep(espera * (n + 1))
    raise MotorErro(f"Falha de conexão com o serviço de voz ({type(ultimo).__name__}: {ultimo}).\n"
                    "Confira sua internet e tente de novo.")


def requisicao_http(url: str, *, metodo="GET", cabecalhos=None, corpo: bytes | None = None,
                    servico: str = "serviço de voz", timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, data=corpo, method=metodo, headers=cabecalhos or {})
    req.add_header("User-Agent", "montador")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as erro:
        detalhe = ""
        try:
            detalhe = erro.read().decode("utf-8", "replace")[:300]
        except Exception:  # noqa: BLE001
            pass
        if erro.code in (401, 403):
            raise MotorErro(f"{servico}: chave recusada (erro {erro.code}). "
                            "Confira a chave e a região no arquivo .env.") from erro
        if erro.code == 429:
            raise MotorErro(f"{servico}: limite de uso atingido (erro 429). "
                            "Aguarde um pouco ou confira seu plano.") from erro
        if 400 <= erro.code < 500:
            raise MotorErro(f"{servico}: pedido recusado (erro {erro.code}). "
                            f"Confira o nome da voz no canais.yaml. {detalhe}") from erro
        raise


def json_http(url: str, **kwargs):
    return json.loads(requisicao_http(url, **kwargs).decode("utf-8"))
