from anonimizador.deteccao.detector import Detector
from anonimizador.registro import Registro, Substituidor


def _registro(textos, por_arquivo=False):
    reg = Registro(por_arquivo)
    det = Detector()
    for arq, t in textos.items():
        for a in det.detectar(t):
            reg.registrar(a, arq)
    reg.consolidar_nomes(textos)
    reg.recontar(textos)
    reg.descartar_sem_ocorrencias()
    reg.numerar()
    return reg


def test_mesma_pessoa_mesmo_codigo(peticao):
    textos = {"a.txt": peticao}
    reg = _registro(textos)
    s = Substituidor(reg, "*").substituir(peticao)
    assert "MARIA APARECIDA" not in s and "529.982.247-25" not in s
    assert "[PESSOA_1], brasileira" in s
    assert "[PESSOA_1]: Confirmo" in s  # rótulo de fala ligado ao nome completo
    assert "Lei Maria da Penha" in s  # expressão protegida


def test_codigos_globais_entre_arquivos():
    textos = {"a.txt": "Requerente: João Carlos da Silva, CPF 529.982.247-25.",
              "b.txt": "O CPF 52998224725 pertence a JOÃO CARLOS DA SILVA."}
    reg = _registro(textos)
    sa = Substituidor(reg, "*").substituir(textos["a.txt"])
    sb = Substituidor(reg, "*").substituir(textos["b.txt"])
    assert "[PESSOA_1]" in sa and "[PESSOA_1]" in sb
    assert "[CPF_1]" in sa and "[CPF_1]" in sb


def test_desmarcar_mantem_texto(peticao):
    textos = {"a.txt": peticao}
    reg = _registro(textos)
    for e in reg.entidades.values():
        if e.tipo == "EMAIL":
            e.ativo = False
    s = Substituidor(reg, "*").substituir(peticao)
    assert "maria.souza@gmail.com" in s


def test_unir():
    textos = {"a.txt": "Testemunha: Ana Paula Moreira. Depois, a testemunha Ana Moreira Lima falou."}
    reg = _registro(textos)
    pessoas = [e for e in reg.entidades.values() if e.tipo == "PESSOA" and e.pai is None]
    assert len(pessoas) == 2
    reg.unir([p.id for p in pessoas])
    reg.numerar()
    s = Substituidor(reg, "*").substituir(textos["a.txt"])
    assert s.count("[PESSOA_1]") == 2


def test_por_arquivo_reinicia_numeracao():
    textos = {"a.txt": "Requerente: Pedro Henrique Alves.", "b.txt": "Requerente: Lucas Ferreira Gomes."}
    reg = _registro(textos, por_arquivo=True)
    assert Substituidor(reg, "a.txt").substituir(textos["a.txt"]).endswith("[PESSOA_1].")
    assert Substituidor(reg, "b.txt").substituir(textos["b.txt"]).endswith("[PESSOA_1].")
