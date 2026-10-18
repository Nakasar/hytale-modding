"""Génère les textures de particules du mod (runes, feu purificateur) (niveaux de gris, teintées par la couleur du spawner).

Usage : python3 tools/make_particle_textures.py  (depuis mods/nakasar-vampires)
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

OUT = Path(__file__).resolve().parent.parent / "src/main/resources/Common/Particles/Textures/Nakasar"


def ring(size, cx, cy, rx, ry, thickness):
    """Masque d'une ellipse creuse (maillon vu de face)."""
    y, x = np.mgrid[0:size, 0:size].astype(float)
    d = np.sqrt(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2)
    inner = 1 - thickness / min(rx, ry)
    return ((d <= 1.0) & (d >= inner)).astype(float)


def bar(size, cx, cy, half_w, half_h):
    """Masque d'un maillon vu de profil (barre arrondie)."""
    y, x = np.mgrid[0:size, 0:size].astype(float)
    dy = np.maximum(np.abs(y - cy) - (half_h - half_w), 0)
    return (np.sqrt((x - cx) ** 2 + dy ** 2) <= half_w).astype(float)


def spectral_chain(size=64):
    """Chaîne verticale : maillons de face et de profil alternés, avec un halo doux."""
    mask = np.zeros((size, size))
    step = 12
    for i, cy in enumerate(range(4, size + step, step)):
        if i % 2 == 0:
            mask = np.maximum(mask, ring(size, size / 2 - 0.5, cy, 6, 8, 2.6))
        else:
            mask = np.maximum(mask, bar(size, size / 2 - 0.5, cy, 1.8, 8))
    core = Image.fromarray((mask * 255).astype(np.uint8))
    halo = core.filter(ImageFilter.GaussianBlur(3))
    alpha = np.maximum(np.asarray(core, float), np.asarray(halo, float) * 0.8)
    # Brillance un peu plus forte au centre de la chaîne, bords légèrement plus sombres.
    lum = 170 + 85 * np.asarray(core, float) / 255
    return rgba(lum, alpha)


def soft_orb(size=32):
    """Orbe à bord doux (gouttelette de sang lumineuse)."""
    y, x = np.mgrid[0:size, 0:size].astype(float)
    c = (size - 1) / 2
    d = np.sqrt((x - c) ** 2 + (y - c) ** 2) / c
    alpha = np.clip(1 - d, 0, 1) ** 1.6 * 255
    lum = 200 + 55 * np.clip(1 - d * 1.5, 0, 1)
    return rgba(lum, alpha)


def rgba(lum, alpha):
    lum = np.clip(lum, 0, 255).astype(np.uint8)
    alpha = np.clip(alpha, 0, 255).astype(np.uint8)
    return Image.fromarray(np.dstack([lum, lum, lum, alpha]), "RGBA")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    spectral_chain().save(OUT / "Spectral_Chain.png")
    soft_orb().save(OUT / "Blood_Orb.png")
    soft_orb().save(OUT / "Purifying_Flame.png")  # teintée en blanc par Nakasar_Purifying_Flame.particlespawner
    print("textures écrites dans", OUT)
