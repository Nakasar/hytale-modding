#!/usr/bin/env python3
"""Génère l'entrée des Fractales des Brumes (étape 2 du GDD, docs/fractales/gdd.md) : le Fragment des Brumes, son
portail, l'instance de l'Observatoire des fractales et son île (la Falaise vient de tools/generate_cliffside.py).

    python3 mods/nakasar-fractals/tools/generate_observatory.py [--preview DOSSIER]

- la clé `PortalKey_Nakasar_Fractal` (« Fragment des Brumes ») : 4 éclats de rune + 1 cœur du Vide à l'établi
  vanilla (recette dans un fichier à part : un id inconnu ne retire que la recette, pas l'objet) ;
- le type de portail et l'instance de l'Observatoire : monde vide (comme Deepworks), ciel des Brumes figé, ni pose
  ni casse de blocs, aucune perte d'objets à la mort ;
- l'île de l'Observatoire, un prefab posé à hauteur fixe dans le vide : parvis d'arrivée et portail de retour au sud,
  l'Astrolabe au centre (cadran de niveau), le cercle d'harmonisation autour, six arches de fractale en couronne au
  nord, le golem d'essai et son pupitre à l'ouest, le registre des fractales à l'est ;
- les blocs du décor (textures et icônes dessinées ici), leurs interactions, le golem d'essai, les langues ;
- `observatory/ObservatoryLayout.java` : les positions dont le Java a besoin (cercle, arches, golem, cage).

Repère : x vers l'est, z vers le sud, y vers le haut ; le centre de l'Astrolabe est en (0, GROUND_Y, 0), GROUND_Y étant
la première couche d'air au-dessus du dallage. À l'est, le coin de l'Archiviste : comptoir, Autel des infusions,
Creuset des Brumes (leurs objets viennent de tools/generate_progression.py).
"""
import json
import shutil
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

MOD = Path(__file__).resolve().parent.parent
PACK = MOD / "src" / "main" / "resources"
SERVER = PACK / "Server"
COMMON = PACK / "Common"
JAVA_LAYOUT = MOD / "src/main/java/dev/nakasar/hytale/fractals/observatory/ObservatoryLayout.java"
LANG = "nakasar_fractals"

KEY = "PortalKey_Nakasar_Fractal"
OBSERVATORY = "Nakasar_Fractal_Observatory"
WEATHER = "Nakasar_Fractal_Weather_Mists"
ENVIRONMENT = "Nakasar_Fractal_Env_Mists"
PREFABS = "Nakasar/Fractals"
TEXTURES = "BlockTextures/Nakasar/Fractals"
ICONS = "Icons/Items/Nakasar/Fractals"
# Icônes des onglets d'établi : le moteur les veut sous Icons/CraftingCategories (Infusions.png vient de
# generate_progression.py, Fragments.png est l'icône du fragment).
CATEGORY_ICONS = "Icons/CraftingCategories/Nakasar/Fractals"
INTERACTIONS = SERVER / "Item/Interactions/Nakasar/Fractals"
ITEMS = SERVER / "Item/Items/Deco/Nakasar/Fractals"
GOLEM = "Nakasar_Fractal_Trial_Golem"

# Recette du fragment (GDD, validée par Kevin le 20 octobre 2026) : après le premier donjon vanilla.
KEY_INPUTS = [("Ingredient_Rune_Shard", 4), ("Ingredient_Voidheart", 1)]

GROUND_Y = 100
ISLAND_RADIUS = 30
ASTROLABE_RADIUS = 3          # socle de l'Astrolabe
CIRCLE_INNER, CIRCLE_OUTER = 5, 8   # cercle d'harmonisation (dalles lumineuses)
ARCH_RADIUS = 21
ARRIVAL = (0, GROUND_Y, 24)   # point d'apparition, sur le parvis au sud
RETURN_PORTAL = (0, 0, 28)    # portail de retour (prefab), derrière le point d'apparition
GOLEM_SPOT = (-19, GROUND_Y, 9)
TRIAL_PANEL = (-15, 0, 7)
TRIAL_CAGE = (-24, 0, 14)     # cage d'essai (bloc Nakasar_Fractal_Cage_Cell)
REGISTRY = (16, 0, 8)
# Coin de l'Archiviste (est, étape 3) : comptoir devant lui, autel des infusions et creuset des Brumes à côté.
ARCHIVIST_SPOT = (18, GROUND_Y, 11)
COUNTER = (16, 0, 11)
ALTAR_SPOT = (13, 0, 13)
FORGE_SPOT = (15, 0, 15)
CAGE_CELL = "Nakasar_Fractal_Cage_Cell"

# Les 6 fractales de la saison 1 (GDD) : id, nom, couleur, pierre et cristal de l'arche, cap (degrés, 0 = nord, sens
# horaire). La Falaise est la seule instance pour l'instant (tools/generate_cliffside.py).
FRACTALS = [
    ("Cliffside", "Falaise", "Cliffside", (176, 120, 210), "Rock_Stone_Brick", "Rock_Crystal_Purple_Block", -100),
    ("Uncategorized", "Inclassable", "Uncategorized", (232, 150, 200), "Rock_Marble_Brick", "Rock_Crystal_Pink_Block", -60),
    ("Volcanic", "Volcanique", "Volcanic", (226, 96, 50), "Rock_Volcanic_Brick", "Rock_Crystal_Red_Block", -20),
    ("SolidOcean", "Océan solide", "Solid Ocean", (70, 200, 180), "Rock_Aqua_Brick", "Rock_Crystal_Cyan_Block", 20),
    ("Swampland", "Marais", "Swampland", (110, 170, 70), "Rock_Lime_Brick", "Rock_Crystal_Green_Block", 60),
    ("Snowblind", "Tempête de neige", "Snowblind", (170, 210, 240), "Soil_Snow_Brick", "Rock_Crystal_Blue_Block", 100),
]
FLAVOR = {
    "Cliffside": ("Un sentier taillé dans la falaise, le long d'un colosse enchaîné. Cinq sceaux à briser au marteau "
                  "des cultistes, jusqu'à l'Archidevin.",
                  "A path carved into the cliff, along a chained colossus. Five seals to break with the cultists' "
                  "hammer, up to the Archdiviner."),
    "Uncategorized": ("Des plateformes sous les harpies, une prison, un escalier mortel et un Asura qui a perdu la "
                      "raison.", "Platforms under harpies, a prison, a deadly staircase and an Asura who lost his mind."),
    "Volcanic": ("Des vagues de grawls, un couloir à rochers et un chaman nourri par le volcan.",
                 "Waves of grawls, a boulder corridor and a shaman fed by the volcano."),
    "SolidOcean": ("Des plateformes de jade au-dessus d'un océan figé, et l'Abîme de Jade.",
                   "Jade platforms over a frozen ocean, and the Jade Maw."),
    "Swampland": ("Trois feux-follets à guider à travers le marais, le Moussu et Carnasse.",
                  "Three wisps to guide through the swamp, the Mossman and Bloomhunger."),
    "Snowblind": ("Un feu de camp à nourrir dans la tempête, la Source élémentaire et un chaman grawl.",
                  "A campfire to feed in the blizzard, the Elemental Source and a grawl shaman."),
}

# Pierres du décor (ids vanilla de tools/vanilla-block-ids-0.7.2.txt).
FLOOR = ["Rock_Marble_Brick_Smooth", "Rock_Marble_Brick_Smooth", "Rock_Marble_Brick"]
TRIM = "Rock_Gold_Brick_Smooth"
EDGE = "Rock_Quartzite_Brick"
EDGE_TOP = "Rock_Quartzite_Brick_Half"
POST_BASE, POST = "Rock_Quartzite_Brick_Pillar_Base", "Rock_Quartzite_Brick_Pillar_Middle"
LANTERN = "Furniture_Temple_Light_Lantern"
UNDERSIDE = ["Rock_Stone", "Rock_Slate", "Rock_Marble", "Rock_Shale"]
MIST_CRYSTALS = ["Rock_Crystal_Blue_Small", "Rock_Crystal_Purple_Small", "Rock_Crystal_White_Small"]
AIR = "Empty"

# Blocs du mod.
DIAL = "Nakasar_Fractal_Astrolabe_Dial"
ASTROLABE_RING = "Nakasar_Fractal_Astrolabe_Ring"
HARMONY = "Nakasar_Fractal_Harmony_Tile"
TRIAL = "Nakasar_Fractal_Trial_Panel"
REGISTRY_BLOCK = "Nakasar_Fractal_Registry"
EXIT_STONE = "Nakasar_Fractal_Exit_Stone"
ALTAR = "Nakasar_Fractal_Infusion_Altar"
FORGE = "Nakasar_Fractal_Mist_Forge"
REWARD_CHEST = "Nakasar_Fractal_Reward_Chest"
COUNTER_BLOCK = "Nakasar_Fractal_Archivist_Counter"
PROGRESS_LANG = "nakasar_fractals_progress"   # langue des objets de tools/generate_progression.py


def arch_stone(fid):
    return f"Nakasar_Fractal_Arch_{fid}"


def heading_to_xz(heading, radius):
    """Cap en degrés (0 = nord = -z, 90 = est = +x) vers (x, z) arrondis."""
    a = math.radians(heading)
    return round(math.sin(a) * radius), round(-math.cos(a) * radius)


# --- prefab -------------------------------------------------------------------------------------

class Prefab:
    """Grille creuse de blocs ; la dernière écriture d'une case l'emporte. Blocs d'une seule case seulement (pas de
    meubles sur plusieurs cases : il faudrait écrire leurs remplissages)."""

    def __init__(self):
        self.blocks = {}

    def set(self, x, y, z, name, rot=0):
        self.blocks[(x, y, z)] = (name, rot)

    def fill(self, x0, y0, z0, x1, y1, z1, name):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    self.set(x, y, z, name)

    def write(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        blocks = []
        for (x, y, z), (name, rot) in sorted(self.blocks.items(), key=lambda kv: (kv[0][1], kv[0][2], kv[0][0])):
            entry = {"x": x, "y": y, "z": z, "name": name}
            if rot:
                entry["rotation"] = rot
            blocks.append(entry)
        with path.open("w", encoding="utf-8", newline="\n") as f:
            f.write('{\n  "version": 8,\n  "blockIdVersion": 8,\n  "anchorX": 0,\n  "anchorY": 0,\n  "anchorZ": 0,\n')
            f.write('  "blocks": [\n')
            f.write(",\n".join("    " + json.dumps(b, separators=(",", ":")) for b in blocks))
            f.write("\n  ]\n}\n")
        return len(blocks)


def pick(options, x, z):
    """Choix déterministe dans `options` selon la case (pas de hasard : le prefab ne change pas d'un tirage à l'autre)."""
    return options[(x * 73856093 ^ z * 19349663) % len(options)]


def island(p, radius, depth):
    """Disque dallé de `radius` blocs (dessus en y = -1), dessous en cône de `depth` blocs, garde-corps au bord."""
    for x in range(-radius - 1, radius + 2):
        for z in range(-radius - 1, radius + 2):
            d = math.hypot(x, z)
            if d > radius + 0.5:
                continue
            p.set(x, -1, z, pick(FLOOR, x, z))
            # Dessous : se resserre vers le bas, comme les îles des Brumes de GW2.
            bottom = -2 - int(depth * (1 - (d / (radius + 0.5)) ** 1.6))
            for y in range(bottom, -1):
                p.set(x, y, z, pick(UNDERSIDE, x + y, z))
    # Garde-corps : muret de 1,5 bloc, poteaux à lanterne tous les 30 degrés.
    posts = {heading_to_xz(h, radius) for h in range(0, 360, 30)}
    for x in range(-radius - 1, radius + 2):
        for z in range(-radius - 1, radius + 2):
            d = math.hypot(x, z)
            if radius - 0.5 < d <= radius + 0.5:
                if (x, z) in posts:
                    p.set(x, 0, z, POST_BASE)
                    p.set(x, 1, z, POST)
                    p.set(x, 2, z, LANTERN)
                else:
                    p.set(x, 0, z, EDGE)
                    p.set(x, 1, z, EDGE_TOP)


def observatory_prefab():
    p = Prefab()
    island(p, ISLAND_RADIUS, 22)
    # Anneau d'or du cercle d'harmonisation et dalles lumineuses (couleur positive : bleu des Brumes).
    for x in range(-CIRCLE_OUTER - 1, CIRCLE_OUTER + 2):
        for z in range(-CIRCLE_OUTER - 1, CIRCLE_OUTER + 2):
            d = math.hypot(x, z)
            if CIRCLE_INNER - 0.5 <= d < CIRCLE_OUTER + 0.5:
                edge = d < CIRCLE_INNER + 0.5 or d >= CIRCLE_OUTER - 0.5
                p.set(x, -1, z, TRIM if edge else HARMONY)
    # Astrolabe : socle rond, anneaux armillaires (blocs lumineux) et cadran au sommet du socle, côté sud.
    for x in range(-ASTROLABE_RADIUS, ASTROLABE_RADIUS + 1):
        for z in range(-ASTROLABE_RADIUS, ASTROLABE_RADIUS + 1):
            if math.hypot(x, z) <= ASTROLABE_RADIUS + 0.3:
                p.set(x, 0, z, "Rock_Gold_Brick_Ornate" if math.hypot(x, z) > ASTROLABE_RADIUS - 0.7 else "Rock_Gold_Brick")
    p.fill(0, 1, 0, 0, 3, 0, "Rock_Gold_Brick_Pillar_Middle")
    for k in range(-2, 3):           # anneau vertical nord-sud
        p.set(0, 5 + round(math.sqrt(max(0, 4 - k * k))), k, ASTROLABE_RING)
        p.set(0, 5 - round(math.sqrt(max(0, 4 - k * k))), k, ASTROLABE_RING)
    for k in range(-2, 3):           # anneau vertical est-ouest
        p.set(k, 5 + round(math.sqrt(max(0, 4 - k * k))), 0, ASTROLABE_RING)
        p.set(k, 5 - round(math.sqrt(max(0, 4 - k * k))), 0, ASTROLABE_RING)
    p.set(0, 5, 0, "Rock_Crystal_White_Block")
    p.set(0, 1, ASTROLABE_RADIUS, DIAL)
    # Arches de fractale : pieds de pierre de la fractale, linteau de cristal, pierre d'arche à utiliser au pied.
    arches = []
    for fid, _, _, _, stone, crystal, heading in FRACTALS:
        cx, cz = heading_to_xz(heading, ARCH_RADIUS)
        # Axe de l'arche perpendiculaire au rayon : l'ouverture regarde l'Astrolabe.
        a = math.radians(heading)
        ux, uz = math.cos(a), math.sin(a)       # le long de l'arche
        for s in (-2, 2):
            x, z = round(cx + ux * s), round(cz + uz * s)
            p.fill(x, 0, z, x, 4, z, stone)
            p.set(x, 5, z, crystal)
        for s in (-1, 0, 1):
            x, z = round(cx + ux * s), round(cz + uz * s)
            p.set(x, 5, z, crystal)
            p.set(x, 6, z, stone)
        p.set(cx, 0, cz, arch_stone(fid))
        arches.append((fid, cx, cz))
    # Parvis d'arrivée au sud : chemin de dalles d'or vers le cercle, portail de retour derrière le point d'apparition.
    for z in range(CIRCLE_OUTER + 1, ISLAND_RADIUS):
        for x in (-1, 0, 1):
            p.set(x, -1, z, TRIM if x == 0 else "Rock_Marble_Brick_Ornate")
    p.fill(-1, 0, RETURN_PORTAL[2] - 1, 1, 3, RETURN_PORTAL[2] + 1, AIR)
    p.set(*RETURN_PORTAL, "Portal_Return")
    # Golem d'essai (ouest) : aire dallée, pupitre de démonstration, cage d'essai fermée par des cristaux.
    gx, _, gz = GOLEM_SPOT
    for x in range(gx - 3, gx + 4):
        for z in range(gz - 3, gz + 4):
            if math.hypot(x - gx, z - gz) <= 3.4:
                p.set(x, -1, z, "Rock_Quartzite_Brick_Decorative")
    p.set(*TRIAL_PANEL, TRIAL)
    cx, _, cz = TRIAL_CAGE
    for x in range(cx - 1, cx + 2):
        for z in range(cz - 1, cz + 2):
            p.set(x, -1, z, "Rock_Gold_Brick")
            p.set(x, 3, z, "Rock_Gold_Brick")
            if (x, z) != (cx, cz):
                for y in (0, 1, 2):
                    p.set(x, y, z, "Rock_Crystal_Red_Block" if y == 1 else "Rock_Gold_Brick_Pillar_Middle")
    p.set(cx, 0, cz, CAGE_CELL)
    p.set(cx, 1, cz, AIR)
    p.set(cx, 2, cz, AIR)
    # Registre des fractales (est) : là où se tiendra l'Archiviste.
    p.set(*REGISTRY, REGISTRY_BLOCK)
    # Coin de l'Archiviste : dallage, comptoir, autel des infusions et creuset des Brumes.
    ax, _, az = ARCHIVIST_SPOT
    for x in range(ax - 6, ax + 2):
        for z in range(az - 2, az + 6):
            if math.hypot(x, z) <= ISLAND_RADIUS - 3:
                p.set(x, -1, z, "Rock_Quartzite_Brick_Decorative")
    p.set(*COUNTER, COUNTER_BLOCK)
    p.set(*ALTAR_SPOT, ALTAR)
    p.set(*FORGE_SPOT, FORGE)
    # Cristaux de Brume semés sur le pourtour (décor).
    for k, h in enumerate(range(15, 360, 30)):
        x, z = heading_to_xz(h, ISLAND_RADIUS - 2)
        if p.blocks.get((x, 0, z), (AIR,))[0] == AIR:
            p.set(x, 0, z, MIST_CRYSTALS[k % len(MIST_CRYSTALS)])
    return p, arches


# --- blocs, textures, icônes ------------------------------------------------------------------------

def texture(path, base, accent, glyph):
    img = Image.new("RGBA", (32, 32), base + (255,))
    d = ImageDraw.Draw(img)
    dark = tuple(int(c * 0.7) for c in base) + (255,)
    d.rectangle((0, 0, 31, 31), outline=dark)
    d.rectangle((2, 2, 29, 29), outline=tuple(min(255, int(c * 1.1)) for c in base) + (255,))
    acc = accent + (255,)
    if glyph == "arch":
        d.arc((7, 6, 25, 30), 180, 360, fill=acc, width=3)
        d.line((7, 17, 7, 28), fill=acc, width=3)
        d.line((25, 17, 25, 28), fill=acc, width=3)
        d.ellipse((13, 15, 19, 21), fill=acc)
    elif glyph == "dial":
        d.ellipse((5, 5, 26, 26), outline=acc, width=2)
        for k in range(12):
            a = math.radians(k * 30)
            d.point((16 + math.cos(a) * 9, 16 + math.sin(a) * 9), fill=acc)
        d.line((16, 16, 16, 8), fill=acc, width=2)
        d.line((16, 16, 22, 19), fill=acc, width=2)
    elif glyph == "ring":
        d.ellipse((6, 6, 25, 25), outline=acc, width=3)
    elif glyph == "tile":
        d.rectangle((6, 6, 25, 25), outline=acc, width=1)
        d.polygon(((16, 8), (24, 16), (16, 24), (8, 16)), outline=acc)
        d.ellipse((14, 14, 17, 17), fill=acc)
    elif glyph == "panel":
        d.rectangle((7, 7, 24, 24), outline=acc, width=2)
        d.ellipse((12, 12, 19, 19), outline=acc, width=2)
    elif glyph == "book":
        d.rectangle((7, 6, 24, 25), fill=accent + (255,))
        d.line((16, 6, 16, 25), fill=dark, width=1)
        for y in (10, 14, 18):
            d.line((9, y, 14, y), fill=dark)
            d.line((18, y, 23, y), fill=dark)
    elif glyph == "altar":
        for k in range(3):
            for j in range(4):
                d.rectangle((6 + j * 5, 7 + k * 6, 9 + j * 5, 10 + k * 6), outline=acc)
        d.ellipse((13, 13, 18, 18), fill=acc)
    elif glyph == "forge":
        d.polygon(((8, 12), (24, 12), (21, 25), (11, 25)), outline=acc, fill=dark)
        d.ellipse((12, 6, 20, 13), fill=acc)
    elif glyph == "chest":
        d.rectangle((6, 10, 25, 25), outline=acc, width=2)
        d.line((6, 15, 25, 15), fill=acc, width=2)
        d.rectangle((14, 13, 17, 18), fill=acc)
    elif glyph == "counter":
        d.rectangle((5, 8, 26, 12), fill=acc)
        d.line((8, 12, 8, 26), fill=acc, width=2)
        d.line((23, 12, 23, 26), fill=acc, width=2)
        d.ellipse((13, 16, 18, 21), outline=acc)
    elif glyph == "exit":
        d.ellipse((7, 7, 24, 24), outline=acc, width=3)
        d.polygon(((13, 11), (21, 16), (13, 21)), fill=acc)
    img.save(path)
    return img


def icon(path, tex):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    img.alpha_composite(tex.resize((48, 48), Image.NEAREST), (8, 8))
    img.save(path)


def block_item(name, tex, light=None, interaction=None, solid=True, quality="Technical", particle="#9aa7c8"):
    block = {
        "Material": "Solid" if solid else "Empty",
        "DrawType": "Cube",
        "Opacity": "Solid",
        "Textures": [{"Sides": f"{TEXTURES}/{tex}.png", "UpDown": f"{TEXTURES}/{tex}.png", "Weight": 1}],
        "HitboxType": "Full",
        "Flags": {},
        "Gathering": {"Breaking": {"GatherType": "Unbreakable"}},
        "BlockParticleSetId": "Stone",
        "BlockSoundSetId": "Stone",
        "ParticleColor": particle,
    }
    if light:
        block["Light"] = {"Color": light}
    if interaction:
        block["Interactions"] = {"Use": {"Interactions": [interaction]}}
    return {
        "TranslationProperties": {"Name": f"{LANG}.items.{name}.name", "Description": f"{LANG}.items.{name}.description"},
        "Icon": f"{ICONS}/{tex}.png",
        "Categories": ["Blocks.Deco"],
        "Quality": quality,
        "PlayerAnimationsId": "Block",
        "BlockType": block,
        "Tags": {"Type": ["Deco"]},
        "ItemSoundSetId": "ISS_Blocks_Stone",
    }


def bench_item(name, tex):
    """Creuset des Brumes : établi en cube (fusion des infusions, fragment refait), cassable pour l'emporter."""
    doc = block_item(name, tex, light="#a8f", quality="Rare", particle="#8a6ad8")
    doc["Categories"] = ["Furniture.Benches"]
    doc["Tags"] = {"Type": ["Bench"]}
    doc["MaxStack"] = 1
    block = doc["BlockType"]
    block["Gathering"] = {"Breaking": {"GatherType": "Benches", "ItemId": name}}
    block["BlockEntity"] = {"Components": {"BenchBlock": {}}}
    block["State"] = {"Definitions": {"CraftCompleted": {"Looping": True}, "CraftCompletedInstant": {}}}
    block["Bench"] = {
        "Type": "Crafting",
        "Id": name,
        "LocalOpenSoundEventId": "SFX_Weapon_Bench_Open",
        "LocalCloseSoundEventId": "SFX_Weapon_Bench_Close",
        "CompletedSoundEventId": "SFX_Weapon_Bench_Craft",
        "Categories": [
            {"Id": "Nakasar_Fractal_Infusions", "Name": f"{PROGRESS_LANG}.benchCategories.nakasar_fractal_infusions",
             "Icon": f"{CATEGORY_ICONS}/Infusions.png"},
            {"Id": "Nakasar_Fractal_Fragments", "Name": f"{PROGRESS_LANG}.benchCategories.nakasar_fractal_fragments",
             "Icon": f"{CATEGORY_ICONS}/Fragments.png"},
        ],
    }
    return doc


def portable(doc, name):
    """Bloc fabricable (autel) : se casse et se rend, pour le poser chez soi."""
    doc["BlockType"]["Gathering"] = {"Breaking": {"GatherType": "Benches", "ItemId": name}}
    doc["Quality"] = "Rare"
    doc["MaxStack"] = 1
    return doc


def hexcolor(rgb):
    return "#%02x%02x%02x" % rgb


def short_light(rgb):
    return "#%x%x%x" % tuple(c // 17 for c in rgb)


# --- assets JSON ---------------------------------------------------------------------------------

def key_item():
    return {
        "Parent": "PortalKey_Taiga",
        "TranslationProperties": {"Name": f"{LANG}.items.{KEY}.name", "Description": f"{LANG}.items.{KEY}.description"},
        "Icon": f"{ICONS}/PortalKey_Fractal.png",
        "Quality": "Epic",
        "PortalKey": {"PortalType": OBSERVATORY, "TimeLimitSeconds": -1},
    }


def key_recipe():
    return {
        "TimeSeconds": 4,
        "KnowledgeRequired": False,
        "Input": [{"ItemId": k, "Quantity": q} for k, q in KEY_INPUTS],
        "PrimaryOutput": {"ItemId": KEY, "Quantity": 1},
        "Output": [{"ItemId": KEY, "Quantity": 1}],
        "BenchRequirement": [{"Type": "Crafting", "Id": "Workbench", "Categories": ["Workbench_Crafting"],
                              "RequiredTierLevel": 1}],
    }


def portal_type():
    return {
        "InstanceId": OBSERVATORY,
        "GameplayConfig": OBSERVATORY,
        "Description": {
            "DisplayName": f"{LANG}.portal.name",
            "FlavorText": f"{LANG}.portal.flavor",
            "ThemeColor": "#4a7ad8",
            "DescriptionTags": [
                {"TranslationKey": f"{LANG}.portal.tag.hub", "Color": "#4a7ad8"},
                {"TranslationKey": f"{LANG}.portal.tag.group", "Color": "#2980b9"},
            ],
            "Objectives": [f"{LANG}.portal.objective"],
        },
        "Spawn": {
            # Le portail de retour est dans le prefab, derrière le point d'arrivée (pas dessus : voir le mod Vampires,
            # un joueur dont l'écran charge encore repartirait aussitôt).
            "SpawnReturnPortal": False,
            "SpawnProviderOverride": {"Id": "Global", "SpawnPoint": {"X": ARRIVAL[0] + 0.5, "Y": float(ARRIVAL[1]),
                                                                     "Z": ARRIVAL[2] + 0.5, "Yaw": 0.0}},
        },
        "TimeLimitSeconds": -1,
        "AllowedEntryCount": 0,
        "CloseWhenEmpty": True,
        "VoidInvasionEnabled": False,
        "AllowPlayersToLeaveViaMap": True,
    }


def gameplay_config():
    return {
        "Parent": "Default",
        "World": {"AllowBlockGathering": False, "AllowBlockPlacement": False, "AllowBlockBreaking": False,
                  "BlockedRootInteractionTags": ["Type=Rail_Kart", "Type=Bed"]},
        "Plugin": {"Portal": {}, "WorldEvents": {}},
        "Death": {"ItemsLossMode": "None", "ItemsAmountLossPercentage": 0, "ItemsDurabilityLossPercentage": 0},
        "WorldMap": {"DisplayDeathMarker": False},
    }


def weather():
    """Ciel des Brumes de GW2 : bleu nuit en haut, violet et turquoise à l'horizon, brume épaisse au loin."""
    hours = lambda pairs: [{"Hour": h, "Color": c} for h, c in pairs]
    return {
        "FogDistance": [-20, 220],
        "FogColors": hours([(0, "#141838"), (12, "#3a4a80"), (18, "#3a2a6a")]),
        "FogDensities": [{"Hour": 0, "Value": 0.5}, {"Hour": 12, "Value": 0.4}],
        "SkyTopColors": hours([(0, "#080a26ff"), (12, "#22306aff"), (18, "#1c1048ff")]),
        "SkyBottomColors": hours([(0, "#2a1a5aff"), (12, "#5a80c8ff"), (18, "#7a4ab0ff")]),
        "SkySunsetColors": hours([(0, "#00000000"), (18, "#c070e0a0"), (21, "#00000000")]),
        "SunlightColors": hours([(0, "#5a5aa8"), (12, "#c8d0f0"), (18, "#a890d8")]),
        "SunColors": hours([(0, "#ffffff"), (18, "#d8a0ff")]),
        "MoonColors": hours([(0, "#e0e8ffff"), (12, "#e0e8ffff")]),
        "MoonGlowColors": hours([(0, "#7aa0ff60"), (12, "#7aa0ff60")]),
        "WaterTints": hours([(0, "#1a2a5a"), (12, "#3a5a9a")]),
    }


def environment():
    return {
        "$Comment": "Brumes de l'Observatoire et des fractales : pas d'apparitions naturelles, ciel figé des Brumes.",
        "Parent": "Env_Zone1_Plains",
        "SpawnDensity": 0.0,
        "BlockModificationAllowed": False,
        "WaterTint": "#3a5a9a",
        "WeatherForecastSeed": ENVIRONMENT,
        "WeatherForecasts": {str(h): [{"WeatherId": WEATHER, "Weight": 1}] for h in range(24)},
    }


def instance(name, display, structure, portal=True, spawn=ARRIVAL, removal=300, weather=WEATHER, time="18:00"):
    """Instance figée à l'heure `time` sous le temps `weather` (par défaut le crépuscule des Brumes)."""
    doc = {
        "DisplayName": display,
        "WorldGen": {"Type": "HytaleGenerator", "WorldStructure": structure},
        "ForcedWeather": weather,
        "GameTime": f"0001-01-01T{time}:00Z",
        "IsGameTimePaused": True,
        "GameplayConfig": OBSERVATORY,
        "IsPvpEnabled": False,
        "IsSpawningNPC": True,
        "SpawnProvider": {"Id": "Global", "SpawnPoint": {"X": spawn[0] + 0.5, "Y": float(spawn[1]), "Z": spawn[2] + 0.5,
                                                         "Pitch": 0, "Yaw": 0, "Roll": 0}},
        "GameMode": "Adventure",
        "IsSpawnMarkersEnabled": True,
        "IsBlockSpawnersEnabled": True,
        "IsSavingPlayers": True,
        "DeleteOnRemove": True,
        # Vide pendant que le groupe est en fractale : il revient ensuite au même Observatoire (retiré au bout de
        # `removal` secondes ; le jeu en rouvre un neuf si le groupe revient plus tard).
        "Plugin": {"Instance": {"RemovalConditions": [{"Type": "WorldEmpty", "TimeoutSeconds": removal}]}},
    }
    if portal:
        doc["Plugin"]["PortalWorldConfig"] = {"Config": {"PortalType": OBSERVATORY, "TimeLimitSeconds": -1}}
    return doc


def biome(name, prefab):
    """Monde vide : aucune densité, le prefab posé à hauteur fixe porte toute l'île."""
    return {
        "Name": name,
        "Terrain": {"Type": "DAOTerrain", "Density": {"Type": "Constant", "Value": -1.0}},
        "MaterialProvider": {"Type": "Constant", "Material": {"Solid": "Empty"}},
        "Props": [{
            "Runtime": 0,
            "ContextPrecision": "Prop",
            "PropDistribution": {
                "Type": "Assigned",
                "OverrideAllProps": True,
                "PropDistribution": {"Type": "Positions", "Positions": {"Type": "List", "Positions": [
                    {"X": 0, "Y": GROUND_Y, "Z": 0}]}},
                "Assignments": {"Type": "Constant", "Prop": {"Type": "Prefab", "WeightedPrefabPaths": [
                    {"Path": f"{PREFABS}/{prefab}", "Weight": 1.0}]}},
            },
        }],
        "EnvironmentProvider": {"Type": "Constant", "Environment": ENVIRONMENT},
        "TintProvider": {"Type": "Constant", "Color": "#5a6ab0"},
    }


def world_structure(biome_name, spawn):
    return {
        "Type": "NoiseRange",
        "DefaultBiome": biome_name,
        "DefaultTransitionDistance": 16,
        "MaxBiomeEdgeDistance": 0,
        "Density": {"Type": "Constant", "Value": 0.0},
        "Biomes": [],
        "SpawnPositions": {"Type": "List", "Positions": [{"X": spawn[0], "Y": spawn[1], "Z": spawn[2]}]},
    }


def interactions():
    out = {
        "Nakasar_Fractal_Use_Dial": {
            "$Comment": "Cadran de l'Astrolabe : monte le niveau du groupe d'un cran, accroupi le descend (meneur seulement).",
            "Type": "Nakasar_Fractal_Dial"},
        "Nakasar_Fractal_Use_Trial_Panel": {
            "$Comment": "Pupitre du golem d'essai : le golem rejoue sur le joueur les attaques annoncées du mod "
                        "(cercle, cône, ligne, puis la cage), pour les voir et les tester.",
            "Type": "Nakasar_Fractal_TrialDemo"},
        "Nakasar_Fractal_Use_Exit": {
            "$Comment": "Pierre de retour d'une fractale : ramène le joueur à l'Observatoire.",
            "Type": "Nakasar_Fractal_Leave"},
        "Nakasar_Fractal_Use_Infusion_Altar": {
            "$Comment": "Autel des infusions : ouvre les 12 emplacements d'infusion du joueur (portés par lui).",
            "Type": "Nakasar_Fractal_OpenInfusions"},
        "Nakasar_Fractal_Use_Reward_Chest": {
            "$Comment": "Coffre de fin de fractale : un coffre par joueur du groupe, et le niveau suivant débloqué.",
            "Type": "Nakasar_Fractal_ClaimReward"},
        "Nakasar_Fractal_Use_Archivist_Counter": {
            "$Comment": "Comptoir de l'Archiviste : sa boutique de troc (comme lui parler).",
            "Type": "Nakasar_Fractal_OpenShop", "Shop": "Nakasar_Fractal_Archivist"},
        "Nakasar_Fractal_Read_Registry": {
            "$Comment": "Registre des fractales : page de lore du jeu (nom et description du bloc).",
            "Type": "OpenCustomUI", "Page": {"Id": "BlockLore", "TextAlignment": "Left"}},
    }
    for fid, *_ in FRACTALS:
        out[f"Nakasar_Fractal_Use_Arch_{fid}"] = {
            "$Comment": f"Arche de la fractale {fid} : le meneur y envoie tout le cercle d'harmonisation.",
            "Type": "Nakasar_Fractal_OpenArch", "Fractal": fid}
    return out


def golem_model():
    return {
        "$Comment": "Golem d'essai de l'Observatoire : le golem d'acier vanilla (Golem_Firesteel), sans ses flammes, "
                    "lueur bleue des Brumes.",
        "Parent": "Golem_Firesteel",
        "Particles": [],
        "Light": {"Color": "#6a8aff", "Radius": 2},
    }


def golem_role():
    """Mannequin immobile : ne riposte pas, encaisse tout (le Java lui rend ses PV et annonce les dégâts)."""
    return {
        "$Comment": "Golem d'essai de l'Observatoire : posé par TrialGolemSystem, immobile, ne riposte jamais. Les "
                    "dégâts reçus sont annoncés au joueur et ses PV remontent après chaque série de coups. Son pupitre "
                    "lui fait rejouer les attaques annoncées du mod. Généré par tools/generate_observatory.py.",
        "Type": "Generic",
        "Appearance": GOLEM,
        "NameTranslationKey": f"{LANG}.npc.Trial_Golem.name",
        "MaxHealth": 100000,
        "StartState": "Idle",
        "DefaultPlayerAttitude": "Neutral",
        "DefaultNPCAttitude": "Ignore",
        "MotionControllerList": [{"Type": "Walk", "MaxWalkSpeed": 0.1, "Gravity": 10, "MaxFallSpeed": 10,
                                  "Acceleration": 10, "JumpHeight": 1.0}],
        "KnockbackScale": 0,
        "DeathAnimationTime": 1.0,
        "Instructions": [{"Sensor": {"Type": "State", "State": "Idle"}, "Instructions": [{"Actions": []}]}],
    }


# --- langues ------------------------------------------------------------------------------------

def lang():
    fr = {
        "items.Nakasar_Fractal_Cage_Cell.name": "Cage de fractale (cible de l'emprisonnement)",
        f"items.{KEY}.name": "Fragment des Brumes",
        f"items.{KEY}.description": "Un éclat des Brumes, figé dans la pierre runique. Posé dans l'Ancienne passerelle, "
                                    "il ouvre l'Observatoire des fractales.",
        "portal.name": "Observatoire des fractales",
        "portal.flavor": "Une île suspendue dans les Brumes, d'où l'on part vers les fractales.",
        "portal.tag.hub": "Brumes",
        "portal.tag.group": "1 à 5 joueurs",
        "portal.objective": "Former un groupe au cercle d'harmonisation et choisir une arche",
        f"items.{DIAL}.name": "Cadran de l'Astrolabe",
        f"items.{DIAL}.description": "Utiliser : niveau suivant. Accroupi : niveau précédent. Seul le meneur le règle.",
        f"items.{ASTROLABE_RING}.name": "Anneau de l'Astrolabe",
        f"items.{ASTROLABE_RING}.description": "Anneau armillaire de l'Astrolabe.",
        f"items.{HARMONY}.name": "Dalle d'harmonisation",
        f"items.{HARMONY}.description": "Les joueurs debout sur le cercle forment le groupe (5 au plus).",
        f"items.{TRIAL}.name": "Pupitre du golem d'essai",
        f"items.{TRIAL}.description": "Utiliser : le golem rejoue sur vous les attaques des fractales.",
        f"items.{EXIT_STONE}.name": "Pierre de retour",
        f"items.{EXIT_STONE}.description": "Utiliser : retour à l'Observatoire.",
        f"items.{ALTAR}.name": "Autel des infusions",
        f"items.{ALTAR}.description": "Utiliser : vos 12 emplacements d'infusion. Chaque infusion posée ajoute sa "
                                      "résistance à l'agonie, où que vous soyez ; la retirer l'enlève.",
        f"items.{FORGE}.name": "Creuset des Brumes",
        f"items.{FORGE}.description": "Fusionne deux infusions identiques en la suivante, et refait un Fragment des "
                                      "Brumes avec des éclats.",
        f"items.{REWARD_CHEST}.name": "Coffre de fin de fractale",
        f"items.{REWARD_CHEST}.description": "Utiliser : votre récompense (une par joueur du groupe). Terminer une "
                                             "fractale à votre plus haut niveau débloque le suivant.",
        f"items.{COUNTER_BLOCK}.name": "Comptoir de l'Archiviste",
        f"items.{COUNTER_BLOCK}.description": "Utiliser : échanger des éclats de Brume contre des infusions et des "
                                              "fragments.",
        f"items.{REGISTRY_BLOCK}.name": "Registre des fractales",
        f"items.{REGISTRY_BLOCK}.description": (
            "Bienvenue dans l'Observatoire, voyageur des Brumes.\n\n"
            "1. Montez sur le cercle d'harmonisation autour de l'Astrolabe : les joueurs qui s'y tiennent forment le "
            "groupe, cinq au plus. Le premier arrivé dans l'Observatoire le mène.\n"
            "2. Le meneur règle le niveau au cadran de l'Astrolabe (accroupi pour descendre).\n"
            "3. Le meneur utilise la pierre d'une arche : tout le cercle part pour cette fractale.\n\n"
            "Saison 1 : Falaise, Inclassable, Volcanique, Océan solide, Marais, Tempête de neige.\n"
            "Le golem d'essai, à l'ouest, sert à tester ses coups, sa résistance à l'agonie et à voir les attaques "
            "des fractales.\n"
            "À l'est, l'Archiviste échange les éclats de Brume ; l'Autel des infusions porte votre résistance à "
            "l'agonie et le Creuset des Brumes fusionne les infusions.\n"
            "Chaque fractale terminée à votre plus haut niveau débloque le suivant ; le meneur ne peut choisir qu'un "
            "niveau qu'il a débloqué.\n\n"
            "Commande de secours : /fractale (niveau, groupe, lancer, quitter, infos)."),
        "npc.Trial_Golem.name": "Golem d'essai",
        "observatory.leader": "Vous menez le groupe de l'Observatoire.",
        "observatory.newLeader": "{name} mène désormais le groupe.",
        "observatory.joined": "Harmonisé avec le groupe ({count}/5).",
        "observatory.left": "Vous quittez le cercle d'harmonisation.",
        "observatory.full": "Le cercle d'harmonisation est complet (5 joueurs).",
        "observatory.level.title": "Niveau {level}",
        "observatory.level.rank": "Rang {rank}",
        "observatory.level.same": "Le niveau est déjà {level}.",
        "observatory.notLeader": "Seul le meneur, {name}, peut faire cela.",
        "observatory.notHere": "Cela se fait dans l'Observatoire des fractales.",
        "observatory.launch": "{fractal}, niveau {level} : le groupe part.",
        "observatory.soon": "{fractal} n'est pas encore ouverte.",
        "observatory.unknown": "Fractale inconnue : {fractal}.",
        "observatory.launchFailed": "La fractale n'a pas pu s'ouvrir.",
        "observatory.left.fractal": "Retour à l'Observatoire.",
        "observatory.notInFractal": "Vous n'êtes pas dans une fractale.",
        "observatory.group": "Groupe ({count}/5), niveau {level}, meneur {leader} : {names}",
        "observatory.fallRescue": "Les Brumes vous ramènent sur l'île.",
        "rank.Initiate": "Initié", "rank.Adept": "Adepte", "rank.Expert": "Expert", "rank.Master": "Maître",
        "trial.hit": "Golem d'essai : {damage} dégâts.",
        "trial.demo": "Le golem d'essai rejoue les attaques des fractales : cercle d'agonie, cône, ligne, puis la cage.",
        "trial.busy": "Le golem d'essai est déjà en démonstration.",
        "trial.noGolem": "Le golem d'essai n'est pas là.",
        "command.desc": "Fractales des Brumes : niveau, groupe, lancement et retour.",
        "command.level.desc": "Règle le niveau du groupe (meneur, dans l'Observatoire).",
        "command.level.arg": "Niveau de 1 à 100",
        "command.group.desc": "Affiche le groupe d'harmonisation.",
        "command.launch.desc": "Lance une fractale pour le cercle (meneur, dans l'Observatoire).",
        "command.launch.arg": "Fractale (Cliffside, Uncategorized, Volcanic, SolidOcean, Swampland, Snowblind)",
        "command.leave.desc": "Quitte la fractale et revient à l'Observatoire.",
    }
    en = {
        "items.Nakasar_Fractal_Cage_Cell.name": "Fractal Cage (imprisonment target)",
        f"items.{KEY}.name": "Mist Fragment",
        f"items.{KEY}.description": "A shard of the Mists, set in runestone. Placed in the Ancient Gateway, it opens the "
                                    "Fractal Observatory.",
        "portal.name": "Fractal Observatory",
        "portal.flavor": "An island hanging in the Mists, where fractal journeys begin.",
        "portal.tag.hub": "Mists",
        "portal.tag.group": "1 to 5 players",
        "portal.objective": "Form a group on the attunement circle and pick an arch",
        f"items.{DIAL}.name": "Astrolabe Dial",
        f"items.{DIAL}.description": "Use: next level. Crouch: previous level. Only the leader sets it.",
        f"items.{ASTROLABE_RING}.name": "Astrolabe Ring",
        f"items.{ASTROLABE_RING}.description": "Armillary ring of the Astrolabe.",
        f"items.{HARMONY}.name": "Attunement Tile",
        f"items.{HARMONY}.description": "Players standing on the circle form the group (5 at most).",
        f"items.{TRIAL}.name": "Training Golem Console",
        f"items.{TRIAL}.description": "Use: the golem replays the fractal attacks on you.",
        f"items.{EXIT_STONE}.name": "Return Stone",
        f"items.{EXIT_STONE}.description": "Use: back to the Observatory.",
        f"items.{ALTAR}.name": "Infusion Altar",
        f"items.{ALTAR}.description": "Use: your 12 infusion slots. Each infusion placed adds its agony resistance, "
                                      "wherever you are; removing it takes it away.",
        f"items.{FORGE}.name": "Mist Crucible",
        f"items.{FORGE}.description": "Fuses two identical infusions into the next one, and remakes a Mist Fragment "
                                      "from shards.",
        f"items.{REWARD_CHEST}.name": "Fractal Reward Chest",
        f"items.{REWARD_CHEST}.description": "Use: your reward (one per group member). Completing a fractal at your "
                                             "highest level unlocks the next one.",
        f"items.{COUNTER_BLOCK}.name": "Archivist's Counter",
        f"items.{COUNTER_BLOCK}.description": "Use: trade Mist Shards for infusions and fragments.",
        f"items.{REGISTRY_BLOCK}.name": "Fractal Registry",
        f"items.{REGISTRY_BLOCK}.description": (
            "Welcome to the Observatory, traveller of the Mists.\n\n"
            "1. Step onto the attunement circle around the Astrolabe: players standing on it form the group, five at "
            "most. The first to arrive in the Observatory leads it.\n"
            "2. The leader sets the level at the Astrolabe dial (crouch to lower it).\n"
            "3. The leader uses an arch stone: the whole circle leaves for that fractal.\n\n"
            "Season 1: Cliffside, Uncategorized, Volcanic, Solid Ocean, Swampland, Snowblind.\n"
            "The training golem, to the west, lets you test your hits, your agony resistance and see the fractal "
            "attacks.\n"
            "To the east, the Archivist trades Mist Shards; the Infusion Altar holds your agony resistance and the "
            "Mist Crucible fuses infusions.\n"
            "Each fractal completed at your highest level unlocks the next; the leader can only pick a level they "
            "have unlocked.\n\n"
            "Fallback command: /fractale (niveau, groupe, lancer, quitter, infos)."),
        "npc.Trial_Golem.name": "Training Golem",
        "observatory.leader": "You lead the Observatory group.",
        "observatory.newLeader": "{name} now leads the group.",
        "observatory.joined": "Attuned with the group ({count}/5).",
        "observatory.left": "You leave the attunement circle.",
        "observatory.full": "The attunement circle is full (5 players).",
        "observatory.level.title": "Level {level}",
        "observatory.level.rank": "{rank} rank",
        "observatory.level.same": "The level is already {level}.",
        "observatory.notLeader": "Only the leader, {name}, can do that.",
        "observatory.notHere": "This is done in the Fractal Observatory.",
        "observatory.launch": "{fractal}, level {level}: the group sets off.",
        "observatory.soon": "{fractal} is not open yet.",
        "observatory.unknown": "Unknown fractal: {fractal}.",
        "observatory.launchFailed": "The fractal could not open.",
        "observatory.left.fractal": "Back to the Observatory.",
        "observatory.notInFractal": "You are not in a fractal.",
        "observatory.group": "Group ({count}/5), level {level}, leader {leader}: {names}",
        "observatory.fallRescue": "The Mists carry you back to the island.",
        "rank.Initiate": "Initiate", "rank.Adept": "Adept", "rank.Expert": "Expert", "rank.Master": "Master",
        "trial.hit": "Training golem: {damage} damage.",
        "trial.demo": "The training golem replays the fractal attacks: agony circle, cone, line, then the cage.",
        "trial.busy": "The training golem is already demonstrating.",
        "trial.noGolem": "The training golem is not here.",
        "command.desc": "Fractals of the Mists: level, group, launch and return.",
        "command.level.desc": "Sets the group level (leader, in the Observatory).",
        "command.level.arg": "Level from 1 to 100",
        "command.group.desc": "Shows the attunement group.",
        "command.launch.desc": "Launches a fractal for the circle (leader, in the Observatory).",
        "command.launch.arg": "Fractal (Cliffside, Uncategorized, Volcanic, SolidOcean, Swampland, Snowblind)",
        "command.leave.desc": "Leaves the fractal and returns to the Observatory.",
    }
    for fid, name_fr, name_en, *_ in FRACTALS:
        fr[f"fractal.{fid}.name"] = name_fr
        en[f"fractal.{fid}.name"] = name_en
        fr[f"items.{arch_stone(fid)}.name"] = f"Arche : {name_fr}"
        en[f"items.{arch_stone(fid)}.name"] = f"Arch: {name_en}"
        fr[f"items.{arch_stone(fid)}.description"] = FLAVOR[fid][0] + "\n\nLe meneur l'utilise pour y envoyer le cercle."
        en[f"items.{arch_stone(fid)}.description"] = FLAVOR[fid][1] + "\n\nThe leader uses it to send the circle there."
    return fr, en


def write_lang(path, entries):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for k, v in entries.items():
        lines.append(f"{k} = {v.replace(chr(10), chr(92) + 'n')}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --- Java ---------------------------------------------------------------------------------------

def java_layout(arches):
    rows = ",\n".join(f'            new Arch("{fid}", {cx}, {cz})' for fid, cx, cz in arches)
    return f"""package dev.nakasar.hytale.fractals.observatory;

import java.util.List;

/**
 * Positions de l'île de l'Observatoire, écrites par tools/generate_observatory.py (ne pas modifier à la main : relancer
 * le générateur). Repère du monde : x vers l'est, z vers le sud ; le centre de l'Astrolabe est en (0, {GROUND_Y}, 0).
 */
public final class ObservatoryLayout {{

    /** Première couche d'air au-dessus du dallage de l'île. */
    public static final int GROUND_Y = {GROUND_Y};
    public static final int ISLAND_RADIUS = {ISLAND_RADIUS};
    /** Cercle d'harmonisation : distance horizontale au centre de l'Astrolabe (blocs), bords compris. */
    public static final double CIRCLE_INNER = {CIRCLE_INNER - 0.5};
    public static final double CIRCLE_OUTER = {CIRCLE_OUTER + 0.5};
    /** Point d'arrivée (pieds) sur le parvis. */
    public static final double[] ARRIVAL = {{{ARRIVAL[0] + 0.5}, {float(ARRIVAL[1])}, {ARRIVAL[2] + 0.5}}};
    /** Golem d'essai (pieds). */
    public static final double[] GOLEM = {{{GOLEM_SPOT[0] + 0.5}, {float(GOLEM_SPOT[1])}, {GOLEM_SPOT[2] + 0.5}}};
    /** Bloc de la cage d'essai (Nakasar_Fractal_Cage_Cell, au niveau des pieds). */
    public static final int[] TRIAL_CAGE = {{{TRIAL_CAGE[0]}, {GROUND_Y + TRIAL_CAGE[1]}, {TRIAL_CAGE[2]}}};
    /** Où revient le joueur à l'ouverture de la cage d'essai (pieds), près du pupitre. */
    public static final double[] TRIAL_RELEASE = {{{TRIAL_PANEL[0] + 1.5}, {float(GROUND_Y + TRIAL_PANEL[1])}, {TRIAL_PANEL[2] + 2.5}}};
    /** L'Archiviste (pieds), derrière son comptoir, tourné vers l'ouest. */
    public static final double[] ARCHIVIST = {{{ARCHIVIST_SPOT[0] + 0.5}, {float(ARCHIVIST_SPOT[1])}, {ARCHIVIST_SPOT[2] + 0.5}}};
    /** Pierre de chaque arche (bloc au sol). */
    public static final List<Arch> ARCHES = List.of(
{rows});

    private ObservatoryLayout() {{
    }}

    /** Arche d'une fractale : id ({{@code FractalCatalog}}) et position de sa pierre. */
    public record Arch(String fractal, int x, int z) {{
    }}
}}
"""


# --- écriture -----------------------------------------------------------------------------------

def write_json(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    (COMMON / TEXTURES).mkdir(parents=True, exist_ok=True)
    (COMMON / ICONS).mkdir(parents=True, exist_ok=True)

    stone = (74, 82, 120)
    blocks = [
        (DIAL, "Astrolabe_Dial", stone, (255, 214, 110), "dial", "#fd8", "Nakasar_Fractal_Use_Dial"),
        (ASTROLABE_RING, "Astrolabe_Ring", (150, 120, 60), (255, 230, 150), "ring", "#fe9", None),
        (HARMONY, "Harmony_Tile", (40, 60, 110), (120, 190, 255), "tile", "#6bf", None),
        (TRIAL, "Trial_Panel", stone, (140, 170, 255), "panel", "#8af", "Nakasar_Fractal_Use_Trial_Panel"),
        (EXIT_STONE, "Exit_Stone", stone, (190, 160, 255), "exit", "#b9f", "Nakasar_Fractal_Use_Exit"),
        (REGISTRY_BLOCK, "Registry", (90, 60, 40), (210, 190, 150), "book", None, "Nakasar_Fractal_Read_Registry"),
    ]
    blocks += [
        (ALTAR, "Infusion_Altar", (60, 50, 100), (200, 140, 255), "altar", "#c8f", "Nakasar_Fractal_Use_Infusion_Altar"),
        (FORGE, "Mist_Forge", (50, 46, 70), (160, 120, 255), "forge", "#a8f", None),
        (REWARD_CHEST, "Reward_Chest", (70, 60, 110), (255, 210, 110), "chest", "#fd8", "Nakasar_Fractal_Use_Reward_Chest"),
        (COUNTER_BLOCK, "Archivist_Counter", (90, 60, 40), (150, 200, 255), "counter", None,
         "Nakasar_Fractal_Use_Archivist_Counter"),
    ]
    for fid, _, _, color, *_ in FRACTALS:
        blocks.append((arch_stone(fid), f"Arch_{fid}", stone, color, "arch", short_light(color),
                       f"Nakasar_Fractal_Use_Arch_{fid}"))
    previews = []
    for name, tex, base, accent, glyph, light, use in blocks:
        img = texture(COMMON / TEXTURES / f"{tex}.png", base, accent, glyph)
        icon(COMMON / ICONS / f"{tex}.png", img)
        previews.append(img)
        if name == FORGE:
            doc = bench_item(name, tex)
        else:
            doc = block_item(name, tex, light, use, particle=hexcolor(accent))
            if name == ALTAR:
                doc = portable(doc, name)
        write_json(ITEMS / f"{name}.json", doc)
    key_tex = texture(COMMON / TEXTURES / "PortalKey_Fractal.png", (40, 50, 110), (150, 200, 255), "ring")
    icon(COMMON / ICONS / "PortalKey_Fractal.png", key_tex)
    (COMMON / CATEGORY_ICONS).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(COMMON / ICONS / "PortalKey_Fractal.png", COMMON / CATEGORY_ICONS / "Fragments.png")
    (COMMON / TEXTURES / "PortalKey_Fractal.png").unlink()

    write_json(SERVER / "Item/Items/Portal/Nakasar" / f"{KEY}.json", key_item())
    write_json(SERVER / "Item/Recipes/Nakasar" / f"Recipe_{KEY}.json", key_recipe())
    for name, doc in interactions().items():
        write_json(INTERACTIONS / f"{name}.json", doc)
    write_json(SERVER / "PortalTypes" / f"{OBSERVATORY}.json", portal_type())
    write_json(SERVER / "GameplayConfigs" / f"{OBSERVATORY}.json", gameplay_config())
    write_json(SERVER / "Weathers" / f"{WEATHER}.json", weather())
    write_json(SERVER / "Environments" / f"{ENVIRONMENT}.json", environment())

    write_json(SERVER / "Instances" / OBSERVATORY / "instance.bson",
               instance(OBSERVATORY, "Observatoire des fractales", OBSERVATORY))
    write_json(SERVER / "HytaleGenerator/Biomes" / f"{OBSERVATORY}.json", biome(OBSERVATORY, "Observatory"))
    write_json(SERVER / "HytaleGenerator/WorldStructures" / f"{OBSERVATORY}.json", world_structure(OBSERVATORY, ARRIVAL))
    obs, arches = observatory_prefab()
    n = obs.write(SERVER / "Prefabs" / PREFABS / "Observatory" / "Observatory.prefab.json")

    write_json(SERVER / "Models" / "Nakasar" / "Fractals" / f"{GOLEM}.json", golem_model())
    write_json(SERVER / "NPC/Roles/Nakasar/Fractals" / f"{GOLEM}.json", golem_role())

    fr, en = lang()
    write_lang(SERVER / "Languages/fr-FR" / f"{LANG}.lang", fr)
    write_lang(SERVER / "Languages/en-US" / f"{LANG}.lang", en)
    JAVA_LAYOUT.parent.mkdir(parents=True, exist_ok=True)
    JAVA_LAYOUT.write_text(java_layout(arches), encoding="utf-8")
    print(f"Observatoire : {n} blocs, {len(blocks)} blocs du mod")

    if preview:
        preview.mkdir(parents=True, exist_ok=True)
        sheet = Image.new("RGBA", (34 * len(previews), 34), (20, 20, 30, 255))
        for k, img in enumerate(previews):
            sheet.alpha_composite(img, (34 * k + 1, 1))
        sheet.resize((sheet.width * 4, sheet.height * 4), Image.NEAREST).save(preview / "blocs.png")
        plan(obs, preview / "observatoire.png")


def plan(p, path):
    """Vue de dessus du prefab (dessus de chaque colonne), 6 pixels par bloc."""
    colors = {}
    def color(name):
        if name not in colors:
            h = abs(hash(name)) % 360
            colors[name] = tuple(int(100 + 80 * math.sin(math.radians(h + k * 120))) for k in range(3))
        return colors[name]
    r = ISLAND_RADIUS + 2
    img = Image.new("RGB", ((2 * r + 1) * 6, (2 * r + 1) * 6), (10, 12, 30))
    d = ImageDraw.Draw(img)
    top = {}
    for (x, y, z), (name, _) in p.blocks.items():
        if name != AIR and (x, z) not in top or name != AIR and y > top[(x, z)][0]:
            top[(x, z)] = (y, name)
    for (x, z), (_, name) in top.items():
        c = color(name)
        if name.startswith("Nakasar_Fractal_Arch"):
            c = (255, 255, 255)
        if name == HARMONY:
            c = (90, 160, 255)
        d.rectangle(((x + r) * 6, (z + r) * 6, (x + r) * 6 + 5, (z + r) * 6 + 5), fill=c)
    img.save(path)


if __name__ == "__main__":
    main()
