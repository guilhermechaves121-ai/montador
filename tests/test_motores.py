import base64
import json

import pytest

from conftest import mp3_falso
from montador.config import ConfigVoz
from montador.motores import MotorErro, obter_motor
from montador.motores import azure, edge, elevenlabs


def test_obter_motor():
    assert obter_motor("edge-tts").nome == "edge"
    assert obter_motor("Azure").nome == "azure"
    assert obter_motor("elevenlabs").nome == "elevenlabs"
    with pytest.raises(MotorErro):
        obter_motor("outro")


def test_edge_simulado(monkeypatch):
    import edge_tts

    class ComunicadorFalso:
        def __init__(self, texto, voz, *, rate, pitch, boundary):
            assert (voz, rate, pitch, boundary) == ("pt-BR-AntonioNeural", "+10%", "-2Hz", "WordBoundary")

        async def stream(self):
            yield {"type": "WordBoundary", "offset": 1_000_000, "duration": 3_000_000, "text": "Olá"}
            yield {"type": "audio", "data": mp3_falso(1.0)}

    monkeypatch.setattr(edge_tts, "Communicate", ComunicadorFalso)
    cfg = ConfigVoz(voz="pt-BR-AntonioNeural", velocidade="+10%", tom="-2Hz")
    s = edge.MotorEdge().sintetizar("Olá", cfg)
    assert s.audio == mp3_falso(1.0)
    assert s.palavras[0].texto == "Olá"
    assert s.palavras[0].inicio == pytest.approx(0.1) and s.palavras[0].fim == pytest.approx(0.4)


def test_edge_sem_voz():
    with pytest.raises(MotorErro, match="voz"):
        edge.MotorEdge().sintetizar("x", ConfigVoz(voz=""))


def test_azure_simulado(monkeypatch):
    monkeypatch.setenv("AZURE_SPEECH_KEY", "chave-teste")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "brazilsouth")
    pedidos = {}

    def falso(url, **kw):
        pedidos.update(url=url, **kw)
        return b"MP3"

    monkeypatch.setattr(azure, "requisicao_http", falso)
    s = azure.MotorAzure().sintetizar("A & B <x>", ConfigVoz(motor="azure", voz="pt-BR-FranciscaNeural"))
    assert s.audio == b"MP3" and s.palavras is None
    assert pedidos["url"].startswith("https://brazilsouth.tts.speech.microsoft.com/")
    ssml = pedidos["corpo"].decode()
    assert "A &amp; B &lt;x&gt;" in ssml and "xml:lang=\"pt-BR\"" in ssml


def test_azure_sem_chave(monkeypatch):
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    with pytest.raises(MotorErro, match="AZURE_SPEECH_KEY"):
        azure.MotorAzure().sintetizar("x", ConfigVoz(voz="v"))


def test_elevenlabs_simulado(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "chave-teste")
    pedidos = {}

    def falso(url, **kw):
        pedidos.update(url=url, **kw)
        return {
            "audio_base64": base64.b64encode(b"MP3").decode(),
            "alignment": {
                "characters": list("Oi mar"),
                "character_start_times_seconds": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
                "character_end_times_seconds": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
            },
        }

    monkeypatch.setattr(elevenlabs, "json_http", falso)
    s = elevenlabs.MotorElevenLabs().sintetizar("Oi mar", ConfigVoz(voz="abc123", velocidade="+50%"))
    assert s.audio == b"MP3"
    assert [(p.texto, p.inicio, p.fim) for p in s.palavras] == [("Oi", 0.0, 0.2), ("mar", 0.3, 0.6)]
    corpo = json.loads(pedidos["corpo"])
    assert corpo["voice_settings"]["speed"] == 1.2  # limitado à faixa do ElevenLabs
    assert "/text-to-speech/abc123/with-timestamps" in pedidos["url"]


def test_listar_vozes_simulado(monkeypatch):
    import edge_tts

    async def vozes():
        return [{"ShortName": "pt-BR-AntonioNeural", "Locale": "pt-BR", "Gender": "Male"}]

    monkeypatch.setattr(edge_tts, "list_voices", vozes)
    assert edge.MotorEdge().listar_vozes()[0].nome == "pt-BR-AntonioNeural"
