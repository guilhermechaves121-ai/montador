"""Configuração dos canais (canais.yaml) e das chaves (.env)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

PASTA_PROJETO = Path(__file__).resolve().parent.parent


class ConfigErro(Exception):
    """Erro de configuração, com mensagem pronta para o usuário."""


@dataclass
class ConfigVoz:
    motor: str = "edge"
    voz: str = ""
    velocidade: str = "+0%"
    tom: str = "+0Hz"
    pausa: float = 0.7
    modelo: str = ""


def _percentual(valor, padrao="+0%") -> str:
    if valor is None or valor == "":
        return padrao
    if isinstance(valor, (int, float)):
        valor = int(valor)
        return f"{valor:+d}%"
    texto = str(valor).strip().replace(" ", "")
    if not texto.endswith("%"):
        texto += "%"
    if texto[0] not in "+-":
        texto = "+" + texto
    return texto


def _hertz(valor, padrao="+0Hz") -> str:
    if valor is None or valor == "":
        return padrao
    if isinstance(valor, (int, float)):
        return f"{int(valor):+d}Hz"
    texto = str(valor).strip().replace(" ", "")
    if texto.lower().endswith("hz"):
        texto = texto[:-2]
    if texto[0] not in "+-":
        texto = "+" + texto
    return texto + "Hz"


MOTORES_ALIAS = {
    "edge": "edge", "edge-tts": "edge", "edgetts": "edge",
    "azure": "azure", "azure-speech": "azure",
    "elevenlabs": "elevenlabs", "eleven": "elevenlabs", "eleven-labs": "elevenlabs",
}


def nome_motor(nome: str) -> str:
    chave = str(nome or "edge").strip().lower()
    return MOTORES_ALIAS.get(chave, chave)


def carregar_canais(caminho: str | Path | None = None) -> dict[str, ConfigVoz]:
    caminho = Path(caminho) if caminho else PASTA_PROJETO / "canais.yaml"
    if not caminho.is_file():
        raise ConfigErro(f"Arquivo de canais não encontrado: {caminho}")
    try:
        dados = yaml.safe_load(caminho.read_text(encoding="utf-8-sig")) or {}
    except yaml.YAMLError as erro:
        raise ConfigErro(f"O arquivo {caminho.name} tem um erro de formatação:\n{erro}") from erro
    canais = dados.get("canais", dados)
    if not isinstance(canais, dict):
        raise ConfigErro(f"{caminho.name} deve conter a seção 'canais:'.")
    resultado = {}
    for nome, cfg in canais.items():
        cfg = cfg or {}
        try:
            pausa = float(str(cfg.get("pausa", 0.7)).replace(",", "."))
        except ValueError as erro:
            raise ConfigErro(f"Canal '{nome}': 'pausa' deve ser um número de segundos.") from erro
        resultado[str(nome)] = ConfigVoz(
            motor=nome_motor(cfg.get("motor", "edge")),
            voz=str(cfg.get("voz", "")),
            velocidade=_percentual(cfg.get("velocidade")),
            tom=_hertz(cfg.get("tom")),
            pausa=max(0.0, pausa),
            modelo=str(cfg.get("modelo", "") or ""),
        )
    return resultado


def config_do_canal(canal: str, caminho: str | Path | None = None) -> ConfigVoz:
    canais = carregar_canais(caminho)
    if canal in canais:
        return canais[canal]
    for nome, cfg in canais.items():
        if nome.lower() == canal.lower():
            return cfg
    disponiveis = ", ".join(canais) or "(nenhum)"
    raise ConfigErro(
        f"O canal '{canal}' não está no canais.yaml. Canais cadastrados: {disponiveis}.\n"
        "Corrija a linha CANAL do roteiro ou adicione o canal no canais.yaml."
    )


def carregar_env(caminho: str | Path | None = None) -> None:
    """Lê o .env (CHAVE=valor) para as variáveis de ambiente, sem sobrescrever as existentes."""
    caminho = Path(caminho) if caminho else PASTA_PROJETO / ".env"
    if not caminho.is_file():
        return
    for linha in caminho.read_text(encoding="utf-8-sig").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        chave = chave.strip()
        if chave.lower().startswith("export "):
            chave = chave[7:].strip()
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "'\"":
            valor = valor[1:-1]
        if chave and not os.environ.get(chave):
            os.environ[chave] = valor
