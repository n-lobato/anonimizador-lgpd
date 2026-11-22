from anonimizador.config import TIPOS
from anonimizador.deteccao.detector import Detector
from anonimizador.deteccao.nomes import detectar_nomes
from anonimizador.texto import Localizador, normalizar


def _por_tipo(texto, **kw):
    r = {}
    for a in Detector(**kw).detectar(texto):
        r.setdefault(a.tipo, []).append(a.texto)
    return r


def test_normalizar_preserva_tamanho():
    t = "JOÃO Ação Çé"
    assert len(normalizar(t)) == len(t)
    assert normalizar(t) == "joao acao ce"


def test_localizador_ignora_acentos_e_prefere_o_mais_longo():
    loc = Localizador({"Maria": "A", "Maria da Silva": "B"})
    achados = loc.encontrar("MARIA DA SILVA e maria; mariana não")
    assert [v for _, _, v in achados] == ["B", "A"]


def test_peticao(peticao):
    r = _por_tipo(peticao)
    assert "MARIA APARECIDA DE SOUZA SANTOS" in r["PESSOA"]
    assert "Thalysson Rodrigues Pereira" in r["PESSOA"]
    assert "José Carlos da Silva Filho" in r["PESSOA"]
    assert "Kauã Ribeiro" in r["PESSOA"]
    assert r["CPF"] == ["529.982.247-25"]
    assert r["EMAIL"] == ["maria.souza@gmail.com"]
    assert r["TELEFONE"] == ["(61) 99876-5432"]
    assert r["CEP"] == ["70355-030"]
    assert r["OAB"] == ["OAB/DF nº 45.678"]
    assert r["PROCESSO"] == ["0701234-93.2026.8.07.0001"]
    assert r["DATA_NASCIMENTO"] == ["12/03/1980"]
    assert r["RG"][0].startswith("1.234.567")
    assert r["ENDERECO"][0].startswith("SQS 308")
    textos = " | ".join(r["PESSOA"])
    for nao in ("Tribunal", "Justiça", "Distrito Federal", "Brasília", "EXCELENTÍSSIMO"):
        assert nao not in textos


def test_nao_confunde_lugares_e_leis():
    nomes = [a.texto for a in detectar_nomes(
        "Moro em São Paulo, na Rua João Pessoa, perto da Escola Maria Quitéria. Aplica-se a Lei Maria da Penha.")]
    assert nomes == []


def test_rotulo_de_fala_e_tratamento():
    nomes = [a.texto for a in detectar_nomes("JUIZ: Pode falar.\nCARLOS: Sim.\nA Sra. Oliveira chegou.")]
    assert "CARLOS" in nomes and "Oliveira" in nomes


def test_lista_propria_e_nunca():
    texto = "O apelido Zeca do Pandeiro apareceu. João da Silva também."
    r = _por_tipo(texto, sempre=[{"termo": "Zeca do Pandeiro", "tipo": "PESSOA"}], nunca=["João da Silva"])
    assert r["PESSOA"] == ["Zeca do Pandeiro"]


def test_onze_digitos_de_cnh_nao_e_cpf():
    r = _por_tipo("CNH nº 01234567890")
    assert "CPF" not in r and r["CNH"] == ["01234567890"]


def test_tipos_desligados(peticao):
    r = _por_tipo(peticao, tipos={"CPF"})
    assert set(r) == {"CPF"}


def test_nome_endereco_e_numero_quebrados_entre_linhas():
    texto = ("Foram eleitos para o conselho fiscal: Ana Lima, Ubiratan\nSilveira e Thaís Prado. O fiador\n"
             "reside na Rua das\nPaineiras, nº 1.040, apto 1203. Testemunha com PIS\n215.90109.28-9.\n\n"
             "MARIA:\nConfirmo.")
    so_linhas = {a.texto for a in Detector().detectar(texto)}
    juntas = {a.texto.replace("\n", " ") for a in Detector().detectar(texto, juntar_linhas=True)}
    assert "Ubiratan Silveira" not in so_linhas  # comportamento anterior
    assert "Ubiratan Silveira" in juntas
    assert any(t.startswith("Rua das Paineiras, nº 1.040") for t in juntas)
    assert "215.90109.28-9" in juntas
    assert "MARIA" in juntas  # rótulo de fala no início da linha continua reconhecido


def test_email_lido_pelo_ocr():
    # formas reais produzidas pelo Tesseract em português a partir de um PDF escaneado
    lidos = ["abigail.fonteneleGQeconomia.df.gov.br", "erica.hashimoto(Ose.df.gov.br",
             "marilda.vilelaQ&Qgmail.com", "abigail.fonteneleQeconomia.df.gov.br",
             "marilda.vileladgmail.com", "joao(@)uol.com.br", "erica.hashimoto(&Pse .df.gov.br"]
    r = _por_tipo(" | ".join(lidos) + ". Site: www.tjdft.jus.br e gov.br. Questão: QUESTÃO 3. "
                  "Rio Queimado.com e caixaQuadra 3.")
    assert r["EMAIL"] == lidos


def test_juntar_linhas_nao_estende_nome_ja_encontrado():
    texto = "Para: Patrícia Oliveira Duarte\nAssunto: Admissão\n\nAVÓS\nPaternos: GERALDO MONTEIRO"
    nomes = [a.texto for a in Detector().detectar(texto, juntar_linhas=True) if a.tipo == "PESSOA"]
    assert "Patrícia Oliveira Duarte" in nomes and "GERALDO MONTEIRO" in nomes
    assert not any("Assunto" in n or "AVÓS" in n for n in nomes)


def test_cpf_com_espacos_so_quando_o_digito_confere():
    r = _por_tipo("CPF 529 982 247 25, telefone e outro número 123 456 789 00.")
    assert r["CPF"] == ["529 982 247 25"]  # o segundo tem dígito inválido e fica de fora


def test_campos_da_identidade_militar():
    """Rótulos como saem da identidade militar lida pelo OCR: sem "de" e com o valor na linha de baixo."""
    d = Detector(set(TIPOS))
    achados = {(a.tipo, a.texto) for a in d.detectar(
        "NR REGISTRO\n0123456789\nDATA NASCIMENTO\n01/02/1970\nFUSEX\n123456789 01", juntar_linhas=True)}
    assert ("RG", "0123456789") in achados
    assert ("DATA_NASCIMENTO", "01/02/1970") in achados
    assert ("MATRICULA", "123456789 01") in achados


def test_doc_origem_da_identidade_e_rotulos_nao_sao_nomes():
    d = Detector(set(TIPOS))
    texto = ("NACIONALIDADE NATURALIDADE\nBRASILEIRA BELEM / PA\nDOC ORIGEM\n"
             "Reg Cas nº 0012345, CART 7º OF, Manaus-AM, Lv\nB-00011, Fl 111, Exp 01 JUN 19.")
    achados = [(a.tipo, a.texto) for a in d.detectar(texto, juntar_linhas=True)]
    assert not any(t == "PESSOA" for t, _ in achados)  # rótulos do documento não são nomes
    assert any(t == "MATRICULA" and v.startswith("0012345") and v.endswith("Fl 111") for t, v in achados)
    # referência a folhas dos autos não é registro civil
    assert not d.detectar("Conforme fls. 242 dos autos, o registro de nascimento foi juntado.")


def test_naturalidade_so_com_rotulo():
    d = Detector(set(TIPOS))

    def nat(t):
        return [a.texto for a in d.detectar(t, juntar_linhas=True) if a.tipo == "NATURALIDADE"]
    assert nat("NACIONALIDADE NATURALIDADE\nBRASILEIRA BELEM / PA\nDOC ORIGEM") == ["BELEM / PA"]
    assert nat("Fulano, brasileiro, natural de Belém/PA, casado") == ["Belém/PA"]
    assert nat("natural de São José dos Campos - SP, residente") == ["São José dos Campos - SP"]
    assert nat("o requerente é natural da cidade, onde reside") == []
    assert nat("Mora em Belém/PA desde 2010.") == []  # sem o rótulo, cidade não é tarjada


def test_validadores_recusam_tamanho_errado_e_repeticao():
    from anonimizador.deteccao import validadores as v
    assert not v.cnpj_valido("11.111.111/1111-11")
    assert not v.cnpj_valido("12.345.678/0001")
    assert not v.pis_valido("111.11111.11-1")
    assert not v.pis_valido("123.4567.89")
    assert not v.luhn_valido("4111 1111 1111")  # 12 dígitos: curto demais para cartão
    assert not v.processo_cnj_valido("0701234-93.2026.8.07.001")  # 19 dígitos
    assert v.processo_cnj_valido("0701234-93.2026.8.07.0001")
