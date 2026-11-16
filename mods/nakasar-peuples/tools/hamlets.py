"""Lieux-dits entre les villages (Kevin, 2026-11-16).

Un lieu-dit n'est pas un village : un groupe de 1 à 3 bâtiments proches (mine isolée, ferme, moulin, caserne et ses
deux tours de guet, forge...), comme les auberges de relais du monde vivant. Les marchands et caravanes des villages
voisins viennent y commercer (Java world/Hamlets, world/HamletTrips).

Repère local : l'origine est la place du lieu-dit (là où attendent les marchands et où vivent les habitants), le
bâtiment principal est au nord (-z) à MAIN_GAP blocs, les autres à l'ouest (« W ») ou à l'est (« E ») de lui, à
SIDE_GAP blocs ; la place regarde la route (Java : rotation selon le côté de la route, comme les avant-postes).

Bâtiments : (chemin du prefab vanilla, côté, chance). Côté None = principal (toujours). Sur un même côté, plusieurs
choix s'excluent : on tire une fois pour le côté, chaque choix a sa chance (la somme peut rester sous 1 : rien sur ce
côté). Il n'existe pas de moulin ni de forge vanilla : ce sont des compositions (grange, silo, établis vanilla posés en
décor devant la forge).

Prefabs, objets et apparences vanilla seulement (règle n° 2). Les Kweebecs ne minent pas et n'utilisent pas de métal
(Kevin, 2026-11-16) : ni mine ni forge chez eux, un bosquet d'herboriste à la place. Lu par tools/generate_hamlets.py.
"""
import outposts

NPC = "Npc/"
MON = "Monuments/"
ROCKS = outposts.ROCKS
LUMBER = outposts.LUMBER
SLOTH = MON + "Incidental/Slothian/Land/"
TRADE = MON + "Encounter/Zone2/Tier3/Tradingpost/"
Z4 = MON + "Encounter/Zone4/Tier4/Village/Farm/"

MAIN_GAP = 4
SIDE_GAP = 3

# Types, dans l'ordre des textes. Règle du terrain préférée (Java Hamlets, mêmes tests que les avant-postes) : un site
# qui ne la remplit pas reste possible si aucun autre ne convient.
TYPES = ["Mine", "Ferme", "Moulin", "Caserne", "Forge", "Comptoir", "Scierie", "Chasse", "Bosquet"]
RULES = {"Mine": "ROCK", "Ferme": "FERTILE", "Moulin": "FERTILE", "Caserne": "NONE", "Forge": "NONE",
         "Comptoir": "NONE", "Scierie": "TREES", "Chasse": "NONE", "Bosquet": "TREES"}
# Poids du tirage du type (le comptoir et la ferme sont les plus communs).
WEIGHTS = {"Mine": 3, "Ferme": 4, "Moulin": 3, "Caserne": 2, "Forge": 3, "Comptoir": 4, "Scierie": 3, "Chasse": 3, "Bosquet": 3}

NAMES = {  # nom fr, nom en, icône vanilla, accueil fr, accueil en
    "Mine": ("Mine isolée", "Isolated mine", "Tool_Pickaxe_Crude",
             "La veine est bonne, ici. Les marchands viennent de loin pour notre pierre et notre minerai.",
             "The vein is good here. Merchants come from afar for our stone and ore."),
    "Ferme": ("Ferme isolée", "Isolated farm", "Plant_Crop_Wheat_Item",
              "Loin du village, la terre est à nous. On vend ce qu'on récolte à qui passe.",
              "Far from the village, the land is ours. We sell what we harvest to whoever passes by."),
    "Moulin": ("Moulin", "Mill", "Ingredient_Flour",
               "Tout le grain de la région passe par ici. Farine, pâte, pain : il y en a pour tout le monde.",
               "All the grain around here comes through. Flour, dough, bread: there's enough for everyone."),
    "Caserne": ("Caserne", "Barracks", "Weapon_Arrow_Crude",
                "Halte-là ! Ah, un ami. Nos deux tours gardent la route ; on a des flèches et des armes à céder.",
                "Halt! Ah, a friend. Our two towers watch the road; we have arrows and weapons to spare."),
    "Forge": ("Forge", "Forge", "Ingredient_Bar_Iron",
              "Le feu ne s'éteint jamais. Outils, lingots, armes : les caravanes repartent toujours chargées.",
              "The fire never dies. Tools, bars, weapons: the caravans always leave fully loaded."),
    "Comptoir": ("Comptoir commercial", "Trading post", "Furniture_Village_Crate",
                 "Bienvenue au comptoir ! Ce que les caravanes apportent, on le revend. Fais ton choix.",
                 "Welcome to the trading post! What the caravans bring, we sell again. Take your pick."),
    "Scierie": ("Scierie", "Sawmill", "Tool_Hatchet_Crude",
                "On coupe, on scie, on empile. Le bois de toute la vallée sort d'ici.",
                "We fell, we saw, we stack. All the valley's timber comes from here."),
    "Chasse": ("Pavillon de chasse", "Hunting lodge", "Ingredient_Hide_Light",
               "Le gibier abonde dans le coin. Viande, peaux, os : tout se troque.",
               "Game is plentiful around here. Meat, hides, bones: everything can be traded."),
    "Bosquet": ("Bosquet d'herboriste", "Herbalist's grove", "Plant_Crop_Health1",
                "Les plantes rares poussent à l'ombre, loin du bruit. Les guérisseurs des villages en raffolent.",
                "Rare plants grow in the shade, far from the noise. Village healers love them."),
}


def annex(people, t):
    """Les prefabs d'un avant-poste de métier, en lieu-dit (même composition, côtés gardés)."""
    return [(path, side, 1.0) for path, side in outposts.PREFABS[people][t]]


BUILDINGS = {
    "Kweebec": {
        "Ferme": annex("Kweebec", "Ferme") + [(NPC + "Kweebec/Oak/Bunny_Area/Kweebec_Oak_Bunny_Area_003", "E", 0.6)],
        "Moulin": [(NPC + "Kweebec/Redwood/Normal_Plot/House/Kweebec_Redwood_Normal_Plot_House_002", None, 1.0),
                   (NPC + "Kweebec/Redwood/Small_Plot/Farm/Kweebec_Redwood_Small_Plot_Farm_002", "W", 1.0),
                   (NPC + "Kweebec/Oak/Water_Pool/Kweebec_Oak_Water_Pool_005", "E", 1.0)],
        "Caserne": [(NPC + "Kweebec/Oak/Houses_Guard/Kweebec_Oak_Houses_Guard_004", None, 1.0),
                    (NPC + "Kweebec/Oak/Guard_Towers/Kweebec_Oak_Guard_Towers_002", "W", 1.0),
                    (NPC + "Kweebec/Oak/Guard_Towers/Kweebec_Oak_Guard_Towers_005", "E", 1.0)],
        "Comptoir": [(NPC + "Kweebec/Oak/Shops/Kweebec_Oak_Shops_004", None, 1.0),
                     (NPC + "Kweebec/Oak/Shops/Kweebec_Oak_Shops_001", "W", 1.0),
                     (NPC + "Kweebec/Oak/Seats/Small/Kweebec_Oak_Seats_Small_002", "E", 0.7)],
        "Scierie": annex("Kweebec", "Scierie"),
        "Chasse": annex("Kweebec", "Chasse"),
        "Bosquet": annex("Kweebec", "Bosquet"),
    },
    "Trork": {
        "Mine": annex("Trork", "Mine"),
        "Ferme": annex("Trork", "Ferme"),
        "Caserne": [(NPC + "Trork/Warehouse/Trork_Warehouse_Trork_Warehouse_001", None, 1.0),
                    (NPC + "Trork/Tier_1/Watchtower/Trork_Tier_1_Watchtower_001", "W", 1.0),
                    (NPC + "Trork/Tier_2/Watchtower/Trork_Tier_2_Watchtower_002", "E", 1.0)],
        "Forge": [(NPC + "Trork/Tier_3/Store/Trork_Tier_3_Store_001", None, 1.0),
                  (NPC + "Trork/Burrow/Trork_Burrow_Trork_Burrow_001", "W", 0.5),
                  (NPC + "Trork/Tier_2/Store/Trork_Tier_2_Store_001", "E", 0.35),
                  (NPC + "Trork/Tier_1/Watchtower/Trork_Tier_1_Watchtower_001", "E", 0.35)],
        "Comptoir": [(NPC + "Trork/Tier_2/Store/Trork_Tier_2_Store_001", None, 1.0),
                     (NPC + "Trork/Bonfire/Trork_Bonfire_Trork_Bonfire_002", "W", 1.0),
                     (NPC + "Trork/Misc/Large/Trork_Misc_Large_004", "E", 0.7)],
        "Scierie": annex("Trork", "Scierie"),
        "Chasse": annex("Trork", "Chasse"),
    },
    "Feran": {
        "Mine": annex("Feran", "Mine"),
        "Ferme": annex("Feran", "Ferme"),
        "Moulin": [(NPC + "Feran/Tier3/Huts/Feran_Tier3_Huts_001", None, 1.0),
                   (MON + "Incidental/Sandstone/Grass/Well/Incidental_Grass_Well_003", "W", 1.0),
                   (TRADE + "Tent/Encounter_Zone2_Tier3_001", "E", 1.0)],
        "Caserne": [(NPC + "Feran/Tier2/Hut/Feran_Tier2_Hut_003", None, 1.0),
                    (NPC + "Feran/Portals_Oasis/Pillar_Hut/Feran_Tier3_Hut_001", "W", 1.0),
                    (NPC + "Feran/Portals_Oasis/Pillar_Hut/Feran_Tier3_Hut_001", "E", 1.0)],
        "Forge": [(NPC + "Feran/Tier2/Hut/Feran_Tier2_Hut_001", None, 1.0),
                  (ROCKS + "002", "W", 0.5),
                  (TRADE + "Tent/Encounter_Zone2_Tier3_003", "E", 0.35),
                  (NPC + "Feran/Portals_Oasis/Pillar_Hut/Feran_Tier3_Hut_001", "E", 0.35)],
        "Comptoir": [(TRADE + "Building_Small/Encounter_Tier3_Building_Small_002", None, 1.0),
                     (TRADE + "Tent/Encounter_Zone2_Tier3_001", "W", 1.0),
                     (TRADE + "Tent/Encounter_Zone2_Tier3_003", "E", 1.0)],
        "Scierie": annex("Feran", "Scierie"),
        "Chasse": annex("Feran", "Chasse"),
    },
    "Renonce": {
        "Mine": [(MON + "Unique/Start_Mine/Unique_Start_Mine_001", None, 1.0),
                 (NPC + "Outlander/Houses/Tier0/Outlander_Houses_Tier0_002", "W", 1.0),
                 (NPC + "Outlander/Braziers/Outlander_Braziers_Npc_Outlander_Brazier_001", "E", 0.7)],
        "Ferme": annex("Renonce", "Ferme"),
        "Moulin": [(NPC + "Outlander/Houses/Tier1/Outlander_Houses_Tier1_003", None, 1.0),
                   (NPC + "Outlander/Misc/Outlander_Misc_001", "W", 1.0),
                   (NPC + "Outlander/Braziers/Outlander_Braziers_Npc_Outlander_Brazier_001", "E", 0.7)],
        "Caserne": [(NPC + "Outlander/Forts/Tier1/Outlander_Forts_Tier1_006", None, 1.0),
                    (NPC + "Outlander/Towers/Tier1/Outlander_Towers_Tier1_001", "W", 1.0),
                    (NPC + "Outlander/Towers/Tier1/Outlander_Towers_Tier1_003", "E", 1.0)],
        # Cour de forge vanilla (fourneau, tonneaux, caisses) et, tirées au sort, la mine et le comptoir ou la tour.
        "Forge": [(NPC + "Outlander/Misc/Outlander_Misc_003", None, 1.0),
                  (MON + "Unique/Start_Mine/Unique_Start_Mine_001", "W", 0.5),
                  (NPC + "Outlander/Houses/Tier0/Outlander_Houses_Tier0_004", "E", 0.35),
                  (NPC + "Outlander/Towers/Tier1/Outlander_Towers_Tier1_002", "E", 0.35)],
        "Comptoir": [(NPC + "Outlander/Houses/Tier1/Outlander_Houses_Tier1_005", None, 1.0),
                     (NPC + "Outlander/Misc/Outlander_Misc_002", "W", 1.0),
                     (NPC + "Outlander/Braziers/Outlander_Braziers_Npc_Outlander_Brazier_001", "E", 1.0)],
        "Scierie": annex("Renonce", "Scierie"),
        "Chasse": annex("Renonce", "Chasse"),
    },
    "Slothian": {
        "Mine": annex("Slothian", "Mine"),
        "Ferme": annex("Slothian", "Ferme") + [(MON + "Incidental/Volcanic/Farm/Incidental_Volcanic_003", "W", 0.7)],
        "Moulin": [(NPC + "Slothian/Disabled/House/Medium/Slothian_Disabled_House_Medium_002", None, 1.0),
                   (Z4 + "Grainsilo/Encounter_Tier4_Grainsilo_001", "W", 1.0),
                   (MON + "Incidental/Basalt/Farm/Incidental_Basalt_002", "E", 1.0)],
        "Caserne": [(NPC + "Slothian/Disabled/House/Medium/Slothian_Disabled_House_Medium_001", None, 1.0),
                    (SLOTH + "Temple/Incidental_Slothian_Slothian_Temple_003", "W", 1.0),
                    (SLOTH + "Temple/Incidental_Slothian_Slothian_Temple_001", "E", 1.0)],
        "Forge": [(NPC + "Slothian/Disabled/House/Medium/Tall/Slothian_Disabled_House_Medium_Tall_001", None, 1.0),
                  (ROCKS + "003", "W", 0.5),
                  (Z4 + "Marketstall/Encounter_Tier4_Marketstall_001", "E", 0.35),
                  (SLOTH + "Temple/Incidental_Slothian_Slothian_Temple_003", "E", 0.35)],
        "Comptoir": [(SLOTH + "Merchant/Incidental_Slothian_Merchant_Slothian_Merchant_001", None, 1.0),
                     (Z4 + "Marketstall/Encounter_Tier4_Marketstall_001", "W", 1.0),
                     (Z4 + "Storage/Encounter_Tier4_Storage_001", "E", 1.0)],
        "Scierie": annex("Slothian", "Scierie"),
        "Chasse": annex("Slothian", "Chasse"),
    },
}

# Décor de la forge : établis vanilla devant le bâtiment principal (« dx dy dz lacet Bloc », relatifs à la place,
# posés seulement dans l'air sur un sol).
DECOR = {
    "Forge": ["-2 0 -2 0 Bench_Furnace", "2 0 -2 0 Bench_Weapon", "0 0 -2 0 Furniture_Village_Crate"],
    "Moulin": ["2 0 -1 0 Plant_Hay_Bundle", "-2 0 -1 0 Furniture_Village_Crate"],
    "Comptoir": ["-2 0 -1 0 Furniture_Village_Crate", "2 0 -1 0 Furniture_Tavern_Barrel"],
}

# Habitants (1 à 3) : genres de rôles du lieu-dit Nakasar_Peuples_<Peuple>_Hamlet_<Genre> (tools/generate_hamlets.py).
RESIDENTS = {
    "Mine": ["Keeper", "Worker", "Worker"], "Ferme": ["Keeper", "Worker"], "Moulin": ["Keeper", "Worker"],
    "Caserne": ["Keeper", "Sentry", "Sentry"], "Forge": ["Keeper", "Worker"], "Comptoir": ["Keeper", "Worker"],
    "Scierie": ["Keeper", "Worker"], "Chasse": ["Keeper", "Worker"], "Bosquet": ["Keeper", "Worker"],
}

# Apparences vanilla des rôles (tenancier, travailleur, garde).
LOOKS = {
    "Kweebec": {"Keeper": "Kweebec_Sapling_Brown", "Worker": "Kweebec_Sapling_HardHat", "Sentry": "Kweebec_Sapling_Razorleaf"},
    "Trork": {"Keeper": "Trork", "Worker": "Trork_Hunter", "Sentry": "Trork_Warrior"},
    "Feran": {"Keeper": "Feran_Civilian", "Worker": "Feran_Burrower", "Sentry": "Feran_Longtooth"},
    "Renonce": {"Keeper": "Outlander_Peon", "Worker": "Outlander_Peon", "Sentry": "Outlander_Hunter"},
    "Slothian": {"Keeper": "Slothian_Monk", "Worker": "Slothian_Villager", "Sentry": "Slothian_Warrior"},
}

# Troc : (objet, quantité, prix en faveurs du peuple). « {wood} », « {stone} », « {brick} » : matériaux du peuple
# (outposts.MAT). BUSY : en plus quand le lieu-dit est animé (assez de marchands venus en 7 jours).
GOODS = {
    "Mine": [("{stone}", 16, 1), ("Ore_Copper", 4, 2), ("Ingredient_Charcoal", 6, 1)],
    "Ferme": [("Plant_Crop_Wheat_Item", 8, 1), ("Plant_Seeds_Wheat", 4, 1), ("Plant_Crop_Carrot_Item", 6, 1)],
    "Moulin": [("Ingredient_Flour", 6, 1), ("Ingredient_Dough", 4, 1), ("Food_Bread", 3, 1)],
    "Caserne": [("Weapon_Arrow_Crude", 16, 1), ("Furniture_Crude_Torch", 4, 1), ("Potion_Health_Small", 1, 2)],
    "Forge": [("Ingredient_Bar_Copper", 2, 2), ("Tool_Pickaxe_Copper", 1, 3), ("Tool_Hatchet_Copper", 1, 3)],
    "Comptoir": [("Ingredient_Fibre", 12, 1), ("Ingredient_Salt", 4, 1), ("Ingredient_Spices", 3, 1)],
    "Scierie": [("{wood}", 12, 1), ("Ingredient_Stick", 12, 1), ("Wood_Softwood_Planks", 16, 1)],
    "Chasse": [("Food_Wildmeat_Raw", 4, 1), ("Ingredient_Hide_Light", 4, 1), ("Ingredient_Bone_Fragment", 6, 1)],
    "Bosquet": [("Plant_Crop_Health1", 2, 2), ("Plant_Crop_Mana1", 2, 2), ("Plant_Crop_Stamina1", 2, 2)],
}
BUSY = {
    "Mine": [("Ore_Iron", 4, 3), ("{brick}", 16, 2)],
    "Ferme": [("Plant_Crop_Corn_Item", 8, 1), ("Plant_Crop_Tomato_Item", 6, 1)],
    "Moulin": [("Food_Pie_Meat", 1, 1), ("Ingredient_Hay", 8, 1)],
    "Caserne": [("Weapon_Arrow_Iron", 12, 3), ("Armor_Leather_Light_Chest", 1, 4)],
    "Forge": [("Ingredient_Bar_Iron", 2, 3), ("Weapon_Sword_Iron", 1, 5)],
    "Comptoir": [("Ingredient_Bolt_Cotton", 1, 1), ("Tool_Map", 1, 3)],
    "Scierie": [("Wood_Hardwood_Planks", 16, 2), ("Ingredient_Tree_Sap", 4, 1)],
    "Chasse": [("Ingredient_Leather_Medium", 2, 2), ("Food_Wildmeat_Cooked", 4, 1)],
    "Bosquet": [("Plant_Seeds_Health1", 2, 2), ("Plant_Crop_Health2", 1, 4)],
}
# Variantes par peuple : les Kweebecs n'utilisent pas de métal (caserne animée : arcs et flèches simples, cuir).
BUSY_BY_PEOPLE = {
    ("Kweebec", "Caserne"): [("Weapon_Arrow_Crude", 32, 2), ("Armor_Leather_Light_Chest", 1, 4)],
}
# Ce que le lieu-dit rachète aux joueurs (une faveur contre…), comme les voyageurs.
BUYS = {
    "Mine": ("Food_Bread", 4), "Ferme": ("Tool_Hoe_Crude", 1), "Moulin": ("Plant_Crop_Wheat_Item", 16),
    "Caserne": ("Food_Wildmeat_Cooked", 4), "Forge": ("Ingredient_Charcoal", 12), "Comptoir": ("Ingredient_Fibre", 12),
    "Scierie": ("Food_Bread", 4), "Chasse": ("Ingredient_Fibre", 12), "Bosquet": ("Ingredient_Tree_Sap", 6),
}


def types(people):
    """Types de lieux-dits du peuple, dans l'ordre de TYPES."""
    return [t for t in TYPES if t in BUILDINGS[people]]
