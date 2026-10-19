#!/usr/bin/env python3
"""Génère les modèles animés du Codex vivant (mini-boss de la bibliothèque de la Tour de l'Alchimiste) et de ses
chapitres ouverts.

    python3 mods/nakasar-vampires/tools/generate_codex_models.py [--preview DOSSIER]

- Common/NPC/Nakasar/Living_Codex/ : grand grimoire de 1,7 bloc de haut qui flotte debout, couverture de cuir noir
  aux coins d'or. Un œil s'ouvre au centre de la couverture (blanc et iris ambré qui luisent, pupille fendue qui
  regarde autour d'elle), un fermoir doré (le trophée) tient la tranche, des runes violettes luisent sur le dos, deux
  chaînes brisées pendent dessous. La couverture (« Cover ») pivote sur le dos comme une porte, trois feuillets
  (« Page1 » à « Page3 ») battent par-dessus le bloc des pages.
- Common/NPC/Nakasar/Codex_Chapter_<sort>/ : petit livre ouvert qui flotte au-dessus d'un pupitre pendant que le Codex
  lit un chapitre ; ses pages et le glyphe qui tourne au-dessus luisent de la couleur du sort (feu, givre, livres).
- Animations : repos, blessure, mort, et pour le Codex « Pages » (nuée de pages) et « Chapter » (il ouvre un chapitre),
  jouées par ses interactions (Effects.ItemAnimationId) via Server/Item/Animations/Nakasar/Nakasar_Living_Codex.json.
  Les états de vol (Fly, FlyIdle…) rejouent le repos.
- Server/Models/Nakasar/Nakasar_Living_Codex.json et Nakasar_Codex_Chapter_<sort>.json : modèles (hitbox, lumière).

Même repère et même écriture que tools/generate_pumpkin_models.py (64 unités = 1 bloc, face avant vers +Z).
--preview DOSSIER écrit des rendus PNG (repos et images clés) pour vérifier les modèles.
"""
import json
import math
import sys
from pathlib import Path

from PIL import Image

import generate_pumpkin_models as gpm
from generate_pumpkin_models import Anim, Box, Joint, keys, mix, p_glow, p_round, shade, soft_noise, solid

LEATHER = (46, 36, 44)
LEATHER_DARK = (22, 16, 22)
LEATHER_LIGHT = (84, 66, 78)
GOLD = (214, 170, 66)
GOLD_DARK = (128, 92, 30)
GOLD_LIGHT = (255, 226, 130)
PAPER = (236, 222, 184)
PAPER_DARK = (186, 164, 120)
INK = (92, 70, 60)
EYE_WHITE = (255, 246, 214)
EYE_EDGE = (222, 170, 120)
IRIS = (255, 168, 30)
IRIS_DARK = (200, 70, 10)
PUPIL = (18, 8, 12)
RUNE = (200, 120, 255)
RUNE_DARK = (120, 50, 200)
IRON = (70, 72, 82)
IRON_DARK = (36, 38, 46)
IRON_LIGHT = (124, 128, 140)

# Couleur de chaque chapitre (pages, glyphe, lumière) : feu, givre, pluie de livres.
CHAPTERS = {
    "Fire": ((255, 196, 90), (255, 90, 20), "#ff6a1c"),
    "Frost": ((214, 244, 255), (90, 170, 255), "#6ab8ff"),
    "Rain": ((255, 240, 170), (214, 160, 50), "#ffd46a"),
}

W, H = 80, 104        # couverture : largeur, hauteur
COVER_T = 5           # épaisseur d'une couverture
PAGES_D = 17          # épaisseur du bloc des pages
FRONT_Z = PAGES_D / 2 + COVER_T / 2 + 0.5  # centre de la couverture avant
LEAF_Z = PAGES_D / 2 + 0.3
BOOK_Y = 96           # centre du livre au-dessus de l'origine (le PNJ vole au ras du sol)


# --- peintres -----------------------------------------------------------------------------------

def p_cover():
    """Cuir noir, plus clair au centre, filet doré en retrait du bord sur les grandes faces."""
    base = p_round(LEATHER, LEATHER_DARK, LEATHER_LIGHT, amp=0.06)

    def paint(rng, w, h, face):
        img = base(rng, w, h, face)
        if face in ("front", "back") and w > 20 and h > 20:
            px = img.load()
            for x in range(w):
                for y in range(h):
                    if (x in (4, w - 5) and 4 <= y <= h - 5) or (y in (4, h - 5) and 4 <= x <= w - 5):
                        px[x, y] = shade(GOLD_DARK, 1.1) + (255,)
        return img

    return paint


def p_pages():
    """Bloc de pages : les tranches sont rayées de feuillets, les faces portent deux colonnes d'écriture."""

    def paint(rng, w, h, face):
        n = soft_noise(rng, w, h, amp=0.05)
        if face in ("front", "back"):
            lines = {y for y in range(6, h - 6, 4)}

            def c(x, y):
                col = mix(PAPER, PAPER_DARK, abs((x + 0.5) / w - 0.5) * 0.5)
                col_a = 6 <= x <= w // 2 - 4
                col_b = w // 2 + 4 <= x <= w - 7
                if y in lines and (col_a or col_b) and rng.random() < 0.8:
                    col = mix(col, INK, 0.55)
                return shade(col, n[y][x])

            return solid(Image.new("RGBA", (w, h)), c)
        return solid(Image.new("RGBA", (w, h)),
                     lambda x, y: shade(mix(PAPER, PAPER_DARK, 0.45 if (x + y) % 2 and face in ("top", "bottom") else
                                            0.45 if x % 2 else 0.0), n[y][x]))

    return paint


def p_leaf(ink=True):
    """Feuillet volant : papier crème, quelques lignes d'écriture."""

    def paint(rng, w, h, face):
        n = soft_noise(rng, w, h, amp=0.05)

        def c(x, y):
            col = mix(PAPER, PAPER_DARK, ((x + 0.5) / w) * 0.3)
            if ink and face in ("front", "back") and 4 <= x <= w - 5 and y % 4 == 0 and 5 <= y <= h - 6:
                col = mix(col, INK, 0.5)
            return shade(col, n[y][x])

        return solid(Image.new("RGBA", (w, h)), c)

    return paint


def p_eye():
    """Blanc de l'œil en amande, plus chaud vers les coins, transparent hors de l'amande."""

    def paint(rng, w, h, face):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        px = img.load()
        for y in range(h):
            for x in range(w):
                u, v = (x + 0.5) / w * 2 - 1, (y + 0.5) / h * 2 - 1
                if face in ("front", "back") and abs(v) > (1 - u * u) ** 0.8:
                    continue
                px[x, y] = mix(EYE_WHITE, EYE_EDGE, abs(u) ** 2) + (255,)
        return img

    return paint


def p_iris():
    def paint(rng, w, h, face):
        cx, cy = (w - 1) / 2, (h - 1) / 2
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        px = img.load()
        for y in range(h):
            for x in range(w):
                r = math.hypot((x - cx) / max(1, cx), (y - cy) / max(1, cy))
                if face in ("front", "back") and r > 1.05:
                    continue
                px[x, y] = mix(IRIS, IRIS_DARK, r) + (255,)
        return img

    return paint


def flat(color):
    return lambda rng, w, h, face: solid(Image.new("RGBA", (w, h)), lambda x, y: color)


# --- Codex vivant -------------------------------------------------------------------------------

def chain(name, pos, links, rot=(0, 0, 0)):
    """Chaîne brisée : maillons alternés (à plat puis de chant), le dernier ouvert."""
    paint = p_round(IRON, IRON_DARK, IRON_LIGHT)
    child = None
    for i in range(links, 0, -1):
        parts = [Box(f"{name}{i}_Link", (0, -5, 0), (7, 11, 2.5) if i % 2 else (2.5, 11, 7), paint)]
        if i == links:
            parts.append(Box(f"{name}{i}_Broken", (2, -11, 0), (3, 4, 2.5), paint, rot=(0, 0, 30)))
        if child:
            parts.append(child)
        child = Joint(f"{name}{i}" if i > 1 else name, (0, -9, 0) if i > 1 else pos, parts, rot=rot if i == 1 else (0, 0, 0))
    return child


def codex_model():
    cover_paint = p_cover()
    gold = p_round(GOLD, GOLD_DARK, GOLD_LIGHT)
    spine_paint = p_round(LEATHER_DARK, (10, 6, 10), LEATHER)
    rune = p_glow((240, 200, 255), RUNE)
    corners = [(sx * (W / 2 - 5), sy * (H / 2 - 5)) for sx in (-1, 1) for sy in (-1, 1)]
    leaves = [Joint(f"Page{i}", (-W / 2 + 3, 0, LEAF_Z + 0.2 * i), [
        Box(f"Page{i}_Leaf", ((W - 8) / 2, 0, 0), (W - 8, H - 10, 0.6), p_leaf(), double=True),
    ]) for i in (1, 2, 3)]
    iris = Joint("Iris", (0, 0, 0.9), [
        Box("Iris_Disc", (0, 0, 0), (13, 13, 0.6), p_iris(), shading="fullbright"),
        Box("Pupil", (0, 0, 0.5), (3.5, 11, 0.6), flat(PUPIL)),
    ])
    eye = Joint("Eye", (W / 2, 8, COVER_T / 2 + 0.6), [
        Box("Eye_Socket", (0, 0, -0.4), (34, 22, 1), p_round(LEATHER_DARK, (8, 4, 8), LEATHER)),
        Box("Eye_White", (0, 0, 0.3), (30, 18, 0.6), p_eye(), shading="fullbright"),
        iris,
        Box("Lid_Top", (0, 11, 0.6), (32, 4, 2), cover_paint, rot=(0, 0, 0)),
        Box("Lid_Bottom", (0, -11, 0.6), (30, 3, 2), cover_paint),
    ])
    cover = Joint("Cover", (-W / 2, 0, FRONT_Z), [
        Box("Front_Cover", (W / 2, 0, 0), (W, H, COVER_T), cover_paint),
        *[Box(f"Front_Corner{k}", (W / 2 + x, y, 0.6), (12, 12, COVER_T + 1), gold) for k, (x, y) in enumerate(corners)],
        *[Box(f"Front_Rune{k}", (W / 2 + 21 * math.cos(math.radians(a)), 8 + 18 * math.sin(math.radians(a)), COVER_T / 2 + 0.3),
              (4, 4, 0.6), rune, shading="fullbright", rot=(0, 0, 45))
          for k, a in enumerate((-90, -30, 30, 150, 210))],
        Box("Front_Sigil", (W / 2, -30, COVER_T / 2 + 0.3), (18, 3, 0.6), gold),
        eye,
        Box("Clasp_Strap", (W + 1.5, -4, -FRONT_Z), (4, 18, 2 * FRONT_Z + COVER_T + 2), gold),
        Box("Clasp_Lock", (W + 4, -4, 0), (4, 10, 9), gold),
        Box("Clasp_Gem", (W + 6.3, -4, 0), (1, 4, 4), p_glow((255, 120, 160), (200, 30, 80)), shading="fullbright"),
    ])
    book = Joint("Book", (0, BOOK_Y, 0), [
        Box("Back_Cover", (0, 0, -FRONT_Z), (W, H, COVER_T), cover_paint),
        *[Box(f"Back_Corner{k}", (x, y, -FRONT_Z - 0.6), (12, 12, COVER_T + 1), gold) for k, (x, y) in enumerate(corners)],
        Box("Pages", (2, 0, 0), (W - 6, H - 6, PAGES_D), p_pages()),
        Box("Spine", (-W / 2 - 2, 0, 0), (6, H + 2, 2 * FRONT_Z + COVER_T), spine_paint),
        *[Box(f"Spine_Band{k}", (-W / 2 - 2.5, y, 0), (7, 4, 2 * FRONT_Z + COVER_T + 1), gold) for k, y in enumerate((-34, 0, 34))],
        *[Box(f"Spine_Rune{k}", (-W / 2 - 5.4, y, 0), (0.6, 9, 6), rune, shading="fullbright") for k, y in enumerate((-17, 17))],
        cover,
        *leaves,
        chain("Chain_L", (-W / 2 + 12, -H / 2, -4), 5, rot=(0, 0, 6)),
        chain("Chain_R", (W / 2 - 14, -H / 2, -6), 4, rot=(0, 0, -8)),
    ])
    return Joint("Body", (0, 0, 0), [book])


CODEX_JOINTS = ["Body", "Book", "Cover", "Page1", "Page2", "Page3", "Eye", "Iris", "Chain_L", "Chain_L2", "Chain_L3",
                "Chain_R", "Chain_R2", "Chain_R3"]


def codex_anims():
    def chains(t, amp=6):
        return {"Chain_L": ((0, 0, amp * math.sin(t * 2.2)), (0, 0, 0)),
                "Chain_L2": ((0, 0, amp * 0.8 * math.sin(t * 2.2 - 0.8)), (0, 0, 0)),
                "Chain_L3": ((0, 0, amp * 0.6 * math.sin(t * 2.2 - 1.6)), (0, 0, 0)),
                "Chain_R": ((amp * 0.5 * math.sin(t * 1.9 + 1), 0, amp * math.sin(t * 1.9 + 1)), (0, 0, 0)),
                "Chain_R2": ((0, 0, amp * 0.8 * math.sin(t * 1.9 + 0.2)), (0, 0, 0)),
                "Chain_R3": ((0, 0, amp * 0.6 * math.sin(t * 1.9 - 0.6)), (0, 0, 0))}

    def look(u):
        return {"Iris": ((0, 0, 0), (4 * math.sin(2 * math.pi * u), 2 * math.sin(4 * math.pi * u + 1), 0))}

    def idle(t):
        # Boucle de 3 s : il flotte, se balance, entrouvre sa couverture, un feuillet frémit, l'œil fouille la salle.
        u = t / 3.0
        s = math.sin(2 * math.pi * u)
        return {"Book": ((3 * s, 5 * math.sin(2 * math.pi * u + 1), 2 * math.sin(4 * math.pi * u)), (0, 5 * s, 0)),
                "Cover": ((0, -(7 + 5 * math.sin(4 * math.pi * u)), 0), (0, 0, 0)),
                "Page1": ((0, -(3 + 3 * math.sin(4 * math.pi * u + 0.5)), 0), (0, 0, 0)),
                **look(u), **chains(2 * math.pi * u * 2)}

    def hurt(t):
        k = keys(t, [(0, 0), (0.07, 1), (0.3, 0)])
        return {"Book": ((-10 * k, 0, 6 * k), (0, 0, -4 * k)), "Cover": ((0, -2, 0), (0, 0, 0)),
                "Iris": ((0, 0, 0), (0, 0, -0.5 * k)), **chains(t * 20, 8 * k)}

    def death(t):
        # Il bat de la couverture, perd ses pages et tombe à plat sur le sol.
        open_ = keys(t, [(0, 0), (0.3, 120), (0.7, 60), (1.1, 150), (1.6, 165)])
        fall = keys(t, [(0, 0), (0.6, 8), (1.4, -BOOK_Y + 8), (1.6, -BOOK_Y + 6)])
        tip = keys(t, [(0, 0), (0.6, 10), (1.4, -88), (1.6, -90)])
        return {"Book": ((tip, keys(t, [(0, 0), (1.6, 40)]), keys(t, [(0, 0), (0.8, 18), (1.6, 6)])), (0, fall, 0)),
                "Cover": ((0, -open_, 0), (0, 0, 0)),
                **{f"Page{i}": ((0, -keys(t, [(0, 0), (0.3 + 0.2 * i, 0), (0.6 + 0.25 * i, 160)]), 0), (0, 0, 0)) for i in (1, 2, 3)},
                **chains(t * 8, 14)}

    def pages(t):
        # Nuée de pages : 1,1 s d'armement (il recule, s'ouvre en grand, les feuillets s'affolent), puis il se jette en
        # avant et les pages partent (1,1 à 1,3 s), avant de se refermer.
        open_ = keys(t, [(0, 7), (0.5, 95), (1.05, 105), (1.15, 125), (1.6, 7)])
        back = keys(t, [(0, 0), (0.9, -12), (1.05, -12), (1.15, 18), (1.6, 0)])
        flutter = lambda i: 30 + 25 * math.sin(t * (30 + 6 * i)) * keys(t, [(0, 0), (0.6, 1), (1.05, 1), (1.1, 0)])
        burst = lambda i: keys(t, [(0, 0), (1.06 + 0.04 * i, 0), (1.18 + 0.04 * i, 170), (1.45, 170), (1.6, 0)])
        return {"Book": ((back * 0.6, 0, math.sin(t * 40) * keys(t, [(0, 0), (1.0, 3), (1.05, 0)])), (0, 0, back * 0.8)),
                "Cover": ((0, -open_, 0), (0, 0, 0)),
                **{f"Page{i}": ((0, -min(165, flutter(i) * keys(t, [(0, 0), (0.4, 1), (1.6, 0)]) + burst(i)), 0), (0, 0, 0))
                   for i in (1, 2, 3)},
                "Iris": ((0, 0, 0), (0, 0, 0)), **chains(t * 6, 10)}

    def chapter(t):
        # Il ouvre un chapitre : il s'élève, s'ouvre tout grand et tourne ses pages une à une, l'œil fixe.
        rise = keys(t, [(0, 0), (0.5, 14), (1.3, 16), (1.6, 0)])
        open_ = keys(t, [(0, 7), (0.45, 160), (1.3, 160), (1.6, 7)])
        return {"Book": ((keys(t, [(0, 0), (0.5, -8), (1.3, -8), (1.6, 0)]), 0, 0), (0, rise, 0)),
                "Cover": ((0, -open_, 0), (0, 0, 0)),
                **{f"Page{i}": ((0, -keys(t, [(0, 0), (0.35 + 0.25 * i, 0), (0.55 + 0.25 * i, 155), (1.3, 155), (1.6, 0)]), 0),
                                (0, 0, 0)) for i in (1, 2, 3)},
                "Iris": ((0, 0, 0), (0, 0, 0)), **chains(t * 5, 6)}

    return [
        Anim("Idle", 3.0, idle, step=6, loop=True),
        Anim("Hurt", 0.3, hurt, step=3),
        Anim("Death", 1.6, death, step=4, hold=True),
        Anim("Pages", 1.6, pages, step=2),
        Anim("Chapter", 1.6, chapter, step=3),
    ]


# --- chapitre ouvert ----------------------------------------------------------------------------

def chapter_model(spell):
    light, deep, _ = CHAPTERS[spell]
    cover = p_round(LEATHER, LEATHER_DARK, LEATHER_LIGHT)
    glow_pages = p_glow(mix(PAPER, light, 0.5), mix(PAPER, deep, 0.35))
    glyph = p_glow((255, 255, 255), deep)
    halves = [Joint(f"Half_{side}", (0, 0, 0), [
        Box(f"Half_{side}_Cover", (sign * 12, 0, 0), (24, 2, 30), cover),
        Box(f"Half_{side}_Pages", (sign * 11.5, 2, 0), (22, 2.5, 27), glow_pages, shading="fullbright"),
    ], rot=(0, 0, sign * 12)) for side, sign in (("L", -1), ("R", 1))]
    leaf = Joint("Leaf", (0, 3.6, 0), [Box("Leaf_Box", (10.5, 0, 0), (21, 0.5, 26), p_leaf(False), double=True,
                                           shading="fullbright")])
    spin = Joint("Glyph", (0, 26, 0), [
        Box("Glyph_Ring", (0, 0, 0), (12, 12, 0.8), glyph, shading="fullbright", rot=(0, 0, 45)),
        Box("Glyph_Core", (0, 0, 0), (5, 5, 1.2), glyph, shading="fullbright"),
    ])
    book = Joint("Book", (0, 16, 0), halves + [leaf, spin], rot=(-28, 0, 0))
    return Joint("Body", (0, 0, 0), [book])


CHAPTER_JOINTS = ["Body", "Book", "Leaf", "Glyph"]


def chapter_anims():
    def idle(t):
        u = t / 2.0
        return {"Book": ((0, 0, 0), (0, 2.5 * math.sin(2 * math.pi * u), 0)),
                "Leaf": ((0, 0, keys(u % 1.0, [(0, 0), (0.35, 0), (0.6, 170), (1, 170)])), (0, 0, 0)),
                "Glyph": ((0, 360 * u, 0), (0, 2 * math.sin(4 * math.pi * u), 0))}

    def hurt(t):
        k = keys(t, [(0, 0), (0.06, 1), (0.25, 0)])
        return {"Book": ((-12 * k, 0, 8 * k), (0, 0, 0))}

    def death(t):
        k = keys(t, [(0, 0), (0.5, 1)])
        return {"Book": ((-28 * k, 0, 70 * k), (0, -14 * k, 0)), "Glyph": ((0, 0, 0), (0, -30 * k, 0))}

    return [
        Anim("Idle", 2.0, idle, step=4, loop=True),
        Anim("Hurt", 0.25, hurt, step=3),
        Anim("Death", 0.5, death, step=3, hold=True),
    ]


# --- écriture -----------------------------------------------------------------------------------

FLIGHT = ("Fly", "FlyBackward", "FlyFast", "FlyIdle")


def add_flight(key):
    """Le Codex et ses chapitres volent : les états de vol rejouent le repos, la blessure et la mort en vol aussi."""
    path = gpm.SERVER / "Models" / "Nakasar" / f"Nakasar_{key}.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    base = f"NPC/Nakasar/{key}/Animations"
    sets = doc["AnimationSets"]
    for state in FLIGHT:
        sets.setdefault(state, gpm.anim_entry(f"{base}/Idle.blockyanim"))
    sets.setdefault("HurtFly", gpm.anim_entry(f"{base}/Hurt.blockyanim", Looping=False))
    sets.setdefault("DeathFly", gpm.anim_entry(f"{base}/Death.blockyanim", Looping=False))
    gpm.write_json(path, doc)


def main():
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    view = {"size": 320, "scale": 2.2, "center": (0, BOOK_Y, 0)}
    gpm.build("Living_Codex", codex_model(), CODEX_JOINTS, codex_anims(), 51, 512, {
        "$Comment": "Codex vivant (mini-boss de la bibliothèque de la Tour de l'Alchimiste), généré par tools/generate_codex_models.py : grand grimoire de cuir noir qui flotte debout, œil luisant sur la couverture, fermoir doré, runes sur le dos, chaînes brisées. La couverture s'ouvre comme une porte et les feuillets battent.",
        "EyeHeight": 1.5,
        "HitBox": {"Max": {"X": 0.75, "Y": 2.4, "Z": 0.45}, "Min": {"X": -0.75, "Y": 0.6, "Z": -0.45}},
        "MinScale": 1,
        "MaxScale": 1,
        "Light": {"Color": "#c47aff", "Radius": 7},
    }, ["Pages", "Chapter"], preview, [
        ("repos", None, 0, view),
        ("face", None, 0, dict(view, yaw=0, pitch=5)),
        ("idle", "Idle", 1.0, view),
        ("pages", "Pages", 1.12, dict(view, yaw=50)),
        ("chapitre", "Chapter", 1.0, dict(view, yaw=20)),
        ("mort", "Death", 1.6, dict(view, center=(0, 40, 0))),
    ])
    add_flight("Living_Codex")
    for spell, (_, _, color) in CHAPTERS.items():
        key = f"Codex_Chapter_{spell}"
        gpm.build(key, chapter_model(spell), CHAPTER_JOINTS, chapter_anims(), 53, 128, {
            "$Comment": f"Chapitre ouvert du Codex vivant ({spell}), généré par tools/generate_codex_models.py : petit livre ouvert qui flotte au-dessus d'un pupitre, pages et glyphe lumineux de la couleur du sort.",
            "EyeHeight": 0.5,
            "HitBox": {"Max": {"X": 0.45, "Y": 0.9, "Z": 0.45}, "Min": {"X": -0.45, "Y": 0, "Z": -0.45}},
            "MinScale": 1,
            "MaxScale": 1,
            "Light": {"Color": color, "Radius": 6},
        }, [], preview, [
            ("repos", None, 0, {"size": 240, "scale": 4.0, "center": (0, 20, 0), "pitch": 30}),
            ("idle", "Idle", 1.0, {"size": 240, "scale": 4.0, "center": (0, 20, 0), "pitch": 30}),
        ])
        add_flight(key)


if __name__ == "__main__":
    main()
