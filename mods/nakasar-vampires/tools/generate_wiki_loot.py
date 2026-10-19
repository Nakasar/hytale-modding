#!/usr/bin/env python3
"""Écrit la page du wiki joueur qui détaille le butin des coffres du Comté Vampire.

    python3 mods/nakasar-vampires/tools/generate_wiki_loot.py

Lit les listes Server/Drops/Nakasar/Halloween/*.json (produites par generate_loot.py) et écrit
docs/wiki/fragment/butin-des-coffres.md. À relancer après chaque changement de generate_loot.py.
Les noms français des objets vanilla sont des traductions d'usage, l'id du jeu est donné à côté.
"""
import json
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DROPS = ROOT / "mods" / "nakasar-vampires" / "src" / "main" / "resources" / "Server" / "Drops" / "Nakasar" / "Halloween"
OUT = ROOT / "docs" / "wiki" / "fragment" / "butin-des-coffres.md"

# Ordre de la page : (titre, liste, où).
TABLES = [
    ("Trésor du manoir", "Nakasar_Loot_Manor_Treasure", "[Manoir du Comte](manoir-du-comte.md), crypte"),
    ("Chambre du manoir", "Nakasar_Loot_Manor_Bedroom", "[Manoir du Comte](manoir-du-comte.md), chambres du comte et de la comtesse"),
    ("Alchimie du manoir", "Nakasar_Loot_Manor_Alchemy", "[Manoir du Comte](manoir-du-comte.md), laboratoire"),
    ("Bibliothèque du manoir", "Nakasar_Loot_Manor_Library", "[Manoir du Comte](manoir-du-comte.md), bibliothèque"),
    ("Atelier du manoir", "Nakasar_Loot_Manor_Workshop", "[Manoir du Comte](manoir-du-comte.md), atelier"),
    ("Cuisine du manoir", "Nakasar_Loot_Manor_Kitchen", "[Manoir du Comte](manoir-du-comte.md), cuisine"),
    ("Quartiers du capitaine", "Nakasar_Loot_Guard_Captain", "[Poste de garde](postes-de-garde.md)"),
    ("Armurerie", "Nakasar_Loot_Guard_Armory", "[Poste de garde](postes-de-garde.md)"),
    ("Caserne", "Nakasar_Loot_Guard_Barracks", "[Poste de garde](postes-de-garde.md)"),
    ("Ruines du château", "Nakasar_Loot_Castle_Ruins", "[Château hanté](chateaux-hantes.md), chambre du donjon"),
    ("Crypte", "Nakasar_Loot_Crypt", "[Crypte](cryptes.md), salle funéraire"),
    ("Maison du notable", "Nakasar_Loot_Village_Rich", "[Village](villages.md), maison du notable"),
    ("Maison du village", "Nakasar_Loot_Village_House", "[Village](villages.md), 9 coffres"),
    ("Ferme", "Nakasar_Loot_Farm", "[Fermes](fermes.md) (zombies, en ruine) et [champs de citrouilles](champs-de-citrouilles.md)"),
    ("Ferme incendiée", "Nakasar_Loot_Farm_Burnt", "[Ferme](fermes.md) incendiée"),
    ("Camp de chasseurs", "Nakasar_Loot_Hunter_Camp", "[Camp de chasseurs](camps-de-chasseurs.md), tente ou pavillon"),
    ("Armurerie des chasseurs", "Nakasar_Loot_Hunter_Armory", "[Camp de chasseurs](camps-de-chasseurs.md), atelier"),
]

NAMES = {
    "Armor_Iron_Chest": "Plastron en fer", "Armor_Iron_Hands": "Gants en fer", "Armor_Iron_Head": "Casque en fer",
    "Armor_Iron_Legs": "Jambières en fer", "Armor_Leather_Medium_Chest": "Plastron en cuir",
    "Armor_Leather_Medium_Head": "Casque en cuir", "Armor_Leather_Raven_Chest": "Plastron de corbeau",
    "Armor_Leather_Raven_Head": "Capuche de corbeau", "Armor_Leather_Soft_Chest": "Tunique en cuir souple",
    "Armor_Leather_Soft_Head": "Capuche en cuir souple", "Armor_Steel_Ancient_Chest": "Plastron en acier ancien",
    "Container_Bucket": "Seau", "Food_Bread": "Pain", "Food_Cheese": "Fromage", "Food_Kebab_Meat": "Brochette de viande",
    "Food_Pie_Apple": "Tarte aux pommes", "Food_Pie_Meat": "Tourte à la viande", "Food_Salad_Mushroom": "Salade de champignons",
    "Food_Vegetable_Cooked": "Légumes cuits", "Food_Wildmeat_Cooked": "Gibier cuit",
    "Ingredient_Bar_Copper": "Lingot de cuivre", "Ingredient_Bar_Gold": "Lingot d'or", "Ingredient_Bar_Iron": "Lingot de fer",
    "Ingredient_Bar_Silver": "**Lingot d'argent**", "Ingredient_Bolt_Shadoweave": "Rouleau de tisse-ombre",
    "Ingredient_Bolt_Silk": "Rouleau de soie", "Ingredient_Bolt_Wool": "Rouleau de laine",
    "Ingredient_Bone_Fragment": "Fragment d'os", "Ingredient_Charcoal": "Charbon de bois",
    "Ingredient_Crystal_Purple": "Cristal violet", "Ingredient_Crystal_Red": "Cristal rouge", "Ingredient_Dough": "Pâte",
    "Ingredient_Fabric_Scrap_Linen": "Chute de lin", "Ingredient_Fabric_Scrap_Silk": "Chute de soie",
    "Ingredient_Fabric_Scrap_Wool": "Chute de laine", "Ingredient_Fibre": "Fibre", "Ingredient_Flour": "Farine",
    "Ingredient_Leather_Dark": "Cuir sombre", "Ingredient_Leather_Light": "Cuir léger", "Ingredient_Leather_Medium": "Cuir moyen",
    "Ingredient_Life_Essence": "Essence de vie", "Ingredient_Rune_Shard": "**Éclat de rune**", "Ingredient_Salt": "Sel",
    "Ingredient_Spices": "Épices", "Ingredient_Stick": "Bâton",
    "Plant_Crop_Carrot_Item": "Carotte", "Plant_Crop_Onion_Item": "Oignon", "Plant_Crop_Potato_Item": "Pomme de terre",
    "Plant_Crop_Pumpkin_Item": "Citrouille", "Plant_Crop_Wheat_Item": "Blé", "Plant_Fruit_Apple": "Pomme",
    "Plant_Fruit_Poison": "Fruit empoisonné", "Plant_Seeds_Carrot": "Graines de carotte", "Plant_Seeds_Onion": "Graines d'oignon",
    "Plant_Seeds_Potato": "Plant de pomme de terre", "Plant_Seeds_Pumpkin": "Graines de citrouille", "Plant_Seeds_Wheat": "Graines de blé",
    "Potion_Antidote": "Antidote", "Potion_Empty": "Fiole vide", "Potion_Health": "Potion de soin",
    "Potion_Health_Lesser": "Potion de soin mineure", "Potion_Mana": "Potion de mana", "Potion_Poison": "Potion de poison",
    "Potion_Regen_Health": "Potion de régénération", "Potion_Stamina_Lesser": "Potion d'endurance mineure",
    "Recipe_Food_Pie_Meat": "Recette : tourte à la viande", "Recipe_Food_Pie_Pumpkin": "Recette : tarte à la citrouille",
    "Recipe_Page": "Page de recette", "Recipe_Plant_Seeds_Health1": "Recette : graines de soin",
    "Recipe_Plant_Seeds_Mana1": "Recette : graines de mana", "Recipe_Plant_Seeds_Stamina1": "Recette : graines d'endurance",
    "Rock_Gem_Diamond": "Diamant", "Rock_Gem_Emerald": "Émeraude", "Rock_Gem_Ruby": "Rubis", "Rock_Gem_Sapphire": "Saphir",
    "Rock_Gem_Topaz": "Topaze", "Rock_Gem_Voidstone": "Pierre du Vide",
    "Tool_Feedbag": "Musette", "Tool_Fertilizer": "Engrais", "Tool_Hammer_Iron": "Marteau en fer", "Tool_Hoe_Copper": "Houe en cuivre",
    "Tool_Hoe_Crude": "Houe grossière", "Tool_Map": "Carte", "Tool_Repair_Kit_Crude": "Kit de réparation grossier",
    "Tool_Repair_Kit_Iron": "Kit de réparation en fer", "Tool_Shovel_Crude": "Pelle grossière", "Tool_Sickle_Copper": "Faucille en cuivre",
    "Weapon_Arrow_Crude": "Flèche grossière", "Weapon_Arrow_Iron": "Flèche en fer", "Weapon_Axe_Iron_Rusty": "Hache en fer rouillée",
    "Weapon_Battleaxe_Steel_Rusty": "Hache de bataille rouillée", "Weapon_Club_Iron_Rusty": "Gourdin en fer rouillé",
    "Weapon_Crossbow_Iron": "Arbalète en fer", "Weapon_Daggers_Bone": "Dagues en os", "Weapon_Daggers_Doomed": "Dagues maudites",
    "Weapon_Daggers_Iron": "Dagues en fer", "Weapon_Longsword_Iron": "Épée longue en fer",
    "Weapon_Longsword_Spectral": "**Épée longue spectrale**", "Weapon_Shield_Rusty": "Bouclier rouillé",
    "Weapon_Shortbow_Iron_Rusty": "Arc court en fer rouillé", "Weapon_Shortbow_Vampire": "**Arc court vampirique**",
    "Weapon_Spear_Iron": "Lance en fer", "Weapon_Spellbook_Grimoire_Brown": "Grimoire brun",
    "Weapon_Spellbook_Grimoire_Purple": "Grimoire violet", "Weapon_Sword_Bone": "Épée en os",
    "Weapon_Sword_Silversteel": "**Épée en acier d'argent**", "Weapon_Sword_Steel": "Épée en acier",
    "Weapon_Sword_Steel_Rusty": "Épée en acier rouillée",
}

# Notes de lore (generate_lore.py) : leur titre français, lien vers la page des notes.
import generate_lore as _lore  # noqa: E402
for _name, (_style, _title, *_rest) in _lore.LORE.items():
    NAMES[_lore.note_id(_name)] = f"Note : [{_title}](notes-et-epitaphes.md)"


def anchor(title):
    # Ancre explicite sans accents ({#...} de Docusaurus), stable quel que soit le moteur.
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    return ascii_title.lower().replace(" ", "-").replace("'", "")


def rolls(lo, hi):
    if lo == hi:
        return f"{lo} fois" if lo > 1 else "1 fois"
    return f"{lo} à {hi} fois"


def qty(item):
    lo, hi = item.get("QuantityMin", 1), item.get("QuantityMax", 1)
    return str(lo) if lo == hi else f"{lo} à {hi}"


def table(drop):
    lines = []
    for i, choice in enumerate(drop["Container"]["Containers"], 1):
        entries = choice["Containers"]
        total = sum(e.get("Weight", 1) for e in entries)
        lines.append(f"**Tirage {i}** ({rolls(choice.get('RollsMin', 1), choice.get('RollsMax', 1))})")
        lines.append("")
        lines.append("| Objet | Quantité | Chance par tirage |")
        lines.append("|---|---|---|")
        for e in sorted(entries, key=lambda e: -e.get("Weight", 1)):
            pct = f"{round(100 * e.get('Weight', 1) / total)} %"
            if e["Type"] == "Empty":
                lines.append(f"| *rien* | | {pct} |")
            else:
                item = e["Item"]
                name = NAMES.get(item["ItemId"], item["ItemId"])
                lines.append(f"| {name} (`{item['ItemId']}`) | {qty(item)} | {pct} |")
        lines.append("")
    return lines


def main():
    out = [
        "# Butin des coffres",
        "",
        "{/* Page générée par mods/nakasar-vampires/tools/generate_wiki_loot.py : ne pas modifier à la main. */}",
        "",
        "Chaque coffre du Comté est rempli à l'apparition de la structure. Son contenu se compose de plusieurs "
        "**tirages** : chacun est fait un nombre de fois aléatoire, et à chaque fois un objet est choisi "
        "selon sa chance. Les noms des objets du jeu de base sont des traductions d'usage ; l'id exact est "
        "indiqué entre parenthèses.",
        "",
        "| Coffre | Où |",
        "|---|---|",
    ]
    out += [f"| [{t}](#{anchor(t)}) | {where} |" for t, _, where in TABLES]
    out.append("")
    for title, drop_id, where in TABLES:
        drop = json.loads((DROPS / f"{drop_id}.json").read_text(encoding="utf-8"))
        out += [f"## {title} {{#{anchor(title)}}}", "", f"{where} · liste `{drop_id}`", ""]
        out += table(drop)
    OUT.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    print(f"{OUT} écrit ({len(TABLES)} coffres)")


if __name__ == "__main__":
    main()
