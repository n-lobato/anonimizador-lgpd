"""Verificação final: procura na cópia gravada os dados originais que foram substituídos.

Não é uma segunda detecção: só confere se algum texto original de uma entidade ativa
(o nome, o CPF etc. exatamente como apareceram no documento) sobrou em algum lugar
do arquivo novo. No Word e no Excel a busca é feita em TODAS as partes do pacote,
inclusive as que o programa não trata, e por isso pega dado esquecido em lugar
inesperado. No PDF, olha a camada de texto e os metadados. Imagens não são
conferidas aqui (exigiria um novo OCR).

O resultado diz o tipo e a parte do arquivo, nunca o dado encontrado.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

from .deteccao.modelo import TIPOS_ALFANUMERICOS, descricao

PACOTES = {".docx", ".docm", ".xlsx", ".xlsm"}
TEXTO = {".txt", ".md", ".csv", ".log", ".srt", ".vtt"}
TAMANHO_MINIMO = 4  # formas curtas ("Ana") dariam alarme falso em qualquer texto


def _padroes(registro) -> list[tuple[str, re.Pattern]]:
    r = []
    for e in registro.entidades.values():
        if not e.ativo:
            continue
        formas = {v for v in e.variantes.values() if v and len(v.strip()) >= TAMANHO_MINIMO}
        for forma in formas:
            r.append((e.tipo, re.compile(r"(?<!\w)" + re.escape(forma.strip()) + r"(?!\w)")))
            digitos = re.sub(r"\D", "", forma)
            if e.tipo in TIPOS_ALFANUMERICOS and len(digitos) >= 6 and digitos != forma:
                r.append((e.tipo, re.compile(r"(?<!\d)" + digitos + r"(?!\d)")))
    return r


def _textos(caminho: Path) -> list[tuple[str, str]]:
    ext = caminho.suffix.lower()
    if ext in PACOTES:
        saida = []
        with zipfile.ZipFile(caminho) as z:
            for nome in z.namelist():
                if nome.lower().endswith((".xml", ".rels", ".vml", ".txt")):
                    saida.append((nome, z.read(nome).decode("utf-8", errors="ignore")))
        return saida
    if ext == ".pdf":
        from .formatos.pdf import fitz
        f = fitz()
        doc = f.open(str(caminho))
        try:
            saida = [(f"página {i + 1}", pg.get_text()) for i, pg in enumerate(doc)]
            saida.append(("metadados", " ".join(str(v) for v in (doc.metadata or {}).values() if v)))
            saida.append(("metadados XMP", doc.get_xml_metadata() or ""))
            return saida
        finally:
            doc.close()
    if ext in TEXTO:
        return [("texto", caminho.read_text(encoding="utf-8", errors="ignore"))]
    return []


def procurar(caminho: Path, registro) -> list[str]:
    """Avisos sobre dados originais que sobraram na cópia (lista vazia se nada sobrou)."""
    padroes = _padroes(registro)
    if not padroes:
        return []
    try:
        textos = _textos(Path(caminho))
    except Exception as e:
        return [f"A verificação final da cópia não pôde ser feita ({e})."]
    sobras: dict[str, set[str]] = {}
    for parte, texto in textos:
        for tipo, rx in padroes:
            if rx.search(texto):
                sobras.setdefault(descricao(tipo), set()).add(parte)
    if not sobras:
        return []
    detalhe = "; ".join(f"{tipo} em {', '.join(sorted(partes)[:3])}"
                        + (" e outras partes" if len(partes) > 3 else "")
                        for tipo, partes in sorted(sobras.items()))
    return [f"ATENÇÃO: a verificação final encontrou na cópia dado(s) que deveriam ter sido "
            f"substituídos ({detalhe}). Confira o arquivo antes de compartilhar."]
