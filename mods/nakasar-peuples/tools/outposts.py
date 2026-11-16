"""Avant-postes de métier des villages (Kevin, 2026-11-15).

Un avant-poste est un bâtiment isolé au rôle précis (ferme, mine, scierie, pêcherie, pavillon de chasse, tour de guet),
rattaché à un village de palier 3 au moins. Au panneau du village (onglet « Avant-postes »), un joueur de rang Ami
reçoit la fondation d'un type (matériaux pris au dépôt) ; il la pose où il veut bâtir, entre le bord du village + 20 et
256 blocs du cœur. Si la place ne convient pas, le bloc n'est pas posé et le joueur lit pourquoi ; sinon l'emprise est
aplanie et marquée par le chantier du peuple, et une journée plus tard les prefabs vanilla ci-dessous sont collés.

Repère local : la fondation est à l'origine, le joueur se tenait au sud (+z) et le bâtiment s'étend au nord (-z), à 3
blocs de la fondation ; le tout tourne avec le côté d'où le joueur a posé (Java : annex/Annexes). Les prefabs gardent
leur rotation 0 dans ce repère.

Lu par tools/generate_workshops.py (bâtiments de métier <Peuple>_AP_<Type>, commandes, spécialités, boutiques).
Prefabs, objets et rôles vanilla seulement (règle n° 2), sauf les rôles de villageois du mod.
"""

NPC = "Npc/"
MON = "Monuments/Incidental/Slothian/Land/"
ROCKS = NPC + "Trork/Resource/Rock/Stone/Trork_Resource_Rock_Stone_"
LUMBER = NPC + "Trork/Resource/Lumber/"

ITEM_PREFIX = "Nakasar_Peuples_Annex_"
# Les six types, dans l'ordre de l'onglet. Règle du terrain (Java Annexes.rule) : FERTILE (60 % de terre), ROCK (pierre
# ou flanc de colline à 16 blocs), TREES (6 troncs à 24 blocs), WATER (eau à 12 blocs, emprise au sec), NONE.
TYPES = ["Ferme", "Mine", "Scierie", "Pecherie", "Chasse", "Tour"]
# Types propres à un peuple, à la place d'un type commun (Kevin, 2026-11-16) : les Kweebecs, amis de la nature, ne minent
# pas et n'utilisent pas de métal ; leur bosquet de plantes rares remplace la mine.
REPLACED = {"Kweebec": {"Mine": "Bosquet"}}
# Tous les types, communs puis propres (objets de fondation, textes).
ALL_TYPES = TYPES + sorted({t for r in REPLACED.values() for t in r.values()})


def types(people):
    """Types d'avant-postes du peuple, dans l'ordre de l'onglet."""
    r = REPLACED.get(people, {})
    return [r.get(t, t) for t in TYPES]


RULES = {"Ferme": "FERTILE", "Mine": "ROCK", "Scierie": "TREES", "Pecherie": "WATER", "Chasse": "NONE", "Tour": "NONE",
         "Bosquet": "TREES"}
# Secondes d'annonce de plus avant un raid, par niveau de la tour de guet (Java Raids : 60 s de base).
TOWER_WARN = 30
# Villageois : 2 au niveau I, 1 de plus aux niveaux II et III.
WORKER_TIERS = [1, 1, 2, 3]

NAMES = {  # (nom fr, nom en, rôle fr, rôle en, métier fr, métier en, icône vanilla)
    "Ferme": ("Ferme", "Farm", "Champs et semences ; range du blé dans son coffre chaque matin ; un convoi le porte au village à midi.",
              "Fields and seeds; stores wheat in its chest every morning; a convoy takes it to the village at noon.", "Fermier", "Farmer", "Plant_Crop_Wheat_Item"),
    "Mine": ("Mine", "Mine", "Pierre et métaux ; range de la pierre dans son coffre chaque matin ; un convoi la porte au village à midi.",
             "Stone and metals; stores stone in its chest every morning; a convoy takes it to the village at noon.", "Mineur", "Miner", "Tool_Pickaxe_Crude"),
    "Bosquet": ("Bosquet", "Grove", "Plantes rares et alchimiques ; range des herbes rares dans son coffre chaque matin ; un convoi les porte au village à midi.",
                "Rare and alchemical plants; stores rare herbs in its chest every morning; a convoy takes them to the village at noon.",
                "Herboriste", "Herbalist", "Plant_Crop_Health1"),
    "Scierie": ("Scierie", "Sawmill", "Bois et charpente ; range des rondins dans son coffre chaque matin ; un convoi les porte au village à midi.",
                "Timber and carpentry; stores logs in its chest every morning; a convoy takes them to the village at noon.", "Scieur", "Sawyer", "Tool_Hatchet_Crude"),
    "Pecherie": ("Pêcherie", "Fishery", "Poissons et nasses ; range du poisson dans son coffre chaque matin ; un convoi le porte au village à midi.",
                 "Fish and traps; stores fish in its chest every morning; a convoy takes it to the village at noon.", "Pêcheur", "Fisher", "Food_Fish_Raw"),
    "Chasse": ("Pavillon de chasse", "Hunting lodge", "Gibier et peaux ; range de la viande dans son coffre chaque matin ; un convoi la porte au village à midi.",
               "Game and hides; stores meat in its chest every morning; a convoy takes it to the village at noon.", "Veneur", "Huntsman", "Ingredient_Hide_Light"),
    "Tour": ("Tour de guet", "Watchtower", "Le village voit venir les raids 30 s plus tôt par niveau ; gardes plus nombreux.",
             "The village sees raids coming 30 s earlier per level; more guards.", "Guetteur", "Lookout", "Weapon_Arrow_Crude"),
}

# Matériaux propres au peuple : bois, pierre taillée, brique.
MAT = {
    "Kweebec": dict(wood="Wood_Oak_Trunk", stone="Rock_Stone_Cobble", brick="Rock_Stone_Brick"),
    "Trork": dict(wood="Wood_Birch_Trunk", stone="Rock_Shale_Cobble", brick="Rock_Shale_Brick"),
    "Feran": dict(wood="Wood_Dry_Trunk", stone="Rock_Sandstone_Cobble", brick="Rock_Sandstone_Brick"),
    "Renonce": dict(wood="Wood_Fir_Trunk", stone="Rock_Slate_Cobble", brick="Rock_Stone_Brick"),
    "Slothian": dict(wood="Wood_Jungle_Trunk", stone="Rock_Basalt_Cobble", brick="Rock_Basalt_Brick"),
}

# Fondation : matériaux pris au dépôt du village quand on la reçoit (le chantier d'un emplacement, en plus léger).
FOUNDATION = {
    "Kweebec": [("Wood_Oak_Trunk", 32), ("Rock_Stone_Cobble", 24), ("Ingredient_Fibre", 12)],
    "Trork": [("Wood_Oak_Trunk", 24), ("Ingredient_Hide_Light", 8), ("Ingredient_Bone_Fragment", 16)],
    "Feran": [("Wood_Dry_Trunk", 24), ("Ingredient_Fibre", 12), ("Ingredient_Salt", 6)],
    "Renonce": [("Wood_Fir_Trunk", 32), ("Rock_Stone_Cobble", 24), ("Ingredient_Hide_Heavy", 4)],
    "Slothian": [("Wood_Jungle_Trunk", 24), ("Rock_Volcanic", 24), ("Furniture_Jungle_Candle", 3)],
}

# Prefabs : [chemin, côté] ; le premier est le bâtiment principal (au nord de la fondation), les suivants à l'ouest
# (« W ») ou à l'est (« E ») de lui, à 2 blocs.
PREFABS = {
    "Kweebec": {
        "Ferme": [(NPC + "Kweebec/Redwood/Normal_Plot/Farm/Kweebec_Redwood_Normal_Plot_Farm_001", None),
                  (NPC + "Kweebec/Redwood/Small_Plot/House/Kweebec_Redwood_Small_Plot_House_001", "W")],
        "Bosquet": [(NPC + "Kweebec/Oak/Garden/Large/Kweebec_Oak_Garden_Large_003", None),
                    (NPC + "Kweebec/Oak/Water_Pool/Kweebec_Oak_Water_Pool_005", "W"),
                    (NPC + "Kweebec/Oak/Lampposts/Kweebec_Oak_Lampposts_004", "E")],
        "Scierie": [(NPC + "Kweebec/Redwood/Normal_Plot/House/Kweebec_Redwood_Normal_Plot_House_001", None),
                    (LUMBER + "Forest_Aspen/Trork_Resource_Lumber_Forest_Aspen_001", "E"),
                    (LUMBER + "Forest_Aspen/Trork_Resource_Lumber_Forest_Aspen_002", "W")],
        "Pecherie": [(NPC + "Kweebec/Redwood/Small_Plot/House/Kweebec_Redwood_Small_Plot_House_002", None),
                     (NPC + "Kweebec/Oak/Seats/Small/Kweebec_Oak_Seats_Small_002", "E")],
        "Chasse": [(NPC + "Kweebec/Redwood/Small_Plot/House/Kweebec_Redwood_Small_Plot_House_001", None),
                   (NPC + "Kweebec/Oak/Seats/Small/Kweebec_Oak_Seats_Small_001", "E"),
                   (NPC + "Kweebec/Oak/Lampposts/Kweebec_Oak_Lampposts_008", "W")],
        "Tour": [(NPC + "Kweebec/Oak/Guard_Towers/Kweebec_Oak_Guard_Towers_004", None),
                 (NPC + "Kweebec/Oak/Lampposts/Kweebec_Oak_Lampposts_005", "E")],
    },
    "Trork": {
        "Ferme": [(NPC + "Trork/Tent/Trork_Tent_001", None), (NPC + "Trork/Bonfire/Trork_Bonfire_Trork_Bonfire_002", "E"),
                  (NPC + "Trork/Misc/Large/Trork_Misc_Large_004", "W")],
        "Mine": [(NPC + "Trork/Burrow/Trork_Burrow_Trork_Burrow_002", None), (ROCKS + "001", "E"), (ROCKS + "005", "W")],
        "Scierie": [(NPC + "Trork/Warehouse/Trork_Warehouse_Trork_Warehouse_001", None),
                    (LUMBER + "Forest_Autumn/Trork_Resource_Lumber_Forest_Autumn_001", "E"),
                    (LUMBER + "Forest_Autumn/Trork_Resource_Lumber_Forest_Autumn_003", "W")],
        "Pecherie": [(NPC + "Trork/Tent/Trork_Tent_001", None), (NPC + "Trork/Fireplace/Trork_Fireplace_001", "E"),
                     (NPC + "Trork/Misc/Large/Trork_Misc_Large_005", "W")],
        "Chasse": [(NPC + "Trork/Trap/Trork_Trap_Trork_Trap_001", None), (NPC + "Trork/Tent/Trork_Tent_001", "W")],
        "Tour": [(NPC + "Trork/Tier_1/Watchtower/Trork_Tier_1_Watchtower_001", None),
                 (NPC + "Trork/Warning/Trork_Warning_Trork_Warning_002", "E")],
    },
    "Feran": {
        "Ferme": [(NPC + "Feran/Tier3/Huts/Feran_Tier3_Huts_001", None), (NPC + "Feran/Tier2/Wall/Feran_Tier2_Wall_002", "E")],
        "Mine": [(NPC + "Feran/Tier3/Huts/Feran_Tier3_Huts_001", None), (ROCKS + "002", "E"), (ROCKS + "004", "W")],
        "Scierie": [(NPC + "Feran/Tier3/Huts/Feran_Tier3_Huts_001", None),
                    (LUMBER + "Forest_Gully/Trork_Resource_Lumber_Forest_Gully_001", "E"),
                    (LUMBER + "Forest_Gully/Trork_Resource_Lumber_Forest_Gully_002", "W")],
        "Pecherie": [(NPC + "Feran/Tier3/Huts/Feran_Tier3_Huts_001", None), (NPC + "Feran/Tier2/Wall/Feran_Tier2_Wall_002", "W")],
        "Chasse": [(NPC + "Feran/Tier3/Huts/Feran_Tier3_Huts_001", None),
                   (NPC + "Outlander/Braziers/Outlander_Braziers_Npc_Outlander_Brazier_001", "E")],
        "Tour": [(NPC + "Feran/Portals_Oasis/Pillar_Hut/Feran_Tier3_Hut_001", None)],
    },
    "Renonce": {
        "Ferme": [(NPC + "Outlander/Houses/Tier1/Outlander_Houses_Tier1_004", None),
                  (NPC + "Outlander/Braziers/Outlander_Braziers_Npc_Outlander_Brazier_001", "E")],
        "Mine": [(NPC + "Outlander/Houses/Tier0/Outlander_Houses_Tier0_002", None), (ROCKS + "002", "E"), (ROCKS + "004", "W")],
        "Scierie": [(NPC + "Outlander/Houses/Tier1/Outlander_Houses_Tier1_007", None),
                    (LUMBER + "Forest_Aspen/Trork_Resource_Lumber_Forest_Aspen_003", "E"),
                    (LUMBER + "Forest_Aspen/Trork_Resource_Lumber_Forest_Aspen_004", "W")],
        "Pecherie": [(NPC + "Outlander/Houses/Tier0/Outlander_Houses_Tier0_004", None),
                     (NPC + "Outlander/Boats/Small/Outlander_Boats_Small_001", "E")],
        "Chasse": [(NPC + "Outlander/Houses/Tier1/Outlander_Houses_Tier1_006", None),
                   (NPC + "Outlander/Braziers/Outlander_Braziers_Npc_Outlander_Brazier_001", "W")],
        "Tour": [(NPC + "Outlander/Towers/Tier2/Outlander_Towers_Tier2_002", None)],
    },
    "Slothian": {
        "Ferme": [(MON + "Merchant/Incidental_Slothian_Merchant_Slothian_Merchant_001", None),
                  (NPC + "Outlander/Braziers/Outlander_Braziers_Npc_Outlander_Brazier_001", "E")],
        "Mine": [(NPC + "Slothian/Disabled/House/Small/Slothian_Disabled_House_Small_001", None), (ROCKS + "003", "E")],
        "Scierie": [(NPC + "Slothian/Disabled/House/Small/Slothian_Disabled_House_Small_002", None),
                    (LUMBER + "Forest_Gully/Trork_Resource_Lumber_Forest_Gully_003", "E")],
        "Pecherie": [(NPC + "Slothian/Disabled/House/Small/Slothian_Disabled_House_Small_003", None)],
        "Chasse": [(MON + "Hunting/Incidental_Slothian_Slothian_Hunting_001", None)],
        "Tour": [(MON + "Temple/Incidental_Slothian_Slothian_Temple_003", None)],
    },
}

# Genres de villageois (4 par avant-poste, niveaux 1, 1, 2, 3) : rôles du mod Nakasar_Peuples_<Peuple>_<Genre>, ou
# « @Rôle » vanilla pour les Trorks (pas de dialogue). Pas de Gatherer (ce sont des suiveurs d'escorte) ni de Merchant.
WORKERS = {
    "Kweebec": {"Ferme": ["Gardener", "Gardener", "Breeder", "WellKeeper"], "Bosquet": ["Gardener", "Gardener", "Healer", "Watcher"],
                "Scierie": ["Builder", "Builder", "Gardener", "Watcher"], "Pecherie": ["WellKeeper", "WellKeeper", "Gardener", "Watcher"],
                "Chasse": ["Guard", "Guard", "Breeder", "Healer"], "Tour": ["Lookout", "Guard", "Guard", "Watcher"]},
    "Trork": {"Ferme": ["@Trork_Warrior", "@Trork_Warrior", "@Trork_Brawler", "@Trork_Shaman"],
              "Mine": ["@Trork_Brawler", "@Trork_Brawler", "@Trork_Warrior", "@Trork_Guard"],
              "Scierie": ["@Trork_Warrior", "@Trork_Brawler", "@Trork_Warrior", "@Trork_Sentry"],
              "Pecherie": ["@Trork_Hunter", "@Trork_Warrior", "@Trork_Hunter", "@Trork_Shaman"],
              "Chasse": ["@Trork_Hunter", "@Trork_Hunter", "@Trork_Warrior", "@Trork_Sentry"],
              "Tour": ["@Trork_Sentry", "@Trork_Guard", "@Trork_Guard", "@Trork_Shaman"]},
    "Feran": {"Ferme": ["Breeder", "WellKeeper", "Breeder", "Watcher"], "Mine": ["Builder", "Builder", "Guard", "Watcher"],
              "Scierie": ["Builder", "Builder", "Watcher", "Breeder"], "Pecherie": ["WellKeeper", "WellKeeper", "Breeder", "Watcher"],
              "Chasse": ["Guard", "Guard", "Breeder", "Lookout"], "Tour": ["Lookout", "Guard", "Guard", "Watcher"]},
    "Renonce": {"Ferme": ["Breeder", "Breeder", "Builder", "Watcher"], "Mine": ["Builder", "Builder", "Guard", "Watcher"],
                "Scierie": ["Builder", "Builder", "Hunter", "Watcher"], "Pecherie": ["Hunter", "Hunter", "Builder", "Watcher"],
                "Chasse": ["Hunter", "Hunter", "Guard", "Breeder"], "Tour": ["Lookout", "Guard", "Guard", "Watcher"]},
    "Slothian": {"Ferme": ["Breeder", "Breeder", "Monk", "Watcher"], "Mine": ["Builder", "Builder", "AshBearer", "Guard"],
                 "Scierie": ["Builder", "Builder", "AshBearer", "Watcher"], "Pecherie": ["Monk", "Monk", "Breeder", "Watcher"],
                 "Chasse": ["Guard", "Guard", "Breeder", "Watcher"], "Tour": ["Lookout", "Guard", "Guard", "Monk"]},
}
# Dialogue d'un genre sans fichier <Peuple>_<Genre> (Server/Nakasar/Dialogues) : celui-ci.
DIALOGUE_ALIAS = {"Lookout": "Watcher"}

# Gêneurs à chasser (commande de chasse), par peuple et type : rôles vanilla (tools/vanilla-refs-0.7.2.txt).
HUNTS = {
    "Kweebec": {"Ferme": ["Trork_Hunter", "Trork_Hunter"], "Bosquet": ["Scarak_Louse", "Scarak_Louse", "Scarak_Louse"],
                "Scierie": ["Wolf_Black", "Wolf_Black"], "Pecherie": ["Trork_Warrior", "Trork_Hunter"], "Chasse": ["Mosshorn"],
                "Tour": ["Trork_Warrior", "Trork_Warrior", "Trork_Brawler"]},
    "Trork": {"Ferme": ["Scarak_Louse", "Scarak_Louse"], "Mine": ["Scarak_Fighter", "Scarak_Fighter"],
              "Scierie": ["Wolf_Black", "Wolf_Black"], "Pecherie": ["Outlander_Hunter", "Outlander_Hunter"], "Chasse": ["Mosshorn"],
              "Tour": ["Outlander_Berserker", "Outlander_Cultist"]},
    "Feran": {"Ferme": ["Scarak_Louse", "Scarak_Louse", "Scarak_Louse"], "Mine": ["Scarak_Fighter", "Scarak_Fighter"],
              "Scierie": ["Scarak_Louse", "Scarak_Louse"], "Pecherie": ["Scarak_Fighter", "Scarak_Louse"], "Chasse": ["Mosshorn"],
              "Tour": ["Scarak_Fighter", "Scarak_Fighter", "Scarak_Defender"]},
    "Renonce": {"Ferme": ["Wolf_White", "Wolf_White"], "Mine": ["Outlander_Cultist", "Outlander_Cultist"],
                "Scierie": ["Wolf_White", "Wolf_White"], "Pecherie": ["Outlander_Hunter", "Outlander_Hunter"],
                "Chasse": ["Wolf_White", "Wolf_White", "Wolf_White"],
                "Tour": ["Outlander_Cultist", "Outlander_Cultist", "Outlander_Berserker"]},
    "Slothian": {"Ferme": ["Larva_Void", "Larva_Void", "Larva_Void"], "Mine": ["Crawler_Void", "Crawler_Void"],
                 "Scierie": ["Crawler_Void", "Crawler_Void"], "Pecherie": ["Larva_Void", "Larva_Void"],
                 "Chasse": ["Skeleton_Burnt_Soldier", "Skeleton_Burnt_Soldier"],
                 "Tour": ["Skeleton_Burnt_Soldier", "Skeleton_Burnt_Soldier", "Skeleton_Burnt_Knight"]},
}
HUNT_TITLES = {
    "Ferme": ("Nuisibles des champs", "Pests in the fields"),
    "Mine": ("Menace des galeries", "Threat in the tunnels"),
    "Bosquet": ("Nuisibles du bosquet", "Pests in the grove"),
    "Scierie": ("Rôdeurs des bois", "Prowlers in the woods"),
    "Pecherie": ("Rôdeurs des berges", "Prowlers on the banks"),
    "Chasse": ("Bête de la traque", "Quarry of the hunt"),
    "Tour": ("Éclaireurs ennemis", "Enemy scouts"),
}

# Par type : deux commandes (les commandes de maître I et II les reprennent en grand), puis la chasse ; boutique du
# niveau I ; deux spécialités (id, nom fr, nom en, icône, ligne fr, ligne en, [niveau II], [niveau III], effet en raid) ;
# lot livré chaque matin au dépôt du village (× niveau). « {wood} », « {stone} », « {brick} » : matériaux du peuple.
TYPE_DATA = {
    "Ferme": dict(
        orders=[("Manure", "Gather", "Ingredient_Poop", 10, "Fumier des champs", "Manure for the fields"),
                ("Hoes", "Craft", "Tool_Hoe_Crude", 2, "Houes de la ferme", "Hoes for the farm")],
        base=[("Plant_Seeds_Wheat", 4, 1), ("Plant_Crop_Wheat_Item", 8, 1), ("Plant_Seeds_Carrot", 4, 1)],
        specs=[("Cereales", "Céréales", "Cereals", "Plant_Crop_Corn_Item", "Maïs, riz et semences éternelles.",
                "Corn, rice and eternal seeds.", [("Plant_Crop_Corn_Item", 8, 1), ("Plant_Seeds_Corn", 4, 1)],
                [("Plant_Crop_Rice_Item", 8, 2), ("Plant_Seeds_Wheat_Eternal", 1, 6)], None),
               ("Primeurs", "Primeurs", "Early produce", "Plant_Crop_Tomato_Item", "Tomates, oignons et citrouilles.",
                "Tomatoes, onions and pumpkins.", [("Plant_Crop_Tomato_Item", 6, 1), ("Plant_Crop_Onion_Item", 6, 1)],
                [("Plant_Crop_Pumpkin_Item", 3, 2), ("Plant_Seeds_Tomato_Eternal", 1, 6)], None)],
        delivery=("Plant_Crop_Wheat_Item", 6)),
    "Mine": dict(
        orders=[("Torches", "Craft", "Furniture_Crude_Torch", 6, "Torches des galeries", "Torches for the tunnels"),
                ("Picks", "Craft", "Tool_Pickaxe_Crude", 2, "Pioches des mineurs", "Picks for the miners")],
        base=[("{stone}", 16, 1), ("Ingredient_Bar_Copper", 2, 2), ("Ore_Copper", 4, 2)],
        specs=[("Filons", "Filons de métal", "Metal veins", "Ingredient_Bar_Iron", "Lingots de fer, de bronze, d'argent et d'or.",
                "Iron, bronze, silver and gold bars.", [("Ingredient_Bar_Iron", 2, 3), ("Ingredient_Bar_Bronze", 2, 3)],
                [("Ingredient_Bar_Silver", 2, 5), ("Ingredient_Bar_Gold", 1, 6)], None),
               ("Carriere", "Carrière", "Quarry", "Rock_Marble_Cobble", "Briques, marbre et quartzite.",
                "Bricks, marble and quartzite.", [("{brick}", 16, 1), ("Rock_Marble_Cobble", 8, 2)],
                [("Rock_Quartzite_Brick", 12, 2), ("Rock_Calcite_Brick", 12, 2)], None)],
        delivery=("{stone}", 16)),
    # Bosquet kweebec : plantes alchimiques vanilla (Health = écarlates, Mana = azurées, Stamina = des tempêtes).
    "Bosquet": dict(
        orders=[("Sap", "Gather", "Ingredient_Tree_Sap", 6, "Sève pour les semis", "Sap for the seedlings"),
                ("Hoes", "Craft", "Tool_Hoe_Crude", 2, "Houes des herboristes", "Hoes for the herbalists")],
        base=[("Plant_Crop_Health1", 2, 2), ("Plant_Crop_Mana1", 2, 2), ("Plant_Crop_Stamina1", 2, 2)],
        specs=[("Ecarlate", "Massif écarlate", "Scarlet bed", "Plant_Crop_Health2", "Plantes écarlates rares et leurs graines.",
                "Rare scarlet plants and their seeds.", [("Plant_Crop_Health2", 2, 3), ("Plant_Seeds_Health1", 2, 2)],
                [("Plant_Crop_Health3", 1, 5), ("Plant_Seeds_Health2", 1, 4)], None),
               ("Azur", "Mare azurée", "Azure pond", "Plant_Crop_Mana2",
                "Plantes azurées et chardons des tempêtes, et leurs graines.",
                "Azure plants and storm thistles, and their seeds.",
                [("Plant_Crop_Mana2", 2, 3), ("Plant_Crop_Stamina2", 2, 3)],
                [("Plant_Crop_Mana3", 1, 5), ("Plant_Crop_Stamina3", 1, 5)], None)],
        delivery=("Plant_Crop_Health1", 1), extra=[("Plant_Crop_Mana1", 1), ("Plant_Crop_Stamina1", 1)]),
    "Scierie": dict(
        orders=[("Hatchets", "Craft", "Tool_Hatchet_Crude", 2, "Haches des bûcherons", "Axes for the woodcutters"),
                ("Rope", "Gather", "Ingredient_Fibre", 12, "Fibres des cordages", "Fibre for the ropes")],
        base=[("{wood}", 12, 1), ("Ingredient_Stick", 12, 1), ("Ingredient_Tree_Bark", 6, 1)],
        specs=[("Charpente", "Charpente", "Carpentry", "Wood_Softwood_Planks", "Planches et poutres.", "Planks and beams.",
                [("Wood_Softwood_Planks", 16, 1), ("Wood_Softwood_Beam", 8, 1)],
                [("Wood_Hardwood_Planks", 16, 2), ("Wood_Hardwood_Beam", 8, 2)], None),
               ("Seve", "Sève et graines", "Sap and seeds", "Ingredient_Tree_Sap", "Sève, graines d'arbres et saignoir.",
                "Sap, tree seeds and sap shunt.", [("Ingredient_Tree_Sap", 4, 1), ("Plant_Seeds_Oak", 2, 1)],
                [("Plant_Seeds_Redwood", 2, 3), ("Tool_Sap_Shunt", 1, 4)], None)],
        delivery=("{wood}", 8)),
    "Pecherie": dict(
        orders=[("Traps", "Craft", "Tool_Fishing_Trap", 2, "Nasses de la pêcherie", "Traps for the fishery"),
                ("Sticks", "Gather", "Ingredient_Stick", 12, "Bois des nasses", "Wood for the traps")],
        base=[("Food_Fish_Raw", 4, 1), ("Tool_Trap_Bait", 2, 1), ("Container_Bucket", 1, 1)],
        specs=[("Fumoir", "Fumoir", "Smokehouse", "Food_Fish_Grilled", "Poisson grillé et prises rares.",
                "Grilled fish and rare catches.", [("Food_Fish_Grilled", 4, 1), ("Food_Fish_Raw_Uncommon", 2, 2)],
                [("Food_Fish_Raw_Rare", 2, 4), ("Food_Fish_Raw_Epic", 1, 6)], None),
               ("Viviers", "Viviers", "Fish tanks", "Ingredient_Water_Essence", "Essence d'eau, riz et prise légendaire.",
                "Water essence, rice and a legendary catch.", [("Ingredient_Water_Essence", 3, 2), ("Plant_Seeds_Rice", 4, 1)],
                [("Food_Fish_Raw_Legendary", 1, 8), ("Ingredient_Water_Essence", 8, 4)], None)],
        delivery=("Food_Fish_Raw", 3)),
    "Chasse": dict(
        orders=[("Snares", "Gather", "Ingredient_Fibre", 12, "Fibres des collets", "Fibre for snares"),
                ("Scrapers", "Craft", "Tool_Bark_Scraper", 2, "Racloirs à peaux", "Hide scrapers")],
        base=[("Food_Wildmeat_Raw", 4, 1), ("Ingredient_Hide_Light", 4, 1), ("Ingredient_Bone_Fragment", 6, 1)],
        specs=[("Pelleterie", "Pelleterie", "Furriery", "Ingredient_Leather_Medium", "Peaux et cuirs moyens et lourds.",
                "Medium and heavy hides and leathers.", [("Ingredient_Hide_Medium", 4, 2), ("Ingredient_Leather_Light", 4, 2)],
                [("Ingredient_Hide_Heavy", 3, 3), ("Ingredient_Leather_Heavy", 3, 4)], None),
               ("Venerie", "Vénerie", "Venery", "Food_Wildmeat_Cooked", "Viande cuite, appâts, caisses de capture.",
                "Cooked meat, bait, capture crates.", [("Food_Wildmeat_Cooked", 4, 1), ("Tool_Trap_Bait", 2, 1)],
                [("Tool_Capture_Crate", 1, 5), ("Weapon_Arrow_Iron", 12, 3)], None)],
        delivery=("Food_Wildmeat_Raw", 3)),
    "Tour": dict(
        orders=[("Logs", "Gather", "{wood}", 16, "Rondins de la tour", "Logs for the tower"),
                ("Spears", "Craft", "Weapon_Spear_Crude", 3, "Lances des guetteurs", "Spears for the watch")],
        base=[("Weapon_Arrow_Crude", 16, 1), ("Furniture_Crude_Torch", 4, 1)],
        specs=[("Guetteurs", "Guetteurs", "Watchmen", "Tool_Map", "Cartes et torches ; en raid, +1 garde au village.",
                "Maps and torches; in raids, +1 guard in the village.", [("Tool_Map", 1, 3), ("Furniture_Crude_Torch", 8, 1)],
                [("Weapon_Arrow_Iron", 16, 3), ("Weapon_Shortbow_Crude", 1, 3)], {"Guards": 1}),
               ("Sentinelles", "Sentinelles", "Sentinels", "Armor_Leather_Light_Chest",
                "Armure légère ; en raid, des gardes plus solides.", "Light armour; sturdier guards in raids.",
                [("Armor_Leather_Light_Chest", 1, 4), ("Potion_Health_Small", 2, 2)],
                [("Weapon_Spear_Stone_Trork", 1, 4), ("Potion_Health_Small", 4, 3)], {"Health": 1.25})],
        delivery=None),
}
# Les Trorks ne subissent pas de raid : leur tour n'a pas d'effet en raid (spécialités sans « Raid »).
NO_RAID = {"Trork"}

# Textes des messages et de l'onglet (Java annex/), fr puis en, clés sans le préfixe « nakasar_peuples. ».
# Balise de route (Java annex/Routes) : liens à 64 blocs = Routes.LINK. Plusieurs modèles vanilla, tous la même
# balise (Routes.isBeacon : id = Routes.BEACON ou Routes.BEACON + "_<Variante>") et mélangeables sur une même route.
# Chaque variante a sa recette à l'établi (même coût). L'id de base garde la haute lanterne du désert (balises déjà
# posées) ; le kit de la quête « Baliser une route » donne la petite lanterne (generate_quests.ROUTE_KIT_ITEM).
BEACON = {
    "item": "Nakasar_Peuples_Route_Beacon",
    "recipe": [("Ingredient_Stick", 4), ("Furniture_Crude_Torch", 1)],
    "output": 2,
    "name": ("Balise de route", "Route beacon"),
    "description": ("Les convois et les voyageurs vont de balise en balise. Deux balises à moins de 64 blocs sont reliées, "
                    "quel que soit leur modèle.",
                    "Convoys and travellers walk from beacon to beacon. Two beacons less than 64 blocks apart are linked, "
                    "whatever their model."),
    # (suffixe d'id, parent vanilla, nom fr, nom en) ; suffixe vide = l'id de base.
    "variants": [
        ("", "Furniture_Desert_Lantern_Tall", "haute lanterne", "tall lantern"),
        ("Lantern", "Deco_Lantern", "petite lanterne", "small lantern"),
        ("Kweebec", "Furniture_Kweebec_Lantern", "lanterne kweebec", "Kweebec lantern"),
        ("Lumberjack", "Furniture_Lumberjack_Lantern", "lanterne de bûcheron", "lumberjack lantern"),
        ("Torch", "Furniture_Crude_Torch", "torche", "torch"),
        ("Desert_Torch", "Furniture_Desert_Torch", "torche du désert", "desert torch"),
        ("Feran_Torch", "Furniture_Feran_Torch_Tall", "grande torche feran", "tall Feran torch"),
    ],
}


def beacon_id(suffix):
    """Id de l'objet (et du bloc) d'une variante de balise."""
    return BEACON["item"] + ("_" + suffix if suffix else "")


LANG = {
    "annex.button": ("Avant-postes", "Outposts"),
    "annex.none": ("Ce peuple ne fonde pas d'avant-postes.", "This people founds no outposts."),
    "annex.page.title": ("Avant-postes de {village}", "Outposts of {village}"),
    "annex.page.orphan": ("Ce village n'existe plus.", "This village no longer exists."),
    "annex.page.intro": ("Recevez la fondation d'un avant-poste, puis posez-la là où vous voulez bâtir, entre {min} et {max} blocs du cœur du village. Les travaux durent une journée.",
                         "Receive an outpost's foundation, then place it where you want to build, {min} to {max} blocks from the village heart. The works take one day."),
    "annex.page.rule": ("Village de palier {tier} au moins, rang {rank} pour recevoir et poser une fondation. Un avant-poste de chaque type par village ; un avant-poste debout ou en travaux peut être détruit (rang {rank}).",
                        "Village of tier {tier} or more, rank {rank} to receive and place a foundation. One outpost of each type per village; a standing outpost or one under construction can be destroyed (rank {rank})."),
    "annex.page.back": ("Retour au panneau", "Back to the board"),
    "annex.page.grant": ("Recevoir la fondation", "Receive the foundation"),
    "annex.page.regive": ("Reprendre la fondation", "Take the foundation again"),
    "annex.page.destroy": ("Détruire l'avant-poste", "Destroy the outpost"),
    "annex.page.destroyConfirm": ("Confirmer la destruction", "Confirm the destruction"),
    "annex.destroy.warn": ("Détruire l'avant-poste ({building}) ? Ses villageois partent, le bâtiment est rasé et son niveau perdu. Le coffre reste avec son contenu ; un quart des matériaux de la fondation revient au dépôt (1 sur {refund}). Cliquez de nouveau pour confirmer.",
                           "Destroy the {building}? Its villagers leave, the building is razed and its level lost. The chest stays with its contents; a quarter of the foundation materials returns to the deposit (1 in {refund}). Click again to confirm."),
    "annex.destroy.rank": ("Il faut être {rank} du village pour détruire un avant-poste.", "You must be {rank} of the village to destroy an outpost."),
    "annex.destroy.nothing": ("Il n'y a rien à détruire : cet avant-poste n'est ni debout ni en travaux.", "There is nothing to destroy: this outpost is neither standing nor under construction."),
    "annex.destroy.convoy": ("Le convoi de l'avant-poste ({building}) est sur la route : attendez qu'il arrive au village pour le détruire.",
                             "The outpost's convoy ({building}) is on the road: wait until it reaches the village to destroy it."),
    "annex.destroyed": ("{player} a détruit l'avant-poste : {building}.", "{player} destroyed the outpost: {building}."),
    "annex.destroyedHere": ("L'avant-poste ({building}) est rasé ({x} {z}). Une nouvelle fondation peut être reçue au panneau.",
                            "The {building} is razed ({x} {z}). A new foundation can be received at the board."),
    "annex.destroyedLater": ("L'avant-poste ({building}) est abandonné ({x} {z}) : il sera rasé au premier passage. Une nouvelle fondation peut être reçue au panneau.",
                             "The {building} is abandoned ({x} {z}): it will be razed on the first visit. A new foundation can be received at the board."),
    "annex.state.cost": ("Fondation : {list}, pris au dépôt.", "Foundation: {list}, taken from the deposit."),
    "annex.state.costMissing": ("Fondation : {list}. Il manque au dépôt : {missing}.", "Foundation: {list}. The deposit lacks: {missing}."),
    "annex.state.granted": ("Fondation remise à {player}, pas encore posée. {rule}", "Foundation given to {player}, not placed yet. {rule}"),
    "annex.state.working": ("Travaux en cours en {x} {z} : encore {hours} h.", "Works under way at {x} {z}: {hours} h left."),
    "annex.state.built": ("Debout en {x} {z}, niveau {level}. Son panneau est sur place.", "Standing at {x} {z}, level {level}. Its board is on site."),
    "annex.hint.FERTILE": ("Il lui faut une terre fertile.", "It needs fertile soil."),
    "annex.hint.ROCK": ("Il lui faut de la roche ou un flanc de colline tout près.", "It needs rock or a hillside close by."),
    "annex.hint.TREES": ("Il lui faut des arbres tout autour.", "It needs trees all around."),
    "annex.hint.WATER": ("Il lui faut de l'eau à moins de 12 blocs.", "It needs water within 12 blocks."),
    "annex.hint.NONE": ("Elle se pose sur tout terrain plat.", "It goes on any flat ground."),
    "annex.lockedTier": ("Le village doit atteindre le palier {tier} pour fonder des avant-postes.", "The village must reach tier {tier} to found outposts."),
    "annex.lockedRank": ("Il faut être {rank} du village pour recevoir une fondation.", "You must be {rank} of the village to receive a foundation."),
    "annex.alreadyBuilt": ("Cet avant-poste est déjà debout.", "This outpost already stands."),
    "annex.alreadyWorks": ("Cet avant-poste est déjà en travaux.", "This outpost is already under construction."),
    "annex.regiveTomorrow": ("La fondation a déjà été reprise aujourd'hui : revenez demain, après {hour} h.", "The foundation was already taken again today: come back tomorrow, after {hour}:00."),
    "annex.regiven": ("Voici de nouveau la fondation : {building}.", "Here is the foundation again: {building}."),
    "annex.missing": ("Il manque au dépôt du village : {list}.", "The village deposit lacks: {list}."),
    "annex.granted": ("{player} a reçu la fondation : {building}.", "{player} received the foundation: {building}."),
    "annex.material": ("{count} {item}", "{count} {item}"),
    "annex.unbound": ("Aucun village n'attend cette fondation : elle ne peut pas être posée.", "No village is waiting for this foundation: it cannot be placed."),
    "annex.placeRank": ("Il faut être {rank} de {village} pour poser cette fondation.", "You must be {rank} of {village} to place this foundation."),
    "annex.tooNear": ("Trop près de {village} ({distance} blocs) : au moins {min} blocs du cœur.", "Too close to {village} ({distance} blocks): at least {min} blocks from the heart."),
    "annex.tooFar": ("Trop loin de {village} ({distance} blocs) : au plus {max} blocs du cœur.", "Too far from {village} ({distance} blocks): at most {max} blocks from the heart."),
    "annex.otherVillage": ("Trop près du village {village} ({distance} blocs, il en faut {min}).", "Too close to the village {village} ({distance} blocks, {min} needed)."),
    "annex.otherAnnex": ("Trop près de l'avant-poste {building} de {village} ({distance} blocs, il en faut {min}).", "Too close to the outpost {building} of {village} ({distance} blocks, {min} needed)."),
    "annex.outpostPlanned": ("Un avant-poste de champion est prévu à {distance} blocs : choisissez une autre place.", "A champion's outpost is planned {distance} blocks away: pick another spot."),
    "annex.unloaded": ("Le terrain autour n'est pas encore chargé : rapprochez-vous.", "The ground around is not loaded yet: come closer."),
    "annex.water": ("La place est dans l'eau ({count} points mouillés) : il faut un sol sec.", "The spot is in water ({count} wet points): dry ground is needed."),
    "annex.relief": ("Le terrain est trop accidenté ({relief} blocs de dénivelé, au plus {max}).", "The ground is too uneven ({relief} blocks of drop, at most {max})."),
    "annex.obstacle": ("Une construction gêne : {block} en {x} {y} {z}.", "A build is in the way: {block} at {x} {y} {z}."),
    "annex.rule.FERTILE": ("Une ferme demande une terre fertile : {percent} % de l'emprise, il en faut {need} %.", "A farm needs fertile soil: {percent} % of the footprint, {need} % needed."),
    "annex.rule.ROCK": ("Une mine demande de la roche ou un flanc de colline tout près (roche : {percent} %).", "A mine needs rock or a hillside close by (rock: {percent} %)."),
    "annex.rule.TREES": ("Une scierie demande des arbres autour : {count} troncs, il en faut {need}.", "A sawmill needs trees around: {count} trunks, {need} needed."),
    "annex.rule.WATER": ("Une pêcherie demande de l'eau à moins de {distance} blocs, au bord mais au sec.", "A fishery needs water within {distance} blocks, on the shore but dry."),
    "annex.started": ("{player} a posé la fondation : {building}. Travaux pendant {hours} h.", "{player} placed the foundation: {building}. Works for {hours} h."),
    "annex.startedHere": ("La zone est marquée : {building} de {village} sera debout dans {hours} h.", "The area is marked: {building} of {village} will stand in {hours} h."),
    "annex.phase": ("{building} : étape {phase} sur {phases} des travaux.", "{building}: stage {phase} of {phases} of the works."),
    "annex.state.convoy": ("Debout en {x} {z}, niveau {level}. Un convoi de {porters} porteurs est en route vers le dépôt.", "Standing at {x} {z}, level {level}. A convoy of {porters} carriers is on its way to the deposit."),
    "annex.convoy.porter": ("Un porteur du convoi de {building} a été tué : sa cargaison est tombée au sol. Il en reste {left}.", "A carrier of the {building} convoy was killed: its load fell to the ground. {left} left."),
    "annex.convoy.lost": ("Le convoi de {building} a été anéanti : la livraison du jour est perdue.", "The {building} convoy was wiped out: today's delivery is lost."),
    "annex.route.placed": ("Balise de route posée : reliée à {links} balise(s) à moins de {range} blocs.", "Route beacon placed: linked to {links} beacon(s) within {range} blocks."),
    "annex.route.alone": ("Balise de route posée, mais aucune autre balise à moins de {range} blocs : elle n'est reliée à rien.", "Route beacon placed, but no other beacon within {range} blocks: it is linked to nothing."),
    "annex.route.removed": ("Balise de route retirée : les convois recalculent leur route.", "Route beacon removed: convoys recompute their route."),
    "annex.route.full": ("Ce monde a déjà {max} balises de route.", "This world already has {max} route beacons."),
    "annex.convoy.reason": ("tu as tué un porteur d'un convoi", "you killed a convoy carrier"),
    "annex.state.chest": ("{state} Coffre de l'avant-poste en {x} {y} {z} : {count} objet(s) en attente du convoi de {hour} h.",
                          "{state} Outpost chest at {x} {y} {z}: {count} item(s) waiting for the {hour}:00 convoy."),
    "annex.state.waiting": ("Debout en {x} {z}, niveau {level}. Le dépôt du village est plein : le convoi attend devant avec {count} objet(s).",
                            "Standing at {x} {z}, level {level}. The village deposit is full: the convoy waits by it with {count} item(s)."),
    "annex.chest.full": ("{building} : le coffre de l'avant-poste déborde, la production du jour est perdue. Videz-le ou faites de la place au dépôt du village.",
                         "{building}: the outpost chest overflows, today's production is lost. Empty it or make room in the village deposit."),
    "annex.deposit.full": ("Le dépôt de {village} est plein : le convoi de {building} ne part pas, la production reste au coffre de l'avant-poste.",
                           "The {village} deposit is full: the {building} convoy stays home, the production waits in the outpost chest."),
    "annex.convoy.waiting": ("Le dépôt est plein : le convoi de {building} attend devant avec {count} objet(s). Faites-lui de la place.",
                             "The deposit is full: the {building} convoy waits by it with {count} item(s). Make some room."),
    "annex.deposit.large": ("{village} grandit : son dépôt devient un grand coffre (36 places).",
                            "{village} grows: its deposit becomes a large chest (36 slots)."),
    "annex.done": ("{building} de {village} est debout !", "{building} of {village} stands!"),
    "annex.doneTitle": ("{building} est debout", "{building} stands"),
}
