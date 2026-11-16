#!/usr/bin/env python3
"""Génère les assets des lieux-dits (Java world/Hamlets, world/HamletTrips ; données tools/hamlets.py).

Sorties :
    Server/Nakasar/Hamlets/<Peuple>_<Type>.json                    composition et emprise de chaque lieu-dit
    Server/NPC/Roles/Nakasar/Peuples/Nakasar_Peuples_<Peuple>_Hamlet_{Keeper,Worker,Sentry}.json
    Server/Nakasar/Dialogues/Monde/Monde_LieuDit_<Type>.json, Monde_Marchand_LieuDit.json
    Server/BarterShops/Nakasar_Peuples_Hamlet_<Peuple>_<Type>[_Anime].json
    bloc « Lieux-dits » en tête des deux fichiers .lang

Rôles Nakasar_Peuples_* : aucune régénération (VillageNoRegenSystem, règle n° 1). Prefabs, apparences et objets
vanilla (règle n° 2). Usage : python3 tools/generate_hamlets.py
"""
import json
from pathlib import Path

import generate_world_life as gwl
import hamlets
import outposts

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
RES = ROOT / "src/main/resources/Server"
ROLES = RES / "NPC/Roles/Nakasar/Peuples"
DIALOGUES = RES / "Nakasar/Dialogues/Monde"
HAMLETS = RES / "Nakasar/Hamlets"
LANG_BEGIN = "# ---- Lieux-dits (généré par tools/generate_hamlets.py, ne pas modifier à la main) ----"
LANG_END = "# ---- Fin des lieux-dits ----"
PEOPLES = ["Kweebec", "Trork", "Feran", "Renonce", "Slothian"]
PEOPLE_NAMES = {p: (gwl.PEOPLES[p][0], gwl.PEOPLES[p][1]) for p in PEOPLES}

FR = {}
EN = {}
ERRORS = []


def t(key, fr, en):
    if key in FR:
        raise SystemExit(f"clé en double : {key}")
    FR[key] = fr
    EN[key] = en
    return "nakasar_peuples." + key


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(path.relative_to(ROOT))


def load_ids(name):
    return {line.strip() for line in (TOOLS / name).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")}


ITEMS = load_ids("vanilla-item-ids-0.7.2.txt")
BLOCKS = load_ids("vanilla-block-ids-0.7.2.txt")


def bounds():
    out = {}
    for line in (TOOLS / "vanilla-prefabs-0.7.2.txt").read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 7 and not line.startswith("#"):
            try:
                out[parts[0]] = tuple(int(v) for v in parts[1:])
            except ValueError:
                pass
    return out


# ---- Composition ----

def layout(people, kind, known):
    """Lignes « chemin x z rot côté chance x0 x1 z0 z1 haut » du lieu-dit, dans le repère local de sa place."""
    lines = []
    main = None
    boxes = {}
    for path, side, chance in hamlets.BUILDINGS[people][kind]:
        b = known.get(path)
        if b is None:
            ERRORS.append(f"{people}_{kind} : prefab vanilla inconnu ou non mesuré {path}")
            continue
        x0, x1, _y0, y1, z0, z1 = b
        if side is None:
            if main is not None:
                ERRORS.append(f"{people}_{kind} : deux bâtiments principaux")
            px, pz = -((x0 + x1) // 2), -hamlets.MAIN_GAP - z1
            main = (px + x0, px + x1, pz + z0, pz + z1)
        else:
            if main is None:
                ERRORS.append(f"{people}_{kind} : le bâtiment principal doit venir en premier")
                continue
            mid = (main[2] + main[3]) // 2
            pz = min(mid - (z0 + z1) // 2, main[3] - z1)
            px = main[0] - hamlets.SIDE_GAP - x1 if side == "W" else main[1] + hamlets.SIDE_GAP - x0
        box = (px + x0, px + x1, pz + z0, pz + z1)
        for other_side, others in boxes.items():
            if other_side == side:
                continue
            for o in others:
                if not (box[1] < o[0] or o[1] < box[0] or box[3] < o[2] or o[3] < box[2]):
                    ERRORS.append(f"{people}_{kind} : {path} chevauche un autre bâtiment")
        if box[3] >= -1:
            ERRORS.append(f"{people}_{kind} : {path} empiète sur la place (z1 = {box[3]})")
        boxes.setdefault(side, []).append(box)
        lines.append(f"{path} {px} {pz} 0 {side or 'M'} {chance:g} {box[0]} {box[1]} {box[2]} {box[3]} {y1 + 1}")
    sides = {}
    for path, side, chance in hamlets.BUILDINGS[people][kind]:
        if side is not None:
            sides[side] = sides.get(side, 0) + chance
    for side, total in sides.items():
        if total > 1.0001:
            ERRORS.append(f"{people}_{kind} : chances du côté {side} au-delà de 1 ({total})")
    return lines


def goods(table, people):
    out = []
    for item, q, price in table:
        item = item.format(**outposts.MAT[people])
        if item not in ITEMS and not item.startswith("Nakasar_"):
            ERRORS.append(f"objet vanilla inconnu {item}")
        out.append((item, q, price))
    return out


def shop(sid, people, kind, busy):
    favor = gwl.FAVOR[people]
    rows = goods(hamlets.GOODS[kind], people)
    if busy:
        rows += goods(hamlets.BUSY_BY_PEOPLE.get((people, kind), hamlets.BUSY[kind]), people)
    slots = [gwl.trade(item, q, favor, price, 6) for item, q, price in rows]
    buy, n = hamlets.BUYS[kind]
    if buy not in ITEMS:
        ERRORS.append(f"objet vanilla inconnu {buy}")
    slots.append(gwl.trade(favor, 1, buy, n, 4))
    name_fr, name_en = hamlets.NAMES[kind][:2]
    pfr, pen = PEOPLE_NAMES[people]
    write(RES / f"BarterShops/{sid}.json", {
        "$Comment": f"Troc du lieu-dit {name_fr} ({people}){' animé' if busy else ''}, généré par tools/generate_hamlets.py : "
                    "faveurs du peuple contre marchandises vanilla ; ouvert au rang Toléré dans le village du lieu-dit.",
        "DisplayNameKey": f"nakasar_peuples.barter.{sid[len('Nakasar_Peuples_'):]}.title",
        "RefreshInterval": {"Days": 2},
        "RestockHour": 6,
        "TradeSlots": slots,
    })
    suffix = " (animé)" if busy else ""
    t(f"barter.{sid[len('Nakasar_Peuples_'):]}.title", f"{name_fr} {pfr}{suffix}", f"{pen} {name_en.lower()}{' (lively)' if busy else ''}")


def hamlet_assets():
    known = bounds()
    for people in PEOPLES:
        for kind in hamlets.types(people):
            hid = f"{people}_{kind}"
            sid = f"Nakasar_Peuples_Hamlet_{hid}"
            shop(sid, people, kind, False)
            shop(sid + "_Anime", people, kind, True)
            residents = [f"Nakasar_Peuples_{people}_Hamlet_{r}" for r in hamlets.RESIDENTS[kind]]
            decor = [] if people == "Kweebec" and kind == "Forge" else hamlets.DECOR.get(kind, [])
            for line in decor:
                block = line.split()[4]
                if block not in BLOCKS:
                    ERRORS.append(f"{hid} : bloc vanilla inconnu {block}")
            write(HAMLETS / f"{hid}.json", {
                "$Comment": f"Lieu-dit {hamlets.NAMES[kind][0]} ({people}), généré par tools/generate_hamlets.py depuis "
                            "tools/hamlets.py. Bâtiments : « chemin x z rot côté chance x0 x1 z0 z1 haut » dans le repère de la "
                            "place (bâtiment principal au nord) ; un tirage par côté (W, E) choisit au plus un bâtiment.",
                "People": people,
                "Type": kind,
                "NameKey": f"nakasar_peuples.hamlet.type.{kind}",
                "Icon": hamlets.NAMES[kind][2],
                "Rule": hamlets.RULES[kind],
                "Weight": hamlets.WEIGHTS[kind],
                "Buildings": layout(people, kind, known),
                "Decor": decor,
                "Residents": residents,
                "Dialogue": f"Monde_LieuDit_{kind}",
                "Shop": sid,
                "ShopBusy": sid + "_Anime",
            })


# ---- Rôles ----

ROLE_TEXTS = {
    "Keeper": ("Tenancier", "Keeper", "Tenancier d'un lieu-dit (world/Hamlets) : on lui parle pour troquer."),
    "Worker": ("Travailleur", "Worker", "Habitant d'un lieu-dit (mineur, fermier, meunier, forgeron...) : world/Hamlets."),
    "Sentry": ("Garde", "Sentry", "Garde d'une caserne de lieu-dit (world/Hamlets) ; ne se bat pas, il veille."),
}


def roles():
    for people in PEOPLES:
        pfr, pen = PEOPLE_NAMES[people]
        for kind, look in hamlets.LOOKS[people].items():
            rid = f"{people}_Hamlet_{kind}"
            fr, en, comment = ROLE_TEXTS[kind]
            role = gwl.walker(rid, comment, look, 110 if kind == "Sentry" else 90, 3, 0.5, 4)
            write(ROLES / f"Nakasar_Peuples_{rid}.json", role)
            t(f"npc.{rid}.name", f"{fr} {pfr}", f"{pen} {en.lower()}")


# ---- Dialogues ----

COMMON = "nakasar_peuples.dialogue.Monde."
RUMOUR = "Rumeur"


def node(nid, text, responses):
    return {"Id": nid, "TextKey": text, "Responses": responses}


def resp(text, action=None, next_=None, check=None):
    r = {"TextKey": text}
    if check:
        r["Conditions"] = [{"Type": "WorldCheck", "Check": check}]
    if action:
        r["Effects"] = [{"Type": "WorldAction", "Action": action}]
    if next_:
        r["Next"] = next_
    return r


def dialogue(did, comment, npc, role, nodes):
    k = f"dialogue.{did}."
    t(k + "npc", *npc)
    t(k + "role", *role)
    nodes = nodes + [node(RUMOUR, COMMON + "rumeurTexte", [
        resp(COMMON + "rumeurAutre", "Rumour", RUMOUR), resp(COMMON + "retour", None, "Accueil"), resp(COMMON + "aurevoir")])]
    write(DIALOGUES / f"{did}.json", {
        "$Comment": comment + " Généré par tools/generate_hamlets.py ; effets WorldAction et conditions WorldCheck (world/WorldDialogueTypes).",
        "NpcNameKey": f"nakasar_peuples.{k}npc",
        "RoleKey": f"nakasar_peuples.{k}role",
        "Entries": [{"Node": "Accueil"}],
        "Nodes": nodes,
    })


def dialogues():
    rumour = resp(COMMON + "rumeur", "Rumour", RUMOUR)
    bye = resp(COMMON + "aurevoir")
    troc = t("dialogue.LieuDit.troc", "Montre-moi ce que tu as.", "Show me what you have.")
    visits = t("dialogue.LieuDit.visites", "Qui vient commercer ici ?", "Who comes to trade here?")
    for kind in hamlets.TYPES:
        name_fr, name_en, _icon, hello_fr, hello_en = hamlets.NAMES[kind]
        did = f"Monde_LieuDit_{kind}"
        dialogue(did, f"Habitant d'un lieu-dit {name_fr} : troc du lieu-dit (élargi quand il est animé), marchands venus, rumeurs.",
                 ("Habitant", "Resident"), (name_fr, name_en), [
            node("Accueil", t(f"dialogue.{did}.accueil", hello_fr, hello_en), [
                resp(troc, "HamletShop"), resp(visits, "HamletVisits", "Accueil"), rumour, bye]),
        ])
    did = "Monde_Marchand_LieuDit"
    dialogue(did, "Marchand ou caravanier d'un village venu commercer dans un lieu-dit (world/HamletTrips).",
             ("Marchand", "Merchant"), ("Marchand en tournée", "Merchant on a round"), [
        node("Accueil", t(f"dialogue.{did}.accueil",
                          "Je fais la tournée des lieux-dits pour mon village. On achète ici, on revend là-bas.",
                          "I do the rounds of the hamlets for my village. We buy here, we sell back home."), [
            resp(t(f"dialogue.{did}.troc", "Que transportes-tu ?", "What are you carrying?"), "TripShop"),
            resp(t(f"dialogue.{did}.ou", "Où vas-tu ?", "Where are you heading?"), "TripWhere", "Accueil"),
            rumour, bye]),
    ])


# ---- Textes du Java ----

def texts():
    for kind in hamlets.TYPES:
        t(f"hamlet.type.{kind}", hamlets.NAMES[kind][0], hamlets.NAMES[kind][1])
    p = "hamlet."
    rows = [
        ("discover", "Lieu-dit : {name} ({people})", "Hamlet: {name} ({people})"),
        ("discoverLine", "Un lieu-dit {people}, rattaché à {village}. Les marchands des villages voisins y viennent commercer.",
         "A {people} hamlet, tied to {village}. Merchants from nearby villages come here to trade."),
        ("lively", "{name} est animé : les marchands se pressent, son troc s'élargit.",
         "{name} is lively: merchants crowd in, its wares grow."),
        ("visits.none", "Personne n'est venu depuis une semaine. Les routes sont calmes.",
         "Nobody has come in a week. The roads are quiet."),
        ("visits.some", "{count} marchands en 7 jours ; dernier venu : {village}.",
         "{count} merchants in 7 days; last one from {village}."),
        ("visits.lively", "{count} marchands en 7 jours ; dernier venu : {village}. On est animés !",
         "{count} merchants in 7 days; last one from {village}. We're lively!"),
        ("shopRank", "Je ne commerce qu'avec les amis de {village} (rang Toléré).", "I only trade with friends of {village} (Tolerated rank)."),
        ("trip.where.out", "Je vais à {hamlet}, puis je rentre à {village}.", "I'm going to {hamlet}, then back to {village}."),
        ("trip.where.stay", "Je commerce ici jusqu'à {hour} h, puis je rentre à {village}.", "I'm trading here until {hour}:00, then heading back to {village}."),
        ("trip.where.back", "Je rentre à {village} avec ce que j'ai acheté à {hamlet}.", "I'm heading back to {village} with what I bought at {hamlet}."),
        ("trip.lost", "Le marchand parti pour {hamlet} n'est jamais revenu.", "The merchant who left for {hamlet} never came back."),
        ("trip.home", "Retour de {hamlet} : le commerce fait grandir le village (+{essor} d'essor).",
         "Back from {hamlet}: trade helps the village grow (+{essor} growth)."),
        ("rumour", "On dit qu'il y a un lieu-dit {people}, {name}, à {distance} blocs vers {dir}.",
         "They say there's a {people} hamlet, {name}, {distance} blocks to the {dir}."),
        ("rumour.trip", "Un marchand de {village} est en route pour {hamlet}.", "A merchant from {village} is on the way to {hamlet}."),
        # Commande /monde
        ("cmd.hamlet.desc", "État du lieu-dit le plus proche, ou en prévoir un ici (opérateurs).",
         "State of the nearest hamlet, or plan one here (operators)."),
        ("cmd.hamlet.arg", "Genre du lieu-dit à prévoir (Mine, Ferme, Moulin...).", "Kind of hamlet to plan (Mine, Ferme, Moulin...)."),
        ("cmd.trip.desc", "Un marchand du village le plus proche part vers le lieu-dit le plus proche (opérateurs).",
         "A merchant from the nearest village leaves for the nearest hamlet (operators)."),
        ("cmd.trip.arg", "caravane pour trois porteurs.", "caravane for three carriers."),
        ("cmd.blocked", "Pas de lieu-dit ici : {why}.", "No hamlet here: {why}."),
        ("cmd.none", "Aucun lieu-dit à moins de {range} blocs.", "No hamlet within {range} blocks."),
        ("cmd.state", "Lieu-dit {name} ({people}, {village}) en {x}, {z} : {stage}, {visits} marchands en 7 jours.",
         "Hamlet {name} ({people}, {village}) at {x}, {z}: {stage}, {visits} merchants in 7 days."),
        ("cmd.stage.0", "pas encore posé", "not placed yet"),
        ("cmd.stage.1", "posé", "placed"),
        ("cmd.stage.2", "aucune place trouvée", "no site found"),
        ("cmd.created", "Lieu-dit {name} prévu en {x}, {z} : il se pose à ton approche.", "Hamlet {name} planned at {x}, {z}: it appears as you approach."),
        ("cmd.unknownType", "Genre inconnu : {type} ({types}).", "Unknown kind: {type} ({types})."),
        ("cmd.tripStarted", "Marchand de {village} parti pour {hamlet}.", "Merchant from {village} left for {hamlet}."),
        ("cmd.tripFailed", "Aucun village à moins de {range} blocs de ce lieu-dit, ou un marchand y va déjà.",
         "No village within {range} blocks of this hamlet, or a merchant is already on the way."),
        ("cmd.trips", "{count} marchands en tournée vers les lieux-dits.", "{count} merchants on hamlet rounds."),
        ("cmd.tripLine", "{kind} de {village} vers {hamlet} : {leg}", "{kind} from {village} to {hamlet}: {leg}"),
        ("cmd.leg.0", "à l'aller ({at}/{length})", "outbound ({at}/{length})"),
        ("cmd.leg.1", "sur place", "on site"),
        ("cmd.leg.2", "au retour ({at}/{length})", "heading home ({at}/{length})"),
        ("state", "Lieux-dits : {count} ({built} posés), {trips} marchands en tournée.", "Hamlets: {count} ({built} placed), {trips} merchants on rounds."),
    ]
    for key, fr, en in rows:
        t(p + key, fr, en)


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
            raise SystemExit(f"clés déjà présentes dans {locale} (hors bloc des lieux-dits) : {dup[:10]}")
        block = [LANG_BEGIN] + [f"{k} = {v}" for k, v in table.items()] + [LANG_END, ""]
        path.write_text("\n".join(block) + text, encoding="utf-8")
        print(f"{path.relative_to(ROOT)} : {len(table)} clés des lieux-dits")


def main():
    hamlet_assets()
    roles()
    dialogues()
    texts()
    if ERRORS:
        raise SystemExit("\n".join(["Erreurs :"] + ERRORS))
    write_langs()


if __name__ == "__main__":
    main()
