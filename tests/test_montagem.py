import csv
import datetime as dt
import subprocess

import pytest

from conftest import MotorFalso
from montador import audio, cli
from montador.config import ConfigVoz
from montador.montagem import montar
from montador.roteiro import ler_roteiro

DATA = dt.date(2026, 1, 15)


def _montar(exemplo, tmp_path, motor, ffmpeg=None, pausa=0.8):
    r = ler_roteiro(exemplo)
    cfg = ConfigVoz(voz="en-US-AndrewNeural", pausa=pausa)
    return montar(r, cfg, tmp_path / "episódios com espaço", motor=motor, data=DATA,
                  ffmpeg=ffmpeg, progresso=lambda *_: None)


def test_estrutura_de_saida_sem_ffmpeg(exemplo, tmp_path, motor_falso):
    res = _montar(exemplo, tmp_path, motor_falso)
    pasta = res.pasta
    assert pasta == tmp_path / "episódios com espaço" / "paper-trail" / "2026-01-15_the-lost-ledger"
    for nome in ("audio/cena_01.mp3", "audio/cena_02.mp3", "audio/cena_03.mp3",
                 "legendas.srt", "linha_do_tempo.csv", "checklist.md"):
        assert (pasta / nome).is_file(), nome
    for vazia in ("imagens", "export"):
        assert (pasta / vazia).is_dir() and not any((pasta / vazia).iterdir())
    assert not (pasta / "narracao_completa.mp3").exists()
    assert res.narracao_completa is None
    assert any("ffmpeg" in a for a in res.avisos)
    # o texto enviado ao motor é exatamente o do roteiro
    assert [t for t, _ in motor_falso.chamadas] == [c.narracao for c in ler_roteiro(exemplo).cenas]


def test_linha_do_tempo_considera_pausa(exemplo, tmp_path, motor_falso):
    res = _montar(exemplo, tmp_path, motor_falso, pausa=0.8)
    t = res.trechos
    assert t[0].inicio == 0
    assert t[1].inicio == pytest.approx(t[0].fim + 0.8)
    assert t[2].inicio == pytest.approx(t[1].fim + 0.8)
    with (res.pasta / "linha_do_tempo.csv").open(encoding="utf-8-sig", newline="") as f:
        linhas = list(csv.reader(f, delimiter=";"))
    assert linhas[0] == ["cena", "inicio", "fim", "duracao", "termo_busca", "texto_tela"]
    assert linhas[1][0] == "1" and linhas[1][1] == "00:00:00.000"
    assert linhas[1][4] == "old shipping office ledger" and linhas[1][5] == "The Lost Ledger"
    assert linhas[2][5] == ""  # TELA: - fica vazio
    checklist = (res.pasta / "checklist.md").read_text(encoding="utf-8")
    assert "archive boxes documents" in checklist and "[ ]" in checklist


def test_legendas_sincronizadas_com_cenas(exemplo, tmp_path, motor_falso):
    res = _montar(exemplo, tmp_path, motor_falso)
    assert res.cenas_sem_tempo_por_palavra == []
    inicio_cena2 = res.trechos[1].inicio
    primeira_da_cena2 = next(l for l in res.legendas if l.texto.startswith("The missing"))
    assert primeira_da_cena2.inicio == pytest.approx(inicio_cena2 + 0.1, abs=0.01)
    inicios = [l.inicio for l in res.legendas]
    assert inicios == sorted(inicios)
    assert all(l.fim > l.inicio for l in res.legendas)
    assert res.legendas[-1].fim <= res.trechos[-1].fim + 0.01
    srt = (res.pasta / "legendas.srt").read_text(encoding="utf-8")
    assert srt.startswith("1\n00:00:00,100 --> ")


def test_legendas_sem_tempo_por_palavra(exemplo, tmp_path):
    res = _montar(exemplo, tmp_path, MotorFalso(com_palavras=False))
    assert res.cenas_sem_tempo_por_palavra == [1, 2, 3]
    por_cena2 = [l for l in res.legendas if res.trechos[1].inicio <= l.inicio < res.trechos[1].fim]
    assert por_cena2[0].inicio == pytest.approx(res.trechos[1].inicio)
    assert por_cena2[-1].fim == pytest.approx(res.trechos[1].fim)


def test_concatena_com_ffmpeg_simulado(exemplo, tmp_path, motor_falso, monkeypatch):
    chamadas = []

    def falso_run(cmd, **kwargs):
        chamadas.append(cmd)
        open(cmd[-1], "wb").write(b"mp3")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", falso_run)
    res = _montar(exemplo, tmp_path, motor_falso, ffmpeg="ffmpeg", pausa=1.0)
    assert res.narracao_completa == res.pasta / "narracao_completa.mp3"
    assert res.narracao_completa.is_file() and not res.avisos
    filtro = chamadas[0][chamadas[0].index("-filter_complex") + 1]
    seg1 = res.trechos[1].inicio - res.trechos[0].inicio
    assert f"whole_dur={seg1:.3f}" in filtro


def test_erro_do_ffmpeg_vira_mensagem(exemplo, tmp_path, motor_falso, monkeypatch):
    monkeypatch.setattr(subprocess, "run",
                        lambda cmd, **k: subprocess.CompletedProcess(cmd, 1, "", "falhou feio"))
    with pytest.raises(audio.AudioErro, match="falhou feio"):
        _montar(exemplo, tmp_path, motor_falso, ffmpeg="ffmpeg")


@pytest.mark.skipif(not audio.encontrar_ffmpeg(), reason="ffmpeg não instalado")
def test_ffmpeg_real(exemplo, tmp_path, motor_falso):
    res = _montar(exemplo, tmp_path, motor_falso, ffmpeg=True)
    assert res.narracao_completa.stat().st_size > 0


def test_cli_montar(exemplo, tmp_path, monkeypatch, capsys):
    motor = MotorFalso()
    monkeypatch.setattr("montador.montagem.obter_motor", lambda nome: motor)
    monkeypatch.setattr(audio, "encontrar_ffmpeg", lambda: None)
    codigo = cli.main(["montar", f'"{exemplo}"', "--saida", str(tmp_path), "--data", "2026-01-15",
                       "--sim"])
    saida = capsys.readouterr().out
    assert codigo == 0
    assert "ETAPA 1" in saida and "Cena 3" in saida and "Pronto!" in saida
    assert (tmp_path / "paper-trail" / "2026-01-15_the-lost-ledger" / "legendas.srt").is_file()


def test_cli_validar(exemplo, capsys):
    assert cli.main(["validar", str(exemplo)]) == 0
    assert "frase com" in capsys.readouterr().out


def test_cli_erro_amigavel(tmp_path, capsys):
    assert cli.main(["validar", str(tmp_path / "nao existe.md")]) == 1
    assert "ERRO" in capsys.readouterr().err


def test_cli_vozes_sem_chave(monkeypatch, capsys):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    assert cli.main(["vozes", "elevenlabs"]) == 1
    assert "ELEVENLABS_API_KEY" in capsys.readouterr().out
