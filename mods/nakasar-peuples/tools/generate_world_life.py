#!/usr/bin/env python3
"""Génère les assets du monde vivant entre les villages (package Java dev.nakasar.hytale.peuples.world).

Proposition « Un monde vivant entre les villages » (15 novembre 2026), les six étapes : voyageurs et embuscades,
vie autour du village, traces et auberges, campements et réfugiés, relations entre villages, calendrier.

Sorties :
    Server/NPC/Roles/Nakasar/Peuples/Nakasar_Peuples_<Peuple>_{Traveller,Peddler,Innkeeper,Camper,Outing,Child,Host}.json
    Server/NPC/Roles/Nakasar/Peuples/Nakasar_Peuples_Trork_Patrol.json      combattant trork (les Trorks n'ont pas de garde)
    Server/NPC/Roles/Nakasar/Peuples/Nakasar_Peuples_Herd_<Espèce>.json     bêtes de la migration (modèles vanilla)
    Server/Models/Nakasar/Peuples/Nakasar_Peuples_{Trork,Renonce}_Young.json  enfants trork et renoncés : le modèle
                                                                            vanilla adulte à l'échelle 0,6 (Kevin)
    Server/Nakasar/Dialogues/Monde/Monde_*.json
    Server/BarterShops/Nakasar_Peuples_Travel_<Peuple>.json, Nakasar_Peuples_Inn.json
    Server/Item/Items/Nakasar/Peuples/Nakasar_Peuples_Letter.json
    Server/WorldEvent/{Event,Stage}/Nakasar/Peuples/Nakasar_Peuples_{Harvest,Fair,Migration}*.json
    bloc « Monde vivant » en tête des deux fichiers .lang

Tous les rôles sont des Nakasar_Peuples_* : aucune régénération (VillageNoRegenSystem, règle n° 1). Apparences et
objets vanilla (règle n° 2). Usage : python3 tools/generate_world_life.py
"""
import copy
import json
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
RES = ROOT / "src/main/resources/Server"
ROLES = RES / "NPC/Roles/Nakasar/Peuples"
DIALOGUES = RES / "Nakasar/Dialogues/Monde"
LANG_BEGIN = "# ---- Monde vivant entre les villages (généré par tools/generate_world_life.py, ne pas modifier à la main) ----"
LANG_END = "# ---- Fin du monde vivant ----"

FR = {}
EN = {}


def t(key, fr, en):
    if key in FR:
        raise SystemExit(f"clé en double : {key}")
    FR[key] = fr
    EN[key] = en


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(path.relative_to(ROOT))


# ---- Peuples : noms et apparences vanilla ----

PEOPLES = {
    # id : (nom fr, nom en, voyageur, colporteur, aubergiste, campeur, enfant, hôte)
    "Kweebec": ("kweebec", "Kweebec", "Kweebec_Sapling_Orange", "Kweebec_Rootling", "Kweebec_Sapling_Brown",
                "Kweebec_Sapling_Green", "Kweebec_Sproutling", "Kweebec_Sapling_Treesinger"),
    "Trork": ("trork", "Trork", "Trork_Hunter", "Trork_Doctor_Witch", "Trork", "Trork_Hunter",
              "Nakasar_Peuples_Trork_Young", "Trork_Chieftain"),
    "Feran": ("feran", "Feran", "Feran_Civilian", "Feran_Civilian", "Feran_Burrower", "Feran_Burrower", "Feran_Cub",
              "Feran_Windwalker"),
    "Renonce": ("renoncé", "Renounced", "Outlander_Peon", "Outlander_Peon", "Outlander_Peon", "Outlander_Hunter",
                "Nakasar_Peuples_Renonce_Young", "Outlander_Sorcerer"),
    "Slothian": ("slothian", "Slothian", "Slothian_Villager", "Slothian_Villager", "Slothian_Monk", "Slothian_Scout",
                 "Slothian_Kid", "Slothian_Elder"),
}

FAVOR = {p: f"Nakasar_Peuples_Favor_{p}" for p in PEOPLES}

INTERACT = {
    "Instructions": [
        {"Continue": True, "Sensor": {"Type": "Any"},
         "Actions": [{"Type": "SetInteractable", "Interactable": True, "Hint": "nakasar_peuples.hint.talk"}]},
        {"Sensor": {"Type": "HasInteracted"}, "Actions": []},
    ]
}


def walker(role_id, comment, appearance, hp, speed, relative, wander, interact=True):
    """PNJ qui marche vers son point d'attache (déplacé par le Java) et flâne autour ; ne se bat pas."""
    role = {
        "$Comment": comment + " Généré par tools/generate_world_life.py. Ne régénère jamais (VillageNoRegenSystem).",
        "Type": "Generic",
        "Appearance": appearance,
        "NameTranslationKey": f"nakasar_peuples.npc.{role_id}.name",
        "MaxHealth": hp,
        "StartState": "Idle",
        "DefaultPlayerAttitude": "Neutral",
        "DefaultNPCAttitude": "Ignore",
        "MotionControllerList": [{
            "Type": "Walk", "MaxWalkSpeed": speed, "Gravity": 10, "RunThreshold": 0.6, "MaxFallSpeed": 15,
            "MaxRotationSpeed": 360, "Acceleration": 10, "JumpHeight": 1.0,
        }],
        "KnockbackScale": 0.5,
        "Instructions": [{
            "Sensor": {"Type": "State", "State": "Idle"},
            "Instructions": [
                {"$Comment": "Loin de son point d'attache (le Java le déplace) : il y marche.",
                 "Sensor": {"Type": "Leash", "Range": 3},
                 "BodyMotion": {"Type": "Seek", "RelativeSpeed": relative, "SlowDownDistance": 2, "StopDistance": 1,
                                "UsePathfinder": True}},
                {"$Comment": "Arrivé : il flâne.",
                 "BodyMotion": {"Type": "WanderInCircle", "Radius": wander, "RelativeSpeed": 0.3, "MaxHeadingChange": 50}},
            ],
        }],
    }
    if interact:
        role["InteractionInstruction"] = copy.deepcopy(INTERACT)
    return role


def roles():
    for pid, (fr, en, traveller, peddler, keeper, camper, child, host) in PEOPLES.items():
        specs = [
            ("Traveller", traveller, 90, 6, 0.6, 2, f"Voyageur {fr}", f"{en} traveller",
             "Voyageur du monde vivant (pèlerin, messager, porteur d'une caravane) : world/Travellers le fait marcher de village en village."),
            ("Peddler", peddler, 110, 6, 0.6, 2, f"Colporteur {fr}", f"{en} peddler",
             "Marchand ambulant ou meneur de caravane (world/Travellers), marchand de la foire (world/Calendar)."),
            ("Innkeeper", keeper, 120, 3, 0.5, 2, f"Aubergiste {fr}", f"{en} innkeeper",
             "Aubergiste d'une auberge de relais (world/Inns)."),
            ("Camper", camper, 90, 3, 0.5, 4, f"Campeur {fr}", f"{en} camper",
             "Habitant d'un campement temporaire ou de réfugiés (world/Camps)."),
            ("Outing", camper, 70, 4, 0.5, 3, f"Villageois {fr} en sortie", f"{en} villager on an outing",
             "Villageois qui sort cueillir, pêcher, couper du bois ou garder les bêtes (world/Surroundings)."),
            ("Child", child, 40, 5, 0.8, 4, f"Enfant {fr}", f"{en} child",
             "Enfant qui joue sur la place ; cache-cache (world/Surroundings)."),
            ("Host", host, 120, 3, 0.5, 2, f"Hôte {fr} de la fête", f"{en} festival host",
             "Hôte de la fête des moissons ou de la foire (world/Calendar)."),
        ]
        for suffix, appearance, hp, speed, rel, wander, nfr, nen, comment in specs:
            rid = f"{pid}_{suffix}"
            write(ROLES / f"Nakasar_Peuples_{rid}.json", walker(rid, comment, appearance, hp, speed, rel, wander))
            t(f"npc.{rid}.name", nfr[0].upper() + nfr[1:], nen)
    # Patrouilleur trork : la conduite du garde kweebec, l'apparence et la hache du guerrier trork vanilla.
    defender = json.loads((ROLES / "Nakasar_Peuples_Kweebec_Defender.json").read_text(encoding="utf-8-sig"))
    warrior = json.loads((ROLES / "Nakasar_Peuples_Raider_Trork_Warrior.json").read_text(encoding="utf-8-sig"))
    patrol = copy.deepcopy(defender)
    patrol["$Comment"] = ("Patrouilleur trork (monde vivant : patrouilles autour du village, escarmouches), généré par "
                          "tools/generate_world_life.py : conduite du garde de raid kweebec, apparence, hache et attaques du "
                          "guerrier trork vanilla. Ne se soigne jamais (règle n° 1).")
    patrol["Appearance"] = warrior["Appearance"]
    patrol["HotbarItems"] = warrior["HotbarItems"]
    patrol["NameTranslationKey"] = "nakasar_peuples.npc.Trork_Patrol.name"
    patrol["MaxHealth"] = 120
    patrol.pop("DisableDamageGroups", None)
    attacks = ["Trork_Warrior_Battleaxe_Swing_Left", "Trork_Warrior_Battleaxe_Swing_Right", "Trork_Warrior_Battleaxe_Swing_Down"]
    text = json.dumps(patrol, ensure_ascii=False)
    for i, old in enumerate(["Kweebec_Sapling_Razorleaf_Spear_Swing_Left", "Kweebec_Sapling_Razorleaf_Spear_Swing_Right",
                             "Kweebec_Sapling_Razorleaf_Spear_Stab"]):
        text = text.replace(old, attacks[i])
    write(ROLES / "Nakasar_Peuples_Trork_Patrol.json", json.loads(text))
    t("npc.Trork_Patrol.name", "Patrouilleur trork", "Trork patroller")


HERDS = {
    # espèce : (apparence vanilla, PV, fr, en)
    "Bison": ("Bison", 160, "Bison", "Bison"),
    "Bison_Calf": ("Bison_Calf", 60, "Bisonneau", "Bison calf"),
    "Deer_Stag": ("Model_Deer_Stag", 103, "Cerf", "Stag"),
    "Deer_Doe": ("Deer_Doe", 80, "Biche", "Doe"),
    "Camel": ("Camel", 140, "Chameau", "Camel"),
    "Camel_Calf": ("Camel_Calf", 60, "Chamelon", "Camel calf"),
    "Moose_Bull": ("Moose_Bull", 170, "Élan", "Moose bull"),
    "Moose_Cow": ("Moose_Cow", 130, "Femelle élan", "Moose cow"),
    "Mouflon": ("Mouflon", 90, "Mouflon", "Mouflon"),
    "Mouflon_Lamb": ("Mouflon_Lamb", 40, "Agneau mouflon", "Mouflon lamb"),
    "Antelope": ("Antelope", 90, "Antilope", "Antelope"),
}


def herds():
    for sid, (appearance, hp, fr, en) in HERDS.items():
        rid = f"Herd_{sid}"
        role = walker(rid, f"Bête de la migration ({fr}), modèle vanilla {appearance} : world/Calendar mène le troupeau ; "
                           "abattue par un joueur, elle rapporte viande et peau (Java).", appearance, hp, 7, 0.55, 3, interact=False)
        write(ROLES / f"Nakasar_Peuples_{rid}.json", role)
        t(f"npc.{rid}.name", fr, en)


def models():
    for pid, parent in (("Trork", "Trork"), ("Renonce", "Outlander_Peon")):
        write(RES / f"Models/Nakasar/Peuples/Nakasar_Peuples_{pid}_Young.json", {
            "$Comment": f"Enfant {pid} : pas d'enfant vanilla, donc le modèle adulte {parent} à l'échelle 0,6 (Kevin, 15 novembre 2026).",
            "Parent": parent,
            "MinScale": 0.6,
            "MaxScale": 0.6,
        })


# ---- Dialogues ----

def node(nid, text, responses):
    return {"Id": nid, "TextKey": text, "Responses": responses}


def resp(text, action=None, next_=None, check=None, close=False):
    r = {"TextKey": text}
    if check:
        r["Conditions"] = [{"Type": "WorldCheck", "Check": check}]
    if action:
        r["Effects"] = [{"Type": "WorldAction", "Action": action}]
    if next_ and not close:
        r["Next"] = next_
    return r


RUMOUR_NODE = "Rumeur"


def dialogue(did, comment, npc_fr, npc_en, role_fr, role_en, nodes):
    k = f"dialogue.{did}."
    t(k + "npc", npc_fr, npc_en)
    t(k + "role", role_fr, role_en)
    # La rumeur (WorldAction Rumour) s'affiche dans la fenêtre, sous la réplique du nœud Rumeur (dialogue/DialogueSpeech).
    if any(e.get("Action") == "Rumour" for n in nodes for r in n["Responses"] for e in r.get("Effects", [])):
        common = "nakasar_peuples.dialogue.Monde."
        nodes = nodes + [node(RUMOUR_NODE, common + "rumeurTexte", [
            resp(common + "rumeurAutre", "Rumour", RUMOUR_NODE), resp(common + "retour", None, "Accueil"), resp(common + "aurevoir")])]
    return {
        "$Comment": comment + " Généré par tools/generate_world_life.py ; effets WorldAction et conditions WorldCheck (world/WorldDialogueTypes).",
        "NpcNameKey": f"nakasar_peuples.{k}npc",
        "RoleKey": f"nakasar_peuples.{k}role",
        "Entries": [{"Node": "Accueil"}],
        "Nodes": nodes,
    }


def dialogues():
    common = "nakasar_peuples.dialogue.Monde."
    t("dialogue.Monde.rumeur", "Quelles nouvelles sur la route ?", "Any news from the road?")
    t("dialogue.Monde.aurevoir", "Bonne route.", "Safe travels.")
    t("dialogue.Monde.retour", "Autre chose…", "Something else…")
    t("dialogue.Monde.rumeurTexte", "Voilà ce qu'on raconte sur la route :", "Here's what they say on the road:")
    t("dialogue.Monde.rumeurAutre", "Une autre nouvelle ?", "Any other news?")
    rumour = resp(common + "rumeur", "Rumour", RUMOUR_NODE)
    bye = resp(common + "aurevoir")

    def say(did, key, fr, en):
        t(f"dialogue.{did}.{key}", fr, en)
        return f"nakasar_peuples.dialogue.{did}.{key}"

    d = "Monde_Marchand"
    write(DIALOGUES / f"{d}.json", dialogue(d, "Marchand ambulant sur la route (étape 1).", "Colporteur", "Peddler",
                                            "Marchand ambulant", "Travelling merchant", [
        node("Accueil", say(d, "accueil", "Je vais d'un village à l'autre avec ma marchandise. Les amis de mon village ont droit à mes meilleurs prix.",
                            "I go from village to village with my wares. Friends of my village get my best prices."), [
            resp(say(d, "troc", "Montre-moi ce que tu vends.", "Show me what you sell."), "Shop"), rumour, bye]),
    ]))
    d = "Monde_Pelerin"
    write(DIALOGUES / f"{d}.json", dialogue(d, "Pèlerin sur la route (étape 1) : rumeurs, escorte.", "Pèlerin", "Pilgrim",
                                            "Pèlerin", "Pilgrim", [
        node("Accueil", say(d, "accueil", "Je marche vers le village voisin. Les routes ne sont plus sûres, tu sais.",
                            "I'm walking to the next village. The roads aren't safe anymore, you know."), [
            resp(say(d, "escorte", "Je t'accompagne jusqu'au bout.", "I'll walk with you to the end."), "Escort", "Escorte"),
            rumour, bye]),
        node("Escorte", say(d, "escorteTexte", "Merci ! Reste près de moi jusqu'au village, ils sauront ce que tu as fait.",
                            "Thank you! Stay close until we reach the village, they'll know what you did."), [bye]),
    ]))
    d = "Monde_Messager"
    write(DIALOGUES / f"{d}.json", dialogue(d, "Messager entre deux villages (étapes 1 et 5) : lettre à porter, lettre de paix entre rivaux.",
                                            "Messager", "Messenger", "Messager", "Messenger", [
        node("Accueil", say(d, "accueil", "J'ai une lettre pour le village voisin. Si tu vas par là, je rentrerais bien chez moi…",
                            "I carry a letter for the next village. If you're going that way, I'd gladly head home…"), [
            resp(say(d, "lettre", "Donne-la-moi, je la porterai.", "Give it to me, I'll deliver it."), "Letter"),
            resp(say(d, "paix", "Et si c'était une lettre de paix ?", "What if it were a peace letter?"), "Parley", check="Parley"),
            rumour, bye]),
    ]))
    d = "Monde_Caravane"
    write(DIALOGUES / f"{d}.json", dialogue(d, "Meneur d'une caravane (étape 1) : troc, escorte ; peut tomber dans une embuscade à mi-chemin.",
                                            "Caravanier", "Caravan leader", "Meneur de caravane", "Caravan leader", [
        node("Accueil", say(d, "accueil", "Nos bêtes sont chargées pour le village voisin. Une escorte ne serait pas de refus.",
                            "Our beasts are loaded for the next village. An escort would be welcome."), [
            resp(say(d, "troc", "Que transportez-vous ?", "What are you carrying?"), "Shop"),
            resp(say(d, "escorte", "Je vous escorte.", "I'll escort you."), "Escort", "Escorte"),
            rumour, bye]),
        node("Escorte", say(d, "escorteTexte", "Parfait. Ouvre l'œil à mi-chemin : c'est là qu'ils attaquent.",
                            "Perfect. Keep your eyes open halfway: that's where they strike."), [bye]),
    ]))
    d = "Monde_Aubergiste"
    write(DIALOGUES / f"{d}.json", dialogue(d, "Aubergiste d'une auberge de relais (étape 3) : repas, troc des voyageurs (niveau 2), rumeurs et lettres (niveau 3).",
                                            "Aubergiste", "Innkeeper", "Auberge de relais", "Relay inn", [
        node("Accueil", say(d, "accueil", "Entre, voyageur ! Il y a toujours une soupe chaude pour qui passe sur cette route.",
                            "Come in, traveller! There's always a hot soup for whoever walks this road."), [
            resp(say(d, "repas", "Je prendrais bien un repas.", "I'd like a meal."), "InnShop"),
            resp(say(d, "voyageurs", "Qu'ont laissé les voyageurs ?", "What did the travellers leave?"), "InnTravel", check="InnLevel2"),
            resp(say(d, "tableau", "Le tableau des nouvelles ?", "The news board?"), None, "Tableau", check="InnLevel3"),
            rumour]),
        node("Tableau", say(d, "tableauTexte", "Des nouvelles de toute la région, et du courrier qui attend un porteur.",
                            "News from all around, and mail waiting for a carrier."), [
            rumour,
            resp(say(d, "lettre", "Je porte une lettre.", "I'll carry a letter."), "InnLetter"),
            resp(common + "retour", None, "Accueil"), bye]),
    ]))
    camps = {
        "Hunters": ("Chasseuse", "Huntress", "Campement de chasseurs", "Hunters' camp",
                    "La chasse est maigre. Rapporte-nous cinq viandes crues, on te donnera du cuir.",
                    "Game is scarce. Bring us five raw meats and we'll give you leather.",
                    "Voici la viande.", "Here's the meat.", "CampTurnIn"),
        "Woodcutters": ("Bûcheron", "Woodcutter", "Campement de bûcherons", "Woodcutters' camp",
                        "On abat du bois loin de chez nous et le pain manque. Trois pains contre de la sève ?",
                        "We cut wood far from home and bread is short. Three loaves for some sap?",
                        "Voici du pain.", "Here's some bread.", "CampTurnIn"),
        "Prospectors": ("Prospecteur", "Prospector", "Campement de prospecteurs", "Prospectors' camp",
                        "On a trouvé du minerai, mais des pillards rôdent. Aide-nous à les repousser et tu auras ta part.",
                        "We found ore, but raiders are prowling. Help us drive them off and you'll get your share.",
                        "Qu'ils viennent.", "Let them come.", "CampDefend"),
        "Merchants": ("Marchande", "Merchant", "Halte de marchands", "Merchants' halt",
                      "Une halte de quelques jours, le temps de vendre ce qu'on a.",
                      "A halt for a few days, long enough to sell what we've got.",
                      "Voyons vos étals.", "Let's see your stalls.", "CampShop"),
        "Refugees": ("Réfugiée", "Refugee", "Campement de réfugiés", "Refugee camp",
                     "Le raid a brûlé notre maison. On attend qu'elle soit relevée… un peu de nourriture aiderait.",
                     "The raid burned our home. We're waiting for it to be rebuilt… a little food would help.",
                     "Je vous donne à manger.", "I'll give you food.", "CampDonate"),
    }
    for kind, (nfr, nen, rfr, ren, afr, aen, qfr, qen, action) in camps.items():
        d = f"Monde_Camp_{kind}"
        check = "CampOpen" if action in ("CampTurnIn", "CampDefend") else None
        write(DIALOGUES / f"{d}.json", dialogue(d, f"{rfr} (étape 4).", nfr, nen, rfr, ren, [
            node("Accueil", say(d, "accueil", afr, aen), [
                resp(say(d, "quete", qfr, qen), action, check=check), rumour, bye]),
        ]))
    d = "Monde_Sortie"
    bye_day = resp(say(d, "aurevoir", "Bonne journée !", "Have a good day!"))
    sortie = dialogue(d, "Villageois en sortie (étape 2) : il dit où il va. world/Surroundings ouvre la fenêtre sur le nœud de son "
                         "travail (gather, fish, wood, herd).", "Villageois", "Villager", "En sortie", "Out and about", [
        node(job, f"nakasar_peuples.world.village.outing.{job}", [bye_day])
        for job in ("gather", "fish", "wood", "herd")])
    sortie["Entries"] = [{"Node": "gather"}]
    write(DIALOGUES / f"{d}.json", sortie)
    d = "Monde_Enfants"
    write(DIALOGUES / f"{d}.json", dialogue(d, "Enfants du village (étape 2) : cache-cache, une fois par jour.", "Enfant", "Child",
                                            "Enfant du village", "Village child", [
        node("Accueil", say(d, "accueil", "Tu joues avec nous ? On se cache, et tu nous cherches !",
                            "Will you play with us? We hide, and you look for us!"), [
            resp(say(d, "jouer", "D'accord, je compte !", "All right, I'm counting!"), "HideAndSeek"),
            resp(say(d, "non", "Une autre fois.", "Another time."))]),
    ]))
    d = "Monde_Fete"
    write(DIALOGUES / f"{d}.json", dialogue(d, "Hôte de la fête des moissons (étape 6) : offrandes de nourriture, réputation doublée.",
                                            "Hôte de la fête", "Festival host", "Fête des moissons", "Harvest festival", [
        node("Accueil", say(d, "accueil", "Les greniers sont pleins, ce soir on fête la moisson ! Chaque offrande compte double.",
                            "The granaries are full, tonight we celebrate the harvest! Every offering counts double."), [
            resp(say(d, "offrir", "J'apporte de quoi manger.", "I bring food."), "FeastOffering"), bye]),
    ]))
    d = "Monde_Foire"
    write(DIALOGUES / f"{d}.json", dialogue(d, "Hôte de la foire (étape 6) : course aux drapeaux.", "Maître de la foire", "Fair master",
                                            "Foire des peuples", "Fair of the peoples", [
        node("Accueil", say(d, "accueil", "Bienvenue à la foire ! Les marchands de tous les peuples sont là. Et la course aux drapeaux t'attend.",
                            "Welcome to the fair! Merchants of every people are here. And the flag race awaits you."), [
            resp(say(d, "course", "Je prends le départ !", "I'm in the race!"), "FairRace"), rumour, bye]),
    ]))


# ---- Trocs ----

def trade(out_id, out_q, in_id, in_q, stock):
    return {"Type": "Fixed", "Trade": {"Output": {"ItemId": out_id, "Quantity": out_q},
                                       "Input": [{"ItemId": in_id, "Quantity": in_q}], "Stock": stock}}


TRAVEL_GOODS = {
    "Kweebec": [("Food_Salad_Berry", 2, 1), ("Ingredient_Tree_Sap", 3, 1), ("Ingredient_Feathers_Light", 4, 1), ("Potion_Health_Small", 1, 2)],
    "Trork": [("Food_Kebab_Meat", 2, 1), ("Ingredient_Leather_Medium", 2, 1), ("Ingredient_Bone_Fragment", 6, 1), ("Ingredient_Hide_Heavy", 1, 2)],
    "Feran": [("Food_Kebab_Fruit", 2, 1), ("Ingredient_Bolt_Cotton", 1, 1), ("Ingredient_Spices", 3, 1), ("Ingredient_Salt", 4, 1)],
    "Renonce": [("Food_Pie_Meat", 1, 1), ("Ingredient_Bolt_Wool", 1, 1), ("Ingredient_Leather_Dark", 2, 1), ("Ingredient_Charcoal", 6, 1)],
    "Slothian": [("Food_Kebab_Vegetable", 2, 1), ("Ingredient_Bolt_Silk", 1, 2), ("Ingredient_Crystal_Green", 2, 1), ("Ingredient_Life_Essence", 4, 1)],
}


def shops():
    for pid, goods in TRAVEL_GOODS.items():
        slots = [trade(item, q, FAVOR[pid], price, 6) for item, q, price in goods]
        slots.append(trade(FAVOR[pid], 1, "Ingredient_Fibre", 12, 4))
        write(RES / f"BarterShops/Nakasar_Peuples_Travel_{pid}.json", {
            "$Comment": f"Troc des voyageurs {pid} (marchand ambulant, caravane, halte de marchands, foire, auberge de niveau 2), "
                        "généré par tools/generate_world_life.py : faveurs du peuple contre marchandises vanilla de sa région.",
            "DisplayNameKey": f"nakasar_peuples.barter.Travel_{pid}.title",
            "RefreshInterval": {"Days": 2},
            "RestockHour": 6,
            "TradeSlots": slots,
        })
        t(f"barter.Travel_{pid}.title", f"Marchandises des voyageurs ({PEOPLES[pid][0]})", f"Travellers' wares ({PEOPLES[pid][1]})")
    write(RES / "BarterShops/Nakasar_Peuples_Inn.json", {
        "$Comment": "Repas de l'auberge de relais (monde vivant, étape 3), généré par tools/generate_world_life.py : on paie en nature.",
        "DisplayNameKey": "nakasar_peuples.barter.Inn.title",
        "RefreshInterval": {"Days": 1},
        "RestockHour": 6,
        "TradeSlots": [
            trade("Food_Pie_Meat", 1, "Food_Wildmeat_Raw", 2, 8),
            trade("Food_Fish_Grilled", 2, "Food_Fish_Raw", 2, 8),
            trade("Food_Bread", 2, "Ingredient_Stick", 8, 8),
            trade("Food_Salad_Mushroom", 1, "Nakasar_Peuples_Favor_Klops", 1, 6),
        ],
    })
    t("barter.Inn.title", "Table de l'auberge", "Inn table")


def items():
    missive = json.loads((RES / "Item/Items/Nakasar/Peuples/Nakasar_Peuples_Missive_Kweebec.json").read_text(encoding="utf-8-sig"))
    letter = copy.deepcopy(missive)
    letter["$Comment"] = ("Lettre d'un messager (monde vivant) : à porter près du cœur du village nommé (drapeau World_Letter:<id>). "
                          "Modèle, texture et icône du parchemin vanilla (Deco_Scroll), comme les missives.")
    letter["TranslationProperties"] = {"Name": "nakasar_peuples.items.Nakasar_Peuples_Letter.name",
                                       "Description": "nakasar_peuples.items.Nakasar_Peuples_Letter.description"}
    letter["MaxStack"] = 1
    write(RES / "Item/Items/Nakasar/Peuples/Nakasar_Peuples_Letter.json", letter)
    t("items.Nakasar_Peuples_Letter.name", "Lettre scellée", "Sealed letter")
    t("items.Nakasar_Peuples_Letter.description", "Une lettre confiée par un messager. Porte-la près du cœur du village qu'il t'a nommé.",
      "A letter handed over by a messenger. Bring it near the heart of the village they named.")


# ---- Évènements de monde ----

EVENTS = {
    # id : (secondes, son, titre fr, titre en, sous-titre fr, sous-titre en, nom fr, nom en, icône)
    "Harvest": (1200, "SFX_Kweebec_Sapling_Alerted", "Fête des moissons", "Harvest festival",
                "Les villageois fêtent la récolte", "The villagers celebrate the harvest", "Fête des moissons", "Harvest festival",
                "UI/WorldMap/MapMarkers/GoblinBreach.png"),
    "Fair": (1800, "SFX_Kweebec_Sapling_Alerted", "Foire des peuples", "Fair of the peoples",
             "Les marchands de tous les peuples sont là", "Merchants of every people are here", "Foire des peuples", "Fair of the peoples",
             "UI/WorldMap/MapMarkers/GoblinBreach.png"),
    "Migration": (1200, None, "Migration", "Migration", "Un troupeau traverse la région", "A herd crosses the land",
                  "Migration d'un troupeau", "Herd migration", "UI/WorldMap/MapMarkers/GoblinBreach.png"),
}


def events():
    for eid, (seconds, sound, tfr, ten, sfr, sen, nfr, nen, icon) in EVENTS.items():
        base = f"Nakasar_Peuples_{eid}"
        key = f"world.event.{eid}."
        write(RES / f"WorldEvent/Event/Nakasar/Peuples/{base}.json", {
            "$Comment": f"{nfr} (monde vivant, étape 6), généré par tools/generate_world_life.py. Lancé par world/Calendar, "
                        "une instance par lieu ; le Java le stoppe à la fin (lieu donné par Nakasar_Peuples_WorldLocation).",
            "Root": f"{base}_Start",
            "IterationCount": 1,
            "InstanceCountMax": -1,
            "Name": f"nakasar_peuples.{key}name",
            "Icon": icon,
        })
        actions = [{"Type": "ShowEventTitleAction", "LocationKey": "WorldLifeLocation", "Radius": 200,
                    "PrimaryTitle": f"nakasar_peuples.{key}title", "SecondaryTitle": f"nakasar_peuples.{key}subtitle",
                    "FadeInDuration": 0.5}]
        write(RES / f"WorldEvent/Stage/Nakasar/Peuples/{base}_Start.json", {
            "$Comment": "Début : le lieu (choisi par le Java), puis le titre à 200 blocs.",
            "Forks": [{
                "Conditions": [
                    {"Type": "Nakasar_Peuples_WorldLocation", "LocationKey": "WorldLifeLocation"},
                    {"Type": "IntervalCondition", "IntervalKey": f"{eid}Start", "MinSeconds": 2, "MaxSeconds": 2},
                ],
                "Actions": actions,
                "Next": f"{base}_Run",
            }],
        })
        write(RES / f"WorldEvent/Stage/Nakasar/Peuples/{base}_Run.json", {
            "$Comment": f"Le rendez-vous : {seconds} s (« … restant » sur la carte, marge de 30 s : le Java le stoppe à la fin).",
            "Forks": [{
                "Conditions": [{"Type": "IntervalCondition", "IntervalKey": f"{eid}Run", "MinSeconds": seconds + 30,
                                "MaxSeconds": seconds + 30, "ShowOnMap": True, "MapIntervalKey": "server.map.worldEvents.runsFor"}],
            }],
        })
        t(key + "name", nfr, nen)
        t(key + "title", tfr, ten)
        t(key + "subtitle", sfr, sen)


# ---- Textes du Java ----

def texts():
    w = "world."
    # Voyageurs
    p = w + "traveller."
    for k, fr, en in (("merchant", "marchand ambulant", "travelling merchant"), ("pilgrim", "pèlerin", "pilgrim"),
                      ("messenger", "messager", "messenger"), ("caravan", "caravane", "caravan")):
        t(p + "kind." + k, fr, en)
    t(p + "line", "{kind} : {from} → {to}, {at}/{length} blocs, {walkers} marcheur(s)", "{kind}: {from} → {to}, {at}/{length} blocks, {walkers} walker(s)")
    t(p + "lost.merchant", "Le marchand ambulant parti pour {to} n'arrivera jamais.", "The travelling merchant bound for {to} will never arrive.")
    t(p + "lost.pilgrim", "Le pèlerin parti pour {to} a été tué en route.", "The pilgrim bound for {to} was killed on the road.")
    t(p + "lost.messenger", "Le messager parti pour {to} a été tué en route.", "The messenger bound for {to} was killed on the road.")
    t(p + "lost.caravan", "La caravane partie pour {to} a été détruite.", "The caravan bound for {to} was destroyed.")
    t(p + "shopRank", "Je ne commerce qu'avec les amis de {village} (rang Toléré).", "I only trade with friends of {village} (rank Tolerated).")
    t(p + "escortStart", "Tu escortes ce voyageur jusqu'à {to}. Reste près de lui jusqu'à l'arrivée.", "You're escorting this traveller to {to}. Stay close until arrival.")
    t(p + "escortDone", "Escorte réussie jusqu'à {to} !", "Escort to {to} complete!")
    t(p + "escortLost", "Tu as laissé le voyageur pour {to} : l'escorte est perdue.", "You left the traveller bound for {to}: the escort is lost.")
    t(p + "escortReason", "escorte d'un voyageur", "escorting a traveller")
    t(p + "letterAlready", "Tu portes déjà une lettre.", "You already carry a letter.")
    t(p + "letterGiven", "Lettre pour {village} ({people}), à {distance} blocs, direction {direction}. Porte-la près du cœur du village.",
      "Letter for {village} ({people}), {distance} blocks away, towards the {direction}. Bring it near the village heart.")
    t(p + "parleyGiven", "Lettre de paix pour {village} ({people}), à {distance} blocs, direction {direction}. Livrée, elle apportera une trêve.",
      "Peace letter for {village} ({people}), {distance} blocks away, towards the {direction}. Delivered, it will bring a truce.")
    t(p + "parleyRank", "Seul un ami de {a} et de {b} (rang Ami dans les deux) peut porter une lettre de paix.",
      "Only a friend of both {a} and {b} (rank Friend in each) can carry a peace letter.")
    t(p + "letterDelivered", "Lettre remise à {village}.", "Letter delivered to {village}.")
    t(p + "letterReason", "lettre d'un messager livrée", "delivered a messenger's letter")
    t(p + "ambushedAway", "Une caravane de {from} a été pillée en route : il manque une part de la cargaison.",
      "A caravan from {from} was plundered on the way: part of its cargo is missing.")
    # Embuscades
    p = w + "ambush."
    t(p + "start", "Embuscade ! Des pillards surgissent sur la route.", "Ambush! Raiders spring onto the road.")
    t(p + "won", "Les pillards sont repoussés, la route est libre.", "The raiders are driven off, the road is clear.")
    # Vie autour du village
    p = w + "village."
    t(p + "outing.gather", "Je vais cueillir des fibres à l'orée du village.", "I'm off to gather fibre at the edge of the village.")
    t(p + "outing.fish", "Je vais pêcher un peu plus loin.", "I'm going fishing a little further on.")
    t(p + "outing.wood", "Je vais ramasser du bois.", "I'm going to fetch wood.")
    t(p + "outing.herd", "Je vais voir les bêtes et ramasser les œufs.", "I'm going to check on the animals and gather eggs.")
    t(p + "monster", "Un villageois de {village} est attaqué hors du village !", "A villager of {village} is attacked outside the village!")
    t(p + "hideBusy", "Les enfants sont déjà en train de jouer.", "The children are already playing.")
    t(p + "hideTired", "On a assez joué pour aujourd'hui !", "We've played enough for today!")
    t(p + "hideStart", "Les enfants se cachent ! Trouve-les tous les {count} en {seconds} s.", "The children hide! Find all {count} in {seconds} s.")
    t(p + "hideFound", "Trouvé ! ({found}/{total})", "Found! ({found}/{total})")
    t(p + "hideWon", "Tous trouvés ! Les enfants rient et te tendent un cadeau.", "All found! The children laugh and give you a present.")
    t(p + "hideLost", "Le temps est écoulé : les enfants ont gagné !", "Time's up: the children win!")
    t(p + "hideReason", "joué à cache-cache avec les enfants", "played hide-and-seek with the children")
    # Traces
    p = w + "trace."
    lore = {
        "ruin": ("Ruines anciennes", "Ancient ruins", [
            ("Des pierres taillées par un peuple oublié. Les anciens de {village} disent qu'une cité se dressait ici avant les leurs.",
             "Stones cut by a forgotten people. The elders of {village} say a city stood here before theirs."),
            ("Un mur à demi enfoui, gravé de signes que personne ne sait plus lire.", "A half-buried wall, carved with signs no one can read anymore."),
            ("La mousse a tout recouvert. Seul un seuil usé rappelle que des gens passaient par là.",
             "Moss has covered everything. Only a worn threshold recalls that people once passed here.")]),
        "oldcamp": ("Vieux campement", "Old camp", [
            ("Les cendres d'un feu, des piquets de tente : des voyageurs ont dormi ici il y a longtemps.",
             "Ashes of a fire, tent pegs: travellers slept here long ago."),
            ("Un campement abandonné en hâte. Qu'est-ce qui les a fait fuir ?", "A camp abandoned in haste. What made them flee?"),
            ("Les chasseurs de {village} s'arrêtaient ici, avant que la route ne change.", "The hunters of {village} stopped here, before the road changed.")]),
        "shrine": ("Autel oublié", "Forgotten shrine", [
            ("Un petit autel où l'on déposait des offrandes pour les voyageurs.", "A small shrine where offerings were left for travellers."),
            ("Les moines de {village} y venaient prier, dit-on.", "The monks of {village} came here to pray, they say."),
            ("La pierre est encore tiède, comme si quelqu'un venait de partir.", "The stone is still warm, as if someone just left.")]),
        "raid": ("Arbres brûlés", "Burnt trees", [
            ("Ici, la nuit du raid sur {village}, le feu a pris aux arbres. Les habitants ne l'oublieront pas.",
             "Here, on the night of the raid on {village}, fire caught the trees. The villagers won't forget it."),
            ("Les troncs noircis gardent la trace des assaillants venus brûler {village}.",
             "The blackened trunks bear the mark of the attackers who came to burn {village}."),
            ("On a reconstruit {village}, mais ces arbres restent morts, en souvenir.", "{village} was rebuilt, but these trees stay dead, in memory.")]),
    }
    for kind, (tfr, ten, notes) in lore.items():
        t(p + kind + ".title", tfr, ten)
        for i, (fr, en) in enumerate(notes, 1):
            t(p + f"{kind}.{i}", fr, en)
    # Auberges
    p = w + "inn."
    t(p + "works", "Le passage entre {a} et {b} est tel qu'une auberge de relais se construit à mi-chemin.",
      "So many pass between {a} and {b} that a relay inn is being built halfway.")
    t(p + "opened", "L'auberge de relais entre {a} et {b} ouvre ses portes.", "The relay inn between {a} and {b} opens its doors.")
    t(p + "level.2", "L'auberge entre {a} et {b} devient une vraie auberge : les voyageurs y laissent leurs marchandises.",
      "The inn between {a} and {b} becomes a true inn: travellers leave their wares there.")
    t(p + "level.3", "L'auberge entre {a} et {b} est devenue un grand relais : nouvelles et courrier de toute la région.",
      "The inn between {a} and {b} is now a great relay: news and mail from all around.")
    t(p + "closed", "Plus personne ne passe entre {a} et {b} : l'aubergiste a fermé.", "No one travels between {a} and {b} anymore: the innkeeper has closed.")
    # Campements
    p = w + "camp."
    types = {"hunters": ("campement de chasseurs", "hunters' camp"), "woodcutters": ("campement de bûcherons", "woodcutters' camp"),
             "prospectors": ("campement de prospecteurs", "prospectors' camp"), "merchants": ("halte de marchands", "merchants' halt"),
             "refugees": ("campement de réfugiés", "refugee camp")}
    for k, (fr, en) in types.items():
        t(p + "type." + k, fr, en)
        t(p + "gone." + k, f"Le {fr} près de {{village}} est levé." if not fr.startswith("halte") else f"La {fr} près de {{village}} est levée.",
          f"The {en} near {{village}} has packed up.")
        if k != "refugees":
            t(p + "new." + k, (f"Un {fr}" if not fr.startswith("halte") else f"Une {fr}") + " s'est installé à {distance} blocs, direction {direction}."
              .replace("installé", "installée" if fr.startswith("halte") else "installé"),
              f"A {en} has set up {{distance}} blocks away, towards the {{direction}}.")
    t(p + "refugees", "Les habitants du bâtiment brûlé de {village} campent au bord du village en attendant qu'il soit relevé.",
      "The people of {village}'s burned building camp at the village edge until it's rebuilt.")
    t(p + "already", "Tu nous as déjà aidés, merci encore.", "You've already helped us, thanks again.")
    t(p + "missing", "Il en faut {count} : {item}.", "We need {count}: {item}.")
    t(p + "thanks", "Merci, voilà pour toi.", "Thank you, this is for you.")
    t(p + "reason", "aidé un campement", "helped a camp")
    t(p + "underAttack", "Ils sont déjà là, défends-nous !", "They're already here, defend us!")
    t(p + "attack", "Des pillards attaquent le campement !", "Raiders attack the camp!")
    t(p + "defended", "Le campement est sauf : voici ta part du minerai.", "The camp is safe: here's your share of the ore.")
    t(p + "noFood", "Tu n'as rien à manger à donner.", "You have no food to give.")
    t(p + "donated", "Tu donnes {count} vivres aux réfugiés de {village}.", "You give {count} food to the refugees of {village}.")
    t(p + "donationReason", "nourri les réfugiés", "fed the refugees")
    t(p + "donatedEnough", "Tu as déjà beaucoup donné aujourd'hui : reviens demain.", "You've already given a lot today: come back tomorrow.")
    # Relations
    p = w + "relation."
    for k, fr, en in (("ally", "alliés", "allies"), ("friendly", "en bons termes", "on good terms"), ("neutral", "neutres", "neutral"),
                      ("tense", "en froid", "at odds"), ("rival", "rivaux", "rivals")):
        t(p + "state." + k, fr, en)
    t(p + "truce", "Trêve de {days} jours entre {a} et {b} !", "A {days}-day truce between {a} and {b}!")
    t(p + "quarrel", "Querelle entre {a} et {b} : les relations se tendent.", "A quarrel between {a} and {b}: relations grow tense.")
    t(p + "skirmish", "Escarmouche entre {a} et {b} sur la route !", "A skirmish between {a} and {b} on the road!")
    t(p + "skirmishAway", "On raconte qu'une escarmouche a opposé {winner} et {loser} : {winner} l'a emporté.",
      "Word is that {winner} and {loser} clashed: {winner} won.")
    t(p + "skirmishDraw", "L'escarmouche s'achève sans vainqueur.", "The skirmish ends with no winner.")
    t(p + "skirmishWon", "{winner} remporte l'escarmouche.", "{winner} wins the skirmish.")
    t(p + "skirmishReason", "présent lors de la victoire d'une escarmouche", "present at a skirmish victory")
    # Calendrier
    p = w + "calendar."
    t(p + "feast.start", "Fête des moissons à {village} ! L'hôte de la fête attend les offrandes.", "Harvest festival in {village}! The host awaits offerings.")
    t(p + "feast.over", "La fête est finie.", "The festival is over.")
    t(p + "feast.reason", "offrande à la fête des moissons", "offering at the harvest festival")
    t(p + "feast.thanks", "Merci pour ces {count} offrandes !", "Thank you for these {count} offerings!")
    t(p + "feast.enough", "Tu as déjà fait tes offrandes à cette fête.", "You've already made your offerings at this festival.")
    t(p + "feast.end", "La fête des moissons de {village} s'achève.", "The harvest festival of {village} ends.")
    t(p + "fair.start", "La foire des peuples s'ouvre à {village} !", "The fair of the peoples opens in {village}!")
    t(p + "fair.over", "La foire est finie.", "The fair is over.")
    t(p + "fair.end", "La foire de {village} ferme ses étals.", "The fair of {village} closes its stalls.")
    t(p + "race.already", "Tu as déjà couru à cette foire.", "You've already run at this fair.")
    t(p + "race.flag", "Drapeau {n} : à {distance} blocs, direction {direction}.", "Flag {n}: {distance} blocks away, towards the {direction}.")
    t(p + "race.start", "Partez ! Touche les {count} drapeaux en {seconds} s.", "Go! Touch all {count} flags in {seconds} s.")
    t(p + "race.found", "Drapeau ! ({found}/{total})", "Flag! ({found}/{total})")
    t(p + "race.won", "Victoire ! La foule t'acclame.", "Victory! The crowd cheers.")
    t(p + "race.lost", "Trop tard, la course est perdue.", "Too late, the race is lost.")
    t(p + "race.reason", "course de la foire gagnée", "won the fair race")
    t(p + "migration.start", "Un troupeau migre près de {village}, venant du {direction}. Attention aux charges !",
      "A herd migrates near {village}, coming from the {direction}. Beware of charges!")
    # Rumeurs
    p = w + "rumour."
    for k, fr, en in (("merchant", "Un marchand ambulant va de {from} à {to}.", "A travelling merchant is heading from {from} to {to}."),
                      ("pilgrim", "Un pèlerin marche de {from} vers {to}.", "A pilgrim walks from {from} to {to}."),
                      ("messenger", "Un messager porte des nouvelles de {from} à {to}.", "A messenger carries news from {from} to {to}."),
                      ("caravan", "Une caravane de {from} est en route vers {to}.", "A caravan from {from} is on its way to {to}.")):
        t(p + "traveller." + k, fr, en)
    for k, (fr, en) in types.items():
        t(p + "camp." + k, ("Une " if fr.startswith("halte") else "Un ") + fr + " s'est installé au {direction} de {village}."
          .replace("installé", "installée" if fr.startswith("halte") else "installé"), f"A {en} has set up to the {{direction}} of {{village}}.")
    for k, fr, en in (("ally", "{a} et {b} sont alliés : leurs caravanes vont et viennent.", "{a} and {b} are allies: their caravans come and go."),
                      ("friendly", "{a} et {b} s'entendent bien.", "{a} and {b} get along well."),
                      ("tense", "Ça se tend entre {a} et {b}.", "Things are tense between {a} and {b}."),
                      ("rival", "{a} et {b} sont rivaux : gare aux escarmouches sur la route.", "{a} and {b} are rivals: beware of skirmishes on the road.")):
        t(p + "relation." + k, fr, en)
    t(p + "inn", "Une auberge accueille les voyageurs entre {a} et {b}.", "An inn welcomes travellers between {a} and {b}.")
    t(p + "fair", "La prochaine foire se tiendra à {village} dans {days} jour(s).", "The next fair will be held in {village} in {days} day(s).")
    t(p + "trace", "On dit que des vestiges anciens se cachent à {distance} blocs d'ici, direction {direction}.",
      "They say ancient remains lie {distance} blocks from here, towards the {direction}.")
    t(p + "none", "Rien de neuf sur les routes.", "Nothing new on the roads.")
    # Commande
    p = w + "command."
    t(p + "desc", "Monde vivant entre les villages", "Living world between villages")
    t(p + "noVillage", "Aucun village à moins de {range} blocs.", "No village within {range} blocks.")
    t(p + "noLink", "{village} n'a aucun voisin à moins de {max} blocs.", "{village} has no neighbour within {max} blocks.")
    t(p + "noSuchVillage", "Aucun village ne s'appelle « {name} ».", "No village is called \"{name}\".")
    t(p + "noLinkTo", "{village} et {to} sont à plus de {max} blocs l'un de l'autre.",
      "{village} and {to} are more than {max} blocks apart.")
    t(p + "to.arg", "village d'arrivée (nom ou id) ; sinon le voisin le plus proche",
      "destination village (name or id); otherwise the nearest neighbour")
    t(p + "state.desc", "État du monde vivant (voyageurs, campements, auberges, relations, calendrier)",
      "Living world state (travellers, camps, inns, relations, calendar)")
    t(p + "state.header", "Monde vivant : {npcs} PNJ, {links} liaison(s), {structures} structure(s) temporaire(s).",
      "Living world: {npcs} NPCs, {links} link(s), {structures} temporary structure(s).")
    t(p + "state.camp", "Campement : {type} près de {village} ({x}, {z})", "Camp: {type} near {village} ({x}, {z})")
    t(p + "state.inn", "Auberge {link} : niveau {level}, ouverte {open} ({x}, {z})", "Inn {link}: level {level}, open {open} ({x}, {z})")
    t(p + "state.link", "{a} – {b} : {length} blocs, relation {relation} ({state}), {traffic} passage(s) en 7 jours",
      "{a} – {b}: {length} blocks, relation {relation} ({state}), {traffic} passage(s) in 7 days")
    t(p + "state.calendar", "Fête dans {feast} j, foire dans {fair} j, migration dans {migration} j. En cours : {running}",
      "Festival in {feast} d, fair in {fair} d, migration in {migration} d. Running: {running}")
    t(p + "traveller.arg", "marchand, pelerin, messager ou caravane", "marchand, pelerin, messager or caravane")
    t(p + "traveller.desc", "Fait partir un voyageur du village le plus proche (ops)", "Send a traveller from the nearest village (ops)")
    t(p + "traveller.done", "{kind} en route vers {to}.", "{kind} on the way to {to}.")
    t(p + "ambush.desc", "Embuscade sur le voyageur le plus proche (ops)", "Ambush the nearest traveller (ops)")
    t(p + "ambush.none", "Aucun voyageur à moins de {range} blocs.", "No traveller within {range} blocks.")
    t(p + "camp.arg", "chasseurs, bucherons, prospecteurs, marchands ou refugies", "chasseurs, bucherons, prospecteurs, marchands or refugies")
    t(p + "camp.desc", "Installe un campement près du village le plus proche (ops)", "Set up a camp near the nearest village (ops)")
    t(p + "camp.done", "Campement installé en {x}, {z}.", "Camp set up at {x}, {z}.")
    t(p + "camp.noRoom", "Pas de place pour un campement.", "No room for a camp.")
    t(p + "inn.desc", "Construit tout de suite l'auberge de la liaison la plus courte du village le plus proche (ops)",
      "Build right away the inn of the nearest village's shortest link (ops)")
    t(p + "inn.done", "Auberge prête en {x}, {z} : elle se pose à ton approche.", "Inn ready at {x}, {z}: it appears as you approach.")
    t(p + "relation.arg", "valeur de -100 à 100", "value from -100 to 100")
    t(p + "relation.desc", "Lit ou fixe la relation entre le village le plus proche et son voisin (ops)",
      "Read or set the relation between the nearest village and its neighbour (ops)")
    t(p + "relation.done", "{a} – {b} : {value} ({state}).", "{a} – {b}: {value} ({state}).")
    t(p + "skirmish.desc", "Escarmouche tout de suite entre le village le plus proche et son voisin (ops)",
      "Start a skirmish now between the nearest village and its neighbour (ops)")
    t(p + "calendar.fete.desc", "Lance la fête des moissons (ops)", "Start the harvest festival (ops)")
    t(p + "calendar.foire.desc", "Lance la foire (ops)", "Start the fair (ops)")
    t(p + "calendar.migration.desc", "Lance une migration (ops)", "Start a migration (ops)")
    t(p + "calendar.arret.desc", "Arrête la fête, la foire et la migration en cours (ops)", "Stop the running festival, fair and migration (ops)")
    t(p + "calendar.feast", "Fête des moissons dans {count} village(s).", "Harvest festival in {count} village(s).")
    t(p + "calendar.fair", "Foire à {village}.", "Fair in {village}.")
    t(p + "calendar.noFair", "Aucun village de palier 2 ou plus pour accueillir la foire.", "No tier 2+ village to host the fair.")
    t(p + "calendar.migration", "Un troupeau migre près de {village}.", "A herd migrates near {village}.")
    t(p + "calendar.noMigration", "Une migration est déjà en cours.", "A migration is already under way.")
    t(p + "calendar.stopped", "Rendez-vous arrêtés.", "Gatherings stopped.")


def write_langs():
    for locale, table in (("fr-FR", FR), ("en-US", EN)):
        path = RES / f"Languages/{locale}/nakasar_peuples.lang"
        text = path.read_text(encoding="utf-8")
        if LANG_BEGIN in text:
            before, rest = text.split(LANG_BEGIN, 1)
            text = before + rest.split(LANG_END, 1)[1].lstrip("\n")
        existing = {line.split("=", 1)[0].strip() for line in text.splitlines() if "=" in line and not line.startswith("#")}
        dup = sorted(k for k in table if k in existing)
        if dup:
            raise SystemExit(f"clés déjà présentes dans {locale} (hors bloc du monde vivant) : {dup[:10]}")
        block = [LANG_BEGIN] + [f"{k} = {v}" for k, v in table.items()] + [LANG_END, ""]
        path.write_text("\n".join(block) + text, encoding="utf-8")
        print(f"{path.relative_to(ROOT)} : {len(table)} clés du monde vivant")


def main():
    roles()
    herds()
    models()
    dialogues()
    shops()
    items()
    events()
    texts()
    write_langs()


if __name__ == "__main__":
    main()
