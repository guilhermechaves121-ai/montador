"""Motor Azure Speech (API REST; exige AZURE_SPEECH_KEY e AZURE_SPEECH_REGION no .env)."""

from __future__ import annotations

import os
from xml.sax.saxutils import escape, quoteattr

from montador.config import ConfigVoz
from montador.motores import Motor, MotorErro, Sintese, Voz, com_tentativas, json_http, requisicao_http

FORMATO = "audio-24khz-48kbitrate-mono-mp3"


def _credenciais() -> tuple[str, str]:
    chave = os.environ.get("AZURE_SPEECH_KEY", "").strip()
    regiao = os.environ.get("AZURE_SPEECH_REGION", "").strip()
    if not chave or not regiao:
        raise MotorErro("Para usar o Azure, preencha AZURE_SPEECH_KEY e AZURE_SPEECH_REGION "
                        "no arquivo .env (veja o .env.exemplo).")
    return chave, regiao


def montar_ssml(texto: str, cfg: ConfigVoz) -> str:
    partes = cfg.voz.split("-")
    idioma = "-".join(partes[:2]) if len(partes) >= 2 else "en-US"
    return (
        f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang={quoteattr(idioma)}>"
        f"<voice name={quoteattr(cfg.voz)}>"
        f"<prosody rate={quoteattr(cfg.velocidade)} pitch={quoteattr(cfg.tom)}>{escape(texto)}</prosody>"
        "</voice></speak>"
    )


class MotorAzure(Motor):
    nome = "azure"

    def sintetizar(self, texto: str, cfg: ConfigVoz) -> Sintese:
        if not cfg.voz:
            raise MotorErro("Defina a 'voz' do canal no canais.yaml (ex.: pt-BR-FranciscaNeural).")
        chave, regiao = _credenciais()
        url = f"https://{regiao}.tts.speech.microsoft.com/cognitiveservices/v1"
        audio = com_tentativas(lambda: requisicao_http(
            url, metodo="POST", servico="Azure Speech",
            cabecalhos={
                "Ocp-Apim-Subscription-Key": chave,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": FORMATO,
            },
            corpo=montar_ssml(texto, cfg).encode("utf-8"),
        ))
        # A API REST não informa tempos por palavra: as legendas são distribuídas por frase.
        return Sintese(audio, None)

    def listar_vozes(self) -> list[Voz]:
        chave, regiao = _credenciais()
        url = f"https://{regiao}.tts.speech.microsoft.com/cognitiveservices/voices/list"
        dados = com_tentativas(lambda: json_http(
            url, servico="Azure Speech", cabecalhos={"Ocp-Apim-Subscription-Key": chave}))
        return [
            Voz(nome=v["ShortName"], idioma=v.get("Locale", ""), genero=v.get("Gender", ""),
                descricao=v.get("LocalName", ""))
            for v in dados
        ]
