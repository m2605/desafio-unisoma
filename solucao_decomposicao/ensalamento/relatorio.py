"""Relatório Resumo da Distribuição (PDF)."""
from __future__ import annotations

import io
import os
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.platypus import (Image, Paragraph, SimpleDocTemplate, Spacer, Table,  # noqa: E402
                                TableStyle)

from .etl import ALERTA, CORRIGIDO, ERRO, ORDEM_TURNOS  # noqa: E402

AZUL = colors.HexColor("#1F4E79")
AZUL_CLARO = colors.HexColor("#DDEBF7")
COR_M = "#2E75B6"
COR_F = "#C55A9E"


def _grafico(res) -> io.BytesIO | None:
    est = [e for e in res.estatisticas]
    if not est:
        return None
    fig, ax = plt.subplots(figsize=(8.2, 3.3), dpi=150)
    nomes = [e.turma for e in est]
    m = [e.meninos for e in est]
    f = [e.meninas for e in est]
    ax.bar(nomes, m, color=COR_M, label="Meninos (M)")
    ax.bar(nomes, f, bottom=m, color=COR_F, label="Meninas (F)")
    for i, e in enumerate(est):
        ax.text(i, e.total + 0.4, str(e.total), ha="center", va="bottom", fontsize=8)
        ax.plot([i - 0.4, i + 0.4], [e.vagas, e.vagas], color="#444", lw=1, ls="--")
    ax.set_ylabel("Alunos")
    ax.set_title("Alunos por turma (linha tracejada = capacidade)", fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2)
    plt.xticks(fontsize=7, rotation=0 if len(est) <= 8 else 45)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf


def _tabela(dados, larguras, zebra=True):
    t = Table(dados, colWidths=larguras, repeatRows=1)
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#BFBFBF")),
    ]
    if zebra:
        for r in range(1, len(dados)):
            if r % 2 == 0:
                estilo.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#F2F2F2")))
    t.setStyle(TableStyle(estilo))
    return t


def gerar_pdf(res, caminho: str) -> str:
    cen = res.cenario
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], textColor=AZUL, fontSize=18, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=AZUL, fontSize=12, spaceBefore=10)
    normal = ParagraphStyle("n", parent=ss["Normal"], fontSize=9, leading=12)
    pequeno = ParagraphStyle("p", parent=ss["Normal"], fontSize=7.5, leading=9.5)
    kpi_v = ParagraphStyle("kv", parent=ss["Normal"], fontSize=16, alignment=TA_CENTER,
                           textColor=AZUL, fontName="Helvetica-Bold", leading=18)
    kpi_l = ParagraphStyle("kl", parent=ss["Normal"], fontSize=7.5, alignment=TA_CENTER,
                           textColor=colors.HexColor("#595959"))

    story = [Paragraph("Relatório Resumo do Ensalamento", h1),
             Paragraph(f"ABC Aprendiz &nbsp;·&nbsp; Arquivo: <b>{os.path.basename(cen.caminho)}</b>"
                       f" &nbsp;·&nbsp; Gerado em {datetime.now():%d/%m/%Y %H:%M}", normal),
             Spacer(1, 8)]

    # KPIs
    erros, alertas, corr = res.contagem(ERRO), res.contagem(ALERTA), res.contagem(CORRIGIDO)
    kpis = [(str(cen.total_linhas), "matriculados (linhas lidas)"),
            (str(res.ensalados), "alunos ensalados"),
            (str(cen.total_linhas - res.ensalados), "não ensalados"),
            (str(sum(1 for e in res.estatisticas)), "turmas"),
            (f"{erros} / {alertas} / {corr}", "erros / alertas / correções")]
    t = Table([[Paragraph(v, kpi_v) for v, _ in kpis], [Paragraph(l, kpi_l) for _, l in kpis]],
              colWidths=[3.5 * cm] * 5)
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, AZUL),
                           ("INNERGRID", (0, 0), (-1, -1), 0.25, AZUL_CLARO),
                           ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FBFF")),
                           ("TOPPADDING", (0, 0), (-1, -1), 6)]))
    story += [t, Spacer(1, 6)]

    if cen.bloqueante:
        story.append(Paragraph("<font color='#C00000'><b>O ensalamento não pôde ser executado.</b>"
                               "</font> Corrija os erros listados abaixo e rode novamente.", normal))

    # Tabela por turma
    if res.estatisticas:
        story.append(Paragraph("Distribuição por turma", h2))
        dados = [["Turma", "Vagas", "Alunos", "Ocupação", "Meninos", "Meninas", "% Meninas",
                  "% Men. turno", "Desvio (p.p.)"]]
        for turno in ORDEM_TURNOS:
            ests = [e for e in res.estatisticas if e.turno == turno]
            tot = sum(e.total for e in ests)
            pf = sum(e.meninas for e in ests) / tot if tot else 0
            for e in ests:
                dados.append([e.turma, e.vagas, e.total,
                              f"{e.total / e.vagas:.0%}" if e.vagas else "-",
                              e.meninos, e.meninas, f"{e.pct_meninas:.1%}" if e.total else "-",
                              f"{pf:.1%}", f"{(e.pct_meninas - pf) * 100:+.1f}" if e.total else "-"])
        story.append(_tabela(dados, [2.4 * cm, 1.3 * cm, 1.4 * cm, 1.7 * cm, 1.6 * cm, 1.6 * cm,
                                     1.8 * cm, 2.6 * cm, 2.0 * cm]))
        g = _grafico(res)
        if g:
            story += [Spacer(1, 6), Image(g, width=17 * cm, height=6.8 * cm)]

    # Modelo matemático
    if res.turnos:
        story.append(Paragraph("Otimização (modelo matemático)", h2))
        story.append(Paragraph(
            "Cada turno é resolvido por Programação Linear Inteira Mista (MILP) em duas fases exatas. "
            "<b>Fase 1</b> (dimensionamento): variáveis inteiras de meninas/meninos por turma, "
            "capacidade, diferença máxima de 1 aluno entre turmas e objetivo lexicográfico "
            "(prioridade de matrícula &gt; equilíbrio de quantidade &gt; equilíbrio de gênero &gt; "
            "proporção de meninas). <b>Fase 2</b> (atribuição): variáveis binárias "
            "x<sub>i,t</sub> (aluno i na turma t) que respeitam as quantidades ótimas e separam "
            "homônimos.", normal))
        dados = [["Turno", "Solver", "Status", "Variáveis", "Restrições", "Nível do objetivo",
                  "Valor ótimo", "Tempo (s)"]]
        for turno, r in res.turnos.items():
            if not r.etapas:
                dados.append([turno, r.solver or "-", r.status, "-", "-", "-", "-", "-"])
            for k, e in enumerate(r.etapas):
                dados.append([turno if k == 0 else "", r.solver if k == 0 else "",
                              e.status, r.n_variaveis if k == 0 else "",
                              r.n_restricoes if k == 0 else "",
                              Paragraph(e.nome, pequeno), f"{e.valor:g}", f"{e.segundos:.2f}"])
        story.append(_tabela(dados, [1.5 * cm, 1.4 * cm, 1.5 * cm, 1.6 * cm, 1.7 * cm, 5.6 * cm,
                                     1.7 * cm, 1.5 * cm], zebra=False))

    # Inconsistências
    if cen.inconsistencias:
        story.append(Paragraph("Inconsistências encontradas", h2))
        story.append(Paragraph("ERRO = impede a alocação · ALERTA = conferir · "
                               "CORRIGIDO = tratado automaticamente. A lista completa está na aba "
                               "'Inconsistências' da planilha.", pequeno))
        ordem = {ERRO: 0, ALERTA: 1, CORRIGIDO: 2}
        incs = sorted(cen.inconsistencias, key=lambda i: (ordem.get(i.tipo, 9), i.linha or 0))
        dados = [["Tipo", "Linha", "Descrição"]]
        for i in incs[:80]:
            dados.append([i.tipo, i.linha or "", Paragraph(i.descricao, pequeno)])
        t = _tabela(dados, [2.0 * cm, 1.2 * cm, 14.6 * cm])
        cores = {ERRO: "#FFC7CE", ALERTA: "#FFEB9C", CORRIGIDO: "#DDEBF7"}
        t.setStyle(TableStyle([("BACKGROUND", (0, r), (0, r), colors.HexColor(cores[incs[r - 1].tipo]))
                               for r in range(1, len(dados)) if incs[r - 1].tipo in cores]))
        story.append(t)
        if len(incs) > 80:
            story.append(Paragraph(f"... e mais {len(incs) - 80} itens (veja a planilha).", pequeno))

    doc = SimpleDocTemplate(caminho, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm,
                            topMargin=1.3 * cm, bottomMargin=1.3 * cm,
                            title="Relatório Resumo do Ensalamento", author="Ensalamento ABC Aprendiz")
    doc.build(story)
    return caminho
