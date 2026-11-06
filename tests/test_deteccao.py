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
    r = _por_tipo("abigail.fonteneleQeconomia.df.gov.br; chave marilda.vileladgmail.com; "
                  "joao(@)uol.com.br. Site: www.tjdft.jus.br e gov.br. Questão: QUESTÃO 3.")
    assert r["EMAIL"] == ["abigail.fonteneleQeconomia.df.gov.br", "marilda.vileladgmail.com", "joao(@)uol.com.br"]


def test_juntar_linhas_nao_estende_nome_ja_encontrado():
    texto = "Para: Patrícia Oliveira Duarte\nAssunto: Admissão\n\nAVÓS\nPaternos: GERALDO MONTEIRO"
    nomes = [a.texto for a in Detector().detectar(texto, juntar_linhas=True) if a.tipo == "PESSOA"]
    assert "Patrícia Oliveira Duarte" in nomes and "GERALDO MONTEIRO" in nomes
    assert not any("Assunto" in n or "AVÓS" in n for n in nomes)
