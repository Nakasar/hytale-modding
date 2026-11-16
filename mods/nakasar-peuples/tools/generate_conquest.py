#!/usr/bin/env python3
"""Génère les assets de la conquête des lieux-dits (GDD « Villages et lieux-dits : allégeance et conquête », Kevin,
16 novembre 2026 ; Java world/Allegiance, Heraldry, Banners, Garrisons, Sieges, Territories, DomainPage).

Sorties :
    Server/Item/Items/Nakasar/Peuples/Standards/Nakasar_Peuples_Standard_<Couleur>_<Emblème>.json   128 bannières
    Server/Item/Items/Nakasar/Peuples/Standards/Nakasar_Peuples_Pennant_<Couleur>.json               8 fanions
    Server/Item/Items/Nakasar/Peuples/Standards/Nakasar_Peuples_Standard_Blank.json                  bannière vierge
        (fabriquée au métier à tisser vanilla : 2 rouleaux de coton et un bâton)
    Common/Blocks/Nakasar/Peuples/Standards/*.png   textures (UV des modèles vanilla, voir plus bas)
    Common/Icons/Nakasar/Peuples/Standards/*.png    icônes 64 × 64
    bloc « Conquête » des deux fichiers .lang (remplacé sur place, ou ajouté en tête la première fois)

Modèles et animations vanilla (règle n° 2) : la bannière est celle des ruines humaines
(Blocks/Decorative_Sets/Human_Ruins/Banner.blockymodel + Banner_Swing.blockyanim, objet parent
Furniture_Outlander_Banner), le fanion celui de Furniture_Flag_Small_Red (Blocks/Miscellaneous/Flag_Small.blockymodel).
Seules les textures changent : changer la couleur ou l'emblème d'un village, c'est changer l'id du bloc.

UV relevés dans Assets.zip (16 novembre 2026) :
    Banner (64 × 128) : poutre 40 × 6 × 6, lignes 0 à 18 ; tissu en trois pans de 32 de large à x = 10 :
        y 18-54, 54-85, 85-112 (l'alpha découpe la forme).
    Flag_Small (32 × 32) : mât 4 × 32 en (0, 0), bouts en (5, 27) ; tissu en trois pans à (4, 0) 8 × 17,
        (12, 0) 7 × 17, (19, 0) 7 × 17.

Usage : python3 tools/generate_conquest.py [--preview DIR]
"""
import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
RES = ROOT / "src/main/resources"
ITEMS = RES / "Server/Item/Items/Nakasar/Peuples/Standards"
TEXTURES = RES / "Common/Blocks/Nakasar/Peuples/Standards"
ICONS = RES / "Common/Icons/Nakasar/Peuples/Standards"
TEX_PATH = "Blocks/Nakasar/Peuples/Standards/"
ICON_PATH = "Icons/Nakasar/Peuples/Standards/"
LANG_BEGIN = "# ---- Conquête des lieux-dits (généré par tools/generate_conquest.py, ne pas modifier à la main) ----"
LANG_END = "# ---- Fin de la conquête ----"
PREFIX = "Nakasar_Peuples_Standard_"
PENNANT = "Nakasar_Peuples_Pennant_"
BLANK = PREFIX + "Blank"

# Couleurs (même ordre que Heraldry.COLOURS) : id, fr, en, tissu, ombre, liseré.
COLOURS = [
    ("Red", "rouge", "red", (168, 36, 42), (112, 22, 30), (226, 186, 92)),
    ("Blue", "bleue", "blue", (40, 76, 156), (24, 46, 104), (226, 196, 110)),
    ("Green", "verte", "green", (46, 120, 62), (28, 78, 40), (222, 204, 120)),
    ("Yellow", "jaune", "yellow", (222, 176, 52), (164, 122, 30), (110, 62, 28)),
    ("White", "blanche", "white", (226, 222, 208), (176, 170, 156), (52, 82, 140)),
    ("Black", "noire", "black", (40, 38, 44), (20, 18, 24), (196, 160, 80)),
    ("Purple", "pourpre", "purple", (106, 48, 132), (66, 28, 86), (220, 190, 110)),
    ("Orange", "orange", "orange", (214, 110, 36), (150, 70, 22), (60, 40, 30)),
]
# Emblèmes (même ordre que Heraldry.EMBLEMS) : id, fr, en, peuple (trois par peuple, l'étoile pour tous).
EMBLEMS = [
    ("Leaf", "à la feuille", "with a leaf", "Kweebec"),
    ("Acorn", "au gland", "with an acorn", "Kweebec"),
    ("Mushroom", "au champignon", "with a mushroom", "Kweebec"),
    ("Tusk", "à la défense", "with a tusk", "Trork"),
    ("Axe", "à la hache", "with an axe", "Trork"),
    ("Skull", "au crâne", "with a skull", "Trork"),
    ("Sun", "au soleil", "with a sun", "Feran"),
    ("Feather", "à la plume", "with a feather", "Feran"),
    ("Dune", "à la dune", "with a dune", "Feran"),
    ("Snowflake", "au flocon", "with a snowflake", "Renonce"),
    ("Hammer", "au marteau", "with a hammer", "Renonce"),
    ("Tower", "à la tour", "with a tower", "Renonce"),
    ("Flame", "à la flamme", "with a flame", "Slothian"),
    ("Eye", "à l'œil", "with an eye", "Slothian"),
    ("Lotus", "au lotus", "with a lotus", "Slothian"),
    ("Star", "à l'étoile", "with a star", None),
]
WOOD = (104, 72, 44)
WOOD_DARK = (70, 46, 28)
WOOD_LIGHT = (136, 98, 62)
LINEN = (214, 202, 176)
LINEN_DARK = (170, 156, 128)

FR = {}
EN = {}


def t(key, fr, en):
    if key in FR:
        raise SystemExit(f"clé en double : {key}")
    FR[key] = fr
    EN[key] = en
    return "nakasar_peuples." + key


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ---- Dessin ----

def poly(d, pts, fill, ox, oy, s=1.0):
    d.polygon([(ox + x * s, oy + y * s) for x, y in pts], fill=fill)


def emblem(d, eid, cx, cy, fg, shade):
    """Emblème centré en (cx, cy), environ 22 × 24 pixels, couleur fg (ombre shade)."""
    if eid == "Leaf":
        poly(d, [(0, -12), (7, -6), (9, 2), (5, 9), (0, 12), (-5, 9), (-9, 2), (-7, -6)], fg, cx, cy)
        d.line([(cx, cy - 10), (cx, cy + 12)], fill=shade, width=1)
        for k in (-5, 0, 5):
            d.line([(cx, cy + k), (cx + 5, cy + k - 4)], fill=shade)
            d.line([(cx, cy + k), (cx - 5, cy + k - 4)], fill=shade)
    elif eid == "Acorn":
        d.ellipse([cx - 7, cy - 4, cx + 7, cy + 12], fill=fg)
        d.rectangle([cx - 9, cy - 8, cx + 9, cy - 2], fill=shade)
        d.rectangle([cx - 1, cy - 12, cx + 1, cy - 8], fill=shade)
    elif eid == "Mushroom":
        d.pieslice([cx - 11, cy - 11, cx + 11, cy + 7], 180, 360, fill=fg)
        d.rectangle([cx - 3, cy - 2, cx + 3, cy + 11], fill=fg)
        for x, y in ((-5, -6), (3, -8), (6, -3)):
            d.ellipse([cx + x - 1, cy + y - 1, cx + x + 1, cy + y + 1], fill=shade)
    elif eid == "Tusk":
        poly(d, [(-6, 12), (-2, 12), (2, 2), (6, -12), (-1, -2)], fg, cx, cy)
        poly(d, [(6, 12), (2, 12), (-1, 4), (-6, -12), (1, -2)], fg, cx, cy)
        d.line([(cx - 5, cy + 11), (cx + 5, cy + 11)], fill=shade)
    elif eid == "Axe":
        d.rectangle([cx - 1, cy - 12, cx + 1, cy + 12], fill=fg)
        poly(d, [(1, -10), (10, -12), (11, -2), (1, -4)], fg, cx, cy)
        poly(d, [(-1, -10), (-10, -12), (-11, -2), (-1, -4)], fg, cx, cy)
    elif eid == "Skull":
        d.ellipse([cx - 9, cy - 11, cx + 9, cy + 5], fill=fg)
        d.rectangle([cx - 5, cy + 2, cx + 5, cy + 10], fill=fg)
        d.ellipse([cx - 6, cy - 5, cx - 1, cy + 0], fill=shade)
        d.ellipse([cx + 1, cy - 5, cx + 6, cy + 0], fill=shade)
        for x in (-3, 0, 3):
            d.line([(cx + x, cy + 6), (cx + x, cy + 10)], fill=shade)
    elif eid == "Sun":
        for k in range(12):
            a = k * math.pi / 6
            d.line([(cx + math.cos(a) * 6, cy + math.sin(a) * 6), (cx + math.cos(a) * 12, cy + math.sin(a) * 12)], fill=fg, width=2)
        d.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=fg)
        d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=shade)
    elif eid == "Feather":
        poly(d, [(6, -12), (9, -6), (4, 4), (-4, 11), (-6, 12), (-5, 8), (-2, -2)], fg, cx, cy)
        d.line([(cx - 6, cy + 12), (cx + 6, cy - 10)], fill=shade)
    elif eid == "Dune":
        d.pieslice([cx - 12, cy - 4, cx + 6, cy + 16], 180, 360, fill=fg)
        d.pieslice([cx - 2, cy - 1, cx + 14, cy + 15], 180, 360, fill=shade)
        d.ellipse([cx + 2, cy - 12, cx + 8, cy - 6], fill=fg)
    elif eid == "Snowflake":
        for k in range(3):
            a = k * math.pi / 3
            dx, dy = math.cos(a) * 12, math.sin(a) * 12
            d.line([(cx - dx, cy - dy), (cx + dx, cy + dy)], fill=fg, width=2)
            for sgn in (-1, 1):
                bx, by = cx + sgn * dx * 0.6, cy + sgn * dy * 0.6
                for b in (-1, 1):
                    ang = a + b * math.pi / 4 + (0 if sgn > 0 else math.pi)
                    d.line([(bx, by), (bx + math.cos(ang) * 4, by + math.sin(ang) * 4)], fill=fg)
        d.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=shade)
    elif eid == "Hammer":
        d.rectangle([cx - 1, cy - 4, cx + 1, cy + 12], fill=fg)
        d.rectangle([cx - 9, cy - 12, cx + 9, cy - 4], fill=fg)
        d.rectangle([cx - 9, cy - 12, cx - 6, cy - 4], fill=shade)
    elif eid == "Tower":
        d.rectangle([cx - 7, cy - 6, cx + 7, cy + 12], fill=fg)
        for x in (-7, -2, 3):
            d.rectangle([cx + x, cy - 11, cx + x + 3, cy - 6], fill=fg)
        d.rectangle([cx - 2, cy + 5, cx + 2, cy + 12], fill=shade)
        d.rectangle([cx - 1, cy - 2, cx + 1, cy + 1], fill=shade)
    elif eid == "Flame":
        poly(d, [(0, -13), (5, -5), (9, 2), (7, 9), (0, 12), (-7, 9), (-9, 2), (-4, -3), (-2, 2)], fg, cx, cy)
        poly(d, [(0, -2), (4, 4), (3, 9), (0, 10), (-3, 9), (-3, 4)], shade, cx, cy)
    elif eid == "Eye":
        poly(d, [(-12, 0), (-6, -6), (0, -8), (6, -6), (12, 0), (6, 6), (0, 8), (-6, 6)], fg, cx, cy)
        d.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill=shade)
        d.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=fg)
    elif eid == "Lotus":
        poly(d, [(0, -12), (4, -2), (0, 6), (-4, -2)], fg, cx, cy)
        poly(d, [(-11, -4), (-3, 2), (-1, 8), (-8, 4)], fg, cx, cy)
        poly(d, [(11, -4), (3, 2), (1, 8), (8, 4)], fg, cx, cy)
        d.rectangle([cx - 10, cy + 8, cx + 10, cy + 10], fill=shade)
    elif eid == "Star":
        pts = []
        for k in range(10):
            r = 12 if k % 2 == 0 else 5
            a = -math.pi / 2 + k * math.pi / 5
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
        d.polygon(pts, fill=fg)
    else:
        raise SystemExit(f"emblème sans dessin : {eid}")


def cloth_mask(img, x0, y0, x1, y1, tail):
    """Coupe le bas du tissu : queue d'aronde (deux pointes)."""
    px = img.load()
    mid = (x0 + x1) // 2
    for y in range(y1 - tail, y1):
        depth = (y - (y1 - tail)) / tail
        half = int((x1 - x0) / 2 * depth)
        for x in range(mid - half, mid + half):
            px[x, y] = (0, 0, 0, 0)


def wood_beam(d, x0, y0, x1, y1):
    d.rectangle([x0, y0, x1 - 1, y1 - 1], fill=WOOD)
    for y in range(y0, y1, 3):
        d.line([(x0, y), (x1 - 1, y)], fill=WOOD_DARK if (y // 3) % 2 else WOOD_LIGHT)


def standard_texture(colour, eid):
    """Texture 64 × 128 de la bannière (UV du modèle vanilla Banner)."""
    img = Image.new("RGBA", (64, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    wood_beam(d, 0, 0, 64, 18)
    x0, x1, y0, y1 = 10, 42, 18, 112
    if colour is None:
        main, dark, trim, fg, shade = LINEN, LINEN_DARK, LINEN_DARK, None, None
    else:
        _cid, _fr, _en, main, dark, trim = colour
        light = colour[0] in ("White", "Yellow", "Orange")
        fg = trim if light else (236, 226, 196)
        shade = dark if not light else (max(0, trim[0] - 20), max(0, trim[1] - 20), max(0, trim[2] - 20))
    d.rectangle([x0, y0, x1 - 1, y1 - 1], fill=main)
    # Plis : bandes d'ombre verticales.
    for x in (x0 + 7, x0 + 23):
        d.line([(x, y0), (x, y1)], fill=dark)
    # Liseré sur les bords et sous la poutre.
    d.rectangle([x0, y0, x1 - 1, y0 + 2], fill=trim)
    d.line([(x0, y0), (x0, y1)], fill=trim, width=2)
    d.line([(x1 - 2, y0), (x1 - 2, y1)], fill=trim, width=2)
    if fg is not None:
        # Écu : bande de la couleur claire derrière l'emblème, au milieu (pan du milieu y 54-85).
        cy = 60
        d.ellipse([x0 + 3, cy - 16, x1 - 4, cy + 16], fill=dark)
        emblem(d, eid, (x0 + x1) // 2 - 1, cy, fg, shade if shade != dark else main)
        d.line([(x0 + 4, 92), (x1 - 5, 92)], fill=trim, width=2)
    cloth_mask(img, x0, y0, x1, y1, 12)
    return img


def pennant_texture(colour):
    """Texture 32 × 32 du fanion (UV du modèle vanilla Flag_Small)."""
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    _cid, _fr, _en, main, dark, trim = colour
    d.rectangle([0, 0, 3, 31], fill=WOOD)
    d.line([(1, 0), (1, 31)], fill=WOOD_LIGHT)
    d.rectangle([5, 27, 12, 31], fill=WOOD_DARK)
    d.rectangle([4, 0, 25, 16], fill=main)
    d.rectangle([4, 0, 25, 2], fill=trim)
    d.rectangle([4, 14, 25, 16], fill=trim)
    d.line([(12, 3), (12, 13)], fill=dark)
    d.line([(19, 3), (19, 13)], fill=dark)
    return img


def icon_of(texture):
    """Icône 64 × 64 : la poutre et le tissu de face."""
    icon = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    cloth = texture.crop((10, 18, 42, 112)).resize((18, 53), Image.NEAREST)
    beam = Image.new("RGBA", (34, 4), WOOD + (255,))
    ImageDraw.Draw(beam).line([(0, 3), (33, 3)], fill=WOOD_DARK + (255,))
    icon.alpha_composite(beam, (15, 4))
    icon.alpha_composite(cloth, (23, 8))
    return icon


def pennant_icon(colour):
    icon = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(icon)
    _cid, _fr, _en, main, dark, trim = colour
    d.rectangle([18, 6, 21, 60], fill=WOOD)
    d.polygon([(22, 8), (50, 14), (22, 30)], fill=main)
    d.line([(22, 8), (50, 14), (22, 30)], fill=trim, width=2)
    return icon


def save_png(img, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


# ---- Objets ----

def standard_item(sid, texture_name, icon_name, comment, recipe=None, quality="Uncommon", color="#7a2b2b"):
    data = {
        "$Comment": comment + " Généré par tools/generate_conquest.py.",
        "Parent": "Furniture_Outlander_Banner",
        "TranslationProperties": {
            "Name": f"nakasar_peuples.items.{sid}.name",
            "Description": f"nakasar_peuples.items.{sid}.description",
        },
        "Icon": ICON_PATH + icon_name,
        "Quality": quality,
        "BlockType": {
            "CustomModelTexture": [{"Texture": TEX_PATH + texture_name, "Weight": 1}],
            "TextureComputedColor": color,
        },
    }
    if recipe:
        data["Recipe"] = recipe
    return data


def pennant_item(pid, texture_name, icon_name, comment, color):
    return {
        "$Comment": comment + " Généré par tools/generate_conquest.py.",
        "TranslationProperties": {
            "Name": f"nakasar_peuples.items.{pid}.name",
            "Description": f"nakasar_peuples.items.{pid}.description",
        },
        "PlayerAnimationsId": "Block",
        "Categories": ["Blocks.Deco"],
        "Icon": ICON_PATH + icon_name,
        "IconProperties": {"Scale": 0.5, "Rotation": [22.5, 49, 22.5], "Translation": [1, -16]},
        "BlockType": {
            "BlockParticleSetId": "Wood",
            "BlockSoundSetId": "Wood",
            "PhysicalMaterialId": "Wood",
            "CustomModel": "Blocks/Miscellaneous/Flag_Small.blockymodel",
            "CustomModelTexture": [{"Texture": TEX_PATH + texture_name, "Weight": 1}],
            "DrawType": "Model",
            "Flags": {},
            "Gathering": {"Breaking": {"GatherType": "Benches"}},
            "HitboxType": "Beam_Thin",
            "Material": "Empty",
            "Opacity": "Transparent",
            "Support": {"Down": [{"FaceType": "Full"}]},
            "VariantRotation": "NESW",
            "ParticleColor": "#3a2014",
            "TextureComputedColor": color,
        },
        "Tags": {"Type": ["Furniture"]},
        "Scale": 0.6,
        "ItemSoundSetId": "ISS_Blocks_Wood",
        "Quality": "Uncommon",
    }


def hexcol(rgb):
    return "#%02x%02x%02x" % rgb


def assets(preview):
    count = 0
    sheet = []
    for colour in COLOURS:
        cid, cfr, cen = colour[0], colour[1], colour[2]
        for eid, efr, een, _people in EMBLEMS:
            sid = f"{PREFIX}{cid}_{eid}"
            tex = standard_texture(colour, eid)
            save_png(tex, TEXTURES / f"{sid}.png")
            save_png(icon_of(tex), ICONS / f"{sid}.png")
            write_json(ITEMS / f"{sid}.json", standard_item(
                sid, f"{sid}.png", f"{sid}.png",
                f"Bannière d'un village (blason {cid} {eid}) : modèle et balancement de la bannière vanilla des ruines humaines.",
                color=hexcol(colour[3])))
            t(f"items.{sid}.name", f"Bannière {cfr} {efr}", f"{cen.capitalize()} banner {een}")
            t(f"items.{sid}.description", "Les couleurs d'un village. Accrochée à un mur, elle dit à qui appartient le lieu.",
              "A village's colours. Hung on a wall, it tells who holds the place.")
            sheet.append(tex)
            count += 1
        pid = f"{PENNANT}{cid}"
        save_png(pennant_texture(colour), TEXTURES / f"{pid}.png")
        save_png(pennant_icon(colour), ICONS / f"{pid}.png")
        write_json(ITEMS / f"{pid}.json", pennant_item(pid, f"{pid}.png", f"{pid}.png",
                                                       f"Fanion {cid} du mât d'un lieu-dit : modèle du petit drapeau vanilla.",
                                                       hexcol(colour[3])))
        t(f"items.{pid}.name", f"Fanion {cfr}", f"{cen.capitalize()} pennant")
        t(f"items.{pid}.description", "Flotte au mât d'un lieu-dit tenu par un village.", "Flies from the mast of a hamlet held by a village.")
    tex = standard_texture(None, None)
    save_png(tex, TEXTURES / f"{BLANK}.png")
    save_png(icon_of(tex), ICONS / f"{BLANK}.png")
    write_json(ITEMS / f"{BLANK}.json", standard_item(
        BLANK, f"{BLANK}.png", f"{BLANK}.png",
        "Bannière vierge : au tableau d'un village dont on porte les couleurs (onglet Domaine), elle prend son blason.",
        recipe={"Input": [{"ItemId": "Ingredient_Bolt_Cotton", "Quantity": 2}, {"ItemId": "Ingredient_Stick", "Quantity": 1}],
                "OutputQuantity": 1, "BenchRequirement": [{"Type": "Crafting", "Id": "Loombench"}]},
        quality="Common", color=hexcol(LINEN)))
    t(f"items.{BLANK}.name", "Bannière vierge", "Blank banner")
    t(f"items.{BLANK}.description",
      "Une toile sans blason. Porte les couleurs d'un village et passe à son tableau (onglet Domaine) pour y broder ses armes.",
      "A cloth with no arms. Wear a village's colours and visit its board (Domain tab) to embroider its arms on it.")
    if preview:
        preview.mkdir(parents=True, exist_ok=True)
        cols = len(EMBLEMS)
        big = Image.new("RGBA", (cols * 36, len(COLOURS) * 98), (40, 44, 52, 255))
        for i, img in enumerate(sheet):
            big.alpha_composite(img.crop((8, 18, 44, 116)), ((i % cols) * 36, (i // cols) * 98))
        big = big.resize((big.width * 2, big.height * 2), Image.NEAREST)
        big.save(preview / "bannieres.png")
        print("aperçu", preview / "bannieres.png")
    print(f"{count} bannières, {len(COLOURS)} fanions, bannière vierge")


# ---- Textes ----

def texts():
    for cid, cfr, cen, *_ in COLOURS:
        t(f"conquest.colour.{cid}", cfr, cen)
    for eid, efr, een, _p in EMBLEMS:
        t(f"conquest.emblem.{eid}", efr, een)
    for key, fr, en in TEXTS:
        t("conquest." + key, fr, en)


# Textes du Java (clés nakasar_peuples.conquest.<clé>) ; {x} : paramètres.
TEXTS = [
    ("arms", "Bannière {colour} {emblem}", "{colour} banner {emblem}"),
]


def write_langs():
    for locale, table in (("fr-FR", FR), ("en-US", EN)):
        path = RES / f"Server/Languages/{locale}/nakasar_peuples.lang"
        text = path.read_text(encoding="utf-8")
        block = "\n".join([LANG_BEGIN] + [f"{k} = {v}" for k, v in table.items()] + [LANG_END]) + "\n"
        if LANG_BEGIN in text:
            before, rest = text.split(LANG_BEGIN, 1)
            after = rest.split(LANG_END, 1)[1].lstrip("\n")
            outside = before + after
            text = before + block + after
        else:
            outside = text
            text = block + text
        existing = {line.split("=", 1)[0].strip() for line in outside.splitlines() if "=" in line and not line.startswith("#")}
        dup = sorted(k for k in table if k in existing)
        if dup:
            raise SystemExit(f"clés déjà présentes dans {locale} (hors bloc de la conquête) : {dup[:10]}")
        path.write_text(text, encoding="utf-8")
        print(f"{path.relative_to(ROOT)} : {len(table)} clés de la conquête")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", type=Path, help="dossier de l'aperçu des bannières")
    args = parser.parse_args()
    assets(args.preview)
    texts()
    write_langs()


if __name__ == "__main__":
    main()
