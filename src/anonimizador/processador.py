"""Orquestra o fluxo: listar arquivos -> analisar -> (revisar) -> aplicar."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .config import Configuracao, Termos
from .deteccao.detector import Detector
from .formatos import EXTENSOES, NAO_SUPORTADOS, ErroFormato, modulo_para
from .registro import Registro, Substituidor

PASTA_SAIDA_PADRAO = "anonimizados"
Progresso = Callable[[int, int, str], None]


@dataclass
class Arquivo:
    caminho: Path
    raiz: Path | None = None  # pasta arrastada (para manter a estrutura na saída)
    texto: str = ""
    cache: object = None
    avisos: list[str] = field(default_factory=list)
    erro: str = ""
    saida: Path | None = None
    status: str = "pendente"

    @property
    def chave(self) -> str:
        return str(self.caminho)


def listar_arquivos(entradas: list[str | Path], incluir_subpastas: bool = True,
                    sufixo: str = "_anonimizado") -> tuple[list[Arquivo], list[str]]:
    """Expande pastas e filtra extensões. Devolve (arquivos, mensagens de ignorados)."""
    arquivos: list[Arquivo] = []
    ignorados: list[str] = []
    vistos: set[str] = set()

    def adicionar(p: Path, raiz: Path | None):
        k = str(p.resolve()).lower()
        if k in vistos:
            return
        ext = p.suffix.lower()
        if p.stem.endswith(sufixo) or p.name.startswith("~$"):
            return
        if ext in EXTENSOES:
            vistos.add(k)
            arquivos.append(Arquivo(p, raiz))
        elif ext in NAO_SUPORTADOS:
            ignorados.append(f"{p.name}: {NAO_SUPORTADOS[ext]}")

    for e in entradas:
        p = Path(e)
        if p.is_dir():
            padrao = p.rglob("*") if incluir_subpastas else p.glob("*")
            for f in sorted(padrao):
                if f.is_file() and PASTA_SAIDA_PADRAO not in f.relative_to(p).parts[:-1] \
                        and not any(parte.startswith(".") for parte in f.relative_to(p).parts):
                    adicionar(f, p)
        elif p.is_file():
            adicionar(p, None)
        else:
            ignorados.append(f"{p}: não encontrado")
    return arquivos, ignorados


def caminho_saida(arq: Arquivo, cfg: Configuracao) -> Path:
    nome = f"{arq.caminho.stem}{cfg.sufixo}{arq.caminho.suffix}"
    if cfg.pasta_saida:
        base = Path(cfg.pasta_saida)
        if arq.raiz is not None:
            rel = arq.caminho.parent.relative_to(arq.raiz)
            base = base / arq.raiz.name / rel
    else:
        base = arq.caminho.parent / PASTA_SAIDA_PADRAO
    base.mkdir(parents=True, exist_ok=True)
    destino = base / nome
    n = 2
    while destino.exists():
        destino = base / f"{arq.caminho.stem}{cfg.sufixo} ({n}){arq.caminho.suffix}"
        n += 1
    return destino


class Sessao:
    def __init__(self, cfg: Configuracao, termos: Termos):
        self.cfg = cfg
        self.termos = termos
        self.registro = Registro(por_arquivo=not cfg.codigos_globais)
        self.registro.protegidos += list(termos.nunca)
        self.arquivos: list[Arquivo] = []
        self.ignorados: list[str] = []

    @property
    def textos(self) -> dict[str, str]:
        return {a.chave: a.texto for a in self.arquivos if not a.erro}

    def carregar(self, entradas: list[str | Path]) -> None:
        self.arquivos, self.ignorados = listar_arquivos(entradas, self.cfg.incluir_subpastas, self.cfg.sufixo)

    def analisar(self, progresso: Progresso | None = None, cancelado: Callable[[], bool] | None = None) -> None:
        detector = Detector(set(self.cfg.tipos) | {"TERMO"}, self.termos.sempre, self.termos.nunca)
        opcoes = self.cfg.opcoes_formato()
        total = len(self.arquivos)
        for i, arq in enumerate(self.arquivos):
            if cancelado and cancelado():
                break
            if progresso:
                progresso(i, total, f"Analisando {arq.caminho.name}")
            mod = modulo_para(arq.caminho.suffix)
            try:
                ext = mod.extrair(str(arq.caminho), opcoes)
                arq.texto, arq.cache, arq.avisos = ext.texto, ext.cache, list(ext.avisos)
                juntar = getattr(mod, "JUNTAR_LINHAS", False)
                for achado in detector.detectar(arq.texto, juntar_linhas=juntar):
                    self.registro.registrar(achado, arq.chave)
                arq.status = "analisado"
            except ErroFormato as e:
                arq.erro, arq.status = str(e), "erro"
            except Exception as e:  # nunca derrubar o lote inteiro por um arquivo
                arq.erro, arq.status = f"erro inesperado: {e}", "erro"
        self.registro.consolidar_nomes(self.textos)
        self.registro.recontar(self.textos)
        self.registro.descartar_sem_ocorrencias()
        self.registro.numerar()
        if progresso:
            progresso(total, total, "Análise concluída")

    def aplicar(self, progresso: Progresso | None = None, cancelado: Callable[[], bool] | None = None) -> None:
        self.registro.numerar()
        opcoes = self.cfg.opcoes_formato()
        validos = [a for a in self.arquivos if not a.erro]
        for i, arq in enumerate(validos):
            if cancelado and cancelado():
                break
            if progresso:
                progresso(i, len(validos), f"Gravando {arq.caminho.name}")
            mod = modulo_para(arq.caminho.suffix)
            subst = Substituidor(self.registro, self.registro.escopo(arq.chave), self.termos.nunca)
            destino = caminho_saida(arq, self.cfg)
            try:
                arq.avisos += mod.anonimizar(str(arq.caminho), str(destino), subst, opcoes, arq.cache)
                arq.saida, arq.status = destino, "anonimizado"
            except ErroFormato as e:
                arq.erro, arq.status = str(e), "erro"
                destino.unlink(missing_ok=True)
            except Exception as e:
                arq.erro, arq.status = f"erro inesperado: {e}", "erro"
                destino.unlink(missing_ok=True)
            arq.cache = None
        if progresso:
            progresso(len(validos), len(validos), "Concluído")

    def pasta_relatorio(self) -> Path | None:
        if self.cfg.pasta_saida:
            return Path(self.cfg.pasta_saida)
        pastas = sorted({a.saida.parent for a in self.arquivos if a.saida})
        if not pastas:
            return None
        try:
            comum = Path(os.path.commonpath([str(p) for p in pastas]))
        except ValueError:
            return pastas[0]
        return comum if comum in pastas else pastas[0]
