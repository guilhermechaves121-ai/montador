"""Montagem do episódio: áudio por cena, narração completa, legendas, linha do tempo e checklist."""

from __future__ import annotations

import csv
import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

from montador import audio
from montador.config import ConfigVoz
from montador.legendas import Legenda, legendas_da_cena, salvar_srt
from montador.motores import Motor, obter_motor
from montador.roteiro import Cena, Roteiro, nome_seguro


@dataclass
class TrechoCena:
    cena: Cena
    arquivo: Path
    inicio: float
    duracao: float

    @property
    def fim(self) -> float:
        return self.inicio + self.duracao


@dataclass
class Resultado:
    pasta: Path
    trechos: list[TrechoCena]
    narracao_completa: Path | None
    legendas: list[Legenda]
    cenas_sem_tempo_por_palavra: list[int] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


def formatar_tempo(segundos: float) -> str:
    ms = int(round(max(0.0, segundos) * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def pasta_do_episodio(roteiro: Roteiro, base: Path, data: dt.date | None = None) -> Path:
    data = data or dt.date.today()
    return (Path(base) / nome_seguro(roteiro.canal)
            / f"{data:%Y-%m-%d}_{nome_seguro(roteiro.episodio)}")


def salvar_linha_do_tempo(trechos: list[TrechoCena], caminho: Path) -> None:
    # utf-8 com BOM e ponto e vírgula: abre certo no Excel em português.
    with caminho.open("w", encoding="utf-8-sig", newline="") as arq:
        escritor = csv.writer(arq, delimiter=";")
        escritor.writerow(["cena", "inicio", "fim", "duracao", "termo_busca", "texto_tela"])
        for t in trechos:
            escritor.writerow([
                t.cena.numero, formatar_tempo(t.inicio), formatar_tempo(t.fim),
                formatar_tempo(t.duracao), t.cena.imagem, t.cena.tela if t.cena.tem_tela else "",
            ])


def gerar_checklist(roteiro: Roteiro, trechos: list[TrechoCena], tem_narracao_completa: bool) -> str:
    linhas = [
        f"# Checklist — {roteiro.episodio}",
        "",
        f"Canal: **{roteiro.canal}** · {len(trechos)} cenas · duração total "
        f"{formatar_tempo(trechos[-1].fim if trechos else 0)}",
        "",
        "## Cenas",
        "",
        "| Feito | Cena | Início | Fim | Duração | Termo de busca | Texto na tela |",
        "|---|---|---|---|---|---|---|",
    ]
    for t in trechos:
        tela = t.cena.tela if t.cena.tem_tela else "—"
        imagem = t.cena.imagem or "—"
        linhas.append(
            f"| [ ] | {t.cena.numero} | {formatar_tempo(t.inicio)} | {formatar_tempo(t.fim)} | "
            f"{formatar_tempo(t.duracao)} | {imagem.replace('|', '/')} | {tela.replace('|', '/')} |"
        )
    audio_final = "narracao_completa.mp3" if tem_narracao_completa else "os arquivos de audio/ em sequência"
    linhas += [
        "",
        "## Montagem",
        "",
        "- [ ] Baixar as imagens de cada cena para a pasta `imagens/` (nomeie como `cena_01...`)",
        f"- [ ] Importar {audio_final} no editor de vídeo",
        "- [ ] Posicionar as imagens conforme os tempos acima (ou `linha_do_tempo.csv`)",
        "- [ ] Adicionar os textos de tela",
        "- [ ] Importar `legendas.srt` e revisar",
        "- [ ] Exportar o vídeo final para a pasta `export/`",
        "",
    ]
    return "\n".join(linhas)


def montar(roteiro: Roteiro, cfg: ConfigVoz, base: Path, *, motor: Motor | None = None,
           data: dt.date | None = None, ffmpeg: str | None | bool = True,
           progresso=print) -> Resultado:
    """Gera todos os arquivos do episódio.

    `ffmpeg=True` procura o ffmpeg automaticamente; `None`/`False` desativa; texto = caminho.
    """
    motor = motor or obter_motor(cfg.motor)
    pasta = pasta_do_episodio(roteiro, base, data)
    pasta_audio = pasta / "audio"
    for sub in (pasta_audio, pasta / "imagens", pasta / "export"):
        sub.mkdir(parents=True, exist_ok=True)
    for antigo in pasta_audio.glob("cena_*.mp3"):
        antigo.unlink()  # evita sobrar cenas de uma montagem anterior com mais cenas

    trechos: list[TrechoCena] = []
    legendas: list[Legenda] = []
    sem_tempo: list[int] = []
    inicio = 0.0
    total = len(roteiro.cenas)
    for n, cena in enumerate(roteiro.cenas, start=1):
        progresso(f"[{n}/{total}] Gerando narração da cena {cena.numero}...")
        sintese = motor.sintetizar(cena.narracao, cfg)
        arquivo = pasta_audio / f"cena_{n:02d}.mp3"
        arquivo.write_bytes(sintese.audio)
        duracao = audio.duracao_mp3(sintese.audio)
        trechos.append(TrechoCena(cena, arquivo, inicio, duracao))
        leg, por_palavra = legendas_da_cena(cena.narracao, inicio, duracao, sintese.palavras)
        legendas.extend(leg)
        if not por_palavra:
            sem_tempo.append(cena.numero)
        inicio += duracao + (cfg.pausa if n < total else 0)

    avisos: list[str] = []
    caminho_ffmpeg = audio.encontrar_ffmpeg() if ffmpeg is True else (ffmpeg or None)
    completa: Path | None = None
    if caminho_ffmpeg:
        progresso("Juntando as cenas em narracao_completa.mp3...")
        completa = pasta / "narracao_completa.mp3"
        segmentos = [
            (trechos[i + 1].inicio - t.inicio) if i + 1 < len(trechos) else t.duracao
            for i, t in enumerate(trechos)
        ]
        audio.concatenar([t.arquivo for t in trechos], completa, segmentos, caminho_ffmpeg)
    else:
        avisos.append(
            "ffmpeg não encontrado: a narracao_completa.mp3 NÃO foi gerada, só os áudios das cenas. "
            "Instale o ffmpeg (veja o README) e rode de novo. As legendas e a linha do tempo já "
            f"consideram as cenas em sequência com pausa de {cfg.pausa:g} s."
        )

    salvar_srt(legendas, pasta / "legendas.srt")
    salvar_linha_do_tempo(trechos, pasta / "linha_do_tempo.csv")
    (pasta / "checklist.md").write_text(
        gerar_checklist(roteiro, trechos, completa is not None), encoding="utf-8")

    return Resultado(pasta, trechos, completa, legendas, sem_tempo, avisos)
