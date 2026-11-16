#!/usr/bin/env python3
"""Génère le colon (outpost/Settlers) : rôles, dialogue et traductions.

Un village au palier max fait venir un colon (un tous les 7 jours de jeu). Il propose au joueur de l'aider à fonder un
nouveau village, le suit, examine l'endroit où le joueur lui parle (règles de la génération naturelle, zone/SiteRules)
et y fonde le village, ou dit pourquoi l'endroit ne convient pas.

Sorties :
    Server/NPC/Roles/Nakasar/Peuples/Nakasar_Peuples_<Peuple>_Settler.json         il attend près du cœur
    Server/NPC/Roles/Nakasar/Peuples/Nakasar_Peuples_<Peuple>_Settler_Follow.json  il suit le joueur
    Server/Nakasar/Dialogues/Colon/Colon.json
    bloc « Colon » en tête des deux fichiers .lang

Les rôles copient le cueilleur du peuple (tools/generate_quests.py : apparence vanilla, ne se bat pas) ; seule la
conduite change. Usage : python3 tools/generate_settlers.py
"""
import copy
import json
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
RES = ROOT / "src/main/resources/Server"
ROLES = RES / "NPC/Roles/Nakasar/Peuples"
DIALOGUES = RES / "Nakasar/Dialogues/Colon"
LANG_BEGIN = "# ---- Colon : fonder un village (généré par tools/generate_settlers.py, ne pas modifier à la main) ----"
LANG_END = "# ---- Fin du colon ----"

PEOPLES = {
    "Kweebec": ("Colon kweebec", "Kweebec settler", "herbe", "grass"),
    "Trork": ("Colon trork", "Trork settler", "herbe", "grass"),
    "Feran": ("Colon feran", "Feran settler", "sable", "sand"),
    "Renonce": ("Colon renoncé", "Forsworn settler", "neige ou terre froide", "snow or cold soil"),
    "Slothian": ("Colon slothian", "Slothian settler", "cendre, boue sèche ou terre brûlée", "ash, dry mud or burnt soil"),
}

FR = {}
EN = {}


def t(key, fr, en):
    FR[key] = fr
    EN[key] = en


def follow_role(gatherer, pid):
    role = copy.deepcopy(gatherer)
    role["$Comment"] = (f"Colon {pid} qui suit le joueur (outpost/Settlers), généré par tools/generate_settlers.py à partir du "
                        "cueilleur du peuple. Il suit le joueur le plus proche à moins de 40 blocs ; le Java le ramène près "
                        "du joueur qu'il accompagne s'il est distancé. Ne se bat pas ; régénération vanilla hors combat (PNJ amical).")
    role["NameTranslationKey"] = f"nakasar_peuples.npc.{pid}_Settler.name"
    sensor = role["Instructions"][0]["Instructions"][0]["Sensor"]
    assert sensor["Type"] == "Player", pid
    sensor["Range"] = 40
    return role


def idle_role(gatherer, pid):
    role = copy.deepcopy(gatherer)
    role["$Comment"] = (f"Colon {pid} qui attend près du cœur d'un village au palier max (outpost/Settlers), généré par "
                        "tools/generate_settlers.py à partir du cueilleur du peuple. Il flâne autour de son poste (point "
                        "d'attache posé par le Java) ; lui parler ouvre le dialogue Colon. Régénération vanilla hors combat (PNJ amical).")
    role["NameTranslationKey"] = f"nakasar_peuples.npc.{pid}_Settler.name"
    role["Instructions"][0]["Instructions"] = [
        {
            "$Comment": "Loin de son poste : il y retourne.",
            "Sensor": {"Type": "Leash", "Range": 4},
            "BodyMotion": {"Type": "Seek", "RelativeSpeed": 0.5, "SlowDownDistance": 2, "StopDistance": 1, "UsePathfinder": True},
        },
        {
            "$Comment": "Il flâne autour de son poste.",
            "BodyMotion": {"Type": "WanderInCircle", "Radius": 2, "RelativeSpeed": 0.3, "MaxHeadingChange": 50},
        },
    ]
    return role


def dialogue():
    k = "nakasar_peuples.dialogue.Colon."
    t("dialogue.Colon.npc", "Colon", "Settler")
    t("dialogue.Colon.role", "Prêt à fonder un village", "Ready to found a village")

    def resp(key, fr, en, effects=None, nxt=None, hint=None):
        t(f"dialogue.Colon.{key}", fr, en)
        r = {"TextKey": k + key}
        if hint:
            r["HintKey"] = k + hint
        if effects:
            r["Effects"] = [{"Type": e} for e in effects]
        if nxt:
            r["Next"] = nxt
        return r

    def node(nid, fr, en, responses):
        key = nid[0].lower() + nid[1:] + "Texte"
        t(f"dialogue.Colon.{key}", fr, en)
        return {"Id": nid, "TextKey": k + key, "Responses": responses}

    t("dialogue.Colon.hintFound", "le village est fondé tout de suite", "the village is founded right away")
    t("dialogue.Colon.hintFollow", "il te suit", "follows you")
    t("dialogue.Colon.hintHome", "il rentre au village", "goes back to the village")
    search = lambda: resp("chercher", "Cherchons encore.", "Let's keep looking.")
    home = lambda: resp("rentrer", "Rentre au village, je reviendrai te chercher.", "Go back to the village, I'll come for you.",
                        ["SettlerHome"], hint="hintHome")
    reasons = [
        ("TropPresPeuple", "TOO_CLOSE_SAME", "Trop près d'un autre village des nôtres : chacun a besoin de ses terres, de ses chasses. Allons plus loin.",
         "Too close to another village of ours: each needs its own land and hunting grounds. Let's go further."),
        ("TropPresAutre", "TOO_CLOSE_OTHER", "Un autre peuple vit tout près d'ici. Je ne veux pas m'installer sur le pas de sa porte.",
         "Another people lives close by. I won't settle on their doorstep."),
        ("Prevu", "PLANNED", "Quelqu'un prépare déjà une fondation tout près d'ici. Cherchons ailleurs.",
         "Someone is already preparing a foundation close by. Let's look elsewhere."),
        ("HorsZone", "OUT_OF_ZONE", "Ces terres ne sont pas celles de mon peuple. Ramène-moi dans notre contrée.",
         "These are not my people's lands. Take me back to our region."),
        ("Rivage", "SHORE", "Trop près de la mer : les tempêtes emporteraient nos huttes. Allons dans les terres.",
         "Too close to the sea: storms would sweep our huts away. Let's go inland."),
        ("Eau", "WATER", "Il y a trop d'eau ici : on ne bâtit pas un village les pieds dans l'eau.",
         "There is too much water here: one does not build a village with wet feet."),
        ("Sol", "GROUND", "Cette terre ne convient pas à mon peuple. Il nous faut un sol à nous.",
         "This soil doesn't suit my people. We need ground of our own."),
        ("Relief", "RELIEF", "Le terrain est trop accidenté pour une place et des maisons. Trouvons plus plat.",
         "The ground is too rough for a square and houses. Let's find flatter land."),
        ("Examen", None, "Je n'arrive pas à bien voir le terrain d'ici. Avançons un peu.",
         "I can't get a good look at the land from here. Let's move a little."),
    ]
    entries = [{"Node": "Ici", "Conditions": [{"Type": "SettlerSite", "Reason": "OK"}]}]
    for nid, reason, _, _ in reasons:
        cond = {"Type": "SettlerSite"}
        if reason:
            cond["Reason"] = reason
        entries.append({"Node": nid, "Conditions": [cond]})
    entries.append({"Node": "Accueil"})
    nodes = [
        node("Accueil", "Notre village est devenu un bourg, et certains d'entre nous rêvent de nouvelles terres. "
                        "M'aideras-tu à trouver où fonder un village ?",
             "Our village has become a town, and some of us dream of new lands. Will you help me find where to found a village?",
             [resp("aider", "Je t'aide : suis-moi.", "I'll help you: follow me.", ["SettlerFollow"], "Suivre", "hintFollow"),
              resp("plusTard", "Pas maintenant.", "Not now.")]),
        node("Suivre", "Merci ! Mène-moi où tu veux. Loin des autres villages, sur une terre des nôtres, et parle-moi quand "
                       "l'endroit te plaît.",
             "Thank you! Lead me wherever you like. Far from other villages, on our kind of land, and talk to me when you like the place.",
             [resp("enRoute", "En route.", "Let's go.")]),
        node("Ici", "Cet endroit me plaît : assez loin des autres, la bonne terre, pas d'eau. Fondons-nous le village ici ? "
                    "Les miens n'attendent que mon signal.",
             "I like this place: far enough from the others, good soil, no water. Shall we found the village here? "
             "My people are only waiting for my signal.",
             [resp("fonder", "Fondons le village ici.", "Let's found the village here.", ["SettlerFound"], hint="hintFound"),
              search(), home()]),
    ]
    for nid, _, fr, en in reasons:
        nodes.append(node(nid, fr, en, [search(), home()]))
    return {
        "$Comment": "Le colon d'un village au palier max (outpost/Settlers), généré par tools/generate_settlers.py. Les entrées "
                    "SettlerSite lisent l'examen du site fait quand le joueur qu'il suit lui parle (zone/SiteRules) ; le détail "
                    "(distances, pourcentages) est aussi dit dans le tchat.",
        "NpcNameKey": k + "npc",
        "RoleKey": k + "role",
        "Entries": entries,
        "Nodes": nodes,
    }


def texts():
    s = "settler."
    t(s + "busy", "Ce colon accompagne déjà quelqu'un d'autre.", "This settler is already travelling with someone else.")
    t(s + "why", "Le colon : {reason}", "The settler: {reason}")
    t(s + "lost", "Votre colon a dû rentrer à {village}. Il vous y attend.", "Your settler had to go back to {village}. They wait for you there.")
    t(s + "already", "Un colon de {village} vous suit déjà.", "A settler from {village} is already following you.")
    t(s + "follows", "Le colon de {village} vous suit. Parlez-lui là où vous voulez fonder un village.",
      "The settler from {village} follows you. Talk to them where you want to found a village.")
    t(s + "founding", "Le colon plante le premier piquet : les {people} s'installent…", "The settler drives in the first stake: the {people} settle in…")
    t(s + "founded", "Village fondé : {name}, chez les {people}.", "Village founded: {name}, among the {people}.")
    t(s + "unstuck", "Les nouveaux bâtiments vous ont poussé un peu plus loin.", "The new buildings pushed you a little further away.")
    t(s + "home", "Le colon rentre à {village} et vous y attendra.", "The settler goes back to {village} and will wait for you there.")
    t(s + "failed", "Les colons n'ont pas pu s'installer ({reason}). Le colon est rentré à son village.",
      "The settlers could not settle ({reason}). The settler went back to their village.")
    p = s + "site."
    t(p + "ok", "l'endroit convient.", "this place will do.")
    t(p + "tooCloseSame", "trop près de {name} ({distance} blocs, il en faut {min} entre deux villages {people}).",
      "too close to {name} ({distance} blocks, two {people} villages need {min}).")
    t(p + "tooCloseOther", "trop près de {name}, village {people} ({distance} blocs, il en faut {min}).",
      "too close to {name}, a {people} village ({distance} blocks, {min} needed).")
    t(p + "planned", "une fondation est déjà prévue à {distance} blocs (il en faut {min}).",
      "a foundation is already planned {distance} blocks away ({min} needed).")
    t(p + "shore", "trop près de la mer : il faut la terre ferme.", "too close to the sea: solid ground is needed.")
    t(p + "outOfZone", "hors des terres du peuple (zone {zone} ; ici, zone {here}).", "outside the people's lands (zone {zone}; here, zone {here}).")
    t(p + "water", "trop d'eau sur le campement ({percent} % de bon sol, il en faut {need} %).",
      "too much water on the camp ({percent}% good soil, {need}% needed).")
    t(p + "ground", "il faut du sol du peuple ({ground}) : {percent} % ici, il en faut {need} %.",
      "the people's soil is needed ({ground}): {percent}% here, {need}% needed.")
    t(p + "relief", "terrain trop accidenté ({relief} blocs d'écart, {max} au plus).", "ground too rough ({relief} blocks of difference, {max} at most).")
    t(p + "unloaded", "le terrain autour n'est pas encore chargé.", "the surrounding land isn't loaded yet.")
    for pid, (_, _, fr, en) in PEOPLES.items():
        t(p + "soil." + pid, fr, en)
    t("command.settler.desc", "Fait venir tout de suite un colon au village le plus proche (ops)",
      "Bring a settler to the nearest village right away (ops)")
    t("command.settler.done", "Un colon attend à {name}.", "A settler waits at {name}.")


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
            raise SystemExit(f"clés déjà présentes dans {locale} (hors bloc du colon) : {dup[:10]}")
        block = [LANG_BEGIN] + [f"{k} = {v}" for k, v in table.items()] + [LANG_END, ""]
        path.write_text("\n".join(block) + text, encoding="utf-8")
        print(f"{path.relative_to(ROOT)} : {len(table)} clés du colon")


def main():
    for pid, (fr, en, _, _) in PEOPLES.items():
        gatherer = json.loads((ROLES / f"Nakasar_Peuples_{pid}_Gatherer.json").read_text(encoding="utf-8"))
        t(f"npc.{pid}_Settler.name", fr, en)
        for suffix, role in (("", idle_role(gatherer, pid)), ("_Follow", follow_role(gatherer, pid))):
            out = ROLES / f"Nakasar_Peuples_{pid}_Settler{suffix}.json"
            out.write_text(json.dumps(role, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(out.relative_to(ROOT))
    DIALOGUES.mkdir(parents=True, exist_ok=True)
    out = DIALOGUES / "Colon.json"
    out.write_text(json.dumps(dialogue(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(out.relative_to(ROOT))
    texts()
    write_langs()


if __name__ == "__main__":
    main()
