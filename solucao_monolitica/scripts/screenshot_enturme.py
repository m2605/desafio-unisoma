"""Abre a interface Enturme, processa uma planilha e salva prints de cada tela.
Captura SOMENTE a janela do app (Win32 PrintWindow), nunca o resto da tela.

Uso: python solucao_monolitica/scripts/screenshot_enturme.py planilha.xlsx pasta_saida
"""
import ctypes
import os
import sys
from ctypes import wintypes

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from PIL import Image  # noqa: E402

import app_enturme as ap  # noqa: E402

planilha, saida = os.path.abspath(sys.argv[1]), sys.argv[2]
os.makedirs(saida, exist_ok=True)
for nome in ("showinfo", "showwarning", "showerror"):
    setattr(ap.messagebox, nome, lambda *a, **k: None)
ctypes.windll.shcore.SetProcessDpiAwareness(1)
root = ap.TkinterDnD.Tk() if ap.TEM_DND else ap.tk.Tk()
app = ap.Enturme(root)


def grab(nome):
    root.update()
    u32, g32 = ctypes.windll.user32, ctypes.windll.gdi32
    hwnd = int(root.wm_frame(), 16)
    r = wintypes.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    hdc = u32.GetWindowDC(hwnd)
    mdc = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, w, h)
    g32.SelectObject(mdc, bmp)
    u32.PrintWindow(hwnd, mdc, 2)

    class BIH(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                    ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD),
                    ("biCompression", wintypes.DWORD), ("biSizeImage", wintypes.DWORD),
                    ("biXPelsPerMeter", wintypes.LONG), ("biYPelsPerMeter", wintypes.LONG),
                    ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]
    bih = BIH(ctypes.sizeof(BIH), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * h * 4)
    g32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bih), 0)
    g32.DeleteObject(bmp)
    g32.DeleteDC(mdc)
    u32.ReleaseDC(hwnd, hdc)
    Image.frombuffer("RGB", (w, h), buf, "raw", "BGRX", 0, 1).save(os.path.join(saida, nome))


def passo1():
    grab("enturme_1_inicial.png")
    app._definir_arquivo(planilha)
    root.after(400, passo2)


def passo2():
    grab("enturme_2_selecionado.png")
    app._processar()
    root.after(250, lambda: (grab("enturme_3_processando.png"), root.after(200, esperar)))


def esperar():
    if app.tela != "resultado":
        root.after(200, esperar)
        return
    root.after(400, lambda: (grab("enturme_4_resultado.png"), root.destroy()))


root.after(900, passo1)
root.mainloop()
print("prints em", saida, "| escala", round(app.s, 2))
