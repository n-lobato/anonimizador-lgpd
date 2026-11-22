"""Linha de comando: os códigos de saída prometidos no README e o que cada opção faz.
Quem usa o programa em scripts depende desses códigos para saber se pode seguir."""

import os

import pytest

from anonimizador import cli
from anonimizador.processador import PASTA_RELATORIO, PASTA_SAIDA_PADRAO

FRASE = "Requerente: Pedro Henrique Alves, CPF 529.982.247-25, telefone (61) 99876-5432."


@pytest.fixture
def pasta(tmp_path):
    p = tmp_path / "processo"
    p.mkdir()
    (p / "peticao.txt").write_text(FRASE, encoding="utf-8")
    return p


def _saida(pasta):
    return pasta / PASTA_SAIDA_PADRAO / "peticao_anonimizado.txt"


def test_tudo_certo_sai_com_zero_e_avisa_que_nao_houve_revisao(pasta, capsys):
    assert cli.main([str(pasta)]) == 0
    texto = _saida(pasta).read_text(encoding="utf-8")
    assert "529.982.247-25" not in texto and "Pedro Henrique Alves" not in texto
    out = capsys.readouterr().out
    assert "[ok]" in out and "Sem revisão manual" in out


def test_sem_arquivo_suportado_sai_com_um(tmp_path, capsys):
    (tmp_path / "foto.heic").write_bytes(b"x")
    assert cli.main([str(tmp_path / "foto.heic")]) == 1
    assert "Nenhum arquivo suportado" in capsys.readouterr().out


def test_arquivo_com_erro_sai_com_dois_e_processa_os_outros(pasta, capsys):
    (pasta / "estragado.docx").write_bytes(os.urandom(2048))
    assert cli.main([str(pasta)]) == 2
    out = capsys.readouterr().out
    assert "[erro] estragado.docx" in out
    assert _saida(pasta).exists()


def test_alerta_sai_com_tres(pasta, capsys, monkeypatch):
    import anonimizador.processador as proc
    monkeypatch.setattr(proc, "procurar_residuos",
                        lambda destino, registro: ["ATENÇÃO: a verificação final encontrou um dado."])
    assert cli.main([str(pasta)]) == 3
    assert "revise esses primeiro" in capsys.readouterr().out


def test_apenas_analisar_nao_grava_nada(pasta, capsys):
    assert cli.main([str(pasta), "--apenas-analisar"]) == 0
    assert not (pasta / PASTA_SAIDA_PADRAO).exists()
    assert "CPF" in capsys.readouterr().out


def test_tipos_limita_o_que_e_trocado(pasta):
    assert cli.main([str(pasta), "--tipos", "CPF"]) == 0
    texto = _saida(pasta).read_text(encoding="utf-8")
    assert "529.982.247-25" not in texto
    assert "Pedro Henrique Alves" in texto and "99876-5432" in texto


def test_pasta_de_saida_escolhida(pasta, tmp_path):
    destino = tmp_path / "entregar"
    assert cli.main([str(pasta), "-o", str(destino)]) == 0
    assert (destino / "processo" / "peticao_anonimizado.txt").exists()  # mantém o nome da pasta
    assert not (pasta / PASTA_SAIDA_PADRAO).exists()


def test_relatorio_so_quando_pedido_e_fora_da_saida(pasta, capsys):
    assert cli.main([str(pasta)]) == 0
    assert not (pasta / PASTA_RELATORIO).exists()
    assert cli.main([str(pasta), "--relatorio"]) == 0
    relatorios = list((pasta / PASTA_RELATORIO).iterdir())
    assert relatorios, "o relatório pedido não foi gerado"
    assert not any(PASTA_SAIDA_PADRAO in r.parts for r in relatorios)
    assert "não compartilhe" in capsys.readouterr().out


def test_relatorio_vai_para_configuracoes_se_cairia_na_saida(pasta, tmp_path):
    """Com a saída na pasta do relatório, ele não pode ficar junto do que será enviado."""
    from anonimizador.config import pasta_config
    assert cli.main([str(pasta), "--relatorio", "-o", str(pasta / PASTA_RELATORIO)]) == 0
    assert list((pasta_config() / "relatorios").iterdir())
    assert [p.name for p in (pasta / PASTA_RELATORIO).rglob("*") if p.is_file()] == ["peticao_anonimizado.txt"]


def test_listar_tipos(capsys):
    assert cli.main(["--listar-tipos"]) == 0
    out = capsys.readouterr().out
    assert "CPF" in out and "PESSOA" in out
