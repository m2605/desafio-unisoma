"""Gera docs/Desenho_da_Solucao.pdf (entrega 'Desenho da solução' do hackathon)."""
from __future__ import annotations

import io
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import (Image, Paragraph, SimpleDocTemplate, Spacer, Table,  # noqa: E402
                                TableStyle)

AQUI = os.path.dirname(os.path.abspath(__file__))
fonte = font_manager.findfont("DejaVu Sans")
pdfmetrics.registerFont(TTFont("DejaVu", fonte))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", fonte.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold", italic="DejaVu",
                              boldItalic="DejaVu-Bold")
AZUL = colors.HexColor("#1F4E79")

st_t = ParagraphStyle("t", fontName="DejaVu-Bold", fontSize=17, textColor=AZUL, leading=21, spaceAfter=2)
st_st = ParagraphStyle("st", fontName="DejaVu", fontSize=9.5, textColor=colors.HexColor("#595959"))
st_h = ParagraphStyle("h", fontName="DejaVu-Bold", fontSize=11.5, textColor=AZUL, spaceBefore=9,
                      spaceAfter=3)
st_n = ParagraphStyle("n", fontName="DejaVu", fontSize=8.8, leading=12)
st_p = ParagraphStyle("p", fontName="DejaVu", fontSize=7.8, leading=10)


def formula(linhas: list[tuple[str, str]], largura_cm=17.5):
    """Renderiza linhas (latex, comentário) com mathtext do matplotlib."""
    alt = 0.36 * len(linhas) + 0.1
    fig = plt.figure(figsize=(largura_cm / 2.54, alt), dpi=220)
    for k, (tex, com) in enumerate(linhas):
        y = 1 - (k + 0.6) / len(linhas)
        fig.text(0.02, y, f"${tex}$", fontsize=10.5, va="center")
        if com:
            fig.text(0.64, y, com, fontsize=8.5, va="center", color="#555555")
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=largura_cm * cm, height=alt * 2.54 * cm)


def tabela(dados, larg, cab=True):
    t = Table([[Paragraph(str(c), st_p) for c in row] for row in dados], colWidths=larg)
    est = [("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#BFBFBF")),
           ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    if cab:
        est += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDEBF7"))]
    t.setStyle(TableStyle(est))
    return t


def main():
    s = [Paragraph("Desenho da Solução — Ensalamento ABC Aprendiz", st_t),
         Paragraph("Desafio UniSoma 2026 · Programação Linear Inteira Mista (MILP) · "
                   "Python 3.12.9 + PuLP + HiGHS", st_st), Spacer(1, 6)]

    s.append(Paragraph("1. Visão geral", st_h))
    s.append(Paragraph(
        "Cada aluno só pode ir para turmas do seu turno, então o problema se separa em dois "
        "subproblemas independentes (Manhã e Tarde). Cada um é resolvido por uma "
        "<b>decomposição exata em dois MILPs</b>: a Fase 1 decide quantas meninas e meninos vão "
        "para cada turma (objetivo lexicográfico de equilíbrio) e a Fase 2 atribui cada aluno a uma "
        "turma respeitando essas quantidades.", st_n))
    s.append(Spacer(1, 4))
    s.append(tabela([
        ["Etapa", "O que faz"],
        ["ETL", "Lê o Excel, acha abas/cabeçalho sem diferenciar maiúsculas/acentos, padroniza "
                "Sexo (M/F) e Turno (Manhã/Tarde), registra TODAS as inconsistências de uma vez. "
                "Linhas com nome vazio, sexo ou turno inválido não são alocadas."],
        ["MILP Fase 1", "Dimensionamento: variáveis inteiras f<sub>t</sub>, m<sub>t</sub> por turma; "
                        "equilíbrio de quantidade (hard) e de gênero (objetivo)."],
        ["MILP Fase 2", "Atribuição: binárias x<sub>i,t</sub>; separa homônimos em turmas diferentes."],
        ["Saída", "Abas 'Ensalamento' e 'Inconsistências' no mesmo Excel + Relatório Resumo em PDF."],
    ], [2.6 * cm, 14.9 * cm]))

    s.append(Paragraph("2. Notação", st_h))
    s.append(Paragraph(
        "I: alunos válidos do turno (I<sub>F</sub> meninas, I<sub>M</sub> meninos) · T: turmas do "
        "turno · C: vagas por turma · w<sub>i</sub> = |I| − posição de i na ordem de matrícula "
        "(peso maior para quem se matriculou antes) · "
        "N = min(|I|, |T|·C) · p<sub>F</sub> = |I<sub>F</sub>|/|I| · G: grupos de homônimos.", st_n))

    s.append(Paragraph("3. Fase 1 — dimensionamento das turmas (MILP lexicográfico)", st_h))
    s.append(Paragraph("Variáveis: z<sub>i</sub> ∈ {0,1} (aluno recebe vaga); f<sub>t</sub>, "
                       "m<sub>t</sub> ∈ ℤ<sub>+</sub> (meninas/meninos na turma t); "
                       "S<sup>±</sup>, F<sup>±</sup>, M<sup>±</sup> ≥ 0 (maior/menor valor); "
                       "d<sub>t</sub> ≥ 0 (desvio de proporção).", st_n))
    s.append(formula([
        (r"\sum_{i \in I} z_i = N", "aloca todos que cabem"),
        (r"\sum_{t} f_t = \sum_{i \in I_F} z_i,\quad \sum_{t} m_t = \sum_{i \in I_M} z_i", "conservação por sexo"),
        (r"f_t + m_t \leq C \quad \forall t", "capacidade"),
        (r"S^- \leq f_t + m_t \leq S^+,\ F^- \leq f_t \leq F^+,\ M^- \leq m_t \leq M^+", "linearização de max/min"),
        (r"S^+ - S^- \leq 1", "equilíbrio de quantidade (hard)"),
        (r"f_t + m_t \geq f_{t+1} + m_{t+1}", "quebra de simetria"),
        (r"-d_t \leq f_t - p_F\,(f_t + m_t) \leq d_t \quad \forall t", "linearização de |·|"),
    ]))
    s.append(Paragraph("<b>Objetivo lexicográfico</b> — cada nível é otimizado e seu valor ótimo "
                       "vira restrição do nível seguinte (um critério menos importante nunca piora "
                       "um mais importante):", st_n))
    s.append(formula([
        (r"N1:\ \min \sum_{i} w_i\,(1 - z_i)", "se faltar vaga: saem os últimos"),
        (r"N2:\ \min\ S^+ - S^-", "turmas do mesmo tamanho"),
        (r"N3:\ \min\ (F^+ - F^-) + (M^+ - M^-)", "gênero espalhado igualmente"),
        (r"N4:\ \min \sum_{t} d_t", "proporção de meninas ≈ a do turno"),
    ]))

    s.append(Paragraph("4. Fase 2 — atribuição aluno → turma (MILP)", st_h))
    s.append(Paragraph("Variáveis: x<sub>i,t</sub> ∈ {0,1} (aluno i na turma t); u<sub>g</sub> ≥ 0 "
                       "(maior nº de homônimos do grupo g numa mesma turma). f*, m*, z* vêm da "
                       "Fase 1.", st_n))
    s.append(formula([
        (r"\min \sum_{g \in G} u_g", "espalhar homônimos entre turmas"),
        (r"\sum_{t} x_{i,t} = z_i^* \quad \forall i", "cada aluno em uma turma"),
        (r"\sum_{i \in I_F} x_{i,t} = f_t^*,\quad \sum_{i \in I_M} x_{i,t} = m_t^* \quad \forall t", "quantidades ótimas"),
        (r"\sum_{i \in g} x_{i,t} \leq u_g \quad \forall g, t", "homônimos"),
    ]))

    s.append(Paragraph("5. Por que a decomposição é exata e rápida", st_h))
    s.append(Paragraph(
        "Alunos do mesmo sexo são intercambiáveis para N2–N4; logo todo (f*, m*) ótimo da Fase 1 é "
        "realizável por alguma atribuição individual, e a Fase 2 escolhe a melhor para os homônimos. "
        "Sem a restrição de homônimos a Fase 2 é um <b>problema de transporte</b> (matriz totalmente "
        "unimodular: a relaxação linear já é inteira). A decomposição elimina a simetria do modelo "
        "x<sub>i,t</sub> puro (turmas idênticas geram |T|! soluções equivalentes): "
        "<b>900 alunos em 26 turmas em ~1 s</b>, contra mais de 90 s sem solução no modelo "
        "monolítico. Solver: HiGHS (branch-and-cut) via PuLP; CBC como alternativa.", st_n))

    s.append(Paragraph("6. Resultados nas instâncias fornecidas (validador oficial: todas APROVADAS)", st_h))
    s.append(tabela([
        ["Instância", "Alunos ensalados", "Turmas (M+T)", "Tamanhos das turmas", "Maior desvio de gênero"],
        ["1", "120 / 120", "2 + 2", "30, 30 | 30, 30", "1,7 p.p."],
        ["2", "160 / 160", "3 + 3", "25, 24, 24 | 29, 29, 29", "2,4 p.p."],
        ["3", "165 / 165", "5 + 1", "28 ×5 | 25", "2,9 p.p."],
        ["4", "147 / 155 (8 linhas inválidas)", "3 + 3", "27, 26, 26 | 23, 23, 22", "2,2 p.p."],
    ], [2.0 * cm, 4.2 * cm, 2.4 * cm, 4.9 * cm, 4.0 * cm]))
    s.append(Spacer(1, 3))
    s.append(Paragraph("Os desvios de gênero restantes são o mínimo matematicamente possível com números "
                       "inteiros (ex.: 61 meninos em 5 turmas → 13/12/12/12/12).", st_p))

    destino = os.path.join(AQUI, "Desenho_da_Solucao.pdf")
    SimpleDocTemplate(destino, pagesize=A4, leftMargin=1.6 * cm, rightMargin=1.6 * cm,
                      topMargin=1.3 * cm, bottomMargin=1.2 * cm,
                      title="Desenho da Solução - Ensalamento").build(s)
    print("Gerado:", destino)


if __name__ == "__main__":
    main()
