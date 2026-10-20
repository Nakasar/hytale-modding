#!/usr/bin/env python3
"""Génère le butin de la Tour de l'Alchimiste (étape 8 du donjon).

    python3 mods/nakasar-vampires/tools/generate_alchemist_loot.py [--preview DOSSIER]

- La pierre philosophale (`Nakasar_Philosopher_Stone`) et son bloc posé sur le piédestal du Bureau
  (`Nakasar_Philosopher_Pedestal_Stone`) : chaque joueur y prend sa propre pierre une fois par instance (interaction Java
  `Nakasar_TakePhilosopherStone`), la pierre reste en place pour les autres. Elle sert au calice du rituel
  (generate_occult.py) ; d'autres recettes, côté chasseurs compris, viendront plus tard.
- Les sacs de l'Alchimiste (`Nakasar_Alchemist_Bag`, `Nakasar_Alchemist_Bag_Hard`) : AlchemistSystem en donne un à
  chaque joueur de l'instance à la mort du boss (le second en mode difficile), ouvert d'un clic droit comme les sacs de
  prime (`Nakasar_OpenBountyBag`). Contenu : les trois principes, des essences, deux éclats de rune, une chance d'objet
  unique, et en mode difficile une chance des lunettes de l'Alchimiste.
- Les objets uniques :
  - la fiole sans fond (`Potion_Nakasar_Bottomless_Flask`) : un grand soin qui ne se vide jamais, rechargé en 90 s
    (Cooldown de l'interaction racine) ;
  - les gants de l'Alchimiste (`Armor_Nakasar_Alchemist_Gloves`) : résistance aux éléments ; les fioles et bombes
    lancées par leur porteur volent 40 % plus loin (tower/AlchemistGlovesSystem.java) ;
  - la lanterne élémentaire (`Nakasar_Elemental_Lantern`) : tenue en main ou dans la main secondaire, sa lumière passe
    du feu au givre, à la foudre puis aux racines (tower/ElementalLanternSystem.java).
- Le cosmétique du mode difficile : les lunettes de l'Alchimiste (`Armor_Nakasar_Alchemist_Goggles`), sans protection,
  pièce du modèle du joueur sur l'os Head (verres violets cerclés de laiton, comme le masque du boss).
- Les potions des trois principes, à l'établi d'alchimie du jeu (onglet des potions de combat, niveau 2) : grand
  élixir de vie, philtre de garde élémentaire, élixir de vif-argent.
- Les listes de butin : sacs et coffres secrets de la tour (`Nakasar_Loot_Tower_Secret`, posés par alchemist_tower.py).

Textes : Server/Languages/*/nakasar_alchemist.lang (écrits à la main). Modèles : moteur de generate_assets.py (32 unités
= 1 bloc), sacs comme les sacs de prime (generate_trophies.py), lunettes comme la tenue de l'Alchimiste
(generate_alchemist_models.py, 64 unités = 1 bloc).
"""
import json
import sys
from pathlib import Path

from PIL import Image

import generate_alchemist_models as gam
import generate_altar as ga
import generate_assets as gx
import generate_occult as go
import generate_pumpkin_models as gpm
import generate_trophies as gt
from generate_pumpkin_models import Box, Joint, p_glow, p_round

PACK = Path(__file__).resolve().parent.parent / "src" / "main" / "resources"
COMMON = PACK / "Common"
SERVER = PACK / "Server"
ITEMS = SERVER / "Item/Items/Alchemist/Nakasar/Loot"
RECIPES = SERVER / "Item/Recipes/Nakasar/Alchemist"
INTERACTIONS = SERVER / "Item/Interactions/Nakasar/Alchemist/Loot"
ROOTS = SERVER / "Item/RootInteractions/Nakasar/Alchemist"
EFFECTS = SERVER / "Entity/Effects/Nakasar/Alchemist"
DROPS = SERVER / "Drops/Nakasar/Alchemist"
HITBOXES = SERVER / "Item/Block/Hitboxes/Nakasar"
MODELS = COMMON / "Items/Nakasar/Alchemist/Loot"
BLOCK_MODELS = COMMON / "Blocks/Nakasar/Alchemist"
ICONS = COMMON / "Icons/Items/Nakasar/Alchemist/Loot"
GOGGLES_DIR = COMMON / "Items/Nakasar/Alchemist/Goggles"
LANG = "nakasar_alchemist"

STONE = "Nakasar_Philosopher_Stone"
PEDESTAL_STONE = "Nakasar_Philosopher_Pedestal_Stone"
TAKE_STONE = "Nakasar_Take_Philosopher_Stone"
BAG = "Nakasar_Alchemist_Bag"
BAG_HARD = "Nakasar_Alchemist_Bag_Hard"
FLASK = "Potion_Nakasar_Bottomless_Flask"
GLOVES = "Armor_Nakasar_Alchemist_Gloves"
LANTERN = "Nakasar_Elemental_Lantern"
GOGGLES = "Armor_Nakasar_Alchemist_Goggles"
ELIXIR = "Potion_Nakasar_Grand_Elixir"
WARD = "Potion_Nakasar_Elemental_Ward"
QUICKSILVER = "Potion_Nakasar_Quicksilver_Draught"
SECRET = "Nakasar_Loot_Tower_Secret"
UNIQUES = (FLASK, GLOVES, LANTERN)

SALT = "Ingredient_Nakasar_Philosophers_Salt"
SULFUR = "Ingredient_Nakasar_Burning_Sulfur"
MERCURY = "Ingredient_Nakasar_Quicksilver"
SHARD = "Ingredient_Rune_Shard"
ESSENCES = ("Ingredient_Fire_Essence", "Ingredient_Ice_Essence", "Ingredient_Lightning_Essence", "Ingredient_Life_Essence")
FLASK_COOLDOWN = 90

GOLD = (212, 170, 72)
GOLD_DARK = (150, 112, 44)
GOLD_LIGHT = (250, 214, 120)
CRIMSON = (214, 28, 46)
CRIMSON_DEEP = (120, 8, 24)
GLASS = (196, 214, 222)
CORK = (150, 108, 70)
PURPLE = (150, 70, 220)
BRASS = (196, 150, 64)
IRON_DARK = (44, 40, 48)
ELEMENT_GLOWS = ((255, 120, 50), (140, 220, 255), (255, 232, 110), (130, 240, 100))


def glow(color):
    return gx.painter(color, glow=True)


def metal(color):
    return gx.painter(color, "iron")


# --- modèles (moteur de generate_assets : (nom, centre, taille, lacet, peintre, ombrage)) -------

def stone_parts(y0):
    """La pierre philosophale : gemme rouge à facettes tenue par quatre griffes d'or."""
    parts = [
        ("Core", (0, y0 + 5, 0), (6, 6, 6), 45, glow(CRIMSON), "fullbright"),
        ("Facet_Top", (0, y0 + 8.5, 0), (4, 2, 4), 0, glow(gx.mix(CRIMSON, (255, 200, 200), 0.35)), "fullbright"),
        ("Facet_Bottom", (0, y0 + 1.5, 0), (3.5, 2, 3.5), 0, glow(CRIMSON_DEEP), "fullbright"),
        ("Band", (0, y0 + 4, 0), (7, 1.5, 7), 0, metal(GOLD), "flat"),
    ]
    for k, (x, z) in enumerate(((-3, -3), (3, -3), (-3, 3), (3, 3))):
        parts.append((f"Claw_{k}", (x, y0 + 4.5, z), (1.2, 4, 1.2), 0, metal(GOLD_LIGHT), "flat"))
    return parts


def pedestal_stone_parts():
    """Bloc du piédestal : un petit berceau d'or et la pierre qui flotte au-dessus."""
    return [
        ("Cradle", (0, 1, 0), (12, 2, 12), 0, metal(GOLD_DARK), "flat"),
        ("Cradle_Top", (0, 2.5, 0), (8, 1, 8), 0, metal(GOLD), "flat"),
    ] + stone_parts(6)


def flask_parts():
    """Fiole sans fond : panse ronde violette qui luit, col d'or, bouchon scellé d'un rubis."""
    return [
        ("Body", (0, 5, 0), (9, 9, 9), 0, glow(PURPLE), "fullbright"),
        ("Body_Glass", (0, 5, 0), (10, 7, 10), 45, gx.painter(gx.mix(GLASS, PURPLE, 0.35), "iron"), "flat"),
        ("Collar", (0, 10.5, 0), (5, 1.5, 5), 0, metal(GOLD), "flat"),
        ("Neck", (0, 12.5, 0), (3, 3, 3), 0, gx.painter(GLASS, "iron"), "flat"),
        ("Cork", (0, 15, 0), (4, 2, 4), 0, gx.painter(CORK, "wood"), "flat"),
        ("Seal", (0, 16.5, 0), (2, 1, 2), 0, glow(CRIMSON), "fullbright"),
    ]


def lantern_parts():
    """Lanterne élémentaire : cage de laiton, quatre cristaux des éléments autour d'un cœur blanc."""
    parts = [
        ("Base", (0, 1, 0), (10, 2, 10), 0, metal(BRASS), "flat"),
        ("Top", (0, 15, 0), (10, 2, 10), 0, metal(BRASS), "flat"),
        ("Cap", (0, 17.5, 0), (5, 3, 5), 0, metal(gx.shade(BRASS, 0.8)), "flat"),
        ("Handle", (0, 21, 0), (6, 1.5, 1.5), 0, metal(IRON_DARK), "flat"),
        ("Core", (0, 8, 0), (3, 6, 3), 0, glow((255, 250, 240)), "fullbright"),
    ]
    for k, (x, z) in enumerate(((-2.5, 0), (2.5, 0), (0, -2.5), (0, 2.5))):
        parts.append((f"Crystal_{k}", (x, 8, z), (2, 8, 2), 0, glow(ELEMENT_GLOWS[k]), "fullbright"))
    for k, (x, z) in enumerate(((-4.5, -4.5), (4.5, -4.5), (-4.5, 4.5), (4.5, 4.5))):
        parts.append((f"Post_{k}", (x, 8, z), (1.5, 12, 1.5), 0, metal(BRASS), "flat"))
    return parts


def goggles():
    """Lunettes de l'Alchimiste sur l'os Head : les verres et la sangle du masque à bec, sans la plaque ni le bec."""
    dark = p_round(gam.LEATHER_DARK, (30, 18, 12), gam.LEATHER)
    brass = p_round(gam.BRASS, gam.BRASS_DARK, gam.BRASS_LIGHT)
    lens = gam.p_lens(gam.LENS, gam.LENS_DEEP)
    parts = [
        Box("StrapL", (15.6, 1.5, 2), (1.4, 3, 24), dark),
        Box("StrapR", (-15.6, 1.5, 2), (1.4, 3, 24), dark),
        Box("StrapBack", (0, 1.5, -14.6), (32.6, 3, 1.4), dark),
        Box("Bridge", (0, 0, 16.2), (6, 1.6, 1.4), brass),
    ]
    for side, x in (("L", 7.5), ("R", -7.5)):
        parts += [Box(f"Rim{side}", (x, 0, 15.4), (9, 9, 2.2), brass),
                  Box(f"Lens{side}", (x, 0, 16.7), (7, 7, 0.8), lens, shading="fullbright"),
                  Box(f"Side{side}", (x + (4.6 if x > 0 else -4.6), 0, 13.2), (1.2, 5, 4), dark)]
    return Joint("Head", (0, 0, 0), parts)


def write_gx_model(name, parts, folder, height, seed):
    atlas, uv = gx.build_atlas(parts, seed=seed, tex_w=64)
    folder.mkdir(parents=True, exist_ok=True)
    ICONS.mkdir(parents=True, exist_ok=True)
    atlas.save(folder / f"{name}.png")
    (folder / f"{name}.blockymodel").write_text(json.dumps(gx.build_model(name, parts, uv), indent=2) + "\n")
    scale = 256 / (height * 1.5)
    big = gx.render(parts, atlas, uv, 256, yaw=-35, pitch=26, scale=scale, center=(0, height / 2, 0))
    big.resize((64, 64), Image.LANCZOS).save(ICONS / f"{name}.png")
    return big


def write_ga_model(name, parts):
    """Objet au moteur de generate_altar (fioles de generate_occult), icône cadrée comme les objets occultes."""
    ga.PARTS = parts
    ga.TEX_W, ga.TEX_H = 64, 64
    atlas, uv = ga.build_atlas()
    MODELS.mkdir(parents=True, exist_ok=True)
    atlas.save(MODELS / f"{name}.png")
    model = ga.build_model(uv)
    model["nodes"][0]["name"] = name
    (MODELS / f"{name}.blockymodel").write_text(json.dumps(model, indent=2) + "\n")
    top = max(c[1] + s[1] / 2 for _, c, s, *_ in parts)
    span = max(max(s[0], s[2]) for _, c, s, *_ in parts)
    scale = min(200 / max(top, 1), 170 / max(span, 1))
    big = ga.render(atlas, uv, 256, yaw=-35, pitch=28, scale=scale, center=(0, top / 2, 0))
    big.resize((64, 64), Image.LANCZOS).save(ICONS / f"{name}.png")
    return big


def write_bag(name, tie, seed):
    ga.PARTS = gt.bag_parts(tie)
    ga.TEX_W, ga.TEX_H = 64, 64
    atlas, uv = ga.build_atlas()
    MODELS.mkdir(parents=True, exist_ok=True)
    atlas.save(MODELS / f"{name}.png")
    model = ga.build_model(uv)
    model["nodes"][0]["name"] = name
    (MODELS / f"{name}.blockymodel").write_text(json.dumps(model, indent=2) + "\n")
    big = ga.render(atlas, uv, 256, yaw=-30, pitch=20, scale=11.0, center=(0, 7, 0))
    big.resize((64, 64), Image.LANCZOS).save(ICONS / f"{name}.png")
    return big


def write_goggles(preview):
    root = goggles()
    atlas, uv = gpm.build_atlas(root, 91, 64)
    GOGGLES_DIR.mkdir(parents=True, exist_ok=True)
    atlas.save(GOGGLES_DIR / "Texture.png")
    doc = gpm.model_json(Joint("Goggles", (0, 0, 0), [root]), uv)
    nodes = doc["nodes"][0]["children"]
    for node in nodes:
        node["shape"]["settings"]["isPiece"] = True
    gpm.write_json(GOGGLES_DIR / "Goggles.blockymodel", {"nodes": nodes, "format": "character", "lod": "auto"})
    # Icône : les lunettes seules, de trois quarts face.
    icon = gpm.render(root, atlas, uv, {}, size=256, yaw=25, pitch=10, scale=5.0, center=(0, 0, 4))
    icon.resize((64, 64), Image.LANCZOS).save(ICONS / "Alchemist_Goggles.png")
    if preview:
        body = gam.mannequin([root, Joint("Chest", (0, 0, 0), []), Joint("Pelvis", (0, 0, 0), [])])
        atlas2, uv2 = gpm.build_atlas(body, 91, 128)
        gpm.render(body, atlas2, uv2, {}, size=360, yaw=20, pitch=8, scale=4.0, center=(0, 108, 0)).save(
            preview / "lunettes_face.png")


# --- définitions ----------------------------------------------------------------------------------

def names(item_id):
    return {"Name": f"{LANG}.items.{item_id}.name", "Description": f"{LANG}.items.{item_id}.description"}


def write(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def held_item(item_id, model, quality, stack, categories=("Items.Ingredients",), **extra):
    doc = {
        "TranslationProperties": names(item_id),
        "Icon": f"Icons/Items/Nakasar/Alchemist/Loot/{model}.png",
        "Model": f"Items/Nakasar/Alchemist/Loot/{model}.blockymodel",
        "Texture": f"Items/Nakasar/Alchemist/Loot/{model}.png",
        "Quality": quality,
        "ItemLevel": 30,
        "Categories": list(categories),
        "PlayerAnimationsId": "Item",
        "ItemSoundSetId": "ISS_Items_Gems",
        "MaxStack": stack,
    }
    doc.update(extra)
    return doc


# Animation de boisson des potions du jeu (Potion_Template, Assets.zip 0.7.2), comme generate_occult.py.
DRINK_ANIMATIONS = {"Parent": "Item", "Animations": {"Consume": {
    "FirstPerson": "Characters/Animations/Items/Main_Handed/Item/Attacks/Drink/Drink_FPS.blockyanim",
    "ThirdPerson": "Characters/Animations/Items/Main_Handed/Item/Attacks/Drink/Drink.blockyanim",
    "Speed": 1, "Looping": True}}}


def drink(interaction_id, effects, consume=True):
    """Boisson tenue 1,5 s (relâcher annule), puis les effets l'un après l'autre ; la fiole bue devient une fiole vide,
    sauf la fiole sans fond."""
    chain = {"Type": "ModifyInventory", "AdjustHeldItemQuantity": -1,
             "ItemToAdd": {"Id": "Potion_Empty", "Quantity": 1}} if consume else None
    for effect_id in reversed(effects):
        step = {"Type": "ApplyEffect", "EffectId": effect_id, "Entity": "User"}
        if chain:
            step["Next"] = chain
        chain = step
    write(INTERACTIONS / f"{interaction_id}.json", {
        "Type": "Charging",
        "FailOnDamage": False,
        "Effects": {"ItemAnimationId": "Consume", "WorldSoundEventId": "SFX_Nakasar_Drink",
                    "ClearAnimationOnFinish": True, "ClearSoundEventOnFinish": True},
        "HorizontalSpeedMultiplier": 0.75,
        "Next": {"1.5": chain},
        "Failed": {"Type": "Simple"},
    })


def potion(item_id, model, quality, effects, consume=True, cooldown=None, stack=10):
    root_id = f"Root_{item_id}"
    root = {"Interactions": [f"{item_id}_Drink"], "RequireNewClick": True}
    if cooldown:
        root["Cooldown"] = {"Id": item_id, "Cooldown": cooldown}
    write(ROOTS / f"{root_id}.json", root)
    drink(f"{item_id}_Drink", effects, consume)
    write(ITEMS / f"{item_id}.json", held_item(
        item_id, model, quality, stack, categories=("Items.Potions",), PlayerAnimationsId=DRINK_ANIMATIONS,
        Consumable=consume, Utility={"Compatible": False}, Interactions={"Secondary": root_id}))


def effect(effect_id, icon, duration, **fields):
    doc = {"Name": f"{LANG}.effects.{effect_id}", "Duration": duration, "OverlapBehavior": "Overwrite",
           "StatusEffectIcon": f"Icons/Items/Nakasar/Alchemist/Loot/{icon}.png"}
    doc.update(fields)
    write(EFFECTS / f"{effect_id}.json", doc)


def recipe(output, inputs, tier=2, seconds=3):
    write(RECIPES / f"Recipe_{output}.json", {
        "TimeSeconds": seconds,
        "KnowledgeRequired": False,
        "Input": [{"ItemId": i, "Quantity": q} for i, q in inputs],
        "PrimaryOutput": {"ItemId": output, "Quantity": 1},
        "Output": [{"ItemId": output, "Quantity": 1}],
        "BenchRequirement": [{"Type": "Crafting", "Id": "Alchemybench", "Categories": ["Alchemy_Potions"],
                              "RequiredTierLevel": tier}],
    })


def single(item, lo, hi=None, weight=None):
    doc = {"Type": "Single", "Item": {"ItemId": item, "QuantityMin": lo, "QuantityMax": hi or lo}}
    if weight is not None:
        doc["Weight"] = weight
    return doc


def chance(percent, container):
    return {"Type": "Choice", "Containers": [dict(container, Weight=percent), {"Type": "Empty", "Weight": 100 - percent}]}


def one_of(items, weight=None):
    doc = {"Type": "Choice", "Containers": [single(i, 1, 1, 1) for i in items]}
    if weight is not None:
        doc["Weight"] = weight
    return doc


def bag_drop(comment, principles, essences, unique, cosmetic):
    lo, hi = principles
    containers = [single(SALT, lo, hi), single(SULFUR, lo, hi), single(MERCURY, lo, hi),
                  {"Type": "Choice", "RollsMin": essences[0], "RollsMax": essences[1],
                   "Containers": [single(e, 1, 1, 1) for e in ESSENCES]},
                  single(SHARD, 2),
                  chance(unique, one_of(UNIQUES))]
    if cosmetic:
        containers.append(chance(cosmetic, single(GOGGLES, 1)))
    return {"$Comment": comment, "Container": {"Type": "Multiple", "Containers": containers}}


def drops():
    write(DROPS / f"{BAG}.json", bag_drop(
        "Sac de l'Alchimiste : 2 à 3 de chaque principe, 3 à 4 essences au hasard, 2 éclats de rune, objet unique 15 %.",
        (2, 3), (3, 4), 15, 0))
    write(DROPS / f"{BAG_HARD}.json", bag_drop(
        "Sac de l'Alchimiste, mode difficile : 4 à 5 de chaque principe, 6 à 8 essences, 2 éclats de rune, objet unique "
        "40 %, lunettes de l'Alchimiste 10 %.", (4, 5), (6, 8), 40, 10))
    write(DROPS / f"{SECRET}.json", {
        "$Comment": "Coffres secrets de la Tour de l'Alchimiste (alchemist_tower.Tower.secrets) : or, gemmes, principes, "
                    "une potion des principes une fois sur trois, un objet unique une fois sur vingt.",
        "Container": {"Type": "Multiple", "Containers": [
            single("Ingredient_Bar_Gold", 2, 4),
            one_of(("Rock_Gem_Ruby", "Rock_Gem_Sapphire", "Rock_Gem_Emerald", "Rock_Gem_Topaz")),
            single(SALT, 1, 3), single(SULFUR, 1, 3), single(MERCURY, 1, 3),
            chance(33, one_of((ELIXIR, WARD, QUICKSILVER))),
            chance(5, one_of(UNIQUES)),
        ]}})


def main():
    preview = None
    if "--preview" in sys.argv:
        preview = Path(sys.argv[sys.argv.index("--preview") + 1])
        preview.mkdir(parents=True, exist_ok=True)
    sheet = []
    ICONS.mkdir(parents=True, exist_ok=True)

    # Pierre philosophale : l'objet, et le bloc posé sur le piédestal du Bureau.
    sheet.append(write_gx_model("Philosopher_Stone", stone_parts(0), MODELS, 12, 801))
    write(ITEMS / f"{STONE}.json", held_item(STONE, "Philosopher_Stone", "Legendary", 1,
                                             Light={"Radius": 2, "Color": "#e33"}))
    sheet.append(write_gx_model("Philosopher_Pedestal_Stone", pedestal_stone_parts(), BLOCK_MODELS, 18, 802))
    write(INTERACTIONS / f"{TAKE_STONE}.json", {
        "$Comment": "Piédestal du Bureau de l'Alchimiste : chaque joueur y prend sa propre pierre, une fois par instance. "
                    "Généré par tools/generate_alchemist_loot.py.",
        "Type": "Nakasar_TakePhilosopherStone", "ItemId": STONE})
    write(ITEMS / f"{PEDESTAL_STONE}.json", {
        "TranslationProperties": names(PEDESTAL_STONE),
        "Icon": "Icons/Items/Nakasar/Alchemist/Loot/Philosopher_Pedestal_Stone.png",
        "Categories": ["Blocks.Deco"],
        "PlayerAnimationsId": "Block",
        "Quality": "Legendary",
        "BlockType": {
            "Material": "Solid",
            "DrawType": "Model",
            "Opacity": "Transparent",
            "CustomModel": "Blocks/Nakasar/Alchemist/Philosopher_Pedestal_Stone.blockymodel",
            "CustomModelTexture": [{"Texture": "Blocks/Nakasar/Alchemist/Philosopher_Pedestal_Stone.png", "Weight": 1}],
            "HitboxType": PEDESTAL_STONE,
            "Flags": {},
            "Gathering": {"Breaking": {"GatherType": "Unbreakable"}},
            "BlockParticleSetId": "Crystal",
            "BlockSoundSetId": "Crystal",
            "ParticleColor": "#d61c2e",
            "Light": {"Color": "#e44"},
            "Particles": [{"SystemId": "Dungeon_Goblin_Temple_Motes", "Scale": 0.5, "PositionOffset": {"X": 0, "Y": 0.4, "Z": 0}}],
            "Interactions": {"Use": {"Interactions": [TAKE_STONE]}},
        },
        "Tags": {"Type": ["Deco"]},
        "ItemSoundSetId": "ISS_Items_Gems",
    })
    write(HITBOXES / f"{PEDESTAL_STONE}.json", {"Boxes": [gx.hitbox_box(-6, 0, -6, 6, 16, 6)]})

    # Sacs : cuir lié d'or (normal) ou de violet (difficile).
    for bag, tie, quality, seed in ((BAG, GOLD, "Epic", 803), (BAG_HARD, PURPLE, "Legendary", 804)):
        name = bag.removeprefix("Nakasar_")
        sheet.append(write_bag(name, tie, seed))
        doc = held_item(bag, name, quality, 16, Tags={"Type": ["Nakasar_Bounty"]},
                        Interactions={"Secondary": f"Root_{bag}"})
        write(ITEMS / f"{bag}.json", doc)
        write(INTERACTIONS / f"{bag}_Open.json", {"Type": "Nakasar_OpenBountyBag", "Droplist": bag})
        write(ROOTS / f"Root_{bag}.json", {"Interactions": [f"{bag}_Open"], "RequireNewClick": True})

    # Objets uniques.
    sheet.append(write_gx_model("Bottomless_Flask", flask_parts(), MODELS, 18, 805))
    effect("Nakasar_Bottomless_Flask_Heal", "Bottomless_Flask", 0.1, StatModifiers={"Health": 30}, ValueType="Percent",
           DamageCalculatorCooldown=0)
    effect("Nakasar_Bottomless_Flask_Regen", "Bottomless_Flask", 5.05, StatModifiers={"Health": 30}, ValueType="Percent",
           DamageCalculatorCooldown=5,
           ApplicationEffects={"Particles": [{"SystemId": "Potion_Health_Heal", "TargetEntityPart": "Entity",
                                              "TargetNodeName": "Pelvis"}]})
    potion(FLASK, "Bottomless_Flask", "Legendary",
           ["Nakasar_Bottomless_Flask_Heal", "Nakasar_Bottomless_Flask_Regen"], consume=False,
           cooldown=FLASK_COOLDOWN, stack=1)

    sheet.append(write_gx_model("Elemental_Lantern", lantern_parts(), MODELS, 22, 806))
    write(ITEMS / f"{LANTERN}.json", held_item(LANTERN, "Elemental_Lantern", "Legendary", 1,
                                               categories=("Items.Tools",), Utility={"Compatible": True}))

    write(ITEMS / f"{GLOVES}.json", {
        "Parent": "Armor_Leather_Light_Hands",
        "TranslationProperties": names(GLOVES),
        "Quality": "Legendary",
        "ItemLevel": 30,
        "Armor": {
            "ArmorSlot": "Hands",
            "BaseDamageResistance": 0,
            "StatModifiers": {"Health": [{"Amount": 10, "CalculationType": "Additive"}]},
            "DamageResistance": {
                "Physical": [{"Amount": 0.04, "CalculationType": "Percent"}],
                "Projectile": [{"Amount": 0.04, "CalculationType": "Percent"}],
                "Elemental": [{"Amount": 0.1, "CalculationType": "Percent"}],
                "Fire": [{"Amount": 0.1, "CalculationType": "Percent"}],
                "Poison": [{"Amount": 0.1, "CalculationType": "Percent"}],
            },
        },
        "MaxDurability": 400,
    })

    write_goggles(preview)
    write(ITEMS / f"{GOGGLES}.json", {
        "TranslationProperties": names(GOGGLES),
        "Quality": "Legendary",
        "ItemLevel": 30,
        "PlayerAnimationsId": "Block",
        "ItemSoundSetId": "ISS_Armor_Leather",
        "Categories": ["Items.Armors"],
        "Icon": "Icons/Items/Nakasar/Alchemist/Loot/Alchemist_Goggles.png",
        "IconProperties": {"Rotation": [0, 0, 0], "Scale": 1.0, "Translation": [0, 0]},
        "Model": "Items/Nakasar/Alchemist/Goggles/Goggles.blockymodel",
        "Texture": "Items/Nakasar/Alchemist/Goggles/Texture.png",
        "Interactions": {"Primary": {"Interactions": [{"Type": "EquipItem"}]},
                         "Secondary": {"Interactions": [{"Type": "EquipItem"}]}},
        "Armor": {"ArmorSlot": "Head", "BaseDamageResistance": 0, "CosmeticsToHide": ["FaceAccessory"]},
        "MaxDurability": 1000,
        "Tags": {"Type": ["Armor"], "Family": ["Nakasar_Cosmetic"]},
    })

    # Potions des trois principes (établi d'alchimie du jeu).
    for name, liquid, band in (("Grand_Elixir", (220, 40, 60), GOLD), ("Elemental_Ward", (90, 200, 220), PURPLE),
                               ("Quicksilver_Draught", (200, 210, 222), (120, 130, 150))):
        sheet.append(write_ga_model(name, go.bottle(liquid, band=band)))
    effect("Nakasar_Grand_Elixir_Heal", "Grand_Elixir", 0.1, StatModifiers={"Health": 40}, ValueType="Percent",
           DamageCalculatorCooldown=0)
    effect("Nakasar_Grand_Elixir_Regen", "Grand_Elixir", 5.05, StatModifiers={"Health": 60}, ValueType="Percent",
           DamageCalculatorCooldown=5,
           ApplicationEffects={"Particles": [{"SystemId": "Potion_Health_Heal", "TargetEntityPart": "Entity",
                                              "TargetNodeName": "Pelvis"}]})
    potion(ELIXIR, "Grand_Elixir", "Epic", ["Nakasar_Grand_Elixir_Heal", "Nakasar_Grand_Elixir_Regen"])
    recipe(ELIXIR, [("Potion_Health_Greater", 1), (SALT, 2), (MERCURY, 1)])

    resist = {k: [{"Amount": 0.3, "CalculationType": "Percent"}] for k in ("Elemental", "Fire", "Ice", "Lightning", "Poison")}
    effect("Nakasar_Elemental_Ward", "Elemental_Ward", 240, DamageResistance=resist)
    potion(WARD, "Elemental_Ward", "Epic", ["Nakasar_Elemental_Ward"])
    recipe(WARD, [("Potion_Empty", 1), (SULFUR, 2), (SALT, 1), ("Ingredient_Fire_Essence", 1),
                  ("Ingredient_Ice_Essence", 1), ("Ingredient_Lightning_Essence", 1)])

    effect("Nakasar_Quicksilver_Burst", "Quicksilver_Draught", 0.1, StatModifiers={"Stamina": 100}, ValueType="Percent",
           DamageCalculatorCooldown=0)
    effect("Nakasar_Quicksilver_Vigor", "Quicksilver_Draught", 300,
           RawStatModifiers={"Stamina": [{"Amount": 1.3, "CalculationType": "Multiplicative", "Target": "Max"}]})
    potion(QUICKSILVER, "Quicksilver_Draught", "Epic", ["Nakasar_Quicksilver_Burst", "Nakasar_Quicksilver_Vigor"])
    recipe(QUICKSILVER, [("Potion_Stamina_Greater", 1), (MERCURY, 2), (SULFUR, 1)])

    drops()
    if preview:
        out = Image.new("RGBA", (256 * len(sheet), 256), (40, 40, 48, 255))
        for i, img in enumerate(sheet):
            out.alpha_composite(img, (256 * i, 0))
        out.save(preview / "butin_tour.png")
    print("butin de la tour : pierre philosophale, 2 sacs, 3 objets uniques, lunettes, 3 potions")


if __name__ == "__main__":
    main()
