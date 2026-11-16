#!/usr/bin/env python3
"""Bâtiments de métier des villages (GDD « Peuples d'Orbis : bâtiments de métier », étape 1 de son implémentation).

Un bâtiment de métier est un bâtiment du plan de village qui a un villageois à métier producteur (élevage, potager,
puits, soins, garde...). Il a son niveau (I à III), sa jauge de savoir-faire et son propre panneau de commandes, posé
devant lui par le Java (dev.nakasar.hytale.peuples.workshop.Workshops) : le même panneau vanilla du peuple que le
tableau du village (Nakasar_Peuples_Board_<Peuple>), dont l'interaction ouvre la page WorkshopPage.

Ce script lit les plans déjà générés (Server/Nakasar/VillageLayouts/*.json) et écrit :
  Server/Nakasar/Workshops/<Id>.json            un asset par bâtiment (plan, bâtiment, métier, place du panneau),
  Server/Nakasar/Requests/<Peuple>/<Bâtiment>/  les commandes du bâtiment (RequestTemplate avec « Workshop »),
  le bloc de langue « bâtiments de métier » des deux fichiers .lang (noms, commandes, textes de la page).

La place du panneau est calculée ici : un bloc hors de l'emprise du bâtiment, sur sa face tournée vers la place (là où
l'aplanissement du Java garde le sol plat), décalée de côté pour ne pas boucher l'entrée ni le poste du villageois,
et vérifiée hors de toute autre emprise (tous paliers), de la place et des postes des métiers.

    python3 tools/generate_workshops.py
"""
import json
from pathlib import Path

import outposts
import plots

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "src/main/resources/Server"
LAYOUTS = RES / "Nakasar/VillageLayouts"
OUT = RES / "Nakasar/Workshops"
REQUESTS = RES / "Nakasar/Requests"
ITEMS = Path(__file__).resolve().parent / "vanilla-item-ids-0.7.2.txt"
REFS = Path(__file__).resolve().parent / "vanilla-refs-0.7.2.txt"
PREFAB_BOUNDS = Path(__file__).resolve().parent / "vanilla-prefabs-0.7.2.txt"
DIALOGUES = RES / "Nakasar/Dialogues"
ANNEX_ITEMS = RES / "Item/Items/Nakasar/Peuples"

LANG_BEGIN = "# ---- Bâtiments de métier (généré par tools/generate_workshops.py, ne pas modifier à la main) ----"
LANG_END = "# ---- Fin des bâtiments de métier ----"

# Récompenses d'une commande (GDD) : savoir-faire, la moitié de la réputation d'une demande du tableau, 1 à 2 faveurs et
# 5 d'essor pour que le bâtiment aide aussi le village.
REWARD = {
    "Gather": dict(Knowledge=30, Essor=5, Favors=1, Reputation=5),
    "Craft": dict(Knowledge=40, Essor=5, Favors=1, Reputation=6),
    "Hunt": dict(Knowledge=45, Essor=5, Favors=2, Reputation=8),
}
HUNT_DISTANCE = (60, 110)
# Commande de maître (étape 2) : une par niveau, plus longue, qui ouvre le chantier d'amélioration. Elle reprend une
# commande du bâtiment en plus grand (×3 au niveau I, ×4 au niveau II ; bande doublée pour une chasse).
MASTER_REWARD = dict(Knowledge=0, Essor=15, Favors=3, Reputation=15)
MASTER_SCALE = {1: 3, 2: 4}
# Chantier d'amélioration (étape 2) : 12 h de jeu, matériaux pris au dépôt = la moitié des 3 premiers matériaux du
# chantier du palier correspondant du plan (palier 2 pour le niveau II, palier 3 pour le niveau III).
UPGRADE_HOURS = 12
# Décor vanilla posé à la fin d'un chantier d'amélioration, à côté du panneau (« dx dy dz lacet Bloc », seulement dans
# l'air au-dessus d'un bloc) : lumières du peuple, comme les étapes du cœur du village.
DECOR = {
    "Kweebec": {2: ["1 0 0 0 Furniture_Kweebec_Lantern"], 3: ["-1 0 0 0 Furniture_Kweebec_Lantern", "0 1 0 0 Furniture_Kweebec_Candle"]},
    "Trork": {2: ["1 0 0 0 Furniture_Crude_Torch"], 3: ["-1 0 0 0 Furniture_Crude_Brazier"]},
    "Feran": {2: ["1 0 0 0 Furniture_Feran_Torch"], 3: ["-1 0 0 0 Furniture_Feran_Torch_Tall"]},
    "Renonce": {2: ["1 0 0 0 Furniture_Lumberjack_Lantern"], 3: ["-1 0 0 0 Furniture_Lumberjack_Lantern"]},
    "Slothian": {2: ["1 0 0 0 Furniture_Jungle_Torch"], 3: ["-1 0 0 0 Furniture_Jungle_Brazier"]},
}

# Une commande : (suffixe, type, objet ou bande, quantité, titre fr, titre en). Les titres tiennent en 24 caractères
# (suivi d'objectif du HUD) ; la ligne de tâche est commune au type (TASKS).
# Un bâtiment : (id, plan, bâtiment du plan, métier, icône vanilla, nom fr, nom en, commandes).
WORKSHOPS = [
    ("Kweebec_Enclos", "Kweebec_Oak", "Enclos", "Eleveur", "Ingredient_Hay", "Enclos des lapins", "Rabbit pen", [
        ("Carrots", "Gather", "Plant_Crop_Turnip_Item", 10, "Navets des lapins", "Turnips for the rabbits"),
        ("Hay", "Gather", "Plant_Crop_Wheat_Item", 12, "Blé pour la litière", "Wheat for bedding"),
        ("Poachers", "Hunt", ["Trork_Hunter", "Trork_Hunter"], 0, "Braconniers trorks", "Trork poachers"),
    ]),
    # Étape 3 : les enclos des quatre autres peuples (tools/generate_pens.py, palier 1).
    ("Trork_Fosse_Aux_Betes", "Trork_Camp", "Fosse_Aux_Betes", "Dresseur", "Food_Wildmeat_Raw", "Fosse aux bêtes",
     "Beast pit", [
        ("Meat", "Gather", "Food_Beef_Raw", 6, "Bœuf pour la fosse", "Beef for the pit"),
        ("Bones", "Gather", "Food_Chicken_Raw", 8, "Volaille des bêtes", "Fowl for the beasts"),
        ("Wolves", "Hunt", ["Wolf_Black", "Wolf_Black"], 0, "Loups affamés", "Hungry wolves"),
    ]),
    ("Feran_Enclos_Oasis", "Feran_Oasis", "Enclos_Oasis", "Eleveuse", "Food_Egg", "Enclos de l'oasis", "Oasis pen", [
        ("Grain", "Gather", "Plant_Crop_Corn_Item", 8, "Maïs des poules", "Corn for the hens"),
        ("Water", "Gather", "Plant_Crop_Rice_Item", 8, "Riz pour l'enclos", "Rice for the pen"),
        ("Scaraks", "Hunt", ["Scarak_Fighter", "Scarak_Fighter"], 0, "Scaraks voleurs d'œufs", "Egg-thief Scaraks"),
    ]),
    ("Renonce_Bergerie_Du_Givre", "Renonce_Givre", "Bergerie_Du_Givre", "Berger", "Ingredient_Fabric_Scrap_Wool",
     "Bergerie du givre", "Frost fold", [
        ("Hay", "Gather", "Plant_Crop_Turnip_Item", 10, "Navets pour l'hiver", "Turnips for winter"),
        ("Wool", "Gather", "Ingredient_Salt", 6, "Sel pour les brebis", "Salt for the ewes"),
        ("Wolves", "Hunt", ["Wolf_White", "Wolf_White"], 0, "Loups des neiges", "Snow wolves"),
    ]),
    ("Slothian_Bauge_De_Veille", "Slothian_Monastere", "Bauge_De_Veille", "Gardien_Bauge", "Food_Pork_Raw",
     "Bauge de veille", "Vigil pen", [
        ("Mud", "Gather", "Soil_Mud_Dry", 16, "Boue de la bauge", "Mud for the pen"),
        ("Roots", "Gather", "Plant_Crop_Potato_Item", 10, "Patates des porcs", "Potatoes for the pigs"),
        ("Crawlers", "Hunt", ["Crawler_Void", "Crawler_Void"], 0, "Rampants à la bauge", "Crawlers at the pen"),
    ]),
    ("Kweebec_Potager", "Kweebec_Oak", "Potager", "Jardiniere", "Plant_Seeds_Lettuce", "Potager", "Vegetable garden", [
        ("Lettuce", "Gather", "Ingredient_Poop", 8, "Fumier du potager", "Manure for the garden"),
        ("Wheat", "Craft", "Tool_Hoe_Crude", 2, "Houes du potager", "Hoes for the garden"),
        ("Soup", "Craft", "Food_Salad_Mushroom", 3, "Salades de champignons", "Mushroom salads"),
    ]),
    ("Kweebec_Puits", "Kweebec_Oak", "Puits", "Puisatiere", "Container_Bucket", "Puits", "Well", [
        ("Buckets", "Craft", "Tool_Shovel_Crude", 2, "Pelles du puisatier", "Shovels for the digger"),
        ("Water", "Gather", "Soil_Clay", 16, "Argile du puits", "Clay for the well"),
        ("Stones", "Gather", "Soil_Gravel", 16, "Gravier de la margelle", "Gravel for the rim"),
    ]),
    ("Kweebec_Grande_Maison", "Kweebec_Oak", "Grande_Maison", "Soigneuse", "Potion_Health_Small", "Maison de soins",
     "House of healing", [
        ("Flowers", "Gather", "Plant_Crop_Mushroom_Cap_White", 6, "Champignons de soin", "Healing mushrooms"),
        ("Vials", "Craft", "Potion_Empty", 3, "Fioles vides", "Empty vials"),
        ("Essence", "Gather", "Ingredient_Fabric_Scrap_Cotton", 8, "Charpie à bandages", "Lint for bandages"),
    ]),
    ("Kweebec_Tour_Est", "Kweebec_Oak", "Tour_Est", "Garde", "Weapon_Arrow_Crude", "Tour de la garde", "Guard tower", [
        ("Arrows", "Craft", "Weapon_Spear_Crude", 3, "Lances pour la tour", "Spears for the tower"),
        ("Scouts", "Hunt", ["Trork_Warrior", "Trork_Warrior", "Trork_Brawler"], 0, "Éclaireurs trorks", "Trork scouts"),
        ("Palisade", "Gather", "Wood_Birch_Trunk", 12, "Bouleau de palissade", "Birch for the palisade"),
    ]),
    ("Trork_Piege", "Trork_Camp", "Piege", "Chasseur", "Ingredient_Hide_Light", "Piège du chasseur", "Hunter's trap", [
        ("Hides", "Gather", "Ingredient_Stick", 12, "Bois des collets", "Wood for snares"),
        ("Wolves", "Hunt", ["Wolf_Black", "Wolf_Black"], 0, "Loups du piège", "Wolves at the trap"),
        ("Bait", "Gather", "Food_Fish_Raw", 6, "Poisson pour l'appât", "Fish for bait"),
    ]),
    ("Trork_Feu_De_Camp", "Trork_Camp", "Feu_De_Camp", "Guerrier", "Food_Wildmeat_Cooked", "Feu de camp", "Campfire", [
        ("Roast", "Craft", "Food_Kebab_Mushroom", 4, "Brochettes du feu", "Skewers for the fire"),
        ("Logs", "Gather", "Wood_Dry_Trunk", 16, "Bois sec du feu", "Dry wood for the fire"),
        ("Mosshorn", "Hunt", ["Mosshorn"], 0, "Gros gibier", "Big game"),
    ]),
    ("Trork_Entrepot", "Trork_Camp", "Entrepot", "Cogneur", "Ingredient_Bar_Copper", "Entrepôt", "Warehouse", [
        ("Copper", "Gather", "Ingredient_Charcoal", 8, "Charbon de l'entrepôt", "Charcoal for the store"),
        ("Stones", "Gather", "Rock_Shale_Cobble", 24, "Schiste de l'entrepôt", "Shale for the store"),
        ("Hides", "Gather", "Ingredient_Hide_Medium", 6, "Peaux épaisses", "Thick hides"),
    ]),
    ("Feran_Entree_Oasis", "Feran_Oasis", "Entree_Oasis", "Porteuse_Eau", "Container_Bucket", "Entrée de l'oasis",
     "Oasis gate", [
        ("Buckets", "Gather", "Soil_Clay", 12, "Argile des jarres", "Clay for the jars"),
        ("Water", "Gather", "Plant_Fruit_Coconut", 4, "Noix de coco", "Coconuts"),
        ("Salt", "Gather", "Plant_Fruit_Mango", 4, "Mangues de l'oasis", "Oasis mangoes"),
    ]),
    ("Feran_Hutte_Pilier", "Feran_Oasis", "Hutte_Pilier", "Garde", "Weapon_Spear_Crude", "Hutte de la garde",
     "Guard hut", [
        ("Spears", "Craft", "Ingredient_Strap_Leather", 4, "Sangles de la garde", "Straps for the guard"),
        ("Scaraks", "Hunt", ["Scarak_Fighter", "Scarak_Fighter", "Scarak_Fighter"], 0, "Scaraks aux portes",
         "Scaraks at the gates"),
        ("Feathers", "Gather", "Food_Chicken_Raw", 6, "Volaille des coureurs", "Fowl for the runners"),
    ]),
    ("Renonce_Maison_Du_Chasseur", "Renonce_Givre", "Maison_Du_Chasseur", "Chasseur", "Ingredient_Hide_Heavy",
     "Maison du chasseur", "Hunter's lodge", [
        ("Hides", "Gather", "Ingredient_Hide_Soft", 4, "Peaux souples", "Soft hides"),
        ("Meat", "Gather", "Ingredient_Stick", 12, "Bois des collets", "Wood for snares"),
        ("Poachers", "Hunt", ["Outlander_Hunter", "Outlander_Hunter"], 0, "Braconniers du culte", "Cult poachers"),
    ]),
    ("Renonce_Tour_Du_Fort", "Renonce_Givre", "Tour_Du_Fort", "Garde", "Weapon_Arrow_Crude", "Tour du fort",
     "Fort tower", [
        ("Fir", "Gather", "Rock_Stone_Cobble", 24, "Pierres des remparts", "Stones for the ramparts"),
        ("Cultists", "Hunt", ["Outlander_Cultist", "Outlander_Cultist", "Outlander_Cultist"], 0,
         "Cultistes près du fort", "Cultists near the fort"),
        ("Arrows", "Gather", "Ingredient_Feathers_Light", 10, "Plumes d'empennage", "Fletching feathers"),
    ]),
    ("Slothian_Etal_Des_Cendres", "Slothian_Monastere", "Etal_Des_Cendres", "Porteur_Cendres", "Ingredient_Charcoal",
     "Étal des cendres", "Ash stall", [
        ("Ash", "Gather", "Soil_Ash", 20, "Cendres de l'étal", "Ash for the stall"),
        ("Charcoal", "Gather", "Wood_Jungle_Trunk", 12, "Bois des braises", "Wood for the embers"),
        ("Fire", "Gather", "Plant_Crop_Chilli_Item", 6, "Piments ardents", "Fiery chillies"),
    ]),
    ("Slothian_Temple_De_Veille", "Slothian_Monastere", "Temple_De_Veille", "Moine", "Furniture_Jungle_Candle",
     "Temple de veille", "Vigil temple", [
        ("Candles", "Gather", "Plant_Flower_Common_Purple", 8, "Fleurs d'offrande", "Offering flowers"),
        ("Void", "Gather", "Ingredient_Crystal_Purple", 2, "Cristaux du temple", "Temple crystals"),
        ("Potions", "Craft", "Potion_Empty", 3, "Fioles de veille", "Vigil vials"),
    ]),
    ("Slothian_Porte_Du_Monastere", "Slothian_Monastere", "Porte_Du_Monastere", "Garde", "Rock_Volcanic",
     "Porte du monastère", "Monastery gate", [
        ("Crawlers", "Hunt", ["Crawler_Void", "Crawler_Void", "Crawler_Void"], 0, "Rampants du Vide",
         "Void crawlers"),
        ("Basalt", "Gather", "Rock_Basalt_Cobble", 20, "Basalte de la porte", "Basalt for the gate"),
        ("Burnt", "Hunt", ["Skeleton_Burnt_Soldier", "Skeleton_Burnt_Soldier"], 0, "Morts brûlés", "Burnt dead"),
    ]),
]

# Étape 3 : spécialités (choisies au niveau II, rang Ami ; une reconversion tous les 7 jours) et bêtes des enclos.
# Un bâtiment : (bêtes de base, [(id, nom fr, nom en, icône, ligne fr, ligne en, bêtes)]). Les bêtes sont des rôles
# vanilla Tamed_* (Assets.zip), ou du mod (tools/generate_pens.py) quand le jeu n'en a pas d'apprivoisé.
PEN = "Nakasar_Peuples_Pen_"
SPECIALTIES = {
    "Kweebec_Enclos": (["Tamed_Bunny", "Tamed_Rabbit"], [
        ("Basse_Cour", "Basse-cour", "Poultry yard", "Food_Egg", "Poules et dindons : œufs, plumes, volaille.",
         "Hens and turkeys: eggs, feathers, poultry.", ["Tamed_Chicken", "Tamed_Turkey", "Tamed_Chicken_Chick"]),
        ("Mousse_Cornes", "Mousse-cornes", "Mosshorns", "Ingredient_Life_Essence",
         "Mousse-cornes : fibre, écorce et essence de vie.", "Mosshorns: fibre, bark and life essence.",
         ["Tamed_Mosshorn", "Tamed_Mosshorn_Plain"]),
        ("Bergerie", "Bergerie", "Sheepfold", "Ingredient_Fabric_Scrap_Wool", "Moutons : laine, rouleaux de laine.",
         "Sheep: wool, bolts of wool.", ["Tamed_Sheep", "Tamed_Sheep_Lamb"]),
    ]),
    "Trork_Fosse_Aux_Betes": (["Tamed_Boar", "Tamed_Boar_Piglet"], [
        ("Loups", "Loups de chasse", "Hunting wolves", "Ingredient_Bone_Fragment", "Loups dressés : crocs, os, peaux.",
         "Trained wolves: fangs, bones, hides.", [PEN + "Wolf_Trork"]),
        ("Porcs_Sauvages", "Porcs sauvages", "Wild pigs", "Food_Pork_Raw", "Porcs sauvages : viande et cuir.",
         "Wild pigs: meat and leather.", ["Tamed_Pig_Wild", "Tamed_Pig_Wild_Piglet"]),
        ("Chevres", "Chèvres des cimes", "Peak goats", "Ingredient_Hide_Medium", "Chèvres : peaux moyennes et lait caillé.",
         "Goats: medium hides and curds.", ["Tamed_Goat", "Tamed_Goat_Kid"]),
    ]),
    "Feran_Enclos_Oasis": (["Tamed_Chicken_Desert", "Tamed_Chicken_Desert_Chick"], [
        ("Chameaux", "Chameaux", "Camels", "Ingredient_Hide_Scaled", "Chameaux : cuir et eau des caravanes.",
         "Camels: leather and caravan water.", ["Tamed_Camel", "Tamed_Camel_Calf"]),
        ("Beliers", "Béliers du plateau", "Plateau rams", "Ingredient_Fabric_Scrap_Wool", "Béliers : laine et cornes.",
         "Rams: wool and horns.", ["Tamed_Ram", "Tamed_Ram_Lamb"]),
        ("Tortues", "Tortues de l'oasis", "Oasis tortoises", "Ingredient_Hide_Scaled", "Tortues : écailles et essence d'eau.",
         "Tortoises: scales and water essence.", [PEN + "Tortoise"]),
    ]),
    "Renonce_Bergerie_Du_Givre": (["Tamed_Mouflon", "Tamed_Mouflon_Lamb"], [
        ("Bisons", "Bisons", "Bison", "Food_Beef_Raw", "Bisons : bœuf et peaux lourdes.", "Bison: beef and heavy hides.",
         ["Tamed_Bison", "Tamed_Bison_Calf"]),
        ("Sangliers", "Sangliers des neiges", "Snow boars", "Food_Wildmeat_Raw", "Sangliers : viande et défenses.",
         "Boars: meat and tusks.", ["Tamed_Boar", "Tamed_Boar_Piglet"]),
        ("Loups_Blancs", "Loups blancs des repentis", "Penitents' white wolves", "Ingredient_Hide_Heavy",
         "Loups blancs : fourrures épaisses.", "White wolves: thick furs.", [PEN + "Wolf_White"]),
    ]),
    "Slothian_Bauge_De_Veille": (["Tamed_Pig_Wild", "Tamed_Pig_Wild_Piglet"], [
        ("Archeopteryx", "Archéoptéryx", "Archaeopteryx", "Ingredient_Feathers_Dark", "Archéoptéryx : plumes sombres.",
         "Archaeopteryx: dark feathers.", [PEN + "Archaeopteryx"]),
        ("Trillodons", "Trillodons", "Trillodons", "Ingredient_Hide_Heavy", "Trillodons : cuir épais et cornes.",
         "Trillodons: thick leather and horns.", [PEN + "Trillodon"]),
        ("Escargots", "Escargots de magme", "Magma snails", "Ingredient_Fire_Essence",
         "Escargots de magme : coquilles et essence de feu.", "Magma snails: shells and fire essence.", [PEN + "Snail_Magma"]),
    ]),
    # Les autres bâtiments de métier (GDD, « Les autres bâtiments de métier ») : deux spécialités sans bêtes.
    "Kweebec_Potager": (None, [
        ("Maraicher", "Maraîcher", "Market garden", "Plant_Crop_Lettuce_Item", "Graines, légumes et salades.",
         "Seeds, vegetables and salads.", []),
        ("Verger", "Verger à baies", "Berry orchard", "Plant_Fruit_Berries_Red", "Baies, baies d'hiver et tartes.",
         "Berries, winter berries and pies.", []),
    ]),
    "Kweebec_Puits": (None, [
        ("Source", "Source claire", "Clear spring", "Ingredient_Water_Essence", "Essence d'eau et fioles.",
         "Water essence and vials.", []),
        ("Vivier", "Vivier", "Fish pond", "Food_Fish_Raw", "Poissons d'eau douce et nasses.", "Freshwater fish and traps.", []),
    ]),
    "Kweebec_Grande_Maison": (None, [
        ("Herbes", "Herbes de soin", "Healing herbs", "Potion_Health_Small", "Potions de vie.", "Health potions.", []),
        ("Elixirs", "Élixirs", "Elixirs", "Potion_Stamina_Small", "Endurance et antidotes.", "Stamina and antidotes.", []),
    ]),
    "Kweebec_Tour_Est": (None, [
        ("Archers", "Archers", "Archers", "Weapon_Shortbow_Crude", "Arcs et flèches ; en raid, 2 gardes de plus postés à la tour.",
         "Bows and arrows; in raids, 2 more guards posted at the tower.", []),
        ("Vigiles", "Vigiles", "Wardens", "Armor_Kweebec_Chest", "Armure kweebec ; en raid, +1 garde et des gardes plus solides.",
         "Kweebec armour; in raids, +1 guard and sturdier guards.", []),
    ]),
    "Trork_Piege": (None, [
        ("Trappeur", "Trappeur", "Trapper", "Ingredient_Hide_Light", "Peaux et os.", "Hides and bones.", []),
        ("Rabatteur", "Rabatteur", "Beater", "Food_Wildmeat_Raw", "Viande et brochettes.", "Meat and skewers.", []),
    ]),
    "Trork_Feu_De_Camp": (None, [
        ("Rotisserie", "Rôtisserie", "Roasting pit", "Food_Wildmeat_Cooked", "Viandes cuites.", "Cooked meats.", []),
        ("Fosse_De_Combat", "Fosse de combat", "Fighting pit", "Weapon_Club_Crude", "Armes en os et armure trork.",
         "Bone weapons and Trork armour.", []),
    ]),
    "Trork_Entrepot": (None, [
        ("Pillards", "Pillards", "Raiders", "Ingredient_Bar_Iron", "Lingots de cuivre et de fer récupérés.",
         "Salvaged copper and iron bars.", []),
        ("Bucherons", "Bûcherons", "Lumberjacks", "Wood_Oak_Trunk", "Rondins, bâtons et écorce.", "Logs, sticks and bark.", []),
    ]),
    "Feran_Entree_Oasis": (None, [
        ("Citerne", "Citerne", "Cistern", "Ingredient_Water_Essence", "Essence d'eau ; la soif s'apaise au village.",
         "Water essence; thirst eases in the village.", []),
        ("Jardin", "Jardin d'oasis", "Oasis garden", "Ingredient_Salt", "Cactus, épices et sel.", "Cactus, spices and salt.", []),
    ]),
    "Feran_Hutte_Pilier": (None, [
        ("Lanciers", "Lanciers", "Spearmen", "Weapon_Spear_Crude", "Lances ; en raid, des gardes plus solides.",
         "Spears; sturdier guards in raids.", []),
        ("Coureurs", "Coureurs des vents", "Windrunners", "Ingredient_Feathers_Light", "Plumes, armure légère ; en raid, +1 garde.",
         "Feathers, light armour; +1 guard in raids.", []),
    ]),
    "Renonce_Maison_Du_Chasseur": (None, [
        ("Trappeur", "Trappeur des neiges", "Snow trapper", "Ingredient_Hide_Heavy", "Peaux lourdes et fourrures.",
         "Heavy hides and furs.", []),
        ("Pecheur", "Pêcheur des glaces", "Ice fisher", "Food_Fish_Raw", "Poissons des eaux froides.", "Cold-water fish.", []),
    ]),
    "Renonce_Tour_Du_Fort": (None, [
        ("Arbaletriers", "Arbalétriers", "Crossbowmen", "Weapon_Crossbow_Iron", "Arbalètes ; en raid, 2 gardes de plus postés à la tour.",
         "Crossbows; in raids, 2 more guards posted at the tower.", []),
        ("Gardes_Du_Givre", "Gardes du givre", "Frost guards", "Ingredient_Fabric_Scrap_Wool",
         "Manteaux ; en raid, +1 garde et des gardes plus solides.",
         "Coats; in raids, +1 guard and sturdier guards.", []),
    ]),
    "Slothian_Etal_Des_Cendres": (None, [
        ("Braises", "Braises", "Embers", "Ingredient_Charcoal", "Essence de feu et charbon.", "Fire essence and charcoal.", []),
        ("Encens", "Encens de veille", "Vigil incense", "Furniture_Jungle_Candle", "Objets contre la corruption du Vide.",
         "Wares against the Void's corruption.", []),
    ]),
    "Slothian_Temple_De_Veille": (None, [
        ("Meditation", "Méditation", "Meditation", "Potion_Regen_Mana_Small", "Potions de régénération.",
         "Regeneration potions.", []),
        ("Chroniques", "Chroniques", "Chronicles", "Ingredient_Life_Essence", "Recettes et objets de mémoire.",
         "Recipes and memory items.", []),
    ]),
    "Slothian_Porte_Du_Monastere": (None, [
        ("Lances", "Lances de basalte", "Basalt spears", "Rock_Volcanic", "Lances ; en raid, des gardes bien plus solides.",
         "Spears; much sturdier guards in raids.", []),
        ("Veilleurs", "Veilleurs", "Watchers", "Furniture_Jungle_Torch", "Torches ; en raid, +1 garde.",
         "Torches; +1 guard in raids.", []),
    ]),
}
# Étape 5 : effet en raid des spécialités de garde (bâtiment ouvert, niveau II ou plus, spécialité choisie) :
# Guards gardes de plus autour du cœur, Posted gardes postés au bâtiment (la tour), Health multiplicateur des PV
# maximaux de tous les gardes du raid. Au niveau III, Guards et Posted prennent +1. Les Trorks ne subissent pas de raid.
RAID = {
    ("Kweebec_Tour_Est", "Archers"): {"Posted": 2},
    ("Kweebec_Tour_Est", "Vigiles"): {"Guards": 1, "Health": 1.25},
    ("Feran_Hutte_Pilier", "Lanciers"): {"Health": 1.35},
    ("Feran_Hutte_Pilier", "Coureurs"): {"Guards": 1},
    ("Renonce_Tour_Du_Fort", "Arbaletriers"): {"Posted": 2},
    ("Renonce_Tour_Du_Fort", "Gardes_Du_Givre"): {"Guards": 1, "Health": 1.25},
    ("Slothian_Porte_Du_Monastere", "Lances"): {"Health": 1.5},
    ("Slothian_Porte_Du_Monastere", "Veilleurs"): {"Guards": 1},
}
# Bêtes d'un enclos selon le niveau (GDD : 3, 5 puis 7, les petits en font partie).
LIVESTOCK_COUNT = [3, 5, 7]
# Intérieur de l'enclos = emprise du bâtiment réduite de ce nombre de blocs (la clôture et une marge).
PEN_INSET = 2

# Étape 4 : une boutique de troc vanilla par bâtiment, spécialité et niveau, payée en faveurs du peuple. Le niveau I
# (et un bâtiment sans spécialité) vend « Base » ; aux niveaux II et III la boutique de la spécialité reprend la base et
# ajoute ses échanges, cumulés. Un échange : (objet vanilla, quantité, prix en faveurs). Le lot de la Part de l'Hôte
# (niveau III, rang Hôte, une fois par jour) est le premier échange du niveau II de la spécialité.
# Un bâtiment : {"Base": [échanges], spécialité: ([niveau II], [niveau III])}.
SHOPS = {
    "Kweebec_Enclos": {
        "Base": [("Ingredient_Hay", 8, 1), ("Food_Egg", 3, 1), ("Plant_Crop_Carrot_Item", 4, 1)],
        "Basse_Cour": ([("Food_Egg", 6, 1), ("Ingredient_Feathers_Light", 6, 1)],
                       [("Food_Chicken_Raw", 4, 2), ("Food_Pie_Meat", 2, 3)]),
        "Mousse_Cornes": ([("Ingredient_Fibre", 8, 1), ("Ingredient_Tree_Bark", 6, 1)],
                          [("Ingredient_Life_Essence", 6, 2), ("Ingredient_Life_Essence_Concentrated", 1, 4)]),
        "Bergerie": ([("Ingredient_Fabric_Scrap_Wool", 6, 1), ("Food_Cheese", 2, 2)],
                     [("Ingredient_Bolt_Wool", 2, 3), ("Armor_Wool_Chest", 1, 5)]),
    },
    "Trork_Fosse_Aux_Betes": {
        "Base": [("Food_Wildmeat_Raw", 3, 1), ("Ingredient_Bone_Fragment", 6, 1), ("Ingredient_Hide_Light", 2, 1)],
        "Loups": ([("Ingredient_Bone_Fragment", 10, 1), ("Ingredient_Hide_Medium", 2, 2)],
                  [("Ingredient_Leather_Medium", 3, 3), ("Weapon_Daggers_Claw_Bone", 1, 4)]),
        "Porcs_Sauvages": ([("Food_Pork_Raw", 4, 1), ("Ingredient_Leather_Light", 3, 1)],
                           [("Ingredient_Strap_Leather", 4, 2), ("Food_Pie_Meat", 2, 3)]),
        "Chevres": ([("Ingredient_Hide_Medium", 3, 1), ("Food_Cheese", 2, 2)],
                    [("Ingredient_Leather_Medium", 4, 3), ("Armor_Leather_Medium_Chest", 1, 5)]),
    },
    "Feran_Enclos_Oasis": {
        "Base": [("Food_Egg", 4, 1), ("Ingredient_Feathers_Light", 4, 1), ("Plant_Seeds_Wheat", 6, 1)],
        "Chameaux": ([("Ingredient_Hide_Scaled", 2, 2), ("Ingredient_Water_Essence", 2, 1)],
                     [("Ingredient_Leather_Scaled", 3, 3), ("Armor_Leather_Light_Chest", 1, 4)]),
        "Beliers": ([("Ingredient_Fabric_Scrap_Wool", 6, 1), ("Food_Cheese", 2, 2)],
                    [("Ingredient_Bolt_Wool", 2, 3), ("Armor_Wool_Head", 1, 4)]),
        "Tortues": ([("Ingredient_Hide_Scaled", 3, 2), ("Ingredient_Water_Essence", 3, 1)],
                    [("Ingredient_Leather_Scaled", 4, 3), ("Ingredient_Chitin_Sturdy", 2, 3)]),
    },
    "Renonce_Bergerie_Du_Givre": {
        "Base": [("Ingredient_Fabric_Scrap_Wool", 4, 1), ("Ingredient_Hay", 8, 1), ("Food_Cheese", 1, 1)],
        "Bisons": ([("Food_Beef_Raw", 4, 1), ("Ingredient_Hide_Heavy", 2, 2)],
                   [("Ingredient_Leather_Heavy", 3, 3), ("Armor_Leather_Heavy_Chest", 1, 5)]),
        "Sangliers": ([("Food_Wildmeat_Raw", 4, 1), ("Ingredient_Hide_Medium", 2, 1)],
                      [("Food_Kebab_Meat", 3, 2), ("Armor_Leather_Medium_Legs", 1, 4)]),
        "Loups_Blancs": ([("Ingredient_Hide_Heavy", 2, 2), ("Ingredient_Bone_Fragment", 8, 1)],
                         [("Ingredient_Leather_Heavy", 4, 3), ("Armor_Wool_Chest", 1, 4)]),
    },
    "Slothian_Bauge_De_Veille": {
        "Base": [("Food_Pork_Raw", 2, 1), ("Ingredient_Leather_Light", 2, 1), ("Plant_Crop_Carrot_Item", 4, 1)],
        "Archeopteryx": ([("Ingredient_Feathers_Dark", 4, 1), ("Food_Egg", 4, 1)],
                         [("Ingredient_Feathers_Red", 4, 2), ("Weapon_Arrow_Iron", 16, 3)]),
        "Trillodons": ([("Ingredient_Hide_Heavy", 2, 2), ("Food_Beef_Raw", 3, 1)],
                       [("Ingredient_Leather_Heavy", 4, 3), ("Armor_Leather_Heavy_Legs", 1, 5)]),
        "Escargots": ([("Ingredient_Fire_Essence", 2, 1), ("Ingredient_Charcoal", 6, 1)],
                      [("Ingredient_Chitin_Sturdy", 2, 3), ("Ingredient_Fire_Essence", 6, 3)]),
    },
    "Kweebec_Potager": {
        "Base": [("Plant_Seeds_Lettuce", 4, 1), ("Plant_Seeds_Carrot", 4, 1), ("Food_Vegetable_Cooked", 2, 1)],
        "Maraicher": ([("Plant_Crop_Lettuce_Item", 4, 1), ("Plant_Seeds_Tomato", 4, 1)],
                      [("Food_Salad_Caesar", 2, 2), ("Plant_Seeds_Carrot_Eternal", 1, 5)]),
        "Verger": ([("Plant_Fruit_Berries_Red", 6, 1), ("Plant_Fruit_Apple", 4, 1)],
                   [("Food_Salad_Berry", 2, 2), ("Food_Pie_Apple", 2, 3)]),
    },
    "Kweebec_Puits": {
        "Base": [("Ingredient_Water_Essence", 2, 1), ("Container_Bucket", 1, 2), ("Rock_Stone_Cobble", 16, 1)],
        "Source": ([("Ingredient_Water_Essence", 4, 1), ("Potion_Empty_Small", 3, 1)],
                   [("Potion_Purify", 1, 3), ("Tool_Watering_Can", 1, 3)]),
        "Vivier": ([("Food_Fish_Raw", 3, 1), ("Tool_Fishing_Trap", 1, 2)],
                   [("Food_Fish_Grilled", 3, 2), ("Food_Fish_Raw_Rare", 1, 4)]),
    },
    "Kweebec_Grande_Maison": {
        "Base": [("Potion_Health_Lesser", 1, 1), ("Plant_Flower_Common_Red", 4, 1), ("Ingredient_Life_Essence", 3, 1)],
        "Herbes": ([("Potion_Health_Small", 2, 1), ("Potion_Regen_Health_Small", 1, 2)],
                   [("Potion_Health", 1, 3), ("Potion_Health_Large", 1, 5)]),
        "Elixirs": ([("Potion_Stamina_Small", 2, 1), ("Potion_Antidote", 1, 2)],
                    [("Potion_Stamina", 1, 3), ("Potion_Regen_Stamina", 1, 4)]),
    },
    "Kweebec_Tour_Est": {
        "Base": [("Weapon_Arrow_Crude", 16, 1), ("Wood_Oak_Trunk", 8, 1), ("Weapon_Shortbow_Crude", 1, 2)],
        "Archers": ([("Weapon_Arrow_Iron", 16, 2), ("Weapon_Shortbow_Copper", 1, 3)],
                    [("Weapon_Arrow_Trueshot", 8, 4), ("Weapon_Shortbow_Iron", 1, 5)]),
        "Vigiles": ([("Tool_Repair_Kit_Crude", 1, 2), ("Armor_Kweebec_Head", 1, 3)],
                    [("Tool_Repair_Kit_Iron", 1, 4), ("Armor_Kweebec_Chest", 1, 5)]),
    },
    "Trork_Piege": {
        "Base": [("Ingredient_Hide_Light", 2, 1), ("Ingredient_Bone_Fragment", 6, 1), ("Tool_Trap_Bait", 2, 1)],
        "Trappeur": ([("Ingredient_Hide_Medium", 2, 1), ("Ingredient_Leather_Light", 3, 1)],
                     [("Ingredient_Leather_Medium", 3, 3), ("Armor_Leather_Light_Head", 1, 3)]),
        "Rabatteur": ([("Food_Wildmeat_Raw", 4, 1), ("Food_Kebab_Meat", 2, 1)],
                      [("Food_Pie_Meat", 2, 3), ("Tool_Capture_Crate", 1, 5)]),
    },
    "Trork_Feu_De_Camp": {
        "Base": [("Food_Wildmeat_Cooked", 2, 1), ("Ingredient_Charcoal", 4, 1), ("Wood_Oak_Trunk", 8, 1)],
        "Rotisserie": ([("Food_Wildmeat_Cooked", 4, 1), ("Food_Kebab_Meat", 3, 1)],
                       [("Ingredient_Spices", 3, 2), ("Food_Pie_Meat", 2, 3)]),
        "Fosse_De_Combat": ([("Weapon_Club_Crude", 1, 2), ("Weapon_Sword_Bone", 1, 3)],
                            [("Weapon_Axe_Bone", 1, 4), ("Armor_Trork_Chest", 1, 5)]),
    },
    "Trork_Entrepot": {
        "Base": [("Rock_Stone_Cobble", 16, 1), ("Ingredient_Bar_Copper", 1, 1), ("Ingredient_Stick", 8, 1)],
        "Pillards": ([("Ingredient_Bar_Copper", 3, 2), ("Ingredient_Bar_Iron", 1, 2)],
                     [("Ingredient_Stud_Iron", 4, 3), ("Ingredient_Bar_Iron", 3, 4)]),
        "Bucherons": ([("Wood_Oak_Trunk", 16, 1), ("Ingredient_Tree_Bark", 6, 1)],
                      [("Ingredient_Tree_Sap", 4, 2), ("Tool_Hatchet_Iron", 1, 5)]),
    },
    "Feran_Entree_Oasis": {
        "Base": [("Ingredient_Water_Essence", 2, 1), ("Ingredient_Salt", 3, 1), ("Container_Bucket", 1, 2)],
        "Citerne": ([("Ingredient_Water_Essence", 4, 1), ("Potion_Empty_Small", 3, 1)],
                    [("Potion_Regen_Stamina_Small", 2, 3), ("Potion_Purify", 1, 3)]),
        "Jardin": ([("Ingredient_Spices", 2, 1), ("Plant_Cactus_Flower", 2, 1)],
                   [("Ingredient_Salt", 8, 2), ("Plant_Seeds_Chilli", 4, 2)]),
    },
    "Feran_Hutte_Pilier": {
        "Base": [("Weapon_Spear_Crude", 1, 2), ("Ingredient_Feathers_Light", 4, 1), ("Weapon_Arrow_Crude", 16, 1)],
        "Lanciers": ([("Weapon_Spear_Bone", 1, 3), ("Weapon_Spear_Copper", 1, 3)],
                     [("Weapon_Spear_Tribal", 1, 4), ("Weapon_Spear_Iron", 1, 5)]),
        "Coureurs": ([("Ingredient_Feathers_Light", 8, 1), ("Armor_Leather_Soft_Head", 1, 2)],
                     [("Potion_Stamina", 1, 3), ("Armor_Leather_Soft_Chest", 1, 4)]),
    },
    "Renonce_Maison_Du_Chasseur": {
        "Base": [("Ingredient_Hide_Heavy", 1, 1), ("Food_Wildmeat_Raw", 3, 1), ("Ingredient_Fabric_Scrap_Wool", 3, 1)],
        "Trappeur": ([("Ingredient_Hide_Heavy", 2, 1), ("Ingredient_Leather_Heavy", 1, 2)],
                     [("Armor_Leather_Heavy_Head", 1, 4), ("Armor_Leather_Heavy_Hands", 1, 4)]),
        "Pecheur": ([("Food_Fish_Raw", 4, 1), ("Tool_Fishing_Trap", 1, 2)],
                    [("Food_Fish_Grilled", 4, 2), ("Food_Fish_Raw_Uncommon", 2, 3)]),
    },
    "Renonce_Tour_Du_Fort": {
        "Base": [("Weapon_Arrow_Crude", 16, 1), ("Wood_Fir_Trunk", 8, 1), ("Weapon_Shortbow_Crude", 1, 2)],
        "Arbaletriers": ([("Weapon_Arrow_Iron", 16, 2), ("Weapon_Crossbow_Iron", 1, 4)],
                         [("Weapon_Arrow_Deadeye", 8, 4), ("Weapon_Crossbow_Ancient_Steel", 1, 6)]),
        "Gardes_Du_Givre": ([("Armor_Wool_Head", 1, 2), ("Armor_Wool_Hands", 1, 2)],
                            [("Armor_Wool_Chest", 1, 4), ("Armor_Wool_Legs", 1, 4)]),
    },
    "Slothian_Etal_Des_Cendres": {
        "Base": [("Ingredient_Charcoal", 4, 1), ("Ingredient_Fire_Essence", 1, 1), ("Furniture_Jungle_Torch", 2, 1)],
        "Braises": ([("Ingredient_Fire_Essence", 3, 1), ("Ingredient_Charcoal", 8, 1)],
                    [("Ingredient_Fire_Essence", 8, 3), ("Weapon_Shortbow_Flame", 1, 6)]),
        "Encens": ([("Furniture_Jungle_Candle", 3, 1), ("Potion_Purify", 1, 2)],
                   [("Potion_Antidote", 2, 3), ("Furniture_Jungle_Brazier", 1, 4)]),
    },
    "Slothian_Temple_De_Veille": {
        "Base": [("Furniture_Jungle_Candle", 2, 1), ("Potion_Mana_Small", 1, 1), ("Ingredient_Void_Essence", 1, 2)],
        "Meditation": ([("Potion_Regen_Mana_Small", 2, 1), ("Potion_Regen_Health_Small", 1, 2)],
                       [("Potion_Regen_Mana", 1, 3), ("Potion_Regen_Health", 1, 4)]),
        "Chroniques": ([("Ingredient_Life_Essence", 4, 1), ("Recipe_Page", 1, 2)],
                       [("Recipe_Plant_Seeds_Mana1", 1, 4), ("Recipe_Book_Magic_Void", 1, 6)]),
    },
    "Slothian_Porte_Du_Monastere": {
        "Base": [("Rock_Volcanic", 16, 1), ("Weapon_Spear_Crude", 1, 2), ("Furniture_Jungle_Torch", 2, 1)],
        "Lances": ([("Rock_Volcanic", 24, 1), ("Weapon_Spear_Stone_Trork", 1, 3)],
                   [("Weapon_Spear_Iron", 1, 5), ("Weapon_Spear_Bronze", 1, 5)]),
        "Veilleurs": ([("Furniture_Jungle_Torch", 4, 1), ("Potion_Purify", 1, 2)],
                      [("Potion_Health", 1, 3), ("Armor_Leather_Raven_Chest", 1, 5)]),
    },
}
# Stock de chaque échange par niveau de la boutique (renouvelé tous les 3 jours, comme le marchand vanilla).
SHOP_STOCK = {1: 8, 2: 6, 3: 3}
BARTER = RES / "BarterShops"
SHOP_PREFIX = "Nakasar_Peuples_W_"
ROMAN = {1: "I", 2: "II", 3: "III"}

TASKS = {
    "Gather": ("Dépose {count}/{needed} {item} au dépôt du village ({distance} blocs, {direction}).",
               "Drop {count}/{needed} {item} in the village deposit ({distance} blocks, {direction})."),
    "Craft": ("Fabrique et dépose {count}/{needed} {item} au dépôt ({distance} blocs, {direction}).",
              "Craft and drop {count}/{needed} {item} in the deposit ({distance} blocks, {direction})."),
    "Hunt": ("Abattus : {count}/{needed}. Ils rôdent à {distance} blocs, {direction}.",
             "Slain: {count}/{needed}. They prowl {distance} blocks away, {direction}."),
}

# Textes de la page du bâtiment (WorkshopPage) et des messages (Workshops), fr puis en.
PAGE = {
    "workshop.hamletKeeper": ("le tenancier du lieu-dit", "the hamlet keeper"),
    "workshop.title": ("{building} de {village}", "{building} of {village}"),
    "workshop.level.1": ("Niveau I · Ouvert", "Level I · Open"),
    "workshop.level.2": ("Niveau II · Établi", "Level II · Established"),
    "workshop.level.3": ("Niveau III · Renommé", "Level III · Renowned"),
    "workshop.levelShort.1": ("I", "I"),
    "workshop.levelShort.2": ("II", "II"),
    "workshop.levelShort.3": ("III", "III"),
    "workshop.keeper": ("{name} y travaille", "{name} works here"),
    "workshop.keeperAbsent": ("{name} revient à {hour} h", "{name} is back at {hour}:00"),
    "workshop.keeperNone": ("Personne n'y travaille encore", "Nobody works here yet"),
    "workshop.noSpecialty": ("Pas encore de spécialité (au niveau II)", "No specialty yet (at level II)"),
    "workshop.specialtyChoose": ("Choisir la spécialité", "Choose the specialty"),
    "workshop.specialtyChange": ("Spécialités", "Specialties"),
    "workshop.specialtyTitle": ("Spécialité : {building}", "Specialty: {building}"),
    "workshop.specialtyIntro": ("Une seule spécialité par bâtiment, choisie au niveau II pour tout le village. Elle change ses commandes, ses offres et ses bêtes.",
                                "One specialty per building, chosen at level II for the whole village. It changes its orders, offers and beasts."),
    "workshop.specialtyRule": ("Choisir ou changer demande le rang {rank}. Changer remet le savoir-faire du niveau à 0, une fois tous les {days} jours.",
                               "Choosing or changing needs rank {rank}. Changing resets the level's know-how to 0, once every {days} days."),
    "workshop.specialtyCurrent": ("Spécialité du bâtiment", "The building's specialty"),
    "workshop.specialtyPick": ("Choisir", "Choose"),
    "workshop.specialtyReconvert": ("Se reconvertir", "Convert"),
    "workshop.specialtyLevel": ("La spécialité se choisit au niveau II.", "The specialty is chosen at level II."),
    "workshop.specialtyRank": ("Il faut le rang {rank} pour choisir la spécialité.", "You need rank {rank} to choose the specialty."),
    "workshop.specialtyCooldown": ("Le bâtiment s'est reconverti récemment : encore {days} jour(s).",
                                   "The building converted recently: {days} more day(s)."),
    "workshop.specialtyChosen": ("{player} a choisi la spécialité {specialty} pour {building}.",
                                 "{player} chose the {specialty} specialty for {building}."),
    "workshop.specialtyConverted": ("{player} a reconverti {building} : {specialty}. Le savoir-faire du niveau repart de 0.",
                                    "{player} converted {building}: {specialty}. The level's know-how starts again from 0."),
    "workshop.specialtyWorks": ("Pas de changement de spécialité pendant les travaux.", "No specialty change during the works."),
    "workshop.specialtyUnknown": ("Spécialité inconnue : {id}", "Unknown specialty: {id}"),
    "workshop.beastsLine": ("Enclos : {count}/{max} bêtes. Une bête tuée revient au matin ; la tuer coûte {rep} de réputation.",
                            "Pen: {count}/{max} beasts. A slain beast comes back in the morning; killing one costs {rep} reputation."),
    "workshop.specialtyBack": ("Retour au bâtiment", "Back to the building"),
    "workshop.specialtyNone": ("Ce bâtiment n'a pas de spécialité.", "This building has no specialty."),
    "reputation.reason.livestock": ("une bête de l'enclos tuée", "a pen beast killed"),
    "workshop.knowledge": ("Savoir-faire", "Know-how"),
    "workshop.knowledgeValue": ("{value} / {max}", "{value} / {max}"),
    "workshop.knowledgeMax": ("Au plus haut", "At the top"),
    "workshop.knowledgeHint": ("Encore {left} de savoir-faire pour le niveau {level}.",
                               "{left} more know-how for level {level}."),
    "workshop.knowledgeFull": ("Jauge pleine : le niveau {level} viendra avec la commande de maître et son chantier.",
                               "Gauge full: level {level} comes with the master order and its works."),
    "workshop.knowledgeCapped": ("Jauge pleine : le niveau {level} attend que le village soit {tier}.",
                                 "Gauge full: level {level} waits for the village to be a {tier}."),
    "workshop.knowledgeTop": ("Le bâtiment est au niveau III : chaque commande sert encore le village.",
                              "The building is level III: each order still helps the village."),
    "workshop.orders": ("Commandes du jour", "Today's orders"),
    "workshop.renew": ("Nouvelles commandes à {hour} h", "New orders at {hour}:00"),
    "workshop.reward": ("Récompense", "Reward"),
    "workshop.knowledgePill": ("+{knowledge} savoir-faire", "+{knowledge} know-how"),
    "workshop.locked": ("Commandes ouvertes au rang {rank}.", "Orders open at rank {rank}."),
    "workshop.empty": ("Aucune commande aujourd'hui.", "No orders today."),
    "workshop.next": ("Prochain niveau", "Next level"),
    "workshop.nextLine": ("Niveau {level} : {need} de savoir-faire, une commande de maître, puis un chantier de 12 h.",
                          "Level {level}: {need} know-how, a master order, then 12 hours of works."),
    "workshop.nextTier": ("Le niveau {level} demande un village au palier {tier}.",
                          "Level {level} needs a village of tier {tier}."),
    "workshop.nextNone": ("Niveau le plus haut atteint.", "Highest level reached."),
    "workshop.offers": ("Offres", "Offers"),
    "workshop.offersOpen": ("{name} troque la production du bâtiment contre des faveurs : ton rang t'ouvre le niveau {level} "
                            "(bâtiment au niveau {max}).",
                            "{name} trades the building's goods for favours: your rank opens level {level} "
                            "(building at level {max})."),
    "workshop.offersRank": ("{name} ne troque qu'à partir du rang {rank}.", "{name} only trades from rank {rank}."),
    "workshop.offersAbsent": ("{name} n'est pas là : la boutique rouvre à {hour} h.",
                              "{name} is away: the shop reopens at {hour}:00."),
    "workshop.offersRule": ("Toléré : niveau I. Ami : niveau II. Hôte : niveau III. Jamais plus que le niveau du bâtiment ; "
                            "le stock revient tous les 3 jours.",
                            "Tolerated: level I. Friend: level II. Host: level III. Never above the building's level; "
                            "stock returns every 3 days."),
    "workshop.offersNoSpecialty": ("Sans spécialité, la boutique reste au niveau I.",
                                   "Without a specialty, the shop stays at level I."),
    "workshop.shopButton": ("Boutique (niveau {level})", "Shop (level {level})"),
    "workshop.shopAbsent": ("Le villageois de ce bâtiment n'est pas là : la boutique rouvre à {hour} h.",
                            "This building's villager is away: the shop reopens at {hour}:00."),
    "workshop.shopRank": ("Cette boutique ouvre au rang {rank}.", "This shop opens at rank {rank}."),
    "workshop.shareLine": ("Part de l'Hôte : chaque matin, {quantity} × {item} attendent chaque {rank} dans la caisse.",
                           "Host's share: every morning, {quantity} × {item} wait in the crate for each {rank}."),
    "workshop.shareButton": ("Prendre la Part de l'Hôte", "Take the Host's share"),
    "workshop.shareLevel": ("La Part de l'Hôte ouvre au niveau III, avec une spécialité.",
                            "The Host's share opens at level III, with a specialty."),
    "workshop.shareRank": ("La Part de l'Hôte est réservée au rang {rank}.", "The Host's share is for rank {rank}."),
    "workshop.shareTaken": ("Tu as déjà pris ta Part de l'Hôte : la caisse se remplit à {hour} h.",
                            "You already took your Host's share: the crate refills at {hour}:00."),
    "workshop.shareGiven": ("Part de l'Hôte : {quantity} × {item}.", "Host's share: {quantity} × {item}."),
    "workshop.limit": ("Tu suis déjà {count} demandes ou commandes : rends-en une avant d'en prendre une autre.",
                       "You already follow {count} requests or orders: finish one before taking another."),
    "workshop.knowledgeGained": ("{building} : +{knowledge} de savoir-faire ({value}/{max}).",
                                 "{building}: +{knowledge} know-how ({value}/{max})."),
    "workshop.knowledgeReady": ("{building} a tout le savoir-faire du niveau {level}.",
                                "{building} has all the know-how for level {level}."),
    "workshop.boardOrphan": ("Ce panneau n'appartient plus à aucun bâtiment.", "This sign no longer belongs to a building."),
    "workshop.notHere": ("Ce bâtiment n'est pas encore debout.", "This building is not standing yet."),
    "workshop.unknown": ("Bâtiment de métier inconnu : {id}", "Unknown workshop: {id}"),
    "workshop.list": ("Bâtiments de métier de {village} : {list}", "Workshops of {village}: {list}"),
    "workshop.listEntry": ("{id} ({name}, niveau {level}, {value}/{max})", "{id} ({name}, level {level}, {value}/{max})"),
    "workshop.listNone": ("{village} n'a pas encore de bâtiment de métier debout.",
                          "{village} has no standing workshop yet."),
    "workshop.text.header": ("{name}, niveau {level}", "{name}, level {level}"),
    "workshop.text.knowledge": ("Savoir-faire : {value}/{max}", "Know-how: {value}/{max}"),
    "workshop.text.order": ("{n}. [{type}] {title} : {state}", "{n}. [{type}] {title}: {state}"),
    "workshop.text.available": ("à prendre", "available"),
    "workshop.text.taken": ("prise", "taken"),
    "workshop.text.done": ("remplie", "done"),
    "workshop.text.locked": ("fermée", "locked"),
    "workshop.text.how": ("Prends une commande au panneau, debout, ou par /village atelier {id}.",
                          "Take an order at the sign, standing, or with /village atelier {id}."),
    "command.workshop.desc": ("Bâtiments de métier du village le plus proche, ou la page de l'un d'eux",
                              "Workshops of the nearest village, or the page of one of them"),
    "command.workshop.arg": ("Id du bâtiment de métier (Kweebec_Enclos...)", "Workshop id (Kweebec_Enclos...)"),
    "command.knowledge.desc": ("Ajoute du savoir-faire à un bâtiment de métier du village le plus proche",
                               "Adds know-how to a workshop of the nearest village"),
    "command.knowledge.arg": ("Quantité de savoir-faire", "Amount of know-how"),
    "command.workshopLevel.desc": ("Met un bâtiment de métier du village le plus proche au niveau voulu (test : savoir-faire à 0, spécialité gardée dès le niveau II, reconversion libre)",
                                   "Sets a workshop of the nearest village to the given level (test: know-how at 0, specialty kept from level II, free conversion)"),
    "command.workshopLevel.arg": ("Niveau (1 à 3)", "Level (1 to 3)"),
    "workshop.nextMaster": ("Jauge pleine : remplis la commande de maître « {title} » pour ouvrir le chantier.",
                            "Gauge full: fill the master order \"{title}\" to open the works."),
    "workshop.nextMaterials": ("Commande de maître remplie : réunis ces matériaux au dépôt, puis lance {hours} h de travaux.",
                               "Master order done: gather these materials in the deposit, then start {hours} hours of works."),
    "workshop.works": ("Travaux en cours : encore {hours} h.", "Works under way: {hours} more hours."),
    "workshop.takeMaster": ("Commande de maître", "Master order"),
    "workshop.startUpgrade": ("Lancer le chantier", "Start the works"),
    # Kevin (2026-11-15) : pendant les travaux, le bouton reste à sa place, grisé, avec le temps restant.
    "workshop.busy": ("Chantier en cours · {hours} h", "Works underway · {hours} h"),
    "workshop.masterNotYet": ("La commande de maître s'ouvre quand la jauge est pleine et que le village a le palier voulu.",
                              "The master order opens once the gauge is full and the village has the tier needed."),
    "workshop.masterMissing": ("Ce bâtiment n'a pas de commande de maître pour ce niveau.", "This building has no master order for this level."),
    "workshop.masterDone": ("{player} a rempli la commande de maître de {building} : le chantier peut commencer.",
                            "{player} filled the master order of {building}: the works can begin."),
    "workshop.upgradeNotYet": ("Le chantier attend la jauge pleine et la commande de maître.",
                               "The works wait for a full gauge and the master order."),
    "workshop.upgradeMissing": ("Il manque au dépôt : {list}.", "Missing from the deposit: {list}."),
    "workshop.materialLine": ("{count} × {item}", "{count} × {item}"),
    "workshop.upgradeStarted": ("Le chantier de {building} commence : niveau {level} dans {hours} h.",
                                "Works on {building} begin: level {level} in {hours} hours."),
    "workshop.levelUp": ("{building} passe au {level} !", "{building} reaches {level}!"),
    "workshop.levelUpTitle": ("{building} : {level}", "{building}: {level}"),
    "workshop.taken": ("Commande prise : {title} ({building}).", "Order taken: {title} ({building})."),
    "workshop.specialtyTwin": ("Déjà la spécialité de {building} : un autre élevage doit en prendre une autre.",
                               "Already the specialty of {building}: another pen must pick another one."),
    # Étape 6 : emplacements libres E1 et E2 (village/Plots, page PlotPage).
    "plot.button": ("Emplacements", "Free plots"),
    "plot.none": ("Ce village n'a pas d'emplacement libre.", "This village has no free plot."),
    "plot.locked": ("Ce terrain s'ouvre au palier {tier}.", "This plot opens at tier {tier}."),
    "plot.rank": ("Il faut le rang {rank} pour décider de ce terrain.", "You need rank {rank} to decide about this plot."),
    "plot.busy": ("Le terrain a déjà un chantier ou un bâtiment.", "The plot already has works or a building."),
    "plot.taken": ("Ce projet est déjà sur l'autre terrain.", "This project is already on the other plot."),
    "plot.chosen": ("{player} choisit {building} pour le terrain {plot}.", "{player} picks {building} for plot {plot}."),
    "plot.noProject": ("Choisissez d'abord un projet pour ce terrain.", "Pick a project for this plot first."),
    "plot.missing": ("Il manque au dépôt du village : {list}.", "The village deposit still lacks: {list}."),
    "plot.started": ("{player} lance le chantier : {building}, {hours} h de travaux.", "{player} starts the works: {building}, {hours} h of work."),
    "plot.nothing": ("Rien à démolir sur ce terrain.", "Nothing to demolish on this plot."),
    "plot.cooldown": ("Une démolition par semaine : encore {days} jour(s).", "One demolition per week: {days} more day(s)."),
    "plot.demolished": ("{player} fait démolir {building} (terrain {plot}). Un quart des matériaux revient au dépôt.",
                        "{player} has {building} torn down (plot {plot}). A quarter of the materials goes back to the deposit."),
    "plot.done": ("{building} est bâti à {village} !", "{building} is built in {village}!"),
    "plot.doneTitle": ("{building} bâti", "{building} built"),
    "plot.hurried": ("Les chantiers d'emplacement finissent au prochain pas du village.", "The plot works finish at the village's next step."),
    "plot.material": ("{count} × {item}", "{count} × {item}"),
    "plot.page.orphan": ("Ce village n'existe plus.", "This village no longer exists."),
    "plot.page.title": ("Emplacements de {village}", "Free plots of {village}"),
    "plot.page.intro": ("Deux terrains réservés pour les bâtiments que le village choisit. Choisissez un projet, réunissez ses matériaux au dépôt, puis lancez le chantier.",
                        "Two plots kept for the buildings the village chooses. Pick a project, gather its materials in the deposit, then start the works."),
    "plot.page.plot": ("Terrain {plot}", "Plot {plot}"),
    "plot.page.select": ("Voir les projets", "See projects"),
    "plot.page.selected": ("Projets affichés", "Projects shown"),
    "plot.page.start": ("Lancer le chantier", "Start the works"),
    "plot.page.busy": ("Chantier en cours · {hours} h", "Works underway · {hours} h"),
    "plot.page.demolish": ("Démolir", "Demolish"),
    "plot.page.catalog": ("Projets pour le terrain {plot}", "Projects for plot {plot}"),
    "plot.page.choose": ("Choisir", "Choose"),
    "plot.page.switch": ("Choisir à la place", "Choose instead"),
    "plot.page.clear": ("Renoncer", "Give up"),
    "plot.page.taken": ("Déjà sur l'autre terrain.", "Already on the other plot."),
    "plot.page.projectLine": ("{job} · {specialties}", "{job} · {specialties}"),
    "plot.page.rule": ("Choisir, lancer ou démolir demande le rang {rank}. Démolir rend un quart des matériaux, une fois tous les {days} jours par terrain.",
                       "Choosing, starting or demolishing needs rank {rank}. Demolishing gives back a quarter of the materials, once every {days} days per plot."),
    "plot.page.back": ("Retour au panneau", "Back to the board"),
    "plot.state.locked": ("Fermé : s'ouvre au palier {tier}.", "Closed: opens at tier {tier}."),
    "plot.state.free": ("Libre : choisissez un projet.", "Free: pick a project."),
    "plot.state.freeCooldown": ("Libre : choisissez un projet. Prochaine démolition possible dans {days} jour(s).",
                                "Free: pick a project. Next demolition possible in {days} day(s)."),
    "plot.state.chosen": ("Projet : {building}. Matériaux : {list}. Il manque : {missing}.",
                          "Project: {building}. Materials: {list}. Still missing: {missing}."),
    "plot.state.chosenNoDeposit": ("Projet : {building}. Matériaux : {list}.", "Project: {building}. Materials: {list}."),
    "plot.state.ready": ("Projet : {building}. Matériaux réunis ({list}) : prêt pour {hours} h de travaux.",
                         "Project: {building}. Materials gathered ({list}): ready for {hours} h of work."),
    "plot.state.working": ("Chantier : {building}, encore {hours} h.", "Works: {building}, {hours} h left."),
    "plot.state.built": ("{building}, niveau {level}.", "{building}, level {level}."),
    "plot.state.demolishIn": ("Démolition possible dans {days} jour(s).", "Can be demolished in {days} day(s)."),
}


def load_ids(path, prefix=None):
    out = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if prefix is None:
            out.add(line)
        else:
            parts = line.split()
            if len(parts) >= 2 and parts[0] == prefix:
                out.add(parts[1])
    return out


def rect(b):
    return (b["X"] + b["MinX"], b["X"] + b["MaxX"], b["Z"] + b["MinZ"], b["Z"] + b["MaxZ"])


def inside(x, z, r, margin=0):
    return r[0] - margin <= x <= r[1] + margin and r[2] - margin <= z <= r[3] + margin


def board_spot(layout, building, errors):
    """Place [x, z, lacet] du panneau : un bloc hors de l'emprise, face tournée vers la place, décalé de côté."""
    by_id = {b["Id"]: b for b in layout["Buildings"]}
    r = rect(building)
    cx, cz = (r[0] + r[1]) // 2, (r[2] + r[3]) // 2
    plaza = layout["PlazaRadius"]
    taken = set()
    for j in layout["Jobs"]:
        taken.add((j["WorkX"], j["WorkZ"]))
        taken.add((j["HomeX"], j["HomeZ"]))
    heart = layout.get("Heart") or {}
    for key in ("Board", "Deposit", "DepositWide", "Banner"):
        if key in heart:
            taken.add((heart[key][0], heart[key][2]))
    # Lacets (VillageHeart) : 0 face au sud (+Z), 1 à l'est, 2 au nord, 3 à l'ouest.
    shifts = (3, -3, 4, -4, 2, -2, 5, -5)
    faces = {  # face -> (cases, lacet)
        "w": ([(r[0] - 1, cz + d) for d in shifts], 3),
        "e": ([(r[1] + 1, cz + d) for d in shifts], 1),
        "n": ([(cx + d, r[2] - 1) for d in shifts], 2),
        "s": ([(cx + d, r[3] + 1) for d in shifts], 0),
    }
    if abs(cx) >= abs(cz):
        order = ["w", "n", "s", "e"] if cx > 0 else ["e", "n", "s", "w"]
    else:
        order = ["n", "w", "e", "s"] if cz > 0 else ["s", "w", "e", "n"]
    # D'abord la face tournée vers la place, puis les côtés, la face arrière en dernier.
    candidates = [(x, z, faces[f][1]) for f in order for x, z in faces[f][0]]
    for x, z, yaw in candidates:
        if not inside(x, z, r, 1):
            continue
        # Les autres projets du même terrain (étape 6) ne sont jamais bâtis en même temps que lui.
        if any(inside(x, z, rect(o), 0) for oid, o in by_id.items()
               if oid != building["Id"] and not (building.get("Plot") and o.get("Plot") == building.get("Plot"))):
            continue
        if abs(x) <= plaza + 1 and abs(z) <= plaza + 1:
            continue
        if any(abs(x - tx) <= 1 and abs(z - tz) <= 1 for tx, tz in taken):
            continue
        return [x, z, yaw]
    errors.append(f"{layout['People']}/{building['Id']} : pas de place libre pour le panneau")
    return None


def upgrades(layout, wid, errors):
    """Chantiers d'amélioration vers les niveaux II et III (matériaux pris au dépôt du village)."""
    out = []
    for level in (2, 3):
        chantier = next((c for c in layout.get("Chantiers", []) if c["Tier"] == level), None)
        if chantier is None:
            errors.append(f"{wid} : le plan n'a pas de chantier du palier {level} pour le niveau {level}")
            continue
        materials = [{"ItemId": m["ItemId"], "Quantity": max(1, (m["Quantity"] + 1) // 2)} for m in chantier["Materials"][:3]]
        out.append({"Level": level, "Hours": UPGRADE_HOURS, "Materials": materials, "Decor": DECOR[layout["People"]][level]})
    return out


def write_shop(sid, people, trades, title_key, comment, items, errors):
    for item, qty, price in [t[:3] for t in trades]:
        if item not in items:
            errors.append(f"{sid} : objet vanilla inconnu {item}")
    doc = {
        "$Comment": comment,
        "DisplayNameKey": title_key,
        "RefreshInterval": {"Days": 3},
        "RestockHour": 6,
        "TradeSlots": [{"Type": "Fixed", "Trade": {
            "Output": {"ItemId": item, "Quantity": qty},
            "Input": [{"ItemId": f"Nakasar_Peuples_Favor_{people}", "Quantity": price}],
            "Stock": stock}} for item, qty, price, stock in trades],
    }
    (BARTER / f"{sid}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


LAYOUT_PEOPLE = {"Kweebec_Oak": "Kweebec", "Trork_Camp": "Trork", "Feran_Oasis": "Feran", "Renonce_Givre": "Renonce",
                 "Slothian_Monastere": "Slothian"}


def plot_workshops(fr, en, errors):
    """Étape 6 : un bâtiment de métier par projet et par terrain (tools/plots.py), ajouté aux tables du script.

    Id <Peuple>_<E1|E2>_<Projet>, bâtiment du plan E1_<Projet>, métier <Métier>_E1. Un deuxième élevage (« twin »)
    reprend les commandes, les bêtes, les spécialités et les boutiques de l'enclos de base. Renvoie {id: enclos de base}.
    """
    twins = {}
    by_id = {w[0]: w for w in WORKSHOPS}
    for layout_id, projects in plots.PROJECTS.items():
        people = LAYOUT_PEOPLE[layout_id]
        for pid in sorted(plots.PLOTS[layout_id]):
            for project in projects:
                wid = f"{people}_{pid}_{project['id']}"
                bid = plots.building_id(pid, project["id"])
                jid = plots.job_id(pid, project["job"])
                fr[f"building.{bid}"], en[f"building.{bid}"] = project["fr"], project["en"]
                fr[f"job.{jid}"], en[f"job.{jid}"] = project["job_fr"], project["job_en"]
                twin = project.get("twin")
                if twin:
                    base = by_id.get(twin)
                    if base is None or twin not in SPECIALTIES or twin not in SHOPS:
                        errors.append(f"{wid} : enclos de base inconnu {twin}")
                        continue
                    WORKSHOPS.append((wid, layout_id, bid, jid, project["icon"], project["fr"], project["en"], base[7]))
                    SPECIALTIES[wid] = SPECIALTIES[twin]
                    SHOPS[wid] = SHOPS[twin]
                    twins[wid] = twin
                    continue
                WORKSHOPS.append((wid, layout_id, bid, jid, project["icon"], project["fr"], project["en"], project["orders"]))
                SPECIALTIES[wid] = ([], [(sid, sfr, sen, icon, lfr, len_, []) for sid, sfr, sen, icon, lfr, len_, *_ in project["specs"]])
                SHOPS[wid] = {"Base": project["base"], **{sp[0]: (sp[6], sp[7]) for sp in project["specs"]}}
                for sp in project["specs"]:
                    if sp[8]:
                        RAID[(wid, sp[0])] = sp[8]
    return twins

# Avant-postes de métier (Kevin, 2026-11-15, tools/outposts.py) : un bâtiment de métier <Peuple>_AP_<Type> par peuple et
# par type, sans plan (champ « Annex ») : commandes dans Requests/<Peuple>/AP_<Type>, mêmes niveaux, spécialités,
# boutiques et Part de l'Hôte que les autres. Rempli par annex_tables avant selling_rules.
ANNEXES = []
# Repère de l'avant-poste : le bâtiment principal à 3 blocs au nord de la fondation, les annexes à 2 blocs de côté.
ANNEX_FRONT_GAP = 3
ANNEX_SIDE_GAP = 2
ANNEX_UPGRADE = {2: (1, 2), 3: (3, 4)}   # matériaux de l'amélioration = fondation × num / den


def load_bounds():
    out = {}
    for line in PREFAB_BOUNDS.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 7 and not line.startswith("#"):
            try:
                out[parts[0]] = tuple(int(v) for v in parts[1:])
            except ValueError:
                pass
    return out


def annex_tables(errors):
    """Commandes, spécialités et boutiques des avant-postes, ajoutées aux tables du script (avant selling_rules)."""
    for people in PEOPLES:
        sub = outposts.MAT[people]
        for t in outposts.types(people):
            data = outposts.TYPE_DATA[t]
            wid = f"{people}_AP_{t}"
            orders = [(suffix, rtype, what.format(**sub), q, tf, te) for suffix, rtype, what, q, tf, te in data["orders"]]
            orders.append(("Hunt", "Hunt", list(outposts.HUNTS[people][t]), 0) + outposts.HUNT_TITLES[t])
            fmt = lambda trades: [(item.format(**sub), q, price) for item, q, price in trades]
            SHOPS[wid] = {"Base": fmt(data["base"])}
            choices = []
            for sid, sfr, sen, icon, lfr, len_, two, three, raid in data["specs"]:
                SHOPS[wid][sid] = (fmt(two), fmt(three))
                choices.append((sid, sfr, sen, icon, lfr, len_, []))
                if raid and people not in outposts.NO_RAID:
                    RAID[(wid, sid)] = raid
            SPECIALTIES[wid] = ([], choices)
            ANNEXES.append((wid, people, t, orders))


def annex_layout(people, t, bounds, errors):
    """Prefabs (« chemin x z rot »), emprise locale [x0, x1, z0, z1] et hauteur de l'avant-poste."""
    lines, boxes, top = [], [], 0
    main = None
    for path, side in outposts.PREFABS[people][t]:
        b = bounds.get(path)
        if b is None:
            errors.append(f"{people}_AP_{t} : prefab vanilla inconnu ou non mesuré {path}")
            return [], [-4, 4, -12, -2], 8
        x0, x1, _y0, y1, z0, z1 = b
        if main is None:
            px, pz = -((x0 + x1) // 2), -ANNEX_FRONT_GAP - z1
            main = (px + x0, px + x1, pz + z0, pz + z1)
        else:
            mid = (main[2] + main[3]) // 2
            pz = min(mid - (z0 + z1) // 2, main[3] - z1)
            px = main[0] - ANNEX_SIDE_GAP - x1 if side == "W" else main[1] + ANNEX_SIDE_GAP - x0
        box = (px + x0, px + x1, pz + z0, pz + z1)
        for other in boxes:
            if not (box[1] < other[0] or other[1] < box[0] or box[3] < other[2] or other[3] < box[2]):
                errors.append(f"{people}_AP_{t} : {path} chevauche un autre prefab")
        boxes.append(box)
        lines.append(f"{path} {px} {pz} 0")
        top = max(top, y1 + 1)
    rect = [min(b[0] for b in boxes) - 1, max(b[1] for b in boxes) + 1, min(b[2] for b in boxes) - 1,
            max(-ANNEX_FRONT_GAP + 1, max(b[3] for b in boxes) + 1)]
    if rect[3] >= 0:
        errors.append(f"{people}_AP_{t} : l'emprise {rect} touche la fondation")
    return lines, rect, top


def annex_workers(people, t, roles, errors):
    out = []
    for i, (kind, tier) in enumerate(zip(outposts.WORKERS[people][t], outposts.WORKER_TIERS)):
        x = (-2, 2, -4, 4)[i]
        if kind.startswith("@"):
            role, dialogue = kind[1:], ""
            if role not in roles:
                errors.append(f"{people}_AP_{t} : rôle vanilla inconnu {role}")
        else:
            role = f"Nakasar_Peuples_{people}_{kind}"
            dialogue = f"{people}_{outposts.DIALOGUE_ALIAS.get(kind, kind)}"
            if not (RES / "NPC/Roles/Nakasar/Peuples" / f"{role}.json").exists():
                errors.append(f"{people}_AP_{t} : rôle du mod absent {role}")
            if not (DIALOGUES / people / f"{dialogue}.json").exists() and not (DIALOGUES / f"{dialogue}.json").exists():
                errors.append(f"{people}_AP_{t} : dialogue absent {dialogue}")
        out.append({"Id": f"AP_{t}_{i + 1}", "Tier": tier, "Role": role, "Dialogue": dialogue, "Building": "",
                    "WorkX": x, "WorkZ": -1, "Home": "", "HomeX": x, "HomeZ": -2, "Builder": False})
    return out


def write_beacon(items, fr, en, errors):
    """Balises de route (Java annex/Routes) : un objet par modèle vanilla, fabriqués à l'établi, tous la même balise."""
    b = outposts.BEACON
    for i in [i for i, _ in b["recipe"]]:
        if i not in items:
            errors.append(f"{b['item']} : objet vanilla inconnu {i}")
    for suffix, parent, name_fr, name_en in b["variants"]:
        item = outposts.beacon_id(suffix)
        if parent not in items:
            errors.append(f"{item} : objet vanilla inconnu {parent}")
        if parent not in b["parent_gathering"]:
            errors.append(f"{item} : récolte du parent {parent} inconnue (outposts.BEACON['parent_gathering'])")
            continue
        gathering = {kind: dict(drop, ItemId=item) for kind, drop in b["parent_gathering"][parent].items()}
        doc = {
            "$Comment": f"Balise de route ({name_fr}, modèle vanilla {parent}) : les convois et les voyageurs vont de "
                        "balise en balise, toutes variantes confondues (Java annex/Routes, RouteBeaconSystems). "
                        "Générée par tools/generate_workshops.py.",
            "Parent": parent,
            "TranslationProperties": {"Name": f"nakasar_peuples.items.{item}.name",
                                      "Description": f"nakasar_peuples.items.{item}.description"},
            "Quality": "Uncommon",
            "BlockType": {"Gathering": gathering},
            "Recipe": {
                "TimeSeconds": 2,
                "KnowledgeRequired": False,
                "Input": [{"ItemId": i, "Quantity": q} for i, q in b["recipe"]],
                "BenchRequirement": [{"Type": "Crafting", "Id": "Workbench", "Categories": ["Workbench_Crafting"],
                                      "RequiredTierLevel": 1}],
                "OutputQuantity": b["output"],
            },
        }
        (ANNEX_ITEMS / f"{item}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        fr[f"items.{item}.name"] = f"{b['name'][0]} ({name_fr})"
        en[f"items.{item}.name"] = f"{b['name'][1]} ({name_en})"
        fr[f"items.{item}.description"], en[f"items.{item}.description"] = b["description"]


def write_annexes(items, roles, fr, en, errors):
    """Écrit les bâtiments de métier des avant-postes, leurs commandes et les objets de fondation."""
    bounds = load_bounds()
    for t in outposts.ALL_TYPES:
        name_fr, name_en, role_fr, role_en, job_fr, job_en, icon = outposts.NAMES[t]
        item = outposts.ITEM_PREFIX + t
        doc = {
            "$Comment": f"Fondation d'avant-poste « {name_fr} », remise au panneau d'un village de palier 3 et posée là où "
                        "l'on veut bâtir (Java annex/AnnexPlaceSystem). Générée par tools/generate_workshops.py.",
            "Parent": "Furniture_Construction_Sign",
            "TranslationProperties": {"Name": f"nakasar_peuples.items.{item}.name",
                                      "Description": f"nakasar_peuples.items.{item}.description"},
            "Quality": "Uncommon",
        }
        (ANNEX_ITEMS / f"{item}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        fr[f"items.{item}.name"], en[f"items.{item}.name"] = f"Fondation : {name_fr}", f"Foundation: {name_en}"
        fr[f"items.{item}.description"] = f"À poser là où vous voulez bâtir l'avant-poste ({role_fr[0].lower()}{role_fr[1:]})"
        en[f"items.{item}.description"] = f"Place it where you want to build the outpost ({role_en[0].lower()}{role_en[1:]})"
        fr[f"annex.role.{t}"], en[f"annex.role.{t}"] = role_fr, role_en
        for i in range(len(outposts.WORKER_TIERS)):
            fr[f"job.AP_{t}_{i + 1}"], en[f"job.AP_{t}_{i + 1}"] = job_fr, job_en
    write_beacon(items, fr, en, errors)
    for key, (f, e) in outposts.LANG.items():
        fr[key], en[key] = f, e
    for wid, people, t, orders in ANNEXES:
        name_fr, name_en, _rf, _re, _jf, _je, icon = outposts.NAMES[t]
        if icon not in items:
            errors.append(f"{wid} : icône vanilla inconnue {icon}")
        prefabs, local, height = annex_layout(people, t, bounds, errors)
        materials = [{"ItemId": i, "Quantity": q} for i, q in outposts.FOUNDATION[people]]
        for m in materials:
            if m["ItemId"] not in items:
                errors.append(f"{wid} : matériau vanilla inconnu {m['ItemId']}")
        upgrades = [{"Level": level, "Hours": UPGRADE_HOURS, "Decor": DECOR[people][level],
                     "Materials": [{"ItemId": i, "Quantity": max(1, q * num // den)} for i, q in outposts.FOUNDATION[people]]}
                    for level, (num, den) in ANNEX_UPGRADE.items()]
        annex = {"Type": t, "Item": outposts.ITEM_PREFIX + t, "Rule": outposts.RULES[t], "Prefabs": prefabs, "Rect": local,
                 "Height": height, "Workers": annex_workers(people, t, roles, errors), "Materials": materials, "Hours": 24,
                 "Decor": ["2 0 -1 0 " + DECOR[people][2][0].split()[-1]]}
        delivery = outposts.TYPE_DATA[t]["delivery"]
        if delivery:
            lot = delivery[0].format(**outposts.MAT[people])
            if lot not in items:
                errors.append(f"{wid} : livraison vanilla inconnue {lot}")
            annex["Delivery"] = {"ItemId": lot, "Quantity": delivery[1]}
            extra = []
            for item, q in outposts.TYPE_DATA[t].get("extra", []):
                item = item.format(**outposts.MAT[people])
                if item not in items:
                    errors.append(f"{wid} : livraison vanilla inconnue {item}")
                extra.append({"ItemId": item, "Quantity": q})
            if extra:
                annex["Extra"] = extra
        if t == "Tour" and people not in outposts.NO_RAID:
            annex["Warn"] = outposts.TOWER_WARN
        doc = {
            "$Comment": "Avant-poste de métier généré par tools/generate_workshops.py depuis tools/outposts.py (ne pas "
                        "modifier à la main) : voir dev.nakasar.hytale.peuples.workshop.Workshop et annex/Annexes.",
            "People": people,
            "Icon": icon,
            "NameKey": f"nakasar_peuples.workshop.{wid}.name",
            "Board": [0, 0, 0],
            "Upgrades": upgrades,
            "Annex": annex,
        }
        specialties(doc, wid, people, name_fr, name_en, items, roles, fr, en, errors)
        (OUT / f"{wid}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        fr[f"workshop.{wid}.name"], en[f"workshop.{wid}.name"] = name_fr, name_en
        write_orders(wid, people, REQUESTS / people / f"AP_{t}", orders, items, roles, fr, en, errors)
        print(f"{wid} : {len(orders)} commandes + 2 de maître, emprise {local}, hauteur {height}")


HAMLET_OWN = []


def hamlet_tables(errors):
    """Paliers propres des lieux-dits sans avant-poste équivalent (hamlets.OWN_TIERS), comme annex_tables."""
    import hamlets
    for people in PEOPLES:
        sub = outposts.MAT[people]
        for kind in hamlets.BUILDINGS[people]:
            data = hamlets.OWN_TIERS.get(kind)
            if data is None:
                continue
            wid = f"{people}_LD_{kind}"
            orders = [(suffix, rtype, what.format(**sub), q, tf, te) for suffix, rtype, what, q, tf, te in data["orders"]]
            orders.append(("Hunt", "Hunt", list(outposts.HUNTS[people][data["hunt_from"]]), 0) + data["hunt_titles"])
            fmt = lambda trades: [(item.format(**sub), q, price) for item, q, price in trades]
            SHOPS[wid] = {"Base": fmt(data["base"])}
            choices = []
            for sid, sfr, sen, icon, lfr, len_, two, three, _raid in data["specs"]:
                SHOPS[wid][sid] = (fmt(two), fmt(three))
                choices.append((sid, sfr, sen, icon, lfr, len_, []))
            SPECIALTIES[wid] = ([], choices)
            HAMLET_OWN.append((wid, people, kind, orders))


def write_hamlet_workshops(items, roles, fr, en, errors):
    """Bâtiments de métier des lieux-dits (<Peuple>_LD_<Genre>) : copies des paliers de l'avant-poste équivalent."""
    import hamlets
    by_wid = {wid: (people, t, orders) for wid, people, t, orders in ANNEXES}
    own = {wid: orders for wid, _p, _k, orders in HAMLET_OWN}
    for people in PEOPLES:
        for kind in hamlets.BUILDINGS[people]:
            wid = f"{people}_LD_{kind}"
            if wid in own:
                name_fr, name_en, icon = hamlets.NAMES[kind][:3]
                upgrades = [{"Level": level, "Hours": UPGRADE_HOURS, "Decor": DECOR[people][level],
                             "Materials": [{"ItemId": i, "Quantity": max(1, q * num // den)} for i, q in outposts.FOUNDATION[people]]}
                            for level, (num, den) in ANNEX_UPGRADE.items()]
                doc = {
                    "$Comment": f"Bâtiment de métier du lieu-dit « {name_fr} » (world/Hamlets), paliers propres de "
                                "tools/hamlets.py OWN_TIERS : généré par tools/generate_workshops.py (ne pas modifier à la main).",
                    "People": people, "Icon": icon, "NameKey": f"nakasar_peuples.workshop.{wid}.name", "Board": [0, 0, 0],
                    "Upgrades": upgrades, "Hamlet": kind,
                }
                specialties(doc, wid, people, name_fr, name_en, items, roles, fr, en, errors)
                (OUT / f"{wid}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                fr[f"workshop.{wid}.name"], en[f"workshop.{wid}.name"] = name_fr, name_en
                write_orders(wid, people, REQUESTS / people / f"LD_{kind}", own[wid], items, roles, fr, en, errors)
                print(f"{wid} : paliers propres, {len(own[wid])} commandes + 2 de maître")
                continue
            ap = f"{people}_AP_{hamlets.WORKSHOP_EQUIV[kind]}"
            if ap not in by_wid:
                errors.append(f"lieu-dit {people} {kind} : avant-poste équivalent absent {ap}")
                continue
            _p, _t, orders = by_wid[ap]
            wid = f"{people}_LD_{kind}"
            name_fr, name_en, icon = hamlets.NAMES[kind][:3]
            if icon not in items:
                errors.append(f"{wid} : icône vanilla inconnue {icon}")
            src = json.loads((OUT / f"{ap}.json").read_text(encoding="utf-8"))
            SHOPS[wid] = SHOPS[ap]
            SPECIALTIES[wid] = SPECIALTIES[ap]
            doc = {
                "$Comment": f"Bâtiment de métier du lieu-dit « {name_fr} » (world/Hamlets), aux paliers de l'avant-poste {ap} : "
                            "généré par tools/generate_workshops.py (ne pas modifier à la main).",
                "People": people,
                "Icon": icon,
                "NameKey": f"nakasar_peuples.workshop.{wid}.name",
                "Board": [0, 0, 0],
                "Upgrades": src["Upgrades"],
                "Hamlet": kind,
            }
            specialties(doc, wid, people, name_fr, name_en, items, roles, fr, en, errors)
            (OUT / f"{wid}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            fr[f"workshop.{wid}.name"], en[f"workshop.{wid}.name"] = name_fr, name_en
            write_orders(wid, people, REQUESTS / people / f"LD_{kind}", orders, items, roles, fr, en, errors)
            print(f"{wid} : paliers de {ap}, {len(orders)} commandes + 2 de maître")


# Kevin (2026-11-15) : une commande ne demande jamais un objet vendu en boutique, celle du bâtiment ou celle du
# village ; une demande du tableau jamais un objet de la boutique du village. Contrôlé ici (selling_rules) : on corrige
# les données (objet demandé ou boutique), le script ne filtre rien.
ASKED_TYPES = ("Gather", "Craft", "Harvest")
PEOPLES = ("Kweebec", "Trork", "Feran", "Renonce", "Slothian")


def shop_items(path):
    doc = json.loads(path.read_text(encoding="utf-8"))
    out = set()
    for slot in doc.get("TradeSlots", []):
        for t in [slot["Trade"]] if "Trade" in slot else slot.get("Trades", []):
            out.add(t["Output"]["ItemId"])
    return out


def selling_rules(errors):
    """Règle de Kevin : erreur si une demande du tableau ou une commande vise un objet vendu en boutique."""
    village_sold = {p: set() for p in PEOPLES}
    for path in BARTER.glob("Nakasar_Peuples_*.json"):
        if path.name.startswith(SHOP_PREFIX):
            continue
        for p in PEOPLES:
            if path.stem.startswith(f"Nakasar_Peuples_{p}_"):
                village_sold[p] |= shop_items(path)
    asked = {p: set() for p in PEOPLES}
    workshop_folders = {(w[1], w[2]) for w in WORKSHOPS}
    for path in REQUESTS.glob("*/*.json"):
        doc = json.loads(path.read_text(encoding="utf-8"))
        if doc.get("Type") in ASKED_TYPES and doc.get("ItemId"):
            asked[doc["People"]].add(doc["ItemId"])
            if doc["ItemId"] in village_sold[doc["People"]]:
                errors.append(f"demande {path.stem} : {doc['ItemId']} est vendu par la boutique du village")
    for wid, orders in [(w[0], w[7]) for w in WORKSHOPS] + [(a[0], a[3]) for a in ANNEXES] + [(h[0], h[3]) for h in HAMLET_OWN]:
        people = wid.split("_")[0]
        shops = SHOPS.get(wid, {})
        own = {t[0] for t in shops.get("Base", [])}
        for key, value in shops.items():
            if key != "Base":
                own |= {t[0] for lst in value for t in lst}
        for suffix, rtype, what, *_ in orders:
            if rtype not in ASKED_TYPES:
                continue
            asked[people].add(what)
            if what in own:
                errors.append(f"commande {wid}_{suffix} : {what} est vendu par la boutique du bâtiment")
            if what in village_sold[people]:
                errors.append(f"commande {wid}_{suffix} : {what} est vendu par la boutique du village")
    return asked


def specialties(doc, wid, people, name_fr, name_en, items, roles, fr, en, errors, building=None):
    """Spécialités, bêtes et boutiques (niveaux I à III) d'un bâtiment de métier, ajoutées à `doc`."""
    specs = SPECIALTIES.get(wid)
    if specs is None:
        errors.append(f"{wid} : pas de spécialités")
    else:
        base, choices = specs
        if base:
            doc["Livestock"] = base
            doc["LivestockCount"] = LIVESTOCK_COUNT
            r = rect(building)
            doc["Pen"] = [r[0] + PEN_INSET, r[1] - PEN_INSET, r[2] + PEN_INSET, r[3] - PEN_INSET]
        doc["Specialties"] = []
        shops = SHOPS.get(wid)
        if shops is None:
            errors.append(f"{wid} : pas de boutiques (SHOPS)")
            shops = {"Base": []}
        if len(shops["Base"]) < 2:
            errors.append(f"{wid} : boutique du niveau I avec moins de 2 échanges "
                          f"({[t[0] for t in shops['Base']]})")
        base_trades = [t + (SHOP_STOCK[1],) for t in shops["Base"]]
        base_id = f"{SHOP_PREFIX}{wid}_Base_1"
        write_shop(base_id, people, base_trades, f"nakasar_peuples.barter.W_{wid}_Base_1.title",
                   f"Boutique du niveau I du bâtiment de métier {wid}, générée par tools/generate_workshops.py.",
                   items, errors)
        fr[f"barter.W_{wid}_Base_1.title"] = f"{name_fr} I"
        en[f"barter.W_{wid}_Base_1.title"] = f"{name_en} I"
        doc["Shop"] = base_id
        for extra in set(shops) - {"Base"} - {c[0] for c in choices}:
            errors.append(f"{wid} : boutique d'une spécialité inconnue {extra}")
        for sid, sfr, sen, sicon, lfr, len_, animals in choices:
            if sicon not in items:
                errors.append(f"{wid}/{sid} : icône vanilla inconnue {sicon}")
            for a in (base or []) + animals:
                if not a.startswith(PEN) and a not in roles:
                    errors.append(f"{wid}/{sid} : rôle vanilla inconnu {a}")
                if a.startswith(PEN) and not (RES / "NPC/Roles/Nakasar/Peuples" / f"{a}.json").exists():
                    errors.append(f"{wid}/{sid} : rôle du mod absent {a} (tools/generate_pens.py)")
            if base and not animals:
                errors.append(f"{wid}/{sid} : spécialité d'enclos sans bêtes")
            spec = {"Id": sid, "NameKey": f"nakasar_peuples.workshop.specialty.{wid}.{sid}",
                    "LineKey": f"nakasar_peuples.workshop.specialtyLine.{wid}.{sid}", "Icon": sicon}
            if animals:
                spec["Animals"] = animals
            if (wid, sid) in RAID:
                if people == "Trork":
                    errors.append(f"{wid}/{sid} : les Trorks ne subissent pas de raid")
                spec["Raid"] = RAID[(wid, sid)]
            two, three = shops.get(sid, ([], []))
            if not two or not three:
                errors.append(f"{wid}/{sid} : boutique des niveaux II et III manquante")
            else:
                trades = list(base_trades)
                spec["Shops"] = []
                for level, add in ((2, two), (3, three)):
                    trades = trades + [t + (SHOP_STOCK[level],) for t in add]
                    shop_id = f"{SHOP_PREFIX}{wid}_{sid}_{level}"
                    write_shop(shop_id, people, trades, f"nakasar_peuples.barter.W_{wid}_{sid}_{level}.title",
                               f"Boutique du niveau {level} du bâtiment de métier {wid}, spécialité {sid}, générée "
                               "par tools/generate_workshops.py.", items, errors)
                    spec["Shops"].append(shop_id)
                    fr[f"barter.W_{wid}_{sid}_{level}.title"] = f"{name_fr} : {sfr} {ROMAN[level]}"
                    en[f"barter.W_{wid}_{sid}_{level}.title"] = f"{name_en}: {sen} {ROMAN[level]}"
                spec["ShareItem"], spec["ShareQuantity"] = two[0][0], two[0][1]
            doc["Specialties"].append(spec)
            fr[f"workshop.specialty.{wid}.{sid}"] = sfr
            en[f"workshop.specialty.{wid}.{sid}"] = sen
            fr[f"workshop.specialtyLine.{wid}.{sid}"] = lfr
            en[f"workshop.specialtyLine.{wid}.{sid}"] = len_


def write_orders(wid, people, folder, orders, items, roles, fr, en, errors):
    """Commandes du bâtiment et ses deux commandes de maître (dossier `folder`, vidé d'abord)."""
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.json"):
        old.unlink()
    for suffix, rtype, what, quantity, title_fr, title_en in orders:
        tid = f"{wid}_{suffix}"
        for title in (title_fr, title_en):
            if len(title) > 24:
                errors.append(f"{tid} : titre de plus de 24 caractères « {title} »")
        t = {
            "$Comment": f"Commande du bâtiment de métier {wid}, générée par tools/generate_workshops.py "
                        "(ne pas modifier à la main) : voir RequestTemplate.",
            "People": people,
            "Workshop": wid,
            "Type": rtype,
            "MinLevel": 1,
            "MaxLevel": 3,
            "Weight": 1,
            "TitleKey": f"nakasar_peuples.request.{tid}.title",
            "TaskKey": f"nakasar_peuples.request.{tid}.task",
        }
        if rtype == "Hunt":
            for role in what:
                if role not in roles:
                    errors.append(f"{tid} : rôle vanilla inconnu {role}")
            t["Spawns"] = list(what)
            t["Roles"] = sorted(set(what))
            t["MinDistance"], t["MaxDistance"] = HUNT_DISTANCE
        else:
            if what not in items:
                errors.append(f"{tid} : objet vanilla inconnu {what}")
            t["ItemId"] = what
            t["Quantity"] = quantity
        t.update(REWARD[rtype])
        (folder / f"{tid}.json").write_text(json.dumps(t, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        fr[f"request.{tid}.title"] = title_fr
        en[f"request.{tid}.title"] = title_en
        fr[f"request.{tid}.task"] = TASKS[rtype][0]
        en[f"request.{tid}.task"] = TASKS[rtype][1]
    for level, (suffix, rtype, what, quantity, _tf, _te) in ((1, orders[0]), (2, orders[1])):
        tid = f"{wid}_Master_{level}"
        scale = MASTER_SCALE[level]
        t = {
            "$Comment": f"Commande de maître du niveau {level} du bâtiment de métier {wid}, générée par "
                        "tools/generate_workshops.py (ne pas modifier à la main) : voir RequestTemplate.",
            "People": people,
            "Workshop": wid,
            "Master": True,
            "Type": rtype,
            "MinLevel": level,
            "MaxLevel": level,
            "Weight": 1,
            "TitleKey": f"nakasar_peuples.request.{tid}.title",
            "TaskKey": f"nakasar_peuples.request.{tid}.task",
        }
        if rtype == "Hunt":
            t["Spawns"] = list(what) * 2
            t["Roles"] = sorted(set(what))
            t["MinDistance"], t["MaxDistance"] = HUNT_DISTANCE[0] + 20, HUNT_DISTANCE[1] + 30
        else:
            t["ItemId"] = what
            t["Quantity"] = quantity * scale
        t.update(MASTER_REWARD)
        (folder / f"{tid}.json").write_text(json.dumps(t, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        roman = "I" * level
        fr[f"request.{tid}.title"] = f"Commande de maître {roman}"
        en[f"request.{tid}.title"] = f"Master order {roman}"
        fr[f"request.{tid}.task"] = TASKS[rtype][0]
        en[f"request.{tid}.task"] = TASKS[rtype][1]


def main():
    items = load_ids(ITEMS)
    roles = load_ids(REFS, "npc")
    errors = []
    fr, en = {}, {}
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.json"):
        old.unlink()
    for old in BARTER.glob(SHOP_PREFIX + "*.json"):
        old.unlink()
    layouts = {}
    twins = plot_workshops(fr, en, errors)
    annex_tables(errors)
    hamlet_tables(errors)
    selling_rules(errors)
    for wid, layout_id, building_id, job_id, icon, name_fr, name_en, orders in WORKSHOPS:
        layout = layouts.setdefault(layout_id, json.loads((LAYOUTS / f"{layout_id}.json").read_text(encoding="utf-8")))
        people = layout["People"]
        building = next((b for b in layout["Buildings"] if b["Id"] == building_id), None)
        job = next((j for j in layout["Jobs"] if j["Id"] == job_id), None)
        if building is None or job is None:
            errors.append(f"{wid} : bâtiment {building_id} ou métier {job_id} absent du plan {layout_id}")
            continue
        if job["Building"] != building_id:
            errors.append(f"{wid} : le métier {job_id} travaille dans {job['Building']}, pas {building_id}")
        if icon not in items:
            errors.append(f"{wid} : icône vanilla inconnue {icon}")
        spot = board_spot(layout, building, errors)
        doc = {
            "$Comment": "Bâtiment de métier généré par tools/generate_workshops.py (ne pas modifier à la main) : voir "
                        "dev.nakasar.hytale.peuples.workshop.Workshop.",
            "People": people,
            "Layout": layout_id,
            "Building": building_id,
            "Job": job_id,
            "Icon": icon,
            "NameKey": f"nakasar_peuples.workshop.{wid}.name",
            "Board": spot or [0, 0, 0],
            "Upgrades": upgrades(layout, wid, errors),
        }
        if wid in twins:
            doc["Twin"] = twins[wid]
        specialties(doc, wid, people, name_fr, name_en, items, roles, fr, en, errors, building)
        (OUT / f"{wid}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        fr[f"workshop.{wid}.name"] = name_fr
        en[f"workshop.{wid}.name"] = name_en

        write_orders(wid, people, REQUESTS / people / building_id, orders, items, roles, fr, en, errors)
        print(f"{wid} : {len(orders)} commandes + 2 de maître, panneau {spot}")
    write_annexes(items, roles, fr, en, errors)
    write_hamlet_workshops(items, roles, fr, en, errors)
    for key, (f, e) in PAGE.items():
        fr[key] = f
        en[key] = e
    if errors:
        for e in errors:
            print("ERREUR", e)
        raise SystemExit(1)
    for locale, table in (("fr-FR", fr), ("en-US", en)):
        path = RES / f"Languages/{locale}/nakasar_peuples.lang"
        text = path.read_text(encoding="utf-8")
        if LANG_BEGIN in text:
            before, rest = text.split(LANG_BEGIN, 1)
            text = before + rest.split(LANG_END, 1)[1].lstrip("\n")
        existing = {line.split("=", 1)[0].strip() for line in text.splitlines() if "=" in line and not line.startswith("#")}
        dup = sorted(k for k in table if k in existing)
        if dup:
            raise SystemExit(f"clés déjà présentes dans {locale} (hors bloc des bâtiments de métier) : {dup[:10]}")
        block = [LANG_BEGIN] + [f"{k} = {v}" for k, v in table.items()] + [LANG_END, ""]
        path.write_text("\n".join(block) + text, encoding="utf-8")
        print(f"{path.relative_to(ROOT)} : {len(table)} clés")


if __name__ == "__main__":
    main()
