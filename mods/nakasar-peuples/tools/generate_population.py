#!/usr/bin/env python3
"""Générations de villageois (Peuples d'Orbis, Kevin, 16 novembre 2026 : Claude Doc « Générations de villageois »).

Le Java (population/) tient le registre des habitants de chaque village : naissances, âges, apprentissages,
passations, morts de vieillesse ou dans l'incendie d'un raid perdu, tombes. Ce script écrit les assets qui vont avec :
  * les rôles des habitants sans poste (village/Villagers, slots « hab:<id> ») : apprenti, adulte sans métier, ancien
    retiré, par peuple, avec apparences VANILLA (règle n° 2) ; l'apprenti est le modèle adulte à l'échelle 0,8 ;
  * leurs dialogues (le nom affiché est celui de la fiche de l'habitant : population/Population.identity) ;
  * la tombe Nakasar_Peuples_Tombstone (Furniture_Village_Tombstone vanilla, incassable) et son interaction
    (population/ReadTombInteraction : épitaphe) ;
  * l'onglet « Habitants » du panneau du village, une mise en page par peuple (PeoplePage_<Peuple>.ui,
    population/PeoplePage) ;
  * le bloc de traductions des générations en tête des deux .lang.

    python3 tools/generate_population.py
"""
import json
from pathlib import Path

from generate_board_ui import COMMON, MEMORIES, OUT, PANEL_HEIGHT, PANEL_WIDTH, THEMES, label, tab_strip

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "src/main/resources/Server"
ROLES = RES / "NPC/Roles/Nakasar/Peuples"
MODELS = RES / "Models/Nakasar/Peuples"
DIALOGUES = RES / "Nakasar/Dialogues"
TOMB = "Nakasar_Peuples_Tombstone"
TOMB_INTERACTION = "Nakasar_Peuples_Read_Tomb"
LANG_BEGIN = "# ---- Générations de villageois (généré par tools/generate_population.py, ne pas modifier à la main) ----"
LANG_END = "# ---- Fin des générations de villageois ----"

PEOPLES = ("Kweebec", "Trork", "Feran", "Renonce", "Slothian")
# Apparences vanilla (déjà portées par les rôles du mod) : adulte sans métier, modèle de l'apprenti (échelle 0,8),
# ancien retiré.
LOOKS = {
    "Kweebec": ("Kweebec_Sapling_Orange", "Kweebec_Sapling_Green", "Kweebec_Sapling_Treesinger"),
    "Trork": ("Trork_Hunter", "Trork", "Trork_Doctor_Witch"),
    "Feran": ("Feran_Civilian", "Feran_Burrower", "Feran_Windwalker"),
    "Renonce": ("Outlander_Peon", "Outlander_Peon", "Outlander_Sorcerer"),
    "Slothian": ("Slothian_Villager", "Slothian_Villager", "Slothian_Elder"),
}
APPRENTICE_SCALE = 0.8
KINDS = ("Resident", "Apprentice", "Retired")
# Errance autour du point d'attache, vitesse relative : l'ancien bouge peu.
WANDER = {"Resident": (4, 0.3), "Apprentice": (2, 0.35), "Retired": (2, 0.2)}

# population/PeoplePage : lignes de la liste, prénoms proposés, lignes de chronique.
ROWS = 9
NAMES = 3
CHRONICLE = 7
LEFT_WIDTH = 590

FR, EN = {}, {}


def t(key, fr, en):
    FR[key] = fr
    EN[key] = en


def write(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ---- Rôles, modèles, dialogues ----

def role(people, kind):
    resident, apprentice, retired = LOOKS[people]
    look = {"Resident": resident, "Apprentice": f"Nakasar_Peuples_{people}_Apprentice", "Retired": retired}[kind]
    radius, speed = WANDER[kind]
    return {
        "$Comment": f"Habitant sans poste ({kind}) d'un village {people.lower()} (générations de villageois), généré par "
                    "tools/generate_population.py. Posé par village/Villagers (slot hab:<id>) quand un joueur approche ; le "
                    "Java déplace son point d'attache (près de son maître, devant son logis, sur la place ; chez lui la nuit "
                    "et pendant un raid). Son nom est celui de sa fiche (population/Population.identity). Régénération "
                    "vanilla hors combat (PNJ amical).",
        "Type": "Generic",
        "Appearance": look,
        "NameTranslationKey": f"nakasar_peuples.npc.{people}_{kind}.name",
        "MaxHealth": 80,
        "StartState": "Idle",
        "DefaultPlayerAttitude": "Neutral",
        "DefaultNPCAttitude": "Ignore",
        "MotionControllerList": [
            {"Type": "Walk", "MaxWalkSpeed": 3, "Gravity": 10, "RunThreshold": 0.6, "MaxFallSpeed": 15,
             "MaxRotationSpeed": 360, "Acceleration": 10, "JumpHeight": 1.0}
        ],
        "KnockbackScale": 0.5,
        "Instructions": [
            {
                "Sensor": {"Type": "State", "State": "Idle"},
                "Instructions": [
                    {
                        "$Comment": "Loin de son point d'attache (le Java l'a déplacé) : il y marche.",
                        "Sensor": {"Type": "Leash", "Range": radius + 3},
                        "BodyMotion": {"Type": "Seek", "RelativeSpeed": 0.5, "SlowDownDistance": 2, "StopDistance": 1,
                                       "UsePathfinder": True},
                    },
                    {
                        "$Comment": "Arrivé : il flâne.",
                        "BodyMotion": {"Type": "WanderInCircle", "Radius": radius, "RelativeSpeed": speed,
                                       "MaxHeadingChange": 50},
                    },
                ],
            }
        ],
        "InteractionInstruction": {
            "Instructions": [
                {"Continue": True, "Sensor": {"Type": "Any"},
                 "Actions": [{"Type": "SetInteractable", "Interactable": True, "Hint": "nakasar_peuples.hint.talk"}]},
                {"Sensor": {"Type": "HasInteracted"}, "Actions": []},
            ]
        },
    }


def apprentice_model(people):
    parent = LOOKS[people][1]
    return {
        "$Comment": f"Apprenti {people.lower()} (générations de villageois) : le modèle vanilla {parent} à l'échelle "
                    f"{str(APPRENTICE_SCALE).replace('.', ',')}, entre l'enfant et l'adulte. Généré par tools/generate_population.py.",
        "Parent": parent,
        "MinScale": APPRENTICE_SCALE,
        "MaxScale": APPRENTICE_SCALE,
    }


def dialogue(people, kind):
    did = f"{people}_{kind}"
    k = f"nakasar_peuples.dialogue.{did}."
    bye = {"TextKey": "nakasar_peuples.dialogue.job.aurevoir"}
    life = {"TextKey": "nakasar_peuples.population.dialogue.life", "Next": "Vie"}
    return did, {
        "$Comment": f"Dialogue de l'habitant sans poste {kind} (générations de villageois), généré par tools/generate_population.py. "
                    "Le nom affiché est celui de sa fiche, la ligne sous la réplique dit son âge et ses parents.",
        "NpcNameKey": f"nakasar_peuples.npc.{people}_{kind}.name",
        "RoleKey": k + "role",
        "People": people,
        "Entries": [{"Node": "Abri", "Conditions": [{"Type": "Raid", "State": "Active"}]}, {"Node": "Accueil"}],
        "Nodes": [
            {"Id": "Accueil", "TextKey": k + "accueil", "Responses": [life, bye]},
            {"Id": "Vie", "TextKey": k + "vie", "Responses": [bye]},
            {"Id": "Abri", "TextKey": "nakasar_peuples.population.dialogue.shelter", "Responses": [bye]},
        ],
    }


ROLE_NAMES = {
    # (fr, en) par sorte
    "Resident": ("Habitant", "Villager"),
    "Apprentice": ("Apprenti", "Apprentice"),
    "Retired": ("Ancien", "Elder"),
}
PEOPLE_ADJ = {"Kweebec": ("kweebec", "Kweebec"), "Trork": ("trork", "Trork"), "Feran": ("feran", "Feran"),
              "Renonce": ("renoncé", "Forsaken"), "Slothian": ("slothian", "Slothian")}

GREETINGS = {
    ("Kweebec", "Resident"): ("Bonjour, voyageur ! Je n'ai pas encore de poste, alors j'aide où il faut : un panier ici, une haie là.",
                              "Hello, traveller! I have no post yet, so I help wherever needed: a basket here, a hedge there."),
    ("Kweebec", "Apprentice"): ("Chut, je regarde comment on fait ! Un jour, ce sera mon travail.",
                                "Shh, I'm watching how it's done! One day this will be my job."),
    ("Kweebec", "Retired"): ("Ah, un visage neuf. J'ai planté la moitié des arbres que tu vois, et j'ai tout le temps de te le raconter.",
                             "Ah, a new face. I planted half the trees you see, and I have all the time in the world to tell you."),
    ("Trork", "Resident"): ("Quoi ? Je cherche une place au camp. Si t'as de la viande, je t'écoute.",
                            "What? I'm looking for a place in the camp. Got meat? Then I'm listening."),
    ("Trork", "Apprentice"): ("Le vieux m'apprend. Je tape plus fort que lui, mais il dit que c'est pas le plus important.",
                              "The old one teaches me. I hit harder than him, but he says that's not what matters."),
    ("Trork", "Retired"): ("J'ai porté le feu de ce camp avant ta naissance. Assieds-toi, et écoute.",
                           "I carried this camp's fire before you were born. Sit down, and listen."),
    ("Feran", "Resident"): ("Que le vent te soit doux. Je cherche encore ma place à l'oasis, mais l'eau est fraîche pour tous.",
                            "May the wind be gentle to you. I am still seeking my place at the oasis, but the water is cool for all."),
    ("Feran", "Apprentice"): ("Mon maître dit que le sable enseigne la patience. Moi, j'apprends surtout à ne pas me brûler.",
                              "My master says sand teaches patience. I mostly learn not to burn myself."),
    ("Feran", "Retired"): ("J'ai vu passer plus de caravanes que de lunes. Repose-toi à l'ombre un moment.",
                           "I have seen more caravans pass than moons. Rest in the shade a while."),
    ("Renonce", "Resident"): ("Salut. Je n'ai pas encore de charge au village, mais le froid ne m'a jamais fait peur.",
                              "Hail. I have no duty in the village yet, but the cold never frightened me."),
    ("Renonce", "Apprentice"): ("J'apprends le métier. Les mains gèlent, mais on n'abandonne pas : c'est la règle.",
                                "I'm learning the trade. Hands freeze, but you don't give up: that's the rule."),
    ("Renonce", "Retired"): ("Les jeunes tiennent les postes, maintenant. Moi, je garde les histoires.",
                             "The young hold the posts now. I keep the stories."),
    ("Slothian", "Resident"): ("Mmh... bonjour... Je n'ai pas de poste... je prends le temps... de trouver le bon.",
                               "Mmh... hello... I have no post... I take my time... to find the right one."),
    ("Slothian", "Apprentice"): ("J'apprends... doucement... mon maître dit que c'est... la meilleure façon.",
                                 "I'm learning... slowly... my master says it is... the best way."),
    ("Slothian", "Retired"): ("Les années passent... comme la vase au fond du marais... sans se presser.",
                              "The years go by... like the silt at the bottom of the swamp... in no hurry."),
}
LIFE = {
    "Resident": ("Je suis né ici, ou j'y suis venu, peu importe : c'est mon village. Quand un poste se libère, je suis prêt à le prendre.",
                 "Born here or come here, it does not matter: this is my village. When a post frees up, I'm ready to take it."),
    "Apprentice": ("J'apprends auprès de celui qui tient le poste. Quand il sera vieux, c'est moi qui le reprendrai.",
                   "I learn from the one who holds the post. When they grow old, I'll take it over."),
    "Retired": ("J'ai laissé mon poste à plus jeune que moi. Maintenant je regarde grandir les enfants et je raconte la chronique.",
                "I left my post to someone younger. Now I watch the children grow and tell the chronicle."),
}


def texts_dialogues():
    t("population.dialogue.life", "Parle-moi de toi.", "Tell me about yourself.")
    t("population.dialogue.shelter", "Un raid ! Je rentre m'enfermer à la maison, ne reste pas dehors !",
      "A raid! I'm going home to lock myself in, don't stay outside!")
    for people in PEOPLES:
        adj_fr, adj_en = PEOPLE_ADJ[people]
        for kind in KINDS:
            fr, en = ROLE_NAMES[kind]
            t(f"npc.{people}_{kind}.name", f"{fr} {adj_fr}", f"{adj_en} {en.lower()}")
            t(f"dialogue.{people}_{kind}.role", fr, en)
            g = GREETINGS[(people, kind)]
            t(f"dialogue.{people}_{kind}.accueil", g[0], g[1])
            life = LIFE[kind]
            t(f"dialogue.{people}_{kind}.vie", life[0], life[1])


# ---- Tombe ----

def tomb_assets():
    write(RES / f"Item/Items/Nakasar/Peuples/{TOMB}.json", {
        "$Comment": "Tombe d'un habitant (générations de villageois, generate_population.py) : pierre tombale vanilla, "
                    "posée par population/Cemetery au cimetière du village ; incassable, la lire ouvre l'épitaphe.",
        "Parent": "Furniture_Village_Tombstone",
        "TranslationProperties": {
            "Name": f"nakasar_peuples.items.{TOMB}.name",
            "Description": f"nakasar_peuples.items.{TOMB}.description",
        },
        "Quality": "Developer",
        "BlockType": {
            "Gathering": {"Breaking": {"GatherType": "Unbreakable"}},
            "Interactions": {"Use": {"Interactions": [TOMB_INTERACTION]}},
        },
    })
    write(RES / f"Item/Interactions/Nakasar/Peuples/{TOMB_INTERACTION}.json", {
        "$Comment": "Tombe d'un habitant : ouvre son épitaphe (population/ReadTombInteraction).",
        "Type": "Nakasar_Peuples_ReadTomb",
    })


# ---- Onglet Habitants ----

def people_page(theme_id):
    th = THEMES[theme_id]
    acc, band, title = th["accent"], th["band"], th["title"]
    emblem = (f'Background: (TexturePath: "{MEMORIES}{th["emblem"]}.png", Color: {acc});' if th["emblem"]
              else "Visible: false;")
    L = []
    w = L.append
    w('$C = "../../../Common.ui";')
    w("")
    w(f"// Généré par tools/generate_population.py (thème {theme_id or 'neutre'}) : ne pas modifier à la main.")
    w("")
    w(f"@Accent = {acc};")
    w(f"@Section = LabelStyle(FontSize: 15, RenderBold: true, RenderUppercase: true, TextColor: {title}, VerticalAlignment: Center);")
    w("@Body = LabelStyle(FontSize: 14, TextColor: #c9d1d9, Wrap: true);")
    w("@SmallWrap = LabelStyle(FontSize: 13, TextColor: #96a9be, Wrap: true);")
    w("")
    w("$C.@PageOverlay {")
    w("  LayoutMode: Middle;")
    w("")
    w("  $C.@DecoratedContainer {")
    w(f"    Anchor: (Width: {PANEL_WIDTH}, Height: {PANEL_HEIGHT});")
    w("")
    w("    #Title {")
    w("      Group {")
    w("        LayoutMode: Center;")
    w(f"        Group #TitleEmblem {{ Anchor: (Width: 26, Height: 26, Right: 8); {emblem} }}")
    w(f'        Label #PageTitle {{ Style: (...$C.@TitleStyle, FontSize: 16, TextColor: {title}); }}')
    w("      }")
    w("    }")
    w("")
    w("    #Content {")
    w("      LayoutMode: Top;")
    w("      Padding: (Full: 17, Top: 12);")
    tab_strip(w, acc, "People")
    w("      Group {")
    w("        LayoutMode: Left;")
    w("        FlexWeight: 1;")
    # Colonne de gauche : recensement et liste.
    w("        Group #Left {")
    w("          LayoutMode: Top;")
    w(f"          Anchor: (Width: {LEFT_WIDTH}, Right: 14);")
    w(f'          {label("Census", "LabelStyle(FontSize: 14, RenderBold: true, TextColor: #e8c46a, VerticalAlignment: Center)", anchor="Height: 22")}')
    w(f'          {label("ListHeader", "@Section", anchor="Height: 22, Top: 6, Bottom: 6")}')
    for i in range(ROWS):
        w(f"          Group #Row{i} {{")
        w("            LayoutMode: Left;")
        w(f"            Anchor: (Height: 48, Bottom: {4 if i < ROWS - 1 else 0});")
        w("            Padding: (Horizontal: 12, Vertical: 3);")
        w(f"            Background: (Color: {band}(0.55));")
        w("            Group {")
        w("              LayoutMode: Top;")
        w("              FlexWeight: 1;")
        w(f'              {label(f"RowName{i}", f"LabelStyle(FontSize: 15, RenderBold: true, TextColor: {acc}, VerticalAlignment: Center)", anchor="Height: 20")}')
        w(f'              {label(f"RowLine{i}", "LabelStyle(FontSize: 13, TextColor: #96a9be, Wrap: true)", anchor="Height: 22")}')
        w("            }")
        w(f'            $C.@SmallSecondaryTextButton #RowOrient{i} {{ @Text = ""; @Anchor = Anchor(Width: 120, Height: 30, Left: 8, Top: 6); }}')
        w("          }")
    w("          Group { FlexWeight: 1; }")
    w("          Group {")
    w("            LayoutMode: Left;")
    w("            Anchor: (Height: 30, Top: 6);")
    w('            $C.@SmallSecondaryTextButton #Prev { @Text = ""; @Anchor = Anchor(Width: 110, Height: 30); }')
    w(f'            {label("PageLine", "LabelStyle(FontSize: 13, TextColor: #96a9be, HorizontalAlignment: Center, VerticalAlignment: Center)", extra=" FlexWeight: 1;")}')
    w('            $C.@SmallSecondaryTextButton #Next { @Text = ""; @Anchor = Anchor(Width: 110, Height: 30); }')
    w("          }")
    w("        }")
    # Colonne de droite : naissance, refuge, orientation, chronique.
    w("        Group #Right {")
    w("          LayoutMode: Top;")
    w("          FlexWeight: 1;")

    def card(header, body_id, body_height, buttons, controls_id=None, bottom=8):
        w("          Group {")
        w("            LayoutMode: Top;")
        w(f"            Anchor: (Bottom: {bottom});")
        w("            Padding: (Horizontal: 14, Vertical: 8);")
        w(f"            Background: (Color: {band}(0.75));")
        w(f'            {label(header, "@Section", anchor="Height: 22")}')
        w(f'            {label(body_id, "@SmallWrap", anchor=f"Height: {body_height}, Top: 2")}')
        w(f"            Group{' #' + controls_id if controls_id else ''} {{")
        w("              LayoutMode: Left;")
        w("              Anchor: (Height: 30, Top: 4);")
        for bid, width in buttons:
            w(f'              $C.@SmallSecondaryTextButton #{bid} {{ @Text = ""; @Anchor = Anchor(Width: {width}, Height: 30, Right: 6); }}')
        w("            }")
        w("          }")

    card("BirthHeader", "BirthLine", 52, [(f"Name{i}", 118) for i in range(NAMES)])
    card("RefugeHeader", "RefugeLine", 36, [("Refuge", 220)])
    card("OrientHeader", "OrientLine", 44, [("OrientPrev", 100), ("OrientNext", 100), ("OrientApply", 150)], "OrientControls")
    w(f'          {label("ChronicleHeader", "@Section", anchor="Height: 22, Top: 2, Bottom: 2")}')
    for i in range(CHRONICLE):
        w(f'          {label(f"Chron{i}", "@SmallWrap", anchor="Height: 30")}')
    w("        }")
    w("      }")
    w("      Group {")
    w("        LayoutMode: Left;")
    w("        Anchor: (Height: 36, Top: 8);")
    w(f'        {label("Rule", "@SmallWrap", extra=" FlexWeight: 1;")}')
    w("      }")
    w("    }")
    w("  }")
    w("}")
    w("")
    w("$C.@BackButton {}")
    return "\n".join(L).replace("Style: LabelStyle(", "Style: (") + "\n"


# ---- Textes ----

def texts():
    p = "population."
    t(p + "and", "{a} et {b}", "{a} and {b}")
    t(p + "alone", "un parent seul", "a single parent")
    t(p + "noParents", "parents inconnus", "unknown parents")
    t(p + "noPost", "sans poste", "no post")
    t(p + "wilds", "des terres sauvages", "the wilds")
    t(p + "today", "aujourd'hui", "today")
    t(p + "daysAgo", "il y a {days} j", "{days} d ago")
    t(p + "ageDays", "{days} j", "{days} d")
    t(p + "ageYears", "{years} an(s)", "{years} yr(s)")
    for s, fr, en in (("child", "Enfant", "Child"), ("apprentice", "Apprenti", "Apprentice"), ("adult", "Adulte", "Adult"),
                      ("elder", "Ancien", "Elder")):
        t(p + "stage." + s, fr, en)
    for s, fr, en in (("chief", "Chef du village", "Village chief"), ("crier", "Crieur", "Crier"), ("merchant", "Marchand", "Merchant")):
        t(p + "post." + s, fr, en)
    t(p + "about.line", "{what}, {age}, {origin}.", "{what}, {age}, {origin}.")
    t(p + "about.apprentice", "apprenti ({post})", "apprentice ({post})")
    t(p + "about.retired", "retiré", "retired")
    t(p + "about.parents", "enfant de {parents}", "child of {parents}")
    t(p + "about.from", "venu de {village}", "came from {village}")
    t(p + "about.founder", "fondateur du village", "village founder")
    t(p + "about.godparent", "{line} Filleul de {player}.", "{line} Godchild of {player}.")
    t(p + "rankNeeded", "Il faut être au moins {rank} du village.", "You must be at least {rank} of the village.")
    t(p + "nameTooLate", "Trop tard : le prénom de l'enfant est déjà choisi.", "Too late: the child's name has already been chosen.")
    t(p + "refugeTier", "Le refuge s'ouvre au palier {tier}.", "The refuge opens at the {tier} tier.")
    t(p + "orientWait", "Le village a déjà orienté un apprenti : encore {days} jour(s).", "The village already guided an apprentice: {days} more day(s).")
    t(p + "oriented", "{name} apprendra désormais le métier : {post}.", "{name} will now learn the trade: {post}.")
    t(p + "godparentReason", "ton filleul grandit", "your godchild grows up")
    # Annonces
    t(p + "announce.birth", "{village} : naissance de {child}, enfant de {parents}.", "{village}: {child} is born, child of {parents}.")
    t(p + "announce.named", "{village} : {player} a choisi le prénom de {child}.", "{village}: {player} chose the name of {child}.")
    t(p + "announce.handover", "{village} : {elder} laisse son poste ({post}) à {heir}.", "{village}: {elder} hands the post ({post}) to {heir}.")
    t(p + "announce.death_age", "{village} : {name} ({post}) s'est éteint de vieillesse.", "{village}: {name} ({post}) passed away of old age.")
    t(p + "announce.death_fire", "{village} : {name} ({post}) a péri dans l'incendie.", "{village}: {name} ({post}) perished in the fire.")
    # Chronique
    for kind, fr, en in (
            ("founded", "{ago} : le registre du village s'ouvre avec {detail} habitants.", "{ago}: the village register opens with {detail} inhabitants."),
            ("apprentice", "{ago} : {who} devient apprenti ({detail}).", "{ago}: {who} becomes an apprentice ({detail})."),
            ("adult", "{ago} : {who} devient adulte.", "{ago}: {who} comes of age."),
            ("elder", "{ago} : {who} devient un ancien ({detail}).", "{ago}: {who} becomes an elder ({detail})."),
            ("handover", "{ago} : {other} laisse son poste ({detail}) à {who}.", "{ago}: {other} hands the post ({detail}) to {who}."),
            ("takes", "{ago} : {who} reprend le poste vacant ({detail}).", "{ago}: {who} takes the vacant post ({detail})."),
            ("arrival", "{ago} : {who} arrive de {detail}.", "{ago}: {who} arrives from {detail}."),
            ("fostered", "{ago} : {who} est recueilli ({detail}).", "{ago}: {who} is taken in ({detail})."),
            ("rehoused", "{ago} : {who} est relogé au refuge ({detail}).", "{ago}: {who} is rehoused in the refuge ({detail})."),
            ("birth", "{ago} : naissance de {who}, enfant de {other}.", "{ago}: {who} is born, child of {other}."),
            ("named", "{ago} : {detail} choisit le prénom de {who}.", "{ago}: {detail} chooses the name of {who}."),
            ("oriented", "{ago} : {who} est orienté vers un métier ({detail}).", "{ago}: {who} is guided towards a trade ({detail})."),
            ("wounded", "{ago} : {who} est blessé en défendant le village.", "{ago}: {who} is wounded defending the village."),
            ("death_age", "{ago} : {who} ({detail}) s'éteint de vieillesse.", "{ago}: {who} ({detail}) dies of old age."),
            ("death_fire", "{ago} : {who} ({detail}) périt dans l'incendie.", "{ago}: {who} ({detail}) perishes in the fire."),
    ):
        t(p + "chron." + kind, fr, en)
    # Raids
    r = p + "raid."
    t(r + "levelLost", "{village} : le raid est perdu, {building} redescend au niveau {level}. Personne n'est mort.",
      "{village}: the raid is lost, {building} drops back to level {level}. Nobody died.")
    t(r + "rehoused", "{village} : {count} habitant(s) relogé(s) au refuge ({refuge}).", "{village}: {count} inhabitant(s) rehoused in the refuge ({refuge}).")
    t(r + "reportLevel", "Le bâtiment touché ({building}) perd un niveau : il redescend au niveau {level}, personne n'est mort.",
      "The building hit ({building}) loses a level: back to level {level}, nobody died.")
    t(r + "reportDead", "{name}, responsable de {building}, a péri dans l'incendie.", "{name}, in charge of {building}, perished in the fire.")
    t(r + "reportNobody", "Personne n'était responsable de {building} : il n'y a pas de mort.", "Nobody was in charge of {building}: no one died.")
    # Tombe
    m = p + "tomb."
    t(f"items.{TOMB}.name", "Tombe d'un habitant", "Villager's grave")
    t(f"items.{TOMB}.description", "Une pierre du cimetière du village. La lire donne son épitaphe.", "A stone of the village graveyard. Read it for its epitaph.")
    t(m + "lived", "A vécu {age} au village {village}.", "Lived {age} in the village of {village}.")
    t(m + "post", "Poste : {post}.", "Post: {post}.")
    t(m + "noPost", "N'a pas tenu de poste.", "Held no post.")
    t(m + "cause.age", "S'est éteint de vieillesse, entouré des siens.", "Passed away of old age, among their own.")
    t(m + "cause.fire", "A péri dans l'incendie d'un raid perdu.", "Perished in the fire of a lost raid.")
    t(m + "parents", "Enfant de {parents}.", "Child of {parents}.")
    t(m + "founder", "Fondateur du village.", "Founder of the village.")
    t(m + "arrived", "Venu d'ailleurs, il a fait sa vie ici.", "Came from elsewhere and made a life here.")
    t(m + "godparent", "Prénom choisi par {player}.", "Name chosen by {player}.")
    t(m + "ago", "Mort il y a {days} jour(s).", "Died {days} day(s) ago.")
    t(m + "unknownTitle", "Tombe", "Grave")
    t(m + "unknown", "Le nom est effacé : personne ne se souvient de qui repose ici.", "The name has worn away: nobody remembers who lies here.")
    # Onglet
    g = p + "page."
    t(g + "tab", "Habitants", "People")
    t(g + "none", "Ce village ne tient pas de registre d'habitants.", "This village keeps no register of inhabitants.")
    t(g + "orphan", "Village introuvable.", "Village not found.")
    t(g + "title", "Habitants de {village}", "People of {village}")
    t(g + "census", "{living} habitants : {children} enfant(s), {apprentices} apprenti(s), {adults} adulte(s), {elders} ancien(s). {beds} lits.",
      "{living} inhabitants: {children} child(ren), {apprentices} apprentice(s), {adults} adult(s), {elders} elder(s). {beds} beds.")
    t(g + "list", "Habitants", "Inhabitants")
    t(g + "row", "{stage}, {age} · {what} · {home}", "{stage}, {age} · {what} · {home}")
    t(g + "rowWounded", "{line} · blessé, se repose", "{line} · wounded, resting")
    t(g + "idle", "sans poste", "no post")
    t(g + "noHome", "sans logis", "homeless")
    t(g + "pages", "Page {page} / {pages}", "Page {page} / {pages}")
    t(g + "prev", "Précédent", "Previous")
    t(g + "next", "Suivant", "Next")
    t(g + "orientSelect", "Orienter", "Guide")
    t(g + "orientSelected", "Choisi", "Selected")
    t(g + "birthHeader", "Naissances", "Births")
    t(g + "birthNaming", "{child} vient de naître, enfant de {parents}. Un {rank} du village peut choisir son prénom jusqu'à demain et devenir son parrain.",
      "{child} was just born, child of {parents}. A {rank} of the village can choose the name until tomorrow and become the godparent.")
    t(g + "birthNone", "Pas de nouveau-né. Lits libres : {free}. {why}", "No newborn. Free beds: {free}. {why}")
    t(g + "birthMourning", "Le village est en deuil : pas de naissance pour l'instant.", "The village is mourning: no births for now.")
    t(g + "birthBurnt", "Un bâtiment brûlé attend d'être rebâti : pas de naissance avant.", "A burnt building awaits rebuilding: no births until then.")
    t(g + "birthNoBed", "Plus de lit libre : il faut de nouvelles maisons.", "No free bed left: the village needs new houses.")
    t(g + "birthHope", "Une naissance peut venir un matin, s'il y a {food} vivres au dépôt.", "A birth may come some morning, if the depot holds {food} food.")
    t(g + "refugeHeader", "Refuge", "Refuge")
    t(g + "refugeSet", "Refuge : {building}. Les habitants d'un bâtiment brûlé y sont relogés.", "Refuge: {building}. People from a burnt building are rehoused there.")
    t(g + "refugeNone", "Pas de refuge : les habitants d'un bâtiment brûlé campent au bord du village.", "No refuge: people from a burnt building camp at the edge of the village.")
    t(g + "refugeTier", "Le refuge s'ouvre au palier {tier}.", "The refuge opens at the {tier} tier.")
    t(g + "refugeButton", "Changer le refuge", "Change the refuge")
    t(g + "orientHeader", "Orientation", "Guidance")
    t(g + "orientHint", "Choisis un apprenti dans la liste pour l'orienter vers un métier (une fois tous les {days} jours).",
      "Pick an apprentice in the list to guide them towards a trade (once every {days} days).")
    t(g + "orientLine", "{name} apprend : {now}. Vers : {post}.", "{name} is learning: {now}. Towards: {post}.")
    t(g + "orientApply", "Orienter", "Guide")
    t(g + "chronicle", "Chronique", "Chronicle")
    t(g + "rule", "Une année du village dure {year} jours. Un {ami} choisit le prénom d'un nouveau-né ; un {hote} désigne le refuge et oriente les apprentis. On ne meurt que de vieillesse, ou quand un raid perdu brûle son bâtiment.",
      "A village year lasts {year} days. A {ami} names a newborn; a {hote} sets the refuge and guides apprentices. People only die of old age, or when a lost raid burns their building.")
    # Commandes
    c = "command."
    t(c + "inhabitants.desc", "Liste les habitants du village le plus proche (générations, ops)", "List the nearest village's inhabitants (generations, ops)")
    t(c + "inhabitants.header", "{village} : {count} habitant(s)", "{village}: {count} inhabitant(s)")
    t(c + "inhabitants.line", "{id} · {name} : {line}", "{id} · {name}: {line}")
    t(c + "age.desc", "Fait vieillir le village le plus proche de N jours (ops)", "Age the nearest village by N days (ops)")
    t(c + "age.arg", "jours", "days")
    t(c + "age.done", "{village} a vieilli de {days} jour(s).", "{village} aged by {days} day(s).")
    t(c + "birth.desc", "Fait naître un enfant au village le plus proche (ops)", "Make a child be born in the nearest village (ops)")
    t(c + "birth.done", "Un enfant est né.", "A child is born.")
    t(c + "birth.failed", "Pas de naissance possible : il faut un lit libre, un foyer avec un adulte et {food} vivres au dépôt.",
      "No birth possible: it needs a free bed, a home with an adult and {food} food in the depot.")
    t(c + "death.desc", "Un habitant meurt (vieillesse, ou incendie) (ops)", "An inhabitant dies (old age, or fire) (ops)")
    t(c + "death.arg", "id de l'habitant (/village habitants)", "inhabitant id (/village habitants)")
    t(c + "death.cause", "vieillesse ou incendie", "age or fire")
    t(c + "death.unknown", "Pas d'habitant vivant d'id {id}.", "No living inhabitant with id {id}.")


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
            raise SystemExit(f"clés déjà présentes dans {locale} (hors bloc des générations) : {dup[:10]}")
        block = [LANG_BEGIN] + [f"{k} = {v}" for k, v in table.items()] + [LANG_END, ""]
        path.write_text("\n".join(block) + text, encoding="utf-8")
        print(f"{path.relative_to(ROOT)} : {len(table)} clés des générations")


def main():
    for people in PEOPLES:
        write(MODELS / f"Nakasar_Peuples_{people}_Apprentice.json", apprentice_model(people))
        for kind in KINDS:
            write(ROLES / f"Nakasar_Peuples_{people}_{kind}.json", role(people, kind))
            did, doc = dialogue(people, kind)
            write(DIALOGUES / people / f"{did}.json", doc)
    tomb_assets()
    for theme_id in THEMES:
        name = f"PeoplePage_{theme_id}.ui" if theme_id else "PeoplePage.ui"
        (OUT / name).write_text(people_page(theme_id), encoding="utf-8")
        print("écrit", name)
    texts_dialogues()
    texts()
    write_langs()


if __name__ == "__main__":
    main()
