"""
Enturme - interface visual (glassmorphism) para o ensalamento da ABC Aprendiz.

Fluxo:
  1. Selecionar a planilha (botão "Buscar arquivo" ou arrastar e soltar)
  2. Confirmar o processamento
  3. Ver o resultado: % de alunos alocados, proporção de gênero por turno,
     aviso de inconsistências e botões para baixar a planilha e o relatório PDF.

O resultado também é gravado na própria planilha (abas Ensalamento e
Inconsistências), como exige o desafio, e uma cópia da planilha e do relatório
fica na pasta "Enturme_Arquivos", ao lado do arquivo original.
"""
from __future__ import annotations

import math
import os
import queue
import shutil
import sys
import threading
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox

from PIL import Image, ImageTk

import enturme_ui as ui
from ensalamento_mono.etl import ORDEM_TURNOS
from ensalamento_mono.pipeline import executar
from ensalamento_mono.saida import PlanilhaAbertaError

try:  # arrastar e soltar
    from tkinterdnd2 import DND_FILES, TkinterDnD
    TEM_DND = True
except Exception:  # pragma: no cover
    TEM_DND = False

PASTA_SAIDA = "Enturme_Arquivos"
EXTENSOES = (".xlsx", ".xlsm")


def escala_da_tela(root: tk.Tk) -> float:
    s = root.winfo_fpixels("1i") / 96.0
    altura_util = root.winfo_screenheight() - 90  # barra de tarefas + título da janela
    largura_util = root.winfo_screenwidth() - 40
    return max(0.6, min(s, altura_util / ui.ALTURA_RESULTADO, largura_util / ui.LARGURA))


class Enturme:
    def __init__(self, root: tk.Tk, arquivo_inicial: str | None = None):
        self.root = root
        root.title("Enturme · Ensalamento automático de turmas")
        root.resizable(False, False)
        try:
            root.iconbitmap(ui.recurso("assets", "enturme.ico"))
        except Exception:
            pass
        self.s = escala_da_tela(root)
        self.pintor = ui.Pintor(self.s)
        self.logo = Image.open(ui.recurso("assets", "abc_icone.png")).convert("RGBA")
        self.canvas = tk.Canvas(root, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.fila: queue.Queue = queue.Queue()
        self.arquivo: str | None = None
        self.resultado = None
        self.copia_xlsx = self.copia_pdf = None
        self.tela = "inicial"
        self._imgs: list = []
        self._spinner = None
        self._ang = 0
        if TEM_DND:
            root.drop_target_register(DND_FILES)
            root.dnd_bind("<<DropEnter>>", self._drag_entrou)
            root.dnd_bind("<<DropLeave>>", lambda e: self._mostrar() or e.action)
            root.dnd_bind("<<Drop>>", self._soltou)
        root.bind("<Return>", lambda e: self._acao_principal())
        if arquivo_inicial and os.path.isfile(arquivo_inicial):
            self.arquivo = os.path.abspath(arquivo_inicial)
            self.tela = "selecionado"
        self._mostrar()
        self.root.after(100, self._processar_fila)

    # ------------------------------------------------------------------ desenho
    def _mostrar(self, arrastando=False):
        if self.tela in ("inicial", "selecionado", "processando"):
            base, hs = ui.tela_selecao(self.pintor, self.logo, self.arquivo, arrastando=arrastando,
                                       processando=self.tela == "processando")
        else:
            base, hs = ui.tela_resultado(self.pintor, self.logo, self.resultado)
        self.root.geometry(f"{base.width}x{base.height}")
        self.canvas.configure(width=base.width, height=base.height)
        self.canvas.delete("all")
        self._imgs = [ImageTk.PhotoImage(base)]
        self.canvas.create_image(0, 0, image=self._imgs[0], anchor="nw")
        for h in hs:
            normal = ImageTk.PhotoImage(h.normal)
            hover = ImageTk.PhotoImage(h.hover) if h.hover else None
            self._imgs += [normal, hover]
            item = self.canvas.create_image(h.x, h.y, image=normal, anchor="nw")
            if hover is None:  # botão desabilitado
                continue
            self.canvas.tag_bind(item, "<Enter>", lambda e, i=item, im=hover: self._hover(i, im, True))
            self.canvas.tag_bind(item, "<Leave>", lambda e, i=item, im=normal: self._hover(i, im, False))
            self.canvas.tag_bind(item, "<Button-1>", lambda e, n=h.nome: self._clique(n))
        if self.tela == "processando":
            self._iniciar_spinner()
        return False

    def _hover(self, item, imagem, dentro):
        self.canvas.itemconfigure(item, image=imagem)
        self.canvas.configure(cursor="hand2" if dentro else "")

    def _iniciar_spinner(self):
        p = self.pintor.p
        cx, cy, r = p(ui.LARGURA / 2), p(250), p(22)
        self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#C9D6EA", width=max(2, p(5)))
        self._spinner = self.canvas.create_arc(cx - r, cy - r, cx + r, cy + r, start=90, extent=100,
                                               style="arc", outline="#0D6EAC", width=max(2, p(5)))
        self._girar()

    def _girar(self):
        if self.tela != "processando" or self._spinner is None:
            return
        self._ang = (self._ang - 12) % 360
        self.canvas.itemconfigure(self._spinner, start=self._ang)
        self.root.after(30, self._girar)

    # ------------------------------------------------------------------ ações
    def _clique(self, nome):
        self.canvas.configure(cursor="")
        if nome in ("buscar", "trocar"):
            self._escolher()
        elif nome == "confirmar":
            self._processar()
        elif nome == "baixar_planilha":
            self._baixar(self.copia_xlsx, "Salvar planilha das turmas", "Planilha do Excel", "*.xlsx")
        elif nome == "baixar_pdf":
            self._baixar(self.copia_pdf, "Salvar relatório em PDF", "PDF", "*.pdf")
        elif nome == "outra":
            self.arquivo, self.resultado, self.tela = None, None, "inicial"
            self._mostrar()

    def _acao_principal(self):
        if self.tela == "inicial":
            self._escolher()
        elif self.tela == "selecionado":
            self._processar()

    def _escolher(self):
        arq = filedialog.askopenfilename(
            title="Selecione a planilha de matriculados",
            filetypes=[("Planilhas do Excel", "*.xlsx *.xlsm"), ("Todos os arquivos", "*.*")])
        if arq:
            self._definir_arquivo(arq)

    def _definir_arquivo(self, arq: str):
        if not arq.lower().endswith(EXTENSOES):
            messagebox.showwarning("Arquivo não suportado",
                                   "Escolha uma planilha do Excel (.xlsx) com as abas Alunos e Turmas.")
            self._mostrar()
            return
        self.arquivo = os.path.abspath(arq)
        self.tela = "selecionado"
        self._mostrar()

    def _drag_entrou(self, evento):
        if self.tela in ("inicial", "selecionado"):
            self._mostrar(arrastando=True)
        return evento.action

    def _soltou(self, evento):
        arquivos = self.root.tk.splitlist(evento.data)
        if self.tela in ("inicial", "selecionado") and arquivos:
            self._definir_arquivo(arquivos[0])
        else:
            self._mostrar()
        return evento.action

    def _processar(self):
        if not self.arquivo:
            return
        self.tela = "processando"
        self._mostrar()
        caminho = self.arquivo

        def trabalho():
            try:
                self.fila.put(("ok", executar(caminho)))
            except PlanilhaAbertaError as exc:
                self.fila.put(("aberta", str(exc)))
            except Exception as exc:
                self.fila.put(("erro", f"{exc}\n\n{traceback.format_exc()}"))

        threading.Thread(target=trabalho, daemon=True).start()

    def _processar_fila(self):
        try:
            tipo, dado = self.fila.get_nowait()
        except queue.Empty:
            self.root.after(100, self._processar_fila)
            return
        if tipo == "ok":
            self._concluir(dado)
        else:
            self.tela = "selecionado"
            self._mostrar()
            if tipo == "aberta":
                messagebox.showwarning("Planilha aberta", dado)
            else:
                messagebox.showerror("Erro inesperado", dado[:3000])
        self.root.after(100, self._processar_fila)

    def _concluir(self, res):
        cen = res.cenario
        pasta = os.path.join(os.path.dirname(res.caminho_excel), PASTA_SAIDA)
        os.makedirs(pasta, exist_ok=True)
        self.copia_xlsx = os.path.join(pasta, os.path.basename(res.caminho_excel))
        shutil.copyfile(res.caminho_excel, self.copia_xlsx)
        self.copia_pdf = None
        if res.caminho_relatorio and os.path.isfile(res.caminho_relatorio):
            self.copia_pdf = os.path.join(pasta, os.path.basename(res.caminho_relatorio))
            shutil.move(res.caminho_relatorio, self.copia_pdf)
        turnos = []
        for turno in ORDEM_TURNOS:
            ests = [e for e in res.estatisticas if e.turno == turno]
            total = sum(e.total for e in ests)
            if total:
                turnos.append((turno, total, sum(e.meninos for e in ests) / total))
        matric = cen.total_linhas
        self.resultado = ui.DadosResultado(
            sucesso=not cen.bloqueante and res.ensalados > 0, pasta=PASTA_SAIDA,
            pct_alocados=res.ensalados / matric if matric else 0.0, alocados=res.ensalados,
            matriculados=matric, turnos=turnos, inconsistencias=len(cen.inconsistencias),
            nao_alocados=matric - res.ensalados, erros=res.contagem("ERRO"))
        self.tela = "resultado"
        self._mostrar()

    def _baixar(self, origem, titulo, tipo, padrao):
        if not origem or not os.path.isfile(origem):
            messagebox.showwarning("Arquivo indisponível", "O arquivo não foi encontrado.")
            return
        destino = filedialog.asksaveasfilename(
            title=titulo, initialfile=os.path.basename(origem), defaultextension=padrao[1:],
            initialdir=os.path.join(os.path.expanduser("~"), "Downloads"),
            filetypes=[(tipo, padrao)])
        if not destino:
            return
        try:
            if os.path.abspath(destino) != os.path.abspath(origem):
                shutil.copyfile(origem, destino)
        except PermissionError:
            messagebox.showwarning("Não foi possível salvar",
                                   "O arquivo de destino parece estar aberto. Feche-o e tente de novo.")
            return
        if messagebox.askyesno("Arquivo salvo", f"Arquivo salvo em:\n{destino}\n\nDeseja abri-lo agora?"):
            try:
                os.startfile(destino)  # type: ignore[attr-defined]
            except Exception as exc:
                messagebox.showerror("Erro", f"Não foi possível abrir o arquivo:\n{exc}")


def diagnostico() -> int:
    """Enturme.exe --diagnostico: confere fontes, arrastar-e-soltar e solver (para suporte)."""
    import pulp
    destino = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "enturme_diagnostico.txt")
    linhas = [f"arrastar_e_soltar={TEM_DND}", f"solvers={pulp.listSolvers(onlyAvailable=True)}"]
    for peso in ("Regular", "Medium", "SemiBold", "Bold"):
        try:
            ui.fonte(peso, 12)
            linhas.append(f"fonte_{peso}=ok")
        except Exception as exc:
            linhas.append(f"fonte_{peso}=ERRO {exc}")
    try:
        root = TkinterDnD.Tk() if TEM_DND else tk.Tk()
        root.withdraw()
        if TEM_DND:
            root.drop_target_register(DND_FILES)
        linhas.append("tk=ok")
        root.destroy()
    except Exception as exc:
        linhas.append(f"tk=ERRO {exc}")
    with open(destino, "w", encoding="utf-8") as fh:
        fh.write("\n".join(linhas) + "\n")
    return 0


def main():
    if "--diagnostico" in sys.argv:
        sys.exit(diagnostico())
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    try:  # nitidez em telas com escala (Windows)
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = TkinterDnD.Tk() if TEM_DND else tk.Tk()
    Enturme(root, args[0] if args else None)
    root.mainloop()


if __name__ == "__main__":
    main()
