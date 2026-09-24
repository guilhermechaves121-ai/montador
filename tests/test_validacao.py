from montador.roteiro import ler_roteiro
from montador.validacao import dividir_frases, relatorio, validar_roteiro, validar_texto


def tipos(texto):
    return {a.tipo: a.trecho for a in validar_texto(texto, 1)}


def test_texto_limpo_sem_avisos():
    assert validar_texto("Era uma vez uma carta que nunca chegou.") == []


def test_algarismos():
    assert tipos("Em 1911 ele pagou 3,5 mil.")["algarismos"] == "1911, 3,5"


def test_abreviacoes():
    t = tipos("O art. 5 e o Dr. Silva citaram o nº 4 e o n.º 7.")
    assert "art." in t["abreviação"] and "Dr." in t["abreviação"]
    assert "nº" in t["abreviação"] and "n.º" in t["abreviação"]


def test_simbolos():
    t = tipos("Pelo § 2, 50% dos sócios A & B.")
    assert set(t["símbolo"].split()) == {"§", "%", "&"}


def test_siglas():
    assert tipos("O FBI e a ONU investigaram.")["sigla"] == "FBI, ONU"
    # Palavra só com inicial maiúscula não é sigla
    assert "sigla" not in tipos("Brasil e Portugal.")


def test_frase_longa():
    longa = " ".join(["palavra"] * 26) + "."
    curta = " ".join(["palavra"] * 25) + "."
    assert "frase longa" in tipos(longa)
    assert "frase longa" not in tipos(curta)


def test_abreviacao_nao_quebra_frase():
    assert dividir_frases("O Dr. Silva chegou. Depois saiu.") == ["O Dr. Silva chegou.", "Depois saiu."]


def test_nao_altera_texto(exemplo):
    r = ler_roteiro(exemplo)
    antes = [c.narracao for c in r.cenas]
    avisos = validar_roteiro(r)
    assert [c.narracao for c in r.cenas] == antes
    assert {a.cena for a in avisos} == {1, 3}
    texto = relatorio(r, avisos)
    assert "Cena 3" in texto and "não foi alterado" in texto
