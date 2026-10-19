#!/usr/bin/env python3
"""Génère les listes de butin des coffres du Fragment halloween (Server/Drops/Nakasar/Halloween).

    python3 mods/nakasar-vampires/tools/generate_loot.py

Chaque coffre posé par generate_prefabs.py porte un composant ItemContainerBlock qui nomme une de
ces listes ; le serveur le remplit à la pose du prefab. Même forme que les coffres du jeu
(Server/Drops/Prefabs/Zone1_Encounters_Tier2.json) : un conteneur « Multiple » de tirages
« Choice », chacun tirant entre RollsMin et RollsMax objets pondérés. Une entrée None est un
tirage vide (le coffre reste plus pauvre).

Butin du domaine du Comte : objets du quotidien dans les fermes et le village, équipement de fer
rouillé au poste de garde, ingrédients d'alchimie, livres et trésor au manoir. Les identifiants
sont ceux du jeu 0.7.2 (Server/Item/Items d'Assets.zip, lus le 2026-10-18).
"""

import json
from pathlib import Path

import generate_lore as lore

OUT = Path(__file__).resolve().parent.parent / "src" / "main" / "resources" / "Server" / "Drops" / "Nakasar" / "Halloween"

# (objet, poids, quantité min, quantité max) ; objet None = tirage vide.
FOOD = [("Food_Bread", 4, 1, 3), ("Food_Cheese", 3, 1, 2), ("Plant_Fruit_Apple", 3, 2, 5),
        ("Food_Pie_Meat", 1, 1, 1), ("Food_Vegetable_Cooked", 2, 1, 2), ("Food_Wildmeat_Cooked", 2, 1, 2)]
CROPS = [("Plant_Crop_Wheat_Item", 4, 2, 6), ("Plant_Crop_Potato_Item", 3, 2, 5), ("Plant_Crop_Carrot_Item", 3, 2, 5),
         ("Plant_Crop_Pumpkin_Item", 2, 1, 3), ("Plant_Crop_Onion_Item", 2, 1, 4)]
SEEDS = [("Plant_Seeds_Wheat", 4, 2, 5), ("Plant_Seeds_Potato", 2, 1, 3), ("Plant_Seeds_Carrot", 2, 1, 3),
         ("Plant_Seeds_Pumpkin", 2, 1, 3), ("Plant_Seeds_Onion", 1, 1, 3)]
FARM_TOOLS = [("Tool_Hoe_Crude", 3, 1, 1), ("Tool_Hoe_Copper", 1, 1, 1), ("Tool_Sickle_Copper", 1, 1, 1),
              ("Tool_Shovel_Crude", 2, 1, 1), ("Container_Bucket", 2, 1, 1), ("Tool_Feedbag", 1, 1, 1),
              ("Tool_Fertilizer", 2, 1, 3)]
HOUSEHOLD = [("Ingredient_Fabric_Scrap_Linen", 4, 1, 4), ("Ingredient_Fabric_Scrap_Wool", 3, 1, 3),
             ("Ingredient_Fibre", 3, 2, 6), ("Ingredient_Stick", 3, 2, 5), ("Ingredient_Charcoal", 2, 1, 4),
             ("Ingredient_Flour", 2, 1, 3), ("Ingredient_Salt", 1, 1, 2), ("Ingredient_Leather_Light", 1, 1, 2)]
BURNT = [("Ingredient_Charcoal", 6, 2, 8), ("Ingredient_Bone_Fragment", 2, 1, 3), ("Ingredient_Stick", 2, 1, 3),
         ("Plant_Seeds_Wheat", 2, 1, 3), (None, 4, 0, 0)]
RUSTY_WEAPONS = [("Weapon_Sword_Steel_Rusty", 3, 1, 1), ("Weapon_Axe_Iron_Rusty", 3, 1, 1),
                 ("Weapon_Club_Iron_Rusty", 2, 1, 1), ("Weapon_Shield_Rusty", 3, 1, 1),
                 ("Weapon_Shortbow_Iron_Rusty", 2, 1, 1), ("Weapon_Spear_Iron", 1, 1, 1),
                 ("Weapon_Battleaxe_Steel_Rusty", 1, 1, 1), ("Weapon_Crossbow_Iron", 1, 1, 1)]
GUARD_SUPPLIES = [("Weapon_Arrow_Iron", 4, 4, 12), ("Weapon_Arrow_Crude", 3, 6, 16), ("Tool_Repair_Kit_Iron", 2, 1, 1),
                  ("Ingredient_Bar_Iron", 3, 1, 3), ("Ingredient_Leather_Medium", 2, 1, 3), ("Potion_Health_Lesser", 3, 1, 2),
                  ("Potion_Stamina_Lesser", 2, 1, 2)]
IRON_ARMOR = [("Armor_Iron_Head", 2, 1, 1), ("Armor_Iron_Chest", 1, 1, 1), ("Armor_Iron_Hands", 2, 1, 1),
              ("Armor_Iron_Legs", 2, 1, 1), ("Armor_Leather_Medium_Chest", 2, 1, 1), ("Armor_Leather_Medium_Head", 2, 1, 1)]
VALUABLES = [("Ingredient_Bar_Silver", 3, 1, 3), ("Ingredient_Bar_Gold", 2, 1, 2), ("Rock_Gem_Ruby", 2, 1, 2),
             ("Rock_Gem_Topaz", 2, 1, 2), ("Rock_Gem_Sapphire", 1, 1, 1), ("Rock_Gem_Emerald", 1, 1, 1)]
ALCHEMY = [("Potion_Empty", 4, 1, 4), ("Potion_Health", 3, 1, 2), ("Potion_Regen_Health", 2, 1, 1),
           ("Potion_Poison", 2, 1, 2), ("Potion_Antidote", 2, 1, 2), ("Potion_Mana", 2, 1, 2),
           ("Ingredient_Life_Essence", 4, 2, 6), ("Ingredient_Crystal_Red", 2, 1, 3), ("Ingredient_Crystal_Purple", 2, 1, 2),
           ("Plant_Fruit_Poison", 2, 1, 3), ("Ingredient_Bone_Fragment", 2, 2, 5), ("Ingredient_Rune_Shard", 2, 1, 2),
           ("Ingredient_Nakasar_Manor_Relic", 1, 1, 1)]
BOOKS = [("Recipe_Page", 5, 1, 2), ("Recipe_Food_Pie_Meat", 1, 1, 1), ("Recipe_Food_Pie_Pumpkin", 1, 1, 1),
         ("Recipe_Plant_Seeds_Health1", 1, 1, 1), ("Recipe_Plant_Seeds_Mana1", 1, 1, 1), ("Recipe_Plant_Seeds_Stamina1", 1, 1, 1),
         ("Weapon_Spellbook_Grimoire_Purple", 1, 1, 1), ("Weapon_Spellbook_Grimoire_Brown", 1, 1, 1), ("Tool_Map", 2, 1, 1)]
FINE_FOOD = [("Food_Pie_Meat", 3, 1, 2), ("Food_Pie_Apple", 3, 1, 2), ("Food_Cheese", 3, 1, 3), ("Food_Bread", 3, 2, 4),
             ("Food_Kebab_Meat", 2, 1, 3), ("Food_Salad_Mushroom", 1, 1, 2), ("Ingredient_Spices", 2, 1, 3)]
CLOTHES = [("Ingredient_Bolt_Silk", 3, 1, 3), ("Ingredient_Bolt_Wool", 3, 1, 3), ("Ingredient_Bolt_Shadoweave", 1, 1, 1),
           ("Ingredient_Fabric_Scrap_Silk", 3, 2, 5), ("Armor_Leather_Soft_Chest", 1, 1, 1), ("Armor_Leather_Soft_Head", 1, 1, 1)]
WORKSHOP = [("Ingredient_Bar_Iron", 4, 2, 5), ("Ingredient_Bar_Copper", 3, 2, 5), ("Ingredient_Bar_Silver", 2, 1, 3),
            ("Ingredient_Leather_Medium", 3, 1, 4), ("Ingredient_Leather_Dark", 1, 1, 2), ("Tool_Repair_Kit_Iron", 2, 1, 1),
            ("Tool_Hammer_Iron", 1, 1, 1), ("Ingredient_Charcoal", 3, 2, 6)]
CRYPT = [("Ingredient_Bone_Fragment", 6, 2, 6), ("Ingredient_Fabric_Scrap_Linen", 3, 1, 3), ("Rock_Gem_Topaz", 1, 1, 1),
         ("Ingredient_Bar_Silver", 1, 1, 2), ("Ingredient_Rune_Shard", 2, 1, 1), ("Weapon_Sword_Bone", 1, 1, 1),
         ("Weapon_Daggers_Bone", 1, 1, 1), ("Potion_Health_Lesser", 2, 1, 1)]
TREASURE = [("Ingredient_Bar_Gold", 4, 2, 5), ("Ingredient_Bar_Silver", 4, 2, 6), ("Rock_Gem_Ruby", 4, 1, 3),
            ("Rock_Gem_Diamond", 1, 1, 1), ("Rock_Gem_Emerald", 2, 1, 2), ("Rock_Gem_Sapphire", 2, 1, 2),
            ("Rock_Gem_Voidstone", 1, 1, 1), ("Ingredient_Nakasar_Manor_Relic", 3, 1, 2)]
TREASURE_GEAR = [("Weapon_Shortbow_Vampire", 2, 1, 1), ("Weapon_Sword_Silversteel", 2, 1, 1), ("Weapon_Longsword_Spectral", 1, 1, 1),
                 ("Weapon_Daggers_Doomed", 1, 1, 1), ("Armor_Steel_Ancient_Chest", 1, 1, 1), ("Armor_Leather_Raven_Chest", 2, 1, 1),
                 ("Armor_Leather_Raven_Head", 2, 1, 1)]
HUNTER_SUPPLIES = [("Weapon_Arrow_Iron", 5, 6, 16), ("Potion_Health_Lesser", 3, 1, 2), ("Potion_Health", 1, 1, 1),
                   ("Potion_Antidote", 2, 1, 2), ("Potion_Stamina_Lesser", 2, 1, 2), ("Ingredient_Bar_Silver", 3, 1, 3),
                   ("Ingredient_Leather_Medium", 2, 1, 3), ("Tool_Repair_Kit_Iron", 1, 1, 1)]
HUNTER_GEAR = [("Weapon_Crossbow_Iron", 3, 1, 1), ("Weapon_Sword_Silversteel", 1, 1, 1), ("Weapon_Daggers_Iron", 2, 1, 1),
               ("Armor_Leather_Raven_Head", 2, 1, 1), ("Armor_Leather_Raven_Chest", 1, 1, 1),
               ("Armor_Leather_Medium_Chest", 2, 1, 1), ("Armor_Leather_Medium_Head", 2, 1, 1)]

# Liste -> tirages : (rolls min, rolls max, entrées).
DROPLISTS = {
    "Nakasar_Loot_Farm": [(1, 3, CROPS), (1, 2, SEEDS), (0, 1, FARM_TOOLS + [(None, 6, 0, 0)]), (0, 2, FOOD)],
    "Nakasar_Loot_Farm_Burnt": [(1, 3, BURNT), (0, 1, [("Tool_Hoe_Crude", 1, 1, 1), (None, 3, 0, 0)])],
    "Nakasar_Loot_Village_House": [(1, 3, HOUSEHOLD), (1, 2, FOOD), (0, 1, CROPS + SEEDS),
                                   (0, 1, [("Potion_Health_Lesser", 2, 1, 1), ("Tool_Repair_Kit_Crude", 1, 1, 1), (None, 6, 0, 0)])],
    "Nakasar_Loot_Village_Rich": [(2, 3, HOUSEHOLD), (1, 2, FINE_FOOD), (1, 1, VALUABLES[:2] + [(None, 2, 0, 0)]),
                                  (0, 1, BOOKS[:3] + [(None, 3, 0, 0)])],
    "Nakasar_Loot_Guard_Barracks": [(1, 2, GUARD_SUPPLIES), (1, 2, FOOD), (0, 1, RUSTY_WEAPONS + [(None, 6, 0, 0)])],
    "Nakasar_Loot_Guard_Armory": [(1, 2, RUSTY_WEAPONS), (0, 1, IRON_ARMOR + [(None, 4, 0, 0)]), (1, 2, GUARD_SUPPLIES)],
    "Nakasar_Loot_Guard_Captain": [(1, 1, IRON_ARMOR), (1, 2, VALUABLES), (1, 2, GUARD_SUPPLIES),
                                   (0, 1, [("Weapon_Sword_Steel", 1, 1, 1), ("Weapon_Longsword_Iron", 2, 1, 1), (None, 3, 0, 0)])],
    "Nakasar_Loot_Crypt": [(1, 3, CRYPT)],
    "Nakasar_Loot_Castle_Ruins": [(1, 2, RUSTY_WEAPONS), (1, 2, VALUABLES), (0, 2, CRYPT)],
    "Nakasar_Loot_Manor_Treasure": [(2, 4, TREASURE), (1, 1, TREASURE_GEAR), (1, 2, ALCHEMY[1:4])],
    "Nakasar_Loot_Manor_Alchemy": [(2, 4, ALCHEMY), (0, 1, BOOKS[3:6] + [(None, 2, 0, 0)])],
    "Nakasar_Loot_Manor_Library": [(1, 3, BOOKS), (0, 1, ALCHEMY + [(None, 6, 0, 0)])],
    "Nakasar_Loot_Manor_Kitchen": [(2, 4, FINE_FOOD), (1, 2, CROPS), (0, 1, [("Ingredient_Salt", 2, 1, 4), ("Ingredient_Flour", 2, 2, 5),
                                                                         ("Ingredient_Dough", 1, 1, 3)])],
    "Nakasar_Loot_Manor_Bedroom": [(1, 3, CLOTHES), (1, 1, VALUABLES), (0, 1, [("Potion_Regen_Health", 1, 1, 1), ("Weapon_Daggers_Iron", 1, 1, 1),
                                                                              (None, 3, 0, 0)])],
    "Nakasar_Loot_Hunter_Camp": [(1, 3, HUNTER_SUPPLIES), (1, 2, [("Food_Wildmeat_Cooked", 3, 1, 3), ("Food_Bread", 3, 1, 3),
                                                                ("Food_Cheese", 1, 1, 2)]),
                                 (0, 1, HUNTER_GEAR + [(None, 8, 0, 0)])],
    "Nakasar_Loot_Hunter_Armory": [(2, 3, HUNTER_SUPPLIES), (1, 1, HUNTER_GEAR + [(None, 3, 0, 0)])],
    "Nakasar_Loot_Manor_Workshop": [(2, 3, WORKSHOP), (0, 1, IRON_ARMOR + RUSTY_WEAPONS[:3] + [(None, 6, 0, 0)])],
}

# Notes de lore (tools/generate_lore.py) : un tirage de plus, souvent vide, parmi les notes du lieu. Une note trouvée
# se lit dans l'infobulle de l'objet, ou en la posant puis en l'utilisant.
LORE_NOTES = {
    "Nakasar_Loot_Hunter_Camp": ("hunter", 4), "Nakasar_Loot_Hunter_Armory": ("hunter", 3),
    "Nakasar_Loot_Village_House": ("village", 6), "Nakasar_Loot_Village_Rich": ("village", 3),
    "Nakasar_Loot_Farm": ("farm", 6), "Nakasar_Loot_Farm_Burnt": ("farm", 4),
    "Nakasar_Loot_Guard_Barracks": ("guard", 5), "Nakasar_Loot_Guard_Captain": ("guard", 2),
    "Nakasar_Loot_Manor_Library": ("manor", 2), "Nakasar_Loot_Manor_Bedroom": ("manor", 4),
    "Nakasar_Loot_Manor_Alchemy": ("manor", 4), "Nakasar_Loot_Manor_Treasure": ("manor", 3),
}
for _name, (_place, _empty) in LORE_NOTES.items():
    DROPLISTS[_name] = DROPLISTS[_name] + [
        (0, 1, [(lore.note_id(n), 1, 1, 1) for n in lore.NOTES_BY_PLACE[_place]] + [(None, _empty, 0, 0)])]


def entry(item, weight, qmin, qmax):
    if item is None:
        return {"Type": "Empty", "Weight": weight}
    return {"Type": "Single", "Weight": weight, "Item": {"ItemId": item, "QuantityMin": qmin, "QuantityMax": qmax}}


def droplist(rolls):
    return {"Container": {"Type": "Multiple", "Containers": [
        {"Type": "Choice", "RollsMin": lo, "RollsMax": hi, "Containers": [entry(*e) for e in entries]}
        for lo, hi, entries in rolls]}}


def item_ids():
    return sorted({e[0] for rolls in DROPLISTS.values() for _, _, entries in rolls for e in entries if e[0]})


def main():
    if OUT.exists():
        for old in OUT.glob("*.json"):
            old.unlink()
    OUT.mkdir(parents=True, exist_ok=True)
    for name, rolls in DROPLISTS.items():
        (OUT / f"{name}.json").write_text(json.dumps(droplist(rolls), indent=2) + "\n", encoding="utf-8")
    print(f"{len(DROPLISTS)} listes de butin, {len(item_ids())} objets différents")


if __name__ == "__main__":
    main()
