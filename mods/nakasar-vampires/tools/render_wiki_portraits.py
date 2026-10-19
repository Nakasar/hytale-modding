#!/usr/bin/env python3
"""Rend les portraits des PNJ dont le modèle 3D est généré par le dépôt, pour le wiki joueur.

    python3 mods/nakasar-vampires/tools/render_wiki_portraits.py

Écrit docs/wiki/images/pnj/Nakasar_Giant_Pumpkin.png, Nakasar_Pumpkin_Vine.png et Nakasar_Enchanted_Gear.png :
vue de 3/4 au repos et une seconde pose, côte à côte. Les modèles sont reconstruits par
generate_pumpkin_models.py et generate_gear_model.py (mêmes graines, donc mêmes textures que les fichiers du pack) sans réécrire le pack.

Les autres PNJ héritent de modèles vanilla (Player, Zombie, Skeleton...) absents du dépôt : leurs
portraits sont des captures en jeu.
"""
from pathlib import Path

from PIL import Image

import generate_gear_model as ggm
import generate_pumpkin_models as gpm

OUT = Path(__file__).resolve().parents[3] / "docs" / "wiki" / "images" / "pnj"
BACKGROUND = (28, 22, 34, 255)


def portrait(root, anims, seed, tex_w, shots):
    atlas, uv = gpm.build_atlas(root, seed, tex_w)
    by_name = {a.name: a for a in anims}
    tiles = []
    for name, t, view in shots:
        pose = by_name[name].pose(t) if name else {}
        tile = gpm.render(root, atlas, uv, pose, **view)
        # Fond du rendu remplacé par une teinte nuit, plus lisible sur le wiki.
        px = tile.load()
        for y in range(tile.height):
            for x in range(tile.width):
                if px[x, y] == (40, 44, 52, 255):
                    px[x, y] = BACKGROUND
        tiles.append(tile)
    sheet = Image.new("RGBA", (sum(t.width for t in tiles), tiles[0].height), BACKGROUND)
    x = 0
    for tile in tiles:
        sheet.paste(tile, (x, 0))
        x += tile.width
    return sheet


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    view = {"size": 420, "scale": 1.75, "center": (0, 62, 0)}
    portrait(gpm.pumpkin_model(), gpm.pumpkin_anims(), 41, 256, [
        (None, 0, view),
        ("Spit", 1.08, dict(view, yaw=0, pitch=5, scale=1.5)),
    ]).save(OUT / "Nakasar_Giant_Pumpkin.png")
    view = {"size": 420, "scale": 1.75, "center": (0, 88, 0)}
    portrait(gpm.vine_model(), gpm.vine_anims(), 43, 128, [
        (None, 0, view),
        ("Strike", 0.38, dict(view, yaw=90, pitch=5)),
    ]).save(OUT / "Nakasar_Pumpkin_Vine.png")
    view = {"size": 420, "scale": 3.0, "center": (0, ggm.HUB_Y, 0)}
    portrait(ggm.gear_model(), ggm.gear_anims(), 57, 256, [
        ("Idle", 0.5, view),
        ("Idle", 1.0, dict(view, yaw=70, pitch=10)),
    ]).save(OUT / "Nakasar_Enchanted_Gear.png")
    print(f"Portraits écrits dans {OUT}")


if __name__ == "__main__":
    main()
