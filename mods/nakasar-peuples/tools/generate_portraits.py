#!/usr/bin/env python3
"""Portraits des PNJ pour la fenêtre de dialogue : tête et buste recadrés dans les rendus vanilla des modèles
(Common/Icons/ModelsGenerated/<Modèle>.png, 128x128, ceux que la page vanilla des Souvenirs affiche), agrandis au plus
proche voisin pour garder les pixels nets.

    python3 tools/generate_portraits.py --assets <dossier du jeu>/Assets.zip [--preview DIR]

Sortie : src/main/resources/Common/Icons/Nakasar/Peuples/Portraits/<Modèle>.png, et la liste des portraits dans
src/main/java/.../dialogue/Portraits.java (entre les marqueurs GENERATED). Le Java choisit le portrait du modèle du PNJ,
ou du plus long préfixe connu (Kweebec_Sapling_Pink -> Kweebec_Sapling) : les variantes vanilla n'ont pas de rendu.
"""
import argparse
import io
import math
import re
import zipfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "src/main/resources/Common/Icons/Nakasar/Peuples/Portraits"
JAVA = ROOT / "src/main/java/dev/nakasar/hytale/peuples/dialogue/Portraits.java"
SOURCE = "Common/Icons/ModelsGenerated/"
# Les peuples d'Orbis (et leurs ennemis) qui parlent ou pourraient parler.
PEOPLES = ("Kweebec_", "Trork_", "Feran_", "Outlander_", "Goblin_", "Scarak_", "Klops", "Slothian")
MIN_SIZE = 160  # côté minimal du portrait livré (agrandissement entier au plus proche voisin)
# Recadrages à la main quand le cadrage automatique tombe mal : (x, y, côté) dans le rendu 128x128.
OVERRIDES = {}


def crop_box(im):
    """Carré tête + buste : le haut de la silhouette sur 62 % de sa hauteur ; une petite créature est prise entière."""
    left, top, right, bottom = im.getbbox()
    height = bottom - top
    if height < 70:
        side = min(128, max(right - left, height) + 6)
        y0 = max(0, min(128 - side, bottom - side + 2))
    else:
        side = min(128, max(int(0.62 * height), 40))
        y0 = max(0, top - 3)
    cx = (left + right) // 2
    x0 = max(0, min(128 - side, cx - side // 2))
    return x0, y0, side


def portrait(im, name):
    x0, y0, side = OVERRIDES.get(name) or crop_box(im)
    crop = im.crop((x0, y0, x0 + side, y0 + side))
    factor = math.ceil(MIN_SIZE / side)
    return crop.resize((side * factor, side * factor), Image.NEAREST)


def write_java(names):
    text = JAVA.read_text(encoding="utf-8")
    body = ",\n".join(f'            "{n}"' for n in names) + "\n"
    text = re.sub(r"(// GENERATED BEGIN[^\n]*\n)(.*?)([ \t]*// GENERATED END)", lambda m: m.group(1) + body + m.group(3),
                  text, flags=re.S)
    JAVA.write_text(text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", required=True, help="Assets.zip du jeu")
    parser.add_argument("--preview", help="dossier où écrire une planche de tous les portraits")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    names = []
    with zipfile.ZipFile(args.assets) as z:
        for entry in sorted(z.namelist()):
            if not entry.startswith(SOURCE) or not entry.endswith(".png"):
                continue
            name = entry[len(SOURCE):-4]
            if "/" in name or not name.startswith(PEOPLES):
                continue
            im = Image.open(io.BytesIO(z.read(entry))).convert("RGBA")
            if im.size != (128, 128) or im.getbbox() is None:
                continue
            portrait(im, name).save(OUT / f"{name}.png", optimize=True)
            names.append(name)
    write_java(names)
    print(f"{len(names)} portraits -> {OUT}")
    if args.preview:
        cell = 96
        cols = 10
        sheet = Image.new("RGBA", (cols * cell, math.ceil(len(names) / cols) * cell), (24, 30, 40, 255))
        for i, n in enumerate(names):
            p = Image.open(OUT / f"{n}.png").resize((cell - 6, cell - 6), Image.NEAREST)
            sheet.alpha_composite(p, ((i % cols) * cell + 3, (i // cols) * cell + 3))
        Path(args.preview).mkdir(parents=True, exist_ok=True)
        sheet.save(Path(args.preview) / "portraits.png")


if __name__ == "__main__":
    main()
