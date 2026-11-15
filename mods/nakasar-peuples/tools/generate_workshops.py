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
    "workshop.offersSoon": ("La boutique de {name} ouvrira avec les spécialités.",
                            "{name}'s shop opens with the specialties."),
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


def main():
    items = load_ids(ITEMS)
    roles = load_ids(REFS, "npc")
    errors = []
    fr, en = {}, {}
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.json"):
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
