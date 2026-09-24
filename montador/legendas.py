"""Geração de legendas .srt sincronizadas com a narração completa."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from montador.motores import Palavra
from montador.validacao import dividir_frases

MAX_CARACTERES = 84  # por legenda (duas linhas de ~42)
MAX_LINHA = 42


@dataclass
class Legenda:
    inicio: float
    fim: float
    texto: str


def dividir_blocos(texto: str, maximo: int = MAX_CARACTERES) -> list[str]:
    """Divide a narração em frases e, se preciso, frases longas em blocos de até `maximo` caracteres."""
    blocos: list[str] = []
    for frase in dividir_frases(texto):
        atual = ""
        for palavra in frase.split():
            candidato = f"{atual} {palavra}".strip()
            if len(candidato) > maximo and atual:
                blocos.append(atual)
                atual = palavra
            else:
                atual = candidato
        if atual:
            blocos.append(atual)
    return blocos


def quebrar_linhas(texto: str, maximo: int = MAX_LINHA) -> str:
    if len(texto) <= maximo:
        return texto
    meio = len(texto) // 2
    espacos = [i for i, c in enumerate(texto) if c == " "]
    if not espacos:
        return texto
    corte = min(espacos, key=lambda i: abs(i - meio))
    return texto[:corte] + "\n" + texto[corte + 1:]


def _tempos_por_palavra(texto: str, blocos: list[str], palavras: list[Palavra]):
    """Localiza cada palavra informada pelo motor no texto e devolve (início, fim) por bloco."""
    # posição de cada bloco no texto original
    faixas = []
    pos = 0
    for bloco in blocos:
        primeira = bloco.split()[0]
        ini = texto.find(primeira, pos)
        if ini < 0:
            return None
        faixas.append(ini)
        pos = ini + 1
    faixas.append(len(texto) + 1)

    texto_min = texto.lower()
    localizadas = []
    pos = 0
    for palavra in palavras:
        alvo = palavra.texto.strip().lower()
        if not alvo:
            continue
        idx = texto_min.find(alvo, pos)
        if idx < 0 or idx - pos > 80:
            # Palavra não encontrada logo adiante (ex.: número lido por extenso); ignora.
            continue
        localizadas.append((idx, palavra))
        pos = idx + len(alvo)

    tempos = []
    for n in range(len(blocos)):
        dentro = [p for idx, p in localizadas if faixas[n] <= idx < faixas[n + 1]]
        if not dentro:
            return None
        tempos.append((dentro[0].inicio, dentro[-1].fim))
    return tempos


def _tempos_proporcionais(blocos: list[str], duracao: float):
    total = sum(len(b) for b in blocos) or 1
    tempos = []
    t = 0.0
    for bloco in blocos:
        dur = duracao * len(bloco) / total
        tempos.append((t, t + dur))
        t += dur
    return tempos


def legendas_da_cena(texto: str, inicio_cena: float, duracao: float,
                     palavras: list[Palavra] | None) -> tuple[list[Legenda], bool]:
    """Devolve as legendas da cena e se foram sincronizadas por palavra."""
    blocos = dividir_blocos(texto)
    if not blocos:
        return [], False
    tempos = _tempos_por_palavra(texto, blocos, palavras) if palavras else None
    por_palavra = tempos is not None
    if tempos is None:
        tempos = _tempos_proporcionais(blocos, duracao)
    else:
        # Estende cada legenda até a próxima quando o intervalo for curto (leitura mais confortável).
        ajustados = []
        for n, (ini, fim) in enumerate(tempos):
            proximo = tempos[n + 1][0] if n + 1 < len(tempos) else min(duracao, fim + 0.5)
            if proximo - fim < 1.0:
                fim = max(fim, proximo)
            ajustados.append((ini, fim))
        tempos = ajustados
    legendas = []
    for bloco, (ini, fim) in zip(blocos, tempos):
        ini = max(0.0, min(ini, duracao))
        fim = max(ini + 0.1, min(fim, duracao))
        legendas.append(Legenda(inicio_cena + ini, inicio_cena + fim, quebrar_linhas(bloco)))
    return legendas, por_palavra


def formatar_tempo_srt(segundos: float) -> str:
    ms = int(round(max(0.0, segundos) * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def gerar_srt(legendas: list[Legenda]) -> str:
    partes = []
    for n, leg in enumerate(legendas, start=1):
        partes.append(f"{n}\n{formatar_tempo_srt(leg.inicio)} --> {formatar_tempo_srt(leg.fim)}\n{leg.texto}\n")
    return "\n".join(partes)


def salvar_srt(legendas: list[Legenda], caminho: Path) -> None:
    caminho.write_text(gerar_srt(legendas), encoding="utf-8")
