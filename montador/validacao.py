"""Aponta trechos da narração que os motores de voz costumam ler errado.

Só avisa: o texto do roteiro nunca é alterado.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from montador.roteiro import Roteiro

LIMITE_PALAVRAS = 25

ABREVIACOES = [
    # português
    "art", "arts", "inc", "dr", "dra", "drs", "sr", "sra", "srta", "prof", "profa",
    "pág", "págs", "pag", "p", "pp", "cap", "caps", "vol", "ed", "av", "tel",
    "etc", "ex", "obs", "séc", "sec", "min", "máx", "max", "aprox", "núm", "num",
    "cia", "ltda", "gov", "jr",
    # inglês
    "mr", "mrs", "ms", "st", "vs", "no", "approx", "dept", "est", "fig",
    "e.g", "i.e", "u.s", "u.k", "a.m", "p.m",
]
_ABREV_RE = re.compile(
    r"(?<![\w.])(?:" + "|".join(re.escape(a) for a in sorted(ABREVIACOES, key=len, reverse=True))
    + r")\.(?=\s|$|[,;:)])",
    re.IGNORECASE,
)
# nº, n°, n.º, Nº etc. (não precisam de ponto final)
_ORDINAL_RE = re.compile(r"(?<!\w)n\.?\s?[º°](?!\w)", re.IGNORECASE)
_ALGARISMOS_RE = re.compile(r"\d+(?:[.,:/]\d+)*")
SIMBOLOS = "§%&$€£#@*/+=°º ª~<>|^_\\"
_SIMBOLOS_RE = re.compile("[" + re.escape(SIMBOLOS.replace(" ", "")) + "]")
_SIGLA_RE = re.compile(r"(?<![\w])[A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ0-9.&-]*[A-ZÀ-ÖØ-Þ0-9](?![\w])")
_FRASE_RE = re.compile(r"[^.!?…]+(?:[.!?…]+[\"'”’»)\]]*|$)")


@dataclass
class Aviso:
    cena: int
    tipo: str
    trecho: str
    mensagem: str

    def __str__(self) -> str:
        return f"Cena {self.cena} - {self.tipo}: {self.mensagem}"


def _unicos(itens):
    vistos = []
    for item in itens:
        if item not in vistos:
            vistos.append(item)
    return vistos


def dividir_frases(texto: str) -> list[str]:
    # Evita quebrar a frase no ponto de abreviações e números (ex.: "Dr. Silva", "3.5").
    protegido = _ABREV_RE.sub(lambda m: m.group(0).replace(".", "․"), texto)
    protegido = re.sub(r"(?<=\d)\.(?=\d)", "․", protegido)
    return [f.replace("․", ".").strip() for f in _FRASE_RE.findall(protegido) if f.strip()]


def validar_texto(texto: str, cena: int = 0) -> list[Aviso]:
    avisos: list[Aviso] = []

    numeros = _unicos(_ALGARISMOS_RE.findall(texto))
    if numeros:
        avisos.append(Aviso(cena, "algarismos", ", ".join(numeros),
                            f"algarismos {', '.join(numeros)} — considere escrever por extenso"))

    abrevs = _unicos(m.group(0) for m in _ABREV_RE.finditer(texto))
    abrevs += _unicos(m.group(0) for m in _ORDINAL_RE.finditer(texto))
    if abrevs:
        avisos.append(Aviso(cena, "abreviação", ", ".join(abrevs),
                            f"abreviações {', '.join(abrevs)} — escreva a palavra inteira"))

    texto_sem_ordinal = _ORDINAL_RE.sub(" ", texto)
    simbolos = _unicos(_SIMBOLOS_RE.findall(texto_sem_ordinal))
    if simbolos:
        avisos.append(Aviso(cena, "símbolo", " ".join(simbolos),
                            f"símbolos {' '.join(simbolos)} — troque por palavras"))

    siglas = _unicos(s for s in _SIGLA_RE.findall(texto) if sum(c.isalpha() for c in s) >= 2)
    if siglas:
        avisos.append(Aviso(cena, "sigla", ", ".join(siglas),
                            f"siglas/maiúsculas {', '.join(siglas)} — confira se a voz lê como deve"))

    for frase in dividir_frases(texto):
        n = len(frase.split())
        if n > LIMITE_PALAVRAS:
            inicio = " ".join(frase.split()[:6])
            avisos.append(Aviso(cena, "frase longa", frase,
                                f"frase com {n} palavras (limite {LIMITE_PALAVRAS}): \"{inicio}...\""))
    return avisos


def validar_roteiro(roteiro: Roteiro) -> list[Aviso]:
    avisos: list[Aviso] = []
    for cena in roteiro.cenas:
        avisos.extend(validar_texto(cena.narracao, cena.numero))
    return avisos


def relatorio(roteiro: Roteiro, avisos: list[Aviso]) -> str:
    linhas = [f"Validação de '{roteiro.episodio}' ({len(roteiro.cenas)} cenas)"]
    if not avisos:
        linhas.append("Nenhum problema encontrado. O texto parece pronto para a narração.")
        return "\n".join(linhas)
    por_cena: dict[int, list[Aviso]] = {}
    for aviso in avisos:
        por_cena.setdefault(aviso.cena, []).append(aviso)
    for numero, lista in por_cena.items():
        linhas.append(f"\nCena {numero}:")
        linhas.extend(f"  - {a.tipo}: {a.mensagem}" for a in lista)
    linhas.append(f"\n{len(avisos)} aviso(s). Isto é só um alerta: o texto não foi alterado.")
    return "\n".join(linhas)
