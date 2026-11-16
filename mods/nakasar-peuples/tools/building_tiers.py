#!/usr/bin/env python3
"""Paliers 1 à 4 des bâtiments et carte plate de revue (Kevin, 16 novembre 2026, « parking à idées » du tableau blanc).

Deux idées regroupées :
1. « Bâtiments de base, d'artisan et avant-postes / lieux-dits : passer à 4 paliers (1-4) avec des variations
   visuelles à chaque palier. »
2. « Une map plate avec tous les prefabs posés dans des rectangles afin de pouvoir les éditer facilement », un panneau
   à côté de chaque prefab qui dit ce que c'est.

Ce script compose, pour chaque bâtiment des cinq peuples, ses quatre paliers à partir des données du mod (rien à la
main) puis range le tout sur une grille. Il écrit src/main/resources/nakasar-peuples/revue-batiments.json, lu par le
Java (dev.nakasar.hytale.peuples.review.ReviewMap, commande « /village revue ») qui crée un monde plat et y colle
chaque palier dans son rectangle.

Bâtiments repris :
- « Base » : bâtiments des plans de village (VillageLayouts) qui n'ont pas de bâtiment de métier ;
- « Artisan » : bâtiments de village qui ont un bâtiment de métier (Workshops/<Peuple>_<Id>.json) ;
- « Projet » : projets des terrains E1/E2 (un seul exemplaire par projet, celui de E1) ;
- « Avant-poste » : avant-postes de métier (Workshops/<Peuple>_AP_<Type>.json, champ Annex) ;
- « Lieu-dit » : lieux-dits (Hamlets/<Peuple>_<Type>.json).
Le cœur du village a déjà ses paliers (VillageHeart) : il n'est pas repris.

Composition des paliers (règle n° 2 d'AGENTS.md : vanilla d'abord, seuls des prefabs et blocs vanilla, plus les
fanions du mod déjà faits de modèles vanilla) :
- palier 1 : le bâtiment tel qu'il est aujourd'hui ;
- palier 2 : abords soignés (sentier devant l'entrée, deux lumières aux coins avant, caisses ou pots du peuple) ;
  un lieu-dit gagne son premier bâtiment annexe ;
- palier 3 : bâtiment agrandi quand le jeu en a une version plus grande dans la même famille (CHAINS : maison
  outlander Tier0 → Tier1, tour trork Tier_1 → Tier_2...), petite pièce vanilla du peuple à côté (potager, foyer,
  brasero), clôture devant avec une barrière, fanion du peuple ; un lieu-dit gagne son second bâtiment ;
- palier 4 : version la plus riche de la famille, enclos complet du bois du peuple (barrière au sud), grandes
  lumières aux quatre coins, deux fanions, deux pièces d'accompagnement.

Repère : l'entrée des prefabs vanilla est supposée au sud (+z, comme la barrière des enclos du mod) ; Kevin retouche
à la main ce qui ne tombe pas juste. Décor « dx dy dz rot Bloc » : dy 0 = posé sur le sol, -1 = remplace le sol.

    python3 tools/building_tiers.py [--preview carte.png]
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = Path(__file__).resolve().parent
RES = ROOT / "src/main/resources/Server"
NAK = RES / "Nakasar"
OUT = ROOT / "src/main/resources/nakasar-peuples/revue-batiments.json"
LANG = RES / "Languages/fr-FR/nakasar_peuples.lang"

PEOPLES = ["Kweebec", "Trork", "Feran", "Renonce", "Slothian"]
PEOPLE_NAMES = {"Kweebec": "Kweebec", "Trork": "Trork", "Feran": "Feran", "Renonce": "Renoncé", "Slothian": "Slothian"}
CATEGORIES = ["Base", "Artisan", "Projet", "AvantPoste", "LieuDit"]
CATEGORY_NAMES = {"Base": "Bâtiment de base", "Artisan": "Bâtiment d'artisan", "Projet": "Projet de terrain",
                  "AvantPoste": "Avant-poste", "LieuDit": "Lieu-dit"}

# ---- Trousse de décor de chaque peuple (blocs vanilla, vérifiés dans vanilla-block-ids-0.7.2.txt) ----
KIT = {
    "Kweebec": {"ground": "Soil_Grass", "path": "Soil_Pathway", "light": "Furniture_Kweebec_Lantern",
                "fence": "Wood_Hardwood_Fence", "props": ["Furniture_Village_Crate", "Furniture_Village_Planter",
                                                          "Furniture_Kweebec_Stool"],
                "big_light": ("piece", "Npc/Kweebec/Oak/Lampposts/Kweebec_Oak_Lampposts_001"),
                "extra": ["Npc/Kweebec/Oak/Garden_Small/Kweebec_Oak_Garden_Small_003",
                          "Npc/Kweebec/Oak/Seats/Small/Kweebec_Oak_Seats_Small_002"],
                "pennant": "Nakasar_Peuples_Pennant_Green"},
    "Trork": {"ground": "Soil_Grass", "path": "Soil_Gravel", "light": "Furniture_Crude_Torch",
              "fence": "Wood_Deadwood_Fence", "props": ["Deco_Bone_Skulls", "Furniture_Village_Crate", "Deco_Trork_Cage"],
              "big_light": ("block", "Furniture_Crude_Brazier"),
              "extra": ["Npc/Trork/Fireplace/Trork_Fireplace_001", "Npc/Trork/Misc/Large/Trork_Misc_Large_005"],
              "pennant": "Nakasar_Peuples_Pennant_Red"},
    "Feran": {"ground": "Soil_Sand", "path": "Rock_Sandstone_Cobble", "light": "Furniture_Feran_Torch_Tall",
              "fence": "Wood_Drywood_Fence", "props": ["Furniture_Feran_Pot", "Furniture_Feran_Planter",
                                                       "Furniture_Feran_Pot_Secondary"],
              "big_light": ("block", "Furniture_Desert_Lantern_Tall"),
              "extra": ["Monuments/Incidental/Sandstone/Grass/Well/Incidental_Grass_Well_003"],
              "pennant": "Nakasar_Peuples_Pennant_Yellow"},
    "Renonce": {"ground": "Soil_Snow", "path": "Rock_Slate_Cobble", "light": "Furniture_Lumberjack_Lantern",
                "fence": "Wood_Softwood_Fence", "props": ["Furniture_Tavern_Barrel", "Furniture_Village_Crate",
                                                          "Furniture_Frozen_Castle_Pot"],
                "big_light": ("piece", "Npc/Outlander/Braziers/Outlander_Braziers_Npc_Outlander_Brazier_001"),
                "extra": ["Npc/Outlander/Braziers/Outlander_Braziers_Npc_Outlander_Brazier_001"],
                "pennant": "Nakasar_Peuples_Pennant_Blue"},
    "Slothian": {"ground": "Soil_Mud_Dry", "path": "Rock_Basalt_Cobble", "light": "Furniture_Jungle_Torch",
                 "fence": "Wood_Tropicalwood_Fence", "props": ["Furniture_Jungle_Pot", "Furniture_Jungle_Planter",
                                                               "Furniture_Jungle_Pot_Secondary"],
                 "big_light": ("block", "Furniture_Jungle_Brazier"),
                 "extra": [],
                 "pennant": "Nakasar_Peuples_Pennant_Purple"},
}

# ---- Familles vanilla : version plus grande d'un prefab aux paliers 3 et 4 ----
NPC = "Npc/"


def _house_outlander(m):
    k, n = int(m.group(1)), int(m.group(2))
    return [f"{NPC}Outlander/Houses/Tier{min(k + d, 3)}/Outlander_Houses_Tier{min(k + d, 3)}_{n:03d}" for d in (1, 2)]


def _tower_outlander(m):
    k, n = int(m.group(1)), int(m.group(2))
    return [f"{NPC}Outlander/Towers/Tier{min(k + d, 3)}/Outlander_Towers_Tier{min(k + d, 3)}_{n:03d}" for d in (1, 2)]


def _watch_trork(m):
    k, n = int(m.group(1)), int(m.group(2))
    return [f"{NPC}Trork/Tier_{min(k + d, 3)}/Watchtower/Trork_Tier_{min(k + d, 3)}_Watchtower_{n:03d}" for d in (1, 2)]


CHAINS = [
    (r"^Npc/Outlander/Houses/Tier(\d)/Outlander_Houses_Tier\d_(\d+)$", _house_outlander),
    (r"^Npc/Outlander/Towers/Tier(\d)/Outlander_Towers_Tier\d_(\d+)$", _tower_outlander),
    (r"^Npc/Trork/Tier_(\d)/Watchtower/Trork_Tier_\d_Watchtower_(\d+)$", _watch_trork),
    (r"^Npc/Trork/Tier_2/Store/Trork_Tier_2_Store_001$",
     lambda m: [NPC + "Trork/Tier_3/Store/Trork_Tier_3_Store_001", NPC + "Trork/Tier_3/Store/Trork_Tier_3_Store_002"]),
    (r"^Npc/Trork/Burrow/Trork_Burrow_Trork_Burrow_00[12]$",
     lambda m: [None, NPC + "Trork/Burrow/Trork_Burrow_Trork_Burrow_003"]),
    (r"^Npc/Kweebec/Redwood/Small_Plot/House/Kweebec_Redwood_Small_Plot_House_\d+$",
     lambda m: [NPC + "Kweebec/Redwood/Normal_Plot/House/Kweebec_Redwood_Normal_Plot_House_001",
                NPC + "Kweebec/Redwood/Normal_Plot/House/Kweebec_Redwood_Normal_Plot_House_002"]),
    (r"^Npc/Kweebec/Redwood/Normal_Plot/House/Kweebec_Redwood_Normal_Plot_House_001$",
     lambda m: [None, NPC + "Kweebec/Redwood/Normal_Plot/House/Kweebec_Redwood_Normal_Plot_House_002"]),
    (r"^Npc/Kweebec/Redwood/Small_Plot/Farm/Kweebec_Redwood_Small_Plot_Farm_\d+$",
     lambda m: [NPC + "Kweebec/Redwood/Normal_Plot/Farm/Kweebec_Redwood_Normal_Plot_Farm_003",
                NPC + "Kweebec/Redwood/Normal_Plot/Farm/Kweebec_Redwood_Normal_Plot_Farm_001"]),
    (r"^Npc/Kweebec/Oak/Garden/Small/Kweebec_Oak_Garden_Small_001$",
     lambda m: [NPC + "Kweebec/Oak/Garden/Medium/Kweebec_Oak_Garden_Medium_001",
                NPC + "Kweebec/Oak/Garden/Large/Kweebec_Oak_Garden_Large_001"]),
    (r"^Npc/Kweebec/Oak/Garden/Medium/Kweebec_Oak_Garden_Medium_001$",
     lambda m: [NPC + "Kweebec/Oak/Garden/Large/Kweebec_Oak_Garden_Large_001",
                NPC + "Kweebec/Oak/Garden/Large/Kweebec_Oak_Garden_Large_003"]),
    (r"^Npc/Kweebec/Oak/Garden/Large/Kweebec_Oak_Garden_Large_001$",
     lambda m: [None, NPC + "Kweebec/Oak/Garden/Large/Kweebec_Oak_Garden_Large_003"]),
    (r"^Npc/Kweebec/Oak/Guard_Towers/Kweebec_Oak_Guard_Towers_00[13]$",
     lambda m: [NPC + "Kweebec/Oak/Guard_Towers/Kweebec_Oak_Guard_Towers_005",
                NPC + "Kweebec/Oak/Guard_Towers/Kweebec_Oak_Guard_Towers_004"]),
    (r"^Npc/Kweebec/Oak/Guard_Towers/Kweebec_Oak_Guard_Towers_00[25]$",
     lambda m: [None, NPC + "Kweebec/Oak/Guard_Towers/Kweebec_Oak_Guard_Towers_004"]),
    (r"^Npc/Kweebec/Oak/Bunny_Area/Kweebec_Oak_Bunny_Area_003$",
     lambda m: [NPC + "Kweebec/Oak/Bunny_Area/Kweebec_Oak_Bunny_Area_001",
                NPC + "Kweebec/Oak/Bunny_Area/Kweebec_Oak_Bunny_Area_005"]),
    (r"^Npc/Kweebec/Oak/Houses_Small/Kweebec_Oak_Houses_Small_001$",
     lambda m: [None, NPC + "Kweebec/Oak/Houses_Small/Kweebec_Oak_Houses_Small_002"]),
    (r"^Npc/Slothian/Disabled/House/Small/Slothian_Disabled_House_Small_(\d+)$",
     lambda m: [f"{NPC}Slothian/Disabled/House/Medium/Slothian_Disabled_House_Medium_{int(m.group(1)):03d}",
                f"{NPC}Slothian/Disabled/House/Medium/Tall/Slothian_Disabled_House_Medium_Tall_{(int(m.group(1)) - 1) % 2 + 1:03d}"]),
    (r"^Npc/Slothian/Disabled/House/Medium/Slothian_Disabled_House_Medium_(\d+)$",
     lambda m: [None, f"{NPC}Slothian/Disabled/House/Medium/Tall/Slothian_Disabled_House_Medium_Tall_{(int(m.group(1)) - 1) % 2 + 1:03d}"]),
    (r"^Npc/Slothian/Disabled/Gate/Slothian_Disabled_Gate_(\d+)$",
     lambda m: [None, NPC + "Slothian/Disabled/Gate/Rich/Slothian_Disabled_Gate_Rich_001"]),
    (r"^Npc/Feran/Tier2/Hut/Feran_Tier2_Hut_00[123]$",
     lambda m: [None, NPC + "Feran/Portals_Oasis/Hut/Feran_Tier2_Hut_004"]),
    (r"^Npc/Feran/Portals_Oasis/Hut/Feran_Tier2_Hut_00[123]$",
     lambda m: [None, NPC + "Feran/Portals_Oasis/Hut/Feran_Tier2_Hut_005"]),
]

# Un prefab agrandi au milieu d'une composition à plusieurs pièces ne doit pas avancer de plus de 3 blocs : sinon il
# chevaucherait ses voisins, et on garde le prefab d'origine.
GROWTH = 3

# ---- Grille de la carte ----
GAP = 6          # blocs entre deux rectangles d'une rangée (le panneau du rectangle suivant y tient)
ROW_GAP = 10     # blocs entre deux rangées (panneaux devant chaque rectangle)
MARGIN = 2       # marge entre le contenu et le liseré du rectangle
PEOPLE_GAP = 40  # blocs entre deux peuples


def load_bounds():
    bounds = {}
    for line in (TOOLS / "vanilla-prefabs-0.7.2.txt").read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        p = line.split()
        if len(p) == 7:
            bounds[p[0]] = tuple(int(v) for v in p[1:])
    # Prefabs du mod (enclos) : bornes lues dans leurs blocs.
    for f in (RES / "Prefabs").rglob("*.prefab.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        bl = [b for b in d["blocks"] if b.get("name") not in (None, "Empty")]
        if not bl:
            continue
        rel = str(f.relative_to(RES / "Prefabs")).replace("\\", "/")[: -len(".prefab.json")]
        bounds[rel] = (min(b["x"] for b in bl), max(b["x"] for b in bl), min(b["y"] for b in bl),
                       max(b["y"] for b in bl), min(b["z"] for b in bl), max(b["z"] for b in bl))
    return bounds


def load_blocks():
    ids = set()
    for line in (TOOLS / "vanilla-block-ids-0.7.2.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            ids.add(line.lstrip("*"))
    for f in (RES / "Item/Items").rglob("*.json"):
        ids.add(f.stem)
    return ids


def load_lang():
    lang = {}
    for line in LANG.read_text(encoding="utf-8").splitlines():
        if " = " in line and not line.startswith("#"):
            k, v = line.split(" = ", 1)
            lang[k.strip()] = v.strip()
    return lang


BOUNDS = load_bounds()
BLOCK_IDS = load_blocks()
LANG_FR = load_lang()


def nice(identifier):
    """« Grande_Maison_Givre » → « Grande maison givre »."""
    s = identifier.replace("_", " ").strip()
    return s[:1].upper() + s[1:].lower()


def rot_bounds(b, rot):
    """Bornes (x0, x1, z0, z1) d'un prefab tourné de rot quarts de tour (même convention que PrefabRotation)."""
    x0, x1, _, _, z0, z1 = b
    for _ in range(rot % 4):
        x0, x1, z0, z1 = -z1, -z0, x0, x1
    return x0, x1, z0, z1


def piece_rect(piece):
    path, x, z, rot = piece
    b = BOUNDS.get(path)
    if b is None:
        return None
    x0, x1, z0, z1 = rot_bounds(b, rot)
    return [x + x0, x + x1, z + z0, z + z1]


def height_of(path):
    b = BOUNDS.get(path)
    return 0 if b is None else b[3]


def union(rects):
    rects = [r for r in rects if r]
    if not rects:
        return [-4, 4, -4, 4]
    return [min(r[0] for r in rects), max(r[1] for r in rects), min(r[2] for r in rects), max(r[3] for r in rects)]


def chain(path):
    for pattern, fn in CHAINS:
        m = re.match(pattern, path)
        if m:
            return [p if p in BOUNDS else None for p in fn(m)]
    return [None, None]


# ---- Sources ----

def village_entries():
    out = []
    for people in PEOPLES:
        layout = next(json.loads(f.read_text(encoding="utf-8")) for f in (NAK / "VillageLayouts").glob("*.json")
                      if json.loads(f.read_text(encoding="utf-8"))["People"] == people)
        for b in layout["Buildings"]:
            bid = b["Id"]
            if bid.startswith("E2_"):
                continue
            if bid.startswith("E1_"):
                cat, wid, name_id = "Projet", f"{people}_E1_{bid[3:]}", bid[3:]
            else:
                wid, name_id = f"{people}_{bid}", bid
                cat = "Artisan" if (NAK / "Workshops" / f"{wid}.json").exists() else "Base"
            name = LANG_FR.get(f"workshop.{wid}.name") if cat != "Base" else None
            src = f"village, palier de village {b['Tier']}" + (" (terrain E1/E2)" if cat == "Projet" else "")
            out.append({"People": people, "Category": cat, "Id": bid, "Name": name or nice(name_id), "Source": src,
                        "Pieces": [(b["Prefab"], 0, 0, 0)], "Optional": []})
    return out


def annex_entries():
    out = []
    for f in sorted((NAK / "Workshops").glob("*_AP_*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        people, t = d["People"], d["Annex"]["Type"]
        pieces = []
        for line in d["Annex"]["Prefabs"]:
            p = line.split()
            pieces.append((p[0], int(p[1]), int(p[2]), int(p[3]) if len(p) > 3 else 0))
        name = LANG_FR.get(f"workshop.{f.stem}.name") or nice(t)
        out.append({"People": people, "Category": "AvantPoste", "Id": "AP_" + t, "Name": name,
                    "Source": "avant-poste de métier", "Pieces": pieces, "Optional": []})
    return out


def hamlet_entries():
    out = []
    for f in sorted((NAK / "Hamlets").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        main, sides = [], {"W": [], "E": []}
        for line in d["Buildings"]:
            p = line.split()
            piece = (p[0], int(p[1]), int(p[2]), int(p[3]))
            side, chance = p[4], float(p[5])
            if side == "M":
                main.append(piece)
            else:
                sides.setdefault(side, []).append((chance, piece))
        # Premier bâtiment annexe au palier 2 (le plus probable de l'ouest, sinon de l'est), le second au palier 3.
        optional = []
        for side in ("W", "E"):
            if sides.get(side):
                optional.append(max(sides[side], key=lambda c: c[0])[1])
        name = LANG_FR.get(f"hamlet.type.{d['Type']}") or nice(d["Type"])
        out.append({"People": d["People"], "Category": "LieuDit", "Id": "LD_" + d["Type"], "Name": name,
                    "Source": "lieu-dit", "Pieces": main, "Optional": optional, "HamletDecor": d.get("Decor", [])})
    return out


# ---- Paliers ----

def fence_ring(x0, x1, z0, z1, wood, gate_x):
    """Clôture du bord du rectangle (coins et rotations des enclos du mod, tools/generate_pens.py), barrière au sud."""
    corner = "*" + wood + "_State_Definitions_Corner"
    blocks = []
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            if x not in (x0, x1) and z not in (z0, z1):
                continue
            if (x, z) == (x0, z0):
                name, rot = corner, 1
            elif (x, z) == (x0, z1):
                name, rot = corner, 2
            elif (x, z) == (x1, z1):
                name, rot = corner, 3
            elif (x, z) == (x1, z0):
                name, rot = corner, 0
            elif z == z1 and abs(x - gate_x) <= 1:
                name, rot = (wood + "_Gate", 0) if x == gate_x else (None, 0)
            elif z == z0:
                name, rot = wood, 2
            elif z == z1:
                name, rot = wood, 0
            elif x == x0:
                name, rot = wood, 3
            else:
                name, rot = wood, 1
            if name:
                blocks.append(f"{x} 0 {z} {rot} {name}")
    return blocks


def front_fence(x0, x1, z, wood, gate_x):
    out = []
    for x in range(x0, x1 + 1):
        if abs(x - gate_x) <= 1:
            if x == gate_x:
                out.append(f"{x} 0 {z} 0 {wood}_Gate")
            continue
        out.append(f"{x} 0 {z} 0 {wood}")
    return out


def tier_compositions(e):
    people = e["People"]
    kit = KIT[people]
    base = list(e["Pieces"])
    optional = list(e.get("Optional", []))
    multi = len(base) + len(optional) > 1
    tiers = []
    for tier in (1, 2, 3, 4):
        pieces = list(base)
        notes = []
        # Lieux-dits : bâtiments annexes.
        if tier >= 2 and optional:
            pieces.append(optional[0])
            notes.append("1er bâtiment annexe")
        if tier >= 3 and len(optional) > 1:
            pieces.append(optional[1])
            notes.append("2e bâtiment annexe")
        # Prefab principal agrandi (famille vanilla).
        if tier >= 3 and pieces:
            path, x, z, rot = pieces[0]
            bigger = chain(path)[tier - 3]
            if bigger is None and tier == 4:
                bigger = chain(path)[0]
            if bigger:
                old = piece_rect(pieces[0])
                new = piece_rect((bigger, x, z, rot))
                fits = old is None or new is None or not multi or (
                    new[0] >= old[0] - GROWTH and new[1] <= old[1] + GROWTH
                    and new[2] >= old[2] - GROWTH and new[3] <= old[3] + GROWTH)
                if fits:
                    pieces[0] = (bigger, x, z, rot)
                    notes.append("prefab agrandi : " + bigger.rsplit("/", 1)[-1])
        rect = union([piece_rect(p) for p in pieces])
        x0, x1, z0, z1 = rect
        cx = (x0 + x1) // 2
        blocks = []
        extra_pieces = []
        if tier >= 2:
            # Sentier de 3 de large devant l'entrée (sud), 4 blocs.
            for dz in range(1, 5):
                for dx in (-1, 0, 1):
                    blocks.append(f"{cx + dx} -1 {z1 + dz} 0 {kit['path']}")
            blocks.append(f"{x0 - 1} 0 {z1 + 1} 0 {kit['light']}")
            blocks.append(f"{x1 + 1} 0 {z1 + 1} 0 {kit['light']}")
            blocks.append(f"{cx - 3} 0 {z1 + 2} 0 {kit['props'][0]}")
            blocks.append(f"{cx + 3} 0 {z1 + 2} 0 {kit['props'][1]}")
            notes.append("sentier, lumières, caisses")
        if tier == 3:
            blocks += front_fence(x0 - 2, x1 + 2, z1 + 5, kit["fence"], cx)
            blocks.append(f"{cx - 3} 0 {z1 + 4} 0 {kit['pennant']}")
            notes.append("clôture avant, fanion")
        if tier >= 3 and kit["extra"]:
            ex = kit["extra"][0]
            b = BOUNDS.get(ex)
            if b:
                ex_x = x1 + 3 - b[0]
                extra_pieces.append((ex, ex_x, z1 - b[5], 0))
                notes.append("pièce vanilla : " + ex.rsplit("/", 1)[-1])
        if tier == 4:
            if len(kit["extra"]) > 1:
                ex = kit["extra"][1]
                b = BOUNDS.get(ex)
                if b:
                    extra_pieces.append((ex, x0 - 3 - b[1], z1 - b[5], 0))
                    notes.append("pièce vanilla : " + ex.rsplit("/", 1)[-1])
            inner = union([rect] + [piece_rect(p) for p in extra_pieces])
            rx0, rx1, rz0, rz1 = inner[0] - 2, inner[1] + 2, inner[2] - 2, inner[3] + 6
            blocks += fence_ring(rx0, rx1, rz0, rz1, kit["fence"], cx)
            kind, big = kit["big_light"]
            for (lx, lz) in ((rx0 + 1, rz0 + 1), (rx1 - 1, rz0 + 1), (rx0 + 1, rz1 - 1), (rx1 - 1, rz1 - 1)):
                if kind == "block":
                    blocks.append(f"{lx} 0 {lz} 0 {big}")
                else:
                    extra_pieces.append((big, lx, lz, 0))
            blocks.append(f"{cx - 3} 0 {rz1 - 1} 0 {kit['pennant']}")
            blocks.append(f"{cx + 3} 0 {rz1 - 1} 0 {kit['pennant']}")
            blocks.append(f"{cx - 4} 0 {z1 + 2} 0 {kit['props'][2]}")
            notes.append("enclos complet, grandes lumières, deux fanions")
        if e["Category"] == "LieuDit":
            # Décor de place du lieu-dit (établis...), dans le même repère que les bâtiments.
            for line in e.get("HamletDecor", []):
                blocks.append(line)
        all_rect = union([rect] + [piece_rect(p) for p in extra_pieces] + [block_rect(b) for b in blocks])
        tiers.append({"Tier": tier,
                      "Pieces": [f"{p[0]} {p[1]} {p[2]} {p[3]}" for p in pieces + extra_pieces],
                      "Blocks": blocks, "Rect": all_rect,
                      "Height": max([height_of(p[0]) for p in pieces + extra_pieces] + [3]),
                      "Notes": notes})
    return tiers


def block_rect(line):
    p = line.split()
    x, z = int(p[0]), int(p[2])
    return [x, x, z, z]


def check_blocks(entries):
    bad = set()
    for e in entries:
        for t in e["Tiers"]:
            for line in t["Blocks"]:
                name = line.split()[4].lstrip("*")
                if name not in BLOCK_IDS:
                    bad.add(name)
            for line in t["Pieces"]:
                if line.split()[0] not in BOUNDS:
                    bad.add("prefab " + line.split()[0])
    if bad:
        raise SystemExit("Ids inconnus : " + ", ".join(sorted(bad)))


# ---- Carte ----

def layout(entries):
    """Range les bâtiments : une colonne par peuple (d'ouest en est), une rangée par bâtiment (du nord au sud, par
    catégorie), les 4 paliers d'une rangée d'ouest en est."""
    x_people = 0
    sections = []
    for people in PEOPLES:
        rows = [e for c in CATEGORIES for e in entries if e["People"] == people and e["Category"] == c]
        z = 0
        width = 0
        categories = []
        for e in rows:
            if not categories or categories[-1]["Category"] != e["Category"]:
                categories.append({"Category": e["Category"], "Name": CATEGORY_NAMES[e["Category"]], "Z": z})
            x = x_people
            depth = max(t["Rect"][3] - t["Rect"][2] for t in e["Tiers"]) + 1 + 2 * MARGIN
            for t in e["Tiers"]:
                r = t["Rect"]
                w = r[1] - r[0] + 1 + 2 * MARGIN
                d = r[3] - r[2] + 1 + 2 * MARGIN
                # Rectangle [x, x + w - 1] × [cz0, cz0 + d - 1], aligné au sud de la rangée (panneaux du même côté).
                cz0 = z + (depth - d)
                t["Cell"] = [x, x + w - 1, cz0, cz0 + d - 1]
                t["Origin"] = [x + MARGIN - r[0], cz0 + MARGIN - r[2]]
                t["Sign"] = [x, cz0 + d + 1]
                x += w + GAP
            width = max(width, x - GAP - x_people)
            z += depth + ROW_GAP
        sections.append({"People": people, "Name": PEOPLE_NAMES[people], "X": x_people, "Width": width,
                         "Spawn": [x_people + 2, -6], "Label": [x_people + 2, -4], "Categories": categories})
        x_people += width + PEOPLE_GAP
    return sections


def label(e, t):
    return f"{PEOPLE_NAMES[e['People']]} · {e['Name']} · palier {t['Tier']}/4 · {CATEGORY_NAMES[e['Category']]}"


def preview(entries, sections, path):
    from PIL import Image, ImageDraw
    xs = [t["Cell"][1] for e in entries for t in e["Tiers"]]
    zs = [t["Cell"][3] for e in entries for t in e["Tiers"]]
    scale = 2
    w, h = (max(xs) + 40) * scale, (max(zs) + 20) * scale
    zs_off = 0
    img = Image.new("RGB", (w, h), (120, 170, 90))
    d = ImageDraw.Draw(img)
    colours = {1: (230, 230, 230), 2: (250, 220, 120), 3: (250, 160, 90), 4: (220, 90, 80)}
    for e in entries:
        for t in e["Tiers"]:
            x0, x1, z0, z1 = t["Cell"]
            d.rectangle([(x0 + 20) * scale, z0 * scale, (x1 + 20) * scale, z1 * scale], outline=(40, 40, 40),
                        fill=colours[t["Tier"]])
    for s in sections:
        d.text(((s["X"] + 20) * scale, 2), s["Name"], fill=(0, 0, 0))
    img.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview")
    args = ap.parse_args()
    entries = village_entries() + annex_entries() + hamlet_entries()
    for e in entries:
        e["Tiers"] = tier_compositions(e)
    check_blocks(entries)
    sections = layout(entries)
    doc = {
        "$Comment": "Carte de revue des paliers 1 à 4 des bâtiments, générée par tools/building_tiers.py (ne pas "
                    "modifier à la main) ; lue par dev.nakasar.hytale.peuples.review.ReviewMap (/village revue).",
        "World": "nakasar_revue_batiments",
        "Margin": MARGIN,
        "Sections": sections,
        "Cells": [],
    }
    for e in entries:
        for t in e["Tiers"]:
            doc["Cells"].append({
                "Key": f"{e['People']}/{e['Category']}/{e['Id']}/{t['Tier']}",
                "People": e["People"], "Category": e["Category"], "Building": e["Id"], "Tier": t["Tier"],
                "Label": label(e, t), "Source": e["Source"], "Notes": t["Notes"],
                "Cell": t["Cell"], "Origin": t["Origin"], "Sign": t["Sign"], "Height": t["Height"],
                "Ground": KIT[e["People"]]["ground"], "Pieces": t["Pieces"], "Blocks": t["Blocks"],
            })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # Une ligne par rectangle : fichier compact et diffs lisibles.
    cells = doc.pop("Cells")
    head = json.dumps(doc, ensure_ascii=False, indent=1)[:-2]
    body = ",\n".join("  " + json.dumps(c, ensure_ascii=False, separators=(",", ":")) for c in cells)
    OUT.write_text(head + ',\n "Cells": [\n' + body + "\n ]\n}\n", encoding="utf-8")
    doc["Cells"] = cells
    counts = {}
    for e in entries:
        counts.setdefault(e["People"], {}).setdefault(e["Category"], 0)
        counts[e["People"]][e["Category"]] += 1
    print(f"{len(entries)} bâtiments, {len(doc['Cells'])} rectangles → {OUT.relative_to(ROOT)}")
    for p, c in counts.items():
        print(" ", p, c)
    xs = max(c["Cell"][1] for c in doc["Cells"])
    zs = max(c["Cell"][3] for c in doc["Cells"])
    print(f"  carte {xs + 1} × {zs + 1} blocs")
    if args.preview:
        preview(entries, sections, args.preview)


if __name__ == "__main__":
    main()
