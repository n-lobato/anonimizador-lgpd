"""Junta os detectores e resolve sobreposições."""

from __future__ import annotations

from ..texto import Localizador, chave
from .modelo import PRIORIDADE, Achado
from .nomes import detectar_nomes
from .padroes import detectar_padroes


def resolver_sobreposicoes(achados: list[Achado]) -> list[Achado]:
    """Mantém o achado mais longo; em empate, o de maior prioridade e confiança."""
    ordenados = sorted(
        achados, key=lambda a: (-a.tamanho, PRIORIDADE.get(a.tipo, 99), -a.confianca, a.ini))
    ocupado: list[tuple[int, int]] = []
    escolhidos = []
    for a in ordenados:
        if a.tamanho <= 0:
            continue
        if any(a.ini < f and i < a.fim for i, f in ocupado):
            continue
        ocupado.append((a.ini, a.fim))
        escolhidos.append(a)
    return sorted(escolhidos, key=lambda a: a.ini)


class Detector:
    def __init__(self, tipos: set[str] | None = None, sempre: list[dict] | None = None,
                 nunca: list[str] | None = None):
        self.tipos = tipos
        self.nunca = {chave(n) for n in (nunca or []) if chave(n)}
        termos = {}
        for item in sempre or []:
            termo = (item.get("termo") or "").strip()
            if termo:
                termos[termo] = item.get("tipo") or "TERMO"
        self._termos = Localizador(termos)

    def detectar(self, texto: str) -> list[Achado]:
        achados: list[Achado] = []
        for ini, fim, tipo in self._termos.encontrar(texto):
            achados.append(Achado(ini, fim, str(tipo), texto[ini:fim], 1.0, "lista própria"))
        achados.extend(detectar_padroes(texto, self.tipos))
        if self.tipos is None or "PESSOA" in self.tipos:
            achados.extend(detectar_nomes(texto))
        if self.nunca:
            achados = [a for a in achados if chave(a.texto) not in self.nunca]
        return resolver_sobreposicoes(achados)
