#!/usr/bin/env python3
"""Génère les armes en argent : objets, recettes, textures, icônes et interactions de munitions.

    python3 mods/nakasar-vampires/tools/generate_silver_weapons.py ASSETS_ZIP [--preview FICHIER.png]

ASSETS_ZIP est l'Assets.zip du jeu (sous Windows :
%APPDATA%\\Hytale\\install\\release\\package\\game\\latest\\Assets.zip). Il n'est lu que pour les
textures, icônes et interactions vanilla à recopier ; le résultat est versionné, le script ne sert
qu'à le refaire (nouvelle arme, autre teinte, nouvelle version du jeu).

Chaque arme en argent hérite (Parent) de sa version en fer : mêmes attaques, mêmes dégâts de base,
même durabilité. Elle ne change que :
- l'apparence : texture et icône du fer repeintes en argent (seules les parties métalliques, grises,
  sont repeintes ; cuir, bois et tissu gardent leur couleur). L'épée reprend l'épée en acier argenté
  vanilla ;
- la recette, au Weapon_Bench, avec des lingots d'argent vanilla à la place des lingots de fer. Elle est
  écrite dans l'objet (et non dans Server/Item/Recipes) parce qu'un objet hérite de la recette de son
  parent : sans la sienne, l'arme en argent se fabriquerait avec du fer ;
- le tag « Material: Silver », que lit SilverDamageSystem (Java) pour doubler les dégâts contre les
  vampires (groupe de PNJ Nakasar_Vampires).

Munitions : l'arc et l'arbalète vanilla ne consomment que Weapon_Arrow_Crude (ModifyInventory, id exact).
L'arc et l'arbalète en argent tirent donc les flèches en argent : on recopie les interactions vanilla qui
retirent ou rendent une flèche, avec l'id de la flèche en argent.
"""
import colorsys
import io
import json
import sys
import zipfile
from pathlib import Path

from PIL import Image

PACK = Path(__file__).resolve().parent.parent / "src" / "main" / "resources"
COMMON = PACK / "Common"
SERVER = PACK / "Server"
TEXTURES = "Items/Weapons/Nakasar/Silver"
ICONS = "Icons/Items/Nakasar/Silver"
ITEMS = SERVER / "Item" / "Items" / "Weapon" / "Nakasar" / "Silver"
ROOTS = SERVER / "Item" / "RootInteractions" / "Nakasar" / "Silver"
INTERACTIONS = SERVER / "Item" / "Interactions" / "Nakasar" / "Silver"
LANG = "nakasar_silver"

CRUDE_ARROW = "Weapon_Arrow_Crude"
SILVER_ARROW = "Weapon_Nakasar_Arrow_Silver"
SILVER_BAR = "Ingredient_Bar_Silver"
SILVER_TAGS = {"Material": ["Silver"]}


def recipe(tab, inputs, time=3.5, quantity=1):
    out = {"TimeSeconds": time, "KnowledgeRequired": False, "Input": inputs,
           "BenchRequirement": [{"Type": "Crafting", "Id": "Weapon_Bench", "Categories": [tab]}]}
    if quantity > 1:
        out["OutputQuantity"] = quantity
    return out


def bars(silver, leather, linen=3):
    return [{"ItemId": SILVER_BAR, "Quantity": silver},
            {"ItemId": "Ingredient_Leather_Light", "Quantity": leather},
            {"ItemId": "Ingredient_Fabric_Scrap_Linen", "Quantity": linen}]


# id, parent, famille (tags), texture et icône vanilla à repeindre (None : gardées telles quelles),
# recette, nom français, nom anglais. Les onglets du Weapon_Bench sont Weapon_Sword, Mace, Battleaxe,
# Daggers et Bow : la hache et le gourdin vont avec la massue, l'épée longue et les lances avec l'épée.
WEAPONS = [
    ("Weapon_Nakasar_Sword_Silver", "Weapon_Sword_Iron", "Sword", None, None,
     recipe("Weapon_Sword", bars(6, 3)), "Épée en argent", "Silver Sword"),
    ("Weapon_Nakasar_Longsword_Silver", "Weapon_Longsword_Iron", "Longsword",
     "Items/Weapons/Longsword/Iron_Texture.png", "Icons/ItemsGenerated/Weapon_Longsword_Iron.png",
     recipe("Weapon_Sword", bars(6, 4)), "Épée longue en argent", "Silver Longsword"),
    ("Weapon_Nakasar_Axe_Silver", "Weapon_Axe_Iron", "Axe",
     "Items/Weapons/Axe/Iron_Texture.png", "Icons/ItemsGenerated/Weapon_Axe_Iron.png",
     recipe("Weapon_Mace", bars(4, 4)), "Hache en argent", "Silver Axe"),
    ("Weapon_Nakasar_Battleaxe_Silver", "Weapon_Battleaxe_Iron", "Battleaxe",
     "Items/Weapons/Battleaxe/Iron_Texture.png", "Icons/ItemsGenerated/Weapon_Battleaxe_Iron.png",
     recipe("Weapon_Battleaxe", bars(10, 4)), "Hache de combat en argent", "Silver Battleaxe"),
    ("Weapon_Nakasar_Mace_Silver", "Weapon_Mace_Iron", "Mace",
     "Items/Weapons/Mace/Iron_Texture.png", "Icons/ItemsGenerated/Weapon_Mace_Iron.png",
     recipe("Weapon_Mace", bars(10, 4)), "Massue en argent", "Silver Mace"),
    ("Weapon_Nakasar_Club_Silver", "Weapon_Club_Iron", "Club",
     "Items/Weapons/Club/Iron_default.png", "Icons/ItemsGenerated/Weapon_Club_Iron.png",
     recipe("Weapon_Mace", bars(4, 4)), "Gourdin en argent", "Silver Club"),
    ("Weapon_Nakasar_Daggers_Silver", "Weapon_Daggers_Iron", "Dagger",
     "Items/Weapons/Dagger/Iron_Texture.png", "Icons/ItemsGenerated/Weapon_Daggers_Iron.png",
     recipe("Weapon_Daggers", bars(4, 2)), "Dagues en argent", "Silver Daggers"),
    ("Weapon_Nakasar_Javelin_Silver", "Weapon_Spear_Iron", "Spear",
     "Items/Weapons/Spear/Iron_Texture.png", "Icons/ItemsGenerated/Weapon_Spear_Iron.png",
     recipe("Weapon_Sword", [{"ItemId": SILVER_BAR, "Quantity": 2}, {"ResourceTypeId": "Wood_Trunk", "Quantity": 1}],
            time=2, quantity=4), "Lance de jet en argent", "Silver Throwing Spear"),
    ("Weapon_Nakasar_Spear_Silver", "Weapon_Nakasar_Spear_Iron", "Spear",
     "Items/Weapons/Spear/Iron_Texture.png", "Icons/ItemsGenerated/Weapon_Spear_Iron.png",
     recipe("Weapon_Sword", [{"ItemId": SILVER_BAR, "Quantity": 4}, {"ResourceTypeId": "Wood_Trunk", "Quantity": 2},
                             {"ItemId": "Ingredient_Leather_Light", "Quantity": 2}]),
     "Lance d'argent à deux mains", "Two-Handed Silver Spear"),
    ("Weapon_Nakasar_Shortbow_Silver", "Weapon_Shortbow_Iron", "Bow",
     "Items/Weapons/Bow/Iron_Texture.png", "Icons/ItemsGenerated/Weapon_Bow_Iron.png",
     recipe("Weapon_Bow", bars(6, 2)), "Arc en argent", "Silver Shortbow"),
    ("Weapon_Nakasar_Crossbow_Silver", "Weapon_Crossbow_Iron", "Crossbow",
     "Items/Weapons/Crossbow/Iron_Texture.png", "Icons/ItemsGenerated/Weapon_Crossbow_Iron.png",
     recipe("Weapon_Bow", bars(6, 4)), "Arbalète de poing en argent", "Silver Hand Crossbow"),
    ("Weapon_Nakasar_Blunderbuss_Silver", "Weapon_Gun_Blunderbuss", "Gun",
     "Items/Weapons/Gun/Blunderbuss_Texture.png", "Icons/ItemsGenerated/Weapon_Gun_Blunderbuss.png",
     recipe("Weapon_Bow", [{"ItemId": SILVER_BAR, "Quantity": 8}, {"ItemId": "Ingredient_Bar_Iron", "Quantity": 4},
                           {"ResourceTypeId": "Wood_Trunk", "Quantity": 2}], time=5), "Tromblon en argent", "Silver Blunderbuss"),
    ("Weapon_Nakasar_Arrow_Silver", "Weapon_Arrow_Iron", "Arrow",
     "Items/Weapons/Arrow/Iron_Texture.png", "Icons/ItemsGenerated/Weapon_Arrow_Iron.png",
     recipe("Weapon_Bow", [{"ItemId": CRUDE_ARROW, "Quantity": 8}, {"ItemId": SILVER_BAR, "Quantity": 1}],
            time=1, quantity=8), "Flèche en argent", "Silver Arrow"),
]

DESCRIPTIONS = {
    "fr": "Inflige le double de dégâts aux vampires (Comte, Comtesse, rejetons).",
    "en": "Deals double damage to vampires (Count, Countess, spawns).",
}
AMMO_NOTE = {
    "fr": " Tire des flèches en argent.",
    "en": " Shoots silver arrows.",
}
ARROW_DESCRIPTION = {
    "fr": "Munition de l'arc et de l'arbalète en argent. Lancée ou en main, double dégâts contre les vampires.",
    "en": "Ammunition for the silver shortbow and crossbow. Thrown or in hand, double damage against vampires.",
}


def silver(image):
    """Repeint en argent les pixels métalliques (peu saturés) ; laisse le reste (cuir, bois, tissu)."""
    image = image.convert("RGBA")
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if s > 0.28:
                continue
            # Métal plus clair et plus contrasté, reflet froid légèrement bleuté.
            v = min(1.0, 0.22 + 0.9 * v ** 0.85)
            rr, gg, bb = v * 0.93, v * 0.96, v * 1.0
            pixels[x, y] = (round(rr * 255), round(gg * 255), round(min(1.0, bb) * 255), a)
    return image


def replace_arrow(value):
    if isinstance(value, dict):
        return {k: replace_arrow(v) for k, v in value.items()}
    if isinstance(value, list):
        return [replace_arrow(v) for v in value]
    return SILVER_ARROW if value == CRUDE_ARROW else value


def rename(value, names):
    if isinstance(value, dict):
        return {k: rename(v, names) for k, v in value.items()}
    if isinstance(value, list):
        return [rename(v, names) for v in value]
    return names.get(value, value)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    assets = zipfile.ZipFile(sys.argv[1])
    preview = sys.argv[sys.argv.index("--preview") + 1] if "--preview" in sys.argv else None

    def vanilla_json(path):
        return json.loads(assets.read("Server/" + path))

    def vanilla_png(path):
        return Image.open(io.BytesIO(assets.read("Common/" + path)))

    # Interactions de munitions recopiées avec la flèche en argent.
    names = {
        "Weapon_Shortbow_Primary_Shoot": "Nakasar_Silver_Shortbow_Primary_Shoot",
        "Weapon_Crossbow_Swap_From": "Nakasar_Silver_Crossbow_Swap_From",
    }
    copies = [
        (INTERACTIONS / "Nakasar_Silver_Shortbow_Primary_Shoot.json",
         "Item/Interactions/Weapons/Shortbow/Primary/Shoot/Weapon_Shortbow_Primary_Shoot.json"),
        (ROOTS / "Root_Nakasar_Silver_Shortbow_Primary_Shoot.json",
         "Item/RootInteractions/Weapons/Shortbow/Root_Weapon_Shortbow_Primary_Shoot.json"),
        (ROOTS / "Root_Nakasar_Silver_Shortbow_Secondary_Guard.json",
         "Item/RootInteractions/Weapons/Shortbow/Root_Weapon_Shortbow_Secondary_Guard.json"),
        (INTERACTIONS / "Nakasar_Silver_Crossbow_Swap_From.json",
         "Item/Interactions/Weapons/Crossbow/Weapon_Crossbow_Swap_From.json"),
        (ROOTS / "Root_Nakasar_Silver_Crossbow_Swap_From.json",
         "Item/RootInteractions/Weapons/Crossbow/Root_Weapon_Crossbow_Swap_From.json"),
    ]
    for target, source in copies:
        write_json(target, rename(replace_arrow(vanilla_json(source)), names))

    # Un objet qui déclare Interactions remplace la table de son parent (des objets vanilla écrivent
    # « Interactions: {} » pour en retirer) : on écrit donc les tables entières, celles du modèle vanilla
    # complétées par l'arme en fer, avec la flèche en argent.
    def full_tables(template_path, iron_path, interactions):
        template = vanilla_json(template_path)
        iron = vanilla_json(iron_path)
        variables = {**template.get("InteractionVars", {}), **iron.get("InteractionVars", {})}
        table = {**template["Interactions"], **iron.get("Interactions", {}), **interactions}
        return {"Interactions": replace_arrow(table), "InteractionVars": replace_arrow(variables)}

    overrides = {
        "Weapon_Nakasar_Shortbow_Silver": full_tables(
            "Item/Items/Weapon/Shortbow/Template_Weapon_Shortbow.json", "Item/Items/Weapon/Shortbow/Weapon_Shortbow_Iron.json",
            {"Primary": "Root_Nakasar_Silver_Shortbow_Primary_Shoot",
             "Secondary": "Root_Nakasar_Silver_Shortbow_Secondary_Guard"}),
        "Weapon_Nakasar_Crossbow_Silver": full_tables(
            "Item/Items/Weapon/Crossbow/Template_Weapon_Crossbow.json", "Item/Items/Weapon/Crossbow/Weapon_Crossbow_Iron.json",
            {"SwapFrom": "Root_Nakasar_Silver_Crossbow_Swap_From"}),
    }

    lang = {"fr": [f"# Armes en argent — textes français (générés par tools/generate_silver_weapons.py)"],
            "en": [f"# Silver weapons — English texts (generated by tools/generate_silver_weapons.py)"]}
    tiles = []
    for item_id, parent, family, texture, icon, item_recipe, name_fr, name_en in WEAPONS:
        item = {
            "Parent": parent,
            "TranslationProperties": {
                "Name": f"{LANG}.items.{item_id}.name",
                "Description": f"{LANG}.items.{item_id}.description",
            },
            "Quality": "Rare",
            "ItemLevel": 25,
            "Tags": {"Type": ["Weapon"], "Family": [family], **SILVER_TAGS},
            "Recipe": item_recipe,
        }
        if texture is None:
            item["Model"] = "Items/Weapons/Sword/Silversteel.blockymodel"
            item["Texture"] = "Items/Weapons/Sword/Silversteel_Texture.png"
            item["Icon"] = "Icons/ItemsGenerated/Weapon_Sword_Silversteel.png"
        else:
            stem = item_id.removeprefix("Weapon_Nakasar_")
            texture_path = f"{TEXTURES}/{stem}_Texture.png"
            icon_path = f"{ICONS}/{item_id}.png"
            painted = silver(vanilla_png(texture))
            (COMMON / texture_path).parent.mkdir(parents=True, exist_ok=True)
            painted.save(COMMON / texture_path)
            painted_icon = silver(vanilla_png(icon))
            (COMMON / icon_path).parent.mkdir(parents=True, exist_ok=True)
            painted_icon.save(COMMON / icon_path)
            item["Texture"] = texture_path
            item["Icon"] = icon_path
            tiles.append((vanilla_png(icon).convert("RGBA"), painted_icon))
        for key, value in overrides.get(item_id, {}).items():
            item[key] = value
        write_json(ITEMS / f"{item_id}.json", item)

        for language, name in (("fr", name_fr), ("en", name_en)):
            if item_id == SILVER_ARROW:
                description = ARROW_DESCRIPTION[language]
            else:
                description = DESCRIPTIONS[language]
                if item_id in overrides:
                    description += AMMO_NOTE[language]
            lang[language].append(f"items.{item_id}.name = {name}")
            lang[language].append(f"items.{item_id}.description = {description}")

    for language, folder in (("fr", "fr-FR"), ("en", "en-US")):
        path = SERVER / "Languages" / folder / f"{LANG}.lang"
        path.write_text("\n".join(lang[language]) + "\n", encoding="utf-8")

    if preview:
        # Icônes vanilla (en haut) et en argent (en bas), pour vérifier la teinte.
        size = 64
        sheet = Image.new("RGBA", (size * len(tiles), size * 2), (40, 40, 48, 255))
        for i, (before, after) in enumerate(tiles):
            sheet.alpha_composite(before.resize((size, size)), (i * size, 0))
            sheet.alpha_composite(after.resize((size, size)), (i * size, size))
        sheet.save(preview)
    print(f"{len(WEAPONS)} armes, {len(copies)} interactions de munitions")


if __name__ == "__main__":
    main()
