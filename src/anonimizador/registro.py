"""Registro das entidades encontradas e dos códigos (pseudônimos) atribuídos.

Cada entidade é um dado pessoal (uma pessoa, um CPF, um endereço) com todas
as formas em que aparece no texto (variantes). A mesma pessoa recebe sempre
o mesmo código, por exemplo [PESSOA_1], em todas as ocorrências.
"""

from __future__ import annotations

import itertools
import re
from collections import defaultdict
from dataclasses import dataclass, field

from .deteccao.dados_nomes import EXPRESSOES_PROTEGIDAS, PARTICULAS, PRENOMES
from .deteccao.modelo import TIPOS_ALFANUMERICOS, Achado, prefixo
from .texto import Localizador, chave, chave_alfanumerica, contexto, normalizar

GLOBAL = "*"
MANTER = ""  # valor especial no Localizador: protege o trecho, não substitui


@dataclass
class Entidade:
    id: int
    tipo: str
    rotulo: str
    escopo: str
    variantes: dict[str, str] = field(default_factory=dict)  # chave normalizada -> forma original
    confianca: float = 1.0
    origem: str = ""
    ativo: bool = True
    codigo: str = ""
    pai: int | None = None
    ordem: int = 0
    ocorrencias: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(self.ocorrencias.values())


def _chave_tipo(tipo: str, texto: str) -> str:
    if tipo == "OAB":  # "OAB/DF nº 45.678" == "45.678 OAB/DF"
        n = normalizar(texto)
        uf = re.search(r"oab\W*([a-z]{2})(?![a-z])", n) or re.search(r"([a-z]{2})\W*$", n)
        return (uf.group(1) if uf else "") + re.sub(r"\D", "", n)
    return chave_alfanumerica(texto) if tipo in TIPOS_ALFANUMERICOS else chave(texto)


def _tokens_nome(texto: str) -> list[str]:
    return [p for p in chave(texto).replace(".", " ").split() if p not in PARTICULAS and len(p) > 1]


def _titulo(palavra: str) -> str:
    return palavra[:1].upper() + palavra[1:].lower()


class Registro:
    def __init__(self, por_arquivo: bool = False):
        self.por_arquivo = por_arquivo
        self.entidades: dict[int, Entidade] = {}
        self._indice: dict[tuple[str, str, str], int] = {}
        self._ids = itertools.count(1)
        self._ordem = itertools.count(1)
        # trechos que nunca são substituídos (internos + lista "nunca" do usuário)
        self.protegidos: list[str] = list(EXPRESSOES_PROTEGIDAS)

    # ------------------------------------------------------------------ básico
    def escopo(self, arquivo: str | None) -> str:
        return arquivo if (self.por_arquivo and arquivo) else GLOBAL

    def escopos(self) -> list[str]:
        return sorted({e.escopo for e in self.entidades.values()})

    def do_escopo(self, escopo: str) -> list[Entidade]:
        return [e for e in self.entidades.values() if e.escopo == escopo]

    def ordenadas(self) -> list[Entidade]:
        return sorted(self.entidades.values(), key=lambda e: (e.escopo, e.tipo != "PESSOA", e.tipo, e.ordem))

    def _nova(self, tipo: str, texto: str, escopo: str, confianca: float, origem: str,
              pai: int | None = None) -> Entidade:
        ent = Entidade(next(self._ids), tipo, texto.strip(), escopo, confianca=confianca,
                       origem=origem, pai=pai, ordem=next(self._ordem))
        self.entidades[ent.id] = ent
        return ent

    def _adicionar_variante(self, ent: Entidade, texto: str) -> None:
        k = chave(texto)
        if k and k not in ent.variantes:
            ent.variantes[k] = texto.strip()
        self._indice[(ent.escopo, ent.tipo, _chave_tipo(ent.tipo, texto))] = ent.id

    def registrar(self, achado: Achado, arquivo: str | None = None) -> Entidade:
        escopo = self.escopo(arquivo)
        k = (escopo, achado.tipo, _chave_tipo(achado.tipo, achado.texto))
        if k in self._indice and self._indice[k] in self.entidades:
            ent = self.entidades[self._indice[k]]
            ent.confianca = max(ent.confianca, achado.confianca)
        else:
            ent = self._nova(achado.tipo, achado.texto, escopo, achado.confianca, achado.origem)
        self._adicionar_variante(ent, achado.texto)
        return ent

    def adicionar_manual(self, termo: str, tipo: str, arquivo: str | None = None) -> Entidade:
        return self.registrar(Achado(0, len(termo), tipo, termo, 1.0, "manual"), arquivo)

    def remover(self, ids: list[int]) -> None:
        for i in ids:
            self.entidades.pop(i, None)
        for e in list(self.entidades.values()):
            if e.pai is not None and e.pai not in self.entidades:
                e.pai = None
        self._reindexar()

    def _reindexar(self) -> None:
        self._indice = {}
        for e in self.entidades.values():
            for forma in e.variantes.values():
                self._indice[(e.escopo, e.tipo, _chave_tipo(e.tipo, forma))] = e.id

    # --------------------------------------------------------- nomes derivados
    def consolidar_nomes(self, textos: dict[str, str]) -> None:
        """Liga menções parciais ao nome completo da mesma pessoa.

        - "João Silva" vira variante de "João Carlos da Silva".
        - "Sr. Pereira" ou "MARIA:" (rótulo de fala) recebem o código da única
          pessoa com aquele sobrenome ou prenome no mesmo escopo.
        - Um prenome usado sozinho mais adiante ("Maria afirmou") vira uma
          entidade derivada, com o mesmo código, que pode ser desmarcada.
        """
        for escopo in self.escopos():
            pessoas = [e for e in self.do_escopo(escopo) if e.tipo == "PESSOA" and e.pai is None]
            completos = [e for e in pessoas if len(_tokens_nome(e.rotulo)) >= 2]
            completos.sort(key=lambda e: -len(_tokens_nome(e.rotulo)))

            # 1) nomes de 2+ palavras contidos em um nome maior (mesmo 1º e último)
            for menor in list(completos):
                tm = _tokens_nome(menor.rotulo)
                for maior in completos:
                    if maior is menor or maior.id not in self.entidades or menor.id not in self.entidades:
                        continue
                    tM = _tokens_nome(maior.rotulo)
                    if len(tM) > len(tm) and tm[0] == tM[0] and tm[-1] == tM[-1] and set(tm) <= set(tM):
                        self.unir([maior.id, menor.id])
                        break
            completos = [e for e in completos if e.id in self.entidades]

            por_prenome: dict[str, list[Entidade]] = defaultdict(list)
            por_sobrenome: dict[str, list[Entidade]] = defaultdict(list)
            for e in completos:
                t = _tokens_nome(e.rotulo)
                por_prenome[t[0]].append(e)
                por_sobrenome[t[-1]].append(e)
                # forma curta "Prenome Sobrenome"
                if len(t) >= 3:
                    self._adicionar_variante(e, f"{_titulo(t[0])} {_titulo(t[-1])}")
                    if t[1] in PRENOMES:  # "Maria Aparecida"
                        por_prenome_composto = f"{_titulo(t[0])} {_titulo(t[1])}"
                        self._adicionar_variante(e, por_prenome_composto)

            # 2) menções de uma palavra só, já detectadas
            for e in [p for p in pessoas if p.id in self.entidades and len(_tokens_nome(p.rotulo)) == 1]:
                tok = _tokens_nome(e.rotulo)[0]
                candidatos = por_sobrenome.get(tok) or por_prenome.get(tok) or []
                if len(candidatos) == 1:
                    e.pai = candidatos[0].id
                    e.origem = f"menção curta de {candidatos[0].rotulo}"

            # 3) prenome isolado no texto, quando só uma pessoa tem esse prenome
            textos_escopo = [t for arq, t in textos.items() if self.escopo(arq) == escopo]
            existentes = {k for e in self.do_escopo(escopo) for k in e.variantes}
            for prenome, lista in por_prenome.items():
                if len(lista) != 1 or len(prenome) < 3 or prenome in existentes:
                    continue
                dono = lista[0]
                forma = next((w for w in dono.rotulo.split() if normalizar(w) == prenome), prenome)
                loc = Localizador({forma: 1})
                if any(self._ocorre_fora(loc, t, dono) for t in textos_escopo):
                    d = self._nova("PESSOA", _titulo(forma) if forma.isupper() else forma, escopo,
                                   0.6, f"prenome de {dono.rotulo}", pai=dono.id)
                    self._adicionar_variante(d, forma)

    def _ocorre_fora(self, loc: Localizador, texto: str, dono: Entidade) -> bool:
        cheio = Localizador({v: 1 for v in dono.variantes.values()})
        ocupado = [(a, b) for a, b, _ in cheio.encontrar(texto)]
        for a, b, _ in loc.encontrar(texto):
            if not any(x <= a and b <= y for x, y in ocupado):
                # só conta se a palavra estiver com inicial maiúscula no original
                if texto[a:a + 1].isupper():
                    return True
        return False

    # ------------------------------------------------------------- operações
    def unir(self, ids: list[int]) -> Entidade | None:
        ents = [self.entidades[i] for i in ids if i in self.entidades]
        if not ents:
            return None
        alvo = ents[0]
        for e in ents[1:]:
            if e.escopo != alvo.escopo:
                continue
            for k, forma in e.variantes.items():
                alvo.variantes.setdefault(k, forma)
            alvo.confianca = max(alvo.confianca, e.confianca)
            for filho in self.entidades.values():
                if filho.pai == e.id:
                    filho.pai = alvo.id
            del self.entidades[e.id]
        if alvo.pai is not None and alvo.pai not in self.entidades:
            alvo.pai = None
        self._reindexar()
        return alvo

    def numerar(self) -> None:
        """Atribui códigos na ordem em que as entidades apareceram."""
        contadores: dict[tuple[str, str], int] = defaultdict(int)
        raizes = sorted((e for e in self.entidades.values() if e.pai is None), key=lambda e: e.ordem)
        for e in raizes:
            p = prefixo(e.tipo)
            contadores[(e.escopo, p)] += 1
            e.codigo = f"{p}_{contadores[(e.escopo, p)]}"
        for e in self.entidades.values():
            if e.pai is not None:
                e.codigo = self.entidades[e.pai].codigo

    def localizador(self, escopo: str, nunca: list[str] | None = None,
                    somente_ativos: bool = True) -> Localizador:
        termos: dict[str, object] = {}
        ents = sorted(self.do_escopo(escopo), key=lambda e: not e.ativo)
        for e in ents:
            valor = e.codigo if (e.ativo or not somente_ativos) else MANTER
            for forma in e.variantes.values():
                termos.setdefault(forma, valor)
        for termo in list(self.protegidos) + list(nunca or []):
            termos.setdefault(termo, MANTER)
        return Localizador(termos)

    def _localizador_ids(self, escopo: str) -> Localizador:
        termos: dict[str, object] = {}
        for e in self.do_escopo(escopo):
            for forma in e.variantes.values():
                termos.setdefault(forma, e.id)
        for termo in self.protegidos:
            termos.setdefault(termo, None)  # casa, mas não é contado
        return Localizador(termos)

    def recontar(self, textos: dict[str, str]) -> None:
        for e in self.entidades.values():
            e.ocorrencias = {}
        for escopo in self.escopos():
            loc = self._localizador_ids(escopo)
            for arq, texto in textos.items():
                if self.escopo(arq) != escopo:
                    continue
                for _, _, i in loc.encontrar(texto):
                    ent = self.entidades.get(i)
                    if ent:
                        ent.ocorrencias[arq] = ent.ocorrencias.get(arq, 0) + 1

    def contextos(self, ent: Entidade, textos: dict[str, str], limite: int = 6) -> list[tuple[str, str]]:
        loc = self._localizador_ids(ent.escopo)
        saida = []
        for arq, texto in textos.items():
            if self.escopo(arq) != ent.escopo:
                continue
            for a, b, i in loc.encontrar(texto):
                if i == ent.id:
                    saida.append((arq, contexto(texto, a, b)))
                    if len(saida) >= limite:
                        return saida
        return saida

    def descartar_sem_ocorrencias(self) -> None:
        vazias = [e.id for e in self.entidades.values() if e.total == 0]
        if vazias:
            self.remover(vazias)


class Substituidor:
    """Aplica o registro a um texto: devolve trechos e códigos a inserir."""

    def __init__(self, registro: Registro, escopo: str, nunca: list[str] | None = None,
                 colchetes: bool = True):
        self._loc = registro.localizador(escopo, nunca)
        self._colchetes = colchetes

    def _fmt(self, codigo: str) -> str:
        return f"[{codigo}]" if self._colchetes else codigo

    def trechos(self, texto: str, colchetes: bool | None = None) -> list[tuple[int, int, str]]:
        usar = self._colchetes if colchetes is None else colchetes
        r = []
        for a, b, cod in self._loc.encontrar(texto):
            if cod == MANTER:
                continue
            r.append((a, b, f"[{cod}]" if usar else str(cod)))
        return r

    def substituir(self, texto: str) -> str:
        if not texto:
            return texto
        partes, pos = [], 0
        for a, b, rep in self.trechos(texto):
            partes.append(texto[pos:a])
            partes.append(rep)
            pos = b
        partes.append(texto[pos:])
        return "".join(partes)
