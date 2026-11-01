"""Gera docs/Manual_do_Usuario_Enturme.pdf (interface Enturme ABC)."""
from __future__ import annotations

import os

from matplotlib import font_manager
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

AQUI = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(AQUI, "img")
fonte = font_manager.findfont("DejaVu Sans")
pdfmetrics.registerFont(TTFont("DejaVu", fonte))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", fonte.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold", italic="DejaVu",
                              boldItalic="DejaVu-Bold")
AZUL = colors.HexColor("#2A4598")

T = ParagraphStyle("t", fontName="DejaVu-Bold", fontSize=22, textColor=AZUL, leading=27)
ST = ParagraphStyle("st", fontName="DejaVu", fontSize=11, textColor=colors.HexColor("#595959"),
                    leading=15)
H = ParagraphStyle("h", fontName="DejaVu-Bold", fontSize=13, textColor=AZUL, spaceBefore=12,
                   spaceAfter=5)
N = ParagraphStyle("n", fontName="DejaVu", fontSize=9.5, leading=13.5, spaceAfter=4)
P = ParagraphStyle("p", fontName="DejaVu", fontSize=8.3, leading=11)
DICA = ParagraphStyle("d", parent=N, backColor=colors.HexColor("#FFF8E1"), borderPadding=6,
                      borderColor=colors.HexColor("#FFD966"), borderWidth=0.5, spaceBefore=6,
                      spaceAfter=8)


def img(nome, largura=16.5):
    caminho = os.path.join(IMG, nome)
    from PIL import Image as PImg
    w, h = PImg.open(caminho).size
    return Image(caminho, width=largura * cm, height=largura * cm * h / w)


def tabela(dados, larg, cores_col0=None):
    t = Table([[Paragraph(str(c), P) for c in r] for r in dados], colWidths=larg)
    est = [("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#BFBFBF")),
           ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDEBF7")),
           ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    for r, cor in (cores_col0 or {}).items():
        est.append(("BACKGROUND", (0, r), (0, r), colors.HexColor(cor)))
    t.setStyle(TableStyle(est))
    return t


def passo(num, titulo, texto, imagem=None):
    bloco = [Paragraph(f"Passo {num} — {titulo}", H), Paragraph(texto, N)]
    if imagem:
        bloco.append(img(imagem, 10.5))
    return KeepTogether(bloco)


def main():
    s = [Spacer(1, 1.2 * cm), Paragraph("Manual do Usuário — Enturme ABC", T),
         Paragraph("Ensalamento automático de turmas da ABC Aprendiz", ST),
         Spacer(1, 0.5 * cm), img("app_3_turmas.png", 13), Spacer(1, 0.5 * cm),
         Paragraph("O Enturme ABC monta automaticamente as turmas da Manhã e da Tarde a partir da "
                   "planilha de matriculados. Ele usa um <b>modelo matemático de otimização</b> para "
                   "garantir turmas do mesmo tamanho (diferença máxima de 1 aluno), proporção de "
                   "meninos e meninas equilibrada e respeito às vagas — em poucos segundos.", N),
         Paragraph("<b>Conteúdo:</b> 1. Antes de começar · 2. Preparando a planilha · "
                   "3. Passo a passo · 4. Entendendo o resultado · 5. Inconsistências: o que fazer · "
                   "6. Perguntas frequentes · 7. Como funciona", N),
         PageBreak()]

    s.append(Paragraph("1. Antes de começar", H))
    s.append(Paragraph("• Não é preciso instalar nada: basta o arquivo <b>Enturme.exe</b> "
                       "(funciona no Windows 10/11).<br/>"
                       "• Guarde uma cópia da planilha original: o resultado é gravado <b>na própria "
                       "planilha</b> escolhida (em abas novas).<br/>"
                       "• Feche a planilha no Excel antes de rodar.", N))
    s.append(Paragraph("<b>Primeira vez abrindo?</b> O Windows pode mostrar a tela azul “O Windows "
                       "protegeu o computador”. Clique em <b>Mais informações</b> → <b>Executar "
                       "assim mesmo</b>. Isso acontece com programas novos sem assinatura digital.",
                       DICA))

    s.append(Paragraph("2. Preparando a planilha (.xlsx)", H))
    s.append(Paragraph("A planilha precisa de duas abas:", N))
    s.append(Paragraph("<b>Aba “Alunos”</b> — uma linha por aluno, com o cabeçalho na linha 1:", N))
    s.append(tabela([["Nome", "Sexo", "Disponibilidade"],
                     ["Gustavo de Oliveira Cardoso", "M", "Manhã"],
                     ["Camila Machado do Nascimento", "F", "Tarde"]],
                    [7 * cm, 2.5 * cm, 4 * cm]))
    s.append(Spacer(1, 4))
    s.append(Paragraph("Sexo: <b>M</b> ou <b>F</b> (também aceita Masculino/Feminino). "
                       "Disponibilidade: <b>Manhã</b> ou <b>Tarde</b> (aceita “manha”, “TARDE”, "
                       "espaços sobrando etc. — o programa corrige e avisa).", N))
    s.append(Paragraph("<b>Aba “Turmas”</b> — quantidade de turmas e vagas <b>por turma</b> em cada "
                       "turno:", N))
    s.append(tabela([["Recursos", "Quantidade", "Significado"],
                     ["turmas_manha", "2", "nº de turmas da manhã"],
                     ["turmas_tarde", "2", "nº de turmas da tarde"],
                     ["vagas_manha", "35", "vagas em CADA turma da manhã"],
                     ["vagas_tarde", "35", "vagas em CADA turma da tarde"]],
                    [3.5 * cm, 2.5 * cm, 7.5 * cm]))

    s.append(PageBreak())
    s.append(Paragraph("3. Passo a passo", H))
    s.append(passo(1, "Abra o Enturme ABC", "Dê dois cliques em <b>Enturme.exe</b>. A janela abre "
                   "vazia, pronta para receber a planilha. O botão <b>Como usar</b>, no canto "
                   "superior direito, mostra um resumo destas instruções.", "app_1_inicial.png"))
    s.append(passo(2, "Escolha a planilha", "Em <b>1. Selecione a planilha (.xlsx)</b>, clique em "
                   "<b>Procurar...</b> e escolha a planilha de matriculados. O caminho do arquivo "
                   "aparece no campo e o botão <b>Rodar ensalamento</b> fica verde. Dica: arrastar a "
                   "planilha para cima do arquivo Enturme.exe abre o programa com ela já "
                   "selecionada.", "app_2_selecionado.png"))
    s.append(passo(3, "Rode o ensalamento", "Feche a planilha no Excel e clique em <b>▶ Rodar "
                   "ensalamento</b>. O modelo de otimização monta as turmas em 1 a 2 segundos. Ao "
                   "terminar, uma mensagem confirma quantos alunos foram ensalados e avisa se algum "
                   "ficou de fora. Os cartões mostram: matriculados, ensalados, não ensalados, "
                   "turmas, erros e alertas.", None))
    s.append(passo(4, "Confira as turmas", "A aba <b>Turmas</b> mostra cada turno e cada turma: "
                   "alunos, vagas, ocupação, meninos, meninas, % de meninas e uma barra com a "
                   "composição da turma.", "app_3_turmas.png"))
    s.append(passo(5, "Confira as inconsistências", "A aba <b>Inconsistências</b> lista os "
                   "problemas encontrados nos dados, com a linha do Excel e o tratamento dado. Use "
                   "<b>Mostrar</b> para ver só Erros, Alertas ou Corrigidos. Dê dois cliques em uma "
                   "linha para ler a descrição completa.", "app_4_inconsistencias.png"))
    s.append(passo(6, "Detalhes da otimização (opcional)", "A aba <b>Otimização</b> mostra o "
                   "solver usado, o status (ótimo provado), o tempo e o valor de cada parte do "
                   "objetivo. É útil para a coordenação conferir a qualidade da solução.",
                   "app_5_otimizacao.png"))
    s.append(Paragraph("<b>Onde ficam os arquivos?</b> O resultado é gravado na própria planilha "
                       "escolhida (abas <b>Ensalamento</b> e <b>Inconsistências</b>), e o "
                       "<b>Relatório Resumo da Distribuição</b> em PDF é criado na mesma pasta, com o "
                       "nome <b>&lt;planilha&gt;_relatorio.pdf</b>. Use os botões <b>Abrir "
                       "planilha</b>, <b>Abrir relatório PDF</b> e <b>Abrir pasta</b>, no rodapé da "
                       "janela, para abri-los.", DICA))

    s.append(PageBreak())
    s.append(Paragraph("4. Entendendo o resultado", H))
    s.append(tabela([
        ["Onde", "O que contém"],
        ["Aba “Ensalamento”", "Nome, Sexo, Disponibilidade e Turma de cada aluno ensalado, na "
                              "ordem da lista de matriculados. Turmas: MANHÃ - A, MANHÃ - B, … e a "
                              "tarde continua as letras (TARDE - C, TARDE - D, …)."],
        ["Aba “Inconsistências”", "Tipo, aba, linha do Excel, nome, campo, valor encontrado e o que "
                                  "foi feito / o que fazer."],
        ["&lt;planilha&gt;_relatorio.pdf (mesma pasta)",
         "Relatório Resumo da Distribuição: totais, tabela por turma (ocupação, meninos, "
                                     "meninas, % e desvio), gráfico e lista de inconsistências."],
    ], [4.2 * cm, 12.3 * cm]))
    s.append(Spacer(1, 6))
    s.append(Paragraph("<b>Tipos de inconsistência</b>", N))
    s.append(tabela([
        ["Tipo", "Significado", "Exemplo"],
        ["ERRO", "O aluno (ou o cenário) <b>não pôde ser ensalado</b>. Corrija a planilha e rode de "
                 "novo.", "Sexo “X”, turno “Integral”, nome vazio, turno sem vagas"],
        ["ALERTA", "O aluno foi ensalado, mas vale conferir.",
         "Mesmo nome em duas linhas (possível cadastro duplicado)"],
        ["CORRIGIDO", "O programa ajustou sozinho e seguiu.",
         "“manha” → Manhã; “feminino” → F; título de coluna errado"],
    ], [2.4 * cm, 8.1 * cm, 6 * cm], {1: "#FFC7CE", 2: "#FFEB9C", 3: "#DDEBF7"}))

    s.append(Paragraph("5. Inconsistências: o que fazer", H))
    s.append(tabela([
        ["Situação", "O que o programa faz", "O que você faz"],
        ["Sexo diferente de M/F (X, ?, vazio)", "Não ensala o aluno e registra ERRO",
         "Corrija o sexo na aba Alunos e rode novamente"],
        ["Disponibilidade inválida (Integral, Noite, vazio)", "Não ensala e registra ERRO",
         "Defina Manhã ou Tarde"],
        ["Linha sem nome", "Ignora a linha e registra ERRO com o nº da linha",
         "Preencha o nome ou apague a linha"],
        ["Nomes repetidos", "Ensala todos e registra ALERTA",
         "Confira se é a mesma pessoa cadastrada 2x"],
        ["Mais alunos que vagas no turno", "Preenche todas as vagas pela ordem de matrícula; "
                                           "os últimos ficam com ERRO “sem vaga”",
         "Aumente turmas/vagas na aba Turmas ou remaneje alunos"],
        ["Aba Turmas incompleta ou com texto", "Interrompe e lista o problema",
         "Preencha as 4 linhas com números inteiros"],
        ["Linha de “Total” no fim da lista", "Não ensala e avisa", "Apague a linha"],
    ], [4.6 * cm, 6.2 * cm, 5.7 * cm]))

    s.append(PageBreak())
    s.append(Paragraph("6. Perguntas frequentes", H))
    for p, r in [
        ("Apareceu “a planilha parece estar aberta no Excel”.",
         "Feche o arquivo no Excel e clique em Rodar ensalamento de novo."),
        ("O que significam os cartões “erros” e “alertas”?",
         "São as contagens da aba Inconsistências: erros (alunos não ensalados ou dados que "
         "impedem o ensalamento) e alertas (para conferir). As correções automáticas também "
         "aparecem na aba. Abra a aba para ver cada item."),
        ("Posso rodar de novo na mesma planilha?",
         "Sim. As abas Ensalamento e Inconsistências são substituídas pela nova execução."),
        ("Rodei duas vezes e as turmas mudaram?",
         "O modelo garante sempre a melhor distribuição; quando há várias igualmente boas, os "
         "alunos podem trocar de turma, mas os tamanhos e proporções continuam ótimos."),
        ("Por que algumas turmas têm 1 aluno a mais?",
         "Quando o total não divide igualmente (ex.: 79 alunos em 3 turmas = 27, 26, 26), a "
         "diferença máxima é 1 aluno — o melhor possível."),
        ("O programa altera meus dados?",
         "Não altera os alunos. Apenas cria as abas de resultado e, se o título de uma coluna "
         "estiver errado (ex.: “Nome” digitado errado), corrige só o título e registra isso."),
    ]:
        s.append(Paragraph(f"<b>{p}</b><br/>{r}", N))

    s.append(Paragraph("7. Como funciona (para curiosos)", H))
    s.append(Paragraph(
        "O Enturme ABC resolve um modelo de <b>Programação Linear Inteira Mista</b> com o solver "
        "HiGHS, considerando os dois turnos ao mesmo tempo. Para cada aluno e cada turma, o modelo "
        "decide se o aluno vai para aquela turma, respeitando: o turno do aluno, as vagas de cada "
        "turma e uma diferença de no máximo 1 aluno entre turmas do mesmo turno. Entre todas as "
        "distribuições possíveis, ele escolhe a melhor em ordem de importância: (1) ninguém sem "
        "sala (e, se faltar vaga, prioridade para quem se matriculou antes); (2) turmas do mesmo "
        "tamanho; (3) a proporção de meninos de cada turma o mais próxima possível da do turno. "
        "Diferente de uma divisão manual ou “no olho”, o solver prova que o resultado é o melhor "
        "possível.", N))

    destino = os.path.join(AQUI, "Manual_do_Usuario_Enturme.pdf")

    def rodape(canvas, doc):
        canvas.saveState()
        canvas.setFont("DejaVu", 7.5)
        canvas.setFillColor(colors.HexColor("#8C8C8C"))
        canvas.drawString(1.8 * cm, 1 * cm, "Enturme ABC · Manual do Usuário · Equipe 14")
        canvas.drawRightString(A4[0] - 1.8 * cm, 1 * cm, f"Página {doc.page}")
        canvas.restoreState()

    SimpleDocTemplate(destino, pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
                      topMargin=1.5 * cm, bottomMargin=1.6 * cm,
                      title="Manual do Usuário - Enturme ABC").build(
        s, onFirstPage=rodape, onLaterPages=rodape)
    print("Gerado:", destino)


if __name__ == "__main__":
    main()
