"""Duração de MP3 (sem dependências) e concatenação com ffmpeg."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

_BITRATES = {
    # (versão MPEG, camada) -> kbps por índice
    (1, 1): [0, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448],
    (1, 2): [0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384],
    (1, 3): [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320],
    (2, 1): [0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256],
    (2, 2): [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],
}
_BITRATES[(2, 3)] = _BITRATES[(2, 2)]
_TAXAS = {1: [44100, 48000, 32000], 2: [22050, 24000, 16000], 2.5: [11025, 12000, 8000]}


class AudioErro(Exception):
    pass


def _cabecalho(b: bytes):
    """Interpreta um cabeçalho de quadro MP3. Devolve (tamanho, amostras, taxa) ou None."""
    if len(b) < 4 or b[0] != 0xFF or (b[1] & 0xE0) != 0xE0:
        return None
    versao_bits = (b[1] >> 3) & 0b11
    camada_bits = (b[1] >> 1) & 0b11
    indice_br = (b[2] >> 4) & 0xF
    indice_taxa = (b[2] >> 2) & 0b11
    preenchimento = (b[2] >> 1) & 1
    if versao_bits == 1 or camada_bits == 0 or indice_br in (0, 15) or indice_taxa == 3:
        return None
    versao = {3: 1, 2: 2, 0: 2.5}[versao_bits]
    camada = {3: 1, 2: 2, 1: 3}[camada_bits]
    bitrate = _BITRATES[(1 if versao == 1 else 2, camada)][indice_br] * 1000
    taxa = _TAXAS[versao][indice_taxa]
    if camada == 1:
        amostras = 384
        tamanho = (12 * bitrate // taxa + preenchimento) * 4
    elif camada == 2 or versao == 1:
        amostras = 1152
        tamanho = 144 * bitrate // taxa + preenchimento
    else:
        amostras = 576
        tamanho = 72 * bitrate // taxa + preenchimento
    return tamanho, amostras, taxa


def _pular_id3(dados: bytes) -> int:
    if dados[:3] == b"ID3" and len(dados) >= 10:
        tamanho = 0
        for byte in dados[6:10]:
            tamanho = (tamanho << 7) | (byte & 0x7F)
        rodape = 10 if dados[5] & 0x10 else 0
        return 10 + tamanho + rodape
    return 0


def duracao_mp3(dados: bytes) -> float:
    """Duração em segundos de um MP3, somando os quadros (funciona sem ffmpeg)."""
    pos = _pular_id3(dados)
    total_amostras = 0
    taxa_final = 0
    quadros = 0
    fim = len(dados)
    while pos + 4 <= fim:
        info = _cabecalho(dados[pos:pos + 4])
        if info is None or info[0] <= 0:
            pos += 1  # procura o próximo quadro válido
            continue
        tamanho, amostras, taxa = info
        if quadros == 0:
            # Cabeçalho Xing/Info (VBR) informa o total de quadros; se existir, usa-o.
            trecho = dados[pos:pos + tamanho]
            for marca in (b"Xing", b"Info"):
                i = trecho.find(marca)
                if 0 < i < 40 and len(trecho) >= i + 12 and trecho[i + 7] & 1:
                    n = int.from_bytes(trecho[i + 8:i + 12], "big")
                    if n > 0:
                        return n * amostras / taxa
        total_amostras += amostras
        taxa_final = taxa
        quadros += 1
        pos += tamanho
    if not quadros:
        raise AudioErro("O arquivo de áudio recebido não é um MP3 válido.")
    return total_amostras / taxa_final


def duracao_arquivo(caminho: str | Path) -> float:
    return duracao_mp3(Path(caminho).read_bytes())


def encontrar_ffmpeg() -> str | None:
    caminho = shutil.which("ffmpeg")
    if caminho:
        return caminho
    # Locais comuns no Windows, caso o PATH não tenha sido configurado.
    candidatos = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "ffmpeg" / "bin" / "ffmpeg.exe",
        Path("C:/ffmpeg/bin/ffmpeg.exe"),
        Path(__file__).resolve().parent.parent / "ffmpeg" / "bin" / "ffmpeg.exe",
    ]
    for candidato in candidatos:
        if candidato.is_file():
            return str(candidato)
    return None


def comando_concatenar(ffmpeg: str, arquivos: list[Path], destino: Path,
                       segmentos: list[float]) -> list[str]:
    """Monta o comando do ffmpeg.

    `segmentos` é a duração exata (áudio + pausa) que cada cena ocupa na narração completa.
    Cada trecho é completado com silêncio e cortado nesse tamanho, para que a narração
    completa bata exatamente com a linha do tempo e as legendas.
    """
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
    for arquivo in arquivos:
        cmd += ["-i", str(arquivo)]
    filtros = []
    rotulos = []
    for i, dur in enumerate(segmentos):
        filtros.append(
            f"[{i}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=mono,"
            f"apad=whole_dur={dur:.3f},atrim=duration={dur:.3f}[a{i}]"
        )
        rotulos.append(f"[a{i}]")
    filtros.append("".join(rotulos) + f"concat=n={len(arquivos)}:v=0:a=1[saida]")
    cmd += ["-filter_complex", ";".join(filtros), "-map", "[saida]",
            "-c:a", "libmp3lame", "-b:a", "128k", str(destino)]
    return cmd


def concatenar(arquivos: list[Path], destino: Path, segmentos: list[float], ffmpeg: str) -> None:
    cmd = comando_concatenar(ffmpeg, arquivos, destino, segmentos)
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    resultado = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", creationflags=flags)
    if resultado.returncode != 0:
        raise AudioErro("O ffmpeg falhou ao juntar as cenas:\n" + (resultado.stderr or "").strip()[-800:])
