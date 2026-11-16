#!/usr/bin/env python3
"""Paliers 1 à 4 des bâtiments et carte plate de revue (Kevin, 16 novembre 2026, « parking à idées » du tableau blanc).

Deux idées regroupées :
1. « Bâtiments de base, d'artisan et avant-postes / lieux-dits : passer à 4 paliers (1-4) avec des variations
   visuelles à chaque palier. »
2. « Une map plate avec tous les prefabs posés dans des rectangles afin de pouvoir les éditer facilement. »

Retours de Kevin sur la première carte (PR #168) :
- rectangles délimités en laine rouge, de taille CONSTANTE pour les quatre paliers d'un bâtiment ;
- par défaut, TOUS les prefabs de tous les types de villages et des autres structures sur la carte ;
- pas de barrières ni de décor autour pour marquer un palier : la différence se voit sur le bâtiment lui-même
  (taille croissante, comme l'arbre du cœur kweebec qui grandit) ;
- les panneaux n'affichent rien ; un clic dessus dit le bâtiment et le palier.

Ce script écrit src/main/resources/nakasar-peuples/revue-batiments.json : la liste ordonnée des bâtiments, par
bande (un peuple, puis « Monde » pour les structures hors village), avec leurs paliers. Le Java
(dev.nakasar.hytale.peuples.review.ReviewMap, commande « /village revue ») mesure chaque prefab sur ses blocs réels,
donne à chaque bâtiment un rectangle à la taille de son plus grand palier, et y colle chaque palier au centre.

Paliers (règle n° 2 d'AGENTS.md : vanilla d'abord, rien d'autre que des prefabs vanilla et ceux du mod) :
- cœur du village : ses quatre étapes réelles (VillageHeart, palier de village 0 à 3), cumulées ;
- autres bâtiments : palier 1 = le prefab d'aujourd'hui ; paliers 2 à 4 = version de plus en plus grande de la même
  famille vanilla (CHAINS d'abord, comme maison outlander Tier0 → Tier1 → Tier2, puis les autres prefabs du même
  dossier classés par volume). Sans version plus grande, le palier reste celui d'en dessous et le panneau le dit
  (« à retoucher à la main »). Lieux-dits : les bâtiments annexes arrivent aux paliers 2 et 3.
- structures du monde vivant (auberges, camps, vestiges, Source de l'Écho) : un seul rectangle, sans palier.

    python3 tools/building_tiers.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = Path(__file__).resolve().parent
RES = ROOT / "src/main/resources/Server"
NAK = RES / "Nakasar"
JAVA = ROOT / "src/main/java/dev/nakasar/hytale/peuples"
OUT = ROOT / "src/main/resources/nakasar-peuples/revue-batiments.json"
LANG = RES / "Languages/fr-FR/nakasar_peuples.lang"

PEOPLES = ["Kweebec", "Trork", "Feran", "Renonce", "Slothian"]
PEOPLE_NAMES = {"Kweebec": "Kweebec", "Trork": "Trork", "Feran": "Feran", "Renonce": "Renoncé", "Slothian": "Slothian",
                "Monde": "Monde"}
ZONE_OF = {1: "zone 1", 2: "zone 2 (désert)", 3: "zone 3 (givre)", 4: "zone 4 (Slothians)"}
CATEGORIES = ["Coeur", "Base", "Artisan", "Projet", "AvantPoste", "LieuDit", "Auberge", "Camp", "Vestige", "Source"]
CATEGORY_NAMES = {"Coeur": "Cœur du village", "Base": "Bâtiment de base", "Artisan": "Bâtiment d'artisan",
                  "Projet": "Projet de terrain", "AvantPoste": "Avant-poste", "LieuDit": "Lieu-dit",
                  "Auberge": "Auberge", "Camp": "Campement", "Vestige": "Vestige", "Source": "Source de l'Écho"}
# Catégories à quatre paliers (les projets de terrain E1/E2 sont des bâtiments d'artisan) ; les autres n'ont qu'un
# rectangle.
TIERED = {"Coeur", "Base", "Artisan", "Projet", "AvantPoste", "LieuDit"}

NPC = "Npc/"


# ---- Familles vanilla : version plus grande d'un prefab ----

def _house_outlander(m):
    k, n = int(m.group(1)), int(m.group(2))
    return [f"{NPC}Outlander/Houses/Tier{min(k + d, 3)}/Outlander_Houses_Tier{min(k + d, 3)}_{n:03d}" for d in (1, 2, 3)]


def _tower_outlander(m):
    k, n = int(m.group(1)), int(m.group(2))
    return [f"{NPC}Outlander/Towers/Tier{min(k + d, 3)}/Outlander_Towers_Tier{min(k + d, 3)}_{n:03d}" for d in (1, 2, 3)]


def _watch_trork(m):
    k, n = int(m.group(1)), int(m.group(2))
    return [f"{NPC}Trork/Tier_{min(k + d, 3)}/Watchtower/Trork_Tier_{min(k + d, 3)}_Watchtower_{n:03d}" for d in (1, 2, 3)]


# Échelles explicites (familles réparties sur plusieurs dossiers) : versions de plus en plus grandes, à la suite.
CHAINS = [
    (r"^Npc/Outlander/Houses/Tier(\d)/Outlander_Houses_Tier\d_(\d+)$", _house_outlander),
    (r"^Npc/Outlander/Towers/Tier(\d)/Outlander_Towers_Tier\d_(\d+)$", _tower_outlander),
    (r"^Npc/Trork/Tier_(\d)/Watchtower/Trork_Tier_\d_Watchtower_(\d+)$", _watch_trork),
    (r"^Npc/Trork/Tier_2/Store/Trork_Tier_2_Store_001$",
     lambda m: [NPC + "Trork/Tier_3/Store/Trork_Tier_3_Store_001", NPC + "Trork/Tier_3/Store/Trork_Tier_3_Store_002"]),
    (r"^Npc/Kweebec/Redwood/Small_Plot/House/Kweebec_Redwood_Small_Plot_House_\d+$",
     lambda m: [NPC + "Kweebec/Redwood/Normal_Plot/House/Kweebec_Redwood_Normal_Plot_House_001",
                NPC + "Kweebec/Redwood/Normal_Plot/House/Kweebec_Redwood_Normal_Plot_House_002"]),
    (r"^Npc/Kweebec/Redwood/Small_Plot/Farm/Kweebec_Redwood_Small_Plot_Farm_\d+$",
     lambda m: [NPC + "Kweebec/Redwood/Normal_Plot/Farm/Kweebec_Redwood_Normal_Plot_Farm_003",
                NPC + "Kweebec/Redwood/Normal_Plot/Farm/Kweebec_Redwood_Normal_Plot_Farm_001"]),
    (r"^Npc/Kweebec/Oak/Garden/Small/Kweebec_Oak_Garden_Small_001$",
     lambda m: [NPC + "Kweebec/Oak/Garden/Medium/Kweebec_Oak_Garden_Medium_001",
                NPC + "Kweebec/Oak/Garden/Large/Kweebec_Oak_Garden_Large_001",
                NPC + "Kweebec/Oak/Garden/Large/Kweebec_Oak_Garden_Large_003"]),
    (r"^Npc/Kweebec/Oak/Garden/Medium/Kweebec_Oak_Garden_Medium_001$",
     lambda m: [NPC + "Kweebec/Oak/Garden/Large/Kweebec_Oak_Garden_Large_001",
                NPC + "Kweebec/Oak/Garden/Large/Kweebec_Oak_Garden_Large_003"]),
    # Maisons-arbres kweebec : petite maison → grande maison (l'arbre grandit).
    (r"^Npc/Kweebec/Oak/Houses_Small/Kweebec_Oak_Houses_Small_001$",
     lambda m: [NPC + "Kweebec/Oak/Houses_Small/Kweebec_Oak_Houses_Small_002",
                NPC + "Kweebec/Oak/Houses_Large/Kweebec_Oak_Houses_Large_001",
                NPC + "Kweebec/Oak/Houses_Large/Kweebec_Oak_Houses_Large_002"]),
    (r"^Npc/Kweebec/Oak/Houses_Small/Kweebec_Oak_Houses_Small_002$",
     lambda m: [NPC + "Kweebec/Oak/Houses_Large/Kweebec_Oak_Houses_Large_001",
                NPC + "Kweebec/Oak/Houses_Large/Kweebec_Oak_Houses_Large_002"]),
    (r"^Npc/Slothian/Disabled/House/Small/Slothian_Disabled_House_Small_(\d+)$",
     lambda m: [f"{NPC}Slothian/Disabled/House/Medium/Slothian_Disabled_House_Medium_{int(m.group(1)):03d}",
                f"{NPC}Slothian/Disabled/House/Medium/Tall/Slothian_Disabled_House_Medium_Tall_{(int(m.group(1)) - 1) % 2 + 1:03d}"]),
    (r"^Npc/Slothian/Disabled/House/Medium/Slothian_Disabled_House_Medium_(\d+)$",
     lambda m: [f"{NPC}Slothian/Disabled/House/Medium/Tall/Slothian_Disabled_House_Medium_Tall_{(int(m.group(1)) - 1) % 2 + 1:03d}"]),
    (r"^Npc/Slothian/Disabled/Gate/Slothian_Disabled_Gate_(\d+)$",
     lambda m: [NPC + "Slothian/Disabled/Gate/Rich/Slothian_Disabled_Gate_Rich_001",
                NPC + "Slothian/Disabled/Gate/Rich/Slothian_Disabled_Gate_Rich_002"]),
    (r"^Npc/Feran/Tier2/Hut/Feran_Tier2_Hut_00[123]$",
     lambda m: [NPC + "Feran/Portals_Oasis/Hut/Feran_Tier2_Hut_004", NPC + "Feran/Portals_Oasis/Hut/Feran_Tier2_Hut_005"]),
    (r"^Npc/Feran/Portals_Oasis/Hut/Feran_Tier2_Hut_00[123]$",
     lambda m: [NPC + "Feran/Portals_Oasis/Hut/Feran_Tier2_Hut_004", NPC + "Feran/Portals_Oasis/Hut/Feran_Tier2_Hut_005"]),
    # Enclos du mod : enclos de plus en plus grand (tools/generate_pens.py, TIER_HALF).
    (r"^Nakasar/Peuples/Pens/(\w+)_Pen$",
     lambda m: [f"Nakasar/Peuples/Pens/{m.group(1)}_Pen_T{t}" for t in (2, 3, 4)]),
    # Tente trork → terrier → réserve → grande réserve.
    (r"^Npc/Trork/Tent/Trork_Tent_001$",
     lambda m: [NPC + "Trork/Burrow/Trork_Burrow_Trork_Burrow_001", NPC + "Trork/Tier_2/Store/Trork_Tier_2_Store_001",
                NPC + "Trork/Tier_3/Store/Trork_Tier_3_Store_001"]),
    (r"^Monuments/Incidental/Slothian/Land/Hunting/Incidental_Slothian_Slothian_Hunting_001$",
     lambda m: ["Monuments/Incidental/Slothian/Land/Hunting/Incidental_Slothian_Slothian_Hunting_002"]),
    (r"^Npc/Feran/Tier3/Huts/Feran_Tier3_Huts_001$",
     lambda m: [NPC + "Feran/Portals_Oasis/Pillar_Hut/Feran_Tier3_Hut_001", NPC + "Feran/Tier2/Hut/Feran_Tier2_Hut_002",
                NPC + "Feran/Tier2/Hut/Feran_Tier2_Hut_001"]),
]

# Dossiers dont les prefabs ne sont PAS des versions les uns des autres (pas d'échelle par volume) : formes différentes
# d'une même ressource ou décor varié, où « plus grand » ne veut pas dire « palier au-dessus ».
NO_FOLDER_LADDER = ("Npc/Kweebec/Oak/Garden_Small", "Npc/Kweebec/Autumn/Garden_Small", "Npc/Kweebec/Oak/Lampposts",
                    "Npc/Kweebec/Oak/Seats", "Npc/Outlander/Braziers", "Npc/Outlander/Spikes", "Npc/Outlander/Boats",
                    "Npc/Trork/Warning", "Npc/Trork/Trap", "Npc/Feran/Portals_Oasis/Wall", "Npc/Feran/Tier2/Wall",
                    "Npc/Feran/Tier3/Walls", "Npc/Feran/Tier2/Entrance", "Npc/Feran/Tier2/Chieftain",
                    "Npc/Feran/Tier3/Chieftain")


# Prefabs vanilla que le mod colle déjà ailleurs (donc présents dans le jeu) mais absents de vanilla-prefabs-0.7.2.txt :
# permis dans une échelle d'une pièce seule (le Java les mesure sur place).
UNMEASURED_OK = {"Monuments/Incidental/Slothian/Land/Hunting/Incidental_Slothian_Slothian_Hunting_002"}


def load_bounds():
    bounds = {}
    for line in (TOOLS / "vanilla-prefabs-0.7.2.txt").read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        p = line.split()
        if len(p) == 7:
            bounds[p[0]] = tuple(int(v) for v in p[1:])
    for f in (RES / "Prefabs").rglob("*.prefab.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        bl = [b for b in d["blocks"] if b.get("name") not in (None, "Empty")]
        if not bl:
            continue
        rel = str(f.relative_to(RES / "Prefabs")).replace("\\", "/")[: -len(".prefab.json")]
        bounds[rel] = (min(b["x"] for b in bl), max(b["x"] for b in bl), min(b["y"] for b in bl),
                       max(b["y"] for b in bl), min(b["z"] for b in bl), max(b["z"] for b in bl))
    return bounds


def load_lang():
    lang = {}
    for line in LANG.read_text(encoding="utf-8").splitlines():
        if " = " in line and not line.startswith("#"):
            k, v = line.split(" = ", 1)
            lang[k.strip()] = v.strip()
    return lang


BOUNDS = load_bounds()
LANG_FR = load_lang()


def nice(identifier):
    s = identifier.replace("_", " ").strip()
    return s[:1].upper() + s[1:].lower()


def volume(path):
    b = BOUNDS[path]
    return (b[1] - b[0] + 1) * (b[3] - b[2] + 1) * (b[5] - b[4] + 1)


def rot_rect(path, x, z, rot):
    b = BOUNDS.get(path)
    if b is None:
        return None
    x0, x1, z0, z1 = b[0], b[1], b[4], b[5]
    for _ in range(rot % 4):
        x0, x1, z0, z1 = -z1, -z0, x0, x1
    return [x + x0, x + x1, z + z0, z + z1]


def ladder(path):
    """Versions de plus en plus grandes de `path` (sans lui), d'abord CHAINS, puis le même dossier par volume."""
    for pattern, fn in CHAINS:
        m = re.match(pattern, path)
        if m:
            out = []
            for p in fn(m):
                if (p in BOUNDS or p in UNMEASURED_OK) and p != path and p not in out:
                    out.append(p)
            return out
    if path not in BOUNDS:
        return []
    folder = path.rsplit("/", 1)[0]
    if folder.startswith(NO_FOLDER_LADDER):
        return []
    me = volume(path)
    sibs = [p for p in BOUNDS if p.rsplit("/", 1)[0] == folder and p != path and volume(p) > me]
    return sorted(sibs, key=volume)


def overlaps(a, b):
    return a and b and not (a[1] + 1 < b[0] or b[1] + 1 < a[0] or a[3] + 1 < b[2] or b[3] + 1 < a[2])


# ---- Sources ----

def layout_of(people):
    for f in (NAK / "VillageLayouts").glob("*.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        if d["People"] == people:
            return d
    raise SystemExit(f"plan de village introuvable : {people}")


def heart_entry(people):
    layout = layout_of(people)
    tiers, pieces, blocks, clear = [], [], [], []
    for step in sorted(layout["Heart"]["Steps"], key=lambda s: s["Tier"]):
        for p in step.get("Pieces", []):
            pieces.append(f"{p['Prefab']} {p['X']} {p.get('Y', 0)} {p['Z']} {p.get('Rotation', 0)}")
        if step.get("Fluids"):
            pieces.append(f"{step['Fluids']} 0 0 0 0")
        # Repère du cœur : y 0 = surface de la place ; carte : dy 0 = posé sur le sol (dy = y - 1).
        for line in step.get("Set", []):
            x, y, z, rot, name = line.split()
            blocks.append(f"{x} {int(y) - 1} {z} {rot} {name}")
        for line in step.get("Clear", []):
            x, y, z, name = line.split()
            clear.append(f"{x} {int(y) - 1} {z} {name}")
        tiers.append({"Tier": step["Tier"] + 1, "Pieces": list(pieces), "Blocks": list(blocks), "Clear": list(clear),
                      "Notes": [f"étape {step['Tier']} du cœur (palier de village {step['Tier']})"]})
    return {"People": people, "Category": "Coeur", "Id": "Coeur", "Name": "Cœur du village",
            "Source": f"plan {layout_file(people).stem}", "Tiers": tiers}


def layout_file(people):
    for f in (NAK / "VillageLayouts").glob("*.json"):
        if json.loads(f.read_text(encoding="utf-8"))["People"] == people:
            return f
    return ""


def village_entries(people):
    out = []
    for b in layout_of(people)["Buildings"]:
        bid = b["Id"]
        if bid.startswith("E2_"):
            continue  # même prefab que le projet E1 (vérifié) : un seul exemplaire
        if bid.startswith("E1_"):
            cat, wid, name_id = "Projet", f"{people}_{bid}", bid[3:]
        else:
            wid, name_id = f"{people}_{bid}", bid
            cat = "Artisan" if (NAK / "Workshops" / f"{wid}.json").exists() else "Base"
        name = LANG_FR.get(f"workshop.{wid}.name") if cat != "Base" else None
        out.append({"People": people, "Category": cat, "Id": bid, "Name": name or nice(name_id),
                    "Source": f"village, palier de village {b['Tier']}", "Pieces": [(b["Prefab"], 0, 0, 0, 0)],
                    "Optional": []})
    return out


def annex_entries(people):
    out = []
    for f in sorted((NAK / "Workshops").glob(f"{people}_AP_*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        pieces = []
        for line in d["Annex"]["Prefabs"]:
            p = line.split()
            pieces.append((p[0], int(p[1]), 0, int(p[2]), int(p[3]) if len(p) > 3 else 0))
        out.append({"People": people, "Category": "AvantPoste", "Id": "AP_" + d["Annex"]["Type"],
                    "Name": LANG_FR.get(f"workshop.{f.stem}.name") or nice(d["Annex"]["Type"]),
                    "Source": "avant-poste de métier", "Pieces": pieces, "Optional": []})
    return out


def hamlet_entries(people):
    out = []
    for f in sorted((NAK / "Hamlets").glob(f"{people}_*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        main, sides = [], {}
        for line in d["Buildings"]:
            p = line.split()
            piece = (p[0], int(p[1]), 0, int(p[2]), int(p[3]))
            if p[4] == "M":
                main.append(piece)
            else:
                sides.setdefault(p[4], []).append((float(p[5]), piece))
        optional = [max(sides[s], key=lambda c: c[0])[1] for s in ("W", "E") if sides.get(s)]
        out.append({"People": people, "Category": "LieuDit", "Id": "LD_" + d["Type"],
                    "Name": LANG_FR.get(f"hamlet.type.{d['Type']}") or nice(d["Type"]), "Source": "lieu-dit",
                    "Pieces": main, "Optional": optional, "Decor": [
                        " ".join(line.split()[:4] + line.split()[4:5]) for line in d.get("Decor", [])]})
    return out


def java_prefabs(file, pattern):
    text = (JAVA / file).read_text(encoding="utf-8")
    return re.findall(pattern, text)


def world_entries():
    """Structures du monde vivant hors village : auberges, campements, vestiges, Source de l'Écho (lus dans le Java)."""
    seen = set()
    out = []

    def add(cat, path, name, source):
        if path in seen:
            return
        seen.add(path)
        ident = path.rsplit("/", 1)[-1]
        if any(o["Id"] == ident for o in out):  # même nom de fichier dans deux dossiers (tentes de réfugiés)
            ident = "_".join(path.split("/")[-2:])
        out.append({"People": "Monde", "Category": cat, "Id": ident, "Name": name, "Source": source,
                    "Pieces": [(path, 0, 0, 0, 0)], "Optional": []})

    inn = (JAVA / "world/Inns.java").read_text(encoding="utf-8")
    block = inn[inn.index("public static String prefab(People people)"):]
    block = block[:block.index("}\n")]
    for zone, path in re.findall(r'(case \d|default) -> "([^"]+)"', block):
        z = 1 if zone == "default" else int(zone.split()[1])
        add("Auberge", path, f"Auberge, {ZONE_OF[z]}", "world/Inns")
    camps = (JAVA / "world/Camps.java").read_text(encoding="utf-8")
    block = camps[camps.index("static String[] prefabs(Type type, int zone)"):]
    block = block[:block.index("public static String camperRole")]
    current = None
    for line in block.splitlines():
        m = re.search(r"case (HUNTERS|WOODCUTTERS|PROSPECTORS|MERCHANTS|REFUGEES)", line)
        if m:
            current = m.group(1)
        for path in re.findall(r'"((?:Monuments|Orbis|Npc)/[^"]+)"', line):
            names = {"HUNTERS": "chasseurs", "WOODCUTTERS": "bûcherons", "PROSPECTORS": "prospecteurs",
                     "MERCHANTS": "marchands", "REFUGEES": "réfugiés"}
            add("Camp", path, f"Campement de {names[current]}", "world/Camps")
    traces = (JAVA / "world/Traces.java").read_text(encoding="utf-8")
    for kind, label in (("RUINS", "Vestige (ruine)"), ("OLD_CAMPS", "Vestige (vieux camp)")):
        block = traces[traces.index(f"private static final String[][] {kind}"):]
        block = block[:block.index("};")]
        for path in re.findall(r'"([^"]+)"', block):
            add("Vestige", path, label, "world/Traces")
    for f in (RES / "Prefabs/Nakasar/Peuples/Oasis").glob("*.prefab.json"):
        add("Source", "Nakasar/Peuples/Oasis/" + f.name[: -len(".prefab.json")], "Source de l'Écho", "zone/EchoSpring")
    return out


# ---- Paliers ----

def grow(pieces, tier, notes):
    """Pièces du palier `tier` : chaque pièce monte de (tier - 1) crans dans son échelle, sans toucher ses voisines."""
    out = list(pieces)
    for i, (path, x, y, z, rot) in enumerate(pieces):
        steps = ladder(path)
        if not steps:
            continue
        want = steps[min(tier - 2, len(steps) - 1)] if tier >= 2 else None
        if not want:
            continue
        rect = rot_rect(want, x, z, rot)
        others = [rot_rect(p[0], p[1], p[3], p[4]) for j, p in enumerate(out) if j != i]
        if len(pieces) > 1 and (rect is None or any(overlaps(rect, o) for o in others)):
            # Version plus grande qui chevaucherait une voisine : on prend la plus grande qui tient.
            fitting = [p for p in steps[: min(tier - 1, len(steps))] if not any(
                overlaps(rot_rect(p, x, z, rot), o) for o in others)]
            if not fitting:
                continue
            want = fitting[-1]
        out[i] = (want, x, y, z, rot)
    return out


def tiers_of(e):
    if e["Category"] == "Coeur":
        return e["Tiers"]
    if e["Category"] not in TIERED:
        return [{"Tier": 0, "Pieces": [fmt(p) for p in e["Pieces"]], "Blocks": list(e.get("Decor", [])), "Clear": [],
                 "Notes": []}]
    tiers = []
    previous = None
    for tier in (1, 2, 3, 4):
        base = list(e["Pieces"])
        notes = []
        pieces = grow(base, tier, notes)
        changed = [p[0].rsplit("/", 1)[-1] for p, b in zip(pieces, base) if p[0] != b[0]]
        if changed:
            notes.append("version plus grande : " + ", ".join(changed))
        extra = []
        if tier >= 2 and e["Optional"]:
            extra.append(e["Optional"][0])
            notes.append("1er bâtiment annexe")
        if tier >= 3 and len(e["Optional"]) > 1:
            extra.append(e["Optional"][1])
            notes.append("2e bâtiment annexe")
        all_pieces = [fmt(p) for p in pieces + extra]
        if tier > 1 and all_pieces == previous:
            notes.append("pas de version vanilla plus grande : à retoucher à la main")
        previous = all_pieces
        tiers.append({"Tier": tier, "Pieces": all_pieces, "Blocks": list(e.get("Decor", [])), "Clear": [], "Notes": notes})
    return tiers


def fmt(p):
    return f"{p[0]} {p[1]} {p[2]} {p[3]} {p[4]}"


def main():
    sections = []
    for people in PEOPLES:
        entries = [heart_entry(people)] + village_entries(people) + annex_entries(people) + hamlet_entries(people)
        sections.append((people, entries))
    sections.append(("Monde", world_entries()))
    doc = {
        "$Comment": "Carte de revue des bâtiments (paliers 1 à 4), générée par tools/building_tiers.py (ne pas modifier "
                    "à la main) ; lue par dev.nakasar.hytale.peuples.review.ReviewMap (/village revue). Pièces : "
                    "« chemin dx dy dz rotation » ; blocs : « dx dy dz rotation Bloc » (dy 0 = posé sur le sol, Empty "
                    "= vider) ; Clear : « dx dy dz Bloc » retiré s'il est là.",
        "World": "nakasar_revue_batiments_v2",
        "Sections": [],
    }
    total_cells = 0
    missing = set()
    for people, entries in sections:
        rows = []
        for c in CATEGORIES:
            for e in entries:
                if e["Category"] != c:
                    continue
                tiers = tiers_of(e)
                for t in tiers:
                    for line in t["Pieces"]:
                        path = line.split()[0]
                        if path not in BOUNDS and not path.startswith(("Monuments/", "Orbis/")) and not (
                                RES / "Prefabs" / (path + ".prefab.json")).exists():
                            missing.add(path)
                total_cells += len(tiers)
                rows.append({"Category": c, "CategoryName": CATEGORY_NAMES[c], "Id": e["Id"], "Name": e["Name"],
                             "Source": e["Source"], "Tiers": tiers})
        doc["Sections"].append({"People": people, "Name": PEOPLE_NAMES[people], "Rows": rows})
    if missing:
        raise SystemExit("Prefabs inconnus : " + ", ".join(sorted(missing)))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sections_json = []
    for s in doc["Sections"]:
        rows = ",\n".join("    " + json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in s["Rows"])
        sections_json.append(f'  {{"People":{json.dumps(s["People"])},"Name":{json.dumps(s["Name"], ensure_ascii=False)},'
                             f'"Rows":[\n{rows}\n  ]}}')
    OUT.write_text("{\n" + f' "$Comment": {json.dumps(doc["$Comment"], ensure_ascii=False)},\n'
                   + f' "World": {json.dumps(doc["World"])},\n "Sections": [\n' + ",\n".join(sections_json)
                   + "\n ]\n}\n", encoding="utf-8")
    print(f"{sum(len(s['Rows']) for s in doc['Sections'])} bâtiments et structures, {total_cells} rectangles → "
          f"{OUT.relative_to(ROOT)}")
    for s in doc["Sections"]:
        counts = {}
        flat = 0
        for r in s["Rows"]:
            counts[r["Category"]] = counts.get(r["Category"], 0) + 1
            flat += sum(1 for t in r["Tiers"] if any("à retoucher" in n for n in t["Notes"]))
        print(f"  {s['Name']}: {counts} ; paliers sans version plus grande : {flat}")


if __name__ == "__main__":
    main()
