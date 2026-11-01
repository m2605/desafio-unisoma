"""
Versão enxuta do pitch: capa, equipe, 3 slides de conteúdo (Problema, Como resolvemos,
Impacto) e obrigado.

Uso: python solucao_monolitica/docs/gerar_slides_curto.py <template.pptx> <saida.pptx> <equipe.json>
"""
from __future__ import annotations

import json
import os
import sys

from pptx import Presentation

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gerar_slides import (AQUI, escrever, imagem_em_caixa, preencher_equipe, remover,  # noqa: E402
                          shape)


def titulo(sh, cinza: str, vermelho: str):
    """Título de dois tons do template: 1º trecho cinza, 2º trecho vermelho."""
    runs = sh.text_frame.paragraphs[0].runs
    runs[0].text = cinza
    runs[1].text = vermelho
    for r in runs[2:]:
        r._r.getparent().remove(r._r)


def main():
    template, saida, arq_equipe = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(arq_equipe, encoding="utf-8") as fh:
        eq = json.load(fh)
    num, sol = eq["numero"], eq["solucao"]
    nomes = ", ".join(m["nome"] for m in eq["membros"])

    prs = Presentation(template)
    sl = list(prs.slides)
    for s in sl:
        if s.element.get("show") is not None:
            del s.element.attrib["show"]
        for sh in s.shapes:
            if sh.has_text_frame and sh.text_frame.text.strip() == "Equipe [00]":
                escrever(sh, f"Equipe {num}")

    # ---- capa
    escrever(shape(sl[1], 117), sol)
    escrever(shape(sl[1], 118), f"Equipe {num}")

    # ---- equipe (fotos e LinkedIn)
    preencher_equipe(sl[2], eq["membros"])

    # ---- 1) O problema
    escrever(shape(sl[3], 171), "Todo semestre, centenas de jovens são distribuídos em turmas "
             "à mão: horas de trabalho, turmas desequilibradas e erros de cadastro descobertos "
             "tarde demais.")
    escrever(shape(sl[3], 178), "Turno: aluno da manhã só em turma da manhã; da tarde, só na tarde")
    escrever(shape(sl[3], 182), "Capacidade: nenhuma turma acima do limite de vagas")
    escrever(shape(sl[3], 186), "Equilíbrio: no máx. 1 aluno de diferença e gênero proporcional")
    escrever(shape(sl[3], 190), "Dados com erro: avisar todas as inconsistências de uma só vez")

    # ---- 2) Como resolvemos (layout do slide do aplicativo)
    titulo(shape(sl[6], 255), "Como ", "resolvemos")
    remover(shape(sl[6], 258))
    remover(shape(sl[6], 259))
    imagem_em_caixa(sl[6], shape(sl[6], 257), os.path.join(AQUI, "img", "enturme_4_resultado.png"))
    escrever(shape(sl[6], 262), "Enturme")
    escrever(shape(sl[6], 266), "Modelo de otimização (MILP + HiGHS): ninguém sem sala, turmas "
             "iguais e gênero equilibrado")
    escrever(shape(sl[6], 270), "Arrasta a planilha e confirma: em ~1 s as turmas estão no Excel, "
             "com relatório PDF")
    escrever(shape(sl[6], 274), "4 de 4 instâncias aprovadas no validador oficial, com solução "
             "ótima provada")

    # ---- 3) Impacto
    escrever(shape(sl[8], 312), "Horas de planilha manual, conferência de vagas e proporções, "
             "erros encontrados só depois.")
    escrever(shape(sl[8], 317), "Dois cliques: turmas ótimas em segundos e todas as pendências "
             "listadas de uma vez.")
    escrever(shape(sl[8], 323), "Equipe livre para focar na formação dos jovens; turmas justas "
             "e decisões transparentes.")

    # ---- obrigado
    remover(shape(sl[9], 333))   # encerramento: só "Obrigado"
    remover(shape(sl[9], 334))

    # mantém: capa(1), equipe(2), problema(3), como resolvemos(6), impacto(8), obrigado(9)
    manter = {1, 2, 3, 6, 8, 9}
    lst = prs.slides._sldIdLst
    for idx, sld in reversed(list(enumerate(list(lst)))):
        if idx not in manter:
            prs.part.drop_rel(sld.rId)
            lst.remove(sld)
    prs.save(saida)
    print("Gerado:", saida, "|", len(prs.slides), "slides")


if __name__ == "__main__":
    main()
