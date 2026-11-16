#!/usr/bin/env python3
"""Génère les assets de la conquête des lieux-dits (GDD « Villages et lieux-dits : allégeance et conquête », Kevin,
16 novembre 2026 ; Java world/Allegiance, Heraldry, Banners, Garrisons, Sieges, Territories, DomainPage).

Sorties :
    Server/Item/Items/Nakasar/Peuples/Standards/Nakasar_Peuples_Standard_<Couleur>_<Emblème>.json   128 bannières
    Server/Item/Items/Nakasar/Peuples/Standards/Nakasar_Peuples_Pennant_<Couleur>.json               8 fanions
    Server/Item/Items/Nakasar/Peuples/Standards/Nakasar_Peuples_Standard_Blank.json                  bannière vierge
        (fabriquée au métier à tisser vanilla : 2 rouleaux de coton et un bâton)
    Common/Blocks/Nakasar/Peuples/Standards/*.png   textures (UV des modèles vanilla, voir plus bas)
    Common/Icons/ItemsGenerated/Nakasar_Peuples_*.png    icônes 64 × 64
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
ICONS = RES / "Common/Icons/ItemsGenerated"
TEX_PATH = "Blocks/Nakasar/Peuples/Standards/"
ICON_PATH = "Icons/ItemsGenerated/"
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
    ("nobody", "personne", "nobody"),
    # Blason (Heraldry)
    ("arms.rank", "Il faut être Hôte de {village} pour changer son blason.", "You must be a Host of {village} to change its arms."),
    ("arms.wait", "Le blason a changé il y a peu : encore {days} jour(s) avant de le reprendre.", "The arms changed recently: {days} more day(s) before changing them again."),
    ("arms.same", "C'est déjà le blason du village.", "These are already the village's arms."),
    ("arms.bolts", "Il faut {count} rouleaux de tissu pour coudre les nouvelles bannières.", "You need {count} bolts of cloth to sew the new banners."),
    ("arms.changed", "{village} adopte un nouveau blason : {arms}. Ses lieux-dits seront repavoisés.", "{village} adopts new arms: {arms}. Its hamlets will be decked anew."),
    # Couleurs du joueur (Colours)
    ("colours.dropped", "Tu ne portes plus les couleurs de {village}.", "You no longer wear the colours of {village}."),
    ("colours.rank", "Il faut être Ami de {village} pour porter ses couleurs.", "You must be a Friend of {village} to wear its colours."),
    ("colours.wait", "Tu as changé de couleurs il y a peu : encore {days} jour(s).", "You changed colours recently: {days} more day(s)."),
    ("colours.taken", "Tu portes désormais les couleurs de {village} ({arms}).", "You now wear the colours of {village} ({arms})."),
    # Embargo, entrée, panneaux
    ("embargo", "Nous ne commerçons pas avec les ennemis de {village}.", "We do not trade with the enemies of {village}."),
    ("enter", "{hamlet}", "{hamlet}"),
    ("enter.sub", "Terre de {village}", "Land of {village}"),
    ("panel.title", "{building} — {hamlet}, terre de {village}", "{building} — {hamlet}, land of {village}"),
    ("panel.line", "Ce lieu-dit appartient à {village}.", "This hamlet belongs to {village}."),
    # Changements de main (Allegiance.setOwner)
    ("owner.embassy", "{hamlet} se rallie à {village} après une ambassade (avant : {from}).", "{hamlet} joins {village} after an embassy (before: {from})."),
    ("owner.rally", "{hamlet} se rallie de lui-même à {village} (avant : {from}).", "{hamlet} rallies to {village} of its own accord (before: {from})."),
    ("owner.conquest", "{village} a pris {hamlet} par les armes (avant : {from}).", "{village} took {hamlet} by force (before: {from})."),
    ("owner.secession", "{hamlet} rejoint {village} (avant : {from}).", "{hamlet} joins {village} (before: {from})."),
    ("owner.command", "{hamlet} appartient désormais à {village} (avant : {from}).", "{hamlet} now belongs to {village} (before: {from})."),
    ("owner.free", "{hamlet} rejette l'autorité de {village} et redevient libre.", "{hamlet} casts off the rule of {village} and is free again."),
    ("occupation.end", "L'occupation de {hamlet} prend fin : le lieu-dit se résigne.", "The occupation of {hamlet} ends: the hamlet resigns itself."),
    # Lettre de ralliement (dialogue)
    ("letter.no", "Une lettre ? Il faudrait d'abord porter les couleurs d'un village dont nous voulons bien entendre parler.", "A letter? First wear the colours of a village we would care to hear from."),
    ("letter.yes", "Bien. Je glisserai un mot en faveur de {village} au prochain émissaire.", "Good. I will put in a word for {village} with their next envoy."),
    # Tribut
    ("tribute.essor", "de l'essor", "growth"),
    ("tribute.lot", "{count} × {item}", "{count} × {item}"),
    ("tribute.home", "Le tribut de {hamlet} est arrivé : {what} et +{essor} d'essor.", "The tribute from {hamlet} has arrived: {what} and +{essor} growth."),
    # Rumeurs
    ("rumour.embassy", "On dit que {hamlet} s'est rallié à {village} après une ambassade.", "They say {hamlet} joined {village} after an embassy."),
    ("rumour.rally", "On dit que {hamlet} s'est donné de lui-même à {village}.", "They say {hamlet} gave itself to {village}."),
    ("rumour.conquest", "On dit que {village} a pris {hamlet} par les armes.", "They say {village} took {hamlet} by force."),
    ("rumour.secession", "On dit que {hamlet} a rejeté l'autorité de {village}.", "They say {hamlet} cast off the rule of {village}."),
    ("rumour.command", "On dit que {hamlet} a changé de maître : {village}.", "They say {hamlet} has a new master: {village}."),
    ("rumour.expedition", "Une troupe de {village} marche sur {hamlet}.", "A troop from {village} is marching on {hamlet}."),
    # « À qui appartient ce lieu ? »
    ("say.free", "À personne ! Nous sommes libres, et nous comptons le rester.", "Nobody! We are free, and we mean to stay so."),
    ("say.freeFavourite", "À personne pour l'instant… même si les gens de {village} sont bien vus ici.", "Nobody for now… though the folk of {village} are well liked here."),
    ("say.occupied", "Les soldats de {village} tiennent la place. Encore {days} jour(s) sous leur botte, dit-on.", "The soldiers of {village} hold the place. {days} more day(s) under their boot, they say."),
    ("say.owned.glad", "Nous sommes de {village}, et fiers de l'être. {guards} garde(s) veillent sur nous.", "We belong to {village}, and proudly. {guards} guard(s) watch over us."),
    ("say.owned.fine", "Nous dépendons de {village}. {guards} garde(s) sont postés ici.", "We answer to {village}. {guards} guard(s) are posted here."),
    ("say.owned.grumble", "{village} prétend nous tenir… ça ne durera pas toujours.", "{village} claims to rule us… it won't last forever."),
    # Réputation
    ("reason.embassy", "tu as attaqué une ambassade", "you attacked an embassy"),
    ("reason.resident", "tu as tué un habitant d'un lieu-dit", "you killed a hamlet resident"),
    ("reason.conquest", "tu as pris part à une conquête", "you took part in a conquest"),
    ("reason.conquered", "tu as aidé à conquérir le lieu-dit", "you helped conquer the hamlet"),
    ("reason.defence", "tu as défendu un lieu-dit", "you defended a hamlet"),
    # Tournées
    ("trip.kind.A", "Ambassade", "Embassy"),
    ("trip.kind.E", "Expédition", "Expedition"),
    ("trip.kind.T", "Tribut", "Tribute"),
    ("trip.kind.G", "Relève de la garde", "Guard relief"),
    ("trip.lost.A", "L'ambassade partie pour {hamlet} n'est jamais revenue.", "The embassy sent to {hamlet} never came back."),
    ("trip.lost.E", "L'expédition partie pour {hamlet} a été anéantie.", "The expedition sent to {hamlet} was wiped out."),
    ("trip.lost.T", "Les porteurs du tribut de {hamlet} ne sont jamais arrivés.", "The tribute porters from {hamlet} never arrived."),
    ("trip.lost.G", "La relève partie pour {hamlet} n'est jamais arrivée.", "The relief sent to {hamlet} never arrived."),
    # Ambassades
    ("embassy.already", "{hamlet} appartient déjà au village.", "{hamlet} already belongs to the village."),
    ("embassy.tier", "Le village doit atteindre le palier 2 pour tenir des lieux-dits.", "The village must reach tier 2 to hold hamlets."),
    ("embassy.full", "{village} tient déjà {cap} lieu(x)-dit(s) : une Maison du conseil plus grande en permettrait davantage.", "{village} already holds {cap} hamlet(s): a bigger Council house would allow more."),
    ("embassy.cooling", "{hamlet} ne veut plus entendre parler de nous pour quelques jours.", "{hamlet} won't hear from us for a few days."),
    ("embassy.busy", "Une ambassade est déjà en route.", "An embassy is already on its way."),
    ("embassy.far", "Ce lieu-dit est trop loin (plus de {range} blocs).", "This hamlet is too far away (more than {range} blocks)."),
    ("embassy.left", "Une ambassade part pour {hamlet}.", "An embassy leaves for {hamlet}."),
    ("embassy.warned", "Une ambassade de {village} se dirige vers {hamlet}.", "An embassy from {village} is heading for {hamlet}."),
    ("embassy.rank", "Il faut être Ami de {village} pour demander une ambassade.", "You must be a Friend of {village} to request an embassy."),
    ("embassy.offering", "Il faut {count} faveurs du peuple pour cette demande.", "This request takes {count} favours of the people."),
    ("embassy.chased", "Les gardes de {owner} chassent l'ambassade de {village} hors de {hamlet} !", "The guards of {owner} drive the embassy of {village} out of {hamlet}!"),
    ("embassy.parley", "L'ambassade de {village} parlemente sur la place de {hamlet}.", "The embassy of {village} parleys in the square of {hamlet}."),
    ("embassy.failed", "{hamlet} repousse l'ambassade de {village} (chance : {chance} %).", "{hamlet} turns away the embassy of {village} (chance: {chance}%)."),
    ("embassy.noRoom", "{hamlet} voudrait nous rejoindre, mais le village ne peut pas tenir un lieu-dit de plus.", "{hamlet} would join us, but the village cannot hold another hamlet."),
    # Expéditions et sièges
    ("siege.tier", "Le village doit atteindre le palier 3 pour lancer une expédition.", "The village must reach tier 3 to send an expedition."),
    ("siege.free", "{hamlet} est libre : on le gagne par la parole, pas par les armes.", "{hamlet} is free: win it with words, not arms."),
    ("siege.notRival", "{village} n'est pas un rival : pas d'expédition contre lui.", "{village} is not a rival: no expedition against it."),
    ("siege.truce", "Une trêve lie le village à {village}.", "A truce binds the village to {village}."),
    ("siege.cooling", "Le village se remet de sa dernière expédition.", "The village is recovering from its last expedition."),
    ("siege.busy", "Une expédition est déjà en marche.", "An expedition is already marching."),
    ("siege.rank", "Il faut être Hôte de {village} pour demander une expédition.", "You must be a Host of {village} to request an expedition."),
    ("siege.announce", "{village} lève une troupe contre {hamlet}, tenu par {owner} !", "{village} raises a troop against {hamlet}, held by {owner}!"),
    ("siege.assault", "La troupe de {village} donne l'assaut à {hamlet} !", "The troop of {village} storms {hamlet}!"),
    ("siege.won", "{village} prend {hamlet} à {owner} !", "{village} takes {hamlet} from {owner}!"),
    ("siege.repelled", "{hamlet} repousse l'assaut de {village} : {owner} garde le lieu-dit.", "{hamlet} repels the assault of {village}: {owner} keeps the hamlet."),
    ("siege.lost", "La troupe partie pour {hamlet} a été anéantie.", "The troop sent to {hamlet} was wiped out."),
    ("siege.retreat", "La troupe envoyée contre {hamlet} renonce et rentre au village.", "The troop sent against {hamlet} gives up and heads home."),
    # Commandes
    ("cmd.allegiance.desc", "Allégeance du lieu-dit le plus proche", "Allegiance of the nearest hamlet"),
    ("cmd.village.arg", "Nom du village", "Village name"),
    ("cmd.embassy.desc", "Une ambassade du village part vers le lieu-dit le plus proche", "Send an embassy from the village to the nearest hamlet"),
    ("cmd.embassy.started", "Ambassade de {village} vers {hamlet} (chance actuelle : {chance} %).", "Embassy from {village} to {hamlet} (current chance: {chance}%)."),
    ("cmd.expedition.desc", "Une expédition du village part vers le lieu-dit le plus proche", "Send an expedition from the village to the nearest hamlet"),
    ("cmd.expedition.forced", "Conditions ignorées : {why}", "Conditions skipped: {why}"),
    ("cmd.expedition.started", "Expédition de {village} vers {hamlet}.", "Expedition from {village} to {hamlet}."),
    ("cmd.busy", "Impossible : une tournée de ce genre est déjà en route.", "Impossible: such a trip is already on its way."),
    ("cmd.influence.arg", "Influence (-100 à 100)", "Influence (-100 to 100)"),
    ("cmd.influence.desc", "Fixe l'influence d'un village sur le lieu-dit le plus proche", "Set a village's influence on the nearest hamlet"),
    ("cmd.influence.set", "Influence de {village} sur {hamlet} : {value}", "Influence of {village} on {hamlet}: {value}"),
    ("cmd.owner.arg", "Village propriétaire, ou « libre »", "Owner village, or « free »"),
    ("cmd.owner.desc", "Donne le lieu-dit le plus proche à un village (ou le libère)", "Give the nearest hamlet to a village (or free it)"),
    ("cmd.header", "{hamlet} : propriétaire {owner}, gardes {guards}/{target}, occupé {occupied}, jours de défaveur {low}, jours de ralliement {rally}",
     "{hamlet}: owner {owner}, guards {guards}/{target}, occupied {occupied}, low days {low}, rally days {rally}"),
    ("cmd.line", "  {village} : influence {value}, relation {relation}, lieux-dits {holds}/{cap}", "  {village}: influence {value}, relation {relation}, hamlets {holds}/{cap}"),
    # Onglet Domaine (DomainPage)
    ("page.tab", "Domaine", "Domain"),
    ("page.title", "{village} — Domaine", "{village} — Domain"),
    ("page.arms", "Blason du village", "Village arms"),
    ("page.arms.hint", "Un Hôte peut changer le blason contre {count} rouleaux de tissu, une fois tous les {days} jours.", "A Host may change the arms for {count} bolts of cloth, once every {days} days."),
    ("page.arms.pending", "Nouveau blason : {count} rouleaux de tissu pour coudre les bannières.", "New arms: {count} bolts of cloth to sew the banners."),
    ("page.button.ColourPrev", "◀ Couleur", "◀ Colour"),
    ("page.button.ColourNext", "Couleur ▶", "Colour ▶"),
    ("page.button.EmblemPrev", "◀ Emblème", "◀ Emblem"),
    ("page.button.EmblemNext", "Emblème ▶", "Emblem ▶"),
    ("page.button.apply", "Adopter ce blason", "Adopt these arms"),
    ("page.button.takeColours", "Porter ses couleurs", "Wear its colours"),
    ("page.button.dropColours", "Quitter ses couleurs", "Drop its colours"),
    ("page.button.embroider", "Broder mes bannières", "Embroider my banners"),
    ("page.button.embassy", "Ambassade ({count} faveurs)", "Embassy ({count} favours)"),
    ("page.button.expedition", "Expédition ({count} faveurs)", "Expedition ({count} favours)"),
    ("page.colours", "Tes couleurs", "Your colours"),
    ("page.colours.none", "Tu ne portes les couleurs d'aucun village.", "You wear no village's colours."),
    ("page.colours.ours", "Tu portes les couleurs de {village}.", "You wear the colours of {village}."),
    ("page.colours.other", "Tu portes les couleurs de {village}.", "You wear the colours of {village}."),
    ("page.banners", "Bannières vierges dans ton sac : {count} (Métier à tisser).", "Blank banners in your bag: {count} (Loom)."),
    ("page.embroidered", "{count} bannière(s) brodée(s) : {arms}.", "{count} banner(s) embroidered: {arms}."),
    ("page.holdings", "Lieux-dits tenus : {count}/{cap} (Maison du conseil niveau {council})", "Hamlets held: {count}/{cap} (Council house level {council})"),
    ("page.none", "Aucun lieu-dit à moins de {range} blocs.", "No hamlet within {range} blocks."),
    ("page.row.name", "{hamlet} · {distance} blocs {dir}", "{hamlet} · {distance} blocks {dir}"),
    ("page.row.free", "Libre", "Free"),
    ("page.row.owner", "À {village}", "Held by {village}"),
    ("page.row.influence", "Notre influence : {value}", "Our influence: {value}"),
    ("page.row.state", "{influence} · gardes : {guards}", "{influence} · guards: {guards}"),
    ("page.row.occupied", "{state} · occupé encore {days} jour(s)", "{state} · occupied for {days} more day(s)"),
    ("page.rule", "Le commerce attire un lieu-dit, le tort l'éloigne. Un Ami peut demander une ambassade, un Hôte une expédition contre un rival.",
     "Trade draws a hamlet in, harm drives it away. A Friend may request an embassy, a Host an expedition against a rival."),
    ("page.embassy.sent", "L'ambassade part pour {hamlet}.", "The embassy leaves for {hamlet}."),
    ("page.expedition.sent", "L'expédition se met en marche vers {hamlet}.", "The expedition marches on {hamlet}."),
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
