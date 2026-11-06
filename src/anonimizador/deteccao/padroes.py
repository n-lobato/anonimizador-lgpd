"""Reconhecimento de documentos e contatos por expressões regulares.

Números com dígito verificador (CPF, CNPJ, PIS, cartão) são validados.
Números sem formato próprio (RG, CNH, conta) só são aceitos quando vêm
acompanhados da palavra que os identifica, para evitar falsos positivos.
"""

from __future__ import annotations

import re
from typing import Iterator

from ..texto import normalizar
from .modelo import Achado
from .validadores import cnpj_valido, cpf_valido, luhn_valido, pis_valido, processo_cnj_valido

I = re.IGNORECASE
NUM = r"(?:n\.?\s?[º°o]\.?|n[º°o]\.?|n\.|número|numero|nr\.?)"

# --------------------------------------------------------------------------
# Expressões
# --------------------------------------------------------------------------
# Espaços opcionais ao redor da pontuação: o OCR às vezes lê "529.982 .247-25".
CPF_FORMATADO = re.compile(r"(?<![\w.\-/])\d{3} ?\. ?\d{3} ?\. ?\d{3} ?[-–] ?\d{2}(?![\w])")
CPF_SIMPLES = re.compile(r"(?<![\w.\-/])\d{11}(?![\w])")
CNPJ_FORMATADO = re.compile(
    r"(?<![\w.\-/])[0-9A-Z]{2} ?\. ?[0-9A-Z]{3} ?\. ?[0-9A-Z]{3} ?/ ?[0-9A-Z]{4} ?- ?\d{2}(?![\w])")
CNPJ_SIMPLES = re.compile(r"(?<![\w.\-/])[0-9A-Z]{12}\d{2}(?![\w])")

RG = re.compile(
    r"(?<!\w)(?:RG|R\.\s?G\.|C\.\s?I\.|c[ée]dula\s+de\s+identidade|carteira\s+de\s+identidade"
    r"|identidade(?:\s+militar|\s+civil|\s+funcional|\s+profissional)?|registro\s+geral)"
    r"(?![a-zà-ú])[^\d\n]{0,20}?"
    r"(?P<v>\d[\d.]{3,13}\d(?:\s?-\s?[\dXx])?"
    r"(?:\s*[-–/]?\s*(?:SSP|SESP|SDS|SPTC|DETRAN|DGPC|SSPDS|IFP|IIRGD|SEJUSP|PCDF|SJS|IGP|SJTC"
    r"|SEDS|ITEP|POLITEC|SESDEC|MD|EB|MB|FAB|COMAER|MEX|PC)(?![a-z])(?:\s*[-/]\s*[A-Z]{2}(?![a-z]))?)?)",
    I)
CNH = re.compile(
    r"(?<!\w)(?:CNH|carteira\s+nacional\s+de\s+habilita[çc][ãa]o|habilita[çc][ãa]o)(?![a-zà-ú])"
    r"[^\d\n]{0,30}?(?P<v>\d{9,11})(?!\d)", I)
TITULO = re.compile(
    r"t[íi]tulo\s+(?:de\s+)?eleitor(?:al)?[^\d\n]{0,25}?(?P<v>\d{4}\s?\d{4}\s?\d{4})(?!\d)", I)
PIS = re.compile(
    r"(?<!\w)(?:PIS/PASEP|PIS|PASEP|NIT|NIS)(?![a-zà-ú])[^\d\n]{0,20}?"
    r"(?P<v>\d{3}\.?\d{5}\.?\d{2}-?\d)(?!\d)", I)
CTPS = re.compile(
    r"(?<!\w)CTPS(?![a-zà-ú])[^\d\n]{0,25}?"
    r"(?P<v>\d{4,8}(?:\s*,?\s*(?:s[ée]rie|/|-)\s*(?:" + NUM + r"\s*)?\d{3,5}(?:-?\d)?)?"
    r"(?:\s*[-/]\s*[A-Z]{2}(?![a-z]))?)", I)
PASSAPORTE = re.compile(
    r"passaporte[^\w\n]{0,5}[^\n\d]{0,20}?(?P<v>(?-i:[A-Z]{2})\d{6,7})(?!\d)", I)

OAB = [
    re.compile(r"(?<!\w)OAB\s*[/\-–]?\s*[A-Z]{2}(?![a-z])\s*,?\s*(?:sob\s+o\s+)?(?:" + NUM +
               r"\s*|:\s*)?\d{1,3}\.?\d{3}(?:\s?-?\s?[A-Z](?![a-z]))?(?!\d)", I),
    re.compile(r"(?<!\w)OAB\s*(?:" + NUM + r"\s*)?\d{1,3}\.?\d{3}(?:-?[A-Z])?\s*[/\-–]\s*[A-Z]{2}(?![a-z])", I),
    re.compile(r"(?<![\w.])\d{1,3}\.?\d{3}(?:-[A-Z])?\s*[-–,]?\s*OAB\s*[/\-–]\s*[A-Z]{2}(?![a-z])", I),
]
MATRICULA = [
    re.compile(
        r"(?<!\w)matr[íi]cula(?:\s+(?:funcional|siape|do\s+im[óo]vel|imobili[áa]ria|"
        r"de\s+registro|militar|escolar))?\s*[:\-–]?\s*(?:sob\s+o\s+)?(?:" + NUM + r"\s*)?[:\-–]?\s*"
        r"(?P<v>\d[\d.\-/]{2,15}\d(?:[ \t]\d[\d.\-/]{0,15})*)(?!\d)", I),
    re.compile(r"(?<!\w)SIAPE\s*[:\-–]?\s*(?:" + NUM + r"\s*)?(?P<v>\d{5,8})(?!\d)", I),
    re.compile(r"(?<!\w)(?:prec[- ]?cp|idt\.?\s*mil(?:itar)?)\s*[:\-–]?\s*(?:" + NUM +
               r"\s*)?(?P<v>\d[\d.\-]{4,15}\d)(?!\d)", I),
]
PROCESSO = re.compile(
    r"(?<![\d.\-])\d{7} ?-? ?\d{2} ?\.? ?\d{4} ?\.? ?\d ?\.? ?\d{2} ?\.? ?\d{4}(?![\d])")
EMAIL = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+(?<!\.)")
# O OCR em português costuma ler o "@" como "Q", "©" ou "(@)" ...
EMAIL_OCR = re.compile(r"(?<![\w.+-])[a-z0-9._+-]*[a-z][a-z0-9._+-]*(?:Q|©|\(@\))[a-z0-9-]+(?:\.[a-z0-9-]+)+(?<!\.)")
# ... ou como "d", que só é aceito antes de provedores conhecidos (evita confundir com sites)
EMAIL_OCR_D = re.compile(
    r"(?<![\w.+-])[a-z0-9._+-]*[a-z][a-z0-9._+-]*d(?:gmail|hotmail|yahoo|outlook|uol|bol|terra|icloud|live|msn|ig)"
    r"\.com(?:\.br)?(?![\w.])")
TELEFONES = [
    re.compile(r"(?<![\w+])(?:\+\s?55\s?)?\(\s?0?\d{2}\s?\)\s?(?:9\s?)?\d{4}[-\s.]?\d{4}(?!\d)"),
    re.compile(r"(?<![\w+])\+\s?55\s?\d{2}\s?(?:9\s?)?\d{4}[-\s.]?\d{4}(?!\d)"),
    re.compile(r"(?<![\w\-/.])\d{2}\s(?:9\s?)\d{4}-\d{4}(?![\d\-])"),
    re.compile(r"(?<![\w\-/.])9\d{4}-\d{4}(?![\d\-])"),
]
TELEFONE_CONTEXTO = re.compile(
    r"(?<!\w)(?:tel(?:efone)?s?|fone|cel(?:ular)?|whats(?:app)?|contato|fax)\.?\s*(?:"
    + NUM + r"\s*)?[:\-–]?\s*(?P<v>(?:\(?0?\d{2}\)?\s?)?(?:9\s?)?\d{4}[-\s.]?\d{4})(?!\d)", I)
CEP = [
    re.compile(r"(?<![\w.\-/])\d{2}\.?\d{3} ?- ?\d{3}(?![\w\-])"),
    re.compile(r"(?<!\w)CEP\s*[:\-–]?\s*(?:" + NUM + r"\s*)?(?P<v>\d{8})(?!\d)", I),
]
DATA_NASC = re.compile(
    r"(?:nascid[oa]s?\s+(?:em|aos|no\s+dia|a)|nasceu\s+(?:em|no\s+dia)|data\s+de\s+nascimento|"
    r"(?<![\w ])nascimento\s*:|"
    r"dt\.?\s*nasc\.?|nasc\.)"
    r"\s*[:\-–?]?\s*(?:\n[^\n:]{0,30}:\s*)?(?:(?:no\s+)?dia\s+)?(?:em\s+)?"
    r"(?P<v>\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}|\d{1,2}º?\s+de\s+[a-zç]+\s+de\s+\d{4})", I)
_MESES = r"(?:janeiro|fevereiro|mar[çc]o|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)"
# Modelo de certidão do CNJ: "DATA DE NASCIMENTO POR EXTENSO" e a tabela "DIA MÊS ANO"
DATA_NASC_CERTIDAO = [
    re.compile(r"data\s+de\s+nascimento\s+por\s+extenso\s*[:\-–]?\s*\n?\s*"
               r"(?P<v>[a-zà-úç]+(?:\s+e\s+[a-zà-úç]+)?\s+de\s+" + _MESES +
               r"\s+de\s+(?:[a-zà-úç]+(?:\s+e\s+|\s+)){0,6}[a-zà-úç]+|\d{1,2}\s+de\s+" + _MESES +
               r"\s+de\s+\d{4})", I),
    re.compile(r"nascimento[\s\S]{0,200}?\bdia\s+m[êe]s\s+ano\s*\n\s*"
               r"(?P<v>\d{1,2}[ \t]+\d{1,2}[ \t]+\d{4})(?!\d)", I),
]
# Registros em conselhos profissionais (CRM, CREA, CRESS, OAB fica à parte)
REGISTRO_PROFISSIONAL = re.compile(
    r"(?<!\w)(?:CRM|CREA|CRESS|COREN|CRC|CRP|CRO|CREFITO|CRF|CRMV|CRN|CAU)\s*[/\-–]?\s*"
    r"(?:[A-Z]{2}(?![a-z]))?\s*(?:" + NUM + r"\s*|:\s*)?(?P<v>\d[\d.\-]{1,10}\d)(?!\d)", I)
PLACA = re.compile(
    r"(?:placas?|ve[íi]culo|carro|moto(?:cicleta)?|autom[óo]vel|caminh[ãa]o)[^\n]{0,40}?"
    r"(?<![A-Za-z0-9])(?P<v>(?-i:[A-Z]{3}\s?-?\s?\d[A-Z0-9]\d{2}))(?![A-Za-z0-9])", I)
AGENCIA = re.compile(
    r"(?<!\w)ag(?:[êe]ncia|\.)\s*(?:" + NUM + r"\s*)?[:\-–]?\s*(?P<v>\d{3,5}(?:-[\dXx])?)(?!\d)", I)
CONTA = re.compile(
    r"(?<!\w)(?:conta(?:\s+corrente|\s+poupan[çc]a|\s+sal[áa]rio|\s+banc[áa]ria)?|c/c|c\.c\.)"
    r"\s*(?:" + NUM + r"\s*)?[:\-–]?\s*(?P<v>\d[\d.]{3,14}-[\dXx]|\d{5,15})(?![\d])", I)
CARTAO = re.compile(r"(?<![\d\-.])(?:\d{4}[ \-.]?){3}\d{4}(?![\d])")
IP = re.compile(
    r"(?<![\d.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\d.])")

# --------------------------------------------------------------------------
# Endereços
# --------------------------------------------------------------------------
_LOGRADOUROS = ["Rua", "Avenida", "Av.", "Travessa", "Trav.", "Tv.", "Alameda", "Al.", "Rodovia",
                "Estrada", "Praça", "Largo", "Beco", "Viela", "Quadra", "Qd.", "Qd", "Conjunto",
                "Conj.", "Chácara", "Sítio", "Fazenda", "Condomínio", "Loteamento", "Residencial"]


def _variantes(palavras: list[str]) -> str:
    formas = set()
    for p in palavras:
        formas.update({p, p.upper()})
    return "|".join(re.escape(f) for f in sorted(formas, key=len, reverse=True))


LOGRADOURO = re.compile(r"(?<![\w])(?:" + _variantes(_LOGRADOUROS) + r")(?=[\s.,:])")
SIGLAS_DF = re.compile(
    r"(?<![\w])(?:SQS|SQN|SQSW|SQNW|SHIS|SHIN|SHCS|SHCN|SMPW|SMDB|SHTN|SHTQ|SMLN|SMAS|SCLN|SCLS|CLN"
    r"|CLS|SHVP|SGAN|SGAS|SEPN|SEPS|SRES|SHA|SMU|SOF|SIA|QI|QL|QE|QS|QR|QNM|QNN|QNL|QND|QNA|QNB"
    r"|QNC|QNE|QNF|QNG|QNH|QNJ|QNO|QNP|QNQ|QNR|QSA|QSB|QSC|QSD|QSE|QSF|CSA|CSB|CSC|CSD|CSE|CSG"
    r"|CNA|CNB|CNC|CND|CNF|CNG|QC|AE|ADE)\s*\d")
GATILHO_ENDERECO = re.compile(
    r"(?:residente|domiciliad[oa]s?|reside|moradora?|com\s+endere[çc]o|endere[çc]o(?:\s+residencial)?)"
    r"(?:\s+e\s+domiciliad[oa]s?)?\s*(?:na|no|em|à|a|ao|:)?\s+(?:cidade\s+de\s+)?", I)
_FIM_ENDERECO = re.compile(
    r"\n|;|\s*[,\-–]?\s*\bCEP\b|,?\s*\b(?:onde|que|vem|vêm|requer|para|sendo|neste|nesta|"
    r"e-?mail|telefone|tel\.|celular|fone|portador[a]?|inscrit[oa]|brasileir[oa]|cpf|rg|"
    r"filh[oa]|nascid[oa]|desde|h[áa]\s|conforme|segundo|tendo)\b|\.\s+(?=[A-ZÀ-Ú])|\.$", I)
_ABREVIACOES = {"n", "nº", "no", "n°", "apto", "ap", "bl", "qd", "lt", "cs", "conj", "av", "dr",
                "sr", "sra", "km", "st", "s", "loja", "lj", "cj", "pq", "jd", "vl", "res", "ed",
                "trav", "tv", "al", "r", "pç", "pc", "est", "rod", "chác", "faz", "sl", "andar"}


def _corte_endereco(texto: str, ini: int, limite: int = 150) -> int:
    janela = texto[ini:ini + limite]
    for m in _FIM_ENDERECO.finditer(janela):
        if m.start() == 0:
            continue
        if m.group().startswith("."):
            palavra = re.search(r"(\S+)$", janela[:m.start()])
            if palavra and palavra.group(1).lower().strip(",") in _ABREVIACOES:
                continue
        return ini + m.start()
    if len(janela) < limite:
        return ini + len(janela)
    corte = janela[:90].rfind(" ")
    return ini + (corte if corte > 10 else 90)


def _enderecos(texto: str) -> Iterator[Achado]:
    inicios = []
    for m in LOGRADOURO.finditer(texto):
        inicios.append((m.start(), False))
    for m in SIGLAS_DF.finditer(texto):
        inicios.append((m.start(), False))
    for m in GATILHO_ENDERECO.finditer(texto):
        inicios.append((m.end(), True))
    vistos = []
    for ini, por_gatilho in sorted(inicios):
        if any(a <= ini < b for a, b in vistos):
            continue
        fim = _corte_endereco(texto, ini)
        trecho = texto[ini:fim].rstrip(" ,.-–")
        fim = ini + len(trecho)
        palavras = trecho.split()
        if len(palavras) < 2:
            continue
        tem_numero = bool(re.search(r"\d", trecho))
        if por_gatilho and not tem_numero:
            continue  # "residente em Brasília/DF" não é endereço completo
        if not tem_numero and not re.match(r"\S+\s+(?:d[aoe]s?\s+)?[A-ZÀ-Ú]", trecho):
            continue
        if not tem_numero and normalizar(palavras[0]).rstrip(".") in (
                "condominio", "residencial", "loteamento", "conjunto", "quadra", "qd", "conj"):
            continue
        vistos.append((ini, fim))
        yield Achado(ini, fim, "ENDERECO", trecho, 0.85 if tem_numero else 0.7, "endereço")


# --------------------------------------------------------------------------
# Execução
# --------------------------------------------------------------------------
def _antes(texto: str, ini: int, n: int = 40) -> str:
    return normalizar(texto[max(0, ini - n):ini])


def _grupo(m: re.Match, tipo: str, conf: float = 1.0, origem: str = "padrão") -> Achado:
    if "v" in m.groupdict() and m.group("v"):
        a, b = m.span("v")
    else:
        a, b = m.span()
    return Achado(a, b, tipo, m.string[a:b], conf, origem)


_OUTROS_DOCUMENTOS = (r"(?:cnh|habilitacao|titulo|eleitor|pis|pasep|nit|nis|rg|identidade|matricula|"
                      r"siape|conta|processo|ctps|renavam|chassi|protocolo|nup|sei)")


def detectar_padroes(texto: str, tipos: set[str] | None = None) -> list[Achado]:
    """Todos os achados por padrão. ``tipos`` limita os tipos procurados."""
    quer = (lambda t: True) if tipos is None else (lambda t: t in tipos)
    r: list[Achado] = []

    if quer("CPF"):
        for m in CPF_FORMATADO.finditer(texto):
            r.append(_grupo(m, "CPF", 1.0 if cpf_valido(m.group()) else 0.85))
        for m in CPF_SIMPLES.finditer(texto):
            antes = _antes(texto, m.start(), 30)
            if re.search(_OUTROS_DOCUMENTOS + r"[^\d\n]{0,20}$", antes):
                continue  # 11 dígitos depois de "CNH", "título" etc. não é CPF
            if cpf_valido(m.group()) or re.search(r"cpf\W{0,15}$", antes):
                r.append(_grupo(m, "CPF", 0.9))
    if quer("CNPJ"):
        for m in CNPJ_FORMATADO.finditer(texto):
            r.append(_grupo(m, "CNPJ", 1.0 if cnpj_valido(m.group()) else 0.85))
        for m in CNPJ_SIMPLES.finditer(texto):
            if re.search(r"cnpj\W{0,15}$", _antes(texto, m.start(), 25)) and (
                    cnpj_valido(m.group()) or m.group().isdigit()):
                r.append(_grupo(m, "CNPJ", 0.9))
    simples = [("RG", RG), ("CNH", CNH), ("TITULO_ELEITOR", TITULO), ("CTPS", CTPS),
               ("PASSAPORTE", PASSAPORTE), ("DATA_NASCIMENTO", DATA_NASC), ("PLACA", PLACA)]
    for tipo, rx in simples:
        if quer(tipo):
            r.extend(_grupo(m, tipo, 0.9) for m in rx.finditer(texto))
    if quer("DATA_NASCIMENTO"):
        for rx in DATA_NASC_CERTIDAO:
            r.extend(_grupo(m, "DATA_NASCIMENTO", 0.9) for m in rx.finditer(texto))
    if quer("PIS"):
        for m in PIS.finditer(texto):
            r.append(_grupo(m, "PIS", 1.0 if pis_valido(m.group("v")) else 0.8))
    if quer("OAB"):
        for rx in OAB:
            r.extend(_grupo(m, "OAB", 0.95) for m in rx.finditer(texto))
    if quer("MATRICULA"):
        for rx in MATRICULA:
            r.extend(_grupo(m, "MATRICULA", 0.85) for m in rx.finditer(texto))
        r.extend(_grupo(m, "MATRICULA", 0.85) for m in REGISTRO_PROFISSIONAL.finditer(texto))
    if quer("PROCESSO"):
        for m in PROCESSO.finditer(texto):
            r.append(_grupo(m, "PROCESSO", 1.0 if processo_cnj_valido(m.group()) else 0.9))
    if quer("EMAIL"):
        r.extend(_grupo(m, "EMAIL") for m in EMAIL.finditer(texto))
        r.extend(_grupo(m, "EMAIL", 0.8, "e-mail lido pelo OCR") for m in EMAIL_OCR.finditer(texto))
        r.extend(_grupo(m, "EMAIL", 0.75, "e-mail lido pelo OCR") for m in EMAIL_OCR_D.finditer(texto))
    if quer("TELEFONE"):
        for rx in TELEFONES:
            r.extend(_grupo(m, "TELEFONE", 0.9) for m in rx.finditer(texto))
        r.extend(_grupo(m, "TELEFONE", 0.85) for m in TELEFONE_CONTEXTO.finditer(texto))
    if quer("CEP"):
        for rx in CEP:
            r.extend(_grupo(m, "CEP", 0.9) for m in rx.finditer(texto))
    if quer("CONTA_BANCARIA"):
        r.extend(_grupo(m, "CONTA_BANCARIA", 0.85) for m in AGENCIA.finditer(texto))
        r.extend(_grupo(m, "CONTA_BANCARIA", 0.85) for m in CONTA.finditer(texto))
    if quer("CARTAO"):
        r.extend(_grupo(m, "CARTAO", 0.95) for m in CARTAO.finditer(texto) if luhn_valido(m.group()))
    if quer("IP"):
        for m in IP.finditer(texto):
            if re.search(r"\bip\b", _antes(texto, m.start(), 40)):
                r.append(_grupo(m, "IP", 0.9))
    if quer("ENDERECO"):
        r.extend(_enderecos(texto))
    return r
