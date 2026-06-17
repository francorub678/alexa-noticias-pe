#!/usr/bin/env python3
"""Genera un ícono 512x512 PNG para el Flash Briefing (colores de Perú)."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

SIZE = 512
ROJO = (213, 43, 30)      # rojo bandera Perú
BLANCO = (255, 255, 255)

img = Image.new("RGB", (SIZE, SIZE), ROJO)
d = ImageDraw.Draw(img)

# Bandas blancas superior e inferior (bandera horizontal, estilo limpio)
d.rectangle([0, 0, SIZE, 70], fill=BLANCO)
d.rectangle([0, SIZE - 70, SIZE, SIZE], fill=BLANCO)


def fuente(tam):
    for ruta in [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ]:
        if Path(ruta).exists():
            try:
                return ImageFont.truetype(ruta, tam)
            except Exception:
                pass
    return ImageFont.load_default()


def texto_centrado(txt, y, tam, color):
    f = fuente(tam)
    bbox = d.textbbox((0, 0), txt, font=f)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    d.text(((SIZE - w) / 2 - bbox[0], y - h / 2 - bbox[1]), txt, font=f, fill=color)


texto_centrado("TOP", 205, 150, BLANCO)
texto_centrado("PERÚ", 335, 150, BLANCO)
texto_centrado("NOTICIAS", 35, 34, ROJO)
texto_centrado("CADA MAÑANA", SIZE - 35, 30, ROJO)

salida = Path(__file__).parent / "docs" / "icono.png"
img.save(salida, "PNG")
print(f"Ícono guardado en {salida}")
