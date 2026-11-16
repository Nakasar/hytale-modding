#!/usr/bin/env python3
"""Camp trork, Peinture de guerre et Klops errant du mod Peuples d'Orbis (étape 7 du plan d'implémentation).

GDD, Progression des zones (zone 1) : deux routes. Les Kweebecs (village, étapes 2 à 6) ou le camp trork, qui commence
hostile, s'apprivoise par la viande (comportement vanilla Dropped_Meat des Trorks), puis par ses demandes et la
chaîne de son chef, jusqu'à la Peinture de guerre. Aider l'un coûte auprès de l'autre (réputations croisées, Java).
Les Klops errants passent de village en village, troquent et confient des colis.

Règle n° 2 d'AGENTS.md : tout réemploie des assets vanilla (modèles de Trorks et de Klops, prefabs Npc/Trork, objets
vanilla pour la faveur trork, la peinture, le rouage et le colis).

Écrit (src/main/resources/Server) :
  * objets : tableau, bannière (marqueur de carte), dent de trophée (faveur trork), Peinture de guerre, rouage klops,
    colis ; l'interaction de la peinture et son effet (teinte ocre, icône) ;
  * PNJ : groupe de réputation Nakasar_Peuples_Trork (groupe vanilla Trork, départ -250 = Honni), crieur, marchand et
    chef trorks, Klops errant ;
  * dialogues : Trork_Crieur, Trork_Marchand, Trork_Chef (chaîne), Klops_Errant ;
  * demandes du tableau trork et de la chaîne ; échoppes trorks et klops ;
  * les traductions fr-FR et en-US (ajoutées aux .lang si la clé manque). Les titres de demande tiennent dans le suivi
    du HUD : {TITLE_MAX} caractères au plus (règle de Kevin, 14 novembre 2026).

    python3 tools/generate_trorks.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "src/main/resources/Server"
ITEMS = RES / "Item/Items/Nakasar/Peuples"
ROLES = RES / "NPC/Roles/Nakasar/Peuples"
DIALOGUES = RES / "Nakasar/Dialogues"
REQUESTS = RES / "Nakasar/Requests/Trork"
SHOPS = RES / "BarterShops"
LANGS = RES / "Languages"

P = "Trork"
PFX = "Nakasar_Peuples_"
FAVOR = PFX + "Favor_Trork"
FAVOR_K = PFX + "Favor_Kweebec"
COG = PFX + "Favor_Klops"
PARCEL = PFX + "Klops_Parcel"
PAINT = PFX + "War_Paint"
MEAT = "Food_Wildmeat_Raw"
TITLE_MAX = 24
INITIAL = -250

FR = {}
EN = {}


def tr(key, fr, en):
    FR[key] = fr
    EN[key] = en
    return "nakasar_peuples." + key


def write(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(path.relative_to(ROOT))


# ---------------------------------------------------------------- Objets

def unbreakable():
    return {"Gathering": {"Breaking": {"GatherType": "Unbreakable"}}}


def item_names(iid, fr, en, fr_desc, en_desc):
    return {"Name": tr(f"items.{iid}.name", fr, en), "Description": tr(f"items.{iid}.description", fr_desc, en_desc)}


def items():
    write(ITEMS / f"{PFX}Board_Trork.json", {
        "$Comment": "Tableau d'un camp trork (étape 7) : le panneau grossier vanilla (Furniture_Crude_Sign) dont l'utilisation "
                    "ouvre le tableau du camp (interaction Java Nakasar_Peuples_OpenBoard). tools/generate_trorks.py.",
        "Parent": "Furniture_Crude_Sign",
        "TranslationProperties": item_names(f"{PFX}Board_Trork", "Tableau du camp", "Camp board",
                                            "Les demandes du camp, griffées dans le bois.", "The camp's requests, scratched into the wood."),
        "Quality": "Developer",
        "BlockType": {**unbreakable(), "Interactions": {"Use": {"Interactions": ["Nakasar_Peuples_Open_Board"]}}},
    })
    write(ITEMS / f"{PFX}Banner_Trork.json", {
        "$Comment": "Bannière d'un camp trork (étape 7) : les crânes vanilla (Deco_Bone_Skulls) posés au nord de la place, "
                    "qui portent le marqueur de carte du camp (découvrable). Icônes : tools/generate_map_icons.py.",
        "Parent": "Deco_Bone_Skulls",
        "TranslationProperties": item_names(f"{PFX}Banner_Trork", "Crânes du camp", "Camp skulls",
                                            "Les Trorks marquent ainsi leur territoire.", "This is how Trorks mark their ground."),
        "Quality": "Developer",
        "BlockType": {**unbreakable(), "BlockEntity": {"Components": {"BlockMapMarker": {
            "Name": tr("marker.Trork", "Camp trork", "Trork camp"),
            "Icon": "Nakasar_Peuples_Trork.png", "CompassIcon": "Nakasar_Peuples_TrorkCompass.png", "Discoverable": True}}}},
    })

    def simple(iid, comment, names, icon, model, texture, quality, sound, extra=None):
        doc = {"$Comment": comment, "TranslationProperties": item_names(iid, *names), "Icon": icon,
               "Categories": ["Items.Ingredients"], "Model": model, "Texture": texture, "PlayerAnimationsId": "Item",
               "Quality": quality, "ItemSoundSetId": sound, "DropOnDeath": True}
        doc.update(extra or {})
        write(ITEMS / f"{iid}.json", doc)

    simple(FAVOR, "Dent de trophée : la faveur des Trorks (étape 7), donnée par les demandes du camp, dépensée chez leur "
                  "marchand. Modèle, texture et icône du fragment d'os vanilla (Ingredient_Bone_Fragment).",
           ("Dent de trophée", "Trophy tooth", "La faveur des Trorks : un Trork ne la donne qu'à qui a mérité son respect.",
            "The Trorks' favour: a Trork only gives it to someone who earned their respect."),
           "Icons/ItemsGenerated/Ingredient_Bone_Fragment.png", "Resources/Materials/Bone_Fragment.blockymodel",
           "Resources/Materials/Bone_Fragment_Texture.png", "Uncommon", "ISS_Items_Bones")
    simple(COG, "Rouage klops (étape 7) : la monnaie du Klops errant, gagnée en livrant ses colis ou en troquant des faveurs. "
                "Modèle, texture et icône du tas de ferraille brillant vanilla (Deco_Scrap_Pile_Shiny).",
           ("Rouage klops", "Klops cog", "Les Klops comptent en rouages. Leur marchand errant les accepte partout.",
            "Klops count in cogs. Their wandering trader takes them anywhere."),
           "Icons/ItemsGenerated/Deco_Scrap_Pile_Shiny.png", "Blocks/Dungeons/Scrap_Pile_Shiny.blockymodel",
           "Blocks/Dungeons/Scrap_Pile_Shiny.png", "Uncommon", "ISS_Items_Metal")
    simple(PARCEL, "Colis du Klops errant (étape 7) : à porter jusqu'au cœur du village qu'il a nommé (drapeau Klops_Parcel:<id>). "
                   "Modèle, texture et icône du rouleau de lin vanilla (Ingredient_Bolt_Linen).",
           ("Colis du Klops", "Klops parcel", "Un paquet ficelé. Le Klops a dit pour qui : /village klops pour s'en souvenir.",
            "A tied-up bundle. The Klops said who it is for: /village klops to remember."),
           "Icons/ItemsGenerated/Ingredient_Bolt_Linen.png", "Resources/Materials/Cotton_Bolt.blockymodel",
           "Resources/Materials/Cotton_Bolt_Textures/Linen_Texture.png", "Common", "ISS_Items_Cloth", {"MaxStack": 1})
    simple(PAINT, "Peinture de guerre (étape 7) : objet de passage de la route trork, donné par le chef au champion de son "
                  "peuple. Clic secondaire : mettre ou ôter la peinture (Java Nakasar_Peuples_WarPaint, non consommée). "
                  "Modèle et icône de la petite potion rouge vanilla.",
           ("Peinture de guerre", "War paint", "Ocre et sang. Peint, les Trorks te laissent passer ; les Kweebecs te regardent de travers.",
            "Ochre and blood. Painted, Trorks let you pass; Kweebecs look at you askance."),
           "Icons/ItemsGenerated/Potion_Health_Small.png", "Items/Consumables/Potions/Potion_Small.blockymodel",
           "Items/Consumables/Potions/Potion_Textures/Red.png", "Epic", "ISS_Items_Potion",
           {"MaxStack": 1, "Interactions": {"Secondary": "Root_Nakasar_Peuples_War_Paint"}})
    write(RES / "Item/Interactions/Nakasar/Peuples/Nakasar_Peuples_War_Paint_Use.json", {
        "$Comment": "Met ou ôte la Peinture de guerre (Java trork/WarPaint).", "Type": "Nakasar_Peuples_WarPaint"})
    write(RES / "Item/RootInteractions/Nakasar/Peuples/Root_Nakasar_Peuples_War_Paint.json", {
        "Interactions": ["Nakasar_Peuples_War_Paint_Use"], "RequireNewClick": True})
    write(RES / "Entity/Effects/Nakasar/Peuples/Nakasar_Peuples_War_Paint.json", {
        "$Comment": "Peinture de guerre portée (étape 7) : teinte ocre rouge et icône, posée et retirée par le Java "
                    "(trork/WarPaintSystem suit le drapeau Trork_War_Paint du joueur). Aucun effet de stat.",
        "Name": tr("effects.Nakasar_Peuples_War_Paint", "Peinture de guerre", "War paint"),
        "StatusEffectIcon": "Icons/ItemsGenerated/Potion_Health_Small.png",
        "Debuff": False,
        "ApplicationEffects": {"EntityTopTint": "#b8452a", "EntityBottomTint": "#5a1a0c"},
        "OverlapBehavior": "Overwrite",
        "Infinite": True,
    })


# ---------------------------------------------------------------- PNJ

def role(rid, appearance, comment, name_fr, name_en, hint="nakasar_peuples.hint.talk"):
    write(ROLES / f"{rid}.json", {
        "$Comment": comment,
        "Type": "Generic",
        "Appearance": appearance,
        "NameTranslationKey": tr(f"npc.{rid.removeprefix(PFX)}.name", name_fr, name_en),
        "MaxHealth": 100,
        "StartState": "Idle",
        "DefaultPlayerAttitude": "Neutral",
        "DefaultNPCAttitude": "Ignore",
        "MotionControllerList": [{"Type": "Walk", "MaxWalkSpeed": 0.1, "Gravity": 10, "MaxFallSpeed": 10,
                                  "Acceleration": 10, "JumpHeight": 1.0}],
        "KnockbackScale": 0,
        "Instructions": [{"Sensor": {"Type": "State", "State": "Idle"}, "Instructions": [{"Actions": []}]}],
        "InteractionInstruction": {"Instructions": [
            {"Continue": True, "Sensor": {"Type": "Any"},
             "Actions": [{"Type": "SetInteractable", "Interactable": True, "Hint": hint}]},
            {"Sensor": {"Type": "HasInteracted"}, "Actions": []}]},
    })


def npcs():
    write(RES / "NPC/Reputation/Groups/Nakasar_Peuples_Trork.json", {
        "$Comment": "Réputation de peuple des Trorks (étape 7) : tous les Trorks vanilla et ceux du mod (groupe PNJ vanilla "
                    "Trork = rôles *Trork*). Un joueur commence Honni (-250, comme People.initialReputation) : les Trorks "
                    "l'attaquent. Les pillards des raids restent hostiles quoi qu'il arrive (raid/RaidAttitudeSystem).",
        "NPCGroups": ["Trork"],
        "InitialReputationValue": INITIAL,
    })
    common = "Posé par Criers (Java) quand un joueur approche du camp, immobile. Tué, il revient au matin suivant. " \
             "Régénération vanilla hors combat (PNJ amical). Groupe vanilla Trork : il suit le rang du joueur au camp."
    role(PFX + "Trork_Crier", "Trork_Sentry", "Le crieur d'un camp trork (étape 7), deux blocs au sud du tableau. " + common,
         "Crieur trork", "Trork crier")
    role(PFX + "Trork_Merchant", "Trork_Doctor_Witch", "La marchande d'un camp trork (étape 7), au sud du dépôt. " + common,
         "Marchande trork", "Trork trader", "server.interactionHints.trade")
    role(PFX + "Trork_Chief", "Trork_Chieftain", "Le chef d'un camp trork (étape 7), à l'est du cœur : la chaîne trork, "
         "jusqu'à la Peinture de guerre. " + common, "Chef trork", "Trork chief")
    role(PFX + "Klops_Wanderer", "Klops_Merchant", "Le Klops errant (étape 7) : posé par klops/Klops à l'ouest du cœur du "
         "village de sa tournée du jour, quand un joueur approche. N'est d'aucun peuple. Dialogue Klops_Errant.",
         "Klops errant", "Wandering Klops", "server.interactionHints.trade")


# ---------------------------------------------------------------- Dialogues

def dlg(did, people, comment, npc_fr, npc_en, role_fr, role_en, entries, nodes):
    k = f"dialogue.{did}."
    return {
        "$Comment": comment,
        "NpcNameKey": tr(k + "npc", npc_fr, npc_en),
        "RoleKey": tr(k + "role", role_fr, role_en),
        **({"People": people} if people else {}),
        "Entries": entries,
        "Nodes": nodes,
    }


def node(did, nid, key, fr, en, responses):
    return {"Id": nid, "TextKey": tr(f"dialogue.{did}.{key}", fr, en), "Responses": responses}


def resp(did, key, fr, en, **extra):
    r = {"TextKey": tr(f"dialogue.{did}.{key}", fr, en)}
    r.update(extra)
    return r


def in_camp():
    return {"Conditions": [{"Type": "InVillage", "People": P}], "FailKey": "nakasar_peuples.dialogue.fail.inVillage"}


def rank(r):
    return [{"Type": "Rank", "Min": r}]


def offer_meat(did, nxt):
    """Route de la viande, aussi par le dialogue : 5 viandes crues contre de la réputation, jusqu'à Toléré."""
    return resp(did, "offrirViande", "Tiens, de la viande. (5 Viande crue)", "Here, meat. (5 Raw meat)",
                HintKey=tr("dialogue.hint.meat", "+40 réputation au camp, jusqu'à Toléré", "+40 camp reputation, up to Tolerated"),
                Conditions=[{"Type": "HasItem", "ItemId": MEAT, "Quantity": 5}, {"Type": "InVillage", "People": P}],
                FailKey=tr(f"dialogue.{did}.failViande", "il faut 5 Viande crue sur toi, au camp", "you need 5 Raw meat, at the camp"),
                Effects=[{"Type": "TakeItem", "ItemId": MEAT, "Quantity": 5}, {"Type": "AddReputation", "Amount": 40}],
                Next=nxt)


def crier():
    d = "Trork_Crieur"
    see = lambda key, fr, en: resp(d, key, fr, en, HintKey="nakasar_peuples.dialogue.hint.openRequests",
                                   Effects=[{"Type": "OpenRequests"}], **in_camp())
    bye = resp(d, "aurevoir", "Je file.", "I'm off.")
    doc = dlg(d, P, "Le crieur trork (étape 7), près du tableau du camp. Honni : il grogne, prend la viande, et laisse "
                    "prendre une demande pour se racheter. Généré par tools/generate_trorks.py.",
              "Gueule-Fort", "Loud-Maw", "Crieur du camp", "Camp crier",
              [{"Node": "Honni", "Conditions": [{"Type": "Rank", "Max": "Honni"}]},
               {"Node": "EnCours", "Conditions": [{"Type": "HasRequest"}]},
               {"Node": "Accueil"}],
              [node(d, "Honni", "honni", "GRRR. Toi pas Trork. Toi viande, ou toi partir. Ou toi faire travail, peut-être.",
                    "GRRR. You no Trork. You meat, or you leave. Or you do work, maybe.",
                    [offer_meat(d, "Mange"), see("travail", "Donne-moi du travail.", "Give me work."), bye]),
               node(d, "Mange", "mange", "*mâche bruyamment* ... Bon. Toi moins puant.", "*chews loudly* ... Good. You smell less.",
                    [see("travail", "Donne-moi du travail.", "Give me work."), bye]),
               node(d, "Accueil", "accueil", "Le camp a faim et froid. Le tableau dit quoi faire. Toi faire, camp content.",
                    "Camp is hungry and cold. Board says what to do. You do, camp happy.",
                    [see("voir", "Montre-moi les demandes.", "Show me the requests."), offer_meat(d, "Mange"), bye]),
               node(d, "EnCours", "encours", "Alors ? Toi ramener ?", "So? You bring?",
                    [resp(d, "rendre", "Voilà ce que j'ai.", "Here's what I have.", HintKey="nakasar_peuples.dialogue.hint.turnIn",
                          Effects=[{"Type": "TurnInRequests"}], Next="Rendu", **in_camp()),
                     see("voir", "Montre-moi les demandes.", "Show me the requests."), bye]),
               node(d, "Rendu", "rendu", "Hmpf. Bon travail. Chef saura.", "Hmph. Good work. Chief will know.",
                    [see("voir", "Montre-moi les demandes.", "Show me the requests."), bye])])
    write(DIALOGUES / P / f"{d}.json", doc)


def merchant():
    d = "Trork_Marchand"
    shops = [("troc", "Montre ta camelote.", "Show your junk.", "Tolere"),
             ("armes", "Des armes trorks ?", "Trork weapons?", "Ami"),
             ("armure", "La réserve du chef.", "The chief's stash.", "Hote")]

    def trade(key, fr, en, r):
        return resp(d, key, fr, en, HintKey=f"nakasar_peuples.dialogue.hint.shop.{r}", Conditions=rank(r),
                    FailKey=f"nakasar_peuples.dialogue.fail.rank.{r}", Effects=[{"Type": "OpenShop", "Shop": f"{PFX}Trork_{r}"}])

    bye = resp(d, "aurevoir", "À plus.", "Later.")
    trades = [trade(*s) for s in shops]
    doc = dlg(d, P, "La marchande trork (étape 7) : troc par rang contre des dents de trophée, échoppes grisées sous le "
                    "rang. Généré par tools/generate_trorks.py.",
              "Mère-Os", "Bone-Mother", "Marchande du camp", "Camp trader",
              [{"Node": "Honni", "Conditions": [{"Type": "Rank", "Max": "Honni"}]},
               {"Node": "Etranger", "Conditions": [{"Type": "Rank", "Max": "Etranger"}]},
               {"Node": "Accueil"}],
              [node(d, "Honni", "honni", "Hssss. Pas de troc avec la viande.", "Hssss. No trade with meat.", [bye]),
               node(d, "Etranger", "etranger", "Toi rien prouvé. Rapporte des dents de trophée, après on parle.",
                    "You prove nothing. Bring trophy teeth, then we talk.", trades + [bye]),
               node(d, "Accueil", "accueil", "Os, peaux, lames. Tout se troque contre des dents.",
                    "Bones, hides, blades. All trade for teeth.", trades + [bye])])
    write(DIALOGUES / P / f"{d}.json", doc)


# Chaîne trork : (étape, modèle, type, champs, réputation, faveurs, rang pour la commencer)
CHAIN = [
    (2, "Trork_Chain_Wolves", "Hunt", {"Spawns": ["Wolf_Black", "Wolf_Black", "Wolf_Black"], "Roles": ["Wolf_Black"],
                                       "MinDistance": 60, "MaxDistance": 120}, 120, 5, "Ami"),
    (3, "Trork_Chain_Mosshorn", "Hunt", {"Spawns": ["Mosshorn", "Mosshorn"], "Roles": ["Mosshorn"],
                                         "MinDistance": 80, "MaxDistance": 140}, 150, 5, "Ami"),
    (4, "Trork_Chain_Rival", "Hunt", {"Spawns": ["Trork_Brawler", "Trork_Guard", "Trork_Guard"],
                                      "Roles": ["Trork_Brawler", "Trork_Guard"], "MinDistance": 120, "MaxDistance": 180}, 200, 6, "Hote"),
]
CHAIN_TITLES = {
    "Trork_Chain_Wolves": ("Chasser les loups", "Hunt the wolves",
                           "Loups abattus : {count}/{needed}. La meute rôde à {distance} blocs, {direction}.",
                           "Wolves slain: {count}/{needed}. The pack prowls {distance} blocks away, {direction}."),
    "Trork_Chain_Mosshorn": ("Abattre deux Mosshorns", "Slay two Mosshorns",
                             "Mosshorns abattus : {count}/{needed}. Ils paissent à {distance} blocs, {direction}.",
                             "Mosshorns slain: {count}/{needed}. They graze {distance} blocks away, {direction}."),
    "Trork_Chain_Rival": ("Battre le clan rival", "Beat the rival clan",
                          "Trorks du clan rival abattus : {count}/{needed}. Leur cogneur attend à {distance} blocs, {direction}.",
                          "Rival clan Trorks slain: {count}/{needed}. Their brawler waits {distance} blocks away, {direction}."),
}


def flag(n):
    return f"{P}_Chain_{n}"


def chain_requests():
    for step, tid, kind, extra, reputation, favors, _ in CHAIN:
        fr, en, task_fr, task_en = CHAIN_TITLES[tid]
        doc = {
            "$Comment": f"Étape {step} de la chaîne trork (étape 7), générée par tools/generate_trorks.py : donnée par le chef "
                        f"(StartChainRequest), jamais tirée au tableau (Weight 0). Remplie, elle pose {flag(step)} : un rang "
                        "de moins chez les Kweebecs (reputation/Rivals).",
            "People": P, "Type": kind, "Weight": 0,
            "TitleKey": tr(f"request.{tid}.title", fr, en), "TaskKey": tr(f"request.{tid}.task", task_fr, task_en),
        }
        doc.update(extra)
        doc.update({"Essor": 0, "Favors": favors, "Reputation": reputation, "Flag": flag(step)})
        write(REQUESTS / f"{tid}.json", doc)


def chief():
    d = "Trork_Chef"
    K = f"dialogue.{d}."
    bye = resp(d, "aurevoir", "Que ta lame reste rouge.", "May your blade stay red.")

    def start(tid, r, nxt):
        return resp(d, "accepter", "J'y vais.", "I'm going.", HintKey="nakasar_peuples.dialogue.hint.chain",
                    Conditions=rank(r), FailKey=f"nakasar_peuples.dialogue.fail.rank.{r}",
                    Effects=[{"Type": "StartChainRequest", "Template": tid}], Next=nxt)

    entries = [
        {"Node": "Honni", "Conditions": [{"Type": "Rank", "Max": "Honni"}]},
        {"Node": "Etranger", "Conditions": [{"Type": "Rank", "Max": "Etranger"}]},
        {"Node": "Fin", "Conditions": [{"Type": "Flag", "Flag": flag(5)}]},
        {"Node": "Peinture", "Conditions": [{"Type": "Flag", "Flag": flag(4)}]},
        {"Node": "RivalEnCours", "Conditions": [{"Type": "ChainRequest", "Template": "Trork_Chain_Rival"}]},
        {"Node": "Rival", "Conditions": [{"Type": "Flag", "Flag": flag(3)}]},
        {"Node": "MosshornEnCours", "Conditions": [{"Type": "ChainRequest", "Template": "Trork_Chain_Mosshorn"}]},
        {"Node": "Mosshorn", "Conditions": [{"Type": "Flag", "Flag": flag(2)}]},
        {"Node": "LoupsEnCours", "Conditions": [{"Type": "ChainRequest", "Template": "Trork_Chain_Wolves"}]},
        {"Node": "Loups", "Conditions": [{"Type": "Flag", "Flag": flag(1)}]},
        {"Node": "Feu"},
    ]
    rival_warning = tr("dialogue.hint.rival", "un rang de moins chez les Kweebecs", "one rank lower with the Kweebecs")
    nodes = [
        node(d, "Honni", "honni", "Toi sens le Kweebec. Les miens te mangeraient bien. Apporte de la viande, ou va-t'en.",
             "You smell of Kweebec. My lot would gladly eat you. Bring meat, or leave.", [offer_meat(d, "Mange"), bye]),
        node(d, "Mange", "mange", "Hmm. La viande parle mieux que toi. Continue.", "Hmm. Meat talks better than you. Keep going.", [bye]),
        node(d, "Etranger", "etranger", "Toi pas encore des nôtres. Nourris le camp, fais ce que dit le tableau. Reviens toléré.",
             "You're not one of us yet. Feed the camp, do what the board says. Come back tolerated.",
             [resp(d, "voirDemandes", "Voir les demandes", "See the requests", HintKey="nakasar_peuples.dialogue.hint.openRequests",
                   Effects=[{"Type": "OpenRequests"}], **in_camp()), offer_meat(d, "Mange"), bye]),
        # Étape 1 : nourrir le feu.
        node(d, "Feu", "feu", "Le feu du camp a faim, et un camp affamé se bat mal. Dix viandes crues, et je saurai si tu tiens parole.",
             "The camp fire is hungry, and a hungry camp fights badly. Ten raw meats, and I'll know if you keep your word.",
             [resp(d, "donnerViande", "Voici dix viandes.", "Here are ten meats.",
                   HintKey=rival_warning,
                   Conditions=rank("Tolere") + [{"Type": "HasItem", "ItemId": MEAT, "Quantity": 10}],
                   FailKey=tr(K + "failViande", "il faut être Toléré des Trorks et porter 10 Viande crue",
                              "you must be Tolerated by the Trorks and carry 10 Raw meat"),
                   Effects=[{"Type": "TakeItem", "ItemId": MEAT, "Quantity": 10}, {"Type": "AddReputation", "Amount": 80},
                            {"Type": "SetFlag", "Flag": flag(1)}], Next="Loups"),
              bye]),
        # Étape 2 : la meute.
        node(d, "Loups", "loups", "Le camp mange. Maintenant, chasse avec nous : une meute de loups noirs rôde. Quand tu seras notre ami.",
             "The camp eats. Now hunt with us: a pack of black wolves prowls. When you are our friend.",
             [start("Trork_Chain_Wolves", "Ami", "Accepte"), bye]),
        node(d, "LoupsEnCours", "loupsEnCours", "La meute vit encore. Va.", "The pack still lives. Go.", [bye]),
        # Étape 3 : les Mosshorns.
        node(d, "Mosshorn", "mosshorn", "Bonne chasse. Un vrai Trork rapporte une peau de Mosshorn. Deux bêtes, pas moins.",
             "Good hunt. A true Trork brings a Mosshorn hide. Two beasts, no less.",
             [start("Trork_Chain_Mosshorn", "Ami", "Accepte"), bye]),
        node(d, "MosshornEnCours", "mosshornEnCours", "Les Mosshorns t'attendent. Reviens avec leur sang.",
             "The Mosshorns await. Come back with their blood.", [bye]),
        # Étape 4 : le clan rival.
        node(d, "Rival", "rival", "Un clan rival campe sur nos terres de chasse. Leur cogneur se croit fort. Quand tu seras notre hôte, montre-lui.",
             "A rival clan camps on our hunting grounds. Their brawler thinks he's strong. When you are our host, show him.",
             [start("Trork_Chain_Rival", "Hote", "Accepte"), bye]),
        node(d, "RivalEnCours", "rivalEnCours", "Le cogneur rival respire encore. Ça ne va pas durer.",
             "The rival brawler still breathes. Not for long.", [bye]),
        # Étape 5 : la Peinture de guerre.
        node(d, "Peinture", "peinture", "Le clan rival a fui. Les miens chantent ton nom. Je ne donne la peinture de guerre qu'au champion du camp.",
             "The rival clan fled. My lot sing your name. I give the war paint only to the camp's champion.",
             [resp(d, "recevoirPeinture", "Recevoir la Peinture de guerre", "Receive the War paint",
                   HintKey=tr("dialogue.hint.chainPaint", "objet de passage de la route trork", "passage item of the Trork road"),
                   Conditions=rank("Champion"), FailKey="nakasar_peuples.dialogue.fail.rank.Champion",
                   Effects=[{"Type": "GiveItem", "ItemId": PAINT, "Quantity": 1}, {"Type": "SetFlag", "Flag": flag(5)}],
                   Next="Fin"), bye]),
        node(d, "Fin", "fin", "Peint, tu marches parmi les Trorks. Les Kweebecs, eux, te regarderont de travers.",
             "Painted, you walk among Trorks. The Kweebecs will look at you askance.", [bye]),
        node(d, "Accepte", "accepte", "Va. Reviens avec du sang sur les mains.", "Go. Come back with blood on your hands.", [bye]),
    ]
    doc = dlg(d, P, "Le chef d'un camp trork (étape 7), généré par tools/generate_trorks.py : la chaîne trork, une étape "
                    "par rang (Toléré : nourrir le feu ; Ami : la meute, les Mosshorns ; Hôte : le clan rival ; Champion : "
                    "la Peinture de guerre). Chaque étape coûte un rang chez les Kweebecs (reputation/Rivals). Honni ou "
                    "étranger, il prend la viande.",
              "Croc-de-Fer", "Iron-Fang", "Chef du camp", "Camp chief", entries, nodes)
    write(DIALOGUES / P / f"{d}.json", doc)


def klops():
    d = "Klops_Errant"
    bye = resp(d, "aurevoir", "Bonne route !", "Safe travels!")
    doc = dlg(d, None, "Le Klops errant (étape 7), généré par tools/generate_trorks.py : troc (faveurs de tous les peuples, "
                       "rouages), colis pour un autre village (effet KlopsParcel), tournée du lendemain (KlopsRoute).",
              "Bricole", "Tinker", "Klops errant", "Wandering Klops",
              [{"Node": "Accueil"}],
              [node(d, "Accueil", "accueil", "Bonjour bonjour ! Des rouages, des faveurs, des colis : un Klops n'arrête jamais de rouler.",
                    "Hello hello! Cogs, favours, parcels: a Klops never stops rolling.",
                    [resp(d, "troc", "Voyons ta marchandise.", "Let's see your wares.", HintKey="nakasar_peuples.dialogue.hint.shop.Tolere",
                          Effects=[{"Type": "OpenShop", "Shop": f"{PFX}Klops"}]),
                     resp(d, "colis", "Tu as un colis à porter ?", "Got a parcel to carry?",
                          HintKey=tr("dialogue.hint.parcel", "3 rouages et +30 réputation à la livraison",
                                     "3 cogs and +30 reputation on delivery"),
                          Effects=[{"Type": "KlopsParcel"}], Next="Colis"),
                     resp(d, "route", "Où vas-tu demain ?", "Where are you off to tomorrow?",
                          Effects=[{"Type": "KlopsRoute"}], Next="Route"),
                     bye]),
               node(d, "Colis", "colisTexte", "Fragile, fragile ! Ils te paieront en rouages.",
                    "Fragile, fragile! They'll pay you in cogs.", [bye]),
               # La tournée (KlopsRoute) s'affiche sous cette réplique, dans la fenêtre (dialogue/DialogueSpeech).
               node(d, "Route", "routeTexte", "La route, toujours la route !", "The road, always the road!", [bye])])
    write(DIALOGUES / "Klops" / f"{d}.json", doc)


# ---------------------------------------------------------------- Demandes du tableau

BOARD = [
    # (id, type, palier min, objet, quantité, essor, faveurs, titre fr, titre en, extra)
    ("Trork_Gather_Meat", "Gather", 0, MEAT, 8, 10, 2, "Viande pour le feu", "Meat for the fire", None),
    ("Trork_Gather_Hides", "Gather", 0, "Ingredient_Hide_Light", 6, 10, 2, "Des peaux", "Some hides", None),
    ("Trork_Gather_Wood", "Gather", 0, "Wood_Oak_Trunk", 16, 10, 2, "Du bois pour le camp", "Wood for the camp", None),
    ("Trork_Gather_Bones", "Gather", 1, "Ingredient_Bone_Fragment", 8, 12, 2, "Des os à graver", "Bones to carve", None),
    ("Trork_Craft_Kebab", "Craft", 2, "Food_Kebab_Meat", 4, 15, 3, "Brochettes du festin", "Feast skewers", None),
    ("Trork_Hunt_Wolves", "Hunt", 0, None, 0, 15, 2, "Chasser les loups", "Hunt the wolves",
     {"Spawns": ["Wolf_Black", "Wolf_Black"], "Roles": ["Wolf_Black"], "MinDistance": 70, "MaxDistance": 130}),
    ("Trork_Hunt_Mosshorn", "Hunt", 1, None, 0, 20, 3, "Chasser le Mosshorn", "Hunt the Mosshorn",
     {"Spawns": ["Mosshorn"], "Roles": ["Mosshorn"], "MinDistance": 80, "MaxDistance": 140}),
]
TASKS = {
    "Gather": ("Dépose {count}/{needed} {item} au dépôt du camp ({distance} blocs, {direction}).",
               "Drop {count}/{needed} {item} in the camp chest ({distance} blocks, {direction})."),
    "Craft": ("Fabrique et dépose {count}/{needed} {item} au dépôt du camp ({distance} blocs, {direction}).",
              "Craft and drop {count}/{needed} {item} in the camp chest ({distance} blocks, {direction})."),
    "Hunt": ("Bêtes abattues : {count}/{needed}. Elles rôdent à {distance} blocs, {direction}.",
             "Beasts slain: {count}/{needed}. They prowl {distance} blocks away, {direction}."),
}


def board_requests():
    for rid, kind, tier, item, qty, essor, favors, fr, en, extra in BOARD:
        doc = {"$Comment": f"Demande trork ({kind}), étape 7 : voir RequestTemplate. Générée par tools/generate_trorks.py.",
               "People": P, "Type": kind, "MinTier": tier, "MaxTier": 3, "Weight": 1,
               "TitleKey": tr(f"request.{rid}.title", fr, en), "TaskKey": tr(f"request.{rid}.task", *TASKS[kind])}
        if item:
            doc.update({"ItemId": item, "Quantity": qty})
        doc.update(extra or {})
        doc.update({"Essor": essor, "Favors": favors})
        write(REQUESTS / f"{rid}.json", doc)


# ---------------------------------------------------------------- Troc

def fixed(out, qty, inp, n, stock):
    return {"Type": "Fixed", "Trade": {"Output": {"ItemId": out, "Quantity": qty},
                                       "Input": [{"ItemId": i, "Quantity": c} for i, c in (inp if isinstance(inp, list) else [(inp, n)])],
                                       "Stock": stock}}


def shop(sid, comment, fr, en, slots):
    write(SHOPS / f"{sid}.json", {"$Comment": comment, "DisplayNameKey": tr(f"barter.{sid.removeprefix(PFX)}.title", fr, en),
                                  "RefreshInterval": {"Days": 3}, "RestockHour": 6, "TradeSlots": slots})


def shops():
    shop(f"{PFX}Trork_Tolere", "Échoppe trork de base (rang Toléré) : viande rôtie, cuir, sangles, tourte, payés en dents de trophée. Objets vanilla, "
         "jamais ce que demandent les Trorks (Kevin, 2026-11-15).",
         "Camelote trork", "Trork junk",
         [fixed("Food_Wildmeat_Cooked", 3, FAVOR, 1, 10), fixed("Ingredient_Leather_Light", 2, FAVOR, 1, 8),
          fixed("Ingredient_Strap_Leather", 2, FAVOR, 1, 8), fixed("Food_Pie_Meat", 1, FAVOR, 2, 6)])
    shop(f"{PFX}Trork_Ami", "Échoppe trork des amis : armes trorks vanilla, payées en dents de trophée.",
         "Lames du camp", "Camp blades",
         [fixed("Weapon_Club_Stone_Trork", 1, FAVOR, 4, 2), fixed("Weapon_Spear_Stone_Trork", 1, FAVOR, 4, 2),
          fixed("Weapon_Battleaxe_Stone_Trork", 1, FAVOR, 6, 2), fixed("Weapon_Daggers_Stone_Trork", 1, FAVOR, 5, 2)])
    shop(f"{PFX}Trork_Hote", "Réserve du chef (rang Hôte) : l'armure trork vanilla, pièce par pièce.",
         "Réserve du chef", "Chief's stash",
         [fixed("Armor_Trork_Head", 1, FAVOR, 6, 1), fixed("Armor_Trork_Chest", 1, FAVOR, 10, 1),
          fixed("Armor_Trork_Legs", 1, FAVOR, 8, 1), fixed("Armor_Trork_Hands", 1, FAVOR, 5, 1)])
    shop(f"{PFX}Klops", "Troc du Klops errant (étape 7) : les faveurs de tous les peuples contre des rouages, et des rouages "
                        "contre des marchandises vanilla. Ouvert à tous, quel que soit le rang.",
         "Charrette du Klops", "Klops cart",
         [fixed(COG, 1, FAVOR_K, 2, 12), fixed(COG, 1, FAVOR, 2, 12),
          fixed("Ingredient_Bolt_Linen", 2, COG, 1, 8), fixed("Potion_Health_Small", 1, COG, 2, 6),
          fixed(FAVOR_K, 1, COG, 2, 6), fixed(FAVOR, 1, COG, 2, 6)])


# ---------------------------------------------------------------- Textes du Java

def java_texts():
    tr("people.Trork.name", "Trorks", "Trorks")
    tr("people.Klops.name", "Klops", "Klops")
    for b, fr, en in [("Feu_De_Camp", "le feu de camp", "the campfire"), ("Tente_Ouest", "la tente ouest", "the west tent"),
                      ("Tente_Est", "la tente est", "the east tent"), ("Tour_De_Guet", "la tour de guet", "the watchtower"),
                      ("Foyer", "le foyer", "the hearth"), ("Avertissement", "le panneau d'avertissement", "the warning sign"),
                      ("Terrier", "le terrier", "the burrow"), ("Piege", "le piège", "the trap"), ("Reserve", "la réserve", "the store"),
                      ("Tente_Sud", "la tente sud", "the south tent"), ("Tour_Est", "la tour est", "the east tower"),
                      ("Entrepot", "l'entrepôt", "the warehouse"), ("Bric_A_Brac", "le bric-à-brac", "the junk pile"),
                      ("Reserve_Du_Chef", "la réserve du chef", "the chief's store"), ("Tour_Ouest", "la tour ouest", "the west tower"),
                      ("Grand_Feu", "le grand feu", "the great fire"),
                      ("Fosse_Aux_Betes", "la fosse aux bêtes", "the beast pit")]:
        tr(f"building.{b}", fr, en)
    for j, fr, en in [("Garde", "Garde", "Guard"), ("Guerrier", "Guerrier", "Warrior"), ("Chasseur", "Chasseur", "Hunter"),
                      ("Cogneur", "Cogneur", "Brawler"), ("Sentinelle", "Sentinelle", "Sentry"), ("Shaman", "Shaman", "Shaman"),
                      ("Dresseur", "Dresseur", "Beast tamer")]:
        tr(f"job.{j}", fr, en)
    tr("chain.Trork.step1", "nourrir le feu du camp (10 Viande crue, rang Toléré)", "feed the camp fire (10 Raw meat, Tolerated rank)")
    tr("chain.Trork.step2", "chasser la meute de loups (rang Ami)", "hunt the wolf pack (Friend rank)")
    tr("chain.Trork.step3", "abattre deux Mosshorns (rang Ami)", "slay two Mosshorns (Friend rank)")
    tr("chain.Trork.step4", "battre le clan rival (rang Hôte)", "beat the rival clan (Host rank)")
    tr("chain.Trork.step5", "recevoir la Peinture de guerre (rang Champion)", "receive the War paint (Champion rank)")
    tr("warPaint.on", "Peinture de guerre mise : les Trorks te laissent passer, les Kweebecs te voient un rang plus bas.",
       "War paint on: Trorks let you pass, Kweebecs see you one rank lower.")
    tr("warPaint.off", "Peinture de guerre ôtée.", "War paint off.")
    tr("warPaint.given", "Pot de Peinture de guerre donné.", "War paint pot given.")
    tr("meat.reason", "viande offerte au camp", "meat offered to the camp")
    tr("meat.enough", "Les Trorks de {village} mangent ta viande, mais elle ne suffit plus : prends leurs demandes.",
       "The Trorks of {village} eat your meat, but it's no longer enough: take their requests.")
    tr("reputation.rivalLost", "-{amount} auprès des {people} (tu aides les {helped})", "-{amount} with the {people} (you help the {helped})")
    tr("reputation.rivalRank", "Les {people} apprennent que tu sers les {helped} : tu tombes à {rank} chez eux.",
       "The {people} learn you serve the {helped}: you drop to {rank} with them.")
    # Paroles du Klops dans la fenêtre de dialogue (dialogue/DialogueSpeech).
    tr("klops.parcelGiven", "Ce colis est pour {village} ({people}), à {distance} blocs, direction {direction}. Porte-le près du cœur du village.",
       "This parcel is for {village} ({people}), {distance} blocks away, heading {direction}. Carry it near the village heart.")
    tr("klops.parcelAlready", "Tu portes déjà un colis pour {village} : livre-le d'abord !",
       "You already carry a parcel for {village}: deliver it first!")
    tr("klops.parcelNowhere", "Je n'ai aucun autre village où envoyer un colis.", "I have no other village to send a parcel to.")
    tr("klops.parcelFor", "Ton colis est pour {village}.", "Your parcel is for {village}.")
    tr("klops.delivered", "Colis livré à {village} : {cogs} rouages.", "Parcel delivered to {village}: {cogs} cogs.")
    tr("klops.reason", "colis du Klops livré", "Klops parcel delivered")
    tr("klops.route", "Le Klops errant est aujourd'hui à {today} ; demain, il sera à {tomorrow}.",
       "The wandering Klops is at {today} today; tomorrow it will be at {tomorrow}.")
    tr("klops.routeNone", "Le Klops errant n'a aucun village où passer.", "The wandering Klops has no village to visit.")
    tr("klops.routeSaid", "Aujourd'hui, je suis à {today} ; demain, je serai à {tomorrow}. Viens me trouver là-bas !",
       "Today I'm at {today}; tomorrow I'll be at {tomorrow}. Come find me there!")
    tr("klops.routeNoneSaid", "Pour l'instant, je n'ai aucun village où passer.", "For now, I have no village to visit.")
    tr("command.klops.desc", "Où est le Klops errant, et ton colis", "Where the wandering Klops is, and your parcel")
    tr("command.warPaint.desc", "Donne la Peinture de guerre (test)", "Gives the War paint (test)")
    tr("command.generate.people", "Peuple (kweebec par défaut, ou trork)", "People (kweebec by default, or trork)")


# ---------------------------------------------------------------- Langues

def check_titles():
    bad = [(k, v) for d in (FR, EN) for k, v in d.items() if k.startswith("request.") and k.endswith(".title") and len(v) > TITLE_MAX]
    for k, v in bad:
        print(f"ERREUR titre trop long pour le suivi du HUD ({len(v)} > {TITLE_MAX}) : {k} = {v}")
    if bad:
        raise SystemExit(1)


def langs():
    for locale, texts in (("fr-FR", FR), ("en-US", EN)):
        path = LANGS / locale / "nakasar_peuples.lang"
        lines = path.read_text(encoding="utf-8").splitlines()
        index = {line.split("=", 1)[0].strip(): i for i, line in enumerate(lines) if "=" in line}
        added = []
        for key, value in texts.items():
            line = f"{key} = {value}"
            if key in index:
                # Les noms de bâtiments et de métiers sont partagés entre peuples : on garde ceux qui existent.
                if not key.startswith(("building.", "job.")):
                    lines[index[key]] = line
            else:
                added.append(line)
        if added:
            lines += ["", "# Étape 7 : camp trork, Peinture de guerre, Klops errant (tools/generate_trorks.py)"] if \
                "# Étape 7 : camp trork, Peinture de guerre, Klops errant (tools/generate_trorks.py)" not in lines else []
            lines += added
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"{path.relative_to(ROOT)} : {len(added)} clés ajoutées")


def main():
    items()
    npcs()
    crier()
    merchant()
    chain_requests()
    chief()
    klops()
    board_requests()
    shops()
    java_texts()
    check_titles()
    langs()


if __name__ == "__main__":
    main()
