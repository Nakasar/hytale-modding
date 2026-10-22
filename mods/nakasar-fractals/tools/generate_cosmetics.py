"""Génère les cosmétiques de la saison 1 des fractales (étape 9 du GDD, docs/fractales/gdd.md).

    python3 mods/nakasar-fractals/tools/generate_cosmetics.py [--preview DOSSIER]

Trois pièces d'apparence, sans protection (armure à 0, comme les tenues du mod Vampires), vendues par l'Archiviste
contre des éclats de Brume (tools/generate_progression.py lit PRICES) et rares dans le coffre des fractales du jour :
- Armor_Nakasar_Fractal_Mist_Crown (tête) : couronne d'éclats de Brume qui flottent autour du front ;
- Armor_Nakasar_Fractal_Archdiviner_Hood (tête) : capuche pointue du culte de l'Archidevin (Falaise), liseré d'or ;
- Armor_Nakasar_Fractal_Mist_Mantle (torse) : épaulières de cristal et courte cape des Brumes.

Écrit les modèles (Common/Items/Nakasar/Fractals/Cosmetics/<Nom>/), les icônes, les objets
(Server/Item/Items/Cosmetic/Nakasar/Fractals/) et la langue nakasar_fractals_cosmetics.lang.

Pièces placées par rapport au centre de l'os, comme les tenues du mod Vampires (64 unités = 1 bloc, devant vers +Z) :
tête 30 × 28 × 28 (dessus à y = +14), torse 28 × 22 × 20.
"""
import json
import math
import sys
from pathlib import Path

import fractal_models as fm

MOD = Path(__file__).resolve().parent.parent
PACK = MOD / "src" / "main" / "resources"
COMMON = PACK / "Common"
SERVER = PACK / "Server"
MODELS = "Items/Nakasar/Fractals/Cosmetics"
ICONS = "Icons/Items/Nakasar/Fractals/Cosmetics"
ITEMS = SERVER / "Item/Items/Cosmetic/Nakasar/Fractals"
LANG = "nakasar_fractals_cosmetics"

CROWN = "Armor_Nakasar_Fractal_Mist_Crown"
HOOD = "Armor_Nakasar_Fractal_Archdiviner_Hood"
MANTLE = "Armor_Nakasar_Fractal_Mist_Mantle"
# Prix à l'Archiviste, en éclats de Brume.
PRICES = {CROWN: 150, HOOD: 200, MANTLE: 250}

BLUE, BLUE_LIGHT, BLUE_DARK = (120, 160, 255), (225, 236, 255), (54, 50, 140)
VIOLET, VIOLET_LIGHT, VIOLET_DARK = (170, 110, 255), (240, 220, 255), (70, 30, 120)
GOLD, GOLD_LIGHT = (214, 170, 70), (255, 230, 150)
ROBE, ROBE_DARK = (52, 36, 78), (30, 20, 46)


def crown():
    """Huit éclats en cercle au-dessus du front (y +15), plus grands devant ; une gemme au milieu du front."""
    parts = [("Circlet_Gem", (0, 6, 14.6), (4, 4, 1.4), 0, fm.crystal(VIOLET_DARK, VIOLET_LIGHT), "fullbright")]
    for k in range(8):
        a = math.radians(k * 45)
        front = math.cos(a)                     # 1 devant, -1 derrière
        h = 7 + 5 * max(0, front)
        x, z = math.sin(a) * 17, math.cos(a) * 17
        light = BLUE_LIGHT if k % 2 else VIOLET_LIGHT
        parts.append((f"Shard_{k}", (round(x, 2), 16 + h / 2, round(z, 2)), (3, h, 3), k * 45 + 20,
                      fm.crystal(BLUE_DARK, light), "fullbright"))
    return parts


def hood():
    """Capuche ouverte devant : dessus, dos, côtés, bord avant, pointe qui tombe dans le dos ; liseré d'or."""
    robe = fm.smooth(ROBE, (70, 50, 100))
    dark = fm.smooth(ROBE_DARK, ROBE)
    gold = fm.smooth(GOLD, GOLD_LIGHT)
    return [
        ("Top", (0, 16, -1), (34, 3, 32), 0, robe, "flat"),
        ("Back", (0, 2, -16), (34, 31, 3), 0, robe, "flat"),
        ("Side_L", (16.5, 2, -1), (3, 31, 30), 0, robe, "flat"),
        ("Side_R", (-16.5, 2, -1), (3, 31, 30), 0, robe, "flat"),
        ("Brim", (0, 13.5, 14.2), (34, 5, 3), 0, dark, "flat"),
        ("Trim_L", (16.6, 2, 14.2), (3.4, 26, 2.2), 0, gold, "flat"),
        ("Trim_R", (-16.6, 2, 14.2), (3.4, 26, 2.2), 0, gold, "flat"),
        ("Trim_Top", (0, 15.6, 15.6), (34, 1.6, 1.2), 0, gold, "flat"),
        ("Tip_A", (0, 13, -19.5), (14, 10, 4), 0, robe, "flat"),
        ("Tip_B", (0, 8, -22), (8, 8, 3), 0, dark, "flat"),
        ("Rune", (0, 4, -17.8), (6, 6, 0.8), 0, fm.crystal(VIOLET_DARK, VIOLET_LIGHT), "fullbright"),
    ]


def mantle():
    """Épaulières de cristal sur les épaules, col, courte cape dans le dos."""
    robe = fm.smooth(ROBE, (70, 50, 100))
    gold = fm.smooth(GOLD, GOLD_LIGHT)
    out = [
        ("Collar", (0, 11, -1), (30, 4, 22), 0, robe, "flat"),
        ("Cape", (0, -6, -11.4), (28, 30, 1.6), 0, robe, "flat"),
        ("Cape_Trim", (0, -21, -11.4), (28, 1.6, 2), 0, gold, "flat"),
        ("Clasp", (0, 10, 10.6), (5, 4, 1.2), 0, fm.crystal(VIOLET_DARK, VIOLET_LIGHT), "fullbright"),
    ]
    for side, sx in (("L", 1), ("R", -1)):
        out += [
            (f"Pauldron_{side}", (sx * 16, 11, 0), (12, 6, 16), 0, fm.smooth(BLUE_DARK, BLUE), "flat"),
            (f"Pauldron_Rim_{side}", (sx * 16, 8.4, 0), (13, 1.4, 17), 0, gold, "flat"),
            (f"Spike_A_{side}", (sx * 17, 17, 3), (3, 7, 3), 30, fm.crystal(BLUE_DARK, BLUE_LIGHT), "fullbright"),
            (f"Spike_B_{side}", (sx * 18.5, 16, -3), (2.4, 5, 2.4), -20, fm.crystal(BLUE_DARK, VIOLET_LIGHT), "fullbright"),
        ]
    return out


# Objet, dossier, os, emplacement d'armure, cosmétiques masqués, qualité, pièces, graine.
OUTFITS = [
    (CROWN, "Mist_Crown", "Head", ["HeadAccessory"], "Rare", crown, 401),
    (HOOD, "Archdiviner_Hood", "Head", ["HeadAccessory", "Haircut", "EarAccessory"], "Epic", hood, 402),
    (MANTLE, "Mist_Mantle", "Chest", ["Cape"], "Epic", mantle, 403),
]
# Hauteur des os sur le mannequin d'aperçu (comme le mod Vampires).
BONE_Y = {"Head": 112, "Chest": 76}


def write_json(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_model(name, bone, parts, seed):
    """Modèle porté : une seule pièce nommée comme l'os (isPiece), les boîtes autour du centre de l'os."""
    folder = COMMON / MODELS / name
    atlas, uv = fm.build_atlas(parts, seed, tex_w=128)
    folder.mkdir(parents=True, exist_ok=True)
    atlas.save(folder / "Texture.png")
    model = fm.build_model(bone, parts, uv)
    model["format"] = "character"
    model["nodes"][0]["shape"]["settings"]["isPiece"] = True
    (folder / "Model.blockymodel").write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")
    icon = fm.render(parts, atlas, uv, 256, yaw=-25, pitch=12, scale=4.0 if bone == "Head" else 3.4, center=(0, 4, 0))
    (COMMON / ICONS).mkdir(parents=True, exist_ok=True)
    icon.resize((64, 64)).save(COMMON / ICONS / f"{name}.png")
    return atlas, uv


def mannequin():
    grey = fm.smooth((150, 150, 160))
    skin = fm.smooth((210, 170, 140))
    return [("M_Head", (0, BONE_Y["Head"], 0), (28, 28, 28), 0, skin, "flat"),
            ("M_Chest", (0, BONE_Y["Chest"], 0), (28, 22, 20), 0, grey, "flat"),
            ("M_Pelvis", (0, 56, 0), (26, 12, 18), 0, grey, "flat"),
            ("M_Legs", (0, 28, 0), (24, 44, 14), 0, grey, "flat")]


def preview_on_body(name, bone, parts, seed, out):
    worn = [(f"W_{n}", (c[0], c[1] + BONE_Y[bone], c[2]), s, r, p, sh) for n, c, s, r, p, sh in parts]
    allp = mannequin() + worn
    atlas, uv = fm.build_atlas(allp, seed, tex_w=256)
    for label, yaw in (("face", -20), ("dos", 160), ("profil", 90)):
        fm.render(allp, atlas, uv, 360, yaw=yaw, pitch=8, scale=2.4, center=(0, 84, 0)).save(out / f"{name}_{label}.png")


def write_item(item_id, name, slot, hide, quality):
    write_json(ITEMS / f"{item_id}.json", {
        "TranslationProperties": {"Name": f"{LANG}.items.{item_id}.name",
                                  "Description": f"{LANG}.items.{item_id}.description"},
        "Quality": quality,
        "ItemLevel": 10,
        "PlayerAnimationsId": "Block",
        "ItemSoundSetId": "ISS_Armor_Leather",
        "Categories": ["Items.Armors"],
        "Icon": f"{ICONS}/{name}.png",
        "IconProperties": {"Rotation": [0, 0, 0], "Scale": 1.0, "Translation": [0, 0]},
        "Model": f"{MODELS}/{name}/Model.blockymodel",
        "Texture": f"{MODELS}/{name}/Texture.png",
        "Interactions": {"Primary": {"Interactions": [{"Type": "EquipItem"}]},
                         "Secondary": {"Interactions": [{"Type": "EquipItem"}]}},
        "Armor": {"ArmorSlot": slot, "BaseDamageResistance": 0, "CosmeticsToHide": hide},
        "MaxDurability": 1000,
        "Tags": {"Type": ["Armor"], "Family": ["Nakasar_Cosmetic"]},
    })


def lang():
    entries = {
        CROWN: ("Couronne des Brumes", "Cosmétique de la saison 1 des fractales : des éclats de Brume flottent autour "
                "du front. Aucune protection.", "Mist Crown", "Fractals season 1 cosmetic: Mist shards float around "
                "the brow. No protection."),
        HOOD: ("Capuche de l'Archidevin", "Cosmétique de la saison 1 des fractales : la capuche pointue du culte de la "
               "Falaise, liseré d'or et rune dans le dos. Aucune protection.", "Archdiviner's Hood",
               "Fractals season 1 cosmetic: the pointed hood of the Cliffside cult, gold trim and a rune on the back. "
               "No protection."),
        MANTLE: ("Mantelet des Brumes", "Cosmétique de la saison 1 des fractales : épaulières de cristal et courte "
                 "cape. Aucune protection.", "Mist Mantle", "Fractals season 1 cosmetic: crystal pauldrons and a "
                 "short cape. No protection."),
    }
    fr, en = {}, {}
    for item_id, (nf, df, ne, de) in entries.items():
        fr[f"items.{item_id}.name"], fr[f"items.{item_id}.description"] = nf, df
        en[f"items.{item_id}.name"], en[f"items.{item_id}.description"] = ne, de
    return fr, en


def write_lang(path, entries):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{k} = {v}\n" for k, v in entries.items()), encoding="utf-8")


def main():
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    for item_id, name, bone, hide, quality, build, seed in OUTFITS:
        parts = build()
        write_model(name, bone, parts, seed)
        write_item(item_id, name, bone, hide, quality)
        if preview:
            preview.mkdir(parents=True, exist_ok=True)
            preview_on_body(name, bone, parts, seed, preview)
    fr, en = lang()
    write_lang(SERVER / "Languages/fr-FR" / f"{LANG}.lang", fr)
    write_lang(SERVER / "Languages/en-US" / f"{LANG}.lang", en)
    print(f"Cosmétiques : {len(OUTFITS)} pièces")


if __name__ == "__main__":
    main()
