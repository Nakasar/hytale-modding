"""Matières peintes « façon Hytale » pour nos modèles en boîtes (Kevin, 25 octobre 2026 : style plus Hytale).

Les peintres de fractal_blocks et fractal_models tirent leur texture d'un échantillon de bloc vanilla (planches, pierre
taillée, bronze, toile…) recoloré vers la teinte voulue : le dessin peint à la main du jeu (veinage, joints, rivets,
éclats) est gardé, seule la couleur change. Les échantillons (32 × 32, 1 texel par unité comme les blocs vanilla) sont
versionnés dans tools/materials/ et extraits d'Assets.zip par generate_vanilla_recolors.py.
"""
from pathlib import Path

from PIL import Image

DIR = Path(__file__).resolve().parent / "materials"
# clé -> texture de bloc vanilla (BlockTextures/<nom>.png)
SWATCHES = {
    "planks": "Wood_Hardwood_Planks",
    "planks_dark": "Wood_Darkwood_Planks",
    "bark": "Wood_Trunk_Oak_Side",
    "brick": "Rock_Stone_Brick",
    "smooth": "Rock_Stone_Brick_Smooth",
    "rock": "Rock_Stone",
    "metal": "Metal_Bronze_Smooth",
    "metal_cold": "Metal_Iron_Smooth",
    "cloth": "Cloth_White",
}
_cache = {}


def _lum(p):
    return 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]


def _swatch(key):
    if key not in _cache:
        img = Image.open(DIR / f"{key}.png").convert("RGBA")
        px = img.load()
        lum = [[_lum(px[x, y]) for x in range(img.width)] for y in range(img.height)]
        mean = sum(map(sum, lum)) / (img.width * img.height)
        _cache[key] = (img.width, img.height, [[v / mean for v in row] for row in lum])
    return _cache[key]


def factors(key, rng, w, h, rotate=False, aligned=False, contrast=1.0):
    """Facteurs de luminosité (1 = moyenne) de l'échantillon `key` sur une face w × h, en mosaïque.
    `rotate` : quart de tour (planches verticales) ; `aligned` : sans décalage (cadres, rivets aux coins)."""
    sw, sh, lum = _swatch(key)
    ox, oy = (0, 0) if aligned else (rng.randrange(sw), rng.randrange(sh))
    out = []
    for y in range(h):
        row = []
        for x in range(w):
            u, v = (y, x) if rotate else (x, y)
            f = lum[(v + oy) % sh][(u + ox) % sw]
            row.append(1 + (f - 1) * contrast)
        out.append(row)
    return out
