import pytest

from montador.roteiro import RoteiroErro, interpretar_roteiro, ler_roteiro, nome_seguro


def test_le_exemplo(exemplo):
    r = ler_roteiro(exemplo)
    assert r.canal == "paper-trail"
    assert r.episodio == "the-lost-ledger"
    assert [c.numero for c in r.cenas] == [1, 2, 3]
    assert r.cenas[0].imagem == "old shipping office ledger"
    assert r.cenas[0].tem_tela
    assert not r.cenas[1].tem_tela


def test_aceita_acentos_bom_e_varias_linhas(tmp_path):
    texto = (
        "\ufeffCANAL: antes-do-capitulo-1\nEPISÓDIO: coração\n\n"
        "=== CENA 1 ===\nNARRAÇÃO: Primeira linha\ncontinua aqui.\nIMAGEM: mar\nTELA: -\n"
        "===CENA 2===\nnarracao: Nota: dois pontos no texto.\n"
    )
    pasta = tmp_path / "pasta com espaço e ação"
    pasta.mkdir()
    arq = pasta / "roteiro ação.md"
    arq.write_text(texto, encoding="utf-8")
    r = ler_roteiro(arq)
    assert r.episodio == "coração"
    assert r.cenas[0].narracao == "Primeira linha continua aqui."
    assert r.cenas[1].narracao == "Nota: dois pontos no texto."


def test_arquivo_ansi(tmp_path):
    arq = tmp_path / "ansi.md"
    arq.write_bytes("CANAL: c\nEPISODIO: e\n=== CENA 1 ===\nNARRACAO: ação\n".encode("cp1252"))
    assert ler_roteiro(arq).cenas[0].narracao == "ação"


@pytest.mark.parametrize("texto, trecho", [
    ("EPISODIO: e\n=== CENA 1 ===\nNARRACAO: x\n", "CANAL"),
    ("CANAL: c\n=== CENA 1 ===\nNARRACAO: x\n", "EPISODIO"),
    ("CANAL: c\nEPISODIO: e\n", "Nenhuma cena"),
    ("CANAL: c\nEPISODIO: e\n=== CENA 1 ===\nIMAGEM: x\n", "sem NARRACAO"),
])
def test_erros(texto, trecho):
    with pytest.raises(RoteiroErro, match=trecho):
        interpretar_roteiro(texto)


def test_arquivo_inexistente(tmp_path):
    with pytest.raises(RoteiroErro, match="não encontrado"):
        ler_roteiro(tmp_path / "nada.md")


def test_nome_seguro():
    assert nome_seguro('a:b/c?"d') == "a-b-c--d"
    assert nome_seguro("coração ") == "coração"
