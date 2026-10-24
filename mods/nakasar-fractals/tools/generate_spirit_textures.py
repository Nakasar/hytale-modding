#!/usr/bin/env python3
"""Textures spectrales des esprits animaux de Carnasse (Marais) : les textures des animaux vanilla (loup blanc, renard,
grizzly), passées en teintes vert d'eau translucides (Kevin, 24 octobre 2026). Le modèle et les animations restent
ceux du jeu (Parent dans generate_swampland.models) ; seule la texture change.

Les textures du jeu ne sont pas dans le dépôt : on les lit dans Assets.zip (dossier du jeu,
%APPDATA%\\Hytale\\install\\release\\package\\game\\latest\\Assets.zip). Les PNG écrits, eux, sont versionnés.

Usage : python3 mods/nakasar-fractals/tools/generate_spirit_textures.py CHEMIN/Assets.zip"""

import io
import sys
import zipfile
from pathlib import Path

from PIL import Image

import fractal_common as fc

OUT = fc.COMMON / fc.NPC_MODELS / "Spirits"
# animal : texture vanilla (sous Common/)
SOURCES = {
    "Wolf": "NPC/Beast/Wolf/Models/Model_Textures/White.png",
    "Fox": "NPC/Beast/Fox/Models/Texture.png",
    "Bear": "NPC/Beast/Bear_Grizzly/Models/Texture.png",
}
DARK = (40, 150, 125)
LIGHT = (215, 255, 240)
ALPHA = (120, 200)     # opacité des zones sombres et claires : le corps reste lisible mais on voit au travers


def spectral(image):
    image = image.convert("RGBA")
    pixels = list(image.getdata())
    lums = [0.3 * r + 0.59 * g + 0.11 * b for r, g, b, a in pixels if a > 0]
    lo, hi = (min(lums), max(lums)) if lums else (0, 255)
    span = max(1.0, hi - lo)
    out = []
    for r, g, b, a in pixels:
        if a == 0:
            out.append((0, 0, 0, 0))
            continue
        t = (0.3 * r + 0.59 * g + 0.11 * b - lo) / span
        color = tuple(round(d + (l - d) * t) for d, l in zip(DARK, LIGHT))
        out.append(color + (round(min(a, ALPHA[0] + (ALPHA[1] - ALPHA[0]) * t)),))
    result = Image.new("RGBA", image.size)
    result.putdata(out)
    return result


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    OUT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(sys.argv[1]) as assets:
        for animal, path in SOURCES.items():
            spectral(Image.open(io.BytesIO(assets.read("Common/" + path)))).save(OUT / f"{animal}.png")
            print(f"{OUT / animal}.png")


if __name__ == "__main__":
    main()
