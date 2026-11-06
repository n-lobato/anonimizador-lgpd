"""Reconhecimento de nomes de pessoas sem depender de internet.

Estratégia (heurística, explicável e ajustável):
1. Localiza sequências de palavras com inicial maiúscula (ou TUDO EM MAIÚSCULAS),
   ligadas por partículas (da, de, do, dos...).
2. Quebra a sequência em palavras comuns de documentos (Tribunal, Vara, Senhor...).
3. Aceita o trecho como nome quando:
   - começa com um prenome conhecido e tem ao menos duas palavras; ou
   - tem ao menos duas palavras que são prenomes ou sobrenomes conhecidos; ou
   - vem depois de um papel processual ("requerente", "testemunha", "Sr.") ou
     antes de uma qualificação (", brasileiro", ", CPF"), mesmo com nome raro; ou
   - é rótulo de fala no início da linha ("MARIA:"), comum em transcrições.
Se o spaCy com modelo em português estiver instalado, ele é usado como reforço.
"""

from __future__ import annotations

import re
from typing import Iterator

from ..texto import normalizar
from .dados_nomes import (EXPRESSOES_NAO_PESSOA, PALAVRAS_COMUNS, PALAVRAS_LUGAR, PARTICULAS,
                          PRENOMES, SOBRENOMES, TRATAMENTOS)
from .modelo import Achado

MAIUSC = "A-ZÀ-ÖØ-Þ"
MINUSC = "a-zß-öø-ÿ"
PALAVRA = re.compile(r"[^\W\d_]+(?:['’\-][^\W\d_]+)*\.?")
SEPARADOR_OK = re.compile(r"[ \t ]{1,3}")

PAPEIS = (
    r"requerente|requerid[oa]|autor[a]?|reu|re|reclamante|reclamad[oa]|impetrante|impetrad[oa]|"
    r"paciente|testemunhas?|advogad[oa]s?|procurador[a]?|nome(?:\s+completo)?|filh[oa]\s+de|"
    r"genitor[a]?|pai|mae|conjuge|espos[oa]|companheir[oa]|menor|vitima|acusad[oa]|"
    r"denunciad[oa]|investigad[oa]|indiciad[oa]|apelante|apelad[oa]|agravante|agravad[oa]|"
    r"embargante|embargad[oa]|recorrente|recorrid[oa]|executad[oa]|exequente|inventariante|"
    r"falecid[oa]|de\s+cujus|interessad[oa]|outorgante|outorgad[oa]|declarante|depoente|"
    r"interrogad[oa]|curador[a]?|curatelad[oa]|tutor[a]?|tutelad[oa]|representante|responsavel|"
    r"servidor[a]?|empregad[oa]|contratante|contratad[oa]|locador[a]?|locatari[oa]|fiador[a]?|"
    r"vendedor[a]?|comprador[a]?|herdeir[oa]|beneficiari[oa]|segurad[oa]|alun[oa]|"
    r"participantes?|presentes|assinado(?:\s+digitalmente)?\s+por|subscrevo|eu|ofendid[oa]|"
    r"noticiante|comunicante|indiciad[oa]|sentenciad[oa]|condenad[oa]|preso|presa|"
    r"juiz[a]?|juiza\s+de\s+direito|juiz\s+de\s+direito|promotor[a]?(?:\s+de\s+justica)?|"
    r"defensor[a]?(?:\s+publico|\s+publica)?|escriva[oa]?|perit[oa]|assistente|secretari[oa]|"
    r"relator[a]?|desembargador[a]?|ministr[oa]|delegad[oa]|agente|escrevente|tabeli[aã]o|"
    r"sr|sra|srta|dr|dra|exmo|exma|ilmo|ilma|prof|profa|senhor|senhora|doutor|doutora|dona|"
    r"prezad[oa]|car[oa]|"
    # profissões, funções e relações pessoais ("o engenheiro Fulano", "a vizinha Fulana")
    r"engenheir[oa]|medic[oa]|enfermeir[oa]|arquitet[oa]|corretor[a]?|motorista|sindic[oa]|"
    r"coordenador[a]?|diretor[a]?|gerente|supervisor[a]?|tecnic[oa]|analista|condomin[oa]|"
    r"morador[a]?|vizinh[oa]|colega|conselheir[oa]|estudante|funcionari[oa]|colaborador[a]?|"
    r"estagiari[oa]|usuari[oa]|prepost[oa]|sobrinh[oa]|irma[o]?|ti[oa]|avo|net[oa]|"
    r"namorad[oa]|noiv[oa]|amig[oa]|cunhad[oa]|genro|nora|sogr[oa]|prim[oa]|membro|"
    r"sindicante|sindicad[oa]|acompanhante|motoboy|porteir[oa]|zelador[a]?|cuidador[a]?|"
    r"contador[a]?|psicolog[oa]|assistente\s+social|cliente|paciente"
)
CONTEXTO_ANTES = re.compile(r"(?:^|[^\w])(?:" + PAPEIS + r")\.?\s*(?:\(?a\)?\s*)?[:,\-–]?\s*$")
CONTEXTO_DEPOIS = re.compile(
    r"^\s*[,\-–(]?\s*(?:brasileir[oa]|estrangeir[oa]|portugues[a]?|argentin[oa]|venezuelan[oa]|"
    r"haitian[oa]|solteir[oa]|casad[oa]|divorciad[oa]|viuv[oa]|separad[oa]|maior|menor|"
    r"portador[a]?|inscrit[oa]|nascid[oa]|natural\s+de|residente|domiciliad[oa]|cpf|rg|oab|"
    r"filh[oa]\s+de|advogad[oa]|matricula|servidor[a]?|militar|empresari[oa]|aposentad[oa]|"
    r"do\s+lar|estudante|qualificad[oa]|ja\s+qualificad[oa]|(?:autor|re|reu|requerente|"
    r"requerid[oa]|testemunha|depoente|declarante)\b"
    # coluna de tabela seguida de CPF ("Dagoberto Lins | 168.976.846-00")
    r"|[|;\t]\s*\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b)")


APELIDO = re.compile(
    r"(?:vulgo|alcunha|conhecid[oa]s?(?:\s+[^\W\d_]+){0,3}?\s+(?:como|por)|chamad[oa]s?\s+de|apelidad[oa]s?\s+de|"
    r"apelido\s+(?:de\s+)?|chama[mr]?\s+(?:ele|ela|o|a)?\s*de)\s*[\"'“‘]?\s*$")

# Cargos e rótulos que costumam vir na linha logo abaixo de um nome assinado.
CARGO_ASSINATURA = re.compile(
    r"^\s*(?:juiz[a]?|desembargador[a]?|ministr[oa]|defensor[a]?|promotor[a]?|procurador[a]?|"
    r"advogad[oa]|delegad[oa]|escriva[oa]?|escrevente|tabeli[aã]o|oficial|perit[oa]|"
    r"sindic[oa]|secretari[oa]|presidente|vice|membro|relator[a]?|conselheir[oa]|tesoureir[oa]|"
    r"diretor[a]?|coordenador[a]?|gerente|chefe|comandante|superintendente|reitor[a]?|"
    r"professor[a]?|analista|assistente|tecnic[oa]|servidor[a]?|agente|inspetor[a]?|"
    r"engenheir[oa]|medic[oa]|contador[a]?|prefeit[oa]|vereador[a]?|deputad[oa]|senador[a]?|"
    r"testemunha|locador[a]?|locatari[oa]|fiador[a]?|outorgante|outorgad[oa]|contratante|"
    r"contratad[oa]|vendedor[a]?|comprador[a]?|representante|responsavel|"
    r"cpf|rg|oab|matricula|siape|cress|crm|crea|coren|crc)\b")


# "Câmara dos Deputados", "Câmara Municipal": aí a palavra é instituição, não sobrenome
INSTITUICAO_DEPOIS = re.compile(
    r"\s+(?:dos\s+deputados|dos\s+vereadores|municipal|legislativa|distrital|federal|"
    r"estadual|de\s+comercio|de\s+vereadores|criminal|civel|tecnica|regional|setorial)\b")

# Prenomes que também são palavras comuns: com artigo, quase sempre não são pessoa
PRENOMES_AMBIGUOS = {"rosa", "clara", "vitoria", "gloria", "graca", "luz", "paz", "aurora", "natal",
                     "serena", "flor", "esperanca", "fe", "mar", "rio", "jardim", "pascoa", "cruz",
                     "marco", "franco", "leal", "bento", "dores", "socorro", "neves", "milagres",
                     "estrela", "liberdade", "ventura", "dia"}

TRATAMENTOS_PESSOA = {"sr", "sra", "srta", "dr", "dra", "dona", "senhor", "senhora", "doutor", "doutora"}

# Depois de "conhecido como", palavras que indicam coisa, não pessoa
NAO_APELIDO = {"plano", "operacao", "programa", "projeto", "lei", "caso", "pacote", "reforma",
               "regime", "acordo", "tratado", "movimento", "grupo", "bloco", "festa", "evento"}


def _linha_de_assinatura(texto: str, ini: int, fim: int) -> bool:
    """Nome sozinho na linha, com cargo/documento na linha seguinte ou traço de assinatura acima."""
    ini_linha = texto.rfind("\n", 0, ini) + 1
    fim_linha = texto.find("\n", fim)
    fim_linha = len(texto) if fim_linha < 0 else fim_linha
    if texto[ini_linha:ini].strip() or texto[fim:fim_linha].strip(" \t,.;"):
        return False
    # próxima linha com texto (PDFs costumam trazer uma linha em branco entre nome e cargo)
    resto = texto[fim_linha + 1:fim_linha + 400].split("\n")
    seguinte = next((l for l in resto[:3] if l.strip()), "")
    # linha de cargo é curta e sem dois-pontos ("Juiz do Trabalho"); "OUTORGANTE: Fulano" não é
    if CARGO_ASSINATURA.match(normalizar(seguinte)) and len(seguinte.strip()) <= 70 and ":" not in seguinte:
        return True
    anterior_fim = ini_linha - 1
    anterior = texto[texto.rfind("\n", 0, max(0, anterior_fim)) + 1:max(0, anterior_fim)]
    return re.fullmatch(r"\s*[_\-–.]{5,}\s*", anterior or "") is not None


def _conhecido(n: str, conjunto: set[str]) -> bool:
    """Palavra conhecida; em nomes com hífen (Jean-Pierre), basta uma das partes."""
    return n in conjunto or ("-" in n and any(p in conjunto for p in n.split("-") if p))


def _norm(p: str) -> str:
    return normalizar(p.rstrip(".")).replace("’", "'")


def _eh_maiuscula(p: str) -> bool:
    base = p.rstrip(".")
    if not base or not base[0].isupper():
        return False
    resto = base[1:].replace("'", "").replace("’", "").replace("-", "")
    return resto == "" or resto.islower() or resto.isupper() or re.fullmatch(
        r"(?:[a-zß-öø-ÿ]+[A-ZÀ-ÖØ-Þ]?)+[a-zß-öø-ÿ]*", resto) is not None


def _eh_inicial(p: str) -> bool:
    return len(p) == 2 and p.endswith(".") and p[0].isupper()


def _sequencias(texto: str) -> Iterator[list[re.Match]]:
    atual: list[re.Match] = []
    fim_anterior = None
    for m in PALAVRA.finditer(texto):
        w = m.group()
        conecta = fim_anterior is not None and SEPARADOR_OK.fullmatch(texto[fim_anterior:m.start()] or "x")
        valido = _eh_maiuscula(w) or _eh_inicial(w) or (_norm(w) in PARTICULAS and w.islower()) or \
            (_norm(w) in PARTICULAS and w.isupper())
        if atual and (not conecta or not valido):
            yield atual
            atual = []
        if valido:
            atual.append(m)
            # ponto final (que não seja de abreviação/inicial) encerra a sequência
            if w.endswith(".") and not _eh_inicial(w) and _norm(w) not in TRATAMENTOS:
                yield atual
                atual = []
                fim_anterior = None
                continue
        fim_anterior = m.end()
    if atual:
        yield atual


def _subsequencias(seq: list[re.Match]) -> Iterator[tuple[list[re.Match], str]]:
    """Quebra nas palavras comuns. Devolve (trecho, palavra comum imediatamente antes)."""
    bloco: list[re.Match] = []
    anterior = ""
    for m in seq:
        n = _norm(m.group())
        uteis = [_norm(x.group()) for x in bloco if _norm(x.group()) not in PARTICULAS]
        sobrenome_ambiguo = n in SOBRENOMES and uteis and _conhecido(uteis[0], PRENOMES) \
            and _norm(bloco[-1].group()) not in PARTICULAS \
            and not INSTITUICAO_DEPOIS.match(normalizar(m.string[m.end():m.end() + 30]))
        if n in PALAVRAS_COMUNS and n not in PRENOMES and not sobrenome_ambiguo:
            if bloco:
                yield bloco, anterior
            bloco = []
            anterior = n
        else:
            bloco.append(m)
    if bloco:
        yield bloco, anterior


def _aparar(bloco: list[re.Match]) -> list[re.Match]:
    while bloco and _norm(bloco[0].group()) in PARTICULAS:
        bloco = bloco[1:]
    while bloco and (_norm(bloco[-1].group()) in PARTICULAS or _eh_inicial(bloco[-1].group())):
        bloco = bloco[:-1]
    return bloco


def _palavra_antes(texto: str, ini: int) -> str:
    m = re.search(r"([^\W\d_]+)\.?\s*$", texto[max(0, ini - 30):ini])
    return normalizar(m.group(1)) if m else ""


def _avaliar(texto: str, bloco: list[re.Match], comum_antes: str) -> Achado | None:
    bloco = _aparar(bloco)
    if not bloco:
        return None
    ini, fim = bloco[0].start(), bloco[-1].end()
    if texto[fim - 1] == "." and not _eh_inicial(bloco[-1].group()):
        fim -= 1
    trecho = texto[ini:fim]
    nomes = [_norm(m.group()) for m in bloco
             if _norm(m.group()) not in PARTICULAS and not _eh_inicial(m.group())]
    if not nomes or any(len(n) < 2 for n in nomes):
        return None
    chave_trecho = " ".join(_norm(m.group()) for m in bloco)
    if chave_trecho in EXPRESSOES_NAO_PESSOA:
        return None

    antes_palavra = comum_antes or _palavra_antes(texto, ini)
    if antes_palavra in PALAVRAS_LUGAR:
        return None
    if antes_palavra in ("senhora", "senhor") and _palavra_antes(
            texto, texto.rfind(" ", 0, max(0, ini - 1))).startswith("noss"):
        return None

    antes = normalizar(texto[max(0, ini - 45):ini])
    depois = normalizar(texto[fim:fim + 45])
    papel = bool(CONTEXTO_ANTES.search(antes))
    tratamento = antes_palavra in TRATAMENTOS
    qualificacao = bool(CONTEXTO_DEPOIS.match(depois))
    linha = texto[texto.rfind("\n", 0, ini) + 1:ini]
    inicio_linha = re.fullmatch(r"[ \t\-–•\d.)]*", linha) is not None
    rotulo_fala = inicio_linha and re.match(r"\s*:", texto[fim:fim + 3]) is not None
    # "o Josias", "a Kethellen": artigo + prenome isolado, comum em conversas e depoimentos
    artigo_prenome = len(nomes) == 1 and _conhecido(nomes[0], PRENOMES) and not trecho.isupper() \
        and re.search(r"(?:^|[\s(\"“])(?:o|a)\s+$", texto[max(0, ini - 4):ini]) is not None \
        and not re.match(r"\s+[A-ZÀ-Ú]", texto[fim:fim + 3]) \
        and nomes[0] not in PRENOMES_AMBIGUOS
    apelido = bool(APELIDO.search(antes)) and nomes[0] not in PALAVRAS_LUGAR \
        and nomes[0] not in NAO_APELIDO
    assinatura = _linha_de_assinatura(texto, ini, fim)
    # "DISTRIBUIDORA CENTRO-OESTE DE ALIMENTOS LTDA" é empresa, não pessoa
    if re.match(r"\s*[-–,]?\s*(?:LTDA|Ltda|S\.\s?A\.?|S/A|EIRELI|Eireli|EPP|ME)\b", texto[fim:fim + 12]):
        return None

    conhecidos = sum(1 for n in nomes if _conhecido(n, PRENOMES) or _conhecido(n, SOBRENOMES))
    primeiro_prenome = _conhecido(nomes[0], PRENOMES)

    if len(nomes) >= 2:
        if primeiro_prenome:
            conf = 0.95 if (papel or qualificacao or tratamento) else 0.9
        elif conhecidos >= 2:
            conf = 0.8
        elif papel or qualificacao or tratamento or rotulo_fala or apelido or assinatura:
            conf = 0.75
        else:
            return None
    else:
        if apelido and nomes[0] not in PALAVRAS_LUGAR and nomes[0] not in NAO_APELIDO:
            return Achado(ini, fim, "PESSOA", trecho, 0.7, "apelido")
        if not (_conhecido(nomes[0], PRENOMES) or _conhecido(nomes[0], SOBRENOMES)):
            # "dona Lurdes", "Sr. Wendson": tratamento de pessoa autoriza nome raro isolado
            # ("seu" fica de fora: também é pronome possessivo)
            if antes_palavra in TRATAMENTOS_PESSOA and nomes[0] not in PALAVRAS_COMUNS \
                    and not trecho.isupper():
                return Achado(ini, fim, "PESSOA", trecho, 0.65, "nome")
            if not (rotulo_fala and qualificacao):
                return None
        if tratamento:
            conf = 0.8
        elif rotulo_fala and _conhecido(nomes[0], PRENOMES):
            conf = 0.75
        elif artigo_prenome:
            conf = 0.6
        elif papel and _conhecido(nomes[0], PRENOMES):
            conf = 0.7
        else:
            return None
    return Achado(ini, fim, "PESSOA", trecho, conf, "nome")


def detectar_nomes(texto: str) -> list[Achado]:
    achados = []
    for seq in _sequencias(texto):
        for bloco, comum_antes in _subsequencias(seq):
            a = _avaliar(texto, bloco, comum_antes)
            if a is None:
                # "FACE DE MARIA SOUZA": tenta a partir do primeiro prenome conhecido
                for k in range(1, len(bloco)):
                    if _norm(bloco[k].group()) in PRENOMES:
                        a = _avaliar(texto, bloco[k:], "")
                        break
            if a:
                achados.append(a)
    achados.extend(_spacy(texto))
    return achados


# --------------------------------------------------------------------------
# Reforço opcional com spaCy (não incluído no executável por padrão)
# --------------------------------------------------------------------------
_NLP = None
_NLP_TENTADO = False


def spacy_disponivel() -> bool:
    return _carregar_spacy() is not None


def _carregar_spacy():
    global _NLP, _NLP_TENTADO
    if _NLP_TENTADO:
        return _NLP
    _NLP_TENTADO = True
    try:
        import spacy  # type: ignore
        for modelo in ("pt_core_news_lg", "pt_core_news_md", "pt_core_news_sm"):
            try:
                _NLP = spacy.load(modelo, disable=["parser", "lemmatizer", "tagger"])
                break
            except Exception:
                continue
    except Exception:
        _NLP = None
    return _NLP


def _spacy(texto: str) -> list[Achado]:
    nlp = _carregar_spacy()
    if nlp is None:
        return []
    achados = []
    passo = 90_000
    for base in range(0, len(texto), passo):
        doc = nlp(texto[base:base + passo])
        for ent in doc.ents:
            if ent.label_ != "PER":
                continue
            palavras = [normalizar(p) for p in ent.text.split()]
            uteis = [p for p in palavras if p not in PARTICULAS]
            if len(uteis) < 2 or any(p in PALAVRAS_COMUNS for p in uteis):
                continue
            if not all(w[:1].isupper() for w in ent.text.split() if normalizar(w) not in PARTICULAS):
                continue
            achados.append(Achado(base + ent.start_char, base + ent.end_char, "PESSOA",
                                  ent.text, 0.6, "spaCy"))
    return achados
