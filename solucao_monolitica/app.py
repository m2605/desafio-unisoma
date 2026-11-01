"""
Enturme - Ensalamento automático de turmas (interface gráfica).

Fluxo: 1) selecionar a planilha  2) Rodar ensalamento  3) conferir resumo,
inconsistências e abrir a planilha/relatório gerados.
"""
from __future__ import annotations

import os
import queue
import sys
import threading
import traceback
import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox, ttk

from PIL import Image, ImageDraw, ImageFont, ImageTk

from ensalamento_mono import __version__
from ensalamento_mono.etl import ALERTA, CORRIGIDO, ERRO, ORDEM_TURNOS
from ensalamento_mono.pipeline import executar
from ensalamento_mono.saida import PlanilhaAbertaError

AZUL = "#2A4598"
NAVY_ESCURO = "#1E3270"
AZUL_MEDIO = "#0D6EAC"
BANDA = "#A7DACE"
VERDE = "#7DB945"
FUNDO = "#F4F7FB"
CINZA = "#595959"

AJUDA = """COMO USAR — ENTURME

1. Clique em "Procurar..." e escolha a planilha Excel (.xlsx) do semestre.
   Ela deve ter as abas:
     • Alunos  – colunas Nome, Sexo (M/F) e Disponibilidade (Manhã/Tarde)
     • Turmas  – Recursos/Quantidade: turmas_manha, turmas_tarde,
                 vagas_manha, vagas_tarde (vagas POR turma)

2. Feche a planilha no Excel (se estiver aberta) e clique em
   "Rodar ensalamento".

3. O resultado é salvo na PRÓPRIA planilha, em duas abas:
     • Ensalamento     – Nome, Sexo, Disponibilidade e Turma
     • Inconsistências – problemas encontrados nos dados:
         ERRO      → o aluno NÃO foi ensalado (corrija e rode de novo)
         ALERTA    → foi ensalado, mas confira (ex.: nomes repetidos)
         CORRIGIDO → o programa ajustou sozinho (ex.: "manha" → "Manhã")
   Também é gerado o Relatório Resumo em PDF na mesma pasta.

Como funciona: um modelo matemático de otimização (Programação Linear
Inteira) distribui os alunos para que as turmas do mesmo turno tenham
quantidades iguais (diferença máxima de 1 aluno) e a proporção de
meninos e meninas mais parecida possível, respeitando as vagas.
"""


def caminho_recurso(rel: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def abrir_arquivo(caminho: str) -> None:
    try:
        os.startfile(caminho)  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover
        messagebox.showerror("Erro", f"Não foi possível abrir:\n{caminho}\n\n{exc}")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Enturme · Ensalamento automático de turmas")
        self.geometry("1040x720")
        self.minsize(860, 620)
        self.configure(bg=FUNDO)
        try:
            self.iconbitmap(caminho_recurso("assets/enturme.ico"))
        except Exception:
            pass
        self.fila: queue.Queue = queue.Queue()
        self.resultado = None
        self._logo_img = None
        self.caminho = tk.StringVar()
        self.status = tk.StringVar(value="Selecione a planilha de matriculados para começar.")
        self._estilos()
        self._montar()
        self.after(100, self._processar_fila)

    # ------------------------------------------------------------------ UI
    def _estilos(self):
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure(".", font=("Segoe UI", 10), background=FUNDO)
        st.configure("TFrame", background=FUNDO)
        st.configure("Card.TFrame", background="white", relief="flat")
        st.configure("TLabel", background=FUNDO)
        st.configure("Card.TLabel", background="white")
        st.configure("Passo.TLabel", background="white", font=("Segoe UI Semibold", 11),
                     foreground=AZUL)
        st.configure("KpiV.TLabel", background="white", font=("Segoe UI", 20, "bold"),
                     foreground=AZUL)
        st.configure("KpiL.TLabel", background="white", foreground=CINZA, font=("Segoe UI", 9))
        st.configure("Rodar.TButton", font=("Segoe UI Semibold", 12), padding=(18, 10),
                     background=VERDE, foreground="white")
        st.map("Rodar.TButton", background=[("disabled", "#BFBFBF"), ("active", "#6CA637")])
        st.configure("TButton", padding=(10, 6))
        altura_fonte = tkfont.Font(root=self, family="Segoe UI", size=9).metrics("linespace")
        st.configure("Treeview", rowheight=max(32, int(altura_fonte * 1.85)),
                     font=("Segoe UI", 9))
        st.configure("Treeview.Heading", font=("Segoe UI Semibold", 9), background="#DDEBF7",
                     padding=(6, 6))
        st.configure("TNotebook", background=FUNDO)
        st.configure("TNotebook.Tab", padding=(14, 6), font=("Segoe UI", 10))
        st.configure("green.Horizontal.TProgressbar", background=VERDE)

    def _criar_logo_enturme(self) -> ImageTk.PhotoImage | None:
        try:
            s = max(1.0, self.winfo_fpixels("1i") / 96.0)
            f = ImageFont.truetype(caminho_recurso("assets/fonts/Poppins-Bold.ttf"), round(28 * s))
            ic = Image.open(caminho_recurso("assets/abc_icone.png")).convert("RGBA")
            h_ic = round(32 * s)
            ic = ic.resize((round(ic.width * h_ic / ic.height), h_ic), Image.LANCZOS)
            larg_txt = int(f.getlength("Enturme"))
            gap = round(10 * s)
            H = round(44 * s)
            W = larg_txt + gap + ic.width + round(4 * s)
            img = Image.new("RGBA", (W, H), (255, 255, 255, 255))
            d = ImageDraw.Draw(img)
            d.text((0, H // 2), "Enturme", font=f, fill=(42, 69, 152, 255), anchor="lm")
            img.alpha_composite(ic, (larg_txt + gap, (H - h_ic) // 2 - round(1 * s)))
            return ImageTk.PhotoImage(img)
        except Exception:
            return None

    def _montar(self):
        topo = tk.Frame(self, bg="white")
        topo.pack(fill="x")
        cab = tk.Frame(topo, bg="white")
        cab.pack(fill="x", padx=20, pady=(8, 8))
        self._logo_img = self._criar_logo_enturme()
        if self._logo_img is not None:
            tk.Label(cab, image=self._logo_img, bg="white", bd=0).pack(side="left")
        else:
            tk.Label(cab, text="Enturme", bg="white", fg=AZUL,
                     font=("Segoe UI", 20, "bold")).pack(side="left")
        ttk.Button(cab, text="❔ Como usar", command=self._ajuda).pack(side="right")

        faixa = tk.Frame(topo, bg=BANDA, height=30)
        faixa.pack(fill="x")
        tk.Label(faixa, text="ENSALAMENTO AUTOMÁTICO DE TURMAS", bg=BANDA, fg=NAVY_ESCURO,
                 font=("Segoe UI Semibold", 9)).pack(pady=(5, 5))

        corpo = ttk.Frame(self, padding=(16, 12))
        corpo.pack(fill="both", expand=True)

        # Passo 1 e 2
        card = ttk.Frame(corpo, style="Card.TFrame", padding=14)
        card.pack(fill="x")
        ttk.Label(card, text="1. Selecione a planilha (.xlsx)", style="Passo.TLabel").grid(
            row=0, column=0, sticky="w")
        ent = ttk.Entry(card, textvariable=self.caminho, state="readonly", font=("Segoe UI", 10))
        ent.grid(row=1, column=0, sticky="ew", pady=(6, 0), ipady=4)
        ttk.Button(card, text="Procurar...", command=self._escolher).grid(
            row=1, column=1, padx=(8, 0), pady=(6, 0))
        ttk.Label(card, text="2. Execute", style="Passo.TLabel").grid(
            row=0, column=2, sticky="w", padx=(24, 0))
        self.btn_rodar = ttk.Button(card, text="▶  Rodar ensalamento", style="Rodar.TButton",
                                    command=self._rodar, state="disabled")
        self.btn_rodar.grid(row=1, column=2, padx=(24, 0), pady=(6, 0), sticky="ew")
        card.columnconfigure(0, weight=1)

        barra = ttk.Frame(corpo, padding=(0, 8))
        barra.pack(fill="x")
        self.prog = ttk.Progressbar(barra, mode="indeterminate", length=180,
                                    style="green.Horizontal.TProgressbar")
        self.prog.pack(side="left")
        ttk.Label(barra, textvariable=self.status, foreground=CINZA).pack(side="left", padx=10)

        # KPIs
        self.kpi_frame = ttk.Frame(corpo)
        self.kpi_frame.pack(fill="x", pady=(0, 8))
        self.kpis = {}
        for i, (chave, rotulo) in enumerate([("lidos", "matriculados"), ("ensalados", "ensalados"),
                                             ("fora", "não ensalados"), ("turmas", "turmas"),
                                             ("erros", "erros"), ("alertas", "alertas")]):
            f = ttk.Frame(self.kpi_frame, style="Card.TFrame", padding=(10, 6))
            f.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0))
            self.kpi_frame.columnconfigure(i, weight=1)
            v = ttk.Label(f, text="–", style="KpiV.TLabel")
            v.pack()
            ttk.Label(f, text=rotulo, style="KpiL.TLabel").pack()
            self.kpis[chave] = v

        # Rodapé com ações (empacotado antes das abas para ficar sempre visível)
        rod = ttk.Frame(corpo, padding=(0, 8, 0, 0))
        rod.pack(side="bottom", fill="x")
        self.btn_excel = ttk.Button(rod, text="📊 Abrir planilha", state="disabled",
                                    command=lambda: abrir_arquivo(self.resultado.caminho_excel))
        self.btn_pdf = ttk.Button(rod, text="📄 Abrir relatório PDF", state="disabled",
                                  command=lambda: abrir_arquivo(self.resultado.caminho_relatorio))
        self.btn_pasta = ttk.Button(rod, text="📁 Abrir pasta", state="disabled",
                                    command=lambda: abrir_arquivo(
                                        os.path.dirname(self.resultado.caminho_excel)))
        for b in (self.btn_excel, self.btn_pdf, self.btn_pasta):
            b.pack(side="left", padx=(0, 8))
        ttk.Label(rod, text=f"v{__version__} · Modelo MILP monolítico (PuLP + HiGHS)",
                  foreground="#8C8C8C").pack(side="right")

        # Abas de resultado
        nb = ttk.Notebook(corpo)
        nb.pack(fill="both", expand=True)
        self.nb = nb

        aba_t = ttk.Frame(nb, padding=8)
        nb.add(aba_t, text="Turmas")
        cols = ("turma", "alunos", "vagas", "ocup", "m", "f", "pf", "barra")
        self.tv_turmas = ttk.Treeview(aba_t, columns=cols, show="headings", height=10)
        for c, t, w, anc in [("turma", "Turma", 110, "w"), ("alunos", "Alunos", 70, "center"),
                             ("vagas", "Vagas", 70, "center"), ("ocup", "Ocupação", 80, "center"),
                             ("m", "Meninos", 80, "center"), ("f", "Meninas", 80, "center"),
                             ("pf", "% Meninas", 85, "center"),
                             ("barra", "Composição (■ meninos  □ meninas)", 300, "w")]:
            self.tv_turmas.heading(c, text=t)
            self.tv_turmas.column(c, width=w, anchor=anc, stretch=(c == "barra"))
        self.tv_turmas.tag_configure("turno", background="#DDEBF7", font=("Segoe UI Semibold", 9))
        sb_t = ttk.Scrollbar(aba_t, orient="vertical", command=self.tv_turmas.yview)
        self.tv_turmas.configure(yscrollcommand=sb_t.set)
        self.tv_turmas.pack(side="left", fill="both", expand=True)
        sb_t.pack(side="right", fill="y")

        aba_i = ttk.Frame(nb, padding=8)
        nb.add(aba_i, text="Inconsistências")
        filtro = ttk.Frame(aba_i)
        filtro.pack(fill="x", pady=(0, 6))
        ttk.Label(filtro, text="Mostrar:").pack(side="left")
        self.filtro = tk.StringVar(value="TODOS")
        for v, t in [("TODOS", "Todos"), (ERRO, "Erros"), (ALERTA, "Alertas"),
                     (CORRIGIDO, "Corrigidos")]:
            ttk.Radiobutton(filtro, text=t, value=v, variable=self.filtro,
                            command=self._preencher_incs).pack(side="left", padx=6)
        quadro = ttk.Frame(aba_i)
        quadro.pack(fill="both", expand=True)
        cols = ("tipo", "linha", "nome", "campo", "desc")
        self.tv_inc = ttk.Treeview(quadro, columns=cols, show="headings")
        for c, t, w in [("tipo", "Tipo", 90), ("linha", "Linha", 55), ("nome", "Nome", 220),
                        ("campo", "Campo", 110), ("desc", "Descrição / Tratamento", 560)]:
            self.tv_inc.heading(c, text=t)
            self.tv_inc.column(c, width=w, anchor="center" if c in ("tipo", "linha") else "w",
                               stretch=(c == "desc"))
        self.tv_inc.tag_configure(ERRO, background="#FFC7CE")
        self.tv_inc.tag_configure(ALERTA, background="#FFEB9C")
        self.tv_inc.tag_configure(CORRIGIDO, background="#DDEBF7")
        sb = ttk.Scrollbar(quadro, orient="vertical", command=self.tv_inc.yview)
        self.tv_inc.configure(yscrollcommand=sb.set)
        self.tv_inc.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tv_inc.bind("<Double-1>", self._detalhe_inc)

        aba_m = ttk.Frame(nb, padding=8)
        nb.add(aba_m, text="Otimização")
        self.txt_modelo = tk.Text(aba_m, wrap="word", font=("Consolas", 9), relief="flat",
                                  bg="white", height=10)
        self.txt_modelo.pack(fill="both", expand=True)
        self.txt_modelo.insert("1.0", "Rode o ensalamento para ver os detalhes da otimização.")
        self.txt_modelo.configure(state="disabled")

    # ------------------------------------------------------------- ações
    def _ajuda(self):
        messagebox.showinfo("Como usar", AJUDA)

    def _escolher(self):
        arq = filedialog.askopenfilename(
            title="Selecione a planilha de matriculados",
            filetypes=[("Planilhas Excel", "*.xlsx *.xlsm"), ("Todos os arquivos", "*.*")])
        if arq:
            self.caminho.set(os.path.normpath(arq))
            self.btn_rodar.configure(state="normal")
            self.status.set("Planilha selecionada. Clique em 'Rodar ensalamento'.")

    def _rodar(self):
        caminho = self.caminho.get()
        if not caminho or not os.path.isfile(caminho):
            messagebox.showwarning("Atenção", "Selecione uma planilha válida.")
            return
        if not caminho.lower().endswith((".xlsx", ".xlsm")):
            messagebox.showwarning("Atenção", "O arquivo precisa ser uma planilha Excel (.xlsx).")
            return
        self.btn_rodar.configure(state="disabled")
        for b in (self.btn_excel, self.btn_pdf, self.btn_pasta):
            b.configure(state="disabled")
        self.prog.start(12)

        def trabalho():
            try:
                res = executar(caminho, progresso=lambda m: self.fila.put(("msg", m)))
                self.fila.put(("ok", res))
            except PlanilhaAbertaError as exc:
                self.fila.put(("aberta", str(exc)))
            except Exception as exc:
                self.fila.put(("erro", f"{exc}\n\n{traceback.format_exc()}"))

        threading.Thread(target=trabalho, daemon=True).start()

    def _processar_fila(self):
        try:
            while True:
                tipo, dado = self.fila.get_nowait()
                if tipo == "msg":
                    self.status.set(dado)
                    continue
                self.prog.stop()
                self.prog["value"] = 0
                self.btn_rodar.configure(state="normal")
                if tipo == "ok":
                    self._mostrar(dado)
                elif tipo == "aberta":
                    self.status.set("Feche a planilha no Excel e tente novamente.")
                    messagebox.showwarning("Planilha aberta", dado)
                else:
                    self.status.set("Ocorreu um erro inesperado.")
                    messagebox.showerror("Erro inesperado", dado[:3000])
        except queue.Empty:
            pass
        self.after(100, self._processar_fila)

    # ---------------------------------------------------------- resultado
    def _mostrar(self, res):
        self.resultado = res
        cen = res.cenario
        self.kpis["lidos"].configure(text=str(cen.total_linhas))
        self.kpis["ensalados"].configure(text=str(res.ensalados))
        self.kpis["fora"].configure(text=str(cen.total_linhas - res.ensalados),
                                    foreground="#C00000" if cen.total_linhas - res.ensalados else AZUL)
        self.kpis["turmas"].configure(text=str(len(res.estatisticas)))
        self.kpis["erros"].configure(text=str(res.contagem(ERRO)),
                                     foreground="#C00000" if res.contagem(ERRO) else AZUL)
        self.kpis["alertas"].configure(text=str(res.contagem(ALERTA)),
                                       foreground="#BF8F00" if res.contagem(ALERTA) else AZUL)

        self.tv_turmas.delete(*self.tv_turmas.get_children())
        for turno in ORDEM_TURNOS:
            ests = [e for e in res.estatisticas if e.turno == turno]
            if not ests:
                continue
            tot = sum(e.total for e in ests)
            pf = sum(e.meninas for e in ests) / tot if tot else 0
            self.tv_turmas.insert("", "end", tags=("turno",), values=(
                turno.upper(), tot, sum(e.vagas for e in ests), "", sum(e.meninos for e in ests),
                sum(e.meninas for e in ests), f"{pf:.1%}", ""))
            for e in ests:
                barra = "■" * e.meninos + "□" * e.meninas
                self.tv_turmas.insert("", "end", values=(
                    "   " + e.turma, e.total, e.vagas, f"{e.total / e.vagas:.0%}" if e.vagas else "-",
                    e.meninos, e.meninas, f"{e.pct_meninas:.1%}" if e.total else "-", barra))
        self._preencher_incs()

        linhas = [f"Arquivo: {cen.caminho}", f"Tempo total: {res.segundos:.2f} s", ""]
        for turno, r in list(res.turnos.items())[:1]:  # um único modelo para os dois turnos
            linhas.append(f"== Modelo único (Manhã + Tarde): solver {r.solver or '-'} | "
                          f"status {r.status} | {r.n_variaveis} variáveis | "
                          f"{r.n_restricoes} restrições | {r.segundos:.2f} s")
            for e in r.etapas:
                linhas.append(f"   {e.nome:<62s} = {e.valor:g}")
            linhas.append("")
        linhas += ["Modelo: MILP monolítico (os dois turnos num único problema).",
                   " Variáveis: x_ij (aluno i na turma j), z_i (aluno sem turma),",
                   "   D_max/D_min por turno e v (maior desvio de meninos).",
                   " Objetivo: min W1·Σz + W2·Σ(Dmax − Dmin) + W3·v  (W1 > W2 > W3).",
                   " Restrições: cobertura, capacidade, turno, limites de tamanho,",
                   "   |maior − menor turma| <= 1 e desvio de gênero linearizado."]
        self.txt_modelo.configure(state="normal")
        self.txt_modelo.delete("1.0", "end")
        self.txt_modelo.insert("1.0", "\n".join(linhas))
        self.txt_modelo.configure(state="disabled")

        self.btn_excel.configure(state="normal")
        self.btn_pasta.configure(state="normal")
        if res.caminho_relatorio:
            self.btn_pdf.configure(state="normal")

        if cen.bloqueante:
            self.status.set("Não foi possível ensalar: veja a aba Inconsistências.")
            self.nb.select(1)
            messagebox.showerror(
                "Ensalamento não realizado",
                f"Foram encontrados {res.contagem(ERRO)} erro(s) que impedem o ensalamento.\n\n"
                "Veja a lista na aba 'Inconsistências' (também gravada na planilha), corrija e "
                "rode novamente.")
            return
        fora = cen.total_linhas - res.ensalados
        msg = (f"Ensalamento concluído em {res.segundos:.1f} s!\n\n"
               f"{res.ensalados} aluno(s) ensalado(s) em {len(res.estatisticas)} turma(s).\n")
        if fora:
            msg += (f"\n⚠ {fora} aluno(s) NÃO foram ensalados (dados inválidos ou falta de vagas). "
                    "Veja a aba 'Inconsistências'.\n")
        msg += ("\nResultado salvo nas abas 'Ensalamento' e 'Inconsistências' da planilha"
                " e no relatório PDF.")
        self.status.set(f"Concluído: {res.ensalados} alunos ensalados. "
                        f"Resultado salvo em {os.path.basename(res.caminho_excel)}.")
        (messagebox.showwarning if fora else messagebox.showinfo)("Ensalamento concluído", msg)

    def _preencher_incs(self):
        self.tv_inc.delete(*self.tv_inc.get_children())
        if not self.resultado:
            return
        f = self.filtro.get()
        ordem = {ERRO: 0, ALERTA: 1, CORRIGIDO: 2}
        incs = sorted(self.resultado.cenario.inconsistencias,
                      key=lambda i: (ordem.get(i.tipo, 9), i.linha or 0))
        for i in incs:
            if f != "TODOS" and i.tipo != f:
                continue
            self.tv_inc.insert("", "end", tags=(i.tipo,),
                               values=(i.tipo, i.linha or "", i.nome, i.campo, i.descricao))

    def _detalhe_inc(self, _evt):
        sel = self.tv_inc.selection()
        if sel:
            v = self.tv_inc.item(sel[0], "values")
            messagebox.showinfo(f"{v[0]} – linha {v[1]}", f"{v[2]}\n\n{v[4]}")


def _sem_janela(planilha: str) -> int:
    """Modo lote: Ensalamento.exe --sem-janela planilha.xlsx (grava log ao lado)."""
    log = os.path.splitext(planilha)[0] + "_log.txt"
    with open(log, "w", encoding="utf-8") as fh:
        try:
            res = executar(planilha, progresso=lambda m: fh.write(m + "\n"))
            fh.write(f"OK ensalados={res.ensalados} erros={res.contagem(ERRO)} "
                     f"solver={','.join(r.solver for r in res.turnos.values())}\n")
            return 0
        except Exception:
            fh.write(traceback.format_exc())
            return 1


def main():
    args = [a for a in sys.argv[1:] if a != "--sem-janela"]
    if "--sem-janela" in sys.argv and args:
        sys.exit(_sem_janela(os.path.abspath(args[0])))
    try:  # textos nítidos em telas com escala (Windows)
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    app = App()
    if args and os.path.isfile(args[0]):  # planilha arrastada sobre o .exe
        app.caminho.set(os.path.abspath(args[0]))
        app.btn_rodar.configure(state="normal")
        app.status.set("Planilha selecionada. Clique em 'Rodar ensalamento'.")
    app.mainloop()


if __name__ == "__main__":
    main()
