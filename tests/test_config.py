import os

import pytest

from montador.config import ConfigErro, carregar_canais, carregar_env, config_do_canal


def test_canais_do_repositorio():
    canais = carregar_canais()
    assert canais["paper-trail"].voz.startswith("en-")
    assert canais["antes-do-capitulo-1"].voz.startswith("pt-")
    for cfg in canais.values():
        assert cfg.motor == "edge"
        assert cfg.pausa > 0


def test_normaliza_valores(tmp_path):
    arq = tmp_path / "canais.yaml"
    arq.write_text("canais:\n  x:\n    motor: Edge-TTS\n    voz: v\n    velocidade: 10\n"
                   "    tom: -5\n    pausa: '1,5'\n", encoding="utf-8")
    cfg = config_do_canal("X", arq)
    assert (cfg.motor, cfg.velocidade, cfg.tom, cfg.pausa) == ("edge", "+10%", "-5Hz", 1.5)


def test_canal_inexistente(tmp_path):
    with pytest.raises(ConfigErro, match="paper-trail"):
        config_do_canal("nao-existe")


def test_env(tmp_path, monkeypatch):
    monkeypatch.delenv("TESTE_CHAVE", raising=False)
    monkeypatch.delenv("TESTE_OUTRA", raising=False)
    arq = tmp_path / ".env"
    arq.write_text('# comentário\nTESTE_CHAVE="abc 123"\nexport TESTE_OUTRA=x\n', encoding="utf-8")
    carregar_env(arq)
    assert os.environ["TESTE_CHAVE"] == "abc 123"
    assert os.environ["TESTE_OUTRA"] == "x"


def test_chaves_fora_do_repositorio():
    from conftest import RAIZ
    gitignore = (RAIZ / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in gitignore and "episodios/" in gitignore
    exemplo = (RAIZ / ".env.exemplo").read_text(encoding="utf-8")
    for linha in exemplo.splitlines():
        if "KEY=" in linha:
            assert linha.strip().endswith("="), "o .env.exemplo não pode conter chaves"
