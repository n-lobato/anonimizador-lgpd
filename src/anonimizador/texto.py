"""Utilitários de texto: normalização sem acentos e busca de termos.

A normalização é feita caractere a caractere e preserva o comprimento do
texto original. Assim, uma posição encontrada no texto normalizado vale
também para o texto original, o que permite substituir o trecho exato.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from typing import Callable, Hashable, Iterable


@lru_cache(maxsize=8192)
def _base(c: str) -> str:
    decomposto = unicodedata.normalize("NFD", c)
    base = decomposto[0] if decomposto else c
    minuscula = base.lower()
    return minuscula[0] if minuscula else base


def normalizar(texto: str) -> str:
    """Minúsculas e sem acentos, com o MESMO comprimento do texto original."""
    return "".join(map(_base, texto))


def chave(texto: str) -> str:
    """Forma canônica para comparar termos (sem acento, minúscula, espaços únicos)."""
    return re.sub(r"\s+", " ", normalizar(texto)).strip()


def chave_alfanumerica(texto: str) -> str:
    """Só letras e números, útil para documentos (CPF com ou sem pontuação)."""
    return re.sub(r"[^0-9a-z]", "", normalizar(texto))


class Localizador:
    """Encontra, de uma só vez, várias expressões em um texto.

    A busca ignora maiúsculas, minúsculas e acentos, respeita limites de
    palavra e sempre prefere a expressão mais longa em cada posição.
    """

    def __init__(self, termos: dict[str, Hashable]):
        # termos: chave normalizada -> valor associado (ex.: id da entidade)
        self._mapa: dict[str, Hashable] = {}
        # valor None: o termo é reconhecido (e "protege" o trecho), mas não é devolvido
        for termo, valor in termos.items():
            k = chave(termo)
            if k:
                self._mapa.setdefault(k, valor)
        self._regex = self._compilar(self._mapa.keys())

    @staticmethod
    def _compilar(chaves: Iterable[str]):
        partes = []
        for k in sorted(chaves, key=len, reverse=True):
            pedacos = [re.escape(p) for p in k.split(" ") if p]
            partes.append(r"\s+".join(pedacos))
        if not partes:
            return None
        return re.compile(r"(?<!\w)(?:" + "|".join(partes) + r")(?!\w)")

    def __bool__(self) -> bool:
        return self._regex is not None

    def encontrar(self, texto: str) -> list[tuple[int, int, Hashable]]:
        if self._regex is None or not texto:
            return []
        norm = normalizar(texto)
        achados = []
        for m in self._regex.finditer(norm):
            valor = self._mapa.get(re.sub(r"\s+", " ", m.group()))
            if valor is not None and valor != "":
                achados.append((m.start(), m.end(), valor))
        return achados

    def substituir(self, texto: str, formatar: Callable[[Hashable], str]) -> str:
        achados = self.encontrar(texto)
        if not achados:
            return texto
        saida, pos = [], 0
        for ini, fim, valor in achados:
            saida.append(texto[pos:ini])
            saida.append(formatar(valor))
            pos = fim
        saida.append(texto[pos:])
        return "".join(saida)


def contexto(texto: str, ini: int, fim: int, margem: int = 45) -> str:
    """Trecho em volta de uma ocorrência, para exibir na revisão."""
    a = max(0, ini - margem)
    b = min(len(texto), fim + margem)
    trecho = texto[a:ini] + "«" + texto[ini:fim] + "»" + texto[fim:b]
    trecho = re.sub(r"\s+", " ", trecho).strip()
    return ("…" if a > 0 else "") + trecho + ("…" if b < len(texto) else "")
