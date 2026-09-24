"""Linha de comando do montador.

    python -m montador validar  roteiro.md
    python -m montador montar   roteiro.md
    python -m montador vozes    [edge|azure|elevenlabs] [--idioma pt-BR]
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

from montador import __version__
from montador.audio import AudioErro
from montador.config import PASTA_PROJETO, ConfigErro, carregar_env, config_do_canal, nome_motor
from montador.montagem import montar
from montador.motores import NOMES_MOTORES, MotorErro, obter_motor
from montador.roteiro import RoteiroErro, ler_roteiro
from montador.validacao import relatorio, validar_roteiro


def _preparar_console() -> None:
    # Garante acentos no console do Windows.
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _caminho(texto: str) -> Path:
    # Ao arrastar arquivos no Windows, o caminho às vezes chega com aspas sobrando.
    return Path(texto.strip().strip('"').strip())


def cmd_validar(args) -> int:
    roteiro = ler_roteiro(_caminho(args.roteiro))
    print(relatorio(roteiro, validar_roteiro(roteiro)))
    return 0


def _perguntar_continuar() -> bool:
    if not sys.stdin or not sys.stdin.isatty():
        return True
    try:
        resposta = input("\nDeseja gerar o áudio mesmo assim? [S/n] ").strip().lower()
    except EOFError:
        return True
    return resposta in ("", "s", "sim", "y", "yes")


def cmd_montar(args) -> int:
    roteiro = ler_roteiro(_caminho(args.roteiro))
    cfg = config_do_canal(roteiro.canal, args.canais)
    if args.motor:
        cfg.motor = nome_motor(args.motor)

    print("=" * 60)
    print("ETAPA 1 de 2: validação do texto")
    print("=" * 60)
    avisos = validar_roteiro(roteiro)
    print(relatorio(roteiro, avisos))
    if avisos and not args.sim and not _perguntar_continuar():
        print("Montagem cancelada. Corrija o roteiro e rode de novo.")
        return 0

    print()
    print("=" * 60)
    print(f"ETAPA 2 de 2: montagem (motor {cfg.motor}, voz {cfg.voz or '?'})")
    print("=" * 60)
    data = dt.date.fromisoformat(args.data) if args.data else None
    resultado = montar(roteiro, cfg, _caminho(args.saida), data=data)

    print()
    for aviso in resultado.avisos:
        print(f"AVISO: {aviso}\n")
    if resultado.cenas_sem_tempo_por_palavra:
        print("Obs.: legendas distribuídas por frase (sem tempo por palavra) nas cenas "
              + ", ".join(map(str, resultado.cenas_sem_tempo_por_palavra)) + ".")
    duracao = resultado.trechos[-1].fim if resultado.trechos else 0
    print(f"Pronto! {len(resultado.trechos)} cenas, {duracao:.1f} segundos de narração.")
    print(f"Arquivos em: {resultado.pasta.resolve()}")
    return 0


def cmd_vozes(args) -> int:
    motores = [nome_motor(args.motor)] if args.motor else NOMES_MOTORES
    codigo = 0
    for nome in motores:
        print(f"\n=== Vozes do motor {nome} ===")
        try:
            vozes = obter_motor(nome).listar_vozes()
        except MotorErro as erro:
            print(f"Não foi possível listar: {erro}")
            codigo = 1
            continue
        if args.idioma:
            filtro = args.idioma.lower()
            vozes = [v for v in vozes if v.idioma.lower().startswith(filtro)]
        for v in sorted(vozes, key=lambda v: (v.idioma, v.nome)):
            detalhes = " · ".join(x for x in (v.idioma, v.genero, v.descricao) if x)
            print(f"  {v.nome:40s} {detalhes}")
        print(f"  ({len(vozes)} vozes)")
    return codigo


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="montador",
        description="Prepara a montagem de vídeos narrados a partir de um roteiro em cenas.",
    )
    parser.add_argument("--version", action="version", version=f"montador {__version__}")
    sub = parser.add_subparsers(dest="comando", metavar="COMANDO")

    p = sub.add_parser("validar", help="aponta trechos que a voz pode ler errado (não altera o texto)")
    p.add_argument("roteiro", help="arquivo .md do roteiro")
    p.set_defaults(funcao=cmd_validar)

    p = sub.add_parser("montar", help="valida e gera áudio, legendas, linha do tempo e checklist")
    p.add_argument("roteiro", help="arquivo .md do roteiro")
    p.add_argument("--saida", default=str(PASTA_PROJETO / "episodios"),
                   help="pasta base de saída (padrão: episodios/)")
    p.add_argument("--canais", default=None, help="arquivo de canais (padrão: canais.yaml)")
    p.add_argument("--data", default=None, help="data do episódio AAAA-MM-DD (padrão: hoje)")
    p.add_argument("--motor", choices=NOMES_MOTORES, help="usa outro motor só desta vez")
    p.add_argument("--sim", action="store_true", help="não pergunta nada; continua mesmo com avisos")
    p.set_defaults(funcao=cmd_montar)

    p = sub.add_parser("vozes", help="lista as vozes disponíveis de cada motor")
    p.add_argument("motor", nargs="?", choices=NOMES_MOTORES, help="motor (padrão: todos)")
    p.add_argument("--idioma", help="filtra por idioma, ex.: pt-BR, en-US, pt")
    p.set_defaults(funcao=cmd_vozes)
    return parser


def main(argv: list[str] | None = None) -> int:
    _preparar_console()
    carregar_env()
    parser = criar_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "funcao", None):
        parser.print_help()
        return 2
    try:
        return args.funcao(args)
    except (RoteiroErro, ConfigErro, MotorErro, AudioErro) as erro:
        print(f"\nERRO: {erro}", file=sys.stderr)
        return 1
    except ValueError as erro:
        print(f"\nERRO: valor inválido: {erro}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrompido.", file=sys.stderr)
        return 130
