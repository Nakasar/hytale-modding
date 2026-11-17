"""Emplacements libres E1, E2 et E3 des villages (GDD des bâtiments de métier, étape 6).

Chaque plan de village réserve deux terrains de 24 × 24 blocs. Kevin (2026-11-15) : E1 s'ouvre au palier 2, E2 au
palier 3 ; les piquets du terrain apparaissent un palier plus tôt. Un joueur de rang Ami choisit au panneau du village
(page « Emplacements ») un des 6 projets du peuple ; chaque projet devient un bâtiment de métier complet (villageois,
panneau, niveaux, spécialités, boutiques). Un projet = deux bâtiments du plan, un par terrain (E1_<Projet>,
E2_<Projet>), jamais collés par les chantiers de palier : le chantier d'emplacement (24 h) les colle.

Lu par tools/generate_village_layouts.py (bâtiments, métiers, terrains du plan) et tools/generate_workshops.py
(bâtiments de métier, commandes, spécialités, boutiques). Prefabs et objets vanilla seulement (règle n° 2).
"""

PLOT_SIZE = 24
PLOT_HOURS = 24
# Un quart des matériaux revient au dépôt quand on démolit (GDD) ; une démolition tous les 7 jours par terrain.
DEMOLISH_DAYS = 7

# Terrains : centre (x, z) relatif au cœur et palier d'ouverture (GDD, « Plans de village », décalés d'un bloc pour
# garder 3 blocs entre le terrain et les bâtiments).
PLOTS = {
    "Kweebec_Oak": {"E1": (28, -37, 2), "E2": (-22, -42, 3), "E3": (-53, 19, 2)},
    "Trork_Camp": {"E1": (20, -37, 2), "E2": (7, 45, 3), "E3": (42, 22, 2)},
    "Feran_Oasis": {"E1": (-2, 40, 2), "E2": (55, 0, 3), "E3": (-57, 0, 2)},
    "Renonce_Givre": {"E1": (28, -30, 2), "E2": (-39, 13, 3), "E3": (0, 48, 2)},
    "Slothian_Monastere": {"E1": (0, 51, 2), "E2": (48, 19, 3), "E3": (-49, -24, 2)},
}

# Matériaux du chantier d'un emplacement (pris au dépôt du village), par peuple.
MATERIALS = {
    "Kweebec": [("Wood_Oak_Trunk", 40), ("Rock_Stone_Cobble", 32), ("Ingredient_Fibre", 16)],
    "Trork": [("Wood_Oak_Trunk", 32), ("Ingredient_Hide_Light", 12), ("Ingredient_Bone_Fragment", 20)],
    "Feran": [("Wood_Dry_Trunk", 32), ("Ingredient_Fibre", 16), ("Ingredient_Salt", 8)],
    "Renonce": [("Wood_Fir_Trunk", 40), ("Rock_Stone_Cobble", 32), ("Ingredient_Hide_Heavy", 6)],
    "Slothian": [("Wood_Jungle_Trunk", 32), ("Rock_Volcanic", 32), ("Furniture_Jungle_Candle", 4)],
}

NPC = "Npc/"
MON = "Monuments/Incidental/Slothian/Land/"
PEN = "Nakasar/Peuples/Pens/"

# Un projet : id, prefab, rotation, métier (id, genre de rôle comme dans les plans : « @Rôle » vanilla ou rôle du mod
# Nakasar_Peuples_<Peuple>_<Genre> ; « dialogue » remplace <Peuple>_<Genre> quand ce dialogue n'existe pas), noms fr/en du bâtiment et du métier, icône, puis soit "Twin" (deuxième enclos :
# bêtes, spécialités et boutiques du bâtiment nommé, jamais la même spécialité que lui), soit commandes, boutique de
# base et deux spécialités. Une spécialité : (id, nom fr, nom en, icône, ligne fr, ligne en, [niveau II], [niveau III],
# effet en raid ou None). Un échange : (objet, quantité, prix en faveurs).
PROJECTS = {
    "Kweebec_Oak": [
        dict(id="Archerie", category="Artisanat", prefab=NPC + "Kweebec/Oak/Shops/Kweebec_Oak_Shops_001", rotation=0, job="Archer", kind="Guard",
             fr="Atelier d'archerie", en="Archery workshop", job_fr="Archer", job_en="Archer", icon="Weapon_Shortbow_Crude",
             orders=[("Arrows", "Gather", "Ingredient_Fibre", 12, "Fibres pour les cordes", "Fibre for bowstrings"),
                     ("Feathers", "Gather", "Ingredient_Bar_Copper", 3, "Cuivre des pointes", "Copper for arrowheads"),
                     ("Sticks", "Gather", "Wood_Ash_Trunk", 10, "Frêne pour les arcs", "Ash wood for bows")],
             base=[("Weapon_Arrow_Crude", 16, 1), ("Ingredient_Stick", 8, 1), ("Weapon_Shortbow_Crude", 1, 2)],
             specs=[("Arcs_Legers", "Arcs légers", "Light bows", "Weapon_Shortbow_Copper", "Arcs courts de cuivre et de fer.",
                     "Copper and iron short bows.", [("Weapon_Shortbow_Copper", 1, 3), ("Weapon_Shortbow_Bronze", 1, 4)],
                     [("Weapon_Shortbow_Iron", 1, 5), ("Weapon_Shortbow_Ricochet", 1, 6)], None),
                    ("Fleches_Chasse", "Flèches de chasse", "Hunting arrows", "Weapon_Arrow_Iron", "Flèches de fer et de précision.",
                     "Iron and precision arrows.", [("Weapon_Arrow_Iron", 16, 2), ("Ingredient_Feathers_Light", 8, 1)],
                     [("Weapon_Arrow_Trueshot", 8, 4), ("Weapon_Arrow_Clearshot", 8, 4)], None)]),
        dict(id="Herboristerie", category="Artisanat", prefab=NPC + "Kweebec/Oak/Shops/Kweebec_Oak_Shops_003", rotation=0, job="Herboriste", kind="Healer",
             fr="Herboristerie", en="Herbalist's", job_fr="Herboriste", job_en="Herbalist", icon="Potion_Health_Lesser",
             orders=[("Flowers", "Gather", "Plant_Crop_Mushroom_Cap_Brown", 8, "Champignons à sécher", "Mushrooms to dry"),
                     ("Essence", "Gather", "Ingredient_Life_Essence", 6, "Essence pour les fioles", "Essence for the vials"),
                     ("Vials", "Gather", "Plant_Flower_Common_Blue", 10, "Fleurs pour remèdes", "Flowers for remedies")],
             base=[("Potion_Health_Lesser", 1, 1), ("Plant_Flower_Common_Red", 4, 1), ("Potion_Empty_Small", 2, 1)],
             specs=[("Potions_Vie", "Potions de vie", "Health potions", "Potion_Health_Small", "Potions de vie et de régénération.",
                     "Health and regeneration potions.", [("Potion_Health_Small", 2, 1), ("Potion_Regen_Health_Small", 1, 2)],
                     [("Potion_Health", 1, 3), ("Potion_Health_Greater", 1, 5)], None),
                    ("Poisons", "Poisons et antidotes", "Poisons and antidotes", "Potion_Antidote", "Antidotes et fioles de poison.",
                     "Antidotes and poison vials.", [("Potion_Antidote", 1, 2), ("Potion_Poison_Minor", 1, 2)],
                     [("Potion_Poison", 1, 3), ("Potion_Poison_Large", 1, 5)], None)]),
        dict(id="Grand_Bassin", legacy=True, prefab=NPC + "Kweebec/Oak/Water_Pool/Kweebec_Oak_Water_Pool_005", rotation=0, job="Pecheuse",
             kind="WellKeeper", fr="Grand bassin", en="Great pool", job_fr="Pêcheuse", job_en="Fisher", icon="Food_Fish_Raw",
             orders=[("Buckets", "Craft", "Container_Bucket", 2, "Seaux pour le bassin", "Buckets for the pool"),
                     ("Water", "Gather", "Soil_Clay", 16, "Argile du bassin", "Clay for the pool"),
                     ("Stones", "Gather", "Rock_Stone_Cobble", 20, "Pierres du bord", "Stones for the edge")],
             base=[("Food_Fish_Raw", 2, 1), ("Ingredient_Water_Essence", 2, 1), ("Tool_Fishing_Trap", 1, 2)],
             specs=[("Poissons", "Poissons", "Fish", "Food_Fish_Raw", "Poissons frais et grillés.", "Fresh and grilled fish.",
                     [("Food_Fish_Raw", 4, 1), ("Food_Fish_Grilled", 2, 1)],
                     [("Food_Fish_Raw_Uncommon", 2, 3), ("Food_Fish_Raw_Rare", 1, 4)], None),
                    ("Essence_Eau", "Essence d'eau", "Water essence", "Ingredient_Water_Essence", "Essence d'eau et potions claires.",
                     "Water essence and clear potions.", [("Ingredient_Water_Essence", 4, 1), ("Potion_Empty_Small", 3, 1)],
                     [("Potion_Purify", 1, 3), ("Potion_Regen_Stamina_Small", 2, 3)], None)]),
        dict(id="Menuiserie", category="Artisanat", prefab=NPC + "Kweebec/Oak/Shops/Kweebec_Oak_Shops_004", rotation=0, job="Menuisier", kind="Gardener",
             fr="Atelier du menuisier", en="Carpenter's workshop", job_fr="Menuisier", job_en="Carpenter", icon="Furniture_Kweebec_Stool",
             orders=[("Logs", "Gather", "Wood_Birch_Trunk", 16, "Bouleau du menuisier", "Birch for the carpenter"),
                     ("Bark", "Craft", "Tool_Hatchet_Crude", 2, "Haches du menuisier", "Carpenter's hatchets"),
                     ("Sap", "Gather", "Ingredient_Tree_Sap", 4, "Sève pour la colle", "Sap for glue")],
             base=[("Ingredient_Stick", 8, 1), ("Wood_Oak_Trunk", 8, 1), ("Ingredient_Tree_Bark", 4, 1)],
             specs=[("Mobilier", "Mobilier kweebec", "Kweebec furniture", "Furniture_Kweebec_Table", "Tabourets, tables, armoires.",
                     "Stools, tables, wardrobes.", [("Furniture_Kweebec_Stool", 1, 1), ("Furniture_Kweebec_Table", 1, 2)],
                     [("Furniture_Kweebec_Wardrobe", 1, 3), ("Furniture_Kweebec_Bed", 1, 3)], None),
                    ("Lanternes", "Lanternes", "Lanterns", "Furniture_Kweebec_Lantern", "Lanternes, bougies et statues.",
                     "Lanterns, candles and statues.", [("Furniture_Kweebec_Lantern", 2, 1), ("Furniture_Kweebec_Candle", 3, 1)],
                     [("Furniture_Kweebec_Lantern_Ceiling", 2, 2), ("Furniture_Kweebec_Statue", 1, 4)], None)]),
        dict(id="Deuxieme_Enclos", category="Elevage", prefab=NPC + "Kweebec/Oak/Bunny_Area/Kweebec_Oak_Bunny_Area_005", rotation=0, job="Eleveur_Bis",
             kind="Breeder", fr="Deuxième enclos", en="Second pen", job_fr="Éleveur", job_en="Breeder", icon="Ingredient_Hay",
             twin="Kweebec_Enclos"),
    ],
    "Trork_Camp": [
        dict(id="Forge_De_Guerre", category="Artisanat", prefab=NPC + "Trork/Misc/Large/Trork_Misc_Large_002", rotation=0, job="Forgeron",
             kind="@Trork_Brawler", fr="Forge de guerre", en="War forge", job_fr="Forgeron", job_en="Smith", icon="Weapon_Club_Crude",
             orders=[("Copper", "Gather", "Ingredient_Bar_Copper", 4, "Cuivre pour la forge", "Copper for the forge"),
                     ("Charcoal", "Gather", "Ingredient_Bar_Iron", 3, "Fer pour la forge", "Iron for the forge"),
                     ("Bones", "Gather", "Soil_Clay", 12, "Argile du four", "Clay for the furnace")],
             base=[("Weapon_Club_Crude", 1, 2), ("Ingredient_Bone_Fragment", 6, 1), ("Ingredient_Charcoal", 4, 1)],
             specs=[("Armes_Os", "Armes en os", "Bone weapons", "Weapon_Sword_Bone", "Épées, dagues et haches d'os.",
                     "Bone swords, daggers and axes.", [("Weapon_Sword_Bone", 1, 3), ("Weapon_Daggers_Bone", 1, 3)],
                     [("Weapon_Axe_Bone", 1, 4), ("Weapon_Club_Stone_Trork", 1, 5)], None),
                    ("Armures_Peau", "Armures de peau", "Hide armour", "Armor_Trork_Chest", "Armures trorks et de cuir.",
                     "Trork and leather armour.", [("Armor_Leather_Light_Head", 1, 2), ("Armor_Trork_Hands", 1, 3)],
                     [("Armor_Trork_Chest", 1, 5), ("Armor_Trork_Legs", 1, 4)], None)]),
        dict(id="Camp_Bucherons", legacy=True, prefab=NPC + "Trork/Resource/Lumber/Forest_Aspen/Trork_Resource_Lumber_Forest_Aspen_001",
             rotation=0, job="Bucheron", kind="@Trork_Warrior", fr="Camp de bûcherons", en="Lumber camp", job_fr="Bûcheron",
             job_en="Lumberjack", icon="Wood_Oak_Trunk",
             orders=[("Logs", "Gather", "Wood_Beech_Trunk", 20, "Hêtre du camp", "Beech for the camp"),
                     ("Hatchets", "Craft", "Tool_Hatchet_Crude", 2, "Haches pour le camp", "Hatchets for the camp"),
                     ("Sap", "Gather", "Ingredient_Fibre", 12, "Fibres des cordes", "Fibre for ropes")],
             base=[("Wood_Oak_Trunk", 12, 1), ("Ingredient_Stick", 8, 1), ("Ingredient_Tree_Bark", 4, 1)],
             specs=[("Bois", "Bois", "Timber", "Wood_Birch_Trunk", "Rondins de chêne, de bouleau et de séquoia.",
                     "Oak, birch and redwood logs.", [("Wood_Oak_Trunk", 24, 1), ("Wood_Birch_Trunk", 16, 1)],
                     [("Wood_Redwood_Trunk", 16, 2), ("Tool_Hatchet_Iron", 1, 5)], None),
                    ("Ecorce_Seve", "Écorce et sève", "Bark and sap", "Ingredient_Tree_Sap", "Écorce, sève et outils pour les récolter.",
                     "Bark, sap and the tools to gather them.", [("Ingredient_Tree_Bark", 8, 1), ("Ingredient_Tree_Sap", 3, 1)],
                     [("Tool_Sap_Shunt", 1, 3), ("Tool_Bark_Scraper", 1, 3)], None)]),
        dict(id="Carriere", legacy=True, prefab=NPC + "Trork/Resource/Rock/Stone/Trork_Resource_Rock_Stone_005", rotation=0, job="Casseur",
             kind="@Trork_Brawler", fr="Carrière", en="Quarry", job_fr="Casseur de pierre", job_en="Stonebreaker",
             icon="Rock_Stone_Cobble",
             orders=[("Stones", "Craft", "Tool_Shovel_Crude", 2, "Pelles de la carrière", "Shovels for the quarry"),
                     ("Picks", "Gather", "Ingredient_Stick", 16, "Manches d'outils", "Tool handles"),
                     ("Copper", "Gather", "Food_Bread", 4, "Pain des carriers", "Bread for the quarrymen")],
             base=[("Rock_Stone_Cobble", 24, 1), ("Ingredient_Bar_Copper", 1, 1), ("Tool_Pickaxe_Crude", 1, 2)],
             specs=[("Pierre", "Pierre", "Stone", "Rock_Volcanic", "Pierre, basalte et poudre.", "Stone, basalt and powder.",
                     [("Rock_Stone_Cobble", 48, 1), ("Rock_Volcanic", 24, 1)],
                     [("Tool_Pickaxe_Iron", 1, 5), ("Ingredient_Powder_Boom", 4, 3)], None),
                    ("Minerai", "Minerai", "Ore", "Ingredient_Bar_Iron", "Lingots de cuivre, de fer et d'argent.",
                     "Copper, iron and silver bars.", [("Ingredient_Bar_Copper", 3, 2), ("Ingredient_Bar_Iron", 1, 2)],
                     [("Ingredient_Bar_Iron", 3, 4), ("Ingredient_Bar_Silver", 1, 4)], None)]),
        dict(id="Tannerie", category="Artisanat", prefab=NPC + "Trork/Tent/Trork_Tent_001", rotation=0, job="Tanneur", kind="@Trork_Hunter",
             fr="Tannerie", en="Tannery", job_fr="Tanneur", job_en="Tanner", icon="Ingredient_Leather_Light",
             orders=[("Hides", "Gather", "Ingredient_Salt", 8, "Sel pour les peaux", "Salt for the hides"),
                     ("Medium", "Gather", "Ingredient_Hide_Medium", 4, "Peaux épaisses", "Thick hides"),
                     ("Wolves", "Hunt", ["Wolf_Black", "Wolf_Black"], 0, "Loups pour les peaux", "Wolves for hides")],
             base=[("Ingredient_Leather_Light", 2, 1), ("Ingredient_Hide_Light", 3, 1), ("Ingredient_Strap_Leather", 2, 1)],
             specs=[("Cuirs", "Cuirs", "Leathers", "Ingredient_Leather_Medium", "Cuirs légers, moyens et lourds.",
                     "Light, medium and heavy leather.", [("Ingredient_Leather_Medium", 2, 2), ("Ingredient_Leather_Light", 4, 1)],
                     [("Ingredient_Leather_Heavy", 2, 3), ("Armor_Leather_Medium_Chest", 1, 5)], None),
                    ("Sangles", "Sangles et sacs", "Straps and bags", "Ingredient_Strap_Leather", "Sangles, musettes et caisses.",
                     "Straps, feedbags and crates.", [("Ingredient_Strap_Leather", 4, 1), ("Tool_Feedbag", 1, 2)],
                     [("Tool_Capture_Crate", 1, 4), ("Armor_Leather_Light_Hands", 1, 3)], None)]),
        dict(id="Deuxieme_Fosse", category="Elevage", prefab=PEN + "Trork_Pen", rotation=0, job="Dresseur_Bis", kind="@Trork_Hunter",
             fr="Deuxième fosse", en="Second pit", job_fr="Dresseur", job_en="Tamer", icon="Food_Wildmeat_Raw",
             twin="Trork_Fosse_Aux_Betes"),
    ],
    "Feran_Oasis": [
        dict(id="Caravanserail", category="Artisanat", prefab=NPC + "Feran/Portals_Oasis/Hut/Feran_Tier2_Hut_002", rotation=0, job="Caravaniere",
             kind="Merchant", dialogue="Feran_Marchand", fr="Caravansérail", en="Caravanserai", job_fr="Caravanière", job_en="Caravaneer", icon="Ingredient_Spices",
             orders=[("Spices", "Gather", "Plant_Crop_Chilli_Item", 6, "Piments des caravanes", "Caravan chillies"),
                     ("Salt", "Gather", "Ingredient_Bar_Copper", 3, "Cuivre pour le troc", "Copper for trade"),
                     ("Hides", "Gather", "Ingredient_Hide_Scaled", 3, "Cuir des caravanes", "Caravan leather")],
             base=[("Ingredient_Spices", 2, 1), ("Ingredient_Salt", 3, 1), ("Food_Bread", 2, 1)],
             specs=[("Epices", "Épices et sel", "Spices and salt", "Ingredient_Salt", "Épices, sel et brochettes.",
                     "Spices, salt and skewers.", [("Ingredient_Spices", 4, 1), ("Ingredient_Salt", 8, 1)],
                     [("Food_Kebab_Vegetable", 3, 2), ("Food_Kebab_Fruit", 3, 2)], None),
                    ("Ailleurs", "Objets d'ailleurs", "Wares from afar", "Ingredient_Bolt_Silk", "Étoffes et fruits d'autres peuples.",
                     "Cloth and fruit from other peoples.", [("Ingredient_Bolt_Linen", 2, 2), ("Plant_Fruit_Coconut", 2, 1)],
                     [("Ingredient_Bolt_Silk", 1, 4), ("Plant_Fruit_Mango", 3, 2)], None)]),
        dict(id="Tissage", category="Artisanat", prefab=NPC + "Feran/Portals_Oasis/Hut/Feran_Tier2_Hut_001", rotation=0, job="Tisserande", kind="Watcher",
             fr="Atelier de tissage", en="Weaving workshop", job_fr="Tisserande", job_en="Weaver", icon="Ingredient_Bolt_Linen",
             orders=[("Cotton", "Gather", "Plant_Crop_Cotton_Item", 8, "Coton à filer", "Cotton to spin"),
                     ("Fibre", "Gather", "Ingredient_Stick", 12, "Bois du métier", "Wood for the loom"),
                     ("Linen", "Gather", "Plant_Flower_Common_Blue", 8, "Fleurs pour teinture", "Flowers for dye")],
             base=[("Ingredient_Fabric_Scrap_Linen", 4, 1), ("Ingredient_Fabric_Scrap_Cotton", 4, 1), ("Ingredient_Fibre", 8, 1)],
             specs=[("Lin_Coton", "Lin et coton", "Linen and cotton", "Ingredient_Bolt_Cotton", "Rouleaux et vêtements de lin et de coton.",
                     "Linen and cotton bolts and clothes.", [("Ingredient_Bolt_Linen", 2, 2), ("Ingredient_Bolt_Cotton", 2, 2)],
                     [("Armor_Cloth_Linen_Chest", 1, 4), ("Armor_Cloth_Cotton_Chest", 1, 4)], None),
                    ("Voiles", "Voiles contre le soleil", "Sun veils", "Armor_Cloth_Linen_Head", "Voiles de tête et tuniques légères.",
                     "Head veils and light tunics.", [("Armor_Cloth_Linen_Head", 1, 2), ("Armor_Cloth_Cotton_Head", 1, 2)],
                     [("Armor_Cloth_Silk_Head", 1, 4), ("Armor_Cloth_Silk_Chest", 1, 6)], None)]),
        dict(id="Citerne", legacy=True, prefab=NPC + "Feran/Portals_Oasis/Wall/Feran_Tier2_Wall_005", rotation=0, job="Gardien_Eau",
             kind="WellKeeper", fr="Citerne", en="Cistern", job_fr="Gardien de l'eau", job_en="Water keeper",
             icon="Ingredient_Water_Essence",
             orders=[("Buckets", "Gather", "Soil_Clay", 16, "Argile de la citerne", "Clay for the cistern"),
                     ("Water", "Gather", "Soil_Gravel", 16, "Gravier filtrant", "Filter gravel"),
                     ("Stones", "Gather", "Rock_Stone_Cobble", 16, "Pierres de la citerne", "Stones for the cistern")],
             base=[("Ingredient_Water_Essence", 2, 1), ("Container_Bucket", 1, 2), ("Potion_Empty_Small", 2, 1)],
             specs=[("Reserve", "Réserve d'eau", "Water store", "Container_Bucket", "Eau, seaux et potions d'endurance.",
                     "Water, buckets and stamina potions.", [("Ingredient_Water_Essence", 4, 1), ("Container_Bucket", 2, 2)],
                     [("Potion_Regen_Stamina_Small", 2, 3), ("Potion_Stamina", 1, 3)], None),
                    ("Essence", "Essence d'eau", "Water essence", "Ingredient_Ice_Essence", "Essences d'eau et de glace.",
                     "Water and ice essence.", [("Ingredient_Water_Essence", 6, 1), ("Potion_Empty", 2, 1)],
                     [("Potion_Purify", 1, 3), ("Ingredient_Ice_Essence", 2, 3)], None)]),
        dict(id="Volerie", category="Artisanat", prefab=NPC + "Feran/Portals_Oasis/Pillar_Hut/Feran_Tier3_Hut_001", rotation=0, job="Fauconnier",
             kind="Lookout", dialogue="Feran_Watcher", fr="Volerie des plumes", en="Feather aviary", job_fr="Fauconnier", job_en="Falconer",
             icon="Ingredient_Feathers_Light",
             orders=[("Feathers", "Gather", "Ingredient_Hay", 8, "Foin des nids", "Hay for the nests"),
                     ("Meat", "Gather", "Food_Wildmeat_Raw", 6, "Viande des rapaces", "Meat for the raptors"),
                     ("Sticks", "Gather", "Ingredient_Stick", 16, "Perchoirs", "Perches")],
             base=[("Ingredient_Feathers_Light", 4, 1), ("Weapon_Arrow_Crude", 16, 1), ("Ingredient_Feathers_Blue", 2, 1)],
             specs=[("Plumes", "Plumes", "Feathers", "Ingredient_Feathers_Blue", "Plumes bleues, rouges et sombres.",
                     "Blue, red and dark feathers.", [("Ingredient_Feathers_Blue", 4, 1), ("Ingredient_Feathers_Red", 4, 1)],
                     [("Ingredient_Feathers_Dark", 6, 2), ("Armor_Leather_Soft_Head", 1, 3)], None),
                    ("Fleches", "Flèches", "Arrows", "Weapon_Arrow_Iron", "Flèches de fer et de précision.", "Iron and precision arrows.",
                     [("Weapon_Arrow_Iron", 16, 2), ("Weapon_Shortbow_Crude", 1, 2)],
                     [("Weapon_Arrow_Trueshot", 8, 4), ("Weapon_Arrow_Deadeye", 8, 4)], None)]),
        dict(id="Deuxieme_Enclos", category="Elevage", prefab=PEN + "Feran_Pen", rotation=0, job="Eleveuse_Bis", kind="Breeder",
             fr="Deuxième enclos", en="Second pen", job_fr="Éleveuse", job_en="Breeder", icon="Food_Egg",
             twin="Feran_Enclos_Oasis"),
    ],
    "Renonce_Givre": [
        dict(id="Forge", category="Artisanat", prefab=NPC + "Outlander/Houses/Tier2/Outlander_Houses_Tier2_001", rotation=0, job="Forgeron_Repenti",
             kind="Guard", fr="Forge des repentis", en="Penitents' forge", job_fr="Forgeron repenti", job_en="Penitent smith",
             icon="Ingredient_Bar_Iron",
             orders=[("Iron", "Gather", "Ingredient_Bar_Iron", 3, "Fer pour la forge", "Iron for the forge"),
                     ("Charcoal", "Gather", "Ingredient_Charcoal", 12, "Charbon de la forge", "Charcoal for the forge"),
                     ("Cultists", "Hunt", ["Outlander_Cultist", "Outlander_Cultist"], 0, "Pillards du culte", "Cult raiders")],
             base=[("Ingredient_Bar_Copper", 2, 1), ("Weapon_Spear_Crude", 1, 2), ("Tool_Repair_Kit_Crude", 1, 2)],
             specs=[("Armes", "Armes", "Weapons", "Weapon_Spear_Iron", "Masses, lances et arbalètes de fer.",
                     "Iron maces, spears and crossbows.", [("Weapon_Club_Iron", 1, 4), ("Weapon_Spear_Iron", 1, 4)],
                     [("Weapon_Crossbow_Iron", 1, 5), ("Weapon_Spear_Cobalt", 1, 7)], None),
                    ("Armures_Lourdes", "Armures lourdes", "Heavy armour", "Armor_Leather_Heavy_Chest", "Armures de cuir lourd.",
                     "Heavy leather armour.", [("Armor_Leather_Heavy_Head", 1, 3), ("Armor_Leather_Heavy_Hands", 1, 3)],
                     [("Armor_Leather_Heavy_Chest", 1, 5), ("Armor_Leather_Heavy_Legs", 1, 5)], None)]),
        dict(id="Fumoir", category="Artisanat", prefab=NPC + "Outlander/Misc/Outlander_Misc_001", rotation=0, job="Fumeur", kind="Hunter",
             fr="Fumoir et tannerie", en="Smokehouse and tannery", job_fr="Tanneur", job_en="Tanner", icon="Food_Wildmeat_Cooked",
             orders=[("Meat", "Gather", "Food_Wildmeat_Raw", 8, "Viande à fumer", "Meat to smoke"),
                     ("Logs", "Gather", "Ingredient_Salt", 6, "Sel pour la saumure", "Salt for the brine"),
                     ("Hides", "Gather", "Wood_Birch_Trunk", 8, "Bouleau pour la fumée", "Birch for the smoke")],
             base=[("Food_Wildmeat_Cooked", 2, 1), ("Ingredient_Hide_Medium", 1, 1), ("Ingredient_Charcoal", 4, 1)],
             specs=[("Viandes_Fumees", "Viandes fumées", "Smoked meats", "Food_Wildmeat_Cooked", "Viandes fumées, brochettes, tourtes.",
                     "Smoked meat, skewers, pies.", [("Food_Wildmeat_Cooked", 4, 1), ("Food_Kebab_Meat", 3, 1)],
                     [("Food_Pie_Meat", 2, 3), ("Ingredient_Spices", 3, 2)], None),
                    ("Fourrures", "Fourrures", "Furs", "Ingredient_Leather_Heavy", "Peaux lourdes et manteaux.",
                     "Heavy hides and coats.", [("Ingredient_Hide_Heavy", 2, 1), ("Ingredient_Leather_Heavy", 1, 2)],
                     [("Armor_Wool_Chest", 1, 4), ("Armor_Leather_Heavy_Head", 1, 4)], None)]),
        dict(id="Cabane_De_Peche", legacy=True, prefab=NPC + "Outlander/Misc/Outlander_Misc_003", rotation=0, job="Pecheur", kind="Hunter",
             fr="Cabane de pêche", en="Fishing hut", job_fr="Pêcheur", job_en="Fisher", icon="Food_Fish_Raw",
             orders=[("Fish", "Gather", "Ingredient_Fibre", 12, "Fibres des filets", "Fibre for nets"),
                     ("Traps", "Gather", "Ingredient_Bone_Fragment", 10, "Os pour les hameçons", "Bones for hooks"),
                     ("Wood", "Gather", "Wood_Birch_Trunk", 12, "Bouleau des pontons", "Birch for the jetties")],
             base=[("Food_Fish_Raw", 2, 1), ("Tool_Fishing_Trap", 1, 2), ("Food_Fish_Grilled", 1, 1)],
             specs=[("Poissons_Froids", "Poissons froids", "Cold fish", "Food_Fish_Raw", "Poissons des eaux froides.",
                     "Cold-water fish.", [("Food_Fish_Raw", 4, 1), ("Food_Fish_Grilled", 3, 1)],
                     [("Food_Fish_Raw_Uncommon", 2, 3), ("Food_Fish_Raw_Rare", 1, 4)], None),
                    ("Nasses", "Filets et nasses", "Nets and traps", "Tool_Fishing_Trap", "Nasses, appâts et belles prises.",
                     "Traps, bait and fine catches.", [("Tool_Fishing_Trap", 2, 2), ("Tool_Trap_Bait", 3, 1)],
                     [("Food_Fish_Raw_Epic", 1, 6), ("Tool_Fishing_Trap", 4, 3)], None)]),
        dict(id="Chenil", category="Defense", prefab=NPC + "Outlander/Misc/Outlander_Misc_002", rotation=0, job="Maitre_Chien", kind="Hunter",
             fr="Chenil", en="Kennel", job_fr="Maître-chien", job_en="Dog master", icon="Ingredient_Bone_Fragment",
             orders=[("Meat", "Gather", "Food_Wildmeat_Raw", 8, "Viande des chiens", "Meat for the dogs"),
                     ("Bones", "Gather", "Food_Chicken_Raw", 6, "Volaille des chiens", "Fowl for the dogs"),
                     ("Wolves", "Hunt", ["Wolf_White", "Wolf_White"], 0, "Loups errants", "Stray wolves")],
             base=[("Ingredient_Bone_Fragment", 6, 1), ("Tool_Feedbag", 1, 2), ("Ingredient_Hide_Medium", 1, 1)],
             specs=[("Loups_Garde", "Loups de garde", "Guard wolves", "Ingredient_Hide_Heavy", "Peaux et harnais ; en raid, +1 garde.",
                     "Hides and harness; +1 guard in raids.", [("Ingredient_Hide_Heavy", 2, 1), ("Armor_Leather_Medium_Head", 1, 3)],
                     [("Armor_Leather_Medium_Chest", 1, 4), ("Tool_Capture_Crate", 1, 4)], {"Guards": 1}),
                    ("Traineaux", "Traîneaux", "Sleds", "Ingredient_Strap_Leather", "Sangles, bois et cartes du givre.",
                     "Straps, wood and frost maps.", [("Ingredient_Strap_Leather", 4, 1), ("Wood_Fir_Trunk", 16, 1)],
                     [("Tool_Map", 1, 4), ("Armor_Wool_Legs", 1, 4)], None)]),
        dict(id="Deuxieme_Bergerie", category="Elevage", prefab=PEN + "Renonce_Pen", rotation=0, job="Berger_Bis", kind="Breeder",
             fr="Deuxième bergerie", en="Second fold", job_fr="Berger", job_en="Shepherd", icon="Ingredient_Fabric_Scrap_Wool",
             twin="Renonce_Bergerie_Du_Givre"),
    ],
    "Slothian_Monastere": [
        dict(id="Scriptorium", category="Savoir", prefab=NPC + "Slothian/Disabled/House/Medium/Slothian_Disabled_House_Medium_003", rotation=0,
             job="Copiste", kind="Monk", fr="Scriptorium", en="Scriptorium", job_fr="Copiste", job_en="Scribe", icon="Recipe_Page",
             orders=[("Candles", "Gather", "Ingredient_Feathers_Light", 8, "Plumes à écrire", "Quills"),
                     ("Bark", "Gather", "Plant_Crop_Cotton_Item", 8, "Coton pour le papier", "Cotton for paper"),
                     ("Void", "Gather", "Plant_Flower_Common_Blue", 6, "Fleurs pour l'encre", "Flowers for ink")],
             base=[("Recipe_Page", 1, 2), ("Furniture_Jungle_Candle", 2, 1), ("Ingredient_Tree_Bark", 4, 1)],
             specs=[("Recettes", "Recettes", "Recipes", "Recipe_Food_Pie_Apple", "Recettes de cuisine et de graines.",
                     "Cooking and seed recipes.", [("Recipe_Food_Pie_Apple", 1, 3), ("Recipe_Food_Salad_Caesar", 1, 3)],
                     [("Recipe_Plant_Seeds_Health2", 1, 5), ("Recipe_Plant_Seeds_Stamina2", 1, 5)], None),
                    ("Souvenirs", "Souvenirs de la veille", "Vigil memories", "Furniture_Jungle_Bookshelf",
                     "Livres, tableaux et grimoires.", "Books, paintings and grimoires.",
                     [("Furniture_Jungle_Bookshelf", 1, 2), ("Furniture_Jungle_Painting", 1, 2)],
                     [("Recipe_Book_Magic_Air", 1, 6), ("Recipe_Plant_Seeds_Mana2", 1, 5)], None)]),
        dict(id="Cabane_De_Peche", legacy=True, prefab=NPC + "Slothian/Disabled/House/Small/Slothian_Disabled_House_Small_002", rotation=0,
             job="Pecheur", kind="Watcher", fr="Cabane de pêche", en="Fishing hut", job_fr="Pêcheur", job_en="Fisher",
             icon="Food_Fish_Raw",
             orders=[("Fish", "Gather", "Ingredient_Fibre", 12, "Fibres des filets", "Fibre for nets"),
                     ("Traps", "Gather", "Ingredient_Bone_Fragment", 10, "Os pour les hameçons", "Bones for hooks"),
                     ("Wood", "Gather", "Wood_Jungle_Trunk", 12, "Bois du radeau", "Wood for the raft")],
             base=[("Food_Fish_Raw", 2, 1), ("Tool_Fishing_Trap", 1, 2), ("Food_Fish_Grilled", 1, 1)],
             specs=[("Poissons", "Poissons", "Fish", "Food_Fish_Raw", "Poissons frais et grillés.", "Fresh and grilled fish.",
                     [("Food_Fish_Raw", 4, 1), ("Food_Fish_Grilled", 3, 1)],
                     [("Food_Fish_Raw_Uncommon", 2, 3), ("Food_Fish_Raw_Rare", 1, 4)], None),
                    ("Coquillages", "Coquillages", "Shellfish", "Ingredient_Chitin_Sturdy", "Coquilles et cristaux du lac.",
                     "Shells and lake crystals.", [("Ingredient_Chitin_Sturdy", 1, 2), ("Ingredient_Crystal_Cyan", 1, 2)],
                     [("Ingredient_Crystal_Blue", 2, 3), ("Ingredient_Chitin_Sturdy", 3, 3)], None)]),
        dict(id="Sanctuaire", category="Culte", prefab=NPC + "Slothian/Disabled/Temple/Medium/Slothian_Disabled_Temple_Medium_001", rotation=0, job="Gardien_Sanctuaire",
             kind="Monk", fr="Sanctuaire", en="Shrine", job_fr="Gardien du sanctuaire", job_en="Shrine keeper", icon="Potion_Purify",
             orders=[("Candles", "Gather", "Plant_Flower_Common_White", 8, "Fleurs d'offrande", "Offering flowers"),
                     ("Void", "Gather", "Ingredient_Crystal_Blue", 2, "Cristaux du sanctuaire", "Shrine crystals"),
                     ("Crawlers", "Hunt", ["Crawler_Void", "Crawler_Void"], 0, "Rampants au sanctuaire", "Crawlers at the shrine")],
             base=[("Potion_Purify", 1, 2), ("Furniture_Jungle_Candle", 2, 1), ("Ingredient_Life_Essence", 3, 1)],
             specs=[("Protection", "Protection contre le Vide", "Ward against the Void", "Potion_Purify",
                     "Potions qui purifient et soignent.", "Potions that purify and heal.",
                     [("Potion_Purify", 2, 2), ("Potion_Antidote", 1, 2)], [("Potion_Health", 1, 3), ("Ingredient_Voidheart", 1, 6)], None),
                    ("Offrandes", "Offrandes", "Offerings", "Furniture_Jungle_Brazier", "Braseros, pots et essences rares.",
                     "Braziers, pots and rare essences.", [("Furniture_Jungle_Brazier", 1, 2), ("Furniture_Jungle_Pot", 2, 1)],
                     [("Ingredient_Life_Essence_Concentrated", 1, 4), ("Ingredient_Crystal_Purple", 2, 4)], None)]),
        dict(id="Puits_De_Basalte", legacy=True, prefab=NPC + "Slothian/Disabled/House/Small/Slothian_Disabled_House_Small_001", rotation=0,
             job="Puisatier", kind="AshBearer", fr="Puits de basalte", en="Basalt well", job_fr="Puisatier", job_en="Well digger",
             icon="Rock_Volcanic",
             orders=[("Basalt", "Gather", "Rock_Basalt_Cobble", 20, "Basalte du puits", "Basalt for the well"),
                     ("Buckets", "Craft", "Tool_Pickaxe_Crude", 2, "Pioches du puits", "Picks for the well"),
                     ("Fire", "Gather", "Soil_Clay", 12, "Argile du puits", "Clay for the well")],
             base=[("Ingredient_Water_Essence", 2, 1), ("Rock_Volcanic", 16, 1), ("Container_Bucket", 1, 2)],
             specs=[("Eau", "Eau", "Water", "Ingredient_Water_Essence", "Eau et potions de régénération.",
                     "Water and regeneration potions.", [("Ingredient_Water_Essence", 4, 1), ("Potion_Empty_Small", 3, 1)],
                     [("Potion_Regen_Health_Small", 2, 3), ("Potion_Purify", 1, 3)], None),
                    ("Essence_Feu", "Essence de feu", "Fire essence", "Ingredient_Fire_Essence", "Essence de feu, charbon, arc de flamme.",
                     "Fire essence, charcoal, flame bow.", [("Ingredient_Fire_Essence", 3, 1), ("Ingredient_Charcoal", 6, 1)],
                     [("Ingredient_Fire_Essence", 8, 3), ("Weapon_Shortbow_Flame", 1, 6)], None)]),
        dict(id="Deuxieme_Bauge", category="Elevage", prefab=PEN + "Slothian_Pen", rotation=0, job="Gardien_Bauge_Bis", kind="Breeder",
             fr="Deuxième bauge", en="Second sty", job_fr="Gardien de la bauge", job_en="Sty keeper", icon="Food_Pork_Raw",
             twin="Slothian_Bauge_De_Veille"),
    ],
}


# Conquête des lieux-dits (Kevin, 16 novembre 2026) : sixième projet de chaque peuple, la Maison du conseil, devenue
# l'Ambassade (catégorie Diplomatie). Chaque
# niveau ajoute un lieu-dit que le village peut tenir (world/Allegiance.cap) ; spécialités Diplomatie (ambassades
# +15 %, ralliement dès +70) et Garnison (un garde de plus par lieu-dit, relève le jour même, un soldat de plus par
# expédition ; Garnison est maintenant à la Caserne). Au niveau III, le tribut prend un tiers de la production au lieu d'un quart.
COUNCIL_SPECS = [
    ("Diplomatie", "Négociants", "Negotiators", "Recipe_Page", "Ambassades plus sûres, ralliement plus tôt ; rouleaux et parchemins.",
     "Surer embassies, earlier rallies; bolts and scrolls.", [("Ingredient_Bolt_Cotton", 4, 1), ("Recipe_Page", 2, 1)],
     [("Ingredient_Bolt_Linen", 4, 2), ("Ingredient_Bolt_Wool", 4, 2)], None),
    # Garnison passe à la Caserne (doc « Structurer les types de bâtiments », Kevin 2026-11-16) ; l'Ambassade prend les Hérauts.
    ("Herauts", "Hérauts", "Heralds", "Deco_Scroll", "Les relations avec les autres villages remontent deux fois plus vite ; cartes et bannières.",
     "Relations with other villages recover twice as fast; maps and banners.", [("Deco_Scroll", 2, 1), ("Deco_Map", 1, 2)],
     [("Furniture_Human_Ruins_Banner", 1, 3), ("Ingredient_Bolt_Silk", 2, 3)], None),
]
COUNCIL_BASE = [("Ingredient_Bolt_Cotton", 2, 1), ("Ingredient_Stick", 8, 1), ("Ingredient_Leather_Light", 2, 1)]


def council(prefab, kind, wood, extra, extra_fr, extra_en, dialogue=None):
    # Maison du conseil → Ambassade (id gardé pour les mondes lancés).
    d = dict(id="Conseil", category="Diplomatie", prefab=NPC + prefab, rotation=0, job="Conseiller", kind=kind, fr="Ambassade", en="Embassy",
             job_fr="Ambassadeur", job_en="Ambassador", icon="Recipe_Page",
             orders=[("Cotton", "Gather", "Plant_Crop_Cotton_Item", 12, "Coton des bannières", "Cotton for the banners"),
                     ("Wood", "Gather", wood, 16, "Bois de la grande table", "Wood for the great table"),
                     ("Gifts", "Gather", extra, 6, extra_fr, extra_en)],
             base=COUNCIL_BASE, specs=COUNCIL_SPECS)
    if dialogue:
        d["dialogue"] = dialogue
    return d


PROJECTS["Kweebec_Oak"].append(council("Kweebec/Oak/Houses_Small/Kweebec_Oak_Houses_Small_001", "Elder", "Wood_Oak_Trunk",
                                       "Ingredient_Fibre", "Fibres des cordes", "Fibre for the ropes"))
PROJECTS["Trork_Camp"].append(council("Trork/Misc/Large/Trork_Misc_Large_003", "@Trork_Warrior", "Wood_Oak_Trunk",
                                      "Ingredient_Hide_Light", "Peaux des tentures", "Hides for the hangings"))
PROJECTS["Feran_Oasis"].append(council("Feran/Portals_Oasis/Hut/Feran_Tier2_Hut_003", "Elder", "Wood_Dry_Trunk",
                                       "Ingredient_Salt", "Sel des hôtes", "Salt for the guests"))
PROJECTS["Renonce_Givre"].append(council("Outlander/Houses/Tier2/Outlander_Houses_Tier2_003", "Elder", "Wood_Fir_Trunk",
                                         "Ingredient_Hide_Heavy", "Fourrures des bancs", "Furs for the benches"))
PROJECTS["Slothian_Monastere"].append(council("Slothian/Disabled/House/Medium/Tall/Slothian_Disabled_House_Medium_Tall_002", "Elder",
                                              "Wood_Jungle_Trunk", "Furniture_Jungle_Candle", "Bougies du conseil", "Candles for the council"))


# ---- Projets des catégories Défense, Savoir et Culte (doc « Structurer les types de bâtiments », Kevin 2026-11-16) ----
# Caserne : +1 + niveau gardes en raid (workshop/Projects) ; spécialités Milice (encore +2 gardes en raid) et Garnison
# (+1 garde dans chaque lieu-dit, ouvrage et expédition). Bibliothèque : savoir-faire +15 %. Temple : essor +10 % ;
# spécialité Protection (un raid perdu ne brûle qu'une fois sur deux). Noms provisoires (doc), prefabs vanilla du peuple.
def caserne(prefab, kind, fr, en, job_fr, job_en, wood, metal, weapons2, weapons3, dialogue=None, raids=True):
    d = dict(id="Caserne", category="Defense", prefab=NPC + prefab, rotation=0, job="Capitaine", kind=kind, fr=fr, en=en,
             job_fr=job_fr, job_en=job_en, icon="Weapon_Shield_Wood",
             orders=[("Spears", "Gather", wood, 16, "Bois des lances", "Wood for the spears"),
                     ("Straps", "Gather", "Ingredient_Fibre", 10, "Cordes des harnais", "Ropes for the harness"),
                     ("Edges", "Gather", metal, 4, "Pointes et lames", "Points and blades")],
             base=[("Weapon_Spear_Crude", 1, 2), ("Weapon_Shield_Wood", 1, 2), ("Potion_Health_Lesser", 1, 1)],
             specs=[("Milice", "Milice", "Militia", "Weapon_Spear_Crude",
                     "En raid, deux gardes de plus ; lances et armures légères." if raids else "Lances et armures de la milice.",
                     "Two more guards in raids; spears and light armour." if raids else "Militia spears and armour.",
                     weapons2[0], weapons3[0], {"Guards": 2} if raids else None),
                    ("Garnison", "Garnison", "Garrison", "Weapon_Shield_Wood", "Un garde de plus dans chaque lieu-dit, ouvrage et expédition ; boucliers.",
                     "One more guard in each hamlet, work and expedition; shields.", weapons2[1], weapons3[1], None)])
    if dialogue:
        d["dialogue"] = dialogue
    return d


def bibliotheque(prefab, kind, fr, en, job_fr, job_en, paper, ink, specs, dialogue=None):
    d = dict(id="Bibliotheque", category="Savoir", prefab=NPC + prefab, rotation=0, job="Archiviste", kind=kind, fr=fr, en=en,
             job_fr=job_fr, job_en=job_en, icon="Deco_Book_Pile_Small",
             orders=[("Paper", "Gather", paper, 10, "De quoi écrire", "Something to write on"),
                     ("Ink", "Gather", ink, 6, "De quoi faire l'encre", "Something for ink"),
                     ("Quills", "Gather", "Ingredient_Feathers_Light", 6, "Plumes à écrire", "Quills")],
             base=[("Deco_Book_Pile_Small", 1, 1), ("Deco_Scroll", 1, 1), ("Recipe_Page", 1, 2)], specs=specs)
    if dialogue:
        d["dialogue"] = dialogue
    return d


def temple(prefab, kind, fr, en, job_fr, job_en, offering, candle, specs, dialogue=None):
    d = dict(id="Temple", category="Culte", prefab=NPC + prefab, rotation=0, job="Pretre", kind=kind, fr=fr, en=en,
             job_fr=job_fr, job_en=job_en, icon=candle,
             orders=[("Offerings", "Gather", offering, 8, "Offrandes", "Offerings"),
                     ("Essence", "Gather", "Ingredient_Life_Essence", 4, "Essence pour les rites", "Essence for the rites"),
                     ("Flowers", "Gather", "Plant_Flower_Common_White", 8, "Fleurs de l'autel", "Flowers for the altar")],
             base=[(candle, 2, 1), ("Potion_Health_Lesser", 1, 1), ("Potion_Stamina_Lesser", 1, 1)], specs=specs)
    if dialogue:
        d["dialogue"] = dialogue
    return d


KNOWLEDGE_SPECS = [
    ("Cartographes", "Cartographes", "Cartographers", "Deco_Map", "Cartes et relevés des environs.", "Maps and surveys of the land.",
     [("Deco_Map", 1, 2), ("Tool_Map", 1, 3)], [("Objective_Treasure_Map", 1, 5), ("Deco_Book_Pile_Large", 1, 3)], None),
    ("Maitres", "Maîtres", "Masters", "Recipe_Page", "Recettes et livres de savoir.", "Recipes and books of lore.",
     [("Recipe_Page", 2, 2), ("Deco_Inkwell", 1, 2)], [("Recipe_Food_Pie_Meat", 1, 4), ("Recipe_Food_Pie_Pumpkin", 1, 4)], None),
]


def cult_specs(blessing2, blessing3):
    return [
        ("Protection", "Protection", "Protection", "Potion_Health_Small", "Un raid perdu ne brûle un bâtiment qu'une fois sur deux ; potions.",
         "A lost raid burns a building only one time in two; potions.", [("Potion_Health_Small", 2, 2), ("Potion_Antidote", 1, 2)],
         [("Potion_Health", 1, 3), ("Potion_Regen_Health_Small", 2, 3)], None),
        ("Benediction", "Bénédiction", "Blessing", blessing2[0][0], "Offrandes et mets bénis.", "Offerings and blessed food.",
         blessing2, blessing3, None),
    ]


PROJECTS["Kweebec_Oak"] += [
    caserne("Kweebec/Oak/Guard_Towers/Kweebec_Oak_Guard_Towers_004", "Guard", "Quartier des Razorleaf", "Razorleaf quarters",
            "Capitaine razorleaf", "Razorleaf captain", "Wood_Ash_Trunk", "Ingredient_Bone_Fragment",
            ([("Weapon_Spear_Leaf", 1, 4), ("Armor_Wood_Head", 1, 2)], [("Weapon_Shield_Wood", 2, 3), ("Armor_Wood_Chest", 1, 3)]),
            ([("Weapon_Spear_Bone", 1, 5), ("Armor_Wood_Legs", 1, 3)], [("Armor_Kweebec_Head", 1, 4), ("Armor_Kweebec_Chest", 1, 5)])),
    bibliotheque("Kweebec/Oak/Shops/Kweebec_Oak_Shops_006", "Elder", "Maison des contes", "House of tales", "Conteuse", "Storyteller",
                 "Ingredient_Tree_Bark", "Plant_Flower_Common_Blue", KNOWLEDGE_SPECS),
    temple("Kweebec/Oak/Shops/Kweebec_Oak_Shops_007", "Elder", "Sanctuaire des racines", "Shrine of roots", "Gardienne des racines",
           "Root keeper", "Ingredient_Tree_Sap", "Furniture_Kweebec_Candle",
           cult_specs([("Food_Salad_Berry", 2, 1), ("Furniture_Kweebec_Lantern", 1, 2)], [("Food_Pie_Apple", 2, 2), ("Furniture_Kweebec_Statue", 1, 4)])),
]
PROJECTS["Trork_Camp"] += [
    caserne("Trork/Misc/Large/Trork_Misc_Large_004", "@Trork_Warrior", "Fosse des guerriers", "Warriors' pit", "Chef de guerre",
            "War chief", "Wood_Oak_Trunk", "Ingredient_Bar_Copper",
            ([("Weapon_Spear_Stone_Trork", 1, 3), ("Armor_Trork_Head", 1, 3)], [("Weapon_Shield_Scrap", 1, 3), ("Armor_Leather_Medium_Chest", 1, 3)]),
            ([("Weapon_Club_Stone_Trork", 1, 4), ("Armor_Trork_Legs", 1, 4)], [("Weapon_Shield_Scrap_Spiked", 1, 4), ("Armor_Leather_Heavy_Chest", 1, 5)]),
            raids=False),
    bibliotheque("Trork/Misc/Large/Trork_Misc_Large_005", "@Trork_Shaman", "Hutte du chaman", "Shaman's hut", "Chaman", "Shaman",
                 "Ingredient_Hide_Light", "Ingredient_Charcoal", KNOWLEDGE_SPECS),
    temple("Trork/Warning/Trork_Warning_Trork_Warning_002", "@Trork_Shaman", "Totem de guerre", "War totem", "Gardien du totem",
           "Totem keeper", "Ingredient_Bone_Fragment", "Furniture_Crude_Candle",
           cult_specs([("Food_Kebab_Meat", 2, 1), ("Deco_Bone_Skulls", 1, 2)], [("Food_Pie_Meat", 2, 2), ("Deco_Bone_Spike_Large", 1, 3)])),
]
PROJECTS["Feran_Oasis"] += [
    caserne("Feran/Tier3/Huts/Feran_Tier3_Huts_001", "Guard", "Camp des lanciers", "Lancers' camp", "Maître lancier", "Lance master",
            "Wood_Dry_Trunk", "Ingredient_Bar_Copper",
            ([("Weapon_Spear_Tribal", 1, 3), ("Armor_Leather_Soft_Head", 1, 2)], [("Weapon_Shield_Wood", 2, 3), ("Armor_Leather_Soft_Chest", 1, 3)]),
            ([("Weapon_Spear_Copper", 1, 4), ("Armor_Leather_Soft_Legs", 1, 3)], [("Weapon_Shield_Copper", 1, 4), ("Armor_Leather_Medium_Chest", 1, 4)])),
    bibliotheque("Feran/Tier3/Chieftain/Feran_Tier3_Chieftain_001", "Elder", "Tente des astrologues", "Astrologers' tent", "Astrologue",
                 "Astrologer", "Plant_Crop_Cotton_Item", "Ingredient_Salt", KNOWLEDGE_SPECS),
    temple("Feran/Tier2/Chieftain/Feran_Tier2_Chieftain_001", "Elder", "Temple du vent", "Temple of the wind", "Prêtresse du vent",
           "Wind priestess", "Ingredient_Salt", "Furniture_Feran_Candle",
           cult_specs([("Food_Kebab_Fruit", 2, 1), ("Furniture_Temple_Wind_Candle", 2, 2)], [("Food_Salad_Berry", 3, 2), ("Furniture_Feran_Bookshelf", 1, 3)])),
]
PROJECTS["Renonce_Givre"] += [
    bibliotheque("Outlander/Houses/Tier1/Outlander_Houses_Tier1_003", "Elder", "Archives du givre", "Frost archives", "Archiviste",
                 "Archivist", "Ingredient_Hide_Light", "Ingredient_Charcoal", KNOWLEDGE_SPECS),
    temple("Outlander/Misc/Outlander_Misc_006", "Elder", "Chapelle des repentis", "Chapel of the repentant", "Chapelain",
           "Chaplain", "Ingredient_Hide_Medium", "Furniture_Tavern_Candle",
           cult_specs([("Food_Bread", 2, 1), ("Furniture_Outlander_Banner", 1, 2)], [("Food_Pie_Pumpkin", 2, 2), ("Furniture_Village_Statue", 1, 4)])),
]
PROJECTS["Slothian_Monastere"] += [
    caserne("Slothian/Disabled/House/Medium/Slothian_Disabled_House_Medium_001", "Guard", "Cloître des gardiens", "Wardens' cloister",
            "Gardien en chef", "Head warden", "Wood_Jungle_Trunk", "Ingredient_Bar_Iron",
            ([("Weapon_Spear_Crude", 2, 3), ("Armor_Cloth_Linen_Head", 1, 2)], [("Weapon_Shield_Wood", 2, 3), ("Armor_Cloth_Linen_Chest", 1, 3)]),
            ([("Weapon_Spear_Iron", 1, 5), ("Armor_Cloth_Linen_Legs", 1, 3)], [("Weapon_Shield_Iron", 1, 5), ("Armor_Cloth_Silk_Chest", 1, 5)])),
]

# Les ateliers sont des raffineries : ressources prises chaque matin au dépôt, par niveau (workshop/Inputs). Certaines
# ne viennent pas du territoire du peuple (sel feran pour le fumoir renoncé, cuivre pour la forge trork…) : une route
# commerciale ou les joueurs les apportent.
INPUTS = {
    ("Kweebec_Oak", "Archerie"): [("Wood_Ash_Trunk", 4), ("Ingredient_Fibre", 4)],
    ("Kweebec_Oak", "Herboristerie"): [("Plant_Flower_Common_Blue", 3), ("Ingredient_Life_Essence", 1)],
    ("Kweebec_Oak", "Menuiserie"): [("Wood_Birch_Trunk", 6)],
    ("Trork_Camp", "Forge_De_Guerre"): [("Ingredient_Bone_Fragment", 4), ("Ingredient_Bar_Copper", 1)],
    ("Trork_Camp", "Tannerie"): [("Ingredient_Hide_Light", 3)],
    ("Feran_Oasis", "Tissage"): [("Plant_Crop_Cotton_Item", 4)],
    ("Feran_Oasis", "Volerie"): [("Food_Wildmeat_Raw", 2)],
    ("Renonce_Givre", "Forge"): [("Ingredient_Bar_Iron", 1), ("Ingredient_Charcoal", 2)],
    ("Renonce_Givre", "Fumoir"): [("Food_Wildmeat_Raw", 3), ("Ingredient_Salt", 1)],
}


def building_id(plot, project):
    return f"{plot}_{project}"


def job_id(plot, job):
    return f"{job}_{plot}"


def plot_rect(x, z):
    """Terrain de PLOT_SIZE blocs centré sur (x, z) : (x0, x1, z0, z1)."""
    half = PLOT_SIZE // 2
    return (x - half, x + half - 1, z - half, z + half - 1)
