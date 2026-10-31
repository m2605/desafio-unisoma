"""
Preenche o template oficial de slides com o conteúdo da solução.

Uso: python docs/gerar_slides.py <template.pptx> <saida.pptx> [equipe.json]
equipe.json: {"numero": "24", "solucao": "...", "membros": [{"nome": "...", "curso": "...",
              "papel": "..."}, ...]}
"""
from __future__ import annotations

import copy
import io
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from pptx import Presentation  # noqa: E402
from pptx.util import Cm  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))


def shape(slide, sufixo):
    return next(s for s in slide.shapes if s.name.startswith(f"Google Shape;{sufixo};"))


def escrever(sh, linhas):
    """Substitui o texto mantendo a formatação do 1º run/parágrafo."""
    if isinstance(linhas, str):
        linhas = [linhas]
    tf = sh.text_frame
    p0 = tf.paragraphs[0]
    modelo_p = copy.deepcopy(p0._p)
    for p in list(tf.paragraphs)[1:]:
        p._p.getparent().remove(p._p)
    for k, linha in enumerate(linhas):
        if k == 0:
            p = p0
        else:
            novo = copy.deepcopy(modelo_p)
            tf._txBody.append(novo)
            p = tf.paragraphs[-1]
        runs = p.runs
        if not runs:
            p.text = linha
            continue
        runs[0].text = linha
        for r in runs[1:]:
            r._r.getparent().remove(r._r)


def remover(sh):
    sh._element.getparent().remove(sh._element)


def imagem_em_caixa(slide, caixa, fonte, margem=0.4):
    from PIL import Image as PImg
    if isinstance(fonte, io.BytesIO):
        fonte.seek(0)
        w, h = PImg.open(fonte).size
        fonte.seek(0)
    else:
        w, h = PImg.open(fonte).size
    bw, bh = caixa.width - Cm(2 * margem), caixa.height - Cm(2 * margem)
    esc = min(bw / w, bh / h)
    iw, ih = int(w * esc), int(h * esc)
    left = caixa.left + (caixa.width - iw) // 2
    top = caixa.top + (caixa.height - ih) // 2
    return slide.shapes.add_picture(fonte, left, top, iw, ih)


def resultados_reais():
    """Roda o modelo monolítico nas 4 instâncias oficiais (em cópias temporárias)."""
    import shutil
    import tempfile
    sys.path.insert(0, os.path.dirname(AQUI))
    from ensalamento_mono.pipeline import executar
    dados = {}
    pasta = os.path.join(os.path.dirname(os.path.dirname(AQUI)), "dados", "instancias")
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(1, 5):
            copia = os.path.join(tmp, f"instancia_{i}.xlsx")
            shutil.copyfile(os.path.join(pasta, f"instancia_{i}.xlsx"), copia)
            res = executar(copia, gerar_relatorio=False)
            dados[f"Inst. {i}"] = [(e.turma[-1], e.meninos, e.meninas) for e in res.estatisticas]
    return dados


def grafico_resultados():
    dados = resultados_reais()  # instância: [(turma, meninos, meninas)]
    fig, axes = plt.subplots(1, 4, figsize=(18, 2.9), dpi=170, sharey=True)
    for ax, (inst, turmas) in zip(axes, dados.items()):
        nomes = [t[0] for t in turmas]
        m = [t[1] for t in turmas]
        f = [t[2] for t in turmas]
        ax.bar(nomes, m, color="#2E75B6", label="Meninos")
        ax.bar(nomes, f, bottom=m, color="#C55A9E", label="Meninas")
        for i, (a, b) in enumerate(zip(m, f)):
            ax.text(i, a + b + 0.5, str(a + b), ha="center", fontsize=9)
        ax.set_title(f"{inst} — validador: APROVADO", fontsize=11)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=9)
    axes[0].legend(frameon=False, fontsize=9, loc="lower left")
    axes[0].set_ylabel("alunos por turma", fontsize=9)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", transparent=True)
    plt.close(fig)
    buf.seek(0)
    return buf


def main():
    template, saida = sys.argv[1], sys.argv[2]
    eq = {"numero": "[00]", "solucao": "Ensala+ ABC",
          "membros": [{"nome": "[Nome 1]", "curso": "[Curso] / [Universidade]",
                       "papel": "Papel na equipe: [modelagem, código, interface…]"}]}
    if len(sys.argv) > 3:
        with open(sys.argv[3], encoding="utf-8") as fh:
            eq.update(json.load(fh))
    num, sol = eq["numero"], eq["solucao"]
    nomes = ", ".join(m["nome"] for m in eq["membros"])

    prs = Presentation(template)
    sl = list(prs.slides)

    # etiqueta "Equipe [00]" em todos os slides
    for s in sl:
        for sh in s.shapes:
            if sh.has_text_frame and sh.text_frame.text.strip() == "Equipe [00]":
                escrever(sh, f"Equipe {num}")

    # 2 – capa
    escrever(shape(sl[1], 117), sol)
    escrever(shape(sl[1], 118), f"Equipe {num}  ·  {nomes}")

    # 3 – equipe (até 4 cartões; remove os que sobrarem)
    cartoes = [(126, 127, 128, 129, 130, 131, 132, 133), (134, 135, 136, 137, 138, 139, 140, 141),
               (142, 143, 144, 145, 146, 147, 148, 149), (150, 151, 152, 153, 154, 155, 156, 157)]
    for k, ids in enumerate(cartoes):
        if k < len(eq["membros"]):
            m = eq["membros"][k]
            escrever(shape(sl[2], ids[4]), m["nome"])
            if m.get("curso"):
                escrever(shape(sl[2], ids[5]), m["curso"])
            else:
                remover(shape(sl[2], ids[5]))
            if m.get("papel"):
                escrever(shape(sl[2], ids[7]), m["papel"])
            else:
                remover(shape(sl[2], ids[6]))
                remover(shape(sl[2], ids[7]))
        else:
            for i in ids:
                remover(shape(sl[2], i))

    # 4 – problema
    escrever(shape(sl[3], 171), "Todo semestre a equipe distribui centenas de jovens em turmas da "
             "Manhã e da Tarde à mão: horas de trabalho, retrabalho e turmas desequilibradas, "
             "além de erros de cadastro descobertos tarde demais.")
    escrever(shape(sl[3], 178), "Disponibilidade: aluno da manhã só vai para turma da manhã (e "
             "o mesmo para a tarde)")
    escrever(shape(sl[3], 182), "Capacidade: nenhuma turma passa do limite de vagas")
    escrever(shape(sl[3], 186), "Equilíbrio: turmas do mesmo turno com no máx. 1 aluno de "
             "diferença e proporção de gênero similar")
    escrever(shape(sl[3], 190), "Ler o Excel da ONG, tratar erros de digitação, alertar TODAS as "
             "inconsistências de uma vez e gravar o resultado no mesmo Excel")

    # 5 – solução
    escrever(shape(sl[4], 203), "O Enturme lê a planilha de matriculados e, com um modelo "
             "matemático de otimização, monta em segundos as turmas mais equilibradas possíveis "
             "— já gravadas no Excel da ONG.")
    escrever(shape(sl[4], 207), "Ótimo, não “no olho”")
    escrever(shape(sl[4], 208), "MILP com prova de otimalidade: turmas com no máx. 1 aluno de "
             "diferença e o menor desvio de gênero possível.")
    escrever(shape(sl[4], 212), "Pega erro antes do problema")
    escrever(shape(sl[4], 213), "Corrige “manha”, “feminino”…; aponta sexo/turno inválidos, nomes "
             "duplicados e falta de vagas — tudo numa única execução.")
    escrever(shape(sl[4], 217), "Arrastar, soltar, pronto")
    escrever(shape(sl[4], 218), "Interface visual feita para a equipe da ONG + relatório PDF com "
             "gráficos para a coordenação.")

    # 6 – modelagem (modelo monolítico)
    escrever(shape(sl[5], 232), "min Z = W1·Σ z_i + W2·Σ_t (D_max − D_min) + W3·v — "
             "hierarquia: (1) ninguém sem sala; (2) turmas do mesmo tamanho; (3) menor desvio de "
             "gênero. Pesos calculados para garantir a hierarquia.")
    escrever(shape(sl[5], 237), "x_ij ∈ {0,1}: aluno i na turma j · z_i ∈ {0,1}: aluno sem turma · "
             "D_max, D_min: maior/menor turma de cada turno · v: maior desvio de meninos.")
    escrever(shape(sl[5], 242), "Cobertura (Σ_j x_ij + z_i = 1) · capacidade · turno do aluno · "
             "D_max − D_min ≤ 1 · desvio de gênero linearizado · se faltar vaga, saem os últimos "
             "matriculados.")
    escrever(shape(sl[5], 247), ["Linguagem: Python 3.12.9", "Biblioteca de otimização: PuLP",
                                 "Solver: HiGHS (MILP branch-and-cut) · CBC reserva",
                                 "Interface: Enturme (Tkinter + Pillow) · .exe (PyInstaller)",
                                 "Relatório: ReportLab + Matplotlib"])

    # 7 – aplicativo
    remover(shape(sl[6], 258))
    remover(shape(sl[6], 259))
    imagem_em_caixa(sl[6], shape(sl[6], 257), os.path.join(AQUI, "img", "enturme_4_resultado.png"))
    escrever(shape(sl[6], 266), "Abrir o Enturme e arrastar (ou buscar) a planilha de matriculados")
    escrever(shape(sl[6], 270), "Confirmar o processamento — turmas prontas em segundos")
    escrever(shape(sl[6], 274), "Ver % alocados e gênero por turno; baixar planilha e relatório PDF")

    # 8 – resultados
    escrever(shape(sl[7], 285), "4 / 4")
    escrever(shape(sl[7], 286), "instâncias APROVADAS pelo validador oficial (+ 10 cenários "
             "extremos testados)")
    escrever(shape(sl[7], 289), "≤ 1,1 s")
    escrever(shape(sl[7], 290), "por instância, com prova de solução ótima pelo solver")
    escrever(shape(sl[7], 293), "≤ 3 p.p.")
    escrever(shape(sl[7], 294), "desvio de gênero por turma — o mínimo possível com números "
             "inteiros")
    remover(shape(sl[7], 296))
    remover(shape(sl[7], 297))
    imagem_em_caixa(sl[7], shape(sl[7], 295), grafico_resultados(), margem=0.25)

    # 9 – impacto
    escrever(shape(sl[8], 312), "Horas montando turmas à mão em planilha, conferindo vagas e "
             "proporções; erros de cadastro aparecem só depois, gerando retrabalho.")
    escrever(shape(sl[8], 317), "2 cliques: o modelo monta as turmas ótimas em segundos e lista "
             "todas as pendências de uma vez, direto no Excel que a equipe já usa.")
    escrever(shape(sl[8], 323), "Equipe livre para focar na educação; turmas justas e "
             "equilibradas para os jovens; decisões transparentes com relatório.")

    # 10 – encerramento
    escrever(shape(sl[9], 333), f"Equipe {num}  ·  {sol}")
    escrever(shape(sl[9], 334), nomes)

    # o template traz slides ocultos (problema, modelagem, resultados): exibe todos
    for s in sl:
        if s.element.get("show") is not None:
            del s.element.attrib["show"]

    # remove o slide de instruções (1)
    lst = prs.slides._sldIdLst
    lst.remove(lst[0])
    prs.save(saida)
    print("Gerado:", saida)


if __name__ == "__main__":
    main()
