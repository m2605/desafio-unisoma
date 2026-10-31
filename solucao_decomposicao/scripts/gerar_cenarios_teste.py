"""
Gera cenários de teste "difíceis" para tentar quebrar a aplicação.

Uso:  python scripts/gerar_cenarios_teste.py cenarios_teste
"""
from __future__ import annotations

import os
import random
import sys

from openpyxl import Workbook

NOMES = ["Ana", "Bruno", "Carla", "Daniel", "Eduarda", "Felipe", "Gabriela", "Heitor", "Isabela",
         "João", "Larissa", "Miguel", "Natália", "Otávio", "Paula", "Rafael", "Sofia", "Thiago",
         "Valentina", "Vinícius", "Beatriz", "Lucas", "Mariana", "Pedro", "Júlia", "Arthur"]
SOBRENOMES = ["Silva", "Souza", "Oliveira", "Santos", "Pereira", "Lima", "Costa", "Ferreira",
              "Almeida", "Rodrigues", "Gomes", "Martins", "Araújo", "Barbosa", "Ribeiro", "Dias"]


def nome(rng):
    return f"{rng.choice(NOMES)} {rng.choice(SOBRENOMES)} {rng.choice(SOBRENOMES)}"


def salvar(caminho, alunos, turmas, cab=("Nome", "Sexo", "Disponibilidade"), prefixo=None):
    wb = Workbook()
    ws = wb.active
    ws.title = "Alunos"
    if prefixo:
        for linha in prefixo:
            ws.append(linha)
    ws.append(list(cab))
    for a in alunos:
        ws.append(list(a))
    wt = wb.create_sheet("Turmas")
    wt.append(["Recursos", "Quantidade"])
    for k, v in turmas:
        wt.append([k, v])
    wb.save(caminho)


def alunos_aleatorios(rng, n_manha, n_tarde, pf=0.5):
    out = []
    for turno, n in (("Manhã", n_manha), ("Tarde", n_tarde)):
        for _ in range(n):
            out.append((nome(rng), "F" if rng.random() < pf else "M", turno))
    rng.shuffle(out)
    return out


def main():
    dest = sys.argv[1]
    os.makedirs(dest, exist_ok=True)
    rng = random.Random(2026)
    cfg = lambda tm, tt, vm, vt: [("turmas_manha", tm), ("turmas_tarde", tt),  # noqa: E731
                                  ("vagas_manha", vm), ("vagas_tarde", vt)]

    # 1. Superlotação na manhã (100 alunos, 2x40 vagas)
    salvar(f"{dest}/c01_superlotacao.xlsx", alunos_aleatorios(rng, 100, 50), cfg(2, 2, 40, 30))
    # 2. Grande: 900 alunos, 13+13 turmas
    salvar(f"{dest}/c02_grande_900.xlsx", alunos_aleatorios(rng, 450, 450, 0.37), cfg(13, 13, 40, 40))
    # 3. Poucos alunos e muitas turmas (turmas vazias)
    salvar(f"{dest}/c03_poucos_alunos.xlsx", alunos_aleatorios(rng, 3, 2), cfg(4, 4, 30, 30))
    # 4. Só um sexo
    salvar(f"{dest}/c04_so_meninas.xlsx", alunos_aleatorios(rng, 40, 40, 1.0), cfg(3, 2, 20, 25))
    # 5. Aba Turmas com erros (texto, chaves com maiúsculas/espaço, faltando chave)
    salvar(f"{dest}/c05_turmas_com_erro.xlsx", alunos_aleatorios(rng, 30, 30),
           [(" Turmas_Manha ", "2"), ("TURMAS_TARDE", "dois"), ("vagas_manha", 20)])
    # 6. Sem turmas na tarde mas com alunos na tarde
    salvar(f"{dest}/c06_sem_turma_tarde.xlsx", alunos_aleatorios(rng, 40, 10), cfg(2, 0, 30, 0))
    # 7. Dados sujos variados + cabeçalho deslocado + colunas trocadas
    sujos = alunos_aleatorios(rng, 30, 30)
    sujos = [(s, d, n) for n, s, d in sujos]  # ordem das colunas trocada
    sujos += [("masculino", "MANHÃ", "Carlos Dirty Um"), ("Fem", "tarde", "Carla Dirty Dois"),
              ("f", "  manhã  ", "  Ana   Espaços  "), ("M", "Manha/Tarde", "Integral Pessoa"),
              ("", "", ""), (None, "Tarde", None), ("M", 7, "Numero Turno"),
              ("F", "Tarde", "joão da silva"), ("F", "Tarde", "João da Silva")]
    salvar(f"{dest}/c07_sujo_colunas_trocadas.xlsx", sujos, cfg(2, 2, 35, 35),
           cab=("Sexo", "Disponibilidade", "Nome do Aluno"),
           prefixo=[["Lista de matriculados 2026/1"], []])
    # 8. Lista vazia
    salvar(f"{dest}/c08_vazia.xlsx", [], cfg(2, 2, 35, 35))
    # 9. Muitos homônimos
    hom = [(f"Maria Souza", "F", "Manhã")] * 6 + [(f"José Lima", "M", "Tarde")] * 4
    hom += alunos_aleatorios(rng, 30, 30)
    salvar(f"{dest}/c09_homonimos.xlsx", hom, cfg(3, 2, 30, 30))
    # 10. Capacidade exata
    salvar(f"{dest}/c10_capacidade_exata.xlsx", alunos_aleatorios(rng, 60, 25), cfg(2, 1, 30, 25))
    print("Cenários gerados em", dest)


if __name__ == "__main__":
    main()
