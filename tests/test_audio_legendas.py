from pathlib import Path

import pytest

from conftest import mp3_falso
from montador import audio
from montador.legendas import (dividir_blocos, formatar_tempo_srt, gerar_srt, legendas_da_cena,
                               quebrar_linhas)
from montador.motores import Palavra


def test_duracao_mp3():
    assert audio.duracao_mp3(mp3_falso(3.0)) == pytest.approx(3.0, abs=0.03)


def test_duracao_mp3_com_id3_e_lixo():
    id3 = b"ID3\x03\x00\x00\x00\x00\x00\x0a" + bytes(10)
    assert audio.duracao_mp3(id3 + b"\x00\x01" + mp3_falso(2.0)) == pytest.approx(2.0, abs=0.03)


def test_mp3_invalido():
    with pytest.raises(audio.AudioErro):
        audio.duracao_mp3(b"isto nao e mp3")


def test_comando_ffmpeg_com_espacos_e_acentos():
    arquivos = [Path("C:/Meus Vídeos/cena_01.mp3"), Path("C:/Meus Vídeos/cena_02.mp3")]
    cmd = audio.comando_concatenar("ffmpeg", arquivos, Path("C:/Meus Vídeos/saída.mp3"), [2.8, 3.0])
    assert cmd.count("-i") == 2
    assert str(arquivos[0]) in cmd  # cada caminho é um argumento separado, sem aspas manuais
    filtro = cmd[cmd.index("-filter_complex") + 1]
    assert "apad=whole_dur=2.800,atrim=duration=2.800" in filtro
    assert "concat=n=2:v=0:a=1" in filtro


def test_blocos_e_linhas():
    texto = "Frase curta. " + " ".join(["longa"] * 30) + "."
    blocos = dividir_blocos(texto)
    assert blocos[0] == "Frase curta."
    assert all(len(b) <= 84 for b in blocos)
    assert " ".join(blocos) == texto
    assert "\n" in quebrar_linhas("uma linha bem comprida que passa de quarenta e dois caracteres")


def test_legendas_por_palavra():
    texto = "Olá mundo. Tudo bem?"
    palavras = [Palavra("Olá", 0.1, 0.4), Palavra("mundo", 0.5, 0.9),
                Palavra("Tudo", 2.0, 2.3), Palavra("bem", 2.4, 2.8)]
    legs, por_palavra = legendas_da_cena(texto, 10.0, 3.0, palavras)
    assert por_palavra
    assert [l.texto for l in legs] == ["Olá mundo.", "Tudo bem?"]
    assert legs[0].inicio == pytest.approx(10.1)
    assert legs[0].fim == pytest.approx(10.9)  # intervalo longo: não estende
    assert legs[1].inicio == pytest.approx(12.0)


def test_legendas_proporcionais_sem_tempos():
    legs, por_palavra = legendas_da_cena("Curta. Uma frase bem mais comprida.", 5.0, 7.0, None)
    assert not por_palavra
    assert legs[0].inicio == pytest.approx(5.0)
    assert legs[-1].fim == pytest.approx(12.0)
    # proporcional ao tamanho: a frase maior fica com mais tempo
    assert (legs[1].fim - legs[1].inicio) > (legs[0].fim - legs[0].inicio)


def test_legendas_caem_para_proporcional_se_palavras_nao_batem():
    legs, por_palavra = legendas_da_cena("Um. Dois.", 0, 2.0, [Palavra("xyz", 0, 1)])
    assert not por_palavra and len(legs) == 2


def test_formato_srt():
    assert formatar_tempo_srt(3723.456) == "01:02:03,456"
    from montador.legendas import Legenda
    srt = gerar_srt([Legenda(0, 1.5, "a"), Legenda(2, 3, "b")])
    assert srt.startswith("1\n00:00:00,000 --> 00:00:01,500\na\n\n2\n")
