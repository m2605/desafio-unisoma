"""Testes da solução monolítica: regras de negócio verificadas de forma independente do modelo."""
from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
from collections import Counter

import pytest
from openpyxl import load_workbook

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from ensalamento_mono.etl import ERRO, normalizar  # noqa: E402
from ensalamento_mono.pipeline import executar  # noqa: E402

DADOS = os.path.join(os.path.dirname(RAIZ), "dados")
INSTANCIAS = sorted(glob.glob(os.path.join(DADOS, "instancias", "*.xlsx")))


@pytest.fixture(scope="session")
def cenarios(tmp_path_factory):
    pasta = tmp_path_factory.mktemp("cenarios")
    subprocess.run([sys.executable, os.path.join(RAIZ, "scripts", "gerar_cenarios_teste.py"),
                    str(pasta)], check=True)
    return pasta


def _rodar(origem, tmp_path):
    copia = tmp_path / os.path.basename(origem)
    shutil.copyfile(origem, copia)
    res = executar(str(copia), gerar_relatorio=False)
    return res, str(copia)


def _checar_regras(res, caminho):
    cen = res.cenario
    wb = load_workbook(caminho, read_only=True)
    assert "Ensalamento" in wb.sheetnames and "Inconsistências" in wb.sheetnames
    linhas = list(wb["Ensalamento"].iter_rows(values_only=True))
    assert list(linhas[0]) == ["Nome", "Sexo", "Disponibilidade", "Turma"]
    dados = linhas[1:]
    cfg = cen.turnos_config()
    n_m, n_t = cfg["Manhã"][0], cfg["Tarde"][0]
    letras = [chr(65 + i) for i in range(n_m + n_t)]
    validas = {f"MANHÃ - {l}": ("Manhã", cfg["Manhã"][1]) for l in letras[:n_m]}
    validas |= {f"TARDE - {l}": ("Tarde", cfg["Tarde"][1]) for l in letras[n_m:]}
    ocup = Counter()
    for nome, sexo, disp, turma in dados:
        assert turma in validas, turma                       # nomenclatura
        assert validas[turma][0] == disp                     # turno correto
        assert sexo in ("M", "F")
        ocup[turma] += 1
    for t, n in ocup.items():
        assert n <= validas[t][1]                            # capacidade
    for turno in ("Manhã", "Tarde"):                         # equilíbrio de quantidade
        tam = [ocup[t] for t, (p, _) in validas.items() if p == turno]
        if tam:
            assert max(tam) - min(tam) <= 1, (turno, tam)
    # todos os válidos que cabem foram alocados (cada homônimo conta)
    esperado = Counter(a.nome for a in cen.alunos)
    obtido = Counter(r[0] for r in dados)
    for nome, k in obtido.items():
        assert k <= esperado[nome]
    sem_vaga = sum(len(r.nao_alocados) for r in res.turnos.values())
    assert sum(obtido.values()) == len(cen.alunos) - sem_vaga
    # quem ficou fora tem ERRO registrado
    texto = " | ".join(i.descricao + " " + i.nome for i in cen.inconsistencias if i.tipo == ERRO)
    for r in res.turnos.values():
        for a in r.nao_alocados:
            assert a.nome in texto
    wb.close()
    return ocup


@pytest.mark.parametrize("arq", INSTANCIAS, ids=os.path.basename)
def test_instancias_oficiais(arq, tmp_path):
    res, caminho = _rodar(arq, tmp_path)
    assert not res.cenario.bloqueante
    _checar_regras(res, caminho)
    # equilíbrio de gênero: amplitude de meninas e de meninos <= 1 por turno
    for turno in ("Manhã", "Tarde"):
        est = [e for e in res.estatisticas if e.turno == turno]
        assert max(e.meninas for e in est) - min(e.meninas for e in est) <= 1
        assert max(e.meninos for e in est) - min(e.meninos for e in est) <= 1


def test_instancia4_dados_sujos(tmp_path):
    res, _ = _rodar(os.path.join(DADOS, "instancias", "instancia_4.xlsx"), tmp_path)
    nomes = {a.nome for a in res.cenario.alunos}
    assert "Heloísa Cavalcanti Rodrigues Dias" not in nomes   # sexo 'X'
    assert "Theo Moreira Soares Monteiro" not in nomes        # 'Integral'
    assert "Clara Ribeiro Soares" in nomes                    # 'feminino' corrigido
    assert "Vinícius Machado de Almeida" in nomes             # 'manha' corrigido
    assert any(i.linha == 102 and i.tipo == ERRO for i in res.cenario.inconsistencias)
    assert res.ensalados == 147


def test_cabecalho_errado_e_corrigido(tmp_path):
    _, caminho = _rodar(os.path.join(DADOS, "instancias", "instancia_1.xlsx"), tmp_path)
    wb = load_workbook(caminho, read_only=True)
    assert normalizar(next(wb["Alunos"].iter_rows(values_only=True))[0]) == "NOME"


def test_cenarios_extremos(cenarios, tmp_path):
    for arq in sorted(glob.glob(str(cenarios / "*.xlsx"))):
        if "c02_grande_900" in arq:  # ~2 min neste modelo; validado à parte
            continue
        res, caminho = _rodar(arq, tmp_path)
        if res.cenario.bloqueante:
            assert res.contagem(ERRO) > 0 and res.ensalados == 0
            continue
        _checar_regras(res, caminho)


def test_superlotacao_prioriza_ordem(cenarios, tmp_path):
    res, _ = _rodar(str(cenarios / "c01_superlotacao.xlsx"), tmp_path)
    manha = res.turnos["Manhã"]
    assert len(manha.nao_alocados) == 20
    alocados = [a for a in res.cenario.alunos if a.ordem in manha.alocacao]
    assert max(a.ordem for a in alocados) < min(a.ordem for a in manha.nao_alocados)


def test_modelo_original_do_documento(tmp_path):
    """O modelo exatamente como no PDF (sem correções) também roda e respeita as regras."""
    from ensalamento_mono.etl import ler_cenario
    from ensalamento_mono.modelo_monolitico import Opcoes, resolver
    cen = ler_cenario(os.path.join(DADOS, "instancias", "instancia_1.xlsx"))
    res = resolver(cen.alunos, cen.turnos_config(), Opcoes.original())
    assert sum(len(r.alocacao) for r in res.values()) == len(cen.alunos)
    for r in res.values():
        tam = Counter(r.alocacao.values())
        assert max(tam.values()) - min(tam.values()) <= 1
