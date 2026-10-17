#!/usr/bin/env python3
"""Génère les prefabs du Fragment halloween (format .prefab.json version 8).

Les structures sont décrites procéduralement (murs, tours, toits, mobilier) puis écrites dans
pack/Server/Prefabs/Nakasar/Halloween/<Catégorie>/<Nom>.prefab.json. Le générateur est
déterministe : relancer le script reproduit exactement les mêmes fichiers.

    python3 mods/nakasar-halloween/tools/generate_prefabs.py

Repère des prefabs : x vers l'est, z vers le sud, y vers le haut. Le worldgen pose le prefab sur
le premier bloc d'air au-dessus du sol : y = 0 est donc la première couche d'air, y = -1 le sol
(remplacé par le dallage de la structure) et y < -1 les fondations et les souterrains.

Un nom de bloc peut être préfixé par une probabilité (« 70%Rock_Stone_Brick ») : le serveur ne
pose alors le bloc qu'avec cette probabilité, à chaque génération. C'est ce qui rend chaque ruine
différente.
"""

import json
import random
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent / "pack"
OUT = PACK / "Server" / "Prefabs" / "Nakasar" / "Halloween"

AIR = "Empty"

# Rotations de bloc (index RotationTuple = yaw, sans tangage ni roulis).
NORTH, EAST, SOUTH, WEST = 0, 1, 2, 3


class Prefab:
    """Grille de blocs creuse ; la dernière écriture d'une case l'emporte."""

    def __init__(self, seed):
        self.blocks = {}
        self.rng = random.Random(seed)

    # --- primitives -------------------------------------------------------------------------

    def set(self, x, y, z, name, rot=0):
        if name is None:
            self.blocks.pop((x, y, z), None)
        else:
            self.blocks[(x, y, z)] = (name, rot)

    def get(self, x, y, z):
        b = self.blocks.get((x, y, z))
        return b[0] if b else None

    def fill(self, x0, y0, z0, x1, y1, z1, name, rot=0):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    self.set(x, y, z, self.pick(name), rot)

    def hollow(self, x0, y0, z0, x1, y1, z1, wall, inside=AIR):
        """Boîte : murs latéraux en `wall`, intérieur en `inside` (sol et plafond non compris)."""
        self.fill(x0, y0, z0, x1, y1, z1, inside)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.set(x, y, z0, self.pick(wall))
                self.set(x, y, z1, self.pick(wall))
            for z in range(z0, z1 + 1):
                self.set(x0, y, z, self.pick(wall))
                self.set(x1, y, z, self.pick(wall))

    def pick(self, palette):
        """Une palette est un nom, ou une liste de (nom, poids) tirée à chaque bloc."""
        if isinstance(palette, str) or palette is None:
            return palette
        names = [p[0] for p in palette]
        weights = [p[1] for p in palette]
        return self.rng.choices(names, weights)[0]

    def floor(self, x0, z0, x1, z1, y, palette, foundation=None, depth=5):
        """Dallage à la hauteur y, avec des fondations sous le dallage (cache les bords flottants)."""
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for z in range(min(z0, z1), max(z0, z1) + 1):
                self.set(x, y, z, self.pick(palette))
                if foundation:
                    for d in range(1, depth + 1):
                        self.set(x, y - d, z, self.pick(foundation))

    def clear(self, x0, y0, z0, x1, y1, z1):
        self.fill(x0, y0, z0, x1, y1, z1, AIR)

    def crenellate(self, x0, z0, x1, z1, y, palette):
        """Merlons un bloc sur deux sur le pourtour du rectangle."""
        for x in range(x0, x1 + 1):
            if (x - x0) % 2 == 0:
                self.set(x, y, z0, self.pick(palette))
                self.set(x, y, z1, self.pick(palette))
        for z in range(z0, z1 + 1):
            if (z - z0) % 2 == 0:
                self.set(x0, y, z, self.pick(palette))
                self.set(x1, y, z, self.pick(palette))

    def spire(self, cx, cz, half, y, palette, step=2):
        """Flèche pyramidale à degrés (anneaux pleins) ; chaque anneau monte de `step` blocs."""
        for r in range(half, -1, -1):
            for dy in range(step if r > 0 else 3):
                for x in range(cx - r, cx + r + 1):
                    for z in range(cz - r, cz + r + 1):
                        if r == 0 or abs(x - cx) == r or abs(z - cz) == r:
                            self.set(x, y, z, self.pick(palette))
                y += 1
        return y

    def ruin(self, chance, keep_below=0, names=None):
        """Transforme une partie des blocs en blocs probabilistes (pierre qui s'effrite).

        Les blocs sous `keep_below` (sol, fondations) restent pleins pour que la structure tienne.
        """
        for pos, (name, rot) in list(self.blocks.items()):
            if name == AIR or "%" in name or pos[1] < keep_below:
                continue
            if names is not None and name not in names:
                continue
            self.blocks[pos] = (f"{chance}%{name}", rot)

    def scatter(self, x0, y, z0, x1, z1, count, palette, require_air=True, rot=None):
        """Pose `count` décorations sur des cases libres d'une surface."""
        placed = 0
        for _ in range(count * 12):
            if placed >= count:
                break
            x = self.rng.randint(min(x0, x1), max(x0, x1))
            z = self.rng.randint(min(z0, z1), max(z0, z1))
            if require_air and self.get(x, y, z) not in (None, AIR):
                continue
            if self.get(x, y - 1, z) in (None, AIR):
                continue
            self.set(x, y, z, self.pick(palette), self.rng.randint(0, 3) if rot is None else rot)
            placed += 1

    # --- export -----------------------------------------------------------------------------

    def write(self, path):
        blocks = []
        for (x, y, z), (name, rot) in sorted(self.blocks.items(), key=lambda kv: (kv[0][1], kv[0][2], kv[0][0])):
            entry = {"x": x, "y": y, "z": z, "name": name}
            if rot:
                entry["rotation"] = rot
            blocks.append(entry)
        doc = {"version": 8, "blockIdVersion": 8, "anchorX": 0, "anchorY": 0, "anchorZ": 0}
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as f:
            f.write("{\n")
            for key, value in doc.items():
                f.write(f'  "{key}": {json.dumps(value)},\n')
            f.write('  "blocks": [\n')
            f.write(",\n".join("    " + json.dumps(b, separators=(",", ":")) for b in blocks))
            f.write("\n  ]\n}\n")
        return len(blocks)


# --- palettes ---------------------------------------------------------------------------------

STONE_WALL = [("Rock_Stone_Brick", 6), ("Rock_Stone_Brick_Mossy", 2), ("Rock_Stone_Cobble", 1), ("Rock_Stone_Cobble_Mossy", 1)]
STONE_FLOOR = [("Rock_Stone_Brick_Smooth", 4), ("Rock_Stone_Cobble", 2), ("Rock_Stone_Cobble_Mossy", 1)]
SLATE_WALL = [("Rock_Slate_Brick", 6), ("Rock_Slate_Cobble", 2), ("Rock_Slate_Cracked", 1)]
SLATE_FLOOR = [("Rock_Slate_Brick_Smooth", 3), ("Rock_Slate_Cobble", 1)]
BASALT_WALL = [("Rock_Basalt_Brick", 7), ("Rock_Basalt_Cobble", 2), ("Rock_Basalt_Brick_Decorative", 1)]
BASALT_FLOOR = [("Rock_Basalt_Brick_Smooth", 4), ("Rock_Basalt_Cobble", 1)]
SHALE_WALL = [("Rock_Shale_Brick", 6), ("Rock_Shale_Cobble", 3)]
FOUNDATION = [("Rock_Stone_Cobble", 3), ("Rock_Stone", 2)]
DEADWOOD = "Wood_Deadwood_Planks"
GRAVE_DIRT = [("Soil_Dirt_Burnt", 3), ("Soil_Dirt", 1), ("Soil_Gravel", 1)]
WEBS = [("Deco_SpiderWeb_Full", 3), ("Deco_SpiderWeb", 4), ("Deco_SpiderWeb_Diagonal", 2)]
BONES = [("Deco_Bone_Pile", 4), ("Deco_Bone_Skulls", 2), ("Deco_Bone_Ribs", 2), ("Deco_Bone_Full", 2), ("Deco_Bone_Spine", 1)]
CANDLES = [("Furniture_Ancient_Candle", 3), ("Furniture_Temple_Dark_Candle", 2), ("Furniture_Crude_Candle", 1)]
PUMPKINS = [("Deco_Halloween_Pumpkin_Scary", 4), ("Deco_Halloween_Pumpkin_Cute", 1), ("Deco_Halloween_Pumpkin_Hypixel", 1)]
DEAD_PLANTS = [("Plant_Bush_Dead", 3), ("Plant_Grass_Gnarled", 4), ("Plant_Grass_Gnarled_Short", 3), ("Plant_Bush_Dead_Twisted", 1)]

MATERIALS = {
    "stone": (STONE_WALL, STONE_FLOOR, "Rock_Stone_Brick", "Rock_Stone_Brick_Ornate"),
    "slate": (SLATE_WALL, SLATE_FLOOR, "Rock_Slate_Brick", "Rock_Slate_Brick_Ornate"),
    "basalt": (BASALT_WALL, BASALT_FLOOR, "Rock_Basalt_Brick", "Rock_Basalt_Brick_Ornate"),
    "shale": (SHALE_WALL, SLATE_FLOOR, "Rock_Shale_Brick", "Rock_Shale_Brick_Ornate"),
}


def stairs_down(p, start, direction, depth, base, wall, width=3, headroom=3):
    """Escalier en demi-dalles (pas de 0,5 bloc : aucune orientation de bloc à deviner).

    Part du sol (y = -1) en `start` = (x, z) et descend de `depth` blocs en avançant d'un bloc par
    demi-pas dans `direction` = (dx, dz) ; `width` cases de large vers la droite de la marche.
    Le tunnel est muré (`wall`) là où il traverse le terrain. Renvoie la dernière case (x, z) ; on y
    marche à la hauteur y = -depth.
    """
    half = base + "_Half"
    dx, dz = direction
    side = (-dz, dx)  # perpendiculaire
    x, z = start
    for i in range(1, 2 * depth + 1):
        x, z = start[0] + dx * (i - 1), start[1] + dz * (i - 1)
        if i % 2 == 0:
            k = -(i // 2)  # première case d'air au-dessus de la marche
            steps = [(k - 1, base)]
        else:
            k = -((i - 1) // 2)
            steps = [(k - 1, half), (k - 2, base)]
        for w in range(-1, width + 1):
            cx, cz = x + side[0] * w, z + side[1] * w
            if w in (-1, width):
                for y in range(k - 2, k + headroom + 1):
                    if p.get(cx, y, cz) is None:
                        p.set(cx, y, cz, p.pick(wall))
                continue
            for y in range(k, k + headroom):
                p.set(cx, y, cz, AIR)
            for y, name in steps:
                p.set(cx, y, cz, name)
            if k + headroom <= -1 and p.get(cx, k + headroom, cz) is None:
                p.set(cx, k + headroom, cz, p.pick(wall))
    return x, z


# --- dead trees -------------------------------------------------------------------------------

def dead_tree(seed, webs=False):
    p = Prefab(seed)
    r = p.rng
    height = r.randint(5, 9)
    p.set(0, -1, 0, "Wood_Burnt_Roots")
    for y in range(0, height):
        p.set(0, y, 0, "Wood_Burnt_Trunk")
    if r.random() < 0.5:
        p.set(0, height, 0, "Wood_Burnt_Branch_Short")
    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    r.shuffle(dirs)
    for i, (dx, dz) in enumerate(dirs[: r.randint(2, 4)]):
        y = r.randint(height // 2, height - 1)
        length = r.randint(2, 4)
        for k in range(1, length + 1):
            p.set(dx * k, y + (k // 2), dz * k, "Wood_Burnt_Branch_Long" if k < length else "Wood_Burnt_Branch_Short")
        if webs and r.random() < 0.7:
            p.set(dx, y - 1, dz, p.pick(WEBS))
    if r.random() < 0.4:
        p.set(r.choice([-1, 1]), 0, r.choice([-1, 1]), p.pick(DEAD_PLANTS))
    return p


def hanging_tree(seed):
    """Arbre mort avec une cage à corbeaux en fer et des os au pied."""
    p = dead_tree(seed, webs=True)
    p.set(2, 4, 0, "Wood_Burnt_Branch_Long")
    p.set(1, 4, 0, "Wood_Burnt_Branch_Long")
    p.set(2, 3, 0, "Deco_Iron_Bars")
    p.set(2, 2, 0, "Deco_Iron_Bars")
    p.set(1, 0, 1, "Deco_Bone_Pile")
    return p


# --- pumpkin fields ---------------------------------------------------------------------------

def pumpkin_field(seed, w=21, d=17):
    p = Prefab(seed)
    r = p.rng
    x0, z0, x1, z1 = -w // 2, -d // 2, w // 2, d // 2
    p.clear(x0, 0, z0, x1, 3, z1)
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            on_row = (z - z0) % 3 != 2
            p.set(x, -1, z, "Soil_Dirt_Tilled" if on_row else p.pick(GRAVE_DIRT))
            p.set(x, -2, z, "Soil_Dirt")
            if on_row and r.random() < 0.55 and not (abs(x) <= 1 and abs(z) <= 1):
                p.set(x, 0, z, r.choice(["Plant_Crop_Pumpkin_StageFinal", "Plant_Crop_Pumpkin_StageFinal", "Plant_Crop_Pumpkin_Stage_3"]))
            elif on_row and r.random() < 0.08:
                p.set(x, 0, z, p.pick(PUMPKINS), r.randint(0, 3))
    # clôture en bois mort, ouverte au sud
    for x in range(x0 - 1, x1 + 2):
        p.set(x, 0, z0 - 1, "Wood_Deadwood_Fence")
        if abs(x) > 1:
            p.set(x, 0, z1 + 1, "Wood_Deadwood_Fence")
    for z in range(z0 - 1, z1 + 2):
        p.set(x0 - 1, 0, z, "Wood_Deadwood_Fence")
        p.set(x1 + 1, 0, z, "Wood_Deadwood_Fence")
    p.set(0, 0, z1 + 1, "Wood_Deadwood_Fence_Gate")
    for x in range(x0 - 1, x1 + 2):
        for z in (z0 - 1, z1 + 1):
            p.set(x, -1, z, "Soil_Grass_Burnt")
    for z in range(z0 - 1, z1 + 2):
        for x in (x0 - 1, x1 + 1):
            p.set(x, -1, z, "Soil_Grass_Burnt")
    # épouvantail au centre, citrouilles-lanternes aux coins
    p.set(0, -1, 0, "Soil_Dirt")
    p.set(0, 0, 0, "Deco_Scarecrow", SOUTH)
    for cx, cz in ((x0 - 1, z0 - 1), (x1 + 1, z0 - 1), (x0 - 1, z1 + 1), (x1 + 1, z1 + 1)):
        p.set(cx, 0, cz, "Wood_Deadwood_Beam")
        p.set(cx, 1, cz, "Deco_Halloween_Pumpkin_Scary", r.randint(0, 3))
    # bottes de foin et charrette de citrouilles près de l'entrée
    for (hx, hz) in ((x1 - 1, z1 - 1), (x1 - 2, z1 - 1), (x1 - 1, z1 - 2)):
        p.set(hx, 0, hz, "Ingredient_Hay")
    p.set(x1 - 1, 1, z1 - 1, p.pick(PUMPKINS), r.randint(0, 3))
    p.set(x0 + 1, 0, z1 - 1, "Halloween_Basket_Pumpkin")
    # une cabane de fermier en ruine dans un coin, une fois sur deux
    if r.random() < 0.5:
        cx0, cz0 = x0 + 1, z0 + 1
        p.floor(cx0, cz0, cx0 + 4, cz0 + 3, -1, DEADWOOD)
        p.hollow(cx0, 0, cz0, cx0 + 4, 2, cz0 + 3, [("Wood_Deadwood_Planks", 5), ("Wood_Deadwood_Beam", 1)])
        p.set(cx0 + 2, 0, cz0 + 3, AIR)
        p.set(cx0 + 2, 1, cz0 + 3, AIR)
        p.fill(cx0, 3, cz0, cx0 + 4, 3, cz0 + 3, "Wood_Deadwood_Roof_Flat")
        p.set(cx0 + 1, 0, cz0 + 1, "Furniture_Crude_Candle")
        p.set(cx0 + 3, 0, cz0 + 1, "Furniture_Crude_Chest_Small", SOUTH)
        p.set(cx0 + 3, 2, cz0 + 2, p.pick(WEBS))
        p.ruin(85, keep_below=0, names={"Wood_Deadwood_Planks", "Wood_Deadwood_Roof_Flat"})
    return p


# --- cemeteries -------------------------------------------------------------------------------

def tomb(p, x, z, r, theme):
    """Une tombe orientée nord-sud : stèle au nord, terre retournée devant."""
    p.set(x, 0, z, r.choice(["Furniture_Village_Tombstone", "Furniture_Village_Tombstone", "Rock_Stone_Brick_Ornate"]), SOUTH)
    open_grave = theme == "undead" and r.random() < 0.45
    for dz in (1, 2):
        if open_grave:
            p.set(x, -1, z + dz, AIR)
            p.set(x, -2, z + dz, p.pick(GRAVE_DIRT))
            if dz == 2:
                p.set(x, -1, z + dz, p.pick(BONES), r.randint(0, 3))
        else:
            p.set(x, -1, z + dz, p.pick(GRAVE_DIRT))
    if theme == "haunted" and r.random() < 0.35:
        p.set(x + 1, 0, z, p.pick(CANDLES))
    if theme == "spiders" and r.random() < 0.4:
        p.set(x, 1, z, p.pick(WEBS))
    if r.random() < 0.15:
        p.set(x, 0, z + 1, p.pick(PUMPKINS), r.randint(0, 3))


def cemetery(seed, theme):
    p = Prefab(seed)
    r = p.rng
    w, d = r.choice([(25, 21), (27, 23), (23, 25)])
    x0, z0, x1, z1 = -w // 2, -d // 2, w // 2, d // 2
    p.clear(x0, 0, z0, x1, 4, z1)
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            p.set(x, -1, z, r.choice(["Soil_Grass_Burnt", "Soil_Grass_Burnt", "Soil_Dirt_Burnt", "Soil_Grass_Burnt_Full"]))
    # allée centrale pavée
    for z in range(z0, z1 + 1):
        p.set(0, -1, z, p.pick(STONE_FLOOR))
        p.set(-1, -1, z, p.pick(STONE_FLOOR) if r.random() < 0.6 else "Soil_Gravel")
    # muret + grille en fer, avec des trouées
    for x in range(x0, x1 + 1):
        for z in (z0, z1):
            if z == z1 and abs(x + 0.5) <= 1.5:
                continue
            p.set(x, 0, z, p.pick(STONE_WALL))
            if r.random() < 0.8:
                p.set(x, 1, z, "Deco_Iron_Bars")
    for z in range(z0, z1 + 1):
        for x in (x0, x1):
            p.set(x, 0, z, p.pick(STONE_WALL))
            if r.random() < 0.8:
                p.set(x, 1, z, "Deco_Iron_Bars")
    for px in (x0, x1):
        for pz in (z0, z1):
            p.fill(px, 0, pz, px, 2, pz, "Rock_Stone_Brick_Pillar_Middle")
            p.set(px, 3, pz, "Deco_Halloween_Pumpkin_Scary" if theme != "spiders" else "Deco_Spider_Cocoon", r.randint(0, 3))
    # portail
    p.fill(-2, 0, z1, -2, 3, z1, "Rock_Stone_Brick_Pillar_Middle")
    p.fill(1, 0, z1, 1, 3, z1, "Rock_Stone_Brick_Pillar_Middle")
    p.fill(-2, 4, z1, 1, 4, z1, "Rock_Stone_Brick_Ornate")
    p.set(-1, 4, z1, "Deco_Lantern")
    # rangées de tombes
    for x in list(range(x0 + 2, -2, 2)) + list(range(2, x1 - 1, 2)):
        for z in range(z0 + 2, z1 - 3, 4):
            if r.random() < 0.8:
                tomb(p, x, z, r, theme)
    # chapelle ou mausolée au fond
    cx0, cx1, cz0, cz1 = -3, 2, z0 + 1, z0 + 6
    if theme != "spiders" or r.random() < 0.5:
        p.floor(cx0, cz0, cx1, cz1, -1, STONE_FLOOR)
        p.hollow(cx0, 0, cz0, cx1, 4, cz1, STONE_WALL)
        p.clear(-1, 0, cz1, 0, 2, cz1)
        p.fill(cx0, 5, cz0, cx1, 5, cz1, "Rock_Stone_Brick_Roof_Flat")
        p.fill(cx0 + 1, 6, cz0 + 1, cx1 - 1, 6, cz1 - 1, "Rock_Stone_Brick_Roof_Flat")
        p.set(-1, 0, cz0 + 1, "Furniture_Ancient_Coffin", SOUTH)
        p.set(cx0 + 1, 0, cz0 + 1, p.pick(CANDLES))
        p.set(cx1 - 1, 0, cz0 + 1, p.pick(CANDLES))
        p.set(cx0 + 1, 3, cz1 - 1, p.pick(WEBS))
        p.set(cx1 - 1, 3, cz0 + 1, p.pick(WEBS))
        p.set(-1, 6, cz0 + 2, "Rock_Stone_Brick_Pillar_Middle")
        p.set(-1, 7, cz0 + 2, "Rock_Stone_Brick_Ornate")
    # décor selon le thème
    if theme == "haunted":
        p.scatter(x0 + 1, 0, z0 + 1, x1 - 1, z1 - 1, 10, CANDLES)
        p.scatter(x0 + 1, 0, z0 + 1, x1 - 1, z1 - 1, 6, PUMPKINS)
        p.scatter(x0 + 1, 0, z0 + 1, x1 - 1, z1 - 1, 8, DEAD_PLANTS)
    elif theme == "spiders":
        for _ in range(5):
            cx, cz = r.randint(x0 + 2, x1 - 2), r.randint(z0 + 2, z1 - 2)
            for dx in range(-2, 3):
                for dz in range(-2, 3):
                    if abs(dx) + abs(dz) <= 3 and r.random() < 0.6:
                        p.set(cx + dx, 0, cz + dz, "Deco_SpiderWeb_Flat")
            p.set(cx, 0, cz, "Deco_Spider_Cocoon")
        p.scatter(x0 + 1, 0, z0 + 1, x1 - 1, z1 - 1, 18, WEBS)
        p.scatter(x0 + 1, 0, z0 + 1, x1 - 1, z1 - 1, 5, [("Cocoon_Spider_Cave", 1), ("Deco_Spider_Cocoon", 2)])
    else:
        p.scatter(x0 + 1, 0, z0 + 1, x1 - 1, z1 - 1, 14, BONES)
        p.scatter(x0 + 1, 0, z0 + 1, x1 - 1, z1 - 1, 4, [("Deco_Bone_Spike", 2), ("Deco_Bone_Ribs_Long", 1)])
    # arbres morts dans les coins
    for tx, tz in ((x0 + 2, z1 - 2), (x1 - 2, z1 - 2)):
        if r.random() < 0.8:
            t = dead_tree(r.randint(0, 1 << 30), webs=theme == "spiders")
            for (bx, by, bz), (name, rot) in t.blocks.items():
                if by >= 0:
                    p.set(tx + bx, by, tz + bz, name, rot)
    p.ruin(80, keep_below=0, names={"Rock_Stone_Brick", "Rock_Stone_Brick_Mossy", "Rock_Stone_Cobble", "Rock_Stone_Cobble_Mossy", "Deco_Iron_Bars"})
    return p


# --- crypts -----------------------------------------------------------------------------------

def crypt(seed, material):
    """Mausolée en surface et salle voûtée enterrée au nord, reliés par un escalier."""
    p = Prefab(seed)
    r = p.rng
    wall, flr, roof, ornate = MATERIALS[material]
    brick = wall[0][0]
    depth = 7
    # salle enterrée : sol à y = -depth - 1, voûte à y = -depth + 4 (sous la couche de terre)
    cy0 = -depth - 1
    cx0, cx1, cz0, cz1 = -6, 6, -23, -12
    for x in range(cx0 - 1, cx1 + 2):
        for y in range(cy0, cy0 + 6):
            for z in range(cz0 - 1, cz1 + 2):
                p.set(x, y, z, p.pick(wall))
    p.floor(cx0, cz0, cx1, cz1, cy0, flr)
    p.clear(cx0, cy0 + 1, cz0, cx1, cy0 + 4, cz1)
    for px in (cx0 + 3, cx1 - 3):
        for pz in (cz0 + 3, cz1 - 3):
            p.fill(px, cy0 + 1, pz, px, cy0 + 4, pz, ornate)
    # mausolée 9 x 11
    x0, x1, z0, z1 = -4, 4, -5, 5
    p.floor(x0 - 1, z0 - 1, x1 + 1, z1 + 1, -1, flr, FOUNDATION, depth=2)
    p.hollow(x0, 0, z0, x1, 5, z1, wall)
    for x in (x0, x1):
        for z in (z0, z1):
            p.fill(x, 0, z, x, 6, z, ornate)
    p.fill(x0, 6, z0, x1, 6, z1, brick)
    p.crenellate(x0, z0, x1, z1, 7, wall)
    # fronton et porte au sud
    p.clear(-1, 0, z1, 1, 3, z1)
    p.fill(-2, 4, z1 + 1, 2, 4, z1 + 1, ornate)
    p.fill(-2, 0, z1 + 1, -2, 3, z1 + 1, ornate)
    p.fill(2, 0, z1 + 1, 2, 3, z1 + 1, ornate)
    p.set(-2, 5, z1 + 1, "Deco_Halloween_Pumpkin_Scary", SOUTH)
    p.set(2, 5, z1 + 1, "Deco_Halloween_Pumpkin_Scary", SOUTH)
    p.set(0, 7, z1, "Furniture_Ancient_Statue", SOUTH)
    p.set(-3, 0, z1 - 1, p.pick(CANDLES))
    p.set(3, 0, z1 - 1, p.pick(CANDLES))
    p.set(-3, 4, z0 + 1, p.pick(WEBS))
    p.set(3, 4, z0 + 1, p.pick(WEBS))
    # escalier : part du fond du mausolée et descend vers le nord jusqu'à la salle
    stairs_down(p, (-1, 2), (0, -1), depth, brick, wall, width=3)
    # cercueils le long des murs, coffre au fond, os et toiles
    for z in range(cz0 + 1, cz1, 3):
        p.set(cx0 + 1, cy0 + 1, z, r.choice(["Furniture_Ancient_Coffin", "Furniture_Temple_Dark_Coffin", "Furniture_Human_Ruins_Coffin"]), EAST)
        p.set(cx1 - 1, cy0 + 1, z, r.choice(["Furniture_Ancient_Coffin", "Furniture_Temple_Dark_Coffin", "Furniture_Village_Coffin"]), WEST)
    p.set(0, cy0 + 1, cz0 + 1, "Furniture_Temple_Dark_Chest_Large", SOUTH)
    p.set(-1, cy0 + 1, cz0 + 1, p.pick(CANDLES))
    p.set(1, cy0 + 1, cz0 + 1, p.pick(CANDLES))
    if r.random() < 0.5:
        p.set(0, cy0 + 1, cz0 + 5, "Furniture_Temple_Dark_Statue", SOUTH)
    p.scatter(cx0 + 1, cy0 + 1, cz0 + 1, cx1 - 1, cz1 - 1, 9, BONES)
    p.scatter(cx0 + 1, cy0 + 1, cz0 + 1, cx1 - 1, cz1 - 1, 5, CANDLES)
    for _ in range(14):
        x, z = r.randint(cx0, cx1), r.randint(cz0, cz1)
        if p.get(x, cy0 + 4, z) == AIR:
            p.set(x, cy0 + 4, z, p.pick(WEBS))
    # tombes et citrouilles devant l'entrée
    for x in (-4, 4):
        p.set(x, 0, z1 + 3, "Furniture_Village_Tombstone", SOUTH)
        p.set(x, -1, z1 + 4, p.pick(GRAVE_DIRT))
    p.set(-1, 0, z1 + 4, p.pick(PUMPKINS), r.randint(0, 3))
    p.ruin(85, keep_below=0, names={n for n, _ in wall})
    return p


# --- castles ----------------------------------------------------------------------------------

def ladder(p, x, y0, y1, z):
    """Échelle contre le mur est, de y0 à y1 (inclus) ; la case y1 est la trappe du plancher."""
    for y in range(y0, y1 + 1):
        p.set(x, y, z, "Furniture_Human_Ruins_Ladder", WEST)


def tower(p, cx, cz, half, height, wall, flr, roof, ornate, spire=False, webs=True):
    x0, x1, z0, z1 = cx - half, cx + half, cz - half, cz + half
    p.floor(x0, z0, x1, z1, -1, flr, FOUNDATION, depth=4)
    p.hollow(x0, 0, z0, x1, height, z1, wall)
    bottom = 0
    for y in range(4, height, 5):
        p.fill(x0 + 1, y, z0 + 1, x1 - 1, y, z1 - 1, flr)
        ladder(p, x1 - 1, bottom, y, cz)
        bottom = y + 1
        # meurtrières
        for (wx, wz) in ((cx, z0), (cx, z1), (x0, cz), (x1, cz)):
            p.set(wx, y + 2, wz, "Deco_Iron_Bars")
    p.fill(x0, height + 1, z0, x1, height + 1, z1, flr)
    if not spire:
        ladder(p, x1 - 1, bottom, height + 1, cz)  # jusqu'aux créneaux
    if spire:
        p.spire(cx, cz, half + 1, height + 2, roof)
    else:
        p.crenellate(x0, z0, x1, z1, height + 2, wall)
    if webs:
        p.set(x0 + 1, height, z0 + 1, p.pick(WEBS))
        p.set(x1 - 1, height, z1 - 1, p.pick(WEBS))


def curtain_wall(p, x0, z0, x1, z1, height, wall, gate_half=2):
    for x in range(x0, x1 + 1):
        for z in (z0, z1):
            if z == z1 and abs(x) <= gate_half:
                continue
            p.fill(x, 0, z, x, height, z, p.pick(wall))
            p.set(x, -1, z, p.pick(FOUNDATION))
    for z in range(z0, z1 + 1):
        for x in (x0, x1):
            p.fill(x, 0, z, x, height, z, p.pick(wall))
            p.set(x, -1, z, p.pick(FOUNDATION))
    # chemin de ronde
    for x in range(x0 + 1, x1):
        p.set(x, height, z0 + 1, p.pick(wall))
        p.set(x, height, z1 - 1, p.pick(wall))
    for z in range(z0 + 1, z1):
        p.set(x0 + 1, height, z, p.pick(wall))
        p.set(x1 - 1, height, z, p.pick(wall))
    p.crenellate(x0, z0, x1, z1, height + 1, wall)


def gatehouse(p, z, height, wall, ornate, gate_half=2):
    p.fill(-gate_half - 1, 0, z, -gate_half - 1, height + 2, z, ornate)
    p.fill(gate_half + 1, 0, z, gate_half + 1, height + 2, z, ornate)
    p.fill(-gate_half, height - 1, z, gate_half, height + 1, z, p.pick(wall))
    for x in range(-gate_half, gate_half + 1):
        p.set(x, height - 2, z, "Deco_Iron_Bars")  # herse relevée
    p.set(-gate_half - 1, height + 3, z, "Deco_Halloween_Pumpkin_Scary", SOUTH)
    p.set(gate_half + 1, height + 3, z, "Deco_Halloween_Pumpkin_Scary", SOUTH)


def keep(p, x0, z0, x1, z1, height, wall, flr, roof, ornate, levels=2):
    p.floor(x0, z0, x1, z1, -1, flr, FOUNDATION, depth=4)
    p.hollow(x0, 0, z0, x1, height, z1, wall)
    level_h = height // levels
    for lv in range(1, levels):
        y = lv * level_h
        p.fill(x0 + 1, y, z0 + 1, x1 - 1, y, z1 - 1, flr)
        # trémie d'escalier (échelle) dans un coin
        p.fill(x1 - 2, y, z0 + 1, x1 - 1, y, z0 + 2, AIR)
        ladder(p, x1 - 1, y - level_h + 1, y, z0 + 1)
    # fenêtres
    for lv in range(levels):
        y = lv * level_h + 2
        for x in range(x0 + 2, x1 - 1, 3):
            p.set(x, y, z0, "Deco_Iron_Bars")
            p.set(x, y, z1, "Deco_Iron_Bars")
        for z in range(z0 + 2, z1 - 1, 3):
            p.set(x0, y, z, "Deco_Iron_Bars")
            p.set(x1, y, z, "Deco_Iron_Bars")
    # porte
    p.clear(-1, 0, z1, 1, 2, z1)
    p.fill(-2, 3, z1, 2, 3, z1, ornate)
    # toit
    p.fill(x0, height + 1, z0, x1, height + 1, z1, flr)
    p.crenellate(x0, z0, x1, z1, height + 2, wall)
    return level_h


def haunted_castle(seed, material):
    p = Prefab(seed)
    r = p.rng
    wall, flr, roof, ornate = MATERIALS[material]
    s = 16
    p.clear(-s, 0, -s, s, 12, s)
    # cour : terre et pavés
    for x in range(-s, s + 1):
        for z in range(-s, s + 1):
            p.set(x, -1, z, r.choice(["Soil_Grass_Burnt", "Soil_Dirt_Burnt", "Rock_Stone_Cobble_Mossy", "Soil_Gravel"]))
    for z in range(-4, s + 1):
        for x in (-1, 0, 1):
            p.set(x, -1, z, p.pick(flr))
    curtain_wall(p, -s, -s, s, s, 8, wall)
    gatehouse(p, s, 8, wall, ornate)
    for cx in (-s, s):
        for cz in (-s, s):
            tower(p, cx, cz, 3, 14, wall, flr, roof, ornate, spire=r.random() < 0.5)
    # donjon
    level_h = keep(p, -6, -12, 6, -2, 12, wall, flr, roof, ornate, levels=2)
    # salle du bas : longue table, chandelier, bannières
    p.fill(-1, 0, -10, 1, 0, -5, "Furniture_Human_Ruins_Table")
    for z in range(-10, -4):
        p.set(-2, 0, z, "Furniture_Human_Ruins_Chair", EAST)
        p.set(2, 0, z, "Furniture_Human_Ruins_Chair", WEST)
    for z in (-10, -7, -5):
        p.set(0, 1, z, p.pick(CANDLES))
    p.set(0, level_h - 1, -7, "Furniture_Tavern_Chandelier")
    for x in (-4, 4):
        p.set(x, 3, -11, "Furniture_Human_Ruins_Banner", SOUTH)
    p.set(-4, 0, -11, "Furniture_Human_Ruins_Bookshelf", SOUTH)
    p.set(4, 0, -11, "Furniture_Human_Ruins_Bookshelf", SOUTH)
    # étage : chambre abandonnée
    y = level_h + 1
    p.set(-4, y, -10, "Furniture_Ancient_Bed", EAST)
    p.set(-4, y, -6, "Furniture_Human_Ruins_Wardrobe", EAST)
    p.set(3, y, -10, "Furniture_Ancient_Chest_Large", SOUTH)
    p.set(0, y, -9, "Furniture_Ancient_Painting", SOUTH)
    p.scatter(-5, y, -11, 5, -3, 6, CANDLES)
    # toiles d'araignée partout sous les plafonds
    for _ in range(40):
        x, z = r.randint(-5, 5), r.randint(-11, -3)
        for yy in (level_h - 1, 2 * level_h - 1):
            if p.get(x, yy, z) == AIR and r.random() < 0.5:
                p.set(x, yy, z, p.pick(WEBS))
    # cour : puits, tombes, arbres morts, citrouilles
    p.hollow(8, 0, 6, 10, 1, 8, wall)
    p.fill(9, -4, 7, 9, 1, 7, AIR)
    p.set(9, -5, 7, "Soil_Mud")
    for y in range(-4, -1):
        for (wx, wz) in ((8, 7), (10, 7), (9, 6), (9, 8)):
            p.set(wx, y, wz, p.pick(wall))
    p.fill(8, 3, 6, 10, 3, 8, "Wood_Deadwood_Roof_Flat")
    p.set(8, 2, 6, "Wood_Deadwood_Beam")
    p.set(10, 2, 8, "Wood_Deadwood_Beam")
    for x in range(-13, -7, 2):
        for z in (6, 10):
            p.set(x, 0, z, "Furniture_Village_Tombstone", SOUTH)
    for tx, tz in ((-10, 13), (12, 12), (-12, 2)):
        t = dead_tree(r.randint(0, 1 << 30), webs=True)
        for (bx, by, bz), (name, rot) in t.blocks.items():
            if by >= 0 and p.get(tx + bx, by, tz + bz) in (None, AIR):
                p.set(tx + bx, by, tz + bz, name, rot)
    p.scatter(-s + 2, 0, -s + 2, s - 2, s - 2, 12, PUMPKINS)
    p.scatter(-s + 2, 0, -1, s - 2, s - 2, 10, DEAD_PLANTS)
    p.scatter(-s + 2, 0, -1, s - 2, s - 2, 8, BONES)
    p.ruin(78, keep_below=1, names={n for n, _ in wall})
    return p


def dracula_castle(seed):
    """Château du comte vampire : basalte et ardoise, flèches, salle du trône, crypte aux cercueils."""
    p = Prefab(seed)
    r = p.rng
    wall, flr, roof, ornate = MATERIALS["basalt"]
    s = 20
    p.clear(-s, 0, -s, s, 16, s)
    for x in range(-s, s + 1):
        for z in range(-s, s + 1):
            p.set(x, -1, z, r.choice(["Soil_Grass_Burnt", "Soil_Dirt_Burnt", "Rock_Basalt_Cobble", "Soil_Grass_Burnt"]))
    # allée de pavés bordée de roses de sang
    for z in range(-6, s + 1):
        for x in (-1, 0, 1):
            p.set(x, -1, z, p.pick(flr))
        for x in (-3, 3):
            p.set(x, -1, z, "Soil_Dirt")
            if z % 2 == 0:
                p.set(x, 0, z, r.choice(["Plant_Crop_Health1", "Plant_Petals_Blood", "Plant_Crop_Health1"]))
    curtain_wall(p, -s, -s, s, s, 10, wall)
    gatehouse(p, s, 10, wall, ornate)
    slate_roof = "Rock_Slate_Brick"
    for cx in (-s, s):
        for cz in (-s, s):
            tower(p, cx, cz, 3, 18, wall, flr, slate_roof, ornate, spire=True)
    # tours de flanc
    for cx, cz in ((-s, 0), (s, 0)):
        tower(p, cx, cz, 2, 14, wall, flr, slate_roof, ornate, spire=True)
    # donjon
    x0, x1, z0, z1 = -9, 9, -17, -5
    keep(p, x0, z0, x1, z1, 16, wall, flr, slate_roof, ornate, levels=2)
    p.spire(x0 + 2, z0 + 2, 2, 19, slate_roof)
    p.spire(x1 - 2, z0 + 2, 2, 19, slate_roof)
    p.fill(0, 18, z0 + 4, 0, 24, z0 + 4, ornate)
    p.spire(0, z0 + 4, 3, 25, slate_roof)
    # salle du trône : tapis rouge, trône, piliers, chandeliers
    for z in range(z0 + 2, z1 + 1):
        for x in (-1, 0, 1):
            p.set(x, -1, z, "Cloth_Block_Wool_Red")
    for z in range(z0 + 3, z1, 3):
        for x in (-5, 5):
            p.fill(x, 0, z, x, 7, z, "Rock_Basalt_Brick_Pillar_Middle")
            p.set(x - 1 if x > 0 else x + 1, 0, z, p.pick(CANDLES))
    p.fill(-2, 0, z0 + 1, 2, 0, z0 + 2, "Rock_Basalt_Brick_Smooth")
    p.set(0, 1, z0 + 1, "Furniture_Royal_Magic_Carpet")
    p.fill(-1, 1, z0 + 1, 1, 1, z0 + 1, "Cloth_Block_Wool_Red")
    p.fill(-1, 2, z0 + 1, 1, 3, z0 + 1, "Rock_Basalt_Brick_Ornate")
    p.set(0, 1, z0 + 2, "Furniture_Temple_Dark_Coffin", SOUTH)
    for x in (-3, 3):
        p.set(x, 1, z0 + 1, "Furniture_Temple_Dark_Statue", SOUTH)
        p.set(x, 4, z0 + 1, "Furniture_Outlander_Banner", SOUTH)
    for z in (z0 + 4, z0 + 9):
        p.set(0, 7, z, "Furniture_Feran_Chandelier")
    for x in (-7, 7):
        for z in range(z0 + 2, z1 - 1, 4):
            p.set(x, 2, z, "Cloth_Block_Wool_Red")
            p.set(x, 3, z, "Cloth_Block_Wool_Red")
    # étage : bibliothèque et chambre du comte
    y = 9
    for x in range(x0 + 1, -2):
        p.set(x, y, z0 + 1, "Furniture_Human_Ruins_Bookshelf", SOUTH)
        p.set(x, y + 1, z0 + 1, "Furniture_Human_Ruins_Bookshelf", SOUTH)
    p.set(4, y, z0 + 3, "Furniture_Temple_Dark_Coffin", WEST)
    p.set(6, y, z0 + 3, "Furniture_Temple_Dark_Chest_Large", WEST)
    p.set(4, y, z1 - 2, "Alchemy_Cauldron_Big")
    p.scatter(x0 + 1, y, z0 + 1, x1 - 1, z1 - 1, 8, CANDLES)
    for _ in range(30):
        x, z = r.randint(x0 + 1, x1 - 1), r.randint(z0 + 1, z1 - 1)
        if p.get(x, 15, z) == AIR:
            p.set(x, 15, z, p.pick(WEBS))
    # crypte sous le donjon : un escalier part de la salle du trône et plonge le long du mur sud
    # (le plafond de la crypte est le dallage de la salle du trône)
    depth = 5
    cy0 = -depth - 1
    cx0, cx1, cz0, cz1 = x0 + 1, x1 - 1, z0 + 1, z1 - 1
    for x in range(cx0 - 1, cx1 + 2):
        for z in range(cz0 - 1, cz1 + 2):
            p.set(x, cy0, z, p.pick(wall))
            p.set(x, cy0 - 1, z, p.pick(FOUNDATION))
    p.floor(cx0, cz0, cx1, cz1, cy0, flr)
    p.clear(cx0, cy0 + 1, cz0, cx1, -2, cz1)
    stairs_down(p, (cx1 - 1, cz1), (0, -1), depth, "Rock_Basalt_Brick", wall, width=2)
    for x in range(cx0 + 1, cx1 - 3, 3):
        p.set(x, cy0 + 1, cz0 + 1, r.choice(["Furniture_Temple_Dark_Coffin", "Furniture_Ancient_Coffin"]), SOUTH)
        p.set(x, cy0 + 1, cz1 - 1, r.choice(["Furniture_Temple_Dark_Coffin", "Furniture_Ancient_Coffin"]), NORTH)
    p.set(0, cy0 + 1, (cz0 + cz1) // 2, "Furniture_Ancient_Chest_Large_Treasure", SOUTH)
    for px in (-4, 3):
        p.fill(px, cy0 + 1, (cz0 + cz1) // 2, px, -2, (cz0 + cz1) // 2, "Rock_Basalt_Brick_Pillar_Middle")
    p.scatter(cx0 + 1, cy0 + 1, cz0 + 1, cx1 - 3, cz1 - 1, 10, CANDLES)
    p.scatter(cx0 + 1, cy0 + 1, cz0 + 1, cx1 - 3, cz1 - 1, 8, BONES)
    # cour : jardin de roses de sang, cercueils dressés, gibets
    for x in range(-16, -6):
        for z in range(6, 16):
            if (x + z) % 2 == 0:
                p.set(x, -1, z, "Soil_Dirt")
                p.set(x, 0, z, r.choice(["Plant_Crop_Health1", "Plant_Crop_Health2", "Plant_Crop_Health3", "Plant_Petals_Blood"]))
    for x in range(8, 17, 3):
        p.set(x, 0, 10, "Furniture_Village_Coffin", SOUTH)
        p.set(x, 0, 14, "Furniture_Village_Tombstone", SOUTH)
    for tx, tz in ((12, 3), (-12, 2)):
        t = hanging_tree(r.randint(0, 1 << 30))
        for (bx, by, bz), (name, rot) in t.blocks.items():
            if by >= 0 and p.get(tx + bx, by, tz + bz) in (None, AIR):
                p.set(tx + bx, by, tz + bz, name, rot)
    p.scatter(-s + 2, 0, -3, s - 2, s - 2, 8, PUMPKINS)
    p.scatter(-s + 2, 0, -3, s - 2, s - 2, 8, BONES)
    p.ruin(92, keep_below=1, names={n for n, _ in wall})
    return p


# --- small decorations ------------------------------------------------------------------------

def bone_pile(seed):
    p = Prefab(seed)
    r = p.rng
    for _ in range(r.randint(3, 6)):
        x, z = r.randint(-2, 2), r.randint(-2, 2)
        p.set(x, 0, z, p.pick(BONES), r.randint(0, 3))
    if r.random() < 0.5:
        p.set(0, 0, 0, "Deco_Bone_Spike_Large" if r.random() < 0.5 else "Deco_Bone_Spike")
    return p


def lone_grave(seed):
    p = Prefab(seed)
    r = p.rng
    p.set(0, 0, 0, r.choice(["Furniture_Village_Tombstone", "Rock_Stone_Brick_Ornate", "Rock_Stone_Cobble_Mossy"]), r.randint(0, 3))
    p.set(0, -1, 1, p.pick(GRAVE_DIRT))
    p.set(0, -1, 2, p.pick(GRAVE_DIRT))
    if r.random() < 0.5:
        p.set(1, 0, 0, p.pick(CANDLES))
    if r.random() < 0.4:
        p.set(-1, 0, 1, p.pick(PUMPKINS), r.randint(0, 3))
    return p


def spider_nest(seed):
    p = Prefab(seed)
    r = p.rng
    for dx in range(-3, 4):
        for dz in range(-3, 4):
            if dx * dx + dz * dz <= 10 and r.random() < 0.7:
                p.set(dx, 0, dz, "Deco_SpiderWeb_Flat")
    p.set(0, 0, 0, "Deco_Spider_Cocoon")
    for _ in range(3):
        p.set(r.randint(-2, 2), 0, r.randint(-2, 2), r.choice(["Deco_Spider_Cocoon", "Cocoon_Spider_Cave", "Deco_Bone_Pile"]))
    return p


def pumpkin_patch(seed):
    p = Prefab(seed)
    r = p.rng
    for _ in range(r.randint(3, 7)):
        x, z = r.randint(-2, 2), r.randint(-2, 2)
        p.set(x, 0, z, r.choice(["Plant_Crop_Pumpkin_StageFinal", "Plant_Crop_Pumpkin_StageFinal", "Deco_Halloween_Pumpkin_Scary"]), r.randint(0, 3))
    return p


# --- main -------------------------------------------------------------------------------------

def main():
    jobs = []
    for i in range(6):
        jobs.append((f"Trees/Dead_Tree_{i + 1}", dead_tree(1000 + i, webs=i % 3 == 0)))
    for i in range(2):
        jobs.append((f"Trees/Hanging_Tree_{i + 1}", hanging_tree(1100 + i)))
    for i in range(3):
        jobs.append((f"PumpkinFields/Pumpkin_Field_{i + 1}", pumpkin_field(2000 + i, *[(21, 17), (25, 15), (17, 21)][i])))
    for t, theme in enumerate(("haunted", "spiders", "undead")):
        for i in range(2):
            jobs.append((f"Cemeteries/{theme.capitalize()}/Cemetery_{theme.capitalize()}_{i + 1}", cemetery(3000 + t * 100 + i, theme)))
    for i, material in enumerate(("stone", "slate", "shale")):
        jobs.append((f"Crypts/Crypt_{material.capitalize()}", crypt(4000 + i, material)))
    jobs.append(("HauntedCastles/Haunted_Castle_Stone", haunted_castle(5000, "stone")))
    jobs.append(("HauntedCastles/Haunted_Castle_Slate", haunted_castle(5001, "slate")))
    jobs.append(("DraculaCastle/Dracula_Castle", dracula_castle(6000)))
    for i in range(3):
        jobs.append((f"Decor/BonePiles/Bone_Pile_{i + 1}", bone_pile(7000 + i)))
        jobs.append((f"Decor/Graves/Lone_Grave_{i + 1}", lone_grave(7100 + i)))
        jobs.append((f"Decor/SpiderNests/Spider_Nest_{i + 1}", spider_nest(7200 + i)))
        jobs.append((f"Decor/PumpkinPatches/Pumpkin_Patch_{i + 1}", pumpkin_patch(7300 + i)))

    if OUT.exists():
        for old in OUT.rglob("*.prefab.json"):
            old.unlink()
    total = 0
    for name, prefab in jobs:
        count = prefab.write(OUT / f"{name}.prefab.json")
        total += count
        print(f"{name}: {count} blocs")
    print(f"{len(jobs)} prefabs, {total} blocs")


if __name__ == "__main__":
    main()
