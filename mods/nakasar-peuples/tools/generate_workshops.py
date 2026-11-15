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

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "src/main/resources/Server"
LAYOUTS = RES / "Nakasar/VillageLayouts"
OUT = RES / "Nakasar/Workshops"
REQUESTS = RES / "Nakasar/Requests"
ITEMS = Path(__file__).resolve().parent / "vanilla-item-ids-0.7.2.txt"
REFS = Path(__file__).resolve().parent / "vanilla-refs-0.7.2.txt"

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
        ("Carrots", "Gather", "Plant_Crop_Carrot_Item", 10, "Carottes des lapins", "Carrots for the rabbits"),
        ("Hay", "Gather", "Ingredient_Hay", 12, "Foin de l'enclos", "Hay for the pen"),
        ("Poachers", "Hunt", ["Trork_Hunter", "Trork_Hunter"], 0, "Braconniers trorks", "Trork poachers"),
    ]),
    # Étape 3 : les enclos des quatre autres peuples (tools/generate_pens.py, palier 1).
    ("Trork_Fosse_Aux_Betes", "Trork_Camp", "Fosse_Aux_Betes", "Dresseur", "Food_Wildmeat_Raw", "Fosse aux bêtes",
     "Beast pit", [
        ("Meat", "Gather", "Food_Wildmeat_Raw", 10, "Viande pour la fosse", "Meat for the pit"),
        ("Bones", "Gather", "Ingredient_Bone_Fragment", 12, "Os à ronger", "Bones to gnaw"),
        ("Wolves", "Hunt", ["Wolf_Black", "Wolf_Black"], 0, "Loups affamés", "Hungry wolves"),
    ]),
    ("Feran_Enclos_Oasis", "Feran_Oasis", "Enclos_Oasis", "Eleveuse", "Food_Egg", "Enclos de l'oasis", "Oasis pen", [
        ("Grain", "Gather", "Plant_Seeds_Wheat", 12, "Grain des poules", "Grain for the hens"),
        ("Water", "Gather", "Ingredient_Water_Essence", 4, "Eau pour l'enclos", "Water for the pen"),
        ("Scaraks", "Hunt", ["Scarak_Fighter", "Scarak_Fighter"], 0, "Scaraks voleurs d'œufs", "Egg-thief Scaraks"),
    ]),
    ("Renonce_Bergerie_Du_Givre", "Renonce_Givre", "Bergerie_Du_Givre", "Berger", "Ingredient_Fabric_Scrap_Wool",
     "Bergerie du givre", "Frost fold", [
        ("Hay", "Gather", "Ingredient_Hay", 12, "Foin pour l'hiver", "Hay for winter"),
        ("Wool", "Gather", "Ingredient_Fabric_Scrap_Wool", 8, "Laine de la bergerie", "Wool for the fold"),
        ("Wolves", "Hunt", ["Wolf_White", "Wolf_White"], 0, "Loups des neiges", "Snow wolves"),
    ]),
    ("Slothian_Bauge_De_Veille", "Slothian_Monastere", "Bauge_De_Veille", "Gardien_Bauge", "Food_Pork_Raw",
     "Bauge de veille", "Vigil pen", [
        ("Mud", "Gather", "Soil_Mud_Dry", 16, "Boue de la bauge", "Mud for the pen"),
        ("Roots", "Gather", "Plant_Crop_Carrot_Item", 10, "Racines des porcs", "Roots for the pigs"),
        ("Crawlers", "Hunt", ["Crawler_Void", "Crawler_Void"], 0, "Rampants à la bauge", "Crawlers at the pen"),
    ]),
    ("Kweebec_Potager", "Kweebec_Oak", "Potager", "Jardiniere", "Plant_Seeds_Lettuce", "Potager", "Vegetable garden", [
        ("Lettuce", "Gather", "Plant_Seeds_Lettuce", 10, "Graines de salade", "Lettuce seeds"),
        ("Wheat", "Gather", "Plant_Seeds_Wheat", 12, "Semences de blé", "Wheat seeds"),
        ("Soup", "Craft", "Food_Vegetable_Cooked", 4, "Légumes pour la soupe", "Vegetables for soup"),
    ]),
    ("Kweebec_Puits", "Kweebec_Oak", "Puits", "Puisatiere", "Container_Bucket", "Puits", "Well", [
        ("Buckets", "Craft", "Container_Bucket", 2, "Seaux pour le puits", "Buckets for the well"),
        ("Water", "Gather", "Ingredient_Water_Essence", 4, "Eau vive", "Living water"),
        ("Stones", "Gather", "Rock_Stone_Cobble", 20, "Pierres de la margelle", "Stones for the rim"),
    ]),
    ("Kweebec_Grande_Maison", "Kweebec_Oak", "Grande_Maison", "Soigneuse", "Potion_Health_Small", "Maison de soins",
     "House of healing", [
        ("Flowers", "Gather", "Plant_Flower_Common_Red", 8, "Fleurs de soin", "Healing flowers"),
        ("Vials", "Craft", "Potion_Health_Small", 2, "Fioles de soin", "Healing vials"),
        ("Essence", "Gather", "Ingredient_Life_Essence", 8, "Essence de vie", "Life essence"),
    ]),
    ("Kweebec_Tour_Est", "Kweebec_Oak", "Tour_Est", "Garde", "Weapon_Arrow_Crude", "Tour de la garde", "Guard tower", [
        ("Arrows", "Craft", "Weapon_Arrow_Crude", 32, "Flèches pour la tour", "Arrows for the tower"),
        ("Scouts", "Hunt", ["Trork_Warrior", "Trork_Warrior", "Trork_Brawler"], 0, "Éclaireurs trorks", "Trork scouts"),
        ("Palisade", "Gather", "Wood_Oak_Trunk", 12, "Bois de la palissade", "Palisade logs"),
    ]),
    ("Trork_Piege", "Trork_Camp", "Piege", "Chasseur", "Ingredient_Hide_Light", "Piège du chasseur", "Hunter's trap", [
        ("Hides", "Gather", "Ingredient_Hide_Light", 8, "Peaux du piège", "Hides for the trap"),
        ("Wolves", "Hunt", ["Wolf_Black", "Wolf_Black"], 0, "Loups du piège", "Wolves at the trap"),
        ("Bait", "Gather", "Ingredient_Bone_Fragment", 10, "Os pour les appâts", "Bones for bait"),
    ]),
    ("Trork_Feu_De_Camp", "Trork_Camp", "Feu_De_Camp", "Guerrier", "Food_Wildmeat_Cooked", "Feu de camp", "Campfire", [
        ("Roast", "Craft", "Food_Wildmeat_Cooked", 6, "Viande du feu", "Meat for the fire"),
        ("Logs", "Gather", "Wood_Oak_Trunk", 16, "Bois pour le feu", "Logs for the fire"),
        ("Mosshorn", "Hunt", ["Mosshorn"], 0, "Gros gibier", "Big game"),
    ]),
    ("Trork_Entrepot", "Trork_Camp", "Entrepot", "Cogneur", "Ingredient_Bar_Copper", "Entrepôt", "Warehouse", [
        ("Copper", "Gather", "Ingredient_Bar_Copper", 4, "Cuivre de l'entrepôt", "Copper for the store"),
        ("Stones", "Gather", "Rock_Stone_Cobble", 24, "Pierres de l'entrepôt", "Stones for the store"),
        ("Hides", "Gather", "Ingredient_Hide_Medium", 6, "Peaux épaisses", "Thick hides"),
    ]),
    ("Feran_Entree_Oasis", "Feran_Oasis", "Entree_Oasis", "Porteuse_Eau", "Container_Bucket", "Entrée de l'oasis",
     "Oasis gate", [
        ("Buckets", "Craft", "Container_Bucket", 2, "Seaux de la porteuse", "Buckets for the carrier"),
        ("Water", "Gather", "Ingredient_Water_Essence", 6, "Eau de l'oasis", "Oasis water"),
        ("Salt", "Gather", "Ingredient_Salt", 6, "Sel de l'oasis", "Oasis salt"),
    ]),
    ("Feran_Hutte_Pilier", "Feran_Oasis", "Hutte_Pilier", "Garde", "Weapon_Spear_Crude", "Hutte de la garde",
     "Guard hut", [
        ("Spears", "Craft", "Weapon_Spear_Crude", 2, "Lances pour la garde", "Spears for the guard"),
        ("Scaraks", "Hunt", ["Scarak_Fighter", "Scarak_Fighter", "Scarak_Fighter"], 0, "Scaraks aux portes",
         "Scaraks at the gates"),
        ("Feathers", "Gather", "Ingredient_Feathers_Light", 8, "Plumes des coureurs", "Runner feathers"),
    ]),
    ("Renonce_Maison_Du_Chasseur", "Renonce_Givre", "Maison_Du_Chasseur", "Chasseur", "Ingredient_Hide_Heavy",
     "Maison du chasseur", "Hunter's lodge", [
        ("Hides", "Gather", "Ingredient_Hide_Heavy", 4, "Peaux lourdes", "Heavy hides"),
        ("Meat", "Gather", "Food_Wildmeat_Raw", 8, "Viande pour l'hiver", "Meat for winter"),
        ("Poachers", "Hunt", ["Outlander_Hunter", "Outlander_Hunter"], 0, "Braconniers du culte", "Cult poachers"),
    ]),
    ("Renonce_Tour_Du_Fort", "Renonce_Givre", "Tour_Du_Fort", "Garde", "Weapon_Arrow_Crude", "Tour du fort",
     "Fort tower", [
        ("Fir", "Gather", "Wood_Fir_Trunk", 16, "Sapin des remparts", "Fir for the ramparts"),
        ("Cultists", "Hunt", ["Outlander_Cultist", "Outlander_Cultist", "Outlander_Cultist"], 0,
         "Cultistes près du fort", "Cultists near the fort"),
        ("Arrows", "Craft", "Weapon_Arrow_Crude", 24, "Flèches du fort", "Arrows for the fort"),
    ]),
    ("Slothian_Etal_Des_Cendres", "Slothian_Monastere", "Etal_Des_Cendres", "Porteur_Cendres", "Ingredient_Charcoal",
     "Étal des cendres", "Ash stall", [
        ("Ash", "Gather", "Soil_Ash", 20, "Cendres de l'étal", "Ash for the stall"),
        ("Charcoal", "Gather", "Ingredient_Charcoal", 8, "Charbon des braises", "Charcoal for embers"),
        ("Fire", "Gather", "Ingredient_Fire_Essence", 4, "Essence de feu", "Fire essence"),
    ]),
    ("Slothian_Temple_De_Veille", "Slothian_Monastere", "Temple_De_Veille", "Moine", "Furniture_Jungle_Candle",
     "Temple de veille", "Vigil temple", [
        ("Candles", "Craft", "Furniture_Jungle_Candle", 4, "Cierges du temple", "Temple candles"),
        ("Void", "Gather", "Ingredient_Void_Essence", 3, "Essence du Vide", "Void essence"),
        ("Potions", "Craft", "Potion_Regen_Mana_Small", 2, "Potions de veille", "Vigil potions"),
    ]),
    ("Slothian_Porte_Du_Monastere", "Slothian_Monastere", "Porte_Du_Monastere", "Garde", "Rock_Volcanic",
     "Porte du monastère", "Monastery gate", [
        ("Crawlers", "Hunt", ["Crawler_Void", "Crawler_Void", "Crawler_Void"], 0, "Rampants du Vide",
         "Void crawlers"),
        ("Basalt", "Gather", "Rock_Volcanic", 20, "Basalte de la porte", "Basalt for the gate"),
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
    for key in ("Board", "Deposit", "Banner"):
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
        if any(inside(x, z, rect(o), 0) for oid, o in by_id.items() if oid != building["Id"]):
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
        (OUT / f"{wid}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        fr[f"workshop.{wid}.name"] = name_fr
        en[f"workshop.{wid}.name"] = name_en

        folder = REQUESTS / people / building_id
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
        print(f"{wid} : {len(orders)} commandes + 2 de maître, panneau {spot}")
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
