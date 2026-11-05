"""Validação de dígitos verificadores de documentos brasileiros."""

from __future__ import annotations

import re


def _digitos(s: str) -> str:
    return re.sub(r"\D", "", s)


def cpf_valido(s: str) -> bool:
    d = _digitos(s)
    if len(d) != 11 or d == d[0] * 11:
        return False
    for pos in (9, 10):
        soma = sum(int(d[i]) * (pos + 1 - i) for i in range(pos))
        dv = (soma * 10) % 11 % 10
        if dv != int(d[pos]):
            return False
    return True


def cnpj_valido(s: str) -> bool:
    """Aceita o CNPJ numérico e o novo CNPJ alfanumérico (a partir de 2026).

    No formato alfanumérico, cada caractere vale (código ASCII - 48) e os
    dois dígitos verificadores continuam numéricos.
    """
    c = re.sub(r"[^0-9A-Z]", "", s.upper())
    if len(c) != 14 or not c[12:].isdigit() or c == c[0] * 14:
        return False
    valores = [ord(ch) - 48 for ch in c]

    def dv(n: int) -> int:
        pesos = list(range(n - 7, 1, -1)) + list(range(9, 1, -1))
        soma = sum(v * p for v, p in zip(valores[:n], pesos))
        r = soma % 11
        return 0 if r < 2 else 11 - r

    return dv(12) == valores[12] and dv(13) == valores[13]


def pis_valido(s: str) -> bool:
    d = _digitos(s)
    if len(d) != 11 or d == d[0] * 11:
        return False
    pesos = [3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    r = sum(int(a) * b for a, b in zip(d, pesos)) % 11
    dv = 0 if r < 2 else 11 - r
    return dv == int(d[10])


def luhn_valido(s: str) -> bool:
    d = _digitos(s)
    if not 13 <= len(d) <= 19:
        return False
    total = 0
    for i, ch in enumerate(reversed(d)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def processo_cnj_valido(s: str) -> bool:
    """NNNNNNN-DD.AAAA.J.TR.OOOO, verificação módulo 97 (Res. CNJ 65/2008)."""
    d = _digitos(s)
    if len(d) != 20:
        return False
    n, dv, resto = d[:7], d[7:9], d[9:]
    return int(n + resto + dv) % 97 == 1
