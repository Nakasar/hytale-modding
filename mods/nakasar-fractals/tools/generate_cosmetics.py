"""Génère les cosmétiques de la saison 1 des fractales (étape 9 du GDD, docs/fractales/gdd.md).

    python3 mods/nakasar-fractals/tools/generate_cosmetics.py

Trois pièces d'apparence, sans protection (armure à 0, comme les tenues du mod Vampires), vendues par l'Archiviste
contre des éclats de Brume (tools/generate_progression.py lit PRICES) et rares dans le coffre des fractales du jour :
- Armor_Nakasar_Fractal_Mist_Crown (tête) : la couronne royale du jeu, velours violet des Brumes ;
- Armor_Nakasar_Fractal_Archdiviner_Hood (tête) : la capuche à longue pointe du jeu, violette au liseré d'or ;
- Armor_Nakasar_Fractal_Mist_Mantle (torse) : la cape royale du jeu (sans col), drap indigo de l'Archidevin.

Écrit les objets (Server/Item/Items/Cosmetic/Nakasar/Fractals/) et la langue nakasar_fractals_cosmetics.lang. Les
modèles et icônes (Common/Items/Nakasar/Fractals/Cosmetics/<Nom>/) sont des cosmétiques vanilla recolorés par
tools/generate_vanilla_recolors.py (Kevin, 25 octobre 2026 : « vanilla d'abord »).
"""
import json
from pathlib import Path

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

# Objet, dossier, os, emplacement d'armure, cosmétiques masqués, qualité.
OUTFITS = [
    (CROWN, "Mist_Crown", "Head", ["HeadAccessory"], "Rare"),
    (HOOD, "Archdiviner_Hood", "Head", ["HeadAccessory", "Haircut", "EarAccessory"], "Epic"),
    (MANTLE, "Mist_Mantle", "Chest", ["Cape"], "Epic"),
]


def write_json(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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
        CROWN: ("Couronne des Brumes", "Cosmétique de la saison 1 des fractales : une couronne d'or sur un velours "
                "violet des Brumes. Aucune protection.", "Mist Crown", "Fractals season 1 cosmetic: a gold crown on "
                "Mist-violet velvet. No protection."),
        HOOD: ("Capuche de l'Archidevin", "Cosmétique de la saison 1 des fractales : la capuche à longue pointe du "
               "culte de la Falaise, liseré d'or. Aucune protection.", "Archdiviner's Hood",
               "Fractals season 1 cosmetic: the long-tipped hood of the Cliffside cult, gold trim. No protection."),
        MANTLE: ("Mantelet des Brumes", "Cosmétique de la saison 1 des fractales : la cape royale bordée de fourrure, "
                 "drap indigo de l'Archidevin. Aucune protection.", "Mist Mantle", "Fractals season 1 cosmetic: the "
                 "fur-trimmed royal cape in the Archdiviner's indigo. No protection."),
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
    for item_id, name, bone, hide, quality in OUTFITS:
        write_item(item_id, name, bone, hide, quality)
    fr, en = lang()
    write_lang(SERVER / "Languages/fr-FR" / f"{LANG}.lang", fr)
    write_lang(SERVER / "Languages/en-US" / f"{LANG}.lang", en)
    print(f"Cosmétiques : {len(OUTFITS)} pièces")


if __name__ == "__main__":
    main()
