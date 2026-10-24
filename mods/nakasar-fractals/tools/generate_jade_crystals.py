#!/usr/bin/env python3
"""Textures des cristaux de jade de l'Océan solide : celles des cristaux du Néant vanilla (bloc et fragments
Rock_Crystal_Void_*), passées du violet au vert jade (Kevin, 24 octobre 2026). Formes et modèles restent ceux du jeu ;
les blocs Nakasar_Fractal_Jade_Crystal_* sont écrits par generate_solid_ocean.py.

Les textures du jeu ne sont pas dans le dépôt : on les lit dans Assets.zip (dossier du jeu,
%APPDATA%\\Hytale\\install\\release\\package\\game\\latest\\Assets.zip). Les PNG écrits, eux, sont versionnés.

Usage : python3 mods/nakasar-fractals/tools/generate_jade_crystals.py CHEMIN/Assets.zip"""

import colorsys
import io
import sys
import zipfile

from PIL import Image

import fractal_common as fc
import generate_observatory as go

SIZES = ("Block", "Large", "Medium", "Small")
BLOCK_TEXTURE = f"{go.TEXTURES}/Jade_Crystal.png"
MODEL_TEXTURE = "Blocks/Nakasar/Fractals/Jade_Crystal_Big.png"
# cible (sous Common/) : texture vanilla (sous Common/)
SOURCES = {
    BLOCK_TEXTURE: "BlockTextures/Rock_Crystal_Void.png",
    MODEL_TEXTURE: "Resources/Crystals/Crystal_Big_Textures/Void.png",
    **{f"{go.ICONS}/Jade_Crystal_{s}.png": f"Icons/ItemsGenerated/Rock_Crystal_Void_{s}.png" for s in SIZES},
}
HUE = 152 / 360        # vert jade
LIFT = 1.3             # le Néant est sombre : le jade un peu plus clair
SATURATION = 1.1


def jade(image):
    image = image.convert("RGBA")
    out = []
    for r, g, b, a in image.getdata():
        _, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        r2, g2, b2 = colorsys.hsv_to_rgb(HUE, min(1.0, s * SATURATION), min(1.0, v * LIFT))
        out.append((round(r2 * 255), round(g2 * 255), round(b2 * 255), a))
    result = Image.new("RGBA", image.size)
    result.putdata(out)
    return result


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    with zipfile.ZipFile(sys.argv[1]) as assets:
        for target, source in SOURCES.items():
            path = fc.COMMON / target
            path.parent.mkdir(parents=True, exist_ok=True)
            jade(Image.open(io.BytesIO(assets.read("Common/" + source)))).save(path)
            print(path)


if __name__ == "__main__":
    main()
