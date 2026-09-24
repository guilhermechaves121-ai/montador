"""Motor ElevenLabs (API REST; exige ELEVENLABS_API_KEY no .env)."""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.parse

from montador.config import ConfigVoz
from montador.motores import Motor, MotorErro, Palavra, Sintese, Voz, com_tentativas, json_http

API = "https://api.elevenlabs.io/v1"
MODELO_PADRAO = "eleven_multilingual_v2"


def _chave() -> str:
    chave = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not chave:
        raise MotorErro("Para usar o ElevenLabs, preencha ELEVENLABS_API_KEY no arquivo .env "
                        "(veja o .env.exemplo).")
    return chave


def velocidade_para_fator(velocidade: str) -> float:
    """Converte '+10%' em 1.1, dentro da faixa aceita pelo ElevenLabs (0,7 a 1,2)."""
    m = re.match(r"^([+-]?\d+(?:\.\d+)?)%$", velocidade.strip())
    fator = 1 + float(m.group(1)) / 100 if m else 1.0
    return round(min(1.2, max(0.7, fator)), 2)


def palavras_do_alinhamento(alinhamento: dict | None) -> list[Palavra] | None:
    if not alinhamento:
        return None
    letras = alinhamento.get("characters") or []
    inicios = alinhamento.get("character_start_times_seconds") or []
    fins = alinhamento.get("character_end_times_seconds") or []
    palavras: list[Palavra] = []
    atual, ini, fim = "", 0.0, 0.0
    for letra, i, f in zip(letras, inicios, fins):
        if letra.isspace():
            if atual:
                palavras.append(Palavra(atual, ini, fim))
                atual = ""
            continue
        if not atual:
            ini = i
        atual += letra
        fim = f
    if atual:
        palavras.append(Palavra(atual, ini, fim))
    return palavras or None


class MotorElevenLabs(Motor):
    nome = "elevenlabs"
    _avisou_tom = False

    def sintetizar(self, texto: str, cfg: ConfigVoz) -> Sintese:
        if not cfg.voz:
            raise MotorErro("Defina a 'voz' do canal no canais.yaml com o ID da voz do ElevenLabs "
                            "(use o comando de listar vozes para ver os IDs).")
        chave = _chave()
        if cfg.tom not in ("+0Hz", "-0Hz") and not self._avisou_tom:
            print("Aviso: o ElevenLabs não permite ajustar o tom; o valor de 'tom' será ignorado.")
            self._avisou_tom = True
        url = (f"{API}/text-to-speech/{urllib.parse.quote(cfg.voz)}/with-timestamps"
               "?output_format=mp3_44100_128")
        corpo = {
            "text": texto,
            "model_id": cfg.modelo or MODELO_PADRAO,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75,
                               "speed": velocidade_para_fator(cfg.velocidade)},
        }
        dados = com_tentativas(lambda: json_http(
            url, metodo="POST", servico="ElevenLabs",
            cabecalhos={"xi-api-key": chave, "Content-Type": "application/json"},
            corpo=json.dumps(corpo).encode("utf-8"),
        ))
        audio = base64.b64decode(dados.get("audio_base64", ""))
        if not audio:
            raise MotorErro("O ElevenLabs não devolveu áudio.")
        return Sintese(audio, palavras_do_alinhamento(dados.get("alignment")))

    def listar_vozes(self) -> list[Voz]:
        chave = _chave()
        dados = com_tentativas(lambda: json_http(
            f"{API}/voices", servico="ElevenLabs", cabecalhos={"xi-api-key": chave}))
        vozes = []
        for v in dados.get("voices", []):
            rotulos = v.get("labels") or {}
            vozes.append(Voz(
                nome=v["voice_id"],
                idioma=rotulos.get("language", "") or rotulos.get("accent", ""),
                genero=rotulos.get("gender", ""),
                descricao=v.get("name", ""),
            ))
        return vozes
