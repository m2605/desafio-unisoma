"""Abre o app, roda uma planilha e salva screenshots (usado no manual).

Uso: python scripts/screenshot_app.py planilha.xlsx pasta_saida
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image  # noqa: E402

import app as appmod  # noqa: E402

planilha, saida = os.path.abspath(sys.argv[1]), sys.argv[2]
os.makedirs(saida, exist_ok=True)
for nome in ("showinfo", "showwarning", "showerror"):
    setattr(appmod.messagebox, nome, lambda *a, **k: None)

try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

a = appmod.App()
a.geometry("1100x720+30+30")


def grab(nome):
    """Captura SOMENTE a janela do app (Win32 PrintWindow), nunca o resto da tela."""
    import ctypes
    from ctypes import wintypes
    a.update()
    u32, g32 = ctypes.windll.user32, ctypes.windll.gdi32
    hwnd = int(a.wm_frame(), 16)
    r = wintypes.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    hdc = u32.GetWindowDC(hwnd)
    mdc = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, w, h)
    g32.SelectObject(mdc, bmp)
    u32.PrintWindow(hwnd, mdc, 2)  # PW_RENDERFULLCONTENT

    class BIH(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                    ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                    ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                    ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                    ("biClrImportant", wintypes.DWORD)]
    bih = BIH(ctypes.sizeof(BIH), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * h * 4)
    g32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bih), 0)
    g32.DeleteObject(bmp)
    g32.DeleteDC(mdc)
    u32.ReleaseDC(hwnd, hdc)
    Image.frombuffer("RGB", (w, h), buf, "raw", "BGRX", 0, 1).save(os.path.join(saida, nome))


def passo1():
    grab("01_inicial.png")
    a.caminho.set(planilha)
    a.btn_rodar.configure(state="normal")
    a.status.set("Planilha selecionada. Clique em 'Rodar ensalamento'.")
    a.after(300, passo2)


def passo2():
    grab("02_selecionado.png")
    a._rodar()
    a.after(500, esperar)


def esperar():
    if a.resultado is None:
        a.after(300, esperar)
        return
    a.after(400, passo3)


def passo3():
    grab("03_turmas.png")
    a.nb.select(1)
    a.after(300, lambda: (grab("04_inconsistencias.png"), a.nb.select(2),
                          a.after(300, lambda: (grab("05_otimizacao.png"), a.destroy()))))


a.after(800, passo1)
a.mainloop()
print("screenshots em", saida)
