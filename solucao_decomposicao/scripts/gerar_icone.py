"""Gera assets/icone.ico (ícone simples: grade de turmas)."""
import os

from PIL import Image, ImageDraw

raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(os.path.join(raiz, "assets"), exist_ok=True)
img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle((8, 8, 248, 248), radius=48, fill="#1F4E79")
cores = ["#2E75B6", "#C55A9E", "#70AD47", "#BDD7EE"]
for k, (x, y) in enumerate([(40, 40), (136, 40), (40, 136), (136, 136)]):
    d.rounded_rectangle((x, y, x + 80, y + 80), radius=16, fill=cores[k])
img.save(os.path.join(raiz, "assets", "icone.ico"),
         sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("ok")
