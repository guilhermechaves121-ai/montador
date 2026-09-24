"""Leitura do roteiro (.md) dividido em cenas."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path


class RoteiroErro(Exception):
    """Erro de formato no roteiro, com mensagem pronta para o usuário."""


@dataclass
class Cena:
    numero: int
    narracao: str
    imagem: str = ""
    tela: str = ""
    linha: int = 0

    @property
    def tem_tela(self) -> bool:
        return bool(self.tela) and self.tela.strip() != "-"


@dataclass
class Roteiro:
    canal: str
    episodio: str
    cenas: list[Cena] = field(default_factory=list)
    arquivo: Path | None = None


_CENA_RE = re.compile(r"^\s*=+\s*CENA\s*(\d+)?\s*=+\s*$", re.IGNORECASE)
_CAMPO_RE = re.compile(r"^\s*([A-Za-zÀ-ÿ_ ]+?)\s*:\s*(.*)$")


def _normalizar_chave(chave: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", chave).encode("ascii", "ignore").decode()
    return sem_acento.strip().upper().replace(" ", "_")


_CHAVES_CABECALHO = {"CANAL": "canal", "EPISODIO": "episodio"}
_CHAVES_CENA = {
    "NARRACAO": "narracao",
    "IMAGEM": "imagem",
    "TELA": "tela",
    "TEXTO_NA_TELA": "tela",
}


def ler_roteiro(caminho: str | Path) -> Roteiro:
    caminho = Path(caminho)
    if not caminho.is_file():
        raise RoteiroErro(f"Arquivo de roteiro não encontrado: {caminho}")
    try:
        texto = caminho.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        # Arquivos salvos pelo Bloco de Notas antigo podem vir em ANSI.
        texto = caminho.read_text(encoding="cp1252")
    roteiro = interpretar_roteiro(texto)
    roteiro.arquivo = caminho
    return roteiro


def interpretar_roteiro(texto: str) -> Roteiro:
    cabecalho: dict[str, str] = {}
    cenas: list[Cena] = []
    atual: dict | None = None
    ultimo_campo: str | None = None

    def fechar_cena():
        if atual is None:
            return
        narracao = " ".join(atual["narracao"]).strip()
        if not narracao:
            raise RoteiroErro(
                f"A cena {atual['numero']} (linha {atual['linha']}) está sem NARRACAO."
            )
        cenas.append(
            Cena(
                numero=atual["numero"],
                narracao=narracao,
                imagem=" ".join(atual["imagem"]).strip(),
                tela=" ".join(atual["tela"]).strip(),
                linha=atual["linha"],
            )
        )

    for num_linha, linha in enumerate(texto.splitlines(), start=1):
        m_cena = _CENA_RE.match(linha)
        if m_cena:
            fechar_cena()
            numero = int(m_cena.group(1)) if m_cena.group(1) else len(cenas) + 1
            atual = {"numero": numero, "linha": num_linha, "narracao": [], "imagem": [], "tela": []}
            ultimo_campo = None
            continue

        if not linha.strip():
            continue

        m_campo = _CAMPO_RE.match(linha)
        chave = _normalizar_chave(m_campo.group(1)) if m_campo else None

        if atual is None:
            if chave in _CHAVES_CABECALHO:
                cabecalho[_CHAVES_CABECALHO[chave]] = m_campo.group(2).strip()
            # Outras linhas antes da primeira cena (títulos, comentários) são ignoradas.
            continue

        if chave in _CHAVES_CENA:
            ultimo_campo = _CHAVES_CENA[chave]
            valor = m_campo.group(2).strip()
            if valor:
                atual[ultimo_campo].append(valor)
        elif ultimo_campo:
            # Continuação de um campo em várias linhas.
            atual[ultimo_campo].append(linha.strip())

    fechar_cena()

    if not cabecalho.get("canal"):
        raise RoteiroErro("O roteiro não tem a linha 'CANAL: nome-do-canal' no início.")
    if not cabecalho.get("episodio"):
        raise RoteiroErro("O roteiro não tem a linha 'EPISODIO: nome-do-episodio' no início.")
    if not cenas:
        raise RoteiroErro("Nenhuma cena encontrada. Cada cena começa com '=== CENA 1 ==='.")

    return Roteiro(canal=cabecalho["canal"], episodio=cabecalho["episodio"], cenas=cenas)


_PROIBIDOS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def nome_seguro(nome: str) -> str:
    """Remove caracteres que o Windows não aceita em nomes de pasta (acentos são mantidos)."""
    limpo = _PROIBIDOS_RE.sub("-", nome).strip().rstrip(". ")
    return limpo or "sem-nome"
