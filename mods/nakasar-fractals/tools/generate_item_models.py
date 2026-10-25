"""Modèles 3D des objets en main du mod Fractales, dans le style des blocs en modèle (fractal_blocks.py).

`fractal_models.write_item_model` passe ici pour tout nom de modèle listé dans ITEMS : les générateurs gardent leurs
appels (mêmes noms de fichiers .blockymodel / .png et d'icônes), seule la forme change. Repère : 1 texel par unité,
origine au centre du bas de l'objet.

    python generate_item_models.py --preview DOSSIER   # planche d'aperçu des objets (n'écrit rien dans le pack)
"""
import json
import math
import sys
import zlib
from pathlib import Path

from PIL import Image

import fractal_blocks as fb

MIST = (186, 140, 255)
BRASS = (204, 158, 76)
GOLD = (232, 190, 96)
COPPER = (190, 112, 70)
SILVER = (200, 206, 218)
IRON = (86, 88, 98)
WOOD = (96, 62, 44)
WOOD_DARK = (70, 44, 34)
FIRE_DARK, FIRE_LIGHT = (250, 120, 30), (255, 236, 150)

CORE_COLORS = {"Cliffside": (186, 140, 255), "Uncategorized": (110, 210, 255), "Volcanic": (255, 140, 60),
               "SolidOcean": (90, 220, 160), "Swampland": (160, 230, 90), "Snowblind": (205, 235, 255)}
RANK_METALS = {"Initiate": (COPPER, False), "Adept": (SILVER, False), "Expert": (GOLD, False), "Master": (MIST, True)}


def part(name, center, size, paint, **kw):
    return dict(name=name, center=center, size=size, paint=paint, **kw)


def glow(color):
    return fb.crystal(fb.shade(color, 0.55), fb.mix(color, (255, 255, 255), 0.6))


def metal_or_glow(color, lit):
    return glow(color) if lit else fb.metal(color, False)


# ---------------------------------------------------------------- objets

def mist_shard():
    """Éclat de Brume : grappe de trois pointes violettes sur une base givrée."""
    c = glow(MIST)
    return [part("Base", (0, 0.75, 0), (6, 1.5, 5), fb.smooth_stone((200, 196, 230), rim=False)),
            part("Spike", (0, 5.5, 0), (3.5, 9, 3.5), c, glow=True, rot=(0, 45, 6)),
            part("Spike_B", (2.4, 3.8, 0.8), (2.5, 6, 2.5), c, glow=True, rot=(0, 20, -26)),
            part("Spike_C", (-2.2, 3.2, -0.6), (2, 4.5, 2), c, glow=True, rot=(0, 60, 30))]


def core(color):
    """Noyau de fractale : sphère de cristal (deux boîtes croisées) dans une monture de laiton à quatre griffes."""
    p = [part("Mount", (0, 1, 0), (7, 2, 7), fb.metal(BRASS, False)),
         part("Mount_Rim", (0, 2.5, 0), (8, 1, 8), fb.metal(GOLD, False), rot=(0, 45, 0)),
         part("Orb", (0, 7, 0), (6, 6.5, 6), glow(color), glow=True),
         part("Orb_X", (0, 7, 0), (7, 5, 5), glow(color), glow=True),
         part("Orb_Z", (0, 7, 0), (5, 5, 7), glow(color), glow=True),
         part("Heart", (0, 7, 3.6), (2, 2, 0.5), glow((255, 255, 255)), glow=True)]
    for k, (x, z) in enumerate(((3, 3), (-3, 3), (3, -3), (-3, -3))):
        p.append(part(f"Claw_{k + 1}", (x * 1.05, 5, z * 1.05), (1.2, 5, 1.2), fb.metal(GOLD, False),
                      rot=(-z * 4, 0, x * 4)))
    return p


def level_fork(rank):
    """Diapason : manche gainé, pommeau, deux branches ; cuivre, argent, or ou cristal selon le rang."""
    color, lit = RANK_METALS[rank]
    m = metal_or_glow(color, lit)
    return [part("Pommel", (0, 1, 0), (3, 2, 3), glow((120, 190, 255)) if not lit else glow((255, 255, 255)),
                 glow=True, rot=(0, 45, 0)),
            part("Grip", (0, 4.5, 0), (2.2, 5, 2.2), fb.cloth((70, 50, 90), (200, 170, 90))),
            part("Neck", (0, 7.5, 0), (1.8, 1.5, 1.8), m, glow=lit),
            part("Bow", (0, 8.9, 0), (7, 1.5, 1.8), m, glow=lit),
            part("Prong_W", (-2.75, 13.4, 0), (1.5, 8, 1.5), m, glow=lit),
            part("Prong_E", (2.75, 13.4, 0), (1.5, 8, 1.5), m, glow=lit),
            part("Note", (0, 14, 0), (1.8, 1.8, 1.8), glow(MIST), glow=True, rot=(45, 45, 0))]


def infusion(n):
    """Infusion +n : fiole bouchée ; le liquide fonce du bleu au violet puis à l'or, la fiole grandit par palier de 3."""
    tier = (n - 1) // 3
    t = (n - 1) / 14
    liquid = fb.mix((110, 170, 255), (190, 110, 255), min(1, t * 1.6)) if t < 0.62 else \
        fb.mix((190, 110, 255), (255, 210, 110), (t - 0.62) / 0.38)
    w = 4 + tier * 0.5
    h = 5 + tier
    p = [part("Glass", (0, h / 2 + 0.5, 0), (w + 1, h, w + 1), fb.glass((200, 220, 240), 90)),
         part("Liquid", (0, (h - 1) / 2 + 0.5, 0), (w, h - 1, w), fb.crystal(fb.shade(liquid, 0.7), fb.mix(liquid, (255, 255, 255), 0.2)), glow=True),
         part("Neck", (0, h + 1.25, 0), (2.2, 1.5, 2.2), fb.glass((200, 220, 240), 120)),
         part("Cork", (0, h + 2.5, 0), (2.6, 1.6, 2.6), fb.planks((170, 120, 76), 2, rim=False))]
    if tier >= 2:
        p.append(part("Collar", (0, h + 0.5, 0), (w + 1.5, 1, w + 1.5), fb.metal(BRASS if tier < 4 else GOLD, False)))
    if tier >= 3:
        p.append(part("Foot", (0, 0.5, 0), (w + 2, 1, w + 2), fb.metal(GOLD, False), rot=(0, 45, 0)))
    if tier >= 4:
        p.append(part("Gem", (0, h / 2 + 0.5, (w + 1) / 2 + 0.3), (1.6, 1.6, 0.6), glow((255, 255, 255)), glow=True))
    return p


def coffer(band, lit=False, sun=False):
    """Coffret de récompense : bois sombre, ferrures du rang, serrure lumineuse (soleil doré pour celui du jour)."""
    wood = fb.planks(WOOD_DARK, 3, vertical=False)
    b = metal_or_glow(band, lit)
    p = [part("Box", (0, 3.5, 0), (11, 6, 8), wood),
         part("Lid", (0, 8, 0), (11, 3, 8), wood),
         part("Band_L", (-3.5, 5, 0), (1.2, 9.4, 8.4), b, glow=lit),
         part("Band_R", (3.5, 5, 0), (1.2, 9.4, 8.4), b, glow=lit),
         part("Foot", (0, 0.4, 0), (12, 0.8, 9), fb.metal(BRASS, False)),
         part("Lock", (0, 6, 4.25), (2.5, 3, 0.6), glow((255, 220, 110)) if sun else glow(MIST), glow=True)]
    if sun:
        p.append(part("Sun", (0, 9.75, 0), (5, 0.5, 5), fb.glyph((255, 220, 110), "ring", ("top",)), glow=True))
    return p


def mist_tear():
    """Larme de Brume : goutte de cristal cyan dans une cage de fil de cuivre."""
    c = glow((120, 210, 255))
    p = [part("Drop", (0, 4.5, 0), (4, 5, 4), c, glow=True, rot=(0, 45, 0)),
         part("Drop_Tip", (0, 8, 0), (2, 2.5, 2), c, glow=True, rot=(0, 45, 0)),
         part("Ring_Top", (0, 9.6, 0), (3, 0.8, 3), fb.metal(COPPER, False)),
         part("Ring_Bottom", (0, 1, 0), (5, 1, 5), fb.metal(COPPER, False))]
    for k, (x, z) in enumerate(((2.6, 0), (-2.6, 0), (0, 2.6), (0, -2.6))):
        p.append(part(f"Wire_{k + 1}", (x, 5, z), (0.6, 8, 0.6), fb.metal(COPPER, False),
                      rot=(-z * 4, 0, x * 4)))
    return p


def imbued_stone():
    """Pierre imprégnée : caillou de basalte fissuré, lave orange dans les fissures."""
    rock = fb.smooth_stone((92, 82, 86))
    lava = glow((255, 130, 40))
    return [part("Rock", (0, 3, 0), (7, 6, 6), rock, rot=(0, 15, 0)),
            part("Rock_B", (1.5, 5.5, 0.5), (4.5, 3, 4.5), rock, rot=(10, 40, 0)),
            part("Crack_A", (0, 3.2, 3.15), (5.5, 1.2, 0.6), lava, glow=True, rot=(0, 15, 20)),
            part("Crack_B", (2.5, 2.4, 2.2), (1.2, 4, 0.6), lava, glow=True, rot=(0, 15, -15)),
            part("Crack_Top", (-0.5, 6.05, 0), (4.5, 0.6, 1.2), lava, glow=True, rot=(0, 35, 0))]


def wisp():
    """Feu-follet en lanterne : socle et chapeau de laiton, vitres, flamme verte."""
    flame = glow((150, 255, 210))
    return [part("Base", (0, 0.75, 0), (7, 1.5, 7), fb.metal(BRASS, False)),
            part("Cap", (0, 9.25, 0), (7, 1.5, 7), fb.metal(BRASS, False)),
            part("Roof", (0, 10.5, 0), (4, 1, 4), fb.metal(GOLD, False)),
            part("Handle", (0, 12, 0), (1, 2.2, 4), fb.metal(BRASS, False)),
            part("Glass", (0, 5, 0), (6, 7, 6), fb.glass((200, 255, 230), 90)),
            part("Flame", (0, 4.5, 0), (3, 4.5, 3), flame, glow=True, rot=(0, 45, 0)),
            part("Flame_Tip", (0, 7, 0), (1.5, 2, 1.5), glow((240, 255, 250)), glow=True, rot=(0, 45, 0))]


def frost_torch():
    """Torche épaisse : manche de bois, tête enveloppée de tissu, flamme vive."""
    return [part("Handle", (0, 7, 0), (2.5, 14, 2.5), fb.planks((120, 84, 50), 2)),
            part("Wrap", (0, 14.5, 0), (3.6, 4, 3.6), fb.cloth((150, 120, 80), (110, 80, 50))),
            part("Head", (0, 17, 0), (3, 1.5, 3), fb.smooth_stone((40, 32, 30), rim=False)),
            part("Flame", (0, 19.5, 0), (3.5, 4.5, 3.5), fb.crystal(FIRE_DARK, FIRE_LIGHT), glow=True,
                 rot=(0, 45, 0)),
            part("Flame_Tip", (0, 22.5, 0), (1.8, 2.5, 1.8), fb.crystal((255, 190, 70), (255, 250, 210)), glow=True,
                 rot=(0, 20, 0))]


def firewood():
    """Fagot : trois bûches liées par deux tours de corde."""
    log = fb.log((84, 60, 44))
    return [part("Log_1", (-1.8, 1.6, 0), (3.2, 3.2, 12), log),
            part("Log_2", (1.8, 1.6, 0), (3.2, 3.2, 12), log),
            part("Log_3", (0, 4.4, 0), (3.2, 3.2, 12), log, rot=(0, 0, 0)),
            part("Rope_A", (0, 3, 3), (7.6, 6.4, 1), fb.solid((170, 140, 96))),
            part("Rope_B", (0, 3, -3), (7.6, 6.4, 1), fb.solid((170, 140, 96)))]


ITEMS = {
    "Mist_Shard": mist_shard,
    "Mist_Tear": mist_tear,
    "Imbued_Stone": imbued_stone,
    "Wisp": wisp,
    "Frost_Torch": frost_torch,
    "Firewood": firewood,
    "Daily_Bag": lambda: coffer(GOLD, sun=True),
}
ITEMS.update({f"Core_{fid}": (lambda c: lambda: core(c))(color) for fid, color in CORE_COLORS.items()})
ITEMS.update({f"Level_Fork_{rank}": (lambda r: lambda: level_fork(r))(rank) for rank in RANK_METALS})
ITEMS.update({f"Infusion_{n:02d}": (lambda k: lambda: infusion(k))(n) for n in range(1, 16)})
ITEMS.update({f"Reward_Bag_{rank}": (lambda c, l: lambda: coffer(c, l))(color, lit)
              for rank, (color, lit) in RANK_METALS.items()})


def render(parts, atlas, uv, size, bg=None):
    return fb.render(parts, atlas, uv, size, yaw=-35, pitch=24, bg=bg)


def prop_model(name, nodes):
    """Même enveloppe que fm.build_model : format prop, nœud racine vide au nom du modèle, ids renumérotés."""
    root = {"id": "1", "name": name, "position": {"x": 0, "y": 0, "z": 0},
            "orientation": {"x": 0, "y": 0, "z": 0, "w": 1},
            "shape": {"type": "none", "offset": {"x": 0, "y": 0, "z": 0}, "stretch": {"x": 1, "y": 1, "z": 1},
                      "settings": {"isPiece": False}, "textureLayout": {}, "unwrapMode": "custom", "visible": True,
                      "doubleSided": False, "shadingMode": "flat"},
            "children": nodes}
    count = 0

    def renumber(node):
        nonlocal count
        count += 1
        node["id"] = str(count)
        for child in node.get("children", []):
            renumber(child)
    renumber(root)
    return {"format": "prop", "lod": "auto", "nodes": [root]}


def write(name, model_dir, icon_dir):
    """Écrit <name>.blockymodel, l'atlas <name>.png et l'icône 64×64 ; rend l'icône (comme fm.write_item_model)."""
    parts = ITEMS[name]()
    atlas, uv = fb.build_atlas(parts, zlib.crc32(name.encode()))
    model = prop_model(name, fb.build_model(parts, uv)["nodes"])
    model_dir.mkdir(parents=True, exist_ok=True)
    icon_dir.mkdir(parents=True, exist_ok=True)
    atlas.save(model_dir / f"{name}.png")
    (model_dir / f"{name}.blockymodel").write_text(json.dumps(model, indent=2) + "\n")
    small = render(parts, atlas, uv, 256).resize((64, 64), Image.LANCZOS)
    small.save(icon_dir / f"{name}.png")
    return small


def main():
    out = Path(sys.argv[sys.argv.index("--preview") + 1])
    out.mkdir(parents=True, exist_ok=True)
    names = list(ITEMS)
    per_row = 8
    w = 192
    rows = math.ceil(len(names) / per_row)
    sheet = Image.new("RGBA", (w * per_row, w * rows), (36, 38, 52, 255))
    for k, name in enumerate(names):
        parts = ITEMS[name]()
        atlas, uv = fb.build_atlas(parts, zlib.crc32(name.encode()))
        sheet.alpha_composite(render(parts, atlas, uv, w), (w * (k % per_row), w * (k // per_row)))
    sheet.save(out / "objets_3d.png")
    print(f"{len(names)} modèles d'objets")


if __name__ == "__main__":
    main()
