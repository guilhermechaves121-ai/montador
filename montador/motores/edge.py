"""Motor edge-tts (gratuito, sem chave)."""

from __future__ import annotations

import asyncio

from montador.config import ConfigVoz
from montador.motores import Motor, MotorErro, Palavra, Sintese, Voz, com_tentativas

_TICKS_POR_SEGUNDO = 10_000_000  # o edge-tts informa tempos em unidades de 100 ns


def _importar():
    try:
        import edge_tts
    except ImportError as erro:
        raise MotorErro("O pacote edge-tts não está instalado. Rode o instalar.bat de novo.") from erro
    return edge_tts


class MotorEdge(Motor):
    nome = "edge"

    def sintetizar(self, texto: str, cfg: ConfigVoz) -> Sintese:
        if not cfg.voz:
            raise MotorErro("Defina a 'voz' do canal no canais.yaml (ex.: pt-BR-AntonioNeural).")
        edge_tts = _importar()

        async def gerar() -> Sintese:
            comunicador = edge_tts.Communicate(
                texto, cfg.voz, rate=cfg.velocidade, pitch=cfg.tom, boundary="WordBoundary"
            )
            audio = bytearray()
            palavras: list[Palavra] = []
            async for parte in comunicador.stream():
                if parte["type"] == "audio":
                    audio.extend(parte["data"])
                elif parte["type"] == "WordBoundary":
                    inicio = parte["offset"] / _TICKS_POR_SEGUNDO
                    fim = inicio + parte["duration"] / _TICKS_POR_SEGUNDO
                    palavras.append(Palavra(parte["text"], inicio, fim))
            if not audio:
                raise MotorErro(f"O edge-tts não devolveu áudio. Confira se a voz '{cfg.voz}' existe "
                                "(use o comando de listar vozes).")
            return Sintese(bytes(audio), palavras or None)

        def executar():
            try:
                return asyncio.run(gerar())
            except edge_tts.exceptions.NoAudioReceived as erro:
                raise MotorErro(f"O edge-tts não devolveu áudio. Confira se a voz '{cfg.voz}' existe "
                                "(use o comando de listar vozes).") from erro
            except ValueError as erro:
                raise MotorErro(f"Configuração inválida para o edge-tts: {erro}\n"
                                "Velocidade deve ser como '+10%' e tom como '-5Hz'.") from erro

        return com_tentativas(executar)

    def listar_vozes(self) -> list[Voz]:
        edge_tts = _importar()
        vozes = com_tentativas(lambda: asyncio.run(edge_tts.list_voices()))
        return [
            Voz(nome=v["ShortName"], idioma=v.get("Locale", ""), genero=v.get("Gender", ""),
                descricao=v.get("FriendlyName", ""))
            for v in vozes
        ]
