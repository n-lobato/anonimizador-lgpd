"""Tipos de dados pessoais e estrutura de um achado."""

from __future__ import annotations

from dataclasses import dataclass

# tipo -> (descrição exibida, prefixo do código)
TIPOS: dict[str, tuple[str, str]] = {
    "PESSOA": ("Nome de pessoa", "PESSOA"),
    "CPF": ("CPF", "CPF"),
    "RG": ("RG / identidade", "RG"),
    "CNH": ("CNH", "CNH"),
    "TITULO_ELEITOR": ("Título de eleitor", "TITULO"),
    "PIS": ("PIS / PASEP / NIT", "PIS"),
    "CTPS": ("CTPS", "CTPS"),
    "PASSAPORTE": ("Passaporte", "PASSAPORTE"),
    "OAB": ("Inscrição na OAB", "OAB"),
    "MATRICULA": ("Matrícula ou registro profissional (SIAPE, imóvel, CRM, CREA...)", "MATRICULA"),
    "CNPJ": ("CNPJ", "CNPJ"),
    "PROCESSO": ("Número de processo (padrão CNJ)", "PROCESSO"),
    "EMAIL": ("E-mail", "EMAIL"),
    "TELEFONE": ("Telefone", "TELEFONE"),
    "ENDERECO": ("Endereço", "ENDERECO"),
    "CEP": ("CEP", "CEP"),
    "DATA_NASCIMENTO": ("Data de nascimento", "DATA_NASC"),
    "PLACA": ("Placa de veículo", "PLACA"),
    "CONTA_BANCARIA": ("Agência / conta bancária", "CONTA"),
    "CARTAO": ("Cartão de crédito", "CARTAO"),
    "IP": ("Endereço IP", "IP"),
    "TERMO": ("Termo da lista própria", "TERMO"),
}

# Tipos cuja comparação ignora pontuação (123.456.789-09 == 12345678909).
TIPOS_ALFANUMERICOS = {
    "CPF", "RG", "CNH", "TITULO_ELEITOR", "PIS", "CTPS", "PASSAPORTE", "MATRICULA",
    "CNPJ", "PROCESSO", "TELEFONE", "CEP", "PLACA", "CONTA_BANCARIA", "CARTAO", "IP",
}

# Em caso de sobreposição de mesmo tamanho, vence a menor prioridade.
PRIORIDADE = {t: i for i, t in enumerate([
    "TERMO", "CPF", "CNPJ", "PROCESSO", "OAB", "EMAIL", "PIS", "TITULO_ELEITOR", "CNH",
    "PASSAPORTE", "CTPS", "RG", "MATRICULA", "CARTAO", "TELEFONE", "CEP", "PLACA",
    "CONTA_BANCARIA", "IP", "DATA_NASCIMENTO", "PESSOA", "ENDERECO",
])}


def descricao(tipo: str) -> str:
    return TIPOS.get(tipo, (tipo, tipo))[0]


def prefixo(tipo: str) -> str:
    return TIPOS.get(tipo, (tipo, tipo))[1]


@dataclass
class Achado:
    ini: int
    fim: int
    tipo: str
    texto: str
    confianca: float = 1.0
    origem: str = "padrão"

    @property
    def tamanho(self) -> int:
        return self.fim - self.ini
