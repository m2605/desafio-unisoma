"""
Desenho das telas da interface "Enturme" (glassmorphism) com Pillow.

Cada tela é composta como uma imagem: fundo com formas geométricas, faixas e
cartões de "vidro" (recorte desfocado do fundo + véu branco + borda), textos em
Poppins. Botões e links são imagens separadas (normal / hover) para que a janela
Tkinter trate cliques e o efeito de passar o mouse.

Todas as medidas estão em pixels lógicos do design (largura 960) e são
multiplicadas pela escala ``s`` (DPI do monitor / tamanho da tela).
"""
from __future__ import annotations

import os
import random
import sys
from dataclasses import dataclass
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter, ImageFont

LARGURA = 960
ALTURA_SELECAO = 643     # telas 1 e 2
ALTURA_RESULTADO = 823   # tela 3

# Paleta extraída do design
NAVY = (42, 69, 152)          # #2A4598 títulos
NAVY_ESCURO = (30, 50, 112)   # #1E3270 texto dos botões claros
AZUL = (13, 110, 172)         # #0D6EAC
AZUL_HOVER = (10, 92, 146)
VERDE_BTN = (125, 185, 69)    # #7DB945
VERDE_BTN_HOVER = (108, 166, 55)
VERDE_OK = (26, 157, 135)     # #1A9D87
VERDE_OK_TXT = (11, 92, 77)   # #0B5C4D
VERDE_PCT = (15, 107, 91)     # #0F6B5B
VERMELHO = (192, 57, 43)
VERMELHO_TXT = (130, 30, 20)
CINZA_BTN = (184, 190, 201)   # #B8BEC9
CINZA_BTN_HOVER = (166, 173, 186)
CINZA_DESAB = (213, 217, 224)  # #D5D9E0
CINZA_DESAB_TXT = (145, 152, 166)
MASC = (108, 185, 238)        # #6CB9EE
FEM = (240, 168, 230)         # #F0A8E6
AVISO_BG = (253, 241, 200)    # #FDF1C8
AVISO_TXT = (92, 63, 0)       # #5C3F00
AVISO_DOBRA = (232, 205, 130)
OK_BG = (214, 240, 228)
FUNDO_CLARO = (236, 250, 239)
FORMA_NAVY = (44, 71, 115)
FORMA_VERDE = (119, 162, 116)
BANDA = (167, 218, 206)
BRANCO = (255, 255, 255)


def recurso(*partes: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *partes)


@lru_cache(maxsize=64)
def fonte(peso: str, tamanho: float) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(recurso("assets", "fonts", f"Poppins-{peso}.ttf"), max(1, round(tamanho)))


@dataclass
class Hotspot:
    """Área clicável desenhada como imagem própria (botão ou link)."""
    nome: str
    x: int
    y: int
    normal: Image.Image
    hover: Image.Image | None = None


class Pintor:
    def __init__(self, s: float):
        self.s = s
        self._fundo_cache: dict[int, tuple[Image.Image, Image.Image]] = {}

    def p(self, v: float) -> int:
        return round(v * self.s)

    def caixa(self, x0, y0, x1, y1):
        return (self.p(x0), self.p(y0), self.p(x1), self.p(y1))

    # ------------------------------------------------------------- fundo
    def fundo(self, altura: int) -> tuple[Image.Image, Image.Image]:
        """Fundo nítido e versão desfocada (para os cartões de vidro)."""
        if altura in self._fundo_cache:
            return self._fundo_cache[altura]
        W, H = self.p(LARGURA), self.p(altura)
        sup = 2  # supersampling para bordas suaves
        img = Image.new("RGB", (W * sup, H * sup), FUNDO_CLARO)
        rng = random.Random(14)
        t = self.p(118) * sup
        cols, lins = W * sup // t + 2, H * sup // t + 2
        for i in range(cols):
            for j in range(lins):
                # cada forma é desenhada num ladrilho próprio (fica recortada nele)
                lad = Image.new("RGB", (t, t), FUNDO_CLARO)
                d = ImageDraw.Draw(lad)
                r = rng.random()
                cor = FORMA_NAVY if rng.random() < 0.55 else FORMA_VERDE
                if r < 0.25:
                    pass                                   # ladrilho vazio
                elif r < 0.50:                             # meio círculo encostado num lado
                    lado = rng.choice(["t", "b", "l", "r"])
                    bb = {"t": (0, -t // 2, t, t // 2), "b": (0, t // 2, t, t * 3 // 2),
                          "l": (-t // 2, 0, t // 2, t), "r": (t // 2, 0, t * 3 // 2, t)}[lado]
                    d.ellipse(bb, fill=cor)
                elif r < 0.78:                             # quarto de círculo a partir de um canto
                    cx, cy = rng.choice([(0, 0), (t, 0), (0, t), (t, t)])
                    d.ellipse((cx - t, cy - t, cx + t, cy + t), fill=cor)
                elif r < 0.90:                             # círculo inteiro
                    d.ellipse((t * 0.06, t * 0.06, t * 0.94, t * 0.94), fill=cor)
                else:                                      # arco grande (meia-lua)
                    d.ellipse((-t // 2, 0, t * 3 // 2, t * 2), fill=cor)
                img.paste(lad, (i * t, j * t))
        img = img.resize((W, H), Image.LANCZOS)
        # véu claro para suavizar o padrão (como no design)
        veu = Image.new("RGB", (W, H), FUNDO_CLARO)
        img = Image.blend(img, veu, 0.08)
        borrado = img.filter(ImageFilter.GaussianBlur(self.p(26)))
        self._fundo_cache[altura] = (img, borrado)
        return img, borrado

    # ------------------------------------------------------------- vidro
    def vidro(self, base: Image.Image, borrado: Image.Image, caixa, raio, veu=118,
              cor_veu=BRANCO, borda=(255, 255, 255, 210), largura_borda=2):
        x0, y0, x1, y1 = self.caixa(*caixa)
        r = self.p(raio)
        mascara = Image.new("L", (x1 - x0, y1 - y0), 0)
        ImageDraw.Draw(mascara).rounded_rectangle((0, 0, x1 - x0 - 1, y1 - y0 - 1), radius=r, fill=255)
        # sombra suave
        sombra = Image.new("RGBA", base.size, (0, 0, 0, 0))
        ImageDraw.Draw(sombra).rounded_rectangle((x0, y0 + self.p(6), x1, y1 + self.p(6)), radius=r,
                                                 fill=(20, 40, 70, 40))
        sombra = sombra.filter(ImageFilter.GaussianBlur(self.p(10)))
        base.alpha_composite(sombra)
        pedaco = borrado.crop((x0, y0, x1, y1)).convert("RGBA")
        pedaco = Image.alpha_composite(pedaco, Image.new("RGBA", pedaco.size, (*cor_veu, veu)))
        base.paste(pedaco, (x0, y0), mascara)
        if borda:
            ImageDraw.Draw(base).rounded_rectangle((x0, y0, x1 - 1, y1 - 1), radius=r, outline=borda,
                                                   width=max(1, self.p(largura_borda)))

    def tracejado(self, base, caixa, raio, cor=NAVY, traco=6, vao=4, largura=1.6):
        """Retângulo arredondado tracejado (área de soltar o arquivo)."""
        x0, y0, x1, y1 = [v * 1.0 for v in caixa]
        r = raio
        import math
        pontos = []
        # percorre o contorno em passos de 1 px lógico
        segs = [((x0 + r, y0), (x1 - r, y0)), ("arc", (x1 - r, y0 + r), -90, 0),
                ((x1, y0 + r), (x1, y1 - r)), ("arc", (x1 - r, y1 - r), 0, 90),
                ((x1 - r, y1), (x0 + r, y1)), ("arc", (x0 + r, y1 - r), 90, 180),
                ((x0, y1 - r), (x0, y0 + r)), ("arc", (x0 + r, y0 + r), 180, 270)]
        for sg in segs:
            if sg[0] == "arc":
                _, (cx, cy), a0, a1 = sg
                n = max(2, int(abs(a1 - a0) / 90 * r * 1.6))
                for k in range(n):
                    a = math.radians(a0 + (a1 - a0) * k / n)
                    pontos.append((cx + r * math.cos(a), cy + r * math.sin(a)))
            else:
                (ax, ay), (bx, by) = sg
                n = max(2, int(math.hypot(bx - ax, by - ay)))
                for k in range(n):
                    pontos.append((ax + (bx - ax) * k / n, ay + (by - ay) * k / n))
        d = ImageDraw.Draw(base)
        periodo, acum, desenhando, ini = traco + vao, 0.0, True, pontos[0]
        for a, b in zip(pontos, pontos[1:] + pontos[:1]):
            passo = math.hypot(b[0] - a[0], b[1] - a[1])
            fase = acum % periodo
            if fase < traco:
                d.line((self.p(a[0]), self.p(a[1]), self.p(b[0]), self.p(b[1])), fill=cor,
                       width=max(1, self.p(largura)))
            acum += passo

    # ------------------------------------------------------------- texto
    def texto(self, base, xy, txt, peso, tam, cor, ancora="mm", espacamento=0.0):
        d = ImageDraw.Draw(base)
        f = fonte(peso, tam * self.s)
        x, y = self.p(xy[0]), self.p(xy[1])
        if not espacamento:
            d.text((x, y), txt, font=f, fill=cor, anchor=ancora)
            return
        larg = sum(f.getlength(c) for c in txt) + self.p(espacamento) * (len(txt) - 1)
        cx = x - larg / 2 if ancora[0] == "m" else x
        for c in txt:
            d.text((cx, y), c, font=f, fill=cor, anchor="l" + ancora[1])
            cx += f.getlength(c) + self.p(espacamento)

    def texto_rico(self, base, xy, partes, tam, cor):
        """Linha centralizada com trechos em pesos diferentes: [(texto, peso), ...]."""
        d = ImageDraw.Draw(base)
        fs = [fonte(p, tam * self.s) for _, p in partes]
        larg = sum(f.getlength(t) for (t, _), f in zip(partes, fs))
        x = self.p(xy[0]) - larg / 2
        for (t, _), f in zip(partes, fs):
            d.text((x, self.p(xy[1])), t, font=f, fill=cor, anchor="lm")
            x += f.getlength(t)

    # ------------------------------------------------------------- ícones
    def icone_upload(self, base, cx, cy, cor=AZUL):
        d = ImageDraw.Draw(base)
        w = max(2, self.p(3.2))
        p = self.p
        d.line((p(cx), p(cy - 18), p(cx), p(cy + 6)), fill=cor, width=w)
        d.line((p(cx - 10), p(cy - 8), p(cx), p(cy - 18), p(cx + 10), p(cy - 8)), fill=cor, width=w,
               joint="curve")
        d.line((p(cx - 19), p(cy), p(cx - 19), p(cy + 16), p(cx + 19), p(cy + 16), p(cx + 19), p(cy)),
               fill=cor, width=w, joint="curve")

    def icone_check(self, base, cx, cy, tam=18, cor=AZUL, largura=3.6):
        d = ImageDraw.Draw(base)
        p = self.p
        d.line((p(cx - tam), p(cy), p(cx - tam * 0.3), p(cy + tam * 0.7), p(cx + tam), p(cy - tam * 0.7)),
               fill=cor, width=max(2, p(largura)), joint="curve")

    def icone_alerta(self, base, cx, cy, cor=AVISO_TXT):
        d = ImageDraw.Draw(base)
        p = self.p
        d.polygon((p(cx), p(cy - 12), p(cx + 13), p(cy + 10), p(cx - 13), p(cy + 10)), outline=cor,
                  width=max(1, p(2)))
        d.line((p(cx), p(cy - 4), p(cx), p(cy + 3)), fill=cor, width=max(1, p(2)))
        d.ellipse((p(cx - 1.3), p(cy + 5.5), p(cx + 1.3), p(cy + 8)), fill=cor)

    # ------------------------------------------------------------- botões
    def botao(self, nome, caixa, rotulo, cor, cor_hover, cor_txt, tam=17, anel=True) -> Hotspot:
        """Botão em pílula com anel branco translúcido (como no design).
        ``caixa`` é o contorno externo (anel incluído), alinhado com os cartões."""
        x0, y0, x1, y1 = caixa
        m = 7 if anel else 0
        W, H = self.p(x1 - x0), self.p(y1 - y0)

        def desenhar(c):
            im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            if anel:
                d.rounded_rectangle((0, 0, W - 1, H - 1), radius=H // 2, fill=(255, 255, 255, 215))
            mm = self.p(m)
            d.rounded_rectangle((mm, mm, W - 1 - mm, H - 1 - mm), radius=(H - 2 * mm) // 2, fill=c)
            d.text((W / 2, H / 2), rotulo, font=fonte("SemiBold", tam * self.s), fill=cor_txt, anchor="mm")
            return im

        return Hotspot(nome, self.p(x0), self.p(y0), desenhar(cor),
                       desenhar(cor_hover) if cor_hover else None)

    def link(self, nome, cx, cy, rotulo, tam=15, cor=AZUL, cor_hover=AZUL_HOVER) -> Hotspot:
        f = fonte("Medium", tam * self.s)
        w = int(f.getlength(rotulo)) + 4
        h = self.p(tam * 1.9)

        def desenhar(c):
            im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            d.text((w / 2, h / 2), rotulo, font=f, fill=c, anchor="mm")
            yl = h / 2 + self.p(tam * 0.62)
            d.line((2, yl, w - 2, yl), fill=c, width=max(1, self.p(1.2)))
            return im

        return Hotspot(nome, self.p(cx) - w // 2, self.p(cy) - h // 2, desenhar(cor), desenhar(cor_hover))

    # ------------------------------------------------------------- moldura comum
    def moldura(self, altura: int, logo: Image.Image) -> Image.Image:
        nitido, borrado = self.fundo(altura)
        base = nitido.convert("RGBA")
        W = self.p(LARGURA)
        # cabeçalho de vidro
        cab = borrado.crop((0, 0, W, self.p(62))).convert("RGBA")
        cab = Image.alpha_composite(cab, Image.new("RGBA", cab.size, (255, 255, 255, 175)))
        base.paste(cab, (0, 0))
        d = ImageDraw.Draw(base)
        d.line((0, self.p(62), W, self.p(62)), fill=(255, 255, 255, 230), width=max(1, self.p(1.5)))
        # logo: "Enturme" + ícone ABC
        f = fonte("Bold", 30 * self.s)
        larg_txt = f.getlength("Enturme")
        h_ic = self.p(34)
        ic = logo.resize((round(logo.width * h_ic / logo.height), h_ic), Image.LANCZOS)
        total = larg_txt + self.p(10) + ic.width
        x = (W - total) / 2
        d.text((x, self.p(32)), "Enturme", font=f, fill=NAVY, anchor="lm")
        base.alpha_composite(ic, (round(x + larg_txt + self.p(10)), self.p(32) - h_ic // 2 - self.p(1)))
        # faixa verde-água
        banda = borrado.crop((0, self.p(63), W, self.p(104))).convert("RGBA")
        banda = Image.alpha_composite(banda, Image.new("RGBA", banda.size, (*BANDA, 200)))
        base.paste(banda, (0, self.p(63)))
        self.texto(base, (LARGURA / 2, 83.5), "ENSALAMENTO AUTOMÁTICO DE TURMAS", "Medium", 13.5,
                   NAVY_ESCURO, espacamento=1.3)
        return base


# =============================================================== telas
def tela_selecao(pt: Pintor, logo, arquivo: str | None, arrastando=False, processando=False):
    """Telas 1 (sem arquivo) e 2 (arquivo escolhido)."""
    base = pt.moldura(ALTURA_SELECAO, logo)
    _, borrado = pt.fundo(ALTURA_SELECAO)
    pt.vidro(base, borrado, (57, 133, 903, 518), 34, veu=125)
    cor_borda = AZUL if arrastando else NAVY
    pt.tracejado(base, (87, 163, 873, 488), 18, cor=cor_borda, largura=2.4 if arrastando else 1.6)
    hs: list[Hotspot] = []
    cx = LARGURA / 2
    if processando:
        pt.texto(base, (cx, 318), "Processando a planilha…", "SemiBold", 21, NAVY)
        pt.texto(base, (cx, 352), "O modelo de otimização está montando as turmas", "Regular", 14, NAVY)
        pt.texto(base, (cx, 448), os.path.basename(arquivo or ""), "Medium", 13, NAVY_ESCURO)
        hs.append(pt.botao("confirmar", (57, 534, 903, 612), "Processando…", CINZA_DESAB, None,
                           CINZA_DESAB_TXT, tam=18))
        return base, hs
    if not arquivo:
        if arrastando:
            pt.icone_upload(base, cx, 262)
            pt.texto(base, (cx, 318), "Solte o arquivo aqui", "SemiBold", 21, NAVY)
            pt.texto(base, (cx, 352), "Planilha do Excel (.xlsx)", "Regular", 14, NAVY)
        else:
            pt.icone_upload(base, cx, 252)
            pt.texto(base, (cx, 305), "Selecione a planilha de matriculados", "SemiBold", 21, NAVY)
            pt.texto(base, (cx, 340), "Arquivo do Excel (.xlsx) com as abas Alunos e Turmas", "Regular",
                     13.5, NAVY)
            pt.texto(base, (cx, 365), "Você também pode arrastar o arquivo e soltar aqui", "Regular",
                     12.5, (90, 108, 160))
            hs.append(pt.botao("buscar", (383, 385, 577, 447), "Buscar arquivo", VERDE_BTN,
                               VERDE_BTN_HOVER, NAVY_ESCURO, tam=15.5))
        hs.append(pt.botao("confirmar", (57, 534, 903, 612),
                           "Confirmar processamento da planilha de alunos", CINZA_DESAB, None,
                           CINZA_DESAB_TXT, tam=18))
        return base, hs
    # tela 2: arquivo escolhido
    pt.icone_check(base, cx, 245, tam=18)
    pt.texto(base, (cx, 302), "Planilha selecionada", "SemiBold", 21, NAVY)
    nome = os.path.basename(arquivo)
    if len(nome) > 48:
        nome = nome[:22] + "…" + nome[-22:]
    f = fonte("Medium", 15.5 * pt.s)
    larg = f.getlength(nome) / pt.s + 76
    x0, x1 = cx - larg / 2, cx + larg / 2
    d = ImageDraw.Draw(base)
    d.rounded_rectangle(pt.caixa(x0, 330, x1, 376), radius=pt.p(23), fill=(255, 255, 255, 150),
                        outline=NAVY, width=max(1, pt.p(1.6)))
    pt.icone_check(base, x0 + 32, 353, tam=6.5, cor=NAVY, largura=1.8)
    pt.texto(base, (x0 + 50, 353), nome, "Medium", 15.5, NAVY, ancora="lm")
    hs.append(pt.link("trocar", cx, 411, "Escolher outro arquivo"))
    hs.append(pt.botao("confirmar", (57, 534, 903, 612), "Confirmar processamento da planilha de alunos",
                       AZUL, AZUL_HOVER, BRANCO, tam=18))
    return base, hs


@dataclass
class DadosResultado:
    sucesso: bool
    pasta: str
    pct_alocados: float
    alocados: int
    matriculados: int
    turnos: list[tuple[str, int, float]]   # (turno, alunos, fração de meninos)
    inconsistencias: int
    nao_alocados: int
    erros: int


def _fmt_pct(v: float) -> str:
    return f"{v * 100:.1f}%".replace(".", ",")


def tela_resultado(pt: Pintor, logo, r: DadosResultado):
    base = pt.moldura(ALTURA_RESULTADO, logo)
    _, borrado = pt.fundo(ALTURA_RESULTADO)
    hs: list[Hotspot] = []
    cor = VERDE_OK if r.sucesso else VERMELHO
    # banner de status
    pt.vidro(base, borrado, (57, 133, 903, 246), 46, veu=205, borda=(*cor, 255))
    d = ImageDraw.Draw(base)
    d.ellipse(pt.caixa(94, 152, 170, 228), fill=cor)
    if r.sucesso:
        pt.icone_check(base, 132, 190, tam=13, cor=BRANCO, largura=4)
        titulo, sub = "Processamento concluído com sucesso!", f"A planilha foi salva na pasta {r.pasta}."
    else:
        pt.texto(base, (132, 189), "!", "Bold", 34, BRANCO)
        titulo, sub = "Não foi possível montar as turmas", \
            "Corrija os erros da aba “Inconsistências” e processe de novo."
    pt.texto(base, (192, 178), titulo, "Bold", 24.5, VERDE_OK_TXT if r.sucesso else VERMELHO_TXT,
             ancora="lm")
    pt.texto(base, (192, 210), sub, "Regular", 14.5, NAVY, ancora="lm")

    # cartão do percentual
    pt.vidro(base, borrado, (57, 270, 285, 470), 26, veu=125)
    pt.texto(base, (86, 350), _fmt_pct(r.pct_alocados), "Bold", 42, VERDE_PCT, ancora="ls")
    pt.texto(base, (86, 382), "alunos alocados", "SemiBold", 14.5, NAVY, ancora="ls")
    pt.texto(base, (86, 402), f"{r.alocados} de {r.matriculados} matriculados", "Regular", 13, NAVY,
             ancora="ls")

    # cartão de proporção de gênero
    pt.vidro(base, borrado, (307, 270, 903, 470), 26, veu=125)
    pt.texto(base, (336, 299), "Proporção de gênero por turno", "Medium", 13, NAVY, ancora="lm")
    y = 335
    for turno, alunos, pm in r.turnos[:2]:
        pt.texto(base, (336, y), turno, "Medium", 14.5, NAVY, ancora="lm")
        pt.texto(base, (874, y), f"{alunos} alunos", "Regular", 14, NAVY, ancora="rm")
        bx0, bx1, by0, by1 = 336, 874, y + 19, y + 45
        corte = bx0 + (bx1 - bx0) * pm
        barra = Image.new("RGBA", (pt.p(bx1 - bx0), pt.p(by1 - by0)), (0, 0, 0, 0))
        mask = Image.new("L", barra.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, barra.width - 1, barra.height - 1),
                                               radius=barra.height // 2, fill=255)
        db = ImageDraw.Draw(barra)
        db.rectangle((0, 0, pt.p(corte - bx0), barra.height), fill=MASC)
        db.rectangle((pt.p(corte - bx0), 0, barra.width, barra.height), fill=FEM)
        base.paste(barra, pt.caixa(bx0, by0, bx1, by1)[:2], mask)
        pt.texto(base, (bx0 + 12, (by0 + by1) / 2), f"Masculino {pm * 100:.0f}%", "SemiBold", 12,
                 NAVY_ESCURO, ancora="lm")
        pt.texto(base, (bx1 - 12, (by0 + by1) / 2), f"Feminino {(1 - pm) * 100:.0f}%", "SemiBold", 12,
                 NAVY_ESCURO, ancora="rm")
        y += 69
    if not r.turnos:
        pt.texto(base, (605, 380), "Nenhum aluno foi alocado.", "Regular", 14, NAVY)

    # bilhete de aviso
    x0, y0, x1, y1 = 192, 492, 767, 590
    if r.inconsistencias:
        fundo, txt = AVISO_BG, AVISO_TXT
    else:
        fundo, txt = OK_BG, VERDE_OK_TXT
    sombra = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(sombra).rectangle(pt.caixa(x0, y0 + 4, x1, y1 + 4), fill=(60, 50, 10, 45))
    base.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(pt.p(6))))
    dobra = 22
    d = ImageDraw.Draw(base)
    d.polygon([pt.caixa(x0, y0, x0, y0)[:2], pt.caixa(x1 - dobra, y0, 0, 0)[:2],
               pt.caixa(x1, y0 + dobra, 0, 0)[:2], pt.caixa(x1, y1, 0, 0)[:2],
               pt.caixa(x0, y1, 0, 0)[:2]], fill=fundo)
    if r.inconsistencias:
        d.polygon([pt.caixa(x1 - dobra, y0, 0, 0)[:2], pt.caixa(x1, y0 + dobra, 0, 0)[:2],
                   pt.caixa(x1 - dobra, y0 + dobra, 0, 0)[:2]], fill=AVISO_DOBRA)
        pt.icone_alerta(base, 232, 543)
        n = r.inconsistencias
        palavra = "inconsistência" if n == 1 else "inconsistências"
        pt.texto_rico(base, (480, 518), [("Notamos ", "Regular"), (f"{n} {palavra}", "SemiBold"),
                                         (" nos dados originais.", "Regular")], 14, txt)
        pt.texto(base, (480, 541), "Por favor, verifique a aba “Inconsistências” na sua planilha",
                 "Regular", 14, txt)
        final = "para ver os alunos não alocados." if r.nao_alocados else "para conferir os ajustes feitos."
        pt.texto(base, (480, 564), final, "Regular", 14, txt)
    else:
        pt.icone_check(base, 232, 541, tam=9, cor=VERDE_OK, largura=2.6)
        pt.texto(base, (490, 530), "Nenhuma inconsistência encontrada nos dados.", "SemiBold", 14, txt)
        pt.texto(base, (490, 553), "Todos os alunos foram alocados.", "Regular", 14, txt)

    # botões (os dois de baixo com a mesma largura, conforme o ajuste pedido)
    if r.sucesso:
        hs.append(pt.botao("baixar_planilha", (57, 610, 903, 682), "Baixar a planilha das turmas",
                           VERDE_BTN, VERDE_BTN_HOVER, NAVY_ESCURO, tam=17.5))
    else:
        hs.append(pt.botao("baixar_planilha", (57, 610, 903, 682), "Abrir a planilha com as inconsistências",
                           VERDE_BTN, VERDE_BTN_HOVER, NAVY_ESCURO, tam=17.5))
    hs.append(pt.botao("baixar_pdf", (57, 702, 470, 774), "Baixar Relatório em PDF", AZUL, AZUL_HOVER,
                       BRANCO, tam=16.5))
    hs.append(pt.botao("outra", (490, 702, 903, 774), "Processar outra planilha", CINZA_BTN,
                       CINZA_BTN_HOVER, NAVY_ESCURO, tam=16.5))
    return base, hs
