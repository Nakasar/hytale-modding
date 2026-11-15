#!/usr/bin/env python3
"""Enclos des villages et bêtes du mod (GDD des bâtiments de métier, étape 3 : spécialités et élevage).

Les Kweebecs ont déjà leur enclos (prefab vanilla Bunny_Area). Les quatre autres peuples en gagnent un au palier 1,
« en pièces vanilla, comme le cœur » : ce script écrit un petit prefab du mod par peuple,
Server/Prefabs/Nakasar/Peuples/Pens/<Peuple>_Pen.prefab.json, avec des blocs vanilla seulement (règle n° 2 d'AGENTS.md) :
un sol de terre, une clôture du bois du peuple (coins comme dans Kweebec_Oak_Bunny_Area_003), une barrière au sud
(côté place après la rotation du plan), une auge et des bottes de foin.

Il écrit aussi les rôles du mod des bêtes sans rôle vanilla Tamed_* (loups, tortues, bêtes de la zone 4) :
Server/NPC/Roles/Nakasar/Peuples/Nakasar_Peuples_Pen_<Bête>.json, des rôles Generic sur le modèle vanilla, qui
flânent autour du centre de l'enclos (point d'attache posé par le Java) et n'attaquent jamais. Le Java
(dev.nakasar.hytale.peuples.workshop.Livestock) pose les bêtes, coupe leur butin et ne les laisse pas se soigner.

    python3 tools/generate_pens.py      (avant tools/generate_village_layouts.py, qui lit les emprises des prefabs)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "src/main/resources/Server"
PENS = RES / "Prefabs/Nakasar/Peuples/Pens"
ROLES = RES / "NPC/Roles/Nakasar/Peuples"
BLOCKS = Path(__file__).resolve().parent / "vanilla-block-ids-0.7.2.txt"

# Demi-côté de la clôture : 13 × 13 blocs, l'intérieur fait 11 × 11.
HALF = 6
# Bois de la clôture et sol, par peuple.
STYLE = {
    "Trork": ("Wood_Deadwood_Fence", "Soil_Mud_Dry"),
    "Feran": ("Wood_Drywood_Fence", "Soil_Dirt"),
    "Renonce": ("Wood_Softwood_Fence", "Soil_Dirt"),
    "Slothian": ("Wood_Tropicalwood_Fence", "Soil_Mud_Dry"),
}
# Décor intérieur (x, z, bloc, rotation), au sol de l'enclos (y = 1).
DECOR = [(-4, -4, "Bench_Trough", 0), (4, -4, "Plant_Hay_Bundle", 0), (4, -3, "Plant_Hay_Bundle", 0), (-4, 4, "Plant_Hay_Bundle", 0)]

# Bêtes du mod : (id, apparence vanilla, PV, vitesse, clé de nom vanilla). PV des rôles vanilla d'Assets.zip.
ANIMALS = [
    ("Wolf_Trork", "Wolf_Trork_Hunter", 38, 5, "server.npcRoles.Wolf_Trork_Hunter.name"),
    ("Wolf_White", "Wolf_White", 103, 5, "server.npcRoles.Wolf_White.name"),
    ("Tortoise", "Tortoise", 103, 2, "server.npcRoles.Tortoise.name"),
    ("Archaeopteryx", "Archaeopteryx", 61, 4, "server.npcRoles.Archaeopteryx.name"),
    ("Trillodon", "Trillodon", 145, 3, "server.npcRoles.Trillodon.name"),
    ("Snail_Magma", "Snail_Magma", 61, 1, "server.npcRoles.Snail_Magma.name"),
]


def fence(x, z, wood):
    """Bloc de clôture du bord (x, z) : rotations et coins relevés dans Kweebec_Oak_Bunny_Area_003."""
    corner = "*" + wood + "_State_Definitions_Corner"
    if (x, z) == (-HALF, -HALF):
        return corner, 1
    if (x, z) == (-HALF, HALF):
        return corner, 2
    if (x, z) == (HALF, HALF):
        return corner, 3
    if (x, z) == (HALF, -HALF):
        return corner, 0
    if z == -HALF:
        return wood, 2
    if z == HALF:
        return wood, 0
    if x == -HALF:
        return wood, 3
    return wood, 1


def pen(people):
    wood, floor = STYLE[people]
    blocks = []
    for x in range(-HALF, HALF + 1):
        for z in range(-HALF, HALF + 1):
            blocks.append({"x": x, "y": 0, "z": z, "name": floor})
            if abs(x) == HALF or abs(z) == HALF:
                if z == HALF and x == 0:
                    name, rot = wood + "_Gate", 0
                else:
                    name, rot = fence(x, z, wood)
                b = {"x": x, "y": 1, "z": z, "name": name}
                if rot:
                    b["rotation"] = rot
                blocks.append(b)
    for x, z, name, rot in DECOR:
        b = {"x": x, "y": 1, "z": z, "name": name}
        if rot:
            b["rotation"] = rot
        blocks.append(b)
    return {"version": 8, "blockIdVersion": 11, "anchorX": 0, "anchorY": 0, "anchorZ": 0, "blocks": blocks}


def role(aid, appearance, health, speed, name_key):
    return {
        "$Comment": f"Bête d'enclos ({appearance}) d'un village du mod, générée par tools/generate_pens.py : modèle vanilla, "
                    "flâne autour du centre de l'enclos (point d'attache posé par workshop/Livestock), n'attaque jamais. "
                    "Pas de butin (Livestock), ne se régénère jamais (VillageNoRegenSystem).",
        "Type": "Generic",
        "Appearance": appearance,
        "NameTranslationKey": name_key,
        "MaxHealth": health,
        "StartState": "Idle",
        "DefaultPlayerAttitude": "Ignore",
        "DefaultNPCAttitude": "Ignore",
        "MotionControllerList": [
            {"Type": "Walk", "MaxWalkSpeed": speed, "Gravity": 10, "RunThreshold": 0.6, "MaxFallSpeed": 15,
             "MaxRotationSpeed": 360, "Acceleration": 10, "JumpHeight": 1.0}
        ],
        "KnockbackScale": 0.6,
        "Instructions": [
            {
                "Sensor": {"Type": "State", "State": "Idle"},
                "Instructions": [
                    {
                        "$Comment": "Sortie de l'enclos (barrière ouverte) : elle y retourne.",
                        "Sensor": {"Type": "Leash", "Range": 7},
                        "BodyMotion": {"Type": "Seek", "RelativeSpeed": 0.5, "SlowDownDistance": 2, "StopDistance": 1,
                                       "UsePathfinder": True},
                    },
                    {
                        "Type": "Random",
                        "Name": "Graze",
                        "Instructions": [
                            {
                                "Weight": 40,
                                "Instructions": [
                                    {
                                        "$Comment": "Elle reste sur place.",
                                        "ActionsBlocking": True,
                                        "BodyMotion": {"Type": "Nothing"},
                                        "Actions": [
                                            {"Type": "Timeout", "Delay": [4, 9]},
                                            {"Type": "ResetInstructions", "Instructions": ["Graze"]},
                                        ],
                                    }
                                ],
                            },
                            {
                                "Weight": 60,
                                "Instructions": [
                                    {
                                        "Continue": True,
                                        "ActionsAtomic": True,
                                        "Actions": [
                                            {"Type": "Timeout", "Delay": [5, 9]},
                                            {"Type": "ResetInstructions", "Instructions": ["Graze"]},
                                        ],
                                    },
                                    {
                                        "$Comment": "Elle flâne dans l'enclos.",
                                        "BodyMotion": {"Type": "WanderInCircle", "Radius": 4, "RelativeSpeed": 0.3,
                                                       "MaxHeadingChange": 60},
                                    },
                                ],
                            },
                        ],
                    },
                ],
            }
        ],
    }


def main():
    known = {line.strip().lstrip("*") for line in BLOCKS.read_text(encoding="utf-8").splitlines() if line.strip()}
    errors = []
    PENS.mkdir(parents=True, exist_ok=True)
    for people in STYLE:
        doc = pen(people)
        for b in doc["blocks"]:
            if b["name"].lstrip("*") not in known:
                errors.append(f"{people} : bloc vanilla inconnu {b['name']}")
        path = PENS / f"{people}_Pen.prefab.json"
        path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        print(f"{path.relative_to(ROOT)} : {len(doc['blocks'])} blocs")
    for aid, appearance, health, speed, name_key in ANIMALS:
        path = ROLES / f"Nakasar_Peuples_Pen_{aid}.json"
        path.write_text(json.dumps(role(aid, appearance, health, speed, name_key), indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
        print(f"{path.relative_to(ROOT)}")
    if errors:
        for e in errors:
            print("ERREUR", e)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
