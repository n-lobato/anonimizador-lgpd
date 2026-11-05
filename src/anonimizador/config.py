"""Configurações e lista de termos do usuário, salvas em JSON localmente."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .deteccao.modelo import TIPOS

TIPOS_PADRAO = [t for t in TIPOS if t != "TERMO"]


@dataclass
class Configuracao:
    tipos: list[str] = field(default_factory=lambda: list(TIPOS_PADRAO))
    ocr: bool = True
    forcar_ocr: bool = False
    idioma_ocr: str = "por"
    dpi_ocr: int = 300
    revisar: bool = True
    codigos_globais: bool = True
    gerar_relatorio: bool = True
    incluir_subpastas: bool = True
    pasta_saida: str = ""  # vazio = subpasta "anonimizados" ao lado de cada original
    sufixo: str = "_anonimizado"

    def opcoes_formato(self):
        from .formatos import Opcoes
        return Opcoes(ocr=self.ocr, forcar_ocr=self.forcar_ocr, idioma_ocr=self.idioma_ocr,
                      dpi_ocr=self.dpi_ocr)


@dataclass
class Termos:
    sempre: list[dict] = field(default_factory=list)  # [{"termo": "...", "tipo": "PESSOA"}]
    nunca: list[str] = field(default_factory=list)


def pasta_config() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        pasta = base / "AnonimizadorLGPD"
    else:
        pasta = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "anonimizador-lgpd"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def _ler_json(caminho: Path) -> dict:
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _gravar_json(caminho: Path, dados: dict) -> None:
    tmp = caminho.with_suffix(".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(caminho)


def carregar_config() -> Configuracao:
    dados = _ler_json(pasta_config() / "config.json")
    cfg = Configuracao()
    for k, v in dados.items():
        if hasattr(cfg, k):
            setattr(cfg, k, v)
    cfg.tipos = [t for t in cfg.tipos if t in TIPOS]
    return cfg


def salvar_config(cfg: Configuracao) -> None:
    _gravar_json(pasta_config() / "config.json", asdict(cfg))


def carregar_termos() -> Termos:
    dados = _ler_json(pasta_config() / "termos.json")
    sempre = [d for d in dados.get("sempre", []) if isinstance(d, dict) and d.get("termo")]
    nunca = [str(t) for t in dados.get("nunca", []) if str(t).strip()]
    return Termos(sempre, nunca)


def salvar_termos(termos: Termos) -> None:
    _gravar_json(pasta_config() / "termos.json", asdict(termos))
