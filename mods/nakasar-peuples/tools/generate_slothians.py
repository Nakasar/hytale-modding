#!/usr/bin/env python3
"""Zone 4 du mod Peuples d'Orbis (étape 9 du plan d'implémentation) : les Slothians, le Vide, l'avant-poste du champion.

GDD, Progression des zones : zone 4 « Les Limbes Ardentes » = Slothians (amis, monastère au bord du Vide) contre le
Vide (rampants, larves, squelettes brûlés), corruption du Vide loin des braseros, Veille des Slothians en fin de mod.
Le jeu n'a qu'un rôle slothian vide (Server/NPC/Roles/Intelligent/Other/Slothian.json, « Abstract », sans instruction) :
tous les rôles sont écrits ici sur les modèles vanilla Slothian_{Villager,Scout,Monk,Warrior,Elder} (Server/Models/
Intelligent/Slothian, squelette du joueur : animations Sit, SitGround, Crouch, IdlePassive). Même recette que les
Feran et les Renoncés de l'étape 8 (tools/generate_zones.py, dont ce script réemploie les fonctions) :

  * plan du monastère (Server/Nakasar/VillageLayouts/Slothian_Monastere.json) : maisons, portes et temple vanilla
    Npc/Slothian/Disabled/* (prefabs complets, sans marqueur d'apparition ni Prefab_Spawner_Block), étal, affût et temple
    des monuments Monuments/Incidental/Slothian/Land/* ;
  * PNJ de service (crieur, guetteur, captif = moine perdu, marchand, chef = l'Abbé), métiers, garde de raid ;
  * demandes du tableau et chaîne (cendres, cristaux d'anomalie vanilla Void_Anomaly_Crystal_Small, moine perdu, faille,
    puis la Veille) ;
  * échoppes (brasero de jungle vanilla anti-Vide, Robe du moine, armes tribales vanilla des Slothians), faveur, missive,
    tableau, bannière (icône de carte), groupes de PNJ et de réputation ;
  * assaillants du Vide (Raider_Void_*) et leur évènement de monde, trophée ;
  * corruption du Vide (effets Nakasar_Peuples_Void_1 à _5, cause de dégâts Nakasar_Peuples_Void), Robe du moine,
    Veille des Slothians ;
  * avant-poste du champion : Pierre de fondation (objet utilisé en main → fenêtre de choix, Java outpost/) ;
  * le bloc « étape 9 » en tête des fichiers .lang fr-FR et en-US (entre deux marqueurs, réécrit à chaque passage).

Titres des demandes : {TITLE_MAX} caractères au plus (règle de Kevin du 14 novembre 2026, vérifiée ici).
Règle n° 1 (AGENTS.md) : aucun PNJ ne se soigne. Règle n° 2 : modèles, armes, attaques, butins, prefabs, sons vanilla.

    python3 tools/generate_slothians.py [--preview /mnt/project-files/peuples/zones]
"""
import argparse
import json
import math
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import generate_raids as gr  # noqa: E402
import generate_village_layouts as gl  # noqa: E402
import generate_zones as gz  # noqa: E402

ROOT = TOOLS.parent
RES = gz.RES
COMMON = gz.COMMON
ROLES = gz.ROLES
ITEMS = gz.ITEMS
TITLE_MAX = gz.TITLE_MAX
LANG_BEGIN = "# ---- Étape 9 : zone 4, Slothians, Vide, avant-poste (généré par tools/generate_slothians.py, ne pas modifier à la main) ----"
LANG_END = "# ---- Fin de l'étape 9 ----"

FR = {}
EN = {}


def t(key, fr, en):
    FR[key] = fr
    EN[key] = en


write = gz.write

PID = "Slothian"
DIS = "Npc/Slothian/Disabled/"
MON = "Monuments/Incidental/Slothian/Land/"

SPEC = {
    "name": ("Slothians", "Slothians"),
    "adj": ("slothian", "Slothian"),
    "layout": "Slothian_Monastere",
    "layout_spec": {
        "People": PID,
        "PlazaRadius": 6,
        "Banner": (0, -4),
        "Buildings": [
            # Palier 0 : deux huttes, l'étal des cendres, l'affût du guetteur.
            ("Hutte_Ouest", 0, DIS + "House/Small/Slothian_Disabled_House_Small_001", -20, 0, 0),
            ("Hutte_Est", 0, DIS + "House/Small/Slothian_Disabled_House_Small_003", 21, 0, 0),
            ("Etal_Des_Cendres", 0, MON + "Merchant/Incidental_Slothian_Merchant_Slothian_Merchant_001", 0, -15, 0),
            ("Affut", 0, MON + "Hunting/Incidental_Slothian_Slothian_Hunting_001", 0, 15, 0),
            # Palier 1 : deux maisons, la porte du monastère.
            ("Maison_Nord_Ouest", 1, DIS + "House/Medium/Slothian_Disabled_House_Medium_001", -24, -24, 0),
            ("Maison_Sud_Est", 1, DIS + "House/Medium/Slothian_Disabled_House_Medium_002", 24, 26, 0),
            ("Porte_Du_Monastere", 1, DIS + "Gate/Slothian_Disabled_Gate_001", 0, 32, 0),
            # Bâtiments de métier, étape 3 : la bauge de veille (enclos du mod en blocs vanilla, barrière à l'ouest).
            ("Bauge_De_Veille", 1, gl.PEN + "Slothian_Pen", 40, -13, 3),
            # Palier 2 : le temple de veille (étape 4 de la chaîne), la grande maison, la hutte du nord.
            ("Temple_De_Veille", 2, MON + "Temple/Incidental_Slothian_Slothian_Temple_001", 26, -26, 0),
            ("Grande_Maison_Slothian", 2, DIS + "House/Medium/Tall/Slothian_Disabled_House_Medium_Tall_001", -26, 26, 0),
            ("Hutte_Nord", 2, DIS + "House/Small/Slothian_Disabled_House_Small_002", 0, -34, 0),
            # Palier 3 : le monastère (lieu central du GDD) et la porte riche.
            ("Monastere", 3, DIS + "Temple/Medium/Slothian_Disabled_Temple_Medium_001", -48, 0, 0),
            ("Porte_Riche", 3, DIS + "Gate/Rich/Slothian_Disabled_Gate_Rich_001", 48, 0, 0),
        ],
        "Chantiers": [
            (1, 24, [("Rock_Basalt_Cobble", 24), ("Soil_Mud_Dry", 16), ("Ingredient_Fibre", 12)]),
            (2, 24, [("Rock_Basalt_Brick", 32), ("Wood_Hardwood_Planks", 32), ("Soil_Ash", 16),
                     ("Ingredient_Fire_Essence", 6)]),
            (3, 24, [("Rock_Basalt_Brick", 64), ("Furniture_Jungle_Candle", 8), ("Ingredient_Fire_Essence", 12),
                     ("Ingredient_Void_Essence", 8)]),
        ],
        # Trois colons au palier 0 (bâtisseur, guetteur, porteur de cendres) : l'avant-poste du champion en hérite.
        "Jobs": [
            ("Batisseur", 0, "Builder", None, None, "Hutte_Est"),
            ("Guetteur", 0, "Watcher", "Affut", "front", "Hutte_Ouest"),
            ("Porteur_Cendres", 0, "AshBearer", "Etal_Des_Cendres", "front", "Hutte_Ouest"),
            ("Garde", 1, "Guard", "Porte_Du_Monastere", "front", "Maison_Sud_Est"),
            ("Gardien_Bauge", 1, "Breeder", "Bauge_De_Veille", "front", "Hutte_Est"),
            ("Moine", 2, "Monk", "Temple_De_Veille", "front", "Hutte_Nord"),
            ("Doyen", 3, "Elder", "Monastere", "front", "Monastere"),
        ],
        "Woodpile": (-4, -3),
    },
    # (métier, apparence vanilla, animation du squelette joueur, rayon). Les Slothians sont lents : ils s'assoient.
    "jobs": [
        ("Builder", "Slothian_Villager", "Crouch", 2),
        ("Watcher", "Slothian_Scout", "IdlePassive", 2),
        ("AshBearer", "Slothian_Villager", "Crouch", 2),
        ("Guard", "Slothian_Warrior", "IdlePassive", 3),
        ("Breeder", "Slothian_Villager", "Crouch", 4),
        ("Monk", "Slothian_Monk", "SitGround", 2),
        ("Elder", "Slothian_Elder", "Sit", 2),
    ],
    "looks": {"Crier": "Slothian_Villager", "Lookout": "Slothian_Scout", "Captive": "Slothian_Monk",
              "Merchant": "Slothian_Villager", "Chief": "Slothian_Monk"},
    "deposit": "Furniture_Jungle_Chest_Small",
    "sign": "Furniture_Temple_Emerald_Sign",
    "statue": "Furniture_Jungle_Brazier",
    # Garde de raid : hache tribale vanilla des Slothians, coups de hache des Outlanders (même squelette joueur).
    "defender": ("Slothian_Warrior", "Weapon_Axe_Tribal",
                 ["Outlander_Berserker_Axe_Swing_Left", "Outlander_Berserker_Axe_Swing_Right",
                  "Outlander_Berserker_Axe_Swing_Down"], 2.6),
    "favor": {"Icon": "Icons/ItemsGenerated/Rubble_Charcoal_Small.png",
              "Model": "Blocks/Stone/Rubble_Charcoal.blockymodel",
              "Texture": "Items/Rubble/Rubble_Textures/Charcoal.png",
              "IconProperties": {"Scale": 0.6, "Rotation": [22.5, 45, 22.5], "Translation": [0, -6]},
              "ItemSoundSetId": "ISS_Blocks_Stone"},
    "vanilla_group": None,
    "enemy": "Void",
}

# Assaillants du Vide : (suffixe, apparence, arme ou None, butin, PV, dégâts, vitesse, attaques vanilla, portée).
RAIDERS = [
    ("Void_Larva", "Larva_Void", None, "Empty", 21, 8, 6.5, ["Larva_Void_Bite"], 1.6),
    ("Void_Crawler", "Crawler_Void", None, "Drop_Crawler_Void", 70, 16, 6.0, ["Root_NPC_Crawler_Void_Attack"], 2.25),
    ("Void_Skeleton_Soldier", "Skeleton_Burnt_Soldier", "Weapon_Sword_Steel_Rusty", "Drop_Skeleton_Burnt_Soldier",
     124, 22, 4.6, ["Root_NPC_Skeleton_Burnt_Soldier_Attack"], 3.0),
    ("Void_Skeleton_Knight", "Skeleton_Burnt_Knight", "Weapon_Sword_Steel_Rusty", "Drop_Skeleton_Burnt_Knight",
     160, 26, 4.4, ["Root_NPC_Skeleton_Knight_Attack"], 3.0),
]
gz.ENEMY_SOUND["Void"] = "SFX_Crawler_Void_Alerted"

REQUESTS = [
    ("Slothian_Gather_Ash", "Gather", {"ItemId": "Soil_Ash", "Quantity": 16}, 10, 1),
    ("Slothian_Gather_Volcanic", "Gather", {"ItemId": "Rock_Volcanic", "Quantity": 16}, 10, 1),
    ("Slothian_Gather_Void", "Gather", {"ItemId": "Ingredient_Void_Essence", "Quantity": 4}, 15, 2),
    ("Slothian_Gather_Mushroom", "Gather", {"ItemId": "Plant_Crop_Mushroom_Glowing_Red", "Quantity": 8}, 10, 1),
    ("Slothian_Craft_Candles", "Craft", {"ItemId": "Furniture_Jungle_Candle", "Quantity": 4}, 15, 2),
    ("Slothian_Hunt_Crawlers", "Hunt", {"Spawns": ["Crawler_Void", "Crawler_Void", "Larva_Void", "Larva_Void"],
                                        "Roles": ["Crawler_Void", "Larva_Void"],
                                        "MinDistance": 90, "MaxDistance": 150}, 20, 3),
    ("Slothian_Hunt_Crystals", "Hunt", {"Spawns": ["Void_Anomaly_Crystal_Small", "Void_Anomaly_Crystal_Small",
                                                   "Void_Anomaly_Crystal_Small"],
                                        "Roles": ["Void_Anomaly_Crystal_Small"],
                                        "MinDistance": 80, "MaxDistance": 140}, 20, 3),
    ("Slothian_Delivery_Missive", "Delivery", {"MinDistance": 90, "MaxDistance": 150}, 10, 1),
    ("Slothian_Escort_Pilgrim", "Escort", {"Spawns": ["Crawler_Void", "Crawler_Void"], "MinDistance": 80,
                                           "MaxDistance": 140}, 20, 3),
    ("Slothian_Defense_Night", "Defense", {}, 25, 3),
]

CHAIN = {
    "give": ("Soil_Ash", 16, 80),
    "templates": [
        (2, "Slothian_Chain_Crystals", "Hunt", {"Spawns": ["Void_Anomaly_Crystal_Small", "Void_Anomaly_Crystal_Small",
                                                           "Void_Anomaly_Crystal_Small", "Crawler_Void"],
                                                "Roles": ["Void_Anomaly_Crystal_Small"],
                                                "MinDistance": 100, "MaxDistance": 160}, 120, 5, "Ami"),
        (3, "Slothian_Chain_Monk", "Escort", {"Spawns": ["Crawler_Void", "Crawler_Void", "Skeleton_Burnt_Soldier"],
                                              "MinDistance": 110, "MaxDistance": 170}, 150, 5, "Ami"),
        (4, "Slothian_Chain_Rift", "Defense", {}, 200, 6, "Hote"),
    ],
    "reward": {"mode": "give", "item": "Nakasar_Peuples_Vigil"},
}
gz.CHAIN_BUILDINGS["Slothian_Chain_Rift"] = "Temple_De_Veille"


# ----------------------------------------------------------------------------------------------------------------------

def raiders():
    for suffix, look, weapon, drops, hp, dmg, speed, swings, reach in RAIDERS:
        rid, doc = gr.raider(suffix, look, weapon or "Weapon_Club_Crude", drops, hp, dmg, speed)
        doc["$Comment"] = (f"Assaillant du Vide d'un raid (étape 9), généré par tools/generate_slothians.py. Apparence, attaques "
                           f"et butin vanilla ({look}). Posé par raid/Raids au camp ; il marche sur le cœur du monastère et "
                           "frappe à vue joueurs et Slothians (RaidAttitudeSystem). Retiré à la fin du raid. Ne se soigne "
                           "jamais.")
        if weapon is None:
            doc.pop("HotbarItems", None)
        else:
            doc["HotbarItems"] = [weapon]
        gz.replace_attacks(doc, swings, reach)
        write(ROLES / f"{rid}.json", doc)


def zone_items():
    """Robe du moine, Veille des Slothians, Pierre de fondation ; corruption du Vide."""
    write(ITEMS / "Nakasar_Peuples_Monk_Robe.json", {
        "$Comment": "Robe du moine (étape 9, GDD Récompenses slothians) : portée (plastron), la corruption du Vide de la "
                    "zone 4 ne monte plus (Java, zone/Climate). Plastron de cendretoile vanilla, échoppe slothiane des amis.",
        "Parent": "Armor_Cloth_Cindercloth_Chest",
        "TranslationProperties": {"Name": "nakasar_peuples.items.Nakasar_Peuples_Monk_Robe.name",
                                  "Description": "nakasar_peuples.items.Nakasar_Peuples_Monk_Robe.description"},
        "Quality": "Epic",
        "MaxDurability": 400,
        "DropOnDeath": False,
    })
    write(ITEMS / "Nakasar_Peuples_Vigil.json", {
        "$Comment": "Veille des Slothians (étape 9) : fin de la chaîne slothiane et du parcours du mod. Portée dans "
                    "l'inventaire, elle protège de la corruption du Vide (Java, zone/Climate) et le titre « Veilleur du "
                    "Vide » s'affiche à l'entrée des villages. Cœur du Vide vanilla (Ingredient_Voidheart), purifié.",
        "TranslationProperties": {"Name": "nakasar_peuples.items.Nakasar_Peuples_Vigil.name",
                                  "Description": "nakasar_peuples.items.Nakasar_Peuples_Vigil.description"},
        "Icon": "Icons/ItemsGenerated/Ingredient_Voidheart.png",
        "Categories": ["Items.Ingredients"],
        "Model": "Resources/Ingredients/Voidheart.blockymodel",
        "Texture": "Resources/Ingredients/Voidheart_Texture.png",
        "PlayerAnimationsId": "Item",
        "Quality": "Legendary",
        "MaxStack": 1,
        "IconProperties": {"Scale": 0.9, "Rotation": [0, 0, 0], "Translation": [0, -13]},
        "ItemEntity": {"ParticleSystemId": None},
        "Scale": 1.2,
        "Light": {"Color": "#fc8", "Radius": 2},
        "ItemSoundSetId": "ISS_Items_Gems",
        "DropOnDeath": False,
    })
    write(ITEMS / "Nakasar_Peuples_Foundation_Stone.json", {
        "$Comment": "Pierre de fondation (étape 9, GDD Récompenses : avant-poste du champion). Donnée une fois par peuple "
                    "au rang Champion (Java, outpost/Outposts). Utilisée en main, elle ouvre la fenêtre « Fonder un "
                    "avant-poste » (maquette avant_poste.png). Pierre de basalte taillée vanilla.",
        "TranslationProperties": {"Name": "nakasar_peuples.items.Nakasar_Peuples_Foundation_Stone.name",
                                  "Description": "nakasar_peuples.items.Nakasar_Peuples_Foundation_Stone.description"},
        "Icon": "Icons/ItemsGenerated/Rock_Basalt_Brick_Ornate.png",
        "Categories": ["Items.Ingredients"],
        "Model": "Blocks/Stone/Rubble_Charcoal.blockymodel",
        "Texture": "Items/Rubble/Rubble_Textures/Charcoal.png",
        "PlayerAnimationsId": "Item",
        "Quality": "Legendary",
        "MaxStack": 4,
        "IconProperties": {"Scale": 0.6, "Rotation": [22.5, 45, 22.5], "Translation": [0, -6]},
        "ItemEntity": {"ParticleSystemId": None},
        "ItemSoundSetId": "ISS_Blocks_Stone",
        "Interactions": {"Secondary": "Root_Nakasar_Peuples_Foundation_Stone"},
        "DropOnDeath": False,
    })
    write(RES / "Item/RootInteractions/Nakasar/Peuples/Root_Nakasar_Peuples_Foundation_Stone.json",
          {"Interactions": ["Nakasar_Peuples_Foundation_Stone"], "RequireNewClick": True})
    write(RES / "Item/Interactions/Nakasar/Peuples/Nakasar_Peuples_Foundation_Stone.json",
          {"$Comment": "Ouvre la fenêtre de fondation d'un avant-poste là où se tient le joueur (Java, outpost/OutpostPage).",
           "Type": "Nakasar_Peuples_ZoneItem", "Action": "Foundation"})

    effects = RES / "Entity/Effects/Nakasar/Peuples"
    for n in range(1, 6):
        write(effects / f"Nakasar_Peuples_Void_{n}.json", {
            "$Comment": f"Corruption du Vide, piles {2 * n - 1} et {2 * n} : {0.15 * (2 * n - 1):.2f} à {0.15 * 2 * n:.2f} % "
                        "des PV max par seconde (Java, zone/Climate). Zone 4, loin d'un brasero, d'un feu ou du monastère.",
            "Name": f"nakasar_peuples.effects.Nakasar_Peuples_Void_{n}",
            "Debuff": True,
            "StatusEffectIcon": f"UI/StatusEffects/Nakasar/Peuples/Void_{n}.png",
            "ApplicationEffects": {"EntityTopTint": "#b48cff"},
            "OverlapBehavior": "Overwrite",
            "Infinite": False,
            "Duration": 1.5,
        })
        t(f"effects.Nakasar_Peuples_Void_{n}", f"Corruption du Vide {2 * n}", f"Void corruption {2 * n}")
    write(effects / "Nakasar_Peuples_Sanctuary.json", {
        "$Comment": "Abri du Vide (zone 4, près d'un brasero, d'un feu ou dans le monastère) : la corruption redescend.",
        "Name": "nakasar_peuples.effects.Nakasar_Peuples_Sanctuary",
        "StatusEffectIcon": "UI/StatusEffects/Nakasar/Peuples/Sanctuary.png",
        "OverlapBehavior": "Overwrite",
        "Infinite": False,
        "Duration": 1.5,
    })
    t("effects.Nakasar_Peuples_Sanctuary", "Flamme qui veille", "Watching flame")
    write(RES / "Entity/Damage/Nakasar_Peuples_Void.json", {
        "$Comment": "Corruption du Vide de la zone 4 : une part des PV max par seconde selon les piles, que l'armure ne réduit pas.",
        "BypassResistances": True,
        "DurabilityLoss": False,
        "StaminaLoss": False,
        "DamageTextColor": "#c8a0ff",
    })
    draw_void_icons()


def draw_void_icons():
    """Icônes de statut : œil du Vide (5 intensités) et flamme d'abri."""
    from PIL import Image, ImageDraw
    size, ss = 128, 4
    big = size * ss
    c = big // 2
    out = gz.STATUS_ICONS
    out.mkdir(parents=True, exist_ok=True)
    for n in range(1, 6):
        img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        # Tentacules (de plus en plus nombreux), puis l'œil.
        for i in range(2 + n):
            a = i * 2 * math.pi / (2 + n) + 0.4
            pts = []
            for k in range(12):
                r = (26 + k * 3.2) * ss
                w = math.sin(k * 0.8) * 0.18
                pts.append((c + math.cos(a + w) * r, c + math.sin(a + w) * r))
            d.line(pts, fill=(60, 20, 90, 255), width=(9 - k // 3) * ss // 2 + 4 * ss, joint="curve")
            d.line(pts, fill=(150, 90, 230, 255), width=4 * ss, joint="curve")
        d.ellipse([c - 30 * ss, c - 20 * ss, c + 30 * ss, c + 20 * ss], fill=(30, 10, 50, 255))
        d.ellipse([c - 26 * ss, c - 16 * ss, c + 26 * ss, c + 16 * ss], fill=(200, 160, 255, 255))
        d.ellipse([c - 10 * ss, c - 13 * ss, c + 10 * ss, c + 13 * ss], fill=(70, 0, 110, 255))
        d.ellipse([c - 4 * ss, c - 8 * ss, c + 2 * ss, c - 2 * ss], fill=(255, 255, 255, 230))
        img.resize((size, size), Image.LANCZOS).save(out / f"Void_{n}.png")
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([c - 30 * ss, c + 26 * ss, c + 30 * ss, c + 40 * ss], fill=(60, 50, 50, 255))   # vasque
    d.polygon([(c - 34 * ss, c + 26 * ss), (c + 34 * ss, c + 26 * ss), (c + 24 * ss, c + 14 * ss), (c - 24 * ss, c + 14 * ss)],
              fill=(90, 80, 75, 255))
    d.polygon([(c - 22 * ss, c + 14 * ss), (c, c - 48 * ss), (c + 22 * ss, c + 14 * ss)], fill=(250, 150, 50, 255))
    d.polygon([(c - 11 * ss, c + 14 * ss), (c, c - 18 * ss), (c + 11 * ss, c + 14 * ss)], fill=(255, 235, 150, 255))
    img.resize((size, size), Image.LANCZOS).save(out / "Sanctuary.png")


def map_icon():
    """Icône de carte : temple à toit en pagode et flamme (même style que generate_map_icons.py)."""
    from PIL import Image, ImageDraw, ImageFilter
    import generate_map_icons as gmi
    S, SS = gmi.SIZE, gmi.SS
    out = COMMON / "UI/WorldMap/MapMarkers"

    def fig(s):
        mask = Image.new("L", (S * s, S * s), 0)
        d = ImageDraw.Draw(mask)
        d.polygon([(6 * s, 28 * s), (24 * s, 18 * s), (42 * s, 28 * s), (36 * s, 30 * s), (24 * s, 24 * s), (12 * s, 30 * s)], fill=255)
        d.rectangle([13 * s, 29 * s, 35 * s, 43 * s], fill=255)
        d.rectangle([21 * s, 34 * s, 27 * s, 43 * s], fill=0)
        d.polygon([(19 * s, 16 * s), (24 * s, 3 * s), (29 * s, 16 * s)], fill=255)  # flamme de veille
        return mask

    for name, fill, th in ((f"Nakasar_Peuples_{PID}.png", (236, 220, 255, 255), 2),
                           (f"Nakasar_Peuples_{PID}Compass.png", (190, 150, 250, 255), 3)):
        big = S * SS
        mask = fig(SS)
        ring = mask.filter(ImageFilter.MaxFilter(2 * th * SS + 1))
        img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
        img.paste(Image.new("RGBA", (big, big), (0, 0, 0, 255)), (0, 0), ring)
        img.paste(Image.new("RGBA", (big, big), fill), (0, 0), mask)
        out.mkdir(parents=True, exist_ok=True)
        img.resize((S, S), Image.LANCZOS).save(out / name)


def shops():
    f = f"Nakasar_Peuples_Favor_{PID}"
    gz.shop(PID, "Tolere", [("Furniture_Jungle_Brazier", 1, 2, 4), ("Furniture_Jungle_Candle", 2, 1, 10),
                            ("Food_Wildmeat_Cooked", 2, 1, 10), ("Rock_Basalt_Brick", 16, 1, 10)],
            f, "Échoppe du monastère", "Monastery stall")
    gz.shop(PID, "Ami", [("Nakasar_Peuples_Monk_Robe", 1, 6, 2), ("Ingredient_Fire_Essence", 2, 2, 8),
                         ("Weapon_Spear_Tribal", 1, 6, 2), ("Weapon_Dart_Tribal", 16, 2, 6)],
            f, "Échoppe des amis du monastère", "Monastery friends' stall")
    gz.shop(PID, "Hote", [("Weapon_Longsword_Tribal", 1, 8, 2), ("Weapon_Battleaxe_Tribal", 1, 8, 2),
                          ("Ingredient_Void_Essence", 2, 3, 6), ("Armor_Cloth_Cindercloth_Head", 1, 6, 2)],
            f, "Réserve de l'hôte du monastère", "Monastery host's reserve")
    # Les textes des échoppes passent par gz.t (bloc de l'étape 8) : on les reprend ici.
    for rank in ("Tolere", "Ami", "Hote"):
        k = f"barter.{PID}_{rank}.title"
        t(k, gz.FR.pop(k), gz.EN.pop(k))


def trophy():
    void = gr.trophy()
    void.update({
        "$Comment": "Trophée du Vide : donné au bilan d'un raid gagné sur le monastère slothian (étape 9). Essence du Vide vanilla.",
        "TranslationProperties": {"Name": "nakasar_peuples.items.Nakasar_Peuples_Trophy_Void.name",
                                  "Description": "nakasar_peuples.items.Nakasar_Peuples_Trophy_Void.description"},
        "Icon": "Icons/ItemsGenerated/Ingredient_Void_Essence.png",
        "Model": "Resources/Ingredients/Essence.blockymodel",
        "Texture": "Resources/Ingredients/Essence_Textures/Void_Essence_Texture.png",
        "IconProperties": {"Scale": 0.6, "Rotation": [0, 0, 0], "Translation": [0, -13]},
        "ItemSoundSetId": "ISS_Items_Gems",
    })
    write(ITEMS / "Nakasar_Peuples_Trophy_Void.json", void)


# ----------------------------------------------------------------------------------------------------------------------
# Textes (voix du GDD : Slothians lents, une phrase pour dix mots)
# ----------------------------------------------------------------------------------------------------------------------

CRIER = {
    "npc": ("Pas-Lent", "Slowstep"), "role": ("Voix du monastère", "Voice of the monastery"),
    "accueil": ("Bienvenue… voyageur. Le tableau… dit… ce qu'il nous faut.", "Welcome… traveller. The board… says… what we need."),
    "voir": ("Montre-moi les besoins du monastère.", "Show me the monastery's needs."),
    "quoi": ("Comment aider ?", "How can I help?"),
    "explication": ("Trois besoins… chaque matin. Prends-en un… sans te presser. Le coffre de la place… reçoit tout.",
                    "Three needs… each morning. Take one… no hurry. The chest on the square… takes everything."),
    "encours": ("Tu reviens… déjà ?", "Back… already?"),
    "rendre": ("Voici ce que j'apporte.", "Here is what I bring."),
    "rendu": ("Bien… très bien. Le Vide… recule d'un pas.", "Good… very good. The Void… steps back."),
    "aurevoir": ("Va… doucement.", "Go… gently."),
    "honni": ("Le Vide… t'a touché. Ou c'est toi… qui l'as aidé. Reviens… purifié.",
              "The Void… touched you. Or you… helped it. Come back… purified."),
    "racheter": ("Je veux réparer mes torts.", "I want to make amends."),
}
MERCHANT = {
    "npc": ("Main-Tranquille", "Quiethand"), "role": ("marchand", "merchant"),
    "honni": ("Non.", "No."),
    "etranger": ("Le monastère… ne troque pas… avec qui il ne connaît pas.", "The monastery… does not trade… with strangers."),
    "commentAider": ("Comment me faire connaître ?", "How do I make myself known?"),
    "conseil": ("Le crieur… près du tableau. Une demande… puis deux.", "The crier… by the board. One request… then two."),
    "voirDemandes": ("Montre-moi les besoins", "Show me the needs"),
    "accueil": ("Braseros… cierges… tout se paie… en cendre bénie.", "Braziers… candles… all paid… in blessed ash."),
    "ami": ("Pour un ami… la robe des moines. Le Vide… n'aime pas la robe.", "For a friend… the monks' robe. The Void… dislikes the robe."),
    "hote": ("Notre hôte… voici les armes… de nos anciens gardiens.", "Our host… here are the weapons… of our old guardians."),
    "troc": ("Voyons ton troc", "Let's see your wares"), "avance": ("Et pour les amis ?", "And for friends?"),
    "reserve": ("Ouvre-moi la réserve", "Open the reserve for me"), "aurevoir": ("Doucement", "Gently"),
}
JOBS = {
    "Builder": {"npc": ("Lourde-Paume", "Heavypalm"), "role": ("Bâtisseur", "Builder"),
                "accueil": ("Une pierre… puis une autre. Pas de hâte.", "One stone… then another. No hurry."),
                "metier": ("Je bâtis… en basalte. Le Vide… ronge le bois.", "I build… in basalt. The Void… gnaws wood."),
                "chantier": ("Un chantier… est ouvert. J'y vais… doucement.", "A site… is open. I'm going… slowly."),
                "statut": ("Voilà… où on en est.", "Here's… where we are.")},
    "Watcher": {"npc": ("Œil-Patient", "Patienteye"), "role": ("Guetteur", "Watcher"),
                "accueil": ("Chut… je regarde la faille.", "Hush… I watch the rift."),
                "metier": ("De l'affût… je vois les cristaux pousser. Quand ils chantent… le Vide vient.",
                           "From the hide… I see the crystals grow. When they sing… the Void comes."),
                "auxArmes": ("Le Vide monte ! Aux braseros !", "The Void rises! To the braziers!"),
                "rumeur": ("Des rampants… rôdent près des cristaux. Ils attendent… la nuit.",
                           "Crawlers… prowl near the crystals. They wait… for night.")},
    "AshBearer": {"npc": ("Gris-de-Cendre", "Ashgrey"), "role": ("Porteur de cendres", "Ash bearer"),
                  "accueil": ("Tu sens… la cendre ? Elle est bénie.", "Do you smell… the ash? It is blessed."),
                  "metier": ("Je porte les cendres… des braseros aux murs. Là où passe la cendre… le Vide ne passe pas.",
                             "I carry ashes… from braziers to walls. Where the ash goes… the Void does not.")},
    "Guard": {"npc": ("Bras-de-Pierre", "Stonearm"), "role": ("Garde", "Guard"),
              "accueil": ("Halte… lentement.", "Halt… slowly."),
              "metier": ("Je tiens la porte. Ma hache… est lente. Mais elle tombe… toujours.",
                         "I hold the gate. My axe… is slow. But it always… falls."),
              "auxArmes": ("Le Vide ! Tiens la porte… avec moi !", "The Void! Hold the gate… with me!"),
              "rumeur": ("Des squelettes brûlés… marchent la nuit. Ils sentent… nos feux.",
                         "Burnt skeletons… walk at night. They smell… our fires.")},
    "Breeder": {"npc": ("Pas-Tranquille", "Quietstep"), "role": ("Gardien de la bauge", "Pen keeper"),
                "accueil": ("Lentement… les bêtes n'aiment pas… les gestes vifs.", "Slowly… the beasts don't like… quick moves."),
                "metier": ("Je garde la bauge… Des porcs, des plumes, des coquilles qui brûlent… Tout sert… à la veille.",
                           "I keep the pen… Pigs, feathers, shells that burn… Everything serves… the vigil.")},
    "Monk": {"npc": ("Frère Souffle", "Brother Breath"), "role": ("Moine", "Monk"),
             "accueil": ("Assieds-toi… respire. Le Vide… déteste le calme.", "Sit… breathe. The Void… hates calm."),
             "metier": ("Je veille… au temple. Tant qu'un moine veille… la faille dort.",
                        "I keep vigil… at the temple. While a monk watches… the rift sleeps.")},
    "Elder": {"npc": ("Mère-Mousse", "Mother Moss"), "role": ("Doyenne", "Dean"),
              "accueil": ("Enfant… tu as marché… si loin.", "Child… you walked… so far."),
              "metier": ("Je me souviens… d'avant la faille. Nous étions… nombreux.", "I remember… before the rift. We were… many.")},
}
CHAIN_TEXTS = {
    "npc": ("L'Abbé Pesant", "Abbot Heavy"), "role": ("Abbé du monastère", "Abbot of the monastery"),
    "aurevoir": ("Va… et veille.", "Go… and keep watch."),
    "nouvelles": ("Et la faille ?", "And the rift?"),
    "nouvellesTexte": ("Elle dort… mal. Chaque nuit… le Vide pousse un peu. Nos braseros… le retiennent.",
                       "It sleeps… badly. Each night… the Void pushes a little. Our braziers… hold it back."),
    "accepter": ("Je m'en charge.", "I'll take care of it."),
    "accepte": ("Bien… prends ton temps. Mais pas trop.", "Good… take your time. But not too much."),
    "auxArmes": ("Le Vide est dans le monastère ! Défends les braseros !", "The Void is in the monastery! Defend the braziers!"),
    "honni": ("Le Vide… parle à travers toi. Va-t'en.", "The Void… speaks through you. Leave."),
    "etranger": ("Un étranger… si loin. Le monastère garde une faille… on ne la confie pas… au premier venu.",
                 "A stranger… so far. The monastery guards a rift… we don't entrust it… to the first comer."),
    "commentAider": ("Comment gagner votre confiance ?", "How do I earn your trust?"),
    "conseil": ("Le tableau… lentement. Reviens… quand on te tolérera.", "The board… slowly. Come back… when you are tolerated."),
    "voirDemandes": ("Voir les besoins", "See the needs"),
    "etape1": ("Nos braseros… ont faim. Porte-nous seize cendres… et nous saurons… que tu restes.",
               "Our braziers… are hungry. Bring us sixteen ashes… and we'll know… you are staying."),
    "donner": ("Voici seize cendres.", "Here are sixteen ashes."),
    "failDonner": ("il faut être Toléré des Slothians et porter 16 Cendres", "you must be Tolerated by the Slothians and carry 16 Ash"),
    "etape2": ("Les braseros brûlent. Mais trois cristaux d'anomalie… ont poussé près d'ici. Quand tu seras notre ami… brise-les.",
               "The braziers burn. But three anomaly crystals… have grown nearby. When you are our friend… break them."),
    "etape2EnCours": ("Trois cristaux… qui chantent. Fais-les taire.", "Three crystals… singing. Silence them."),
    "etape3": ("Les cristaux se taisent. Mais Frère Lenteur… est parti les prier… et ne revient pas. Ramène-le.",
               "The crystals are silent. But Brother Slowness… went to pray at them… and has not come back. Bring him home."),
    "etape3EnCours": ("Frère Lenteur… attend quelque part. Ramène-le… au cœur du monastère.",
                      "Brother Slowness… waits somewhere. Bring him… to the heart of the monastery."),
    "etape4": ("Frère Lenteur a vu… la faille s'ouvrir. Une nuit… le Vide montera. Quand tu seras notre hôte… tiens le temple avec nous.",
               "Brother Slowness saw… the rift opening. One night… the Void will rise. When you are our host… hold the temple with us."),
    "etape4EnCours": ("Cette nuit… le Vide monte. Reste au temple… près des braseros.", "Tonight… the Void rises. Stay at the temple… by the braziers."),
    "etape4Attente": ("Le Vide montera… mais nous n'avons pas de temple de veille. Aide le monastère… à grandir.",
                      "The Void will rise… but we have no vigil temple yet. Help the monastery… grow."),
    "recompense": ("Tu as tenu. Prends la Veille… le cœur du Vide, purifié par nos prières. Nous ne la donnons… qu'à un champion.",
                   "You held. Take the Vigil… the Void's heart, purified by our prayers. We give it… only to a champion."),
    "recevoir": ("Recevoir la Veille des Slothians", "Receive the Slothian Vigil"),
    "fin": ("Tu as marché… de la prairie… jusqu'ici. Tous les peuples… te connaissent. Veille… sur eux.",
            "You walked… from the meadow… to here. Every people… knows you. Watch… over them."),
}
REQUEST_TEXTS = {
    "Slothian_Gather_Ash": ("Des cendres", "Some ash", "deposit"),
    "Slothian_Gather_Volcanic": ("Pierre volcanique", "Volcanic stone", "deposit"),
    "Slothian_Gather_Void": ("Essences du Vide", "Void essences", "deposit"),
    "Slothian_Gather_Mushroom": ("Champignons rouges", "Red mushrooms", "deposit"),
    "Slothian_Craft_Candles": ("Des cierges", "Candles", "craft"),
    "Slothian_Hunt_Crawlers": ("Chasser les rampants", "Hunt the crawlers", ("Créatures du Vide abattues", "Void creatures slain", "Elles rôdent", "They prowl")),
    "Slothian_Hunt_Crystals": ("Briser les cristaux", "Break the crystals", ("Cristaux brisés", "Crystals broken", "Ils poussent", "They grow")),
    "Slothian_Delivery_Missive": ("Message au guetteur", "Word to the lookout", "missive"),
    "Slothian_Escort_Pilgrim": ("Ramener le pèlerin", "Bring back the pilgrim", ("Délivre le pèlerin slothian et ramène-le au monastère", "Free the Slothian pilgrim and bring them back to the monastery")),
    "Slothian_Defense_Night": ("Garder le monastère", "Guard the monastery", "defense"),
    "Slothian_Chain_Crystals": ("Les cristaux d'anomalie", "The anomaly crystals", ("Cristaux brisés", "Crystals broken", "Ils chantent", "They sing")),
    "Slothian_Chain_Monk": ("Le moine perdu", "The lost monk", ("Retrouve Frère Lenteur et ramène-le au monastère", "Find Brother Slowness and bring him back to the monastery")),
    "Slothian_Chain_Rift": ("Tenir la faille", "Hold the rift", "defense"),
}


def texts():
    t("people.Slothian.name", "Slothians", "Slothians")
    t("marker.Slothian", "Monastère slothian", "Slothian monastery")
    t(f"items.Nakasar_Peuples_Board_{PID}.name", "Tableau du monastère", "Monastery board")
    t(f"items.Nakasar_Peuples_Board_{PID}.description", "Les demandes du village, sa jauge d'essor et le contenu de son dépôt.",
      "The village's requests, its growth gauge and the contents of its deposit.")
    t(f"items.Nakasar_Peuples_Banner_{PID}.name", "Brasero du monastère", "Monastery brazier")
    t(f"items.Nakasar_Peuples_Banner_{PID}.description", "Marque le monastère sur la carte des voyageurs qui passent à proximité.",
      "Marks the monastery on the map of travellers passing nearby.")
    t(f"items.Nakasar_Peuples_Favor_{PID}.name", "Cendre bénie", "Blessed ash")
    t(f"items.Nakasar_Peuples_Favor_{PID}.description",
      "La faveur des Slothians : donnée pour une demande remplie, elle se dépense à leurs échoppes.",
      "The Slothians' favour: given for a fulfilled request, spent at their stalls.")
    t(f"items.Nakasar_Peuples_Missive_{PID}.name", "Missive slothiane", "Slothian missive")
    t(f"items.Nakasar_Peuples_Missive_{PID}.description", "Une feuille pliée, écrite très lentement. À remettre au guetteur indiqué par la demande.",
      "A folded leaf, written very slowly. Give it to the lookout named by the request.")
    t("absent.voice.Slothian", "« {who}… dort ailleurs, cette nuit. Il reviendra… au matin. Doucement. »",
      "“{who}… sleeps elsewhere tonight. They'll be back… in the morning. Gently.”")
    for kind, (fr, en) in {"Crier": ("Crieur slothian", "Slothian crier"), "Lookout": ("Guetteur slothian", "Slothian lookout"),
                           "Captive": ("Moine égaré", "Lost monk"), "Merchant": ("Marchand slothian", "Slothian merchant"),
                           "Chief": ("Abbé du monastère", "Monastery abbot"), "Defender": ("Gardien slothian", "Slothian warden"),
                           "Builder": ("Bâtisseur slothian", "Slothian builder"), "Watcher": ("Guetteur slothian", "Slothian watcher"),
                           "AshBearer": ("Porteur de cendres", "Ash bearer"), "Guard": ("Garde slothian", "Slothian guard"),
                           "Breeder": ("Gardien de la bauge", "Pen keeper"),
                           "Monk": ("Moine slothian", "Slothian monk"), "Elder": ("Doyenne slothiane", "Slothian dean")}.items():
        t(f"npc.{PID}_{kind}.name", fr, en)
    for bid, fr, en in [("Hutte_Ouest", None, None), ("Hutte_Est", None, None),
                        ("Etal_Des_Cendres", "Étal des cendres", "Ash stall"), ("Affut", "Affût", "Hide"),
                        ("Maison_Nord_Ouest", "Maison du nord-ouest", "North-west house"),
                        ("Maison_Sud_Est", "Maison du sud-est", "South-east house"),
                        ("Porte_Du_Monastere", "Porte du monastère", "Monastery gate"),
                        ("Temple_De_Veille", "Temple de veille", "Vigil temple"),
                        ("Grande_Maison_Slothian", "Grande maison", "Great house"), ("Hutte_Nord", "Hutte du nord", "North hut"),
                        ("Monastere", "Monastère", "Monastery"), ("Porte_Riche", "Porte des pèlerins", "Pilgrims' gate"),
                        ("Bauge_De_Veille", "Bauge de veille", "Vigil pen")]:
        if fr:
            t(f"building.{bid}", fr, en)
    t("job.Porteur_Cendres", "Porteur de cendres", "Ash bearer")
    t("job.Moine", "Moine", "Monk")
    t("job.Gardien_Bauge", "Gardien de la bauge", "Pen keeper")
    t("job.Doyen", "Doyenne du monastère", "Dean of the monastery")
    t(f"dialogue.hint.reward.{PID}", "reçois la Veille des Slothians", "receive the Slothian Vigil")
    t(f"dialogue.hint.chainGive.{PID}", "rend 16 Cendres (étape 1 de la chaîne)", "hand over 16 Ash (chain step 1)")
    for rank, rfr, ren in (("Tolere", "Toléré", "Tolerated"), ("Ami", "Ami", "Friend"), ("Hote", "Hôte", "Host"),
                           ("Champion", "Champion", "Champion")):
        t(f"dialogue.fail.rank.{rank}.{PID}", f"il faut être {rfr} des Slothians", f"you must be {ren} of the Slothians")
    t("dialogue.fail.building.Temple_De_Veille", "il faut que le temple de veille soit debout (palier Village)",
      "the vigil temple must be standing (Village tier)")
    for kind, table in (("Crieur", CRIER), ("Marchand", MERCHANT)):
        for k, (fr, en) in table.items():
            t(f"dialogue.{PID}_{kind}.{k}", fr, en)
    for job, table in JOBS.items():
        for k, (fr, en) in table.items():
            t(f"dialogue.{PID}_{job}.{k}", fr, en)
    for k, (fr, en) in CHAIN_TEXTS.items():
        t(f"dialogue.{PID}_Chef.{k}", fr, en)
    for i, (fr, en) in enumerate([
            ("porter les cendres (16 Cendres, rang Toléré)", "carry the ashes (16 Ash, Tolerated)"),
            ("briser 3 cristaux d'anomalie (rang Ami)", "break 3 anomaly crystals (Friend)"),
            ("ramener le moine perdu (rang Ami)", "bring back the lost monk (Friend)"),
            ("tenir la faille une nuit (rang Hôte)", "hold the rift for a night (Host)"),
            ("recevoir la Veille des Slothians (rang Champion)", "receive the Slothian Vigil (Champion)")], start=1):
        t(f"chain.{PID}.step{i}", fr, en)

    # Demandes (même gabarit que l'étape 8).
    for tid, (fr, en, kind) in REQUEST_TEXTS.items():
        if len(fr) > TITLE_MAX or len(en) > TITLE_MAX:
            raise SystemExit(f"titre trop long ({TITLE_MAX} max) : {tid} « {fr} » / « {en} »")
        t(f"request.{tid}.title", fr, en)
        if kind == "deposit":
            task = ("Dépose {count}/{needed} {item} au dépôt du village ({distance} blocs, {direction}).",
                    "Drop {count}/{needed} {item} in the village deposit ({distance} blocks, {direction}).")
        elif kind == "craft":
            task = ("Fabrique et dépose {count}/{needed} {item} au dépôt ({distance} blocs, {direction}).",
                    "Craft and drop {count}/{needed} {item} in the deposit ({distance} blocks, {direction}).")
        elif kind == "missive":
            task = ("Remets la missive au guetteur, à {distance} blocs, {direction}.",
                    "Give the missive to the lookout, {distance} blocks away, {direction}.")
        elif kind == "defense":
            task = ("Repousse la montée du Vide de la nuit sur le monastère. Son cœur est à {distance} blocs, {direction}.",
                    "Repel tonight's rising of the Void on the monastery. Its heart is {distance} blocks away, {direction}.")
        elif len(kind) == 4:
            task = (kind[0] + " : {count}/{needed}. " + kind[2] + " à {distance} blocs, {direction}.",
                    kind[1] + ": {count}/{needed}. " + kind[3] + " {distance} blocks away, {direction}.")
        else:
            task = (kind[0] + " : {distance} blocs, {direction}.", kind[1] + ": {distance} blocks, {direction}.")
        t(f"request.{tid}.task", *task)

    # Raids du Vide.
    t(f"raid.enemy.{PID}", "une montée du Vide", "a rising of the Void")
    t(f"raid.event.name.{PID}", "Montée du Vide", "Rising of the Void")
    t(f"raid.map.arrivesIn.{PID}", "Le Vide monte dans {time}", "The Void rises in {time}")
    t(f"raid.title.warningSub.{PID}", "Le Vide s'agite, direction {direction}", "The Void stirs, from the {direction}")
    t(f"raid.title.wave.{PID}", "Le Vide monte !", "The Void rises!")
    t(f"raid.report.lost.timeout.{PID}",
      "Bilan de la nuit sur {village} : défaite. Le Vide tenait encore le monastère au bout de l'assaut ({killed}/{raiders} abattus). Incendié : {building}. Le village perd un palier.",
      "Night report for {village}: defeat. The Void still held the monastery at the end of the assault ({killed}/{raiders} slain). Burned: {building}. The village loses a tier.")
    t(f"raid.report.lost.abandon.{PID}",
      "Bilan de la nuit sur {village} : défaite. Personne n'est resté pour veiller ({killed}/{raiders} abattus). Incendié : {building}. Le village perd un palier.",
      "Night report for {village}: defeat. No one stayed to keep watch ({killed}/{raiders} slain). Burned: {building}. The village loses a tier.")
    t(f"raid.report.lost.guards.{PID}",
      "Bilan de la nuit sur {village} : défaite. Tous les gardiens sont tombés et le Vide a atteint le cœur du monastère ({killed}/{raiders} abattus). Incendié : {building}. Le village perd un palier.",
      "Night report for {village}: defeat. All the wardens fell and the Void reached the heart of the monastery ({killed}/{raiders} slain). Burned: {building}. The village loses a tier.")
    t(f"raid.status.warn.{PID}", "Le Vide monte : il sera là dans {seconds} s.", "The Void is rising: it will be here in {seconds} s.")
    t(f"raid.cause.Random.{PID}", "la faille s'agite", "the rift stirs")
    for suffix, fr, en in [("Void_Larva", "Larve du Vide", "Void larva"), ("Void_Crawler", "Rampant du Vide", "Void crawler"),
                           ("Void_Skeleton_Soldier", "Soldat brûlé", "Burnt soldier"),
                           ("Void_Skeleton_Knight", "Chevalier brûlé", "Burnt knight")]:
        t(f"npc.Raider_{suffix}.name", fr, en)
    t("items.Nakasar_Peuples_Trophy_Void.name", "Trophée du Vide", "Void trophy")
    t("items.Nakasar_Peuples_Trophy_Void.description", "Une essence arrachée au Vide, la nuit où il a reculé devant le monastère.",
      "An essence torn from the Void, the night it fell back before the monastery.")

    # Objets de la zone 4 et de l'avant-poste.
    t("items.Nakasar_Peuples_Monk_Robe.name", "Robe du moine", "Monk's robe")
    t("items.Nakasar_Peuples_Monk_Robe.description", "Tissée dans la cendre bénie. Portée, la corruption du Vide ne monte plus.",
      "Woven with blessed ash. Worn, the Void's corruption no longer rises.")
    t("items.Nakasar_Peuples_Vigil.name", "Veille des Slothians", "Slothian Vigil")
    t("items.Nakasar_Peuples_Vigil.description",
      "Le cœur du Vide, purifié par les moines. Tant que tu la portes, le Vide ne te ronge pas et les peuples te savent veilleur.",
      "The Void's heart, purified by the monks. While you carry it, the Void does not gnaw at you and the peoples know you as a watcher.")
    t("items.Nakasar_Peuples_Foundation_Stone.name", "Pierre de fondation", "Foundation stone")
    t("items.Nakasar_Peuples_Foundation_Stone.description",
      "Offerte aux champions. Utilise-la là où tu veux fonder un avant-poste d'un peuple qui t'a fait champion.",
      "Given to champions. Use it where you want to found an outpost of a people that made you their champion.")

    k = "climate."
    t(k + "void.start", "Le Vide te ronge. Reste près d'un brasero, d'un feu ou du monastère.",
      "The Void gnaws at you. Stay near a brazier, a fire or the monastery.")
    t(k + "status.void", "Climat : corruption du Vide, {stacks}/{max} piles.", "Climate: Void corruption, {stacks}/{max} stacks.")
    t(k + "reveal.Slothian", "Le Manteau du givre se réchauffe vers l'est : un brasero brûle au monastère {village}, en {x} {z} ({distance} blocs).",
      "The Frost Mantle warms towards the east: a brazier burns at the {village} monastery, at {x} {z} ({distance} blocks).")
    t("command.climate.void", "Climat imposé : corruption du Vide de la zone 4 (loin d'un brasero, d'un feu ou du monastère).",
      "Forced climate: zone 4 Void corruption (away from a brazier, a fire or the monastery).")
    t("entry.subtitleVigil", "{people} · {rank} · Veilleur du Vide", "{people} · {rank} · Watcher of the Void")
    t("reputation.allyGain", "+{amount} auprès des {people} (ils entendent parler de ton aide aux {helped})",
      "+{amount} with the {people} (they hear of your help to the {helped})")

    # Avant-poste du champion (outpost/).
    o = "outpost."
    t(o + "title", "Fonder un avant-poste", "Found an outpost")
    t(o + "where", "Pierre de fondation posée en {x} {z}, à {distance} blocs de {village}.",
      "Foundation stone placed at {x} {z}, {distance} blocks from {village}.")
    t(o + "whereAlone", "Pierre de fondation posée en {x} {z}.", "Foundation stone placed at {x} {z}.")
    t(o + "footer", "L'avant-poste prend le nom que choisit son peuple ; ses colons arrivent au matin suivant.",
      "The outpost takes the name its people choose; its settlers arrive the next morning.")
    t(o + "found", "Fonder l'avant-poste", "Found the outpost")
    t(o + "cancel", "Annuler", "Cancel")
    t(o + "choose", "Choisir", "Choose")
    t(o + "chosen", "Choisi", "Chosen")
    t(o + "ok", "Champion des {people} ✓", "Champion of the {people} ✓")
    t(o + "okPaint", "Peinture de guerre ✓", "War Paint ✓")
    t(o + "need", "Il faut être Champion des {people}", "You must be Champion of the {people}")
    t(o + "needTrork", "Il faut être Champion des Trorks, ou porter la Peinture de guerre",
      "You must be Champion of the Trorks, or wear the War Paint")
    for pid, fr, en, dfr, den in [
            ("Kweebec", "Hameau kweebec", "Kweebec hamlet", "3 colons, un dépôt et un tableau. Palier 0, grandit comme un village.",
             "3 settlers, a deposit and a board. Tier 0, grows like a village."),
            ("Trork", "Feu de clan trork", "Trork clan fire", "Un camp trork apprivoisé : gardes et guerriers, ses propres demandes.",
             "A tamed Trork camp: guards and warriors, its own requests."),
            ("Feran", "Halte feran", "Feran waystation", "Une oasis feran : huttes, porteuse d'eau, abri contre la soif.",
             "A Feran oasis: huts, water carrier, a shelter from thirst."),
            ("Renonce", "Refuge des Renoncés", "Forsworn refuge", "Un hameau renoncé : abri contre le froid et tour de guet.",
             "A Forsworn hamlet: shelter from the cold and a watchtower."),
            ("Slothian", "Ermitage slothian", "Slothian hermitage", "Un ermitage slothian : brasero contre le Vide, 3 colons.",
             "A Slothian hermitage: a brazier against the Void, 3 settlers.")]:
        t(o + f"option.{pid}", fr, en)
        t(o + f"option.{pid}.desc", dfr, den)
    t(o + "stoneGiven", "Les {people} te font champion : ils t'offrent une Pierre de fondation pour bâtir un avant-poste à leur image.",
      "The {people} make you their champion: they give you a Foundation Stone to build an outpost in their image.")
    t(o + "noChoice", "Choisis d'abord un avant-poste dans la liste.", "Choose an outpost from the list first.")
    t(o + "locked", "Tu ne remplis pas la condition de cet avant-poste.", "You don't meet this outpost's condition.")
    t(o + "tooClose", "Trop près de {name} ({distance} blocs ; il en faut {min}). Éloigne-toi avant de poser la pierre.",
      "Too close to {name} ({distance} blocks; {min} needed). Move away before placing the stone.")
    t(o + "noStone", "Il te faut une Pierre de fondation.", "You need a Foundation Stone.")
    t(o + "pending", "Avant-poste {people} prévu en {x} {z} : ses colons arrivent au matin (6 h).",
      "{people} outpost planned at {x} {z}: its settlers arrive in the morning (6:00).")
    t(o + "alreadyPending", "Un de tes avant-postes attend déjà ses colons en {x} {z}.",
      "One of your outposts is already waiting for its settlers at {x} {z}.")
    t(o + "built", "Les colons sont arrivés : l'avant-poste {name} est fondé en {x} {z}.",
      "The settlers have arrived: the outpost {name} is founded at {x} {z}.")
    t(o + "failed", "Les colons n'ont pas pu s'installer en {x} {z} : {reason} La pierre t'est rendue.",
      "The settlers could not settle at {x} {z}: {reason} The stone is given back to you.")
    t(o + "list", "Avant-postes : {count}.", "Outposts: {count}.")
    t(o + "listLine", "{people} en {x} {z}, de {owner}{state}", "{people} at {x} {z}, by {owner}{state}")
    t(o + "stateWaiting", " (colons attendus au matin)", " (settlers expected in the morning)")
    t(o + "stateBuilt", " : {name}", ": {name}")
    t("command.outpost.desc", "Avant-postes : liste, ou pierre (ops) pour en recevoir une, ou finir (ops) pour les bâtir tout de suite",
      "Outposts: list, or pierre (ops) to get a stone, or finir (ops) to build them right away")
    t("command.outpost.arg", "liste, pierre ou finir", "liste, pierre or finir")
    t("command.outpost.stone", "Pierre de fondation reçue.", "Foundation stone received.")
    t("command.outpost.finished", "{count} avant-poste(s) lancé(s).", "{count} outpost(s) started.")


def write_langs():
    for locale, table in (("fr-FR", FR), ("en-US", EN)):
        path = RES / f"Languages/{locale}/nakasar_peuples.lang"
        text = path.read_text(encoding="utf-8")
        if LANG_BEGIN in text:
            before, rest = text.split(LANG_BEGIN, 1)
            after = rest.split(LANG_END, 1)[1].lstrip("\n")
            text = before + after
        existing = {line.split("=", 1)[0].strip() for line in text.splitlines() if "=" in line and not line.startswith("#")}
        dup = sorted(k for k in table if k in existing)
        if dup:
            raise SystemExit(f"clés déjà présentes dans {locale} (hors bloc étape 9) : {dup[:10]}")
        block = [LANG_BEGIN] + [f"{k} = {v}" for k, v in table.items()] + [LANG_END, ""]
        path.write_text("\n".join(block) + text, encoding="utf-8")
        print(f"{path.relative_to(ROOT)} : {len(table)} clés de l'étape 9")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", type=Path, help="dossier où écrire l'aperçu PNG du plan")
    args = parser.parse_args()
    bounds = gl.load_bounds()
    doc, rects, errors = gl.build(SPEC["layout"], SPEC["layout_spec"], bounds)
    for e in errors:
        print("ERREUR", e)
    doc["$Comment"] = doc["$Comment"].replace("generate_village_layouts.py", "generate_slothians.py (étape 9)")
    write(RES / f"Nakasar/VillageLayouts/{SPEC['layout']}.json", doc)
    print(f"plan {SPEC['layout']} : {len(doc['Buildings'])} bâtiments, rayon {doc['Radius']}")
    if args.preview:
        gl.preview(SPEC["layout"], doc, rects, args.preview)

    gz.service_roles(PID, SPEC)
    gz.job_roles(PID, SPEC)
    gz.defender(PID, SPEC)
    raiders()
    gz.raid_event(PID, "Void")
    gz.copy_dialogue(PID, "Crieur")
    gz.copy_dialogue(PID, "Marchand")
    for tid, kind, extra, essor, favors in REQUESTS:
        write(RES / f"Nakasar/Requests/{PID}/{tid}.json", gz.request_doc(PID, tid, kind, extra, essor, favors))
    steps = {"give": CHAIN["give"]}
    for n, tid, kind, extra, rep, fav, rank in CHAIN["templates"]:
        write(RES / f"Nakasar/Requests/{PID}/{tid}.json", gz.chain_doc(PID, n, tid, kind, extra, rep, fav))
        steps[n] = (tid, rank)
    write(RES / f"Nakasar/Dialogues/{PID}/{PID}_Chef.json", gz.chain_dialogue(PID, steps, CHAIN["reward"]))
    gz.people_items(PID, SPEC)
    write(RES / f"NPC/Reputation/Groups/Nakasar_Peuples_{PID}.json",
          {"$Comment": "Réputation de peuple slothian (étape 9) : ReputationPlugin vanilla. Le jeu n'a pas de groupe de PNJ "
                       "slothian vanilla (rôle Slothian abstrait) : seuls les Slothians du mod comptent.",
           "NPCGroups": [f"Nakasar_Peuples_{PID}"], "InitialReputationValue": 0})
    shops()
    trophy()
    zone_items()
    map_icon()
    texts()
    # Les commentaires des assets copiés par les fonctions de l'étape 8 citent generate_zones.py : on rectifie.
    for path in list(RES.rglob(f"*{PID}*.json")):
        raw = path.read_text(encoding="utf-8")
        fixed = raw.replace("(étape 8), généré par tools/generate_zones.py", "(étape 9), généré par tools/generate_slothians.py") \
                   .replace("(étape 8), générée par tools/generate_zones.py", "(étape 9), générée par tools/generate_slothians.py") \
                   .replace("généré par tools/generate_zones.py (étape 8)", "généré par tools/generate_slothians.py (étape 9)") \
                   .replace("(étape 8)", "(étape 9)")
        if fixed != raw:
            path.write_text(fixed, encoding="utf-8")
    write_langs()
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
