#!/usr/bin/env python3
"""Génère la brèche des chasseurs de vampires (évènement de monde Nakasar_Hunter_Breach).

    python3 mods/nakasar-vampires/tools/generate_breach.py

Écrit :
  - les campements posés par l'évènement : src/main/resources/Server/Prefabs/Nakasar/Breach/*.prefab.json ;
  - le bloc de la brèche, Nakasar_Breach_Rift (déchirure de particules rouges, lumière, marqueur de carte) ;
  - les icônes de la carte et de la boussole (Common/UI/WorldMap/MapMarkers/Nakasar_HunterBreach*.png) et
    l'icône d'objet du bloc.

Les campements réutilisent les briques de generate_prefabs.py (tentes, feu purificateur...). Les chasseurs n'y
sont pas des blocs d'apparition mais des entités « marqueur d'apparition » du prefab, comme les gobelins du portail
de brèche vanilla : l'évènement suit les entités qu'il pose et les retire quand il restaure le terrain, et le
plugin retire alors leurs chasseurs (BreachHunterCleanupSystem). Le générateur est déterministe.
"""

import base64
import json
import math
import uuid
from pathlib import Path

from PIL import Image, ImageDraw

import generate_prefabs as gp
from generate_prefabs import AIR, EAST, NORTH, SOUTH, WEST, Prefab, tent

PACK = Path(__file__).resolve().parent.parent / "src" / "main" / "resources"
OUT = PACK / "Server" / "Prefabs" / "Nakasar" / "Breach"
ITEM = PACK / "Server" / "Item" / "Items" / "Deco" / "Nakasar" / "Breach" / "Nakasar_Breach_Rift.json"
MAP_MARKERS = PACK / "Common" / "UI" / "WorldMap" / "MapMarkers"
ITEM_ICON = PACK / "Common" / "Icons" / "Items" / "Nakasar" / "Breach" / "Breach_Rift.png"

RIFT = "Nakasar_Breach_Rift"
MARKER = "Nakasar_Breach_Hunter"  # = BreachHunterCleanupSystem.MARKER
MAP_ICON = "Nakasar_HunterBreach.png"
COMPASS_ICON = "Nakasar_HunterBreachCompass.png"
TORCH, LANTERN = gp.PURIFYING_TORCH, gp.PURIFYING_LANTERN

LIFT = 1  # décalage vertical à l'écriture (voir write_prefab)
RADIUS = 8  # clairière du campement ; les chasseurs (laisse ~14 blocs) restent autour
GROUND = [("Soil_Pathway", 3), ("Soil_Dirt", 3), ("Soil_Grass", 2), ("Soil_Gravel", 1)]
SCORCHED = [("Soil_Dirt_Burnt", 3), ("Soil_Grass_Burnt", 1)]
ARCH = [("Rock_Stone_Brick_Mossy", 3), ("Rock_Stone_Cobble_Mossy", 2), ("Rock_Stone_Brick", 1)]


def disc(r):
    return [(x, z) for x in range(-r, r + 1) for z in range(-r, r + 1) if x * x + z * z <= r * r + r]


def rift_arch(p, z):
    """Arche de pierre en ruine plantée au nord du camp, la déchirure rouge en son milieu."""
    for x in range(-2, 3):
        for dz in (-1, 0, 1):
            p.set(x, -1, z + dz, p.pick(SCORCHED))
    for x in (-2, 2):
        p.fill(x, 0, z, x, 3, z, ARCH)
    for x in range(-2, 3):
        if x == 1:
            continue  # pierre tombée : l'arche est brisée
        p.set(x, 4, z, p.pick(ARCH))
    p.set(1, 0, z + 1, "Rock_Stone_Cobble_Mossy")
    p.set(0, 0, z, RIFT)
    for x in (-3, 3):
        p.set(x, 0, z, TORCH)


def post(p, x, z, top=LANTERN):
    p.fill(x, 0, z, x, 1, z, "Wood_Softwood_Beam")
    p.set(x, 2, z, top)


def breach_camp(seed, variant):
    """Campement de chasseurs dressé devant la brèche : feu de camp, tentes de cuir, atelier, lanternes de feu
    blanc (qui tiennent les morts-vivants à distance), quatre ou cinq chasseurs."""
    p = Prefab(seed)
    r = p.rng
    for x, z in disc(RADIUS):
        p.fill(x, 0, z, x, 4, z, AIR)
        p.set(x, -1, z, p.pick(GROUND))
        p.fill(x, -5, z, x, -2, z, "Soil_Dirt")  # fondations : le terrain peut varier de 4 blocs sous le camp
    rift_arch(p, -6)
    p.set(0, -1, 1, "Rock_Stone_Cobble")
    p.set(0, 0, 1, "Bench_Campfire")
    stools = [(2, 1), (-2, 1), (0, 3)]
    for sx, sz in stools:
        p.set(sx, 0, sz, "Furniture_Crude_Stool")
    if variant == "tents":
        tent(p, -9, -3)
        tent(p, 4, -3)
        p.set(-4, 0, 5, "Bench_Weapon", EAST)
        p.set(-6, 0, 3, "Furniture_Crude_Table")
        p.set(-6, 1, 3, "Furniture_Crude_Candle")
        hunters = [(-2, 3), (2, 3), (3, -2), (-3, -2), (5, 3)]
        posts = [(-6, 6), (7, 3), (0, 8)]
    else:
        tent(p, -9, -3)
        # pas de tir à l'est : cibles, foin, mannequin
        for z in (-2, 1):
            p.set(7, 0, z, "Deco_Target", WEST)
        p.fill(7, 0, 3, 7, 1, 3, "Ingredient_Hay")
        p.set(5, 0, -3, "Tinkering_Target_Dummy", WEST)
        p.set(-4, 0, 5, "Bench_Armory", EAST)
        hunters = [(-2, 3), (2, 3), (3, -3), (-3, -2)]
        posts = [(-6, 6), (6, -5), (0, 8)]
    for bx, bz in ((4, 6), (5, 5), (6, 4)):
        p.set(bx, 0, bz, r.choice(["Furniture_Village_Crate", "Furniture_Tavern_Barrel", "Furniture_Ancient_Barrel"]))
    p.set(-2, 0, 7, "Furniture_Ancient_Sack")
    for lx, lz in posts:
        post(p, lx, lz)
    for x, z in hunters:
        assert p.free(x, 0, z) and p.free(x, 1, z), f"chasseur en ({x}, {z}) sur une case occupée"
    p.scatter(-RADIUS, 0, -RADIUS, RADIUS, RADIUS, 6, [("Plant_Grass_Lush_Short", 2), ("Plant_Grass_Lush", 1)], rot=0)
    for x, z in hunters:
        p.set(x, 0, z, AIR)
    return p, hunters


def marker_entity(name, x, z, index):
    """Entité « marqueur d'apparition » telle que l'écrivent les prefabs vanilla (portail de brèche gobelin).
    L'UUID est remplacé par un neuf à chaque pose (FromPrefab), il n'a qu'à exister."""
    ident = uuid.uuid5(uuid.NAMESPACE_URL, f"nakasar/breach/{name}/{index}")
    return {"Components": {
        "SpawnMarkerComponent": {"SpawnMarker": MARKER, "RespawnTime": 0.0, "SpawnCount": 0, "NPCReferences": [],
                                 "PersistedFlock": {}, "SpawnPosition": {"X": 0.0, "Y": 0.0, "Z": 0.0}},
        "Transform": {"Position": {"X": x + 0.5, "Y": float(LIFT), "Z": z + 0.5},
                      "Rotation": {"Pitch": 0.0, "Yaw": round(math.atan2(-x, -z), 4), "Roll": 0.0}},
        "Intangible": {},
        "UUID": {"UUID": {"$binary": base64.b64encode(ident.bytes).decode(), "$type": "04"}},
        "Nameplate": {"Text": MARKER},
        "HiddenFromAdventurePlayer": {},
        "PrefabCopyable": {},
        "Model": {"Model": {"Id": "NPC_Spawn_Marker", "Scale": 1.0, "Static": False}},
    }}


def write_prefab(path, p, hunters):
    """Écrit le prefab, monté d'un cran : l'évènement pose le prefab avec son y = 0 sur le bloc de surface trouvé
    (Spawner.findSurface), alors que les briques de generate_prefabs.py mettent la première couche d'air en y = 0."""
    count = p.write(path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    for block in doc["blocks"]:
        block["y"] += LIFT
    entities = [marker_entity(path.stem, x, z, i) for i, (x, z) in enumerate(hunters)]
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("{\n")
        for key in ("version", "blockIdVersion", "anchorX", "anchorY", "anchorZ"):
            f.write(f'  "{key}": {json.dumps(doc[key])},\n')
        f.write('  "blocks": [\n')
        f.write(",\n".join("    " + json.dumps(b, separators=(",", ":")) for b in doc["blocks"]))
        f.write('\n  ],\n  "entities": [\n')
        f.write(",\n".join("    " + json.dumps(e, separators=(",", ":")) for e in entities))
        f.write("\n  ]\n}\n")
    return count


# --- icônes ------------------------------------------------------------------------------------

def rift_shape(size, cx, cy, h, w):
    """Déchirure verticale en zigzag : polygone fermé."""
    pts_l, pts_r = [], []
    steps = 7
    for i in range(steps + 1):
        t = i / steps
        y = cy - h / 2 + t * h
        bulge = math.sin(t * math.pi) * w
        zig = (1 if i % 2 else -1) * w * 0.35
        pts_l.append((cx - bulge + zig, y))
        pts_r.append((cx + bulge + zig, y))
    return pts_l + pts_r[::-1]


def map_icon(size=48, compass=False):
    img = Image.new("RGBA", (size * 4, size * 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = 4
    c = size * s / 2
    # pastille sombre cerclée d'argent
    d.ellipse([s * 2, s * 2, size * s - s * 2, size * s - s * 2], fill=(24, 12, 20, 235), outline=(196, 206, 220, 255), width=s * 3)
    # deux carreaux d'arbalète d'argent croisés derrière la brèche
    for sign in (-1, 1):
        x0, y0 = c - sign * size * s * 0.30, c - size * s * 0.30
        x1, y1 = c + sign * size * s * 0.30, c + size * s * 0.30
        d.line([x0, y0, x1, y1], fill=(208, 216, 228, 255), width=s * 3)
        d.polygon([(x1, y1), (x1 - sign * s * 7, y1 - s * 2), (x1 - sign * s * 2, y1 - s * 7)], fill=(232, 238, 246, 255))
    # la brèche rouge
    d.polygon(rift_shape(size * s, c, c, size * s * 0.62, size * s * 0.13), fill=(120, 6, 22, 255))
    d.polygon(rift_shape(size * s, c, c, size * s * 0.50, size * s * 0.07), fill=(232, 40, 64, 255))
    if compass:
        # la boussole n'affiche que la brèche, sans pastille : on efface le fond hors du cercle intérieur
        mask = Image.new("L", img.size, 0)
        ImageDraw.Draw(mask).ellipse([s * 9, s * 9, size * s - s * 9, size * s - s * 9], fill=255)
        img.putalpha(Image.composite(img.getchannel("A"), mask, mask))
    return img.resize((size, size), Image.LANCZOS)


def write_rift_item():
    item = {
        "$Comment": "Déchirure de la brèche des chasseurs (évènement Nakasar_Hunter_Breach) : bloc sans forme ni collision, particules de faille rouge, lumière rouge, marqueur sur la carte et la boussole. Posé par le prefab de la brèche, retiré avec lui. Généré par tools/generate_breach.py.",
        "TranslationProperties": {"Name": "nakasar_breach.items.Nakasar_Breach_Rift.name"},
        "Icon": "Icons/Items/Nakasar/Breach/Breach_Rift.png",
        "Quality": "Developer",
        "Categories": ["Blocks.Deco"],
        "BlockType": {
            "Material": "Empty",
            "DrawType": "Empty",
            "Opacity": "Transparent",
            "Gathering": {"Breaking": {"GatherType": "Unbreakable"}},
            "Light": {"Color": "#d23"},
            "Particles": [{"SystemId": "Dungeon_Goblin_Void_Rift", "Color": "#c8203c", "PositionOffset": {"X": 0, "Y": 1.5, "Z": 0}}],
            "BlockEntity": {"Components": {"BlockMapMarker": {
                "Name": "nakasar_breach.name", "Icon": MAP_ICON, "CompassIcon": COMPASS_ICON}}},
        },
    }
    ITEM.parent.mkdir(parents=True, exist_ok=True)
    ITEM.write_text(json.dumps(item, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    if OUT.exists():
        for old in OUT.rglob("*.prefab.json"):
            old.unlink()
    for i, variant in enumerate(("tents", "range")):
        p, hunters = breach_camp(9500 + i, variant)
        path = OUT / f"Hunter_Breach_Camp_{variant.capitalize()}.prefab.json"
        print(f"{path.name}: {write_prefab(path, p, hunters)} blocs, {len(hunters)} chasseurs")
    write_rift_item()
    MAP_MARKERS.mkdir(parents=True, exist_ok=True)
    map_icon().save(MAP_MARKERS / MAP_ICON)
    map_icon(compass=True).save(MAP_MARKERS / COMPASS_ICON)
    ITEM_ICON.parent.mkdir(parents=True, exist_ok=True)
    map_icon(64).save(ITEM_ICON)
    print("brèche des chasseurs générée")


if __name__ == "__main__":
    main()
