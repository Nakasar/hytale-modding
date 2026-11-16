#!/usr/bin/env python3
"""Icônes de carte des villages (étape 2) : une pousse à deux feuilles sur un toit de chaumière, figure claire cernée
de noir comme les marqueurs vanilla (Common/UI/WorldMap/MapMarkers/GoblinBreach.png : 48x48, figure blanche, contour
noir). Aucune icône vanilla de village ni de Kweebec n'existe dans Assets.zip (0.7.x), d'où ce dessin.

    python3 tools/generate_map_icons.py [--preview DIR]

Sortie : src/main/resources/Common/UI/WorldMap/MapMarkers/Nakasar_Peuples_Kweebec{,Compass}.png
"""
import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "src/main/resources/Common/UI/WorldMap/MapMarkers"
SIZE = 48
SS = 8  # suréchantillonnage pour des bords lisses


def leaf(draw, base, angle, length, width, fill):
    """Feuille en amande partant de `base` dans la direction `angle` (radians, 0 = vers la droite)."""
    points = []
    for i in range(33):
        t = i / 32
        # demi-largeur en fuseau, nulle aux deux bouts
        w = width * math.sin(math.pi * t) * (1 - 0.25 * t)
        points.append((t * length, w))
    points += [(x, -y) for x, y in reversed(points)]
    ca, sa = math.cos(angle), math.sin(angle)
    draw.polygon([(base[0] + x * ca - y * sa, base[1] + x * sa + y * ca) for x, y in points], fill=fill)


def figure(scale):
    """Masque (L) de la figure : toit en chevron, pousse et deux feuilles, en coordonnées 48x48 multipliées par `scale`."""
    s = scale
    mask = Image.new("L", (SIZE * s, SIZE * s), 0)
    d = ImageDraw.Draw(mask)
    # Toit de chaumière (chevron épais) et murs bas.
    d.polygon([(6 * s, 31 * s), (24 * s, 19 * s), (42 * s, 31 * s), (38 * s, 34 * s), (24 * s, 25 * s), (10 * s, 34 * s)], fill=255)
    d.rectangle([13 * s, 32 * s, 35 * s, 41 * s], fill=255)
    d.rectangle([21 * s, 35 * s, 27 * s, 41 * s], fill=0)  # porte
    # Tige de la pousse, du faîte vers le haut.
    d.line([(24 * s, 21 * s), (24 * s, 11 * s)], fill=255, width=3 * s)
    leaf(d, (24 * s, 13 * s), math.radians(-150), 13 * s, 4.5 * s, 255)
    leaf(d, (24 * s, 11 * s), math.radians(-35), 15 * s, 5 * s, 255)
    return mask


def trork_figure(scale):
    """Étape 7, camp trork : une tente pointue et deux défenses recourbées de part et d'autre."""
    s = scale
    mask = Image.new("L", (SIZE * s, SIZE * s), 0)
    d = ImageDraw.Draw(mask)
    d.polygon([(24 * s, 12 * s), (36 * s, 39 * s), (12 * s, 39 * s)], fill=255)
    d.polygon([(24 * s, 26 * s), (28 * s, 39 * s), (20 * s, 39 * s)], fill=0)  # entrée
    d.line([(24 * s, 12 * s), (24 * s, 6 * s)], fill=255, width=2 * s)
    for side in (-1, 1):
        cx = 24 + side * 16
        d.arc([(cx - 7) * s, 14 * s, (cx + 7) * s, 40 * s], 90 if side < 0 else -90 - 180, 270 if side < 0 else 90 - 180,
              fill=255, width=3 * s)
    return mask


def annex_figure(scale):
    """Avant-poste de métier : une cabane basse sous un fanion planté sur un mât."""
    s = scale
    mask = Image.new("L", (SIZE * s, SIZE * s), 0)
    d = ImageDraw.Draw(mask)
    d.polygon([(10 * s, 30 * s), (21 * s, 22 * s), (32 * s, 30 * s), (29 * s, 32 * s), (21 * s, 26 * s), (13 * s, 32 * s)], fill=255)
    d.rectangle([14 * s, 31 * s, 28 * s, 41 * s], fill=255)
    d.rectangle([19 * s, 34 * s, 23 * s, 41 * s], fill=0)  # porte
    d.line([(36 * s, 41 * s), (36 * s, 7 * s)], fill=255, width=3 * s)  # mât
    d.polygon([(37 * s, 7 * s), (46 * s, 11 * s), (37 * s, 16 * s)], fill=255)  # fanion
    return mask


def icon(fill, thickness, shape=figure):
    big = SIZE * SS
    mask = shape(SS)
    ring = mask.filter(ImageFilter.MaxFilter(2 * thickness * SS + 1))
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    img.paste(Image.new("RGBA", (big, big), (0, 0, 0, 255)), (0, 0), ring)
    img.paste(Image.new("RGBA", (big, big), fill), (0, 0), mask)
    return img.resize((SIZE, SIZE), Image.LANCZOS)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", type=Path, help="dossier où écrire un aperçu agrandi")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    marker = icon((232, 246, 214, 255), 2)
    compass = icon((176, 232, 132, 255), 3)
    marker.save(OUT / "Nakasar_Peuples_Kweebec.png")
    compass.save(OUT / "Nakasar_Peuples_KweebecCompass.png")
    icon((246, 222, 196, 255), 2, trork_figure).save(OUT / "Nakasar_Peuples_Trork.png")
    icon((232, 120, 84, 255), 3, trork_figure).save(OUT / "Nakasar_Peuples_TrorkCompass.png")
    icon((240, 228, 190, 255), 2, annex_figure).save(OUT / "Nakasar_Peuples_Annex.png")
    icon((226, 196, 106, 255), 3, annex_figure).save(OUT / "Nakasar_Peuples_AnnexCompass.png")
    print("icônes écrites dans", OUT.relative_to(ROOT))
    if args.preview:
        args.preview.mkdir(parents=True, exist_ok=True)
        sheet = Image.new("RGBA", (2 * 4 * SIZE + 30, 4 * SIZE + 20), (88, 108, 136, 255))
        sheet.alpha_composite(marker.resize((4 * SIZE, 4 * SIZE), Image.NEAREST), (10, 10))
        sheet.alpha_composite(compass.resize((4 * SIZE, 4 * SIZE), Image.NEAREST), (20 + 4 * SIZE, 10))
        sheet.save(args.preview / "icones_carte.png")


if __name__ == "__main__":
    main()
