from anonimizador.deteccao.validadores import (cnpj_valido, cpf_valido, luhn_valido, pis_valido,
                                               processo_cnj_valido)


def test_cpf():
    assert cpf_valido("529.982.247-25")
    assert cpf_valido("52998224725")
    assert not cpf_valido("529.982.247-26")
    assert not cpf_valido("111.111.111-11")


def test_cnpj_numerico_e_alfanumerico():
    assert cnpj_valido("11.222.333/0001-81")
    assert not cnpj_valido("11.222.333/0001-82")
    assert cnpj_valido("12.ABC.345/01DE-35")  # exemplo oficial do CNPJ alfanumérico


def test_outros():
    assert pis_valido("123.45678.90-0")
    assert luhn_valido("4111 1111 1111 1111")
    assert processo_cnj_valido("0701234-93.2026.8.07.0001")
    assert not processo_cnj_valido("0701234-56.2026.8.07.0001")
