#!/usr/bin/env python3
"""Génère les prefabs du Fragment halloween (format .prefab.json version 8).

Les structures sont décrites procéduralement (murs, tours, toits, mobilier) puis écrites dans
src/main/resources/Server/Prefabs/Nakasar/Halloween/<Catégorie>/<Nom>.prefab.json. Le générateur est
déterministe : relancer le script reproduit exactement les mêmes fichiers.

    python3 mods/nakasar-vampires/tools/generate_prefabs.py

Repère des prefabs : x vers l'est, z vers le sud, y vers le haut. Le worldgen pose le prefab sur
le premier bloc d'air au-dessus du sol : y = 0 est donc la première couche d'air, y = -1 le sol
(remplacé par le dallage de la structure) et y < -1 les fondations et les souterrains.

Un nom de bloc peut être préfixé par une probabilité (« 70%Rock_Stone_Brick ») : le serveur ne
pose alors le bloc qu'avec cette probabilité, à chaque génération. C'est ce qui rend chaque ruine
différente.

Ids de blocs : tous viennent de tools/vanilla-block-ids-0.7.2.txt (vérifié par validateAssets). Un
état de bloc s'écrit « *<Bloc>_State_Definitions_<État> » (clé générée par StateData du serveur),
par exemple une citrouille mûre : *Plant_Crop_Pumpkin_Block_State_Definitions_StageFinal.
"""

import json
import math
import random
import re
from pathlib import Path

import generate_lore as lore

PACK = Path(__file__).resolve().parent.parent / "src" / "main" / "resources"
OUT = PACK / "Server" / "Prefabs" / "Nakasar" / "Halloween"

AIR = "Empty"

# Rotations de bloc : index RotationTuple = tangage × 4 + lacet.
# Lacet seul : un meuble regarde le sud (+Z) en rotation 0, puis l'est, le nord et l'ouest (lu dans
# les hitboxes du jeu : dossier de chaise et tableau collés au nord en rotation 0, et dans les
# maisons du village vanilla). Portes et fenêtres : 0 dans un mur le long de x, 1 le long de z.
# Une souche de branche (VariantRotation NESW) s'accroche au nord, à l'ouest, au sud puis à l'est.
SOUTH, EAST, NORTH, WEST = 0, 1, 2, 3
# Tuyaux (troncs, branches longues, VariantRotation Pipe) : 0 debout, 4 couché nord-sud, 5 couché est-ouest.
UPRIGHT, ALONG_Z, ALONG_X = 0, 4, 5
# Blocs en ligne (clôtures, murets, grilles) : orientés à l'écriture par Prefab.orient_lines.
LINE_BLOCK = re.compile(r"(_Fence|_Brick_Wall|_Cobble_Wall|Iron_Bars|Iron_Railing)$")


# Meubles de plusieurs blocs : cases occupées en rotation 0 (dx, dy, dz) depuis le bloc posé, lues
# dans Server/Item/Block/Hitboxes du jeu (0.7.2). Le prefab liste chaque case en plus du bloc posé,
# avec son décalage (« filler »), comme les prefabs vanilla ; Prefab.write les ajoute et refuse deux
# meubles qui se chevauchent ou un meuble qui rentre dans un mur.
def _box(x0, x1, y0, y1, z0, z1):
    return [(x, y, z) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1) for z in range(z0, z1 + 1)]


HITBOXES = {
    "Table": _box(0, 1, 0, 0, 0, 1),
    "Chest_Large": _box(-1, 0, 0, 0, 0, 0),
    "Wardrobe": _box(-1, 0, 0, 1, 0, 0),
    "Desk": _box(-1, 0, 0, 0, 0, 0),
    "Bench": _box(-1, 0, 0, 0, 0, 0),
    "Bench_Backrest": _box(-1, 0, 0, 0, 0, 0),
    "Coffin": _box(0, 1, 0, 0, 0, 0),
    "Bed_Large": _box(0, 1, 0, 1, 0, 2),
    "Bed_Low": _box(0, 1, 0, 0, 0, 2),
    "Bed_Royal": _box(0, 2, 0, 2, 0, 3),
    "Chandelier": _box(-1, 1, -1, 0, -1, 1),
    "Tall": _box(0, 0, 0, 1, 0, 0),
    "Taller": _box(0, 0, 0, 2, 0, 0),
    "Statue_Large": _box(-1, 1, 0, 2, 0, 0),
    "Workstation": _box(-1, 0, 0, 1, 0, 0),
    "Workstation_Low": _box(-1, 0, 0, 0, 0, 0),
    "Painting_2x2": _box(-1, 0, 0, 1, 0, 0),
    "Painting_3x2": _box(-1, 1, 0, 1, 0, 0),
    "Carpet_Large": _box(0, 1, 0, 0, 0, 1),
    "Door_Medium": _box(0, 2, 0, 2, 0, 0),
    "Breach_Rift": _box(-1, 1, 0, 3, 0, 0),  # Nakasar_Breach_Rift (generate_breach.py) : l'ouverture de l'arche
}
FURNITURE = {
    **{f"Furniture_{s}_Table": "Table" for s in ("Ancient", "Crude", "Village", "Human_Ruins", "Temple_Dark", "Royal_Magic", "Tavern", "Lumberjack", "Feran")},
    **{f"Furniture_{s}_Chest_Large": "Chest_Large" for s in ("Ancient", "Crude", "Village", "Human_Ruins", "Temple_Dark", "Royal_Magic", "Tavern", "Lumberjack", "Feran")},
    **{f"Furniture_{s}_Wardrobe": "Wardrobe" for s in ("Ancient", "Crude", "Village", "Human_Ruins", "Temple_Dark", "Royal_Magic", "Tavern", "Lumberjack", "Feran")},
    **{f"Furniture_{s}_Bed": "Bed_Large" for s in ("Ancient", "Village", "Human_Ruins", "Tavern", "Lumberjack", "Feran")},
    **{f"Furniture_{s}_Coffin": "Coffin" for s in ("Ancient", "Village", "Human_Ruins", "Temple_Dark")},
    "Furniture_Temple_Dark_Bed": "Bed_Low",
    "Furniture_Royal_Magic_Bed": "Bed_Royal",
    "Furniture_Human_Ruins_Desk": "Desk", "Furniture_Village_Counter": "Desk",
    "Furniture_Ancient_Bench": "Bench", "Furniture_Castle_Bench": "Bench", "Furniture_Tavern_Bench": "Bench",
    "Furniture_Royal_Magic_Couch": "Bench", "Furniture_Feran_Bench": "Bench",
    "Furniture_Village_Bench": "Bench_Backrest", "Furniture_Human_Ruins_Bench": "Bench_Backrest",
    "Furniture_Feran_Chandelier": "Chandelier", "Furniture_Tavern_Chandelier": "Chandelier",
    "Furniture_Temple_Dark_Statue": "Tall", "Furniture_Village_Tombstone": "Tall",
    "Furniture_Temple_Dark_Candle": "Tall", "Furniture_Human_Ruins_Candle": "Tall",
    "Furniture_Dungeon_Earth_Brazier": "Tall", "Furniture_Village_Painting_1x2": "Tall",
    "Furniture_Human_Ruins_Statue_Broken": "Taller", "Furniture_Village_Statue": "Taller",
    "Furniture_Temple_Dark_Statue_Gaia": "Taller", "Deco_Scarecrow": "Taller",
    "Furniture_Ancient_Statue": "Statue_Large",
    "Furniture_Village_Painting_2x2": "Painting_2x2", "Furniture_Village_Painting_3x2": "Painting_3x2",
    "Furniture_Royal_Magic_Carpet": "Carpet_Large",
    "Furniture_Ancient_Door_Medium": "Door_Medium", "Furniture_Temple_Dark_Door_Medium": "Door_Medium",
    "Furniture_Human_Ruins_Door_Medium": "Door_Medium",
    **{f"Furniture_{s}_Door": "Tall" for s in ("Ancient", "Crude", "Village", "Human_Ruins", "Temple_Dark", "Tavern", "Lumberjack")},
    **{b: "Workstation" for b in ("Bench_Alchemy", "Bench_Arcane", "Bench_Cooking", "Bench_Furnace", "Bench_Weapon",
                                  "Bench_Armory", "Bench_Armour", "Bench_Loom", "Bench_Tannery", "Bench_Farming")},
    **{b: "Workstation_Low" for b in ("Bench_WorkBench", "Bench_Lumbermill", "Bench_Trough")},
    "Halloween_Wagon": "Table",
    "Tinkering_Target_Dummy": "Tall",
    "Nakasar_Breach_Rift": "Breach_Rift",
    "Nakasar_Contract_Board": "Tall",  # tableau de contrats de la brèche (generate_lore.py)
}


def footprint(name, rot):
    """Cases occupées par un meuble posé en `name` avec le lacet `rot` (rotation du jeu : 90° envoie
    (x, z) sur (z, -x))."""
    base = name.split("%")[-1]
    if base.startswith("*"):
        base = base[1:].split("_State_Definitions_")[0]
    cells = HITBOXES.get(FURNITURE.get(base), [(0, 0, 0)])
    out = []
    for x, y, z in cells:
        for _ in range(rot % 4):
            x, z = z, -x
        out.append((x, y, z))
    return out


def pack_filler(dx, dy, dz):
    return (dx & 31) | ((dz & 31) << 5) | ((dy & 31) << 10)


def pumpkin_crop(stage):
    return f"*Plant_Crop_Pumpkin_Block_State_Definitions_{stage}"


class Prefab:
    """Grille de blocs creuse ; la dernière écriture d'une case l'emporte."""

    def __init__(self, seed):
        self.blocks = {}
        self.components = {}  # (x, y, z) -> composants du bloc (coffre et sa liste de butin...)
        self.claims = {}      # case secondaire d'un meuble -> case du meuble
        self.rng = random.Random(seed)

    # --- primitives -------------------------------------------------------------------------

    def set(self, x, y, z, name, rot=0):
        pos = (x, y, z)
        self.components.pop(pos, None)
        old = self.blocks.get(pos)
        if old and old[0] != AIR:
            for dx, dy, dz in footprint(*old):
                if self.claims.get((x + dx, y + dy, z + dz)) == pos:
                    del self.claims[(x + dx, y + dy, z + dz)]
        if name is None:
            self.blocks.pop(pos, None)
            return
        self.blocks[pos] = (name, rot)
        if name != AIR:
            for dx, dy, dz in footprint(name, rot):
                if (dx, dy, dz) != (0, 0, 0):
                    self.claims[(x + dx, y + dy, z + dz)] = pos

    def reserved(self):
        """Cases déjà prises par les parties secondaires des meubles posés."""
        return set(self.claims)

    def fits(self, x, y, z, name, rot=0, reserved=None):
        """Le meuble tient-il là : toutes ses cases libres (air ou rien) et posées sur du plein."""
        cells = footprint(name, rot)
        taken = self.reserved() if reserved is None else reserved
        if not all(self.free(x + dx, y + dy, z + dz) and (x + dx, y + dy, z + dz) not in taken for dx, dy, dz in cells):
            return False
        return all(not self.free(x + dx, y - 1, z + dz) for dx, dy, dz in cells if dy == 0)

    def chest(self, x, y, z, name, rot, droplist):
        """Coffre rempli à la pose par le serveur avec la liste de butin `droplist` (Server/Drops)."""
        self.set(x, y, z, name, rot)
        capacity = 36 if name.endswith("_Large") else 18
        self.components[(x, y, z)] = {"Components": {"ItemContainerBlock": {"Droplist": droplist, "Capacity": capacity}}}

    def get(self, x, y, z):
        b = self.blocks.get((x, y, z))
        return b[0] if b else None

    def free(self, x, y, z):
        """Case vide : ni bloc, ni partie d'un meuble de plusieurs blocs."""
        return self.get(x, y, z) in (None, AIR) and (x, y, z) not in self.claims

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
        """Flèche pyramidale à degrés ; chaque anneau monte de `step` blocs.

        La base est une dalle pleine et le haut de chaque anneau déborde d'un cran vers l'intérieur :
        l'anneau suivant repose dessus (sinon les anneaux ne se touchent que par les arêtes et la
        flèche flotte en jeu).
        """
        for x in range(cx - half, cx + half + 1):
            for z in range(cz - half, cz + half + 1):
                self.set(x, y, z, self.pick(palette))
        y += 1
        for r in range(half, -1, -1):
            layers = step if r > 0 else 3
            for dy in range(layers):
                for x in range(cx - r, cx + r + 1):
                    for z in range(cz - r, cz + r + 1):
                        ring = max(abs(x - cx), abs(z - cz))
                        if r == 0 or ring == r or (dy == layers - 1 and ring == r - 1):
                            self.set(x, y, z, self.pick(palette))
                y += 1
        return y

    def gable(self, x0, z0, x1, z1, y, full, half, gable_wall=None):
        """Toit à deux pans en demi-dalles (faîte nord-sud) posé sur un rectangle à la hauteur y.

        Chaque pas vers le faîte monte d'une demi-dalle : pas d'orientation de bloc à deviner. Les
        pignons (murs nord et sud sous le toit) sont remplis avec `gable_wall`.
        """
        width = x1 - x0 + 1
        for i in range((width + 1) // 2):
            h2 = i + 1  # hauteur en demi-blocs au-dessus de y
            for x in (x0 + i, x1 - i):
                for z in range(z0 - 1, z1 + 2):
                    for k in range(h2 // 2):
                        if k == h2 // 2 - 1 or z in (z0 - 1, z1 + 1) or x in (x0, x1):
                            self.set(x, y + k, z, self.pick(full))
                    if h2 % 2:
                        self.set(x, y + h2 // 2, z, self.pick(half))
                if gable_wall:
                    for k in range((h2 + 1) // 2):
                        for z in (z0, z1):
                            if self.free(x, y + k, z):
                                self.set(x, y + k, z, self.pick(gable_wall))

    def steep_roof(self, x0, z0, x1, z1, y, full, half, ridge="x", gable_wall=None):
        """Toit gothique à deux pans à 45° : un bloc de montée par rangée, adouci d'une demi-dalle.

        `ridge` = axe du faîte ("x" : pignons à l'est et à l'ouest, "z" : pignons au nord et au sud).
        Chaque rangée fait deux blocs d'épaisseur pour toucher la suivante par une face. Les pignons
        sont remplis avec `gable_wall`. Renvoie la hauteur du faîte.
        """
        if ridge == "x":
            lo, hi, a0, a1 = z0, z1, x0, x1
            at = lambda u, v: (v, u)  # u le long de la pente (z), v le long du faîte (x)
        else:
            lo, hi, a0, a1 = x0, x1, z0, z1
            at = lambda u, v: (u, v)
        rows = (hi - lo) // 2 + 1
        top = y
        for i in range(rows):
            h = y + i
            top = h
            for u in {lo + i, hi - i}:
                for v in range(a0, a1 + 1):
                    x, z = at(u, v)
                    for k in range(max(y, h - 1), h + 1):
                        self.set(x, k, z, self.pick(full))
                    self.set(x, h + 1, z, half)
            if gable_wall:
                for v in (a0, a1):
                    for u in range(lo + i + 1, hi - i):
                        x, z = at(u, v)
                        self.set(x, h, z, self.pick(gable_wall))
        return top + 1

    def ruin(self, chance, keep_below=0, names=None):
        """Effrite la structure : garde environ `chance` % des blocs visés, surtout en bas.

        Les blocs retirés le sont à la génération du prefab (pas de bloc probabiliste, tiré à chaque
        pose, qui laissait des pans de mur suspendus dans le vide). Plus un bloc est haut, plus il a
        de chances de tomber ; puis tout ce qui ne rejoint plus le sol de face en face est retiré
        aussi. Les blocs sous `keep_below` (sol, fondations) restent pleins.
        """
        targets = [pos for pos, (name, _) in self.blocks.items()
                   if name != AIR and pos[1] >= keep_below and (names is None or name in names)]
        if not targets:
            return
        top = max(pos[1] for pos in targets)
        for pos in targets:
            h = (pos[1] - keep_below) / max(1, top - keep_below)
            if self.rng.random() < (100 - chance) / 100 * (0.3 + 1.4 * h):
                self.set(*pos, AIR)
        for pos in floating_blocks(self):
            self.set(*pos, None)

    def scatter(self, x0, y, z0, x1, z1, count, palette, require_air=True, rot=None):
        """Pose `count` décorations sur des cases libres d'une surface."""
        placed = 0
        taken = self.reserved()
        for _ in range(count * 12):
            if placed >= count:
                break
            x = self.rng.randint(min(x0, x1), max(x0, x1))
            z = self.rng.randint(min(z0, z1), max(z0, z1))
            name = self.pick(palette)
            r = self.rng.randint(0, 3) if rot is None else rot
            if require_air and not self.fits(x, y, z, name, r, taken):
                continue
            if self.free(x, y - 1, z):
                continue
            self.set(x, y, z, name, r)
            taken.update((x + dx, y + dy, z + dz) for dx, dy, dz in footprint(name, r))
            placed += 1

    def paste(self, other, dx, dy, dz, min_y=None, only_free=True):
        """Copie un autre prefab (un arbre dans un cimetière...) décalé de (dx, dy, dz)."""
        taken = self.reserved()
        for (bx, by, bz), (name, rot) in other.blocks.items():
            if min_y is not None and by < min_y:
                continue
            if only_free and (not self.free(bx + dx, by + dy, bz + dz) or (bx + dx, by + dy, bz + dz) in taken):
                continue
            self.set(bx + dx, by + dy, bz + dz, name, rot)
            if (bx, by, bz) in other.components:
                self.components[(bx + dx, by + dy, bz + dz)] = other.components[(bx, by, bz)]

    # --- export -----------------------------------------------------------------------------

    def orient_lines(self):
        """Tourne clôtures, murets et grilles dans le sens de leur ligne.

        Ces blocs (VariantRotation Wall / NESW) se dessinent le long de l'axe x en rotation 0 et
        le long de z en rotation 1 ; en jeu ils ne se raccordent pas seuls dans un prefab. Le sens
        se lit sur les voisins de la même famille, à défaut sur les blocs pleins qui les tiennent.
        """
        def line(name):
            return LINE_BLOCK.search(name.split("%")[-1]) is not None

        for (x, y, z), (name, rot) in list(self.blocks.items()):
            if rot or not line(name):
                continue
            def count(pred, axis):
                ds = ((1, 0), (-1, 0)) if axis == "x" else ((0, 1), (0, -1))
                return sum(1 for dx, dz in ds if pred(self.blocks.get((x + dx, y, z + dz), (AIR, 0))[0]))
            along_x, along_z = count(line, "x"), count(line, "z")
            if along_x == along_z:
                solid = lambda n: n != AIR and not n.split("%")[-1].startswith(("Plant_", "Deco_Halloween"))
                along_x, along_z = count(solid, "x"), count(solid, "z")
            if along_z > along_x:
                self.blocks[(x, y, z)] = (name, 1)

    def fillers(self):
        """Cases secondaires des meubles de plusieurs blocs : {(x, y, z): (nom, rotation, décalage)}.

        Échoue si une case tombe sur un bloc déjà posé (mur, autre meuble) : c'est ce qui donnait des
        tables imbriquées en jeu.
        """
        out, clashes = {}, []
        for (x, y, z), (name, rot) in self.blocks.items():
            if name == AIR:
                continue
            for dx, dy, dz in footprint(name, rot):
                if (dx, dy, dz) == (0, 0, 0):
                    continue
                cell = (x + dx, y + dy, z + dz)
                if self.get(*cell) not in (None, AIR) or cell in out:
                    clashes.append(f"{name}@{(x, y, z)} -> {cell} ({self.get(*cell) or out[cell][0]})")
                out[cell] = (name, rot, pack_filler(dx, dy, dz))
        if clashes:
            raise ValueError(f"meubles qui se chevauchent : {clashes[:6]}")
        return out

    def write(self, path):
        self.orient_lines()
        try:
            fillers = self.fillers()
        except ValueError as e:
            raise ValueError(f"{path.name} : {e}") from None
        cells = dict(self.blocks)
        for cell, (name, rot, _) in fillers.items():
            cells[cell] = (name, rot)
        blocks = []
        for (x, y, z), (name, rot) in sorted(cells.items(), key=lambda kv: (kv[0][1], kv[0][2], kv[0][0])):
            entry = {"x": x, "y": y, "z": z, "name": name}
            if rot:
                entry["rotation"] = rot
            if (x, y, z) in fillers:
                entry["filler"] = fillers[(x, y, z)][2]
            if (x, y, z) in self.components:
                entry["components"] = self.components[(x, y, z)]
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

# Listes de butin des coffres (src/main/resources/Server/Drops/Nakasar/Halloween, tools/generate_loot.py).
LOOT_FARM = "Nakasar_Loot_Farm"
LOOT_FARM_BURNT = "Nakasar_Loot_Farm_Burnt"
LOOT_VILLAGE = "Nakasar_Loot_Village_House"
LOOT_VILLAGE_RICH = "Nakasar_Loot_Village_Rich"
LOOT_BARRACKS = "Nakasar_Loot_Guard_Barracks"
LOOT_ARMORY = "Nakasar_Loot_Guard_Armory"
LOOT_CAPTAIN = "Nakasar_Loot_Guard_Captain"
LOOT_CRYPT = "Nakasar_Loot_Crypt"
LOOT_CASTLE = "Nakasar_Loot_Castle_Ruins"
LOOT_MANOR_TREASURE = "Nakasar_Loot_Manor_Treasure"
LOOT_MANOR_ALCHEMY = "Nakasar_Loot_Manor_Alchemy"
LOOT_MANOR_LIBRARY = "Nakasar_Loot_Manor_Library"
LOOT_MANOR_KITCHEN = "Nakasar_Loot_Manor_Kitchen"
LOOT_MANOR_BEDROOM = "Nakasar_Loot_Manor_Bedroom"
LOOT_MANOR_WORKSHOP = "Nakasar_Loot_Manor_Workshop"
LOOT_HUNTER_CAMP = "Nakasar_Loot_Hunter_Camp"
LOOT_HUNTER_ARMORY = "Nakasar_Loot_Hunter_Armory"

# Blocs d'apparition invisibles du mod (un marqueur par bloc).
SPAWN_VILLAGER = "Nakasar_Spawner_Zombie_Villager"
SPAWN_FARMER = "Nakasar_Spawner_Zombie_Farmer"
SPAWN_ABOMINATION = "Nakasar_Spawner_Zombie_Abomination"
SPAWN_REBEL = "Nakasar_Spawner_Zombie_Rebel"
SPAWN_GUARD = "Nakasar_Spawner_Skeleton_Guard"
SPAWN_CAPTAIN = "Nakasar_Spawner_Guard_Captain"
SPAWN_SPIDER = "Nakasar_Spawner_Spider"
SPAWN_GIANT_PUMPKIN = "Nakasar_Spawner_Giant_Pumpkin"
SPAWN_HUNTER = "Nakasar_Spawner_Vampire_Hunter"
# Sol de cellule : le Capitaine y téléporte sa cible (le plugin cherche la plus proche).
PRISON_CELL = "Nakasar_Prison_Cell"

STONE_WALL = [("Rock_Stone_Brick", 6), ("Rock_Stone_Brick_Mossy", 3), ("Rock_Stone_Cobble", 1), ("Rock_Stone_Cobble_Mossy", 1)]
STONE_FLOOR = [("Rock_Stone_Brick_Smooth", 4), ("Rock_Stone_Cobble", 2), ("Rock_Stone_Cobble_Mossy", 1)]
SLATE_WALL = [("Rock_Slate_Cobble", 6), ("Rock_Slate", 2), ("Rock_Shale_Cobble", 1)]
SLATE_FLOOR = [("Rock_Shale_Brick_Smooth", 3), ("Rock_Slate_Cobble", 1)]
BASALT_WALL = [("Rock_Basalt_Brick", 7), ("Rock_Basalt_Cobble", 2), ("Rock_Basalt_Brick_Decorative", 1)]
BASALT_FLOOR = [("Rock_Basalt_Brick_Smooth", 4), ("Rock_Basalt_Cobble", 1)]
SHALE_WALL = [("Rock_Shale_Brick", 6), ("Rock_Shale_Cobble", 3)]
SHALE_FLOOR = [("Rock_Shale_Brick_Smooth", 3), ("Rock_Shale_Cobble", 1)]
FOUNDATION = [("Rock_Stone_Cobble", 3), ("Rock_Stone", 2)]
DEADWOOD = "Wood_Deadwood_Planks"
GRAVE_DIRT = [("Soil_Dirt_Burnt", 3), ("Soil_Dirt", 1), ("Soil_Gravel", 1)]
GROUND = [("Soil_Grass_Burnt", 6), ("Soil_Dirt_Burnt", 2), ("Soil_Gravel_Mossy", 1)]
PATH = [("Soil_Pathway", 5), ("Soil_Gravel", 2), ("Rock_Stone_Cobble_Mossy", 1)]
WEBS = [("Deco_SpiderWeb_Full", 3), ("Deco_SpiderWeb", 4)]
BONES = [("Deco_Bone_Pile", 4), ("Deco_Bone_Skulls", 2), ("Deco_Bone_Ribs", 2), ("Deco_Bone_Full", 2), ("Deco_Bone_Spine", 1)]
CANDLES = [("Furniture_Ancient_Candle", 3), ("Furniture_Feran_Candle", 2), ("Furniture_Crude_Candle", 1)]
DEAD_PLANTS = [("Plant_Bush_Dead", 3), ("Plant_Grass_Gnarled", 4), ("Plant_Grass_Gnarled_Short", 3), ("Plant_Grass_Gnarled_Tall", 2),
               ("Plant_Bush_Dead_Twisted", 1), ("Plant_Bramble_Dead_Twisted", 1)]
GLOW_MUSHROOMS = [("Plant_Crop_Mushroom_Glowing_Purple", 3), ("Plant_Crop_Mushroom_Glowing_Violet", 2), ("Plant_Crop_Mushroom_Glowing_Green", 1)]
PUMPKIN_CROPS = [(pumpkin_crop("StageFinal"), 5), (pumpkin_crop("Stage3"), 2), (pumpkin_crop("Stage2"), 1)]

MATERIALS = {
    # murs, sol, bloc plein, bloc décoratif, demi-dalle (escaliers et toits)
    "stone": (STONE_WALL, STONE_FLOOR, "Rock_Stone_Brick", "Rock_Stone_Brick_Ornate", "Rock_Stone_Brick_Half"),
    "slate": (SLATE_WALL, SLATE_FLOOR, "Rock_Slate_Cobble", "Rock_Shale_Brick_Ornate", "Rock_Slate_Cobble_Half"),
    "basalt": (BASALT_WALL, BASALT_FLOOR, "Rock_Basalt_Brick", "Rock_Basalt_Brick_Ornate", "Rock_Basalt_Brick_Half"),
    "shale": (SHALE_WALL, SHALE_FLOOR, "Rock_Shale_Brick", "Rock_Shale_Brick_Ornate", "Rock_Shale_Brick_Half"),
}


def stairs_down(p, start, direction, depth, base, half, wall, width=3, headroom=3):
    """Escalier en demi-dalles (pas de 0,5 bloc : aucune orientation de bloc à deviner).

    Part du sol (y = -1) en `start` = (x, z) et descend de `depth` blocs en avançant d'un bloc par
    demi-pas dans `direction` = (dx, dz) ; `width` cases de large vers la droite de la marche.
    Le tunnel est muré (`wall`) là où il traverse le terrain. Renvoie la dernière case (x, z) ; on y
    marche à la hauteur y = -depth.
    """
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
#
# Un arbre est fait de troncs pleins (cubes) et de branches en tube. Chaque morceau touche le
# précédent par une face : tronc debout, tronc couché (rotation 4 ou 5) pour le départ d'une
# branche, coude en tronc debout quand la branche remonte, tube debout ou couché ensuite et souche
# courte (Branch_Short, accrochée au bloc précédent) au bout. Rien ne flotte.

SPECIES = {
    # essence : (poids, feuilles mortes de l'essence, posées sur le dessus des branches)
    "Ash": (5, "Plant_Leaves_Dead"),        # frêne mort, brun sombre (comme Trees/Ash_Dead du jeu)
    "Petrified": (3, "Plant_Leaves_Petrified"),  # gris pâle, ressort la nuit
    "Burnt": (2, "Plant_Leaves_Burnt"),      # calciné, noir
}

DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]
FACES = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))


def stub_rotation(d):
    """Souche de branche qui pointe vers d : elle s'accroche au bloc derrière elle."""
    return {(0, 1): 0, (1, 0): 1, (0, -1): 2, (-1, 0): 3}[d]


def wood_blocks(p):
    return {pos for pos, (name, _) in p.blocks.items() if name.startswith("Wood_") and "Gnarled" not in name}


def is_connected(p):
    """Tous les blocs de bois d'un arbre se touchent par une face (vérifié à la génération)."""
    wood = wood_blocks(p)
    if not wood:
        return True
    start = min(wood, key=lambda b: (b[1], abs(b[0]) + abs(b[2])))
    seen, todo = {start}, [start]
    while todo:
        x, y, z = todo.pop()
        for d in FACES:
            n = (x + d[0], y + d[1], z + d[2])
            if n in wood and n not in seen:
                seen.add(n)
                todo.append(n)
    return seen == wood


def floating_blocks(p):
    """Blocs qui ne rejoignent pas le sol (y <= 0) de face en face : ils flotteraient en jeu."""
    solid = {pos for pos, (name, _) in p.blocks.items() if name != AIR}
    seen = {pos for pos in solid if pos[1] <= 0}
    todo = list(seen)
    while todo:
        x, y, z = todo.pop()
        for d in FACES:
            n = (x + d[0], y + d[1], z + d[2])
            if n in solid and n not in seen:
                seen.add(n)
                todo.append(n)
    return solid - seen


def dead_tree(seed, size="medium", species=None, hanging=None, webs=False):
    """Arbre mort à la manière des arbres du jeu : `size` small / medium / large, `hanging` None /
    "lantern" / "cage" / "noose".

    Comme les arbres vanilla, tout le squelette est en blocs pleins : un fût droit de troncs, des
    branches en troncs pleins qui montent en escalier (chaque bloc touche le précédent par une face),
    et seulement au bout des rameaux des tubes fins (branche longue debout, souche sur le côté). Les
    feuilles mortes de l'essence se posent sur le dessus des branches. Aucun bloc ne flotte : c'est
    vérifié à la génération.
    """
    p = Prefab(seed)
    r = p.rng
    if species is None:
        species = r.choices(list(SPECIES), [w for w, _ in SPECIES.values()])[0]
    trunk, full = f"Wood_{species}_Trunk", f"Wood_{species}_Trunk_Full"
    twig, stub = f"Wood_{species}_Branch_Long", f"Wood_{species}_Branch_Short"
    leaves = SPECIES[species][1]
    height = {"small": r.randint(5, 7), "medium": r.randint(8, 10), "large": r.randint(11, 14)}[size]
    wide = {"small": 0, "medium": 1, "large": height // 2}[size]  # hauteur du pied élargi 2×2

    # fût : droit, élargi en 2×2 au pied des grands arbres, contreforts et racines au sol
    for y in range(height):
        p.set(0, y, 0, trunk)
    if size == "large":
        for y in range(wide):
            for dx, dz in ((1, 0), (0, 1), (1, 1)):
                p.set(dx, y, dz, trunk)
    foot = [(dx, dz) for dx, dz in ((0, 0), (1, 0), (0, 1), (1, 1)) if p.get(dx, 0, dz)]
    for fx, fz in foot:
        for d in DIRS:
            bx, bz = fx + d[0], fz + d[1]
            if p.free(bx, 0, bz) and r.random() < (0.6 if size != "small" else 0.3):
                p.set(bx, 0, bz, full)
                if size == "large" and r.random() < 0.4 and p.free(bx, 1, bz):
                    p.set(bx, 1, bz, full)
                p.set(bx, -1, bz, f"Wood_{species}_Roots")

    tips, limbs = [], []

    def touches_other_wood(cell, prev):
        x, y, z = cell
        for d in FACES:
            n = (x + d[0], y + d[1], z + d[2])
            if n != prev and n in p.blocks and p.blocks[n][0].startswith("Wood_"):
                return True
        return False

    def grow(start, d, length, rise, depth):
        """Branche en troncs pleins depuis `start` vers d ; `rise` = probabilité de monter d'un cran."""
        cell = start
        horizontal = 0
        for k in range(length):
            up = horizontal > 0 and r.random() < rise
            nxt = (cell[0], cell[1] + 1, cell[2]) if up else (cell[0] + d[0], cell[1], cell[2] + d[1])
            if not p.free(*nxt) or touches_other_wood(nxt, cell):
                break
            p.set(*nxt, full)
            horizontal = 0 if up else horizontal + 1
            if not up:
                limbs.append(nxt)
            cell = nxt
            rise = min(0.8, rise + 0.08)
            if depth == 0 and k == length // 2 and length >= 4 and r.random() < 0.6:
                side = (d[1], d[0]) if r.random() < 0.5 else (-d[1], -d[0])
                grow(cell, side, r.randint(2, 3), 0.45, 1)
        if cell != start:
            tips.append((cell, d))

    # branches le long du fût, tournées dans des directions différentes
    count = {"small": r.randint(2, 3), "medium": r.randint(3, 4), "large": r.randint(4, 5)}[size]
    dirs = DIRS[:]
    r.shuffle(dirs)
    low = max(wide + 2, height // 2 if size == "small" else height // 3 + 1)
    heights = sorted(r.sample(range(low, height - 1), min(count, height - 1 - low)))
    for i, y in enumerate(heights):
        length = r.randint(1, 2) + {"small": 0, "medium": 2, "large": 3}[size]
        grow((0, y, 0), dirs[i % 4], length, 0.25, 0)
    # couronne : deux ou trois rameaux qui partent du sommet en remontant
    for d in r.sample(DIRS, r.randint(2, 3) if size != "small" else 1):
        grow((0, height - 1, 0), d, r.randint(2, 3) + (size == "large"), 0.5, 1)

    # bouts de rameaux : tube fin debout, parfois une souche qui continue sur le côté
    for (x, y, z), d in tips + [((0, height - 1, 0), None)]:
        for k in range(1, r.randint(1, 2) + 1):
            if not p.free(x, y + k, z):
                break
            p.set(x, y + k, z, twig, UPRIGHT)
        if d and p.free(x + d[0], y, z + d[1]) and r.random() < 0.6:
            p.set(x + d[0], y, z + d[1], stub, stub_rotation(d))

    # feuilles mortes posées sur le dessus des branches (le modèle du jeu repose sur un bloc plein)
    if r.random() < 0.75:
        for x, y, z in limbs:
            if p.free(x, y + 1, z) and r.random() < 0.3:
                p.set(x, y + 1, z, leaves)

    # ce qui pend sous les branches : lanterne, cage, corde, toiles, buissons morts
    hung = False
    r.shuffle(limbs)
    for x, y, z in limbs:
        drop = {"lantern": 2, "cage": 3, "noose": 2}.get(hanging, 0)
        if hanging and not hung and y >= drop + 2 and all(p.free(x, y - k, z) for k in range(1, drop + 2)):
            hung = True
            if hanging == "lantern":
                p.set(x, y - 1, z, "Deco_Iron_Chains_Vertical")
                p.set(x, y - 2, z, "Deco_Lantern_Ceiling")
            elif hanging == "cage":
                p.set(x, y - 1, z, "Deco_Iron_Chains_Vertical")
                p.set(x, y - 2, z, "Deco_Iron_Bars")
                p.set(x, y - 3, z, "Deco_Iron_Bars")
                if p.free(x, 0, z):
                    p.set(x, 0, z, "Deco_Bone_Skulls")
            else:
                for k in range(1, 3):
                    p.set(x, y - k, z, "Deco_Rope")
            continue
        if not p.free(x, y - 1, z) or y < 3:
            continue
        if webs and r.random() < 0.35:
            p.set(x, y - 1, z, p.pick(WEBS))
        elif r.random() < 0.2:
            p.set(x, y - 1, z, "Plant_Bush_Dead_Hanging")

    # au pied : herbes tordues, racines noueuses, parfois des os ou des champignons qui luisent
    for _ in range(r.randint(2, 5)):
        gx, gz = r.randint(-2, 3), r.randint(-2, 3)
        if p.free(gx, 0, gz):
            p.set(gx, 0, gz, r.choice(["Wood_Gnarled_Roots", "Plant_Grass_Gnarled", "Plant_Grass_Gnarled_Short", "Plant_Bush_Dead"]))
    if r.random() < 0.3:
        gx, gz = r.choice([(-2, 1), (2, -1), (1, 2), (-1, -2)])
        if p.free(gx, 0, gz):
            p.set(gx, 0, gz, p.pick(GLOW_MUSHROOMS if r.random() < 0.6 else BONES), r.randint(0, 3))
    assert is_connected(p), f"arbre {seed} : bois détaché"
    assert not floating_blocks(p), f"arbre {seed} : blocs qui flottent {sorted(floating_blocks(p))[:5]}"
    return p


# --- pumpkin fields ---------------------------------------------------------------------------

def face_toward(x, z, tx, tz):
    """Lacet d'un objet posé en (x, z) pour qu'il regarde vers (tx, tz), sur l'axe dominant."""
    dx, dz = tx - x, tz - z
    if abs(dx) > abs(dz):
        return EAST if dx > 0 else WEST
    return SOUTH if dz >= 0 else NORTH


def hang_lantern(p, x, y, z):
    """Lanterne de plafond en (x, y, z), suspendue par une chaîne au premier bloc plein au-dessus."""
    top = y + 1
    while p.free(x, top, z):
        top += 1
        if top > y + 12:
            raise ValueError(f"lanterne en ({x}, {y}, {z}) : pas de plafond au-dessus")
    p.fill(x, y + 1, z, x, top - 1, z, "Deco_Iron_Chains_Vertical")
    p.set(x, y, z, "Deco_Lantern_Ceiling")


def lantern_post(p, x, z, height=2, top="Deco_Lantern"):
    p.fill(x, 0, z, x, height - 1, z, "Wood_Deadwood_Beam")
    p.set(x, height, z, top)


def shed(p, x0, z0, w, d):
    """Cabane en planches de bois mort, toit à deux pans, porte au sud."""
    x1, z1 = x0 + w - 1, z0 + d - 1
    p.floor(x0, z0, x1, z1, -1, DEADWOOD)
    p.hollow(x0, 0, z0, x1, 2, z1, [("Wood_Deadwood_Planks", 5), ("Wood_Deadwood_Decorative", 1)])
    for cx in (x0, x1):
        for cz in (z0, z1):
            p.fill(cx, 0, cz, cx, 2, cz, "Wood_Deadwood_Beam")
    door = (x0 + x1) // 2
    p.clear(door, 0, z1, door, 1, z1)
    p.set(x0, 1, (z0 + z1) // 2, AIR)  # fenêtre
    p.gable(x0, z0, x1, z1, 3, "Wood_Deadwood_Planks", "Wood_Deadwood_Planks_Half", gable_wall=DEADWOOD)
    p.chest(door + 1, 0, z0 + 1, "Furniture_Crude_Chest_Small", SOUTH, LOOT_FARM)
    p.set(x0 + 1, 0, z0 + 1, "Ingredient_Hay")
    p.set(x0 + 1, 1, z0 + 1, "Furniture_Crude_Candle")
    p.set(x1 - 1, 2, z1 - 1, p.pick(WEBS))
    if p.free(door, 2, z1 + 1):
        p.set(door, 2, z1 + 1, "Deco_Lantern_Ceiling")


GIANT_CLEARING = 7   # rayon de la clairière de la citrouille géante (elle ne bouge pas, ses vrilles frappent autour)
TENDRILS = [("Plant_Bramble_Dead_Twisted", 3), ("Plant_Roots_Leafy", 2), ("Plant_Bush_Bramble", 2), ("Plant_Bush_Dead", 1)]
ROTTEN_SOIL = [("Soil_Dirt_Burnt", 4), ("Soil_Mud", 2), ("Soil_Dirt", 2), ("Soil_Dirt_Tilled", 1)]


def pumpkin_field(seed, w=23, d=19, giant=False):
    """Champ de citrouilles délaissé : rangs de citrouilles, allée, clôture, cabane du fermier.

    Les citrouilles sculptées ne sont qu'à l'entrée, tournées vers le chemin ; les épouvantails et
    les meules regardent l'allée centrale. `giant` : la citrouille géante (élite) au centre, dans une
    clairière de terre pourrie bordée de ronces et de citrouilles entières.
    """
    p = Prefab(seed)
    r = p.rng
    x0, z0, x1, z1 = -w // 2, -d // 2, w // 2, d // 2
    p.clear(x0 - 1, 0, z0 - 1, x1 + 1, 5, z1 + 1)
    yard = lambda x, z: z >= z1 - 2 and (x >= x1 - 5 or x <= x0 + 3)   # coin de la récolte, près de l'entrée
    # sillons est-ouest : deux rangs de terre labourée, un rang de terre brûlée ; allée centrale nord-sud
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            aisle = abs(x) <= 1
            on_row = (z - z0) % 3 != 2
            if aisle or yard(x, z):
                p.set(x, -1, z, p.pick(PATH))
                continue
            p.set(x, -1, z, "Soil_Dirt_Tilled" if on_row else p.pick(GRAVE_DIRT))
            p.set(x, -2, z, "Soil_Dirt")
            if on_row and r.random() < 0.72:
                p.set(x, 0, z, p.pick(PUMPKIN_CROPS))
            elif not on_row and r.random() < 0.1:
                p.set(x, 0, z, p.pick(DEAD_PLANTS))
    # clôture de bois mort, ouverte au milieu des côtés nord et sud
    for x in range(x0 - 1, x1 + 2):
        for z in (z0 - 1, z1 + 1):
            p.set(x, -1, z, "Soil_Grass_Burnt")
            if abs(x) > 1:
                p.set(x, 0, z, "Wood_Deadwood_Fence")
    for z in range(z0 - 1, z1 + 2):
        for x in (x0 - 1, x1 + 1):
            p.set(x, -1, z, "Soil_Grass_Burnt")
            p.set(x, 0, z, "Wood_Deadwood_Fence")
    # poteaux : lanternes aux coins et le long de l'allée, citrouilles sculptées de part et d'autre
    # des entrées, tournées vers l'extérieur
    for cx, cz in ((x0 - 1, z0 - 1), (x1 + 1, z0 - 1), (x0 - 1, z1 + 1), (x1 + 1, z1 + 1)):
        lantern_post(p, cx, cz, 2)
    for cz, facing in ((z0 - 1, NORTH), (z1 + 1, SOUTH)):
        for cx in (-2, 2):
            p.fill(cx, 0, cz, cx, 1, cz, "Wood_Deadwood_Beam")
            p.set(cx, 2, cz, "Deco_Halloween_Pumpkin_Scary", facing)
    for z in range(z0 + 3, z1 - 2, 6):
        lantern_post(p, 2 if (z // 6) % 2 else -2, z, 2)
    # épouvantails dans les rangs, tournés vers l'allée
    for sx, sz in ((x0 + 4, z0 + 3), (x1 - 4, z0 + 9), (r.choice([x0 + 5, x1 - 5]), z0 + 6)):
        p.set(sx, -1, sz, "Soil_Dirt")
        p.clear(sx, 0, sz, sx, 2, sz)
        p.set(sx, 0, sz, "Deco_Scarecrow", face_toward(sx, sz, 0, sz))
    # charrette de la récolte près de l'entrée sud, paniers et meules de foin
    p.set(x1 - 4, 0, z1 - 2, "Halloween_Wagon", WEST)
    for hx, hz, hh in ((x1, z1 - 1, 2), (x1, z1 - 2, 1), (x1 - 1, z1, 1), (x0, z1, 1)):
        p.fill(hx, 0, hz, hx, hh - 1, hz, "Ingredient_Hay")
        if r.random() < 0.6:
            p.set(hx, hh, hz, pumpkin_crop("StageFinal"))
    p.set(2, 0, z1 - 1, "Halloween_Basket_Pumpkin")
    p.set(-2, 0, z1 - 1, "Halloween_Basket_Straw")
    p.set(x0 + 2, 0, z1 - 1, "Halloween_Basket_Pumpkin")
    # cabane de fermier dans un coin du nord
    sw, sd = 5, 4
    sx0 = x0 + 1 if r.random() < 0.5 else x1 - sw
    p.clear(sx0, 0, z0, sx0 + sw - 1, 5, z0 + sd + 1)
    shed(p, sx0, z0, sw, sd)
    p.ruin(90, keep_below=1, names={"Wood_Deadwood_Planks", "Wood_Deadwood_Planks_Half"})
    # un arbre mort penché sur la clôture
    p.paste(dead_tree(r.randint(0, 1 << 30), "medium"), x1 + 4, 0, z0 + 2, min_y=0)
    if giant:
        giant_clearing(p)
    return p


def giant_clearing(p, radius=GIANT_CLEARING):
    """Clairière de la citrouille géante au centre du champ : rien ne pousse plus à portée de ses
    vrilles, sauf des ronces sur le bord ; citrouilles entières et lanternes tournées vers l'extérieur
    en couronne, ossements des curieux. Le bloc d'apparition est au centre."""
    r = p.rng
    for x in range(-radius, radius + 1):
        for z in range(-radius, radius + 1):
            if x * x + z * z <= radius * radius:
                p.clear(x, 0, z, x, 5, z)
                p.set(x, -1, z, p.pick(ROTTEN_SOIL))
                p.set(x, -2, z, "Soil_Dirt")
    spawners(p, SPAWN_GIANT_PUMPKIN, [(0, 0)])
    near_center = lambda x, z: x * x + z * z <= 4
    for _ in range(30):
        a = r.random() * 2 * math.pi
        d = radius - 1.5 + r.random() * 2.5
        x, z = round(math.cos(a) * d), round(math.sin(a) * d)
        if p.free(x, 0, z) and not p.free(x, -1, z):
            p.set(x, 0, z, p.pick(TENDRILS))
    for _ in range(18):
        x, z = r.randint(-radius + 1, radius - 1), r.randint(-radius + 1, radius - 1)
        if not near_center(x, z) and x * x + z * z < (radius - 1) ** 2 and p.free(x, 0, z):
            p.set(x, 0, z, "Plant_Vine_Rug" if r.random() < 0.7 else p.pick(BONES), r.randint(0, 3))
    for k in range(6):
        a = (k + r.random() * 0.5) * math.pi / 3
        x, z = round(math.cos(a) * (radius + 1)), round(math.sin(a) * (radius + 1))
        p.clear(x, 0, z, x, 2, z)
        p.set(x, -1, z, "Soil_Dirt")
        if k % 2:
            p.set(x, 0, z, "Plant_Crop_Pumpkin_Block")
            if r.random() < 0.5:
                p.set(x, 1, z, "Plant_Crop_Pumpkin_Block")
        else:
            p.set(x, 0, z, "Deco_Halloween_Pumpkin_Scary", face_toward(x, z, 2 * x, 2 * z))


# --- cemeteries -------------------------------------------------------------------------------

def stone_cross(p, x, z, wall="Rock_Stone_Brick_Wall"):
    """Croix de pierre : les murets se raccordent tout seuls en croix."""
    p.set(x, 0, z, wall)
    p.set(x, 1, z, wall)
    p.set(x, 2, z, wall)
    p.set(x - 1, 1, z, wall)
    p.set(x + 1, 1, z, wall)


def grave(p, x, z, r, theme):
    """Une sépulture tête au nord (z), pied au sud (z + 1, z + 2)."""
    kind = r.choices(["stele", "cross", "obelisk", "sarcophagus", "broken", "open"],
                     [5, 2, 1, 2, 2, 4 if theme == "undead" else 0.5])[0]
    if kind == "stele":
        p.set(x, 0, z, "Furniture_Village_Tombstone", SOUTH)
    elif kind == "cross":
        stone_cross(p, x, z)
    elif kind == "obelisk":
        p.set(x, 0, z, "Rock_Stone_Brick_Pillar_Base")
        p.set(x, 1, z, "Rock_Stone_Brick_Pillar_Middle")
        p.set(x, 2, z, "Rock_Stone_Brick_Ornate")
        p.set(x, 3, z, p.pick(CANDLES))
    elif kind == "sarcophagus":
        p.set(x, 0, z, "Furniture_Village_Tombstone", SOUTH)
        for dz in (1, 2):
            p.set(x, 0, z + dz, "Rock_Stone_Brick_Smooth")
            p.set(x, 1, z + dz, "Rock_Stone_Brick_Half")
        return
    elif kind == "broken":
        p.set(x, 0, z, r.choice(["Furniture_Village_Tombstone", "Furniture_Human_Ruins_Statue_Broken"]), r.randint(0, 3))
        p.set(x + r.choice([-1, 1]), 0, z + 1, "Rock_Stone_Cobble_Mossy_Half")
    if kind == "open":
        # tombe ouverte : fosse, cercueil au fond, terre rejetée sur le côté
        p.set(x, 0, z, "Furniture_Village_Tombstone", r.randint(0, 3))
        for dz in (1, 2):
            p.set(x, -1, z + dz, AIR)
            p.set(x, -2, z + dz, AIR)
            p.set(x, -3, z + dz, p.pick(GRAVE_DIRT))
            if r.random() < 0.6:
                p.set(x + 1, 0, z + dz, "Soil_Dirt_Burnt")
        p.set(x, -2, z + 1, "Furniture_Village_Coffin", WEST)  # couché nord-sud dans la fosse
        return
    for dz in (1, 2):
        p.set(x, -1, z + dz, p.pick(GRAVE_DIRT))
    if theme == "haunted" and r.random() < 0.6:
        p.set(x, 0, z + 1, r.choice([p.pick(CANDLES), "Plant_Petals_Blood", "Plant_Petals_Blood"]))
    elif theme == "spiders" and r.random() < 0.5:
        p.set(x, 0, z + 1, p.pick(WEBS))
    elif theme == "undead" and r.random() < 0.4:
        p.set(x, 0, z + 1, p.pick(BONES), r.randint(0, 3))
    elif r.random() < 0.2:
        p.set(x, 0, z + 2, p.pick(DEAD_PLANTS))


def mausoleum(p, x0, z0, r, door_south=True):
    """Petit caveau 5 × 5 en pierre, toit en demi-dalles, grille à l'entrée."""
    x1, z1 = x0 + 4, z0 + 4
    p.floor(x0, z0, x1, z1, -1, STONE_FLOOR)
    p.hollow(x0, 0, z0, x1, 3, z1, STONE_WALL)
    for cx in (x0, x1):
        for cz in (z0, z1):
            p.set(cx, 0, cz, "Rock_Stone_Brick_Pillar_Base")
            p.fill(cx, 1, cz, cx, 3, cz, "Rock_Stone_Brick_Pillar_Middle")
    p.gable(x0, z0, x1, z1, 4, "Rock_Slate_Cobble", "Rock_Slate_Cobble_Half")
    dz = z1 if door_south else z0
    p.clear(x0 + 2, 0, dz, x0 + 2, 1, dz)
    p.set(x0 + 2, 0, dz, "Deco_Iron_Bars")
    p.set(x0 + 2, 2, dz, "Rock_Stone_Brick_Ornate")
    p.set(x0 + 2, 0, (z0 + z1) // 2, "Furniture_Ancient_Coffin", SOUTH)
    p.set(x0 + 1, 0, z0 + 1, p.pick(CANDLES))
    p.set(x1 - 1, 0, z0 + 1, p.pick(CANDLES))
    p.set(x1 - 1, 2, z1 - 1, p.pick(WEBS))
    outside = dz + (1 if door_south else -1)
    p.set(x0 + 1, 0, outside, "Furniture_Village_Brazier")
    p.set(x1 - 1, 0, outside, "Furniture_Village_Brazier")


def chapel(p, cx, z0, r, theme):
    """Chapelle 9 × 13 : nef au toit pentu, clocher sur la façade sud, autel et bancs."""
    x0, x1, z1 = cx - 4, cx + 4, z0 + 12
    p.floor(x0, z0, x1, z1, -1, STONE_FLOOR, FOUNDATION, depth=2)
    p.hollow(x0, 0, z0, x1, 5, z1, STONE_WALL)
    for z in range(z0, z1 + 1, 3):
        for x in (x0, x1):
            p.set(x, 0, z, "Rock_Stone_Brick_Pillar_Base")
            p.fill(x, 1, z, x, 5, z, "Rock_Stone_Brick_Pillar_Middle")
        if z0 < z < z1:
            for x in (x0, x1):
                p.fill(x, 2, z + 1, x, 3, z + 1, "Deco_Iron_Bars")  # vitraux brisés
    p.gable(x0 - 1, z0, x1 + 1, z1, 6, "Rock_Slate_Cobble", "Rock_Slate_Cobble_Half", gable_wall=STONE_WALL)
    # clocher : tour 5 × 5 sur la façade sud
    tx0, tz0 = cx - 2, z1 - 2
    p.hollow(tx0, 0, tz0, tx0 + 4, 12, tz0 + 4, STONE_WALL)
    for y in (6, 11):
        p.fill(tx0 + 1, y, tz0 + 1, tx0 + 3, y, tz0 + 3, "Wood_Deadwood_Planks")
    for y in range(8, 11):
        for (wx, wz) in ((cx, tz0), (cx, tz0 + 4), (tx0, tz0 + 2), (tx0 + 4, tz0 + 2)):
            p.set(wx, y, wz, AIR)  # baies du beffroi
    p.set(cx, 10, tz0 + 2, "Deco_Iron_Chains_Vertical")
    p.set(cx, 9, tz0 + 2, "Deco_Lantern_Ceiling")
    p.crenellate(tx0, tz0, tx0 + 4, tz0 + 4, 13, STONE_WALL)
    p.spire(cx, tz0 + 2, 1, 13, "Rock_Slate_Cobble", step=2)
    # porche
    p.clear(cx - 1, 0, tz0 + 4, cx + 1, 2, tz0 + 4)
    p.clear(cx - 1, 0, tz0, cx + 1, 2, tz0)
    p.fill(cx - 1, 3, tz0 + 4, cx + 1, 3, tz0 + 4, "Rock_Stone_Brick_Ornate")
    p.set(cx, 2, tz0 + 3, "Deco_Lantern_Ceiling")
    p.set(cx - 2, 0, tz0 + 5, "Furniture_Village_Brazier")
    p.set(cx + 2, 0, tz0 + 5, "Furniture_Village_Brazier")
    # intérieur : allée, bancs, autel, cercueil
    for z in range(z0 + 1, tz0):
        p.set(cx, -1, z, "Cloth_Block_Wool_Purple" if theme == "haunted" else "Rock_Stone_Brick_Smooth")
    for z in range(z0 + 4, tz0 - 1, 2):
        for x in (cx - 2, cx + 2):
            p.set(x, 0, z, "Furniture_Ancient_Bench", NORTH)
    p.fill(cx - 1, 0, z0 + 1, cx + 1, 0, z0 + 1, "Rock_Stone_Brick_Smooth")
    p.set(cx, 1, z0 + 1, "Furniture_Temple_Dark_Statue", SOUTH)
    p.set(cx - 1, 1, z0 + 1, p.pick(CANDLES))
    p.set(cx + 1, 1, z0 + 1, p.pick(CANDLES))
    p.set(cx, 0, z0 + 3, "Furniture_Ancient_Coffin", WEST)   # devant l'autel, dans l'axe de la nef
    p.set(cx - 3, 0, z0 + 1, "Furniture_Temple_Dark_Brazier")
    p.set(cx + 3, 0, z0 + 1, "Furniture_Temple_Dark_Brazier")
    p.set(cx, 5, z0 + 6, "Furniture_Tavern_Chandelier")
    for _ in range(10):
        x, z = r.randint(x0 + 1, x1 - 1), r.randint(z0 + 1, tz0 - 1)
        if p.free(x, 5, z):
            p.set(x, 5, z, p.pick(WEBS))
    p.scatter(x0 + 1, 0, z0 + 3, x1 - 1, tz0 - 1, 4, BONES if theme == "undead" else CANDLES)


def cemetery(seed, theme):
    p = Prefab(seed)
    r = p.rng
    w, d = r.choice([(31, 33), (33, 31), (29, 33)])
    x0, z0, x1, z1 = -w // 2, -d // 2, w // 2, d // 2
    p.clear(x0, 0, z0, x1, 6, z1)
    # sol : herbe brûlée en plaques, allée principale nord-sud et allée transversale
    blobs = [(r.randint(x0, x1), r.randint(z0, z1), r.randint(2, 5)) for _ in range(9)]
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            near = any((x - bx) ** 2 + (z - bz) ** 2 <= br * br for bx, bz, br in blobs)
            p.set(x, -1, z, r.choice(["Soil_Dirt_Burnt", "Soil_Gravel_Mossy", "Soil_Ash"]) if near else p.pick(GROUND))
    cross_z = z0 + 18
    for z in range(z0 + 1, z1 + 1):
        for x in (-1, 0, 1):
            p.set(x, -1, z, p.pick(PATH))
    for x in range(x0 + 1, x1):
        p.set(x, -1, cross_z, p.pick(PATH))
    # muret, grille et piliers, avec des brèches
    for x in range(x0, x1 + 1):
        for z in (z0, z1):
            if z == z1 and abs(x) <= 2:
                continue
            p.set(x, 0, z, "Rock_Stone_Brick_Wall")
            p.set(x, 1, z, "Deco_Iron_Bars")
    for z in range(z0, z1 + 1):
        for x in (x0, x1):
            p.set(x, 0, z, "Rock_Stone_Brick_Wall")
            p.set(x, 1, z, "Deco_Iron_Bars")
    for k in range(r.randint(2, 4)):  # brèches
        if r.random() < 0.5:
            bx, bz, along = r.randint(x0 + 3, x1 - 3), r.choice([z0, z1]), (1, 0)
        else:
            bx, bz, along = r.choice([x0, x1]), r.randint(z0 + 3, z1 - 3), (0, 1)
        if bz == z1 and abs(bx) <= 4:
            continue
        for i in range(r.randint(1, 3)):
            p.set(bx + along[0] * i, 1, bz + along[1] * i, AIR)
            if r.random() < 0.6:
                p.set(bx + along[0] * i, 0, bz + along[1] * i, "Rock_Stone_Cobble_Mossy_Half")
    posts = [(x, z) for x in range(x0, x1 + 1, 4) for z in (z0, z1)] + [(x, z) for z in range(z0 + 4, z1, 4) for x in (x0, x1)]
    for i, (px, pz) in enumerate(posts):
        if pz == z1 and abs(px) <= 2:
            continue
        p.set(px, 0, pz, "Rock_Stone_Brick_Pillar_Base")
        p.set(px, 1, pz, "Rock_Stone_Brick_Pillar_Middle")
        p.set(px, 2, pz, "Rock_Stone_Brick_Ornate")
        if i % 2 == 0:
            p.set(px, 3, pz, "Deco_Spider_Cocoon" if theme == "spiders" else "Deco_Lantern")
        elif r.random() < 0.6:
            p.set(px, 3, pz, p.pick(CANDLES))
    # portail : deux hauts piliers, linteau, lanterne suspendue
    for gx in (-3, 3):
        p.set(gx, 0, z1, "Rock_Stone_Brick_Pillar_Base")
        p.fill(gx, 1, z1, gx, 4, z1, "Rock_Stone_Brick_Pillar_Middle")
        p.set(gx, 5, z1, "Rock_Stone_Brick_Ornate")
        p.set(gx, 6, z1, "Deco_Lantern")
        p.set(gx, 0, z1 + 1, "Furniture_Village_Brazier")
    p.fill(-2, 5, z1, 2, 5, z1, "Rock_Stone_Brick_Ornate")
    p.set(0, 6, z1, "Rock_Stone_Brick_Pillar_Middle")
    p.set(0, 7, z1, "Rock_Stone_Brick_Ornate")
    p.set(0, 4, z1, "Deco_Iron_Chains_Vertical")
    p.set(0, 3, z1, "Deco_Lantern_Ceiling")
    # chapelle au fond
    chapel(p, 0, z0 + 1, r, theme)
    # caveaux de famille près du portail
    mausoleum(p, x0 + 2, z1 - 7, r)
    if r.random() < 0.7:
        mausoleum(p, x1 - 6, z1 - 7, r)
    # rangées de tombes de part et d'autre de l'allée, en dehors de la chapelle et des caveaux
    for x in list(range(x0 + 3, -3, 3)) + list(range(4, x1 - 1, 3)):
        for z in range(z0 + 3, z1 - 9, 4):
            if abs(x) <= 6 and z <= z0 + 15:  # chapelle
                continue
            if z in (cross_z - 2, cross_z - 1, cross_z):
                continue
            if r.random() < 0.85:
                grave(p, x, z, r, theme)
    # lanternes le long de l'allée
    for z in range(z0 + 16, z1 - 1, 5):
        lantern_post(p, 2, z, 2)
        lantern_post(p, -2, z + 2, 2)
    # arbres morts et décor selon le thème
    tree_spots = [(x0 + 2, cross_z + 1), (x1 - 2, cross_z - 4), (x0 + 3, z0 + 3), (x1 - 3, z0 + 4)]
    for tx, tz in tree_spots:
        if r.random() < 0.75:
            t = dead_tree(r.randint(0, 1 << 30), r.choice(["small", "medium"]), webs=theme == "spiders",
                          hanging="lantern" if theme == "haunted" and r.random() < 0.5 else None)
            p.paste(t, tx, 0, tz, min_y=0)
    if theme == "haunted":
        p.scatter(x0 + 1, 0, z0 + 1, x1 - 1, z1 - 1, 14, CANDLES)
        p.scatter(x0 + 1, 0, z0 + 1, x1 - 1, z1 - 1, 10, GLOW_MUSHROOMS)
        p.scatter(x0 + 1, 0, z0 + 1, x1 - 1, z1 - 1, 10, DEAD_PLANTS)
    elif theme == "spiders":
        for _ in range(6):
            cx, cz = r.randint(x0 + 2, x1 - 2), r.randint(z0 + 16, z1 - 2)
            for dx in range(-2, 3):
                for dz in range(-2, 3):
                    if abs(dx) + abs(dz) <= 3 and r.random() < 0.6 and p.free(cx + dx, 0, cz + dz):
                        p.set(cx + dx, 0, cz + dz, "Deco_SpiderWeb_Flat")
            p.set(cx, 0, cz, "Deco_Spider_Cocoon")
        p.scatter(x0 + 1, 0, z0 + 1, x1 - 1, z1 - 1, 22, WEBS)
        p.scatter(x0 + 1, 1, z0 + 1, x1 - 1, z1 - 1, 10, WEBS, require_air=True)
        p.scatter(x0 + 1, 0, z0 + 1, x1 - 1, z1 - 1, 8, [("Deco_Spider_Cocoon", 2), ("Deco_Bone_Pile", 1)])
        p.scatter(x0 + 1, 0, z0 + 1, x1 - 1, z1 - 1, 6, GLOW_MUSHROOMS)
    else:
        p.scatter(x0 + 1, 0, z0 + 1, x1 - 1, z1 - 1, 18, BONES)
        p.scatter(x0 + 1, 0, z0 + 1, x1 - 1, z1 - 1, 5, [("Deco_Bone_Spike", 2), ("Deco_Bone_Ribs_Long", 1), ("Deco_Bone_Spike_Large", 1)])
        p.scatter(x0 + 1, 0, z0 + 1, x1 - 1, z1 - 1, 8, [("Plant_Crop_Mushroom_Glowing_Green", 2), ("Plant_Crop_Mushroom_Glowing_Purple", 1)])
        p.scatter(x0 + 1, 0, z0 + 1, x1 - 1, z1 - 1, 8, DEAD_PLANTS)
    # chapelle et caveaux usés par le temps ; le muret et sa grille restent entiers (brèches à part)
    p.ruin(90, keep_below=1, names={"Rock_Stone_Brick", "Rock_Stone_Brick_Mossy", "Rock_Stone_Cobble", "Rock_Stone_Cobble_Mossy"})
    return p


# --- crypts -----------------------------------------------------------------------------------

def crypt(seed, material):
    """Mausolée en surface et salle voûtée enterrée au nord, reliés par un escalier."""
    p = Prefab(seed)
    r = p.rng
    wall, flr, brick, ornate, half = MATERIALS[material]
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
            p.set(px + (1 if px < 0 else -1), cy0 + 1, pz, "Furniture_Temple_Dark_Brazier")
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
    p.set(-2, 5, z1 + 1, "Deco_Lantern")
    p.set(2, 5, z1 + 1, "Deco_Lantern")
    p.set(0, 3, z1, "Deco_Lantern_Ceiling")
    p.set(0, 7, z1, "Furniture_Temple_Dark_Statue", SOUTH)
    p.set(-3, 0, z1 - 1, p.pick(CANDLES))
    p.set(3, 0, z1 - 1, p.pick(CANDLES))
    p.set(-3, 4, z0 + 1, p.pick(WEBS))
    p.set(3, 4, z0 + 1, p.pick(WEBS))
    # escalier : part du fond du mausolée et descend vers le nord jusqu'à la salle
    stairs_down(p, (-1, 2), (0, -1), depth, brick, half, wall, width=3)
    # cercueils le long des murs, coffre au fond, os et toiles
    for z in range(cz0 + 1, cz1, 3):
        p.set(cx0 + 1, cy0 + 1, z, r.choice(["Furniture_Ancient_Coffin", "Furniture_Temple_Dark_Coffin", "Furniture_Human_Ruins_Coffin"]), EAST)
        p.set(cx1 - 1, cy0 + 1, z, r.choice(["Furniture_Ancient_Coffin", "Furniture_Temple_Dark_Coffin", "Furniture_Village_Coffin"]), WEST)
    p.chest(0, cy0 + 1, cz0 + 1, "Furniture_Temple_Dark_Chest_Large", SOUTH, LOOT_CRYPT)
    p.set(-2, cy0 + 1, cz0 + 1, p.pick(CANDLES))
    p.set(1, cy0 + 1, cz0 + 1, p.pick(CANDLES))
    if r.random() < 0.5:
        p.set(0, cy0 + 1, cz0 + 5, "Furniture_Temple_Dark_Statue", SOUTH)
    p.scatter(cx0 + 1, cy0 + 1, cz0 + 1, cx1 - 1, cz1 - 1, 9, BONES)
    p.scatter(cx0 + 1, cy0 + 1, cz0 + 1, cx1 - 1, cz1 - 1, 5, CANDLES)
    p.scatter(cx0 + 1, cy0 + 1, cz0 + 1, cx1 - 1, cz1 - 1, 4, [("Rock_Crystal_Purple_Small", 1)])
    for _ in range(14):
        x, z = r.randint(cx0, cx1), r.randint(cz0, cz1)
        if p.get(x, cy0 + 4, z) == AIR:
            p.set(x, cy0 + 4, z, p.pick(WEBS))
    # tombes, braseros et citrouilles devant l'entrée
    for x in (-4, 4):
        p.set(x, 0, z1 + 3, "Furniture_Village_Tombstone", SOUTH)
        p.set(x, -1, z1 + 4, p.pick(GRAVE_DIRT))
        p.set(x, -1, z1 + 5, p.pick(GRAVE_DIRT))
    for x in (-3, 3):
        p.set(x, 0, z1 + 1, "Furniture_Village_Brazier")
    for z in range(z1 + 1, z1 + 7):
        for x in (-1, 0, 1):
            p.set(x, -1, z, p.pick(PATH))
    p.paste(dead_tree(r.randint(0, 1 << 30), "medium", webs=True), 7, 0, z1 + 3, min_y=0)
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
        p.set(cx, height + 2, cz, "Furniture_Village_Brazier")
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
    p.set(-gate_half - 1, height + 3, z, "Furniture_Village_Brazier")
    p.set(gate_half + 1, height + 3, z, "Furniture_Village_Brazier")
    p.set(0, height - 1, z - 1, "Deco_Lantern_Ceiling")
    for x in (-gate_half - 2, gate_half + 2):
        p.set(x, 0, z + 1, "Furniture_Village_Brazier")


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
    wall, flr, roof, ornate, _ = MATERIALS[material]
    s = 16
    p.clear(-s, 0, -s, s, 12, s)
    # cour : terre et pavés
    for x in range(-s, s + 1):
        for z in range(-s, s + 1):
            p.set(x, -1, z, r.choice(["Soil_Grass_Burnt", "Soil_Dirt_Burnt", "Rock_Stone_Cobble_Mossy", "Soil_Gravel_Mossy"]))
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
    for z in (-10, -8, -6):                       # trois tables de 2 × 2 bout à bout
        p.set(-1, 0, z, "Furniture_Human_Ruins_Table")
    for z in range(-10, -4):
        p.set(-2, 0, z, "Furniture_Human_Ruins_Chair", EAST)
        p.set(1, 0, z, "Furniture_Human_Ruins_Chair", WEST)
    for z in (-10, -7, -5):
        p.set(-1 + (z % 2), 1, z, p.pick(CANDLES))
    p.set(0, level_h - 1, -7, "Furniture_Tavern_Chandelier")
    for x in (-4, 4):
        p.set(x, 3, -11, "Furniture_Human_Ruins_Banner", SOUTH)
    p.set(-4, 0, -11, "Furniture_Human_Ruins_Bookshelf", SOUTH)
    p.set(4, 0, -11, "Furniture_Human_Ruins_Bookshelf", SOUTH)
    p.set(-5, 0, -3, "Furniture_Temple_Dark_Brazier")
    p.set(5, 0, -3, "Furniture_Temple_Dark_Brazier")
    # étage : chambre abandonnée
    y = level_h + 1
    p.set(-4, y, -10, "Furniture_Ancient_Bed", EAST)
    p.set(-4, y, -6, "Furniture_Human_Ruins_Wardrobe", EAST)
    p.chest(3, y, -11, "Furniture_Ancient_Chest_Large", SOUTH, LOOT_CASTLE)
    p.set(0, y + 1, -11, "Furniture_Ancient_Painting", SOUTH)
    p.scatter(-5, y, -11, 5, -3, 6, CANDLES)
    # toiles d'araignée partout sous les plafonds
    for _ in range(16):
        x, z = r.randint(-5, 5), r.randint(-11, -3)
        for yy in (level_h - 1, 2 * level_h - 1):
            if p.get(x, yy, z) == AIR and p.free(x, yy, z) and r.random() < 0.5:
                p.set(x, yy, z, p.pick(WEBS))
    # cour : puits, tombes, arbres morts, citrouilles
    p.hollow(8, 0, 6, 10, 1, 8, wall)
    p.fill(9, -4, 7, 9, 1, 7, AIR)
    p.set(9, -5, 7, "Soil_Mud")
    for y in range(-4, -1):
        for (wx, wz) in ((8, 7), (10, 7), (9, 6), (9, 8)):
            p.set(wx, y, wz, p.pick(wall))
    p.gable(8, 6, 10, 8, 2, "Wood_Deadwood_Planks", "Wood_Deadwood_Planks_Half")
    p.set(8, 2, 6, "Wood_Deadwood_Beam")
    p.set(10, 2, 8, "Wood_Deadwood_Beam")
    for x in range(-13, -7, 2):
        for z in (6, 10):
            grave(p, x, z, r, "haunted")
    for tx, tz, size in ((-10, 13, "medium"), (12, 12, "medium"), (-12, 2, "small")):
        p.paste(dead_tree(r.randint(0, 1 << 30), size, webs=True), tx, 0, tz, min_y=0)
    p.scatter(-s + 2, 0, -1, s - 2, s - 2, 10, DEAD_PLANTS)
    p.scatter(-s + 2, 0, -1, s - 2, s - 2, 8, BONES)
    p.scatter(-s + 2, 0, -1, s - 2, s - 2, 6, GLOW_MUSHROOMS)
    p.ruin(78, keep_below=1, names={n for n, _ in wall})
    return p


# --- manoir du comte et crypte d'arrivée ------------------------------------------------------
#
# Blocs du pack (tools/generate_assets.py) : vitraux, gargouille, grille à lances, vantail de portail.
# Leurs modèles regardent vers +Z (le sud) sans rotation ; FACING donne la rotation (NESW) pour
# qu'ils regardent vers un autre côté.
GLASS_RED, GLASS_VIOLET = "Nakasar_Stained_Glass_Red", "Nakasar_Stained_Glass_Violet"
GARGOYLE, RAILING, GATE = "Nakasar_Gargoyle", "Nakasar_Iron_Railing", "Nakasar_Iron_Gate"
FACING = {"S": 0, "E": 1, "N": 2, "W": 3}
MANOR_WALL = [("Rock_Basalt_Brick", 8), ("Rock_Basalt_Brick_Decorative", 1), ("Rock_Basalt_Cobble", 1)]
MANOR_FLOOR = [("Rock_Basalt_Brick_Smooth", 5), ("Rock_Shale_Brick_Smooth", 2)]
MANOR_ROOF, MANOR_ROOF_HALF = "Rock_Slate_Cobble", "Rock_Slate_Cobble_Half"
MANOR_TRIM = "Rock_Basalt_Brick_Ornate"
WOOD_FLOOR = [("Wood_Deadwood_Planks", 4), ("Wood_Deadwood_Decorative", 1)]


def lancet(p, x, y, z, glass, height=3):
    """Fenêtre en ogive : vitrail de `height` blocs, clé de voûte ornée au-dessus, appui lisse dessous."""
    p.fill(x, y, z, x, y + height - 1, z, glass)
    p.set(x, y + height, z, MANOR_TRIM)
    p.set(x, y - 1, z, "Rock_Basalt_Brick_Smooth")


def rose_window(p, cx, cy, z=None, x=None):
    """Rosace 3 × 3 : couronne de vitraux rouges, cœur violet, dans le plan d'un mur (z ou x fixé)."""
    for a in (-1, 0, 1):
        for b in (-1, 0, 1):
            glass = GLASS_VIOLET if a == b == 0 else GLASS_RED
            if z is not None:
                p.set(cx + a, cy + b, z, glass)
            else:
                p.set(x, cy + b, cx + a, glass)


def perched_gargoyle(p, x, y, z, facing):
    """Gargouille sur un corbeau en saillie : (x, y - 1, z) doit toucher un mur par une face."""
    p.set(x, y - 1, z, MANOR_TRIM)
    p.set(x, y, z, GARGOYLE, FACING[facing])


def stairs_up(p, x0, x1, z_start, dz, rise, base, half, floor_y=-1):
    """Escalier droit en demi-dalles qui monte de `rise` blocs vers `dz` (± 1), sur x0..x1.

    Une case par demi-bloc ; la dernière marche arrive au niveau du sol de l'étage. Les marches sont
    pleines jusqu'au sol (pas de vide dessous). Renvoie la liste des z des marches.
    """
    zs = []
    for i in range(2 * rise):
        z = z_start + dz * i
        h2 = i + 1  # hauteur de la marche en demi-blocs au-dessus du sol
        for x in range(x0, x1 + 1):
            for y in range(floor_y + 1, floor_y + 1 + h2 // 2):
                p.set(x, y, z, base)
            if h2 % 2:
                p.set(x, floor_y + 1 + h2 // 2, z, half)
        zs.append(z)
    return zs


RETURN_PORTAL_Z = 3   # portail de retour, au sud du point d'arrivée (0, 0, 0) de la crypte


def spawn_crypt(seed):
    """Crypte fermée autour du point d'arrivée (centre en 0, 0, 0 : le joueur apparaît là).

    11 × 11, toit pentu en ardoise, porte au nord (vers le manoir), vitraux, cercueils le long des
    murs, gargouilles aux angles. Le portail de retour (`Portal_Return`) est posé ici, 3 blocs au
    sud du centre, et non par le jeu (`SpawnReturnPortal: false` dans PortalTypes) : posé par le
    jeu, il tombe sur le point d'arrivée, et un joueur dont l'écran charge encore au bout de
    15 secondes repart aussitôt chargé (il est déjà dans le portail).
    """
    p = Prefab(seed)
    r = p.rng
    h = 5
    p.clear(-8, 0, -12, 8, 14, 8)
    for x in range(-8, 9):
        for z in range(-12, 9):
            p.set(x, -1, z, p.pick(GROUND))
    p.floor(-5, -5, 5, 5, -1, STONE_FLOOR, FOUNDATION, depth=3)
    p.hollow(-5, 0, -5, 5, h, 5, STONE_WALL)
    for cx in (-5, 5):
        for cz in (-5, 5):
            p.set(cx, 0, cz, "Rock_Stone_Brick_Pillar_Base")
            p.fill(cx, 1, cz, cx, h, cz, "Rock_Stone_Brick_Pillar_Middle")
    p.steep_roof(-5, -5, 5, 5, h + 1, MANOR_ROOF, MANOR_ROOF_HALF, ridge="z", gable_wall=STONE_WALL)
    # porte au nord, lanternes et chemin vers le manoir
    p.set(0, 0, -5, "Furniture_Temple_Dark_Door", NORTH)
    p.set(0, 1, -5, AIR)
    p.set(0, 2, -5, "Rock_Stone_Brick_Ornate")
    p.fill(-1, 3, -5, 1, 3, -5, "Rock_Stone_Brick_Ornate")
    for x in (-2, 2):
        lantern_post(p, x, -7, 2)
    for z in range(-12, -5):
        for x in (-1, 0, 1):
            p.set(x, -1, z, p.pick(PATH))
    # vitraux : rosace au-dessus de la porte, ogives sur les côtés et derrière le portail
    rose_window(p, 0, 7, z=-5)
    for z in (-2, 2):
        p.fill(-5, 1, z, -5, 3, z, GLASS_VIOLET)
        p.fill(5, 1, z, 5, 3, z, GLASS_VIOLET)
    p.fill(0, 1, 5, 0, 3, 5, GLASS_RED)
    p.set(0, 4, 5, "Rock_Stone_Brick_Ornate")
    # intérieur : cercueils, bougies, braseros, toiles ; rien à moins de 2 blocs du centre
    for z in (-2, 3):                      # cercueils couchés le long des murs (2 blocs vers le nord)
        p.set(-4, 0, z, "Furniture_Ancient_Coffin", EAST)
    for z in (-3, 2):                      # (2 blocs vers le sud)
        p.set(4, 0, z, "Furniture_Ancient_Coffin", WEST)
    for x in (-4, 4):
        for z in (-4, 4):
            p.set(x, 0, z, p.pick(CANDLES))
    for x in (-3, 3):
        p.set(x, 0, 4, "Furniture_Temple_Dark_Brazier")
    p.set(-4, 0, 0, p.pick(BONES))
    p.set(4, 0, 0, "Deco_Bone_Skulls")
    for x, z in ((-4, -4), (4, 4), (-4, 4), (4, -4)):
        p.set(x, h, z, p.pick(WEBS))
    # gargouilles aux quatre angles, sur des corbeaux contre les pignons
    for x in (-5, 5):
        perched_gargoyle(p, x, h + 1, -6, "N")
        perched_gargoyle(p, x, h + 1, 6, "S")
    # abords : tombes et citrouilles
    for x, z in ((-7, -9), (7, -9), (-7, 7), (7, 7)):
        grave(p, x, z, r, r.choice(["haunted", "plain"]))
    p.scatter(-8, 0, -12, 8, 8, 6, DEAD_PLANTS)
    # point d'arrivée et portail de retour : 3 × 3 × 3 blocs libres chacun (le modèle du portail
    # déborde d'un bloc autour de sa case)
    p.fill(-1, 0, -1, 1, 2, 4, AIR)
    p.set(0, 0, RETURN_PORTAL_Z, "Portal_Return")
    return p


def vampire_manor(seed):
    """Manoir gothique du comte : domaine clos de grilles à lances, jardin, corps de logis à étage.

    Plan (nord = -Z, la façade regarde le sud, vers le point d'apparition) :
    - domaine 57 × 51 fermé par une grille sur muret, portail en fer forgé au sud entre deux piliers
      à gargouille ;
    - corps de logis 27 × 17 (rez-de-chaussée et étage), deux ailes en avancée avec pignon sur
      la façade, tour-porche au centre avec rosace et flèche, tour d'angle au nord-ouest ;
    - rez-de-chaussée : grand hall à piliers et tapis rouge jusqu'au trône (marqueur du comte ou
      de la comtesse), cheminées, salle à manger (aile ouest), bibliothèque (aile est), escalier ;
    - étage : chambre du comte, boudoir de la comtesse, galerie de tableaux, balcon sur le porche ;
    - crypte sous le hall, où veillent les rejetons ;
    - jardin : allée bordée de lanternes, roses de sang, tombes de famille, mausolée, arbres morts.
    """
    p = Prefab(seed)
    r = p.rng
    X, Z0, Z1 = 28, -25, 25
    p.clear(-X, 0, Z0, X, 34, Z1)
    for x in range(-X, X + 1):
        for z in range(Z0, Z1 + 1):
            p.set(x, -1, z, p.pick(GROUND))

    # --- clôture : muret de basalte, grille à lances, piliers ; portail au sud -------------------
    gate_half = 2
    for x in range(-X, X + 1):
        for z in (Z0, Z1):
            if z == Z1 and abs(x) <= gate_half:
                continue
            p.set(x, -1, z, p.pick(FOUNDATION))
            p.set(x, 0, z, "Rock_Basalt_Brick")
            p.set(x, 1, z, RAILING)
    for z in range(Z0, Z1 + 1):
        for x in (-X, X):
            p.set(x, -1, z, p.pick(FOUNDATION))
            p.set(x, 0, z, "Rock_Basalt_Brick")
            p.set(x, 1, z, RAILING)
    posts = [(x, z) for x in range(-X, X + 1, 7) for z in (Z0, Z1)] + [(x, z) for z in range(Z0, Z1 + 1, 6) for x in (-X, X)]
    for x, z in posts:
        if z == Z1 and abs(x) <= gate_half + 1:
            continue
        p.fill(x, 0, z, x, 2, z, "Rock_Basalt_Brick")
        p.set(x, 3, z, MANOR_TRIM)
        p.set(x, 4, z, "Deco_Lantern")
    for x in (-gate_half - 1, gate_half + 1):
        p.fill(x, 0, Z1, x, 3, Z1, "Rock_Basalt_Brick")
        p.set(x, 4, Z1, MANOR_TRIM)
        p.set(x, 5, Z1, GARGOYLE, FACING["S"])
    for x in range(-gate_half, gate_half + 1):
        p.set(x, 4, Z1, RAILING)  # imposte en fer forgé entre les piliers
        p.set(x, -1, Z1, p.pick(PATH))
    p.set(0, 3, Z1, "Deco_Lantern_Ceiling")
    # vantaux ouverts vers l'intérieur, contre les piliers
    for x in (-gate_half, gate_half):
        p.set(x, 0, Z1 - 1, GATE, FACING["E"])
    for x in (-gate_half - 2, gate_half + 2):
        p.set(x, 0, Z1 - 1, "Furniture_Village_Brazier")

    # --- corps de logis ---------------------------------------------------------------------------
    mx0, mx1, mz0, mz1 = -13, 13, -20, -4   # bloc principal
    wings = [(-13, -7), (7, 13)]           # ailes en avancée jusqu'à z = 2
    wz1 = 2
    tx0, tx1, tz0, tz1 = -3, 3, -5, 1      # tour-porche
    top = 10                               # dernier rang de mur (étage : sol en y = 5)
    upper = 5

    p.floor(mx0, mz0, mx1, mz1, -1, MANOR_FLOOR, FOUNDATION, depth=3)
    for wx0, wx1 in wings:
        p.floor(wx0, mz1, wx1, wz1, -1, MANOR_FLOOR, FOUNDATION, depth=3)
    p.floor(tx0, tz0, tx1, tz1, -1, MANOR_FLOOR, FOUNDATION, depth=3)
    p.hollow(mx0, 0, mz0, mx1, top, mz1, MANOR_WALL)
    for wx0, wx1 in wings:
        p.hollow(wx0, 0, mz1, wx1, top, wz1, MANOR_WALL)
        p.clear(wx0 + 1, 0, mz1, wx1 - 1, top, mz1)   # l'aile s'ouvre sur le corps de logis
    th = 22                                # dernier rang de mur de la tour-porche
    p.hollow(tx0, 0, tz0, tx1, th, tz1, MANOR_WALL)
    p.clear(tx0 + 1, 0, tz0, tx1 - 1, top, tz0)      # la tour s'ouvre sur le hall
    # contreforts sur la façade et les pignons
    for x in (mx0, mx1, -7, 7, tx0, tx1):
        for zz in (wz1 + 1,) if x in (mx0, mx1, -7, 7) else (tz1 + 1,):
            p.fill(x, 0, zz, x, 3, zz, "Rock_Basalt_Brick")
            p.set(x, 4, zz, "Rock_Basalt_Brick_Half")
    # planchers de l'étage (bois) et plafonds
    p.fill(mx0 + 1, upper, mz0 + 1, mx1 - 1, upper, mz1 - 1, WOOD_FLOOR)
    for wx0, wx1 in wings:
        p.fill(wx0 + 1, upper, mz1, wx1 - 1, upper, wz1 - 1, WOOD_FLOOR)
    p.fill(tx0 + 1, upper, tz0, tx1 - 1, upper, tz1 - 1, WOOD_FLOOR)
    p.fill(mx0 + 1, top + 1, mz0 + 1, mx1 - 1, top + 1, mz1 - 1, MANOR_FLOOR)
    for wx0, wx1 in wings:
        p.fill(wx0 + 1, top + 1, mz1, wx1 - 1, top + 1, wz1 - 1, MANOR_FLOOR)
    # corniche ornée en haut des murs, cordon entre les niveaux
    for x in range(mx0, mx1 + 1):
        for z in (mz0, mz1):
            p.set(x, top + 1, z, MANOR_TRIM)
            p.set(x, upper, z, "Rock_Basalt_Brick_Smooth")
    for z in range(mz0, wz1 + 1):
        for x in (mx0, mx1):
            p.set(x, top + 1, z, MANOR_TRIM)
            p.set(x, upper, z, "Rock_Basalt_Brick_Smooth")
    for wx0, wx1 in wings:
        for x in range(wx0, wx1 + 1):
            p.set(x, top + 1, wz1, MANOR_TRIM)
            p.set(x, upper, wz1, "Rock_Basalt_Brick_Smooth")
        for z in range(mz1, wz1 + 1):
            p.set(wx1 if wx0 < 0 else wx0, top + 1, z, MANOR_TRIM)

    # toits pentus en ardoise : corps de logis (faîte est-ouest), ailes (pignons au sud), tour
    p.steep_roof(mx0, mz0, mx1, mz1, top + 2, MANOR_ROOF, MANOR_ROOF_HALF, ridge="x", gable_wall=MANOR_WALL)
    for wx0, wx1 in wings:
        p.steep_roof(wx0, mz1 - 2, wx1, wz1, top + 2, MANOR_ROOF, MANOR_ROOF_HALF, ridge="z", gable_wall=MANOR_WALL)
        cx = (wx0 + wx1) // 2
        p.set(cx, top + 4, wz1, GLASS_RED)       # œil-de-bœuf dans le pignon
        p.set(cx, top + 3, wz1, GLASS_RED)
        for x in (wx0, wx1):
            perched_gargoyle(p, x, top + 2, wz1 + 1, "S")
    p.fill(tx0, th + 1, tz0, tx1, th + 1, tz1, MANOR_FLOOR)
    for x in (tx0, tx1):
        for z in (tz0, tz1):
            p.set(x, th + 2, z, GARGOYLE, FACING["S" if z == tz1 else "N"])
    p.spire(0, (tz0 + tz1) // 2, 2, th + 2, MANOR_ROOF)
    for y in (top + 2, 17):                          # planchers de la tour au-dessus du toit
        p.fill(tx0 + 1, y, tz0 + 1, tx1 - 1, y, tz1 - 1, WOOD_FLOOR)
    # cheminées
    for x in (-9, 9):
        p.fill(x, top + 2, mz0 + 3, x, top + 9, mz0 + 3, "Rock_Basalt_Brick")
        p.set(x, top + 10, mz0 + 3, "Rock_Basalt_Brick_Half")
    # tour d'angle au nord-ouest, flèche
    tower(p, mx0, mz0, 3, 18, MANOR_WALL, MANOR_FLOOR, MANOR_ROOF, MANOR_TRIM, spire=True)
    # la tour mord sur l'angle du hall : passage au rez-de-chaussée par son mur est, et à l'étage
    # depuis le palier de l'escalier par son mur sud
    p.clear(mx0 + 3, 0, mz0 + 1, mx0 + 3, 2, mz0 + 2)
    p.clear(mx0 + 1, upper + 1, mz0 + 3, mx0 + 2, upper + 3, mz0 + 3)

    # --- façade : porche, porte, balcon, fenêtres -----------------------------------------------
    p.clear(-1, 0, tz1, 1, 3, tz1)
    p.fill(-2, 4, tz1, 2, 4, tz1, MANOR_TRIM)
    p.set(0, 5, tz1, MANOR_TRIM)
    for x in (-1, 1):
        p.set(x, 0, tz1 - 1, GATE, FACING["E"])  # vantaux ouverts dans l'embrasure
    for x in (-3, 3):
        p.set(x, 0, tz1 + 3, "Rock_Basalt_Brick_Pillar_Base")
        p.fill(x, 1, tz1 + 3, x, 3, tz1 + 3, "Rock_Basalt_Brick_Pillar_Middle")
    p.fill(-3, 4, tz1 + 1, 3, 4, tz1 + 3, "Rock_Basalt_Brick_Smooth")   # dalle du porche = balcon
    for x in range(-3, 4):
        p.set(x, 5, tz1 + 3, RAILING)
    for z in (tz1 + 1, tz1 + 2):
        p.set(-3, 5, z, RAILING)
        p.set(3, 5, z, RAILING)
    p.set(0, 3, tz1 + 2, "Deco_Lantern_Ceiling")
    p.clear(0, upper + 1, tz1, 0, upper + 2, tz1)         # porte-fenêtre sur le balcon
    p.set(0, upper + 3, tz1, MANOR_TRIM)
    rose_window(p, 0, 14, z=tz1)
    for x in (-2, 2):
        lancet(p, x, upper + 1, tz1, GLASS_VIOLET)
        lancet(p, x, 13, tz1, GLASS_VIOLET, height=3)
    for x in (-1, 1):
        lancet(p, x, 18, tz1, GLASS_RED, height=3)  # baies hautes de la tour
    for x in (tx0, tx1):
        lancet(p, x, 18, tz1 - 2, GLASS_RED, height=3)
    for wx0, wx1 in wings:
        for x in range(wx0 + 2, wx1 - 1, 2):
            lancet(p, x, 1, wz1, GLASS_RED)
            lancet(p, x, upper + 2, wz1, GLASS_RED)
        side = wx0 if wx0 < 0 else wx1
        for z in (mz1 + 2, wz1 - 2):
            lancet(p, side, 1, z, GLASS_VIOLET)
            lancet(p, side, upper + 2, z, GLASS_VIOLET)
    for x in (-5, 5):                                 # façade entre les ailes et la tour
        lancet(p, x, 1, mz1, GLASS_RED)
        lancet(p, x, upper + 2, mz1, GLASS_RED)
    for x in range(mx0 + 3, mx1 - 2, 4):              # façade nord
        lancet(p, x, 1, mz0, GLASS_VIOLET)
        lancet(p, x, upper + 2, mz0, GLASS_VIOLET)
    for z in range(mz0 + 4, mz1 - 1, 4):              # pignons est et ouest
        lancet(p, mx1, 1, z, GLASS_RED)
        lancet(p, mx1, upper + 2, z, GLASS_RED)
        if z > mz0 + 4:
            lancet(p, mx0, 1, z, GLASS_RED)
            lancet(p, mx0, upper + 2, z, GLASS_RED)
    rose_window(p, (mz0 + mz1) // 2, top + 4, x=mx1)
    rose_window(p, (mz0 + mz1) // 2, top + 4, x=mx0)

    # --- intérieur : cloisons ------------------------------------------------------------------------
    # Le hall occupe le centre (x -6..6) sur les deux niveaux ; de chaque côté, deux pièces de 5 blocs
    # de large séparées par un mur en z = -10 (les ailes prolongent celles du sud jusqu'à la façade).
    for y0, y1 in ((0, upper - 1), (upper + 1, top)):
        for side in (-1, 1):
            px = 7 * side
            p.fill(px, y0, mz0 + 1, px, y1, mz1 - 1, MANOR_WALL)
            for x in range(8, 13):
                p.set(x * side, y0, -10, p.pick(MANOR_WALL))
                for y in range(y0 + 1, y1 + 1):
                    p.set(x * side, y, -10, p.pick(MANOR_WALL))
    doors = [(-7, 0, -14), (-7, 0, -7), (7, 0, -14), (7, 0, -7),            # cuisine, salle à manger, cabinet, bibliothèque
             (-7, upper + 1, -13), (-7, upper + 1, -6), (7, upper + 1, -13), (7, upper + 1, -6)]
    for dx, dy, dz in doors:
        p.clear(dx, dy, dz, dx, dy + 2, dz + 1)
        p.set(dx, dy + 3, dz, MANOR_TRIM)
        p.set(dx, dy + 3, dz + 1, MANOR_TRIM)

    # --- hall : tapis, piliers, trône, escaliers ---------------------------------------------------
    for z in range(mz0 + 1, tz1 + 1):                # tapis rouge de la porte au trône
        for x in (-1, 0, 1):
            p.set(x, -1, z, "Cloth_Block_Wool_Red")
    for z in (-16, -12, -8):                         # piliers du hall
        for x in (-3, 3):
            p.set(x, 0, z, "Rock_Basalt_Brick_Pillar_Base")
            p.fill(x, 1, z, x, upper - 1, z, "Rock_Basalt_Brick_Pillar_Middle")
    for z in (-13, -8):
        p.set(0, upper - 1, z, "Furniture_Feran_Chandelier")
    # trône sur une estrade, au fond du hall
    p.fill(-3, 0, mz0 + 1, 3, 0, mz0 + 2, "Rock_Basalt_Brick_Smooth")
    p.fill(-1, 1, mz0 + 1, 1, 1, mz0 + 1, "Cloth_Block_Wool_Red")
    p.fill(-1, 2, mz0 + 1, 1, 3, mz0 + 1, MANOR_TRIM)
    p.set(0, 4, mz0 + 1, "Furniture_Outlander_Banner", SOUTH)
    p.set(0, 1, mz0 + 2, "Furniture_Royal_Magic_Chair", SOUTH)
    for x in (-3, 3):
        p.set(x, 1, mz0 + 1, "Furniture_Temple_Dark_Statue", SOUTH)
        p.set(x, 0, mz0 + 3, "Furniture_Temple_Dark_Brazier")
    # le comte ou la comtesse attend devant son trône (marqueur invisible du mod)
    p.set(0, 0, mz0 + 5, "Nakasar_Spawner_Vampire_Count")
    # escalier d'honneur le long du mur ouest du hall, qui monte vers le nord jusqu'à la galerie
    sx0, sx1 = -6, -5
    zs = stairs_up(p, sx0, sx1, -6, -1, upper + 1, "Rock_Basalt_Brick", "Rock_Basalt_Brick_Half")
    for i, z in enumerate(zs):
        if (i + 1) / 2 >= 2:                         # trémie dans le plancher au-dessus des marches
            for x in (sx0, sx1):
                p.set(x, upper, z, AIR)
        if 3 <= i < len(zs) - 1:
            p.set(sx1 + 1, upper + 1, z, RAILING)       # garde-corps de la galerie autour de la trémie
    p.set(sx1 + 1, upper + 1, zs[2], RAILING)
    for x in (sx0, sx1):
        p.set(x, upper + 1, zs[2] + 1, RAILING)
    # escalier de la crypte, côté est du hall, derrière une balustrade
    depth = 5
    stairs_down(p, (5, -6), (0, -1), depth, "Rock_Basalt_Brick", "Rock_Basalt_Brick_Half", MANOR_WALL, width=2)
    for z in range(-15, -7):
        p.set(4, 0, z, RAILING)

    # --- cuisine (nord-ouest) ----------------------------------------------------------------------
    p.set(-12, 0, -15, "Bench_Cooking", EAST)
    p.set(-12, 0, -12, "Bench_Furnace", EAST)
    p.set(-12, 0, -16, "Furniture_Village_Shelf_Full", EAST)
    p.set(-10, 0, -14, "Furniture_Village_Table")
    for x, z, item in ((-10, -14, "Deco_Plate"), (-9, -14, "Deco_Mug"), (-10, -13, "Deco_Bucket"), (-9, -13, "Deco_Plate")):
        p.set(x, 1, z, item, SOUTH)
    for x, z in ((-9, -19), (-8, -19)):
        p.set(x, 0, z, "Furniture_Ancient_Barrel")
    p.set(-8, 0, -18, "Furniture_Ancient_Crate")
    p.set(-9, 0, -18, "Furniture_Ancient_Sack")
    p.set(-8, 1, -19, "Furniture_Ancient_Sack")
    p.chest(-8, 0, -11, "Furniture_Village_Chest_Small", WEST, LOOT_MANOR_KITCHEN)
    p.set(-10, upper - 1, -12, "Deco_Lantern_Ceiling")

    # --- salle à manger (ouest et aile ouest) -------------------------------------------------------
    for z in (-8, -6, -4, -2):                       # longue table : quatre tables de 2 × 2 bout à bout
        p.set(-11, 0, z, "Furniture_Temple_Dark_Table")
    for z in range(-8, 0):
        p.set(-12, 0, z, "Furniture_Royal_Magic_Chair", EAST)
        p.set(-9, 0, z, "Furniture_Royal_Magic_Chair", WEST)
    p.set(-11, 0, -9, "Furniture_Royal_Magic_Chair", SOUTH)   # bouts de table : le comte, la comtesse
    p.set(-10, 0, 0, "Furniture_Royal_Magic_Chair", NORTH)
    for z in (-7, -4, -1):
        p.set(-11 + (z % 2), 1, z, p.pick(CANDLES))
    for x, z in ((-10, -6), (-11, -3)):              # sur la table (x -11..-10), entre les bougies
        p.set(x, 1, z, r.choice(["Deco_Plate", "Deco_Tankard"]), SOUTH)
    for z in (-6, -2):
        p.set(-10, upper - 1, z, "Furniture_Tavern_Chandelier")
    p.set(-9, 0, 1, "Furniture_Village_Counter", NORTH)      # desserte contre la façade
    p.set(-9, 1, 1, "Deco_Tankard", NORTH)

    # --- cabinet du comte (nord-est) : cheminée, bureau, coffre ----------------------------------------
    hx = 9
    p.clear(hx - 1, 0, mz0, hx + 1, 1, mz0)
    p.set(hx, -1, mz0, "Rock_Basalt_Brick_Smooth")
    p.set(hx, 0, mz0, "Furniture_Temple_Dark_Brazier")
    p.fill(hx - 2, 2, mz0 + 1, hx + 2, 2, mz0 + 1, MANOR_TRIM)
    p.fill(hx - 2, 0, mz0 + 1, hx - 2, 1, mz0 + 1, "Rock_Basalt_Brick")
    p.fill(hx + 2, 0, mz0 + 1, hx + 2, 1, mz0 + 1, "Rock_Basalt_Brick")
    p.set(hx, 3, mz0 + 1, "Furniture_Ancient_Painting", SOUTH)
    p.set(hx - 1, 3, mz0 + 1, p.pick(CANDLES))
    p.set(hx + 1, 3, mz0 + 1, p.pick(CANDLES))
    p.set(11, 0, -15, "Furniture_Human_Ruins_Desk", SOUTH)
    p.set(10, 0, -14, "Furniture_Royal_Magic_Chair", NORTH)
    p.set(11, 1, -15, "Deco_Map", SOUTH)
    p.set(10, 1, -15, "Deco_Inkwell", SOUTH)
    p.set(12, 0, -12, "Furniture_Ancient_Bookshelf", WEST)
    p.set(12, 1, -12, "Furniture_Ancient_Bookshelf", WEST)
    p.set(9, 0, -11, "Furniture_Royal_Magic_Couch", SOUTH)
    p.set(10, upper - 1, -13, "Deco_Lantern_Ceiling")

    # --- bibliothèque (est et aile est) ----------------------------------------------------------------
    for z in range(-9, 2):
        if z not in (-5, -4):
            p.set(12, 0, z, "Furniture_Ancient_Bookshelf", WEST)
            p.set(12, 1, z, "Furniture_Ancient_Bookshelf", WEST)
    for x in range(8, 12):
        p.set(x, 0, -9, "Furniture_Human_Ruins_Bookshelf", SOUTH)
        p.set(x, 1, -9, "Furniture_Human_Ruins_Bookshelf", SOUTH)
    p.set(12, 0, -5, "Furniture_Temple_Dark_Statue", WEST)    # statue entre deux rayonnages
    p.set(9, 0, -5, "Furniture_Royal_Magic_Table")
    p.set(8, 0, -5, "Furniture_Royal_Magic_Chair", EAST)
    p.set(11, 0, -4, "Furniture_Royal_Magic_Chair", WEST)
    p.set(9, 1, -5, "Deco_Book_Pile_Small", SOUTH)
    p.set(10, 1, -4, p.pick(CANDLES))
    p.set(10, 1, -5, "Deco_Scroll", EAST)
    p.set(8, 0, 0, "Deco_Book_Pile_Large", SOUTH)
    p.chest(8, 0, 1, "Furniture_Ancient_Chest_Small", EAST, LOOT_MANOR_LIBRARY)
    p.set(10, upper - 1, -1, "Furniture_Tavern_Chandelier")

    # --- crypte sous le hall ----------------------------------------------------------------------
    cy0 = -depth - 1
    cx0, cx1, cz0, cz1 = -10, 10, mz0 + 1, mz1 - 1
    for x in range(cx0 - 1, cx1 + 2):
        for z in range(cz0 - 1, cz1 + 2):
            p.set(x, cy0, z, p.pick(MANOR_WALL))
            p.set(x, cy0 - 1, z, p.pick(FOUNDATION))
            for y in range(cy0 + 1, -1):
                if x in (cx0 - 1, cx1 + 1) or z in (cz0 - 1, cz1 + 1):
                    p.set(x, y, z, p.pick(MANOR_WALL))
    p.floor(cx0, cz0, cx1, cz1, cy0, MANOR_FLOOR)
    for x in range(cx0, cx1 + 1):
        for z in range(cz0, cz1 + 1):
            for y in range(cy0 + 1, -1):
                if not (5 <= x <= 6 and -15 <= z <= -6):   # l'escalier de la crypte
                    p.set(x, y, z, AIR)
    for x in range(cx0 + 1, 3, 3):
        p.set(x, cy0 + 1, cz0 + 1, r.choice(["Furniture_Temple_Dark_Coffin", "Furniture_Ancient_Coffin"]), SOUTH)
        p.set(x + 1, cy0 + 1, cz1 - 1, r.choice(["Furniture_Temple_Dark_Coffin", "Furniture_Ancient_Coffin"]), NORTH)
    mid = (cz0 + cz1) // 2
    p.chest(0, cy0 + 1, mid, "Furniture_Ancient_Chest_Large", SOUTH, LOOT_MANOR_TREASURE)
    for x in (-2, 1):
        p.set(x, cy0 + 1, mid, "Deco_Treasure_Pile_Small")
    # ses rejetons gardent la crypte (marqueurs invisibles du mod)
    for x in (cx0 + 2, 2):
        p.set(x, cy0 + 1, mid + 1, "Nakasar_Spawner_Vampire_Spawn")
    for px in (-5, 3):
        p.fill(px, cy0 + 1, mid - 2, px, -2, mid - 2, "Rock_Basalt_Brick_Pillar_Middle")
        p.set(px, cy0 + 1, mid - 3, "Furniture_Temple_Dark_Brazier")
    p.scatter(cx0 + 1, cy0 + 1, cz0 + 1, 3, cz1 - 1, 8, CANDLES)
    p.scatter(cx0 + 1, cy0 + 1, cz0 + 1, 3, cz1 - 1, 5, BONES)

    # --- étage -------------------------------------------------------------------------------------
    y = upper + 1
    # galerie au-dessus du hall : tableaux face aux fenêtres, statues, tapis, salon
    for x in (-2, 3):
        p.set(x, y + 1, mz0 + 1, "Furniture_Village_Painting_2x2", SOUTH)
    for x in (-4, 5):
        p.set(x, y, mz0 + 1, "Furniture_Temple_Dark_Statue", SOUTH)
    for z in range(mz0 + 2, mz1 + 1):
        p.set(0, y - 1, z, "Cloth_Block_Wool_Red")
    p.set(4, y, -15, "Furniture_Royal_Magic_Couch", WEST)
    p.set(3, y, -13, "Furniture_Royal_Magic_Table")
    p.set(3, y + 1, -13, p.pick(CANDLES))
    p.set(0, top, -13, "Furniture_Feran_Chandelier")
    p.set(0, top, -7, "Furniture_Feran_Chandelier")
    # chambre de la comtesse (nord-ouest) : lit, coiffeuse, armoire, coffre à bijoux
    p.set(-12, y, -16, "Furniture_Temple_Dark_Bed", SOUTH)
    p.set(-12, y, -12, "Furniture_Royal_Magic_Wardrobe", EAST)
    p.set(-9, y, -16, "Furniture_Royal_Magic_Table")
    p.set(-9, y + 1, -16, "Furniture_Royal_Magic_Potion_Glow")
    p.set(-8, y + 1, -15, "Deco_Potion")
    p.set(-10, y, -16, "Furniture_Village_Stool")
    p.set(-10, y, -13, "Furniture_Royal_Magic_Carpet")
    p.chest(-8, y, -11, "Furniture_Royal_Magic_Chest_Small", WEST, LOOT_MANOR_BEDROOM)
    p.set(-10, top, -14, "Furniture_Royal_Magic_Potion_Glow_Ceiling")
    # laboratoire d'alchimie (ouest et aile ouest)
    p.set(-12, y, -8, "Bench_Alchemy", EAST)
    p.set(-12, y, -4, "Alchemy_Cauldron_Big")
    p.set(-10, y, -5, "Alchemy_Cauldron")
    p.set(-9, y, 1, "Bench_Arcane", NORTH)
    p.set(-10, y, -2, "Furniture_Temple_Dark_Table")
    for x, z, item in ((-10, -2, "Deco_Potion"), (-9, -2, "Rock_Crystal_Red_Small"), (-10, -1, "Deco_Book_Pile_Small"), (-9, -1, "Deco_Bone_Skulls")):
        p.set(x, y + 1, z, item, SOUTH)
    for z in (-1, 0):
        p.set(-12, y, z, "Furniture_Temple_Dark_Shelf", EAST)
        p.set(-12, y + 1, z, "Deco_Potion", EAST)
    p.chest(-8, y, -9, "Furniture_Temple_Dark_Chest_Small", WEST, LOOT_MANOR_ALCHEMY)
    p.set(-10, top, -6, "Furniture_Royal_Magic_Potion_Glow_Ceiling")
    p.set(-10, top, -1, "Furniture_Royal_Magic_Potion_Glow_Ceiling")
    # chambre du comte (nord-est) : lit à baldaquin, cercueil au pied, armoire, coffre
    p.set(9, y, -19, "Furniture_Royal_Magic_Bed", SOUTH)
    p.set(9, y, -13, "Furniture_Temple_Dark_Coffin", SOUTH)
    p.set(12, y, -14, "Furniture_Royal_Magic_Wardrobe", WEST)
    p.chest(12, y, -11, "Furniture_Royal_Magic_Chest_Large", WEST, LOOT_MANOR_BEDROOM)
    p.set(8, y, -19, p.pick(CANDLES))
    p.set(10, top, -14, "Furniture_Feran_Chandelier")
    # atelier (est et aile est) : établi, forge d'armes, métier à tisser, caisses
    p.set(12, y, -8, "Bench_WorkBench", WEST)
    p.set(12, y, -5, "Bench_Weapon", WEST)
    p.set(10, y, 1, "Bench_Loom", NORTH)
    p.set(8, y, -3, "Furniture_Village_Table")
    p.set(8, y + 1, -3, "Deco_Bucket", SOUTH)
    p.set(8, y, 1, "Furniture_Ancient_Crate")
    p.set(8, y + 1, 1, "Furniture_Ancient_Crate")
    p.set(12, y, 1, "Furniture_Ancient_Barrel")
    p.chest(8, y, -9, "Furniture_Village_Chest_Small", EAST, LOOT_MANOR_WORKSHOP)
    p.set(10, top, -4, "Deco_Lantern_Ceiling")
    # combles : quelques toiles d'araignée sous le toit
    for _ in range(12):
        x, z = r.randint(mx0 + 1, mx1 - 1), r.randint(mz0 + 1, mz1 - 1)
        for yy in range(top + 2, top + 14):
            if p.get(x, yy, z) not in (None, AIR):
                if p.free(x, yy - 1, z) and yy - 1 > top + 1:
                    p.set(x, yy - 1, z, p.pick(WEBS))
                break

    # --- jardin -------------------------------------------------------------------------------------
    for z in range(tz1 + 1, Z1):                     # allée de la grille au porche
        for x in (-1, 0, 1):
            p.set(x, -1, z, p.pick(PATH))
        if z % 4 == 0 and z > tz1 + 4:
            for x in (-3, 3):
                lantern_post(p, x, z, 2)
    for x in (-5, 5):                                # statues sur socle et gargouilles dans l'allée
        p.set(x, 0, 14, "Rock_Basalt_Brick")
        p.set(x, 1, 14, MANOR_TRIM)
        p.set(x, 2, 14, GARGOYLE, FACING["E" if x < 0 else "W"])
    for x0b in (-24, 9):                              # roseraies de sang
        for x in range(x0b, x0b + 15):
            for z in range(7, 20):
                if (x % 3 == 0 and z % 2 == 0) and abs(x) > 6 and r.random() < 0.7:
                    p.set(x, -1, z, "Soil_Dirt")
                    p.set(x, 0, z, r.choice(["Plant_Crop_Health1", "Plant_Petals_Blood", "Plant_Crop_Health2", "Plant_Petals_Blood"]))
    for tx, tz, hanging in ((-18, 4, "noose"), (19, 4, "cage")):
        p.paste(dead_tree(r.randint(0, 1 << 30), "medium", species="Burnt", hanging=hanging), tx, 0, tz, min_y=0)
    # tombes de famille à l'est, mausolée à l'ouest, derrière le logis
    for x in range(17, 26, 3):
        for z in (-20, -16, -12):
            grave(p, x, z, r, r.choice(["undead", "haunted"]))
    mausoleum(p, -25, -21, r, door_south=True)
    p.scatter(-X + 2, 0, Z0 + 2, X - 2, Z1 - 2, 10, BONES)
    p.scatter(-X + 2, 0, Z0 + 2, X - 2, Z1 - 2, 20, DEAD_PLANTS)
    return p


# --- domaine du comte : maisons, village, fermes, poste de garde ---------------------------------
#
# Maisons à la manière du village brûlé vanilla (Monuments/Encounter/Zone4/Tier4/Village) :
# rez-de-chaussée en moellons, étage à colombages, toit à deux pans en blocs de toit du jeu (45°),
# fenêtres et portes « Ancient », mobilier contre les murs et jamais imbriqué (Prefab.fits).

TIMBER = [("Wood_Deadwood_Planks", 6), ("Wood_Deadwood_Decorative", 1)]
COBBLE_WALL = [("Rock_Stone_Cobble", 6), ("Rock_Stone_Cobble_Mossy", 2), ("Rock_Stone", 1)]
WILD_GROWTH = [("Plant_Grass_Gnarled", 4), ("Plant_Grass_Gnarled_Tall", 2), ("Plant_Bush_Dead", 2), ("Plant_Bush_Dead_Tall", 1),
               ("Plant_Bramble_Dead_Twisted", 1), ("Plant_Grass_Dry_Tall", 2)]
RUBBLE = [("Deco_Trash_Pile_Small", 3), ("Rock_Stone_Cobble_Half", 2), ("Wood_Deadwood_Planks_Half", 2), ("Deco_Trash_Pile_Large", 1)]
BLOOD = "Plant_Petals_Blood"
WHEAT = "*Plant_Crop_Wheat_Block_State_Definitions_StageFinal"
WHEAT_YOUNG = "*Plant_Crop_Wheat_Block_State_Definitions_Stage3"
WHEAT_BURNT = "Plant_Crop_Wheat_Stage_4_Burnt"
DOOR_ROT = {NORTH: 0, SOUTH: 0, EAST: 1, WEST: 1}   # portes et fenêtres : 0 dans un mur le long de x


def roof(p, x0, z0, x1, z1, y, mat="Wood_Deadwood", ridge="x", gable=None, overhang=1, slope=None):
    """Toit à deux pans en blocs de toit du jeu (pente 45°) sur des murs dont le haut est en y - 1.

    `ridge` = axe du faîte. La rangée au-dessus d'un mur est en y, le débord en y - 1, chaque rangée
    vers le faîte monte d'un bloc ; le faîte impair reçoit le bloc « Topper ». Les pignons sont
    remplis avec `gable`. Rotation des pentes : 0 descend vers +Z (sud), 2 vers le nord, 1 vers l'est,
    3 vers l'ouest (lu dans les maisons vanilla). `slope` remplace le bloc de pente (toile de tente) :
    largeur paire alors, il n'y a pas de « Topper » pour toutes les toiles. Renvoie la hauteur du faîte.
    """
    if slope:
        span = (x1 - x0) if ridge == "z" else (z1 - z0)
        assert span % 2 == 1, f"{slope} : largeur paire obligatoire, pas de faîtage pour cette toile"
    slope, topper = slope or f"{mat}_Roof", f"*{mat}_Roof_State_Definitions_Topper"
    if ridge == "x":
        lo, hi, a0, a1, low_rot, high_rot, top_rot = z0, z1, x0, x1, NORTH, SOUTH, 0
        at = lambda u, v: (v, u)
    else:
        lo, hi, a0, a1, low_rot, high_rot, top_rot = x0, x1, z0, z1, WEST, EAST, 1
        at = lambda u, v: (u, v)
    height = lambda u: y + min(u - lo, hi - u)
    peak = y
    for u in range(lo - overhang, hi + overhang + 1):
        h = height(u)
        peak = max(peak, h)
        if u - lo < hi - u:
            name, rot = slope, low_rot
        elif u - lo > hi - u:
            name, rot = slope, high_rot
        else:
            name, rot = topper, top_rot
        for v in range(a0 - overhang, a1 + overhang + 1):
            x, z = at(u, v)
            p.set(x, h, z, name, rot)
        if gable and lo <= u <= hi:
            for v in (a0, a1):
                x, z = at(u, v)
                for k in range(y, h):
                    p.set(x, k, z, p.pick(gable))
    return peak


def wall_cells(x0, z0, x1, z1):
    """Cases au pied des murs intérieurs d'une pièce, avec l'orientation qui regarde la pièce."""
    out = []
    for x in range(x0, x1 + 1):
        out.append((x, z0, SOUTH))
        out.append((x, z1, NORTH))
    for z in range(z0 + 1, z1):
        out.append((x0, z, EAST))
        out.append((x1, z, WEST))
    return out


def place_along_walls(p, room, y, name, keep=(), tries=None, loot=None):
    """Pose `name` contre un mur de la pièce `room` = (x0, z0, x1, z1), à un endroit libre."""
    cells = wall_cells(*room)
    p.rng.shuffle(cells)
    taken = p.reserved() | set(keep)
    for x, z, rot in cells[:tries]:
        if p.fits(x, y, z, name, rot, taken):
            if loot:
                p.chest(x, y, z, name, rot, loot)
            else:
                p.set(x, y, z, name, rot)
            return (x, z, rot)
    return None


def dining_table(p, room, y, table, chair, keep=()):
    """Table de 2 × 2 au milieu de la pièce, chaises tournées vers elle, bougie ou assiette dessus."""
    x0, z0, x1, z1 = room
    spots = [(x, z) for x in range(x0 + 1, x1 - 1) for z in range(z0 + 1, z1 - 1)]
    p.rng.shuffle(spots)
    taken = p.reserved() | set(keep)
    for tx, tz in spots:
        if not p.fits(tx, y, tz, table, 0, taken):
            continue
        p.set(tx, y, tz, table)
        for cx, cz, rot in ((tx - 1, tz, EAST), (tx + 2, tz + 1, WEST), (tx, tz + 2, NORTH), (tx + 1, tz - 1, SOUTH)):
            if p.rng.random() < 0.8 and x0 <= cx <= x1 and z0 <= cz <= z1 and p.fits(cx, y, cz, chair, rot, taken | set(keep)):
                p.set(cx, y, cz, chair, rot)
        p.set(tx, y + 1, tz, p.pick(CANDLES))
        p.set(tx + 1, y + 1, tz + 1, p.rng.choice(["Deco_Plate", "Deco_Mug", "Deco_Tankard"]), SOUTH)
        return (tx, tz)
    return None


def house(p, x0, z0, w, d, door, floors=1, kind="home", loot=LOOT_VILLAGE, wood="Wood_Deadwood"):
    """Maison de `w` × `d` (murs compris) dont la porte donne vers `door` (NORTH, SOUTH, EAST, WEST).

    Rez-de-chaussée en moellons, étage à colombages, poutres d'angle, toit de bois dans le sens de
    la longueur, cheminée sur un pignon. `kind` : "home" (pièce à vivre, lit, coffre), "barn"
    (grange : foin, caisses, auge), "smithy" (forge). Renvoie la case devant la porte.
    """
    x1, z1 = x0 + w - 1, z0 + d - 1
    r = p.rng
    planks = [(f"{wood}_Planks", 6), (f"{wood}_Decorative", 1)]
    beam = f"{wood}_Beam"
    top = 4 * floors - 1
    p.clear(x0 - 1, 0, z0 - 1, x1 + 1, top + w // 2 + d // 2 + 4, z1 + 1)
    p.floor(x0, z0, x1, z1, -1, f"{wood}_Planks", FOUNDATION, depth=2)
    p.hollow(x0, 0, z0, x1, 3, z1, COBBLE_WALL)
    if floors > 1:
        p.hollow(x0, 4, z0, x1, top, z1, planks)
        p.fill(x0 + 1, 4, z0 + 1, x1 - 1, 4, z1 - 1, f"{wood}_Planks")
        for x in range(x0, x1 + 1):                 # sablière en saillie entre les niveaux
            for z in (z0, z1):
                p.set(x, 4, z, beam)
        for z in range(z0, z1 + 1):
            for x in (x0, x1):
                p.set(x, 4, z, beam)
    for cx in (x0, x1):
        for cz in (z0, z1):
            p.fill(cx, 0, cz, cx, top, cz, beam)
    # toit dans le sens de la longueur, pignons en planches
    ridge = "x" if w >= d else "z"
    peak = roof(p, x0, z0, x1, z1, top + 1, wood, ridge, gable=planks)
    # porte au milieu du mur, petit perron en pavés
    dx, dz = {NORTH: (0, -1), SOUTH: (0, 1), EAST: (1, 0), WEST: (-1, 0)}[door]
    if door in (NORTH, SOUTH):
        px, pz = (x0 + x1) // 2, z0 if door == NORTH else z1
    else:
        px, pz = x0 if door == WEST else x1, (z0 + z1) // 2
    p.clear(px, 0, pz, px, 1, pz)
    p.set(px, 0, pz, "Furniture_Ancient_Door", DOOR_ROT[door])
    p.set(px, 2, pz, beam)
    p.set(px + dx, -1, pz + dz, "Rock_Stone_Cobble")
    inside = (px - dx, pz - dz)
    # fenêtres tous les trois blocs, aux deux niveaux, sauf à côté de la porte
    for level in range(floors):
        wy = 4 * level + 1 + (level > 0)
        for x in range(x0 + 2, x1 - 1, 3):
            for z in (z0, z1):
                if abs(x - px) > 1 or z != pz:
                    p.set(x, wy, z, "Furniture_Ancient_Window", 0)
        for z in range(z0 + 2, z1 - 1, 3):
            for x in (x0, x1):
                if abs(z - pz) > 1 or x != px:
                    p.set(x, wy, z, "Furniture_Ancient_Window", 1)
    # cheminée contre le pignon opposé à la porte (ou le pignon est)
    if ridge == "x":
        chx, chz = (x0 - 1 if door != WEST else x1 + 1), (z0 + z1) // 2
    else:
        chx, chz = (x0 + x1) // 2, (z0 - 1 if door != NORTH else z1 + 1)
    p.fill(chx, -1, chz, chx, peak + 1, chz, COBBLE_WALL)
    p.set(chx, peak + 2, chz, "Rock_Stone_Cobble_Half")
    # mobilier
    room = (x0 + 1, z0 + 1, x1 - 1, z1 - 1)
    keep = {inside, (inside[0] - dx, inside[1] - dz)}
    if floors > 1:                                     # échelle et trémie vers l'étage
        lx, lz = (x1 - 1, z0 + 1) if door != EAST else (x0 + 1, z0 + 1)
        lrot = WEST if lx == x1 - 1 else EAST
        for y in range(0, 5):
            p.set(lx, y, lz, "Furniture_Ancient_Ladder", lrot)
        keep |= {(lx, lz), (lx - (1 if lrot == WEST else -1), lz)}
    if kind == "barn":
        for _ in range(4):
            place_along_walls(p, room, 0, "Ingredient_Hay", keep)
        place_along_walls(p, room, 0, "Bench_Trough", keep)
        for name in ("Furniture_Ancient_Crate", "Furniture_Ancient_Sack", "Furniture_Ancient_Barrel", "Furniture_Ancient_Crate"):
            place_along_walls(p, room, 0, name, keep)
        place_along_walls(p, room, 0, "Furniture_Crude_Chest_Small", keep, loot=loot)
    elif kind == "smithy":
        place_along_walls(p, room, 0, "Bench_Furnace", keep)
        place_along_walls(p, room, 0, "Bench_Weapon", keep)
        place_along_walls(p, room, 0, "Furniture_Ancient_Barrel", keep)
        place_along_walls(p, room, 0, "Furniture_Ancient_Chest_Large", keep, loot=loot)
    else:
        place_along_walls(p, room, 0, "Bench_Cooking", keep)
        dining_table(p, room, 0, "Furniture_Ancient_Table", "Furniture_Ancient_Chair", keep)
        place_along_walls(p, room, 0, "Furniture_Ancient_Barrel", keep)
        place_along_walls(p, room, 0, "Furniture_Village_Shelf_Full", keep)
        bed_y = 5 if floors > 1 else 0
        place_along_walls(p, room, bed_y, "Furniture_Ancient_Bed", keep)
        place_along_walls(p, room, bed_y, "Furniture_Ancient_Wardrobe", keep)
        place_along_walls(p, room, bed_y, "Furniture_Village_Chest_Small", keep, loot=loot)
        if floors > 1:
            place_along_walls(p, room, bed_y, "Furniture_Ancient_Bed", keep)
            place_along_walls(p, room, 0, "Furniture_Ancient_Crate", keep)
    hang_lantern(p, (x0 + x1) // 2, top, (z0 + z1) // 2)
    return (px + dx, pz + dz)


def well(p, cx, cz):
    """Puits de pierre 3 × 3, margelle, deux poteaux et un toit, seau sur le bord."""
    for x in range(cx - 1, cx + 2):
        for z in range(cz - 1, cz + 2):
            if (x, z) != (cx, cz):
                p.set(x, -1, z, "Rock_Stone_Cobble")
                p.set(x, 0, z, p.pick(COBBLE_WALL))
    for y in range(-6, 1):
        p.set(cx, y, cz, AIR)
    p.set(cx, -7, cz, "Soil_Mud")
    for x in (cx - 1, cx + 1):
        p.fill(x, 1, cz, x, 2, cz, "Wood_Deadwood_Beam")
    roof(p, cx - 1, cz, cx + 1, cz, 3, "Wood_Deadwood", "z", overhang=0)
    p.set(cx, 3, cz, "Wood_Deadwood_Beam", ALONG_X)          # treuil sous le faîtage
    p.set(cx, 1, cz - 1, "Deco_Bucket")


def field(p, x0, z0, x1, z1, crop="wheat", state="fine"):
    """Champ labouré : rangs est-ouest, rigole entre deux rangs. `state` fine / wild / burnt."""
    r = p.rng
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            furrow = (z - z0) % 4 == 3
            if state == "burnt":
                p.set(x, -1, z, "Soil_Ash" if furrow or r.random() < 0.3 else "Soil_Dirt_Burnt")
                if not furrow and r.random() < 0.75:
                    p.set(x, 0, z, WHEAT_BURNT)
                continue
            p.set(x, -1, z, "Soil_Dirt_Burnt" if furrow else "Soil_Dirt_Tilled")
            p.set(x, -2, z, "Soil_Dirt")
            if furrow:
                if r.random() < 0.15:
                    p.set(x, 0, z, p.pick(WILD_GROWTH))
                continue
            if state == "wild":
                if r.random() < 0.55:
                    p.set(x, 0, z, p.pick(WILD_GROWTH) if r.random() < 0.6 else WHEAT_YOUNG)
            elif crop == "pumpkin":
                if r.random() < 0.7:
                    p.set(x, 0, z, p.pick(PUMPKIN_CROPS))
            elif r.random() < 0.9:
                p.set(x, 0, z, WHEAT if r.random() < 0.8 else WHEAT_YOUNG)


def fence_rect(p, x0, z0, x1, z1, gates=(), broken=0.0, fence="Wood_Deadwood_Fence"):
    """Clôture autour d'un rectangle, ouverte aux cases `gates` ; `broken` = part de poteaux tombés."""
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            if x in (x0, x1) or z in (z0, z1):
                if (x, z) in gates or p.rng.random() < broken:
                    continue
                p.set(x, 0, z, fence)


def scarecrow(p, x, z, facing):
    p.set(x, -1, z, "Soil_Dirt")
    p.clear(x, 0, z, x, 2, z)
    p.set(x, 0, z, "Deco_Scarecrow", facing)


def overgrow(p, x0, z0, x1, z1, count, palette=WILD_GROWTH):
    """Herbes folles posées sur le sol (y = 0) des cases libres."""
    p.scatter(x0, 0, z0, x1, z1, count, palette, rot=0)


def webs_inside(p, x0, z0, x1, z1, y0, y1, count):
    """Toiles d'araignée accrochées sous les plafonds et dans les coins."""
    r = p.rng
    for _ in range(count * 4):
        if count <= 0:
            break
        x, z = r.randint(x0, x1), r.randint(z0, z1)
        for y in range(y1, y0 - 1, -1):
            if p.free(x, y, z) and not p.free(x, y + 1, z):
                p.set(x, y, z, p.pick(WEBS))
                count -= 1
                break


def spider_lair(p, x0, z0, x1, z1, nests=5):
    """Toiles au sol, cocons et squelettes : ce qui reste des habitants."""
    r = p.rng
    for _ in range(nests):
        cx, cz = r.randint(x0, x1), r.randint(z0, z1)
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                if abs(dx) + abs(dz) <= 3 and r.random() < 0.55 and p.free(cx + dx, 0, cz + dz) and not p.free(cx + dx, -1, cz + dz):
                    p.set(cx + dx, 0, cz + dz, "Deco_SpiderWeb_Flat")
        if p.free(cx, 0, cz):
            p.set(cx, 0, cz, "Deco_Spider_Cocoon")


def spawners(p, name, spots):
    """Un bloc d'apparition par case (un PNJ chacun), sur une case libre posée sur du plein : la case
    demandée, sinon la plus proche dans un rayon de 3. Échoue si une case n'a aucune place."""
    for x, z in spots:
        ring = sorted(((dx, dz) for dx in range(-3, 4) for dz in range(-3, 4)), key=lambda d: d[0] ** 2 + d[1] ** 2)
        spot = next(((x + dx, y, z + dz) for dx, dz in ring for y in (0, 5, 1, -1)
                     if p.free(x + dx, y, z + dz) and p.free(x + dx, y + 1, z + dz) and not p.free(x + dx, y - 1, z + dz)), None)
        if spot is None:
            raise ValueError(f"{name} : aucune case libre près de ({x}, {z})")
        p.set(*spot, name)


VILLAGE_PLOTS = [
    # (x0, z0, largeur, profondeur, porte, étages, type) ; rues : x -2..2 (nord-sud), z -2..2 (est-ouest)
    (-13, -12, 9, 7, EAST, 2, "home"), (-25, -11, 9, 7, SOUTH, 1, "home"),
    (5, -13, 7, 9, WEST, 1, "home"), (16, -12, 11, 8, SOUTH, 1, "barn"),
    (-12, 5, 8, 9, EAST, 1, "smithy"), (-26, 5, 9, 9, NORTH, 2, "home"),
    (5, 5, 9, 7, WEST, 2, "home"), (17, 5, 9, 9, NORTH, 1, "home"),
    (-8, -30, 7, 9, SOUTH, 1, "home"), (4, 22, 9, 7, WEST, 1, "home"),
]


def village(seed, variant):
    """Village abandonné du domaine : dix maisons le long de deux rues, place au puits, jardins.

    `variant` : "zombies" (villageois transformés, portes enfoncées, fenêtres condamnées),
    "ruins" (désert, en ruine, envahi par les herbes), "spiders" (envahi par les araignées).
    """
    p = Prefab(seed)
    r = p.rng
    X, Z = 34, 34
    p.clear(-X, 0, -Z, X, 4, Z)
    for x in range(-X, X + 1):
        for z in range(-Z, Z + 1):
            p.set(x, -1, z, p.pick(GROUND))
    # rues en terre battue et pavés, place centrale
    for x in range(-X, X + 1):
        for z in range(-Z, Z + 1):
            street = abs(x) <= 2 or abs(z) <= 2
            square = abs(x) <= 6 and abs(z) <= 6
            if square or (street and r.random() < 0.92):
                p.set(x, -1, z, "Rock_Stone_Cobble" if square and r.random() < 0.6 else p.pick(PATH))
    well(p, 0, 0)
    doors = []
    for i, (x0, z0, w, d, door, floors, kind) in enumerate(VILLAGE_PLOTS):
        loot = LOOT_VILLAGE_RICH if i == 0 else LOOT_VILLAGE
        doors.append(house(p, x0, z0, w, d, door, floors, kind, loot))
    # jardins clos derrière quelques maisons, potagers en friche
    for gx0, gz0, gx1, gz1 in ((-25, -24, -15, -16), (19, 17, 29, 25), (-26, 18, -17, 26)):
        field(p, gx0 + 1, gz0 + 1, gx1 - 1, gz1 - 1, "wheat", "wild")
        fence_rect(p, gx0, gz0, gx1, gz1, gates={((gx0 + gx1) // 2, gz1)}, broken=0.15)
    # place : bancs autour du puits, lanternes, panneau
    for x, z, rot in ((-4, -4, SOUTH), (4, 4, NORTH)):
        p.set(x, 0, z, "Furniture_Village_Bench", rot)
    for x, z in ((-4, 4), (4, -4)):
        lantern_post(p, x, z, 2)
    p.set(3, 0, -4, "Furniture_Village_Sign", NORTH)
    # variantes
    if variant == "zombies":
        for (dx, dz) in r.sample(doors, 4):          # portes enfoncées : planches arrachées devant
            p.set(dx, 0, dz, r.choice(["Wood_Deadwood_Planks_Half", "Deco_Trash_Pile_Small"]))
        for pos, (name, rot) in list(p.blocks.items()):
            if name == "Furniture_Ancient_Window" and r.random() < 0.35:
                p.set(*pos, "Wood_Deadwood_Planks_Half" if pos[1] % 2 else "Wood_Deadwood_Planks", 0)  # condamnées
            elif name == "Furniture_Ancient_Door" and r.random() < 0.4:
                p.set(*pos, AIR)
        p.scatter(-X + 2, 0, -Z + 2, X - 2, Z - 2, 22, [(BLOOD, 3), ("Deco_Bone_Pile", 1), ("Deco_Trash_Pile_Small", 2)], rot=0)
        overgrow(p, -X + 1, -Z + 1, X - 1, Z - 1, 50)
        spawners(p, SPAWN_VILLAGER, [(0, 4), (-4, 1), (5, -1), (1, -15), (-1, 17), (-20, 0), (21, -1)] +
                 [(x + 2, z + 2) for x, z, *_ in VILLAGE_PLOTS[:3]])
    elif variant == "ruins":
        p.ruin(62, keep_below=1, names={n for n, _ in COBBLE_WALL + TIMBER} | {"Wood_Deadwood_Roof", "Wood_Deadwood_Planks",
                                                                                "Wood_Deadwood_Beam", "Furniture_Ancient_Window"})
        p.scatter(-X + 2, 0, -Z + 2, X - 2, Z - 2, 40, RUBBLE, rot=0)
        overgrow(p, -X + 1, -Z + 1, X - 1, Z - 1, 220)
        for _ in range(6):                            # arbres morts qui poussent dans les décombres
            tx, tz = r.randint(-X + 4, X - 4), r.randint(-Z + 4, Z - 4)
            if p.free(tx, 0, tz) and p.free(tx, 3, tz):
                p.paste(dead_tree(r.randint(0, 1 << 30), "small"), tx, 0, tz, min_y=0)
    else:  # spiders
        p.ruin(85, keep_below=1, names={n for n, _ in COBBLE_WALL} | {"Wood_Deadwood_Roof"})
        for x0, z0, w, d, *_ in VILLAGE_PLOTS:
            webs_inside(p, x0 + 1, z0 + 1, x0 + w - 2, z0 + d - 2, 0, 8, 6)
        for dx, dz in doors:
            p.set(dx, 0, dz, "Deco_SpiderWeb_Full")
        spider_lair(p, -X + 3, -Z + 3, X - 3, Z - 3, 9)
        p.scatter(-X + 2, 0, -Z + 2, X - 2, Z - 2, 14, [("Deco_Bone_Pile", 2), ("Deco_Bone_Skulls", 1), ("Deco_Spider_Cocoon", 2)])
        overgrow(p, -X + 1, -Z + 1, X - 1, Z - 1, 60)
        spawners(p, SPAWN_SPIDER, [(0, 5), (-5, -1), (6, 1), (0, -18), (0, 20), (-22, 0), (22, 0)])
    return p


def farm(seed, variant):
    """Ferme délaissée : maison du fermier, grange, champs de blé clos, potager, puits.

    `variant` : "zombies" (fermiers transformés et un gros zombie difforme dans la grange),
    "ruins" (abandonnée, en ruine, champs en friche), "burnt" (incendiée : bois calciné, blé brûlé).
    """
    p = Prefab(seed)
    r = p.rng
    X, Z = 24, 22
    p.clear(-X, 0, -Z, X, 4, Z)
    for x in range(-X, X + 1):
        for z in range(-Z, Z + 1):
            p.set(x, -1, z, "Soil_Ash" if variant == "burnt" and r.random() < 0.45 else p.pick(GROUND))
    burnt = variant == "burnt"
    wood = "Wood_Blackwood" if burnt else "Wood_Deadwood"
    # cour en terre battue entre la maison et la grange, chemin vers le sud
    for x in range(-X, X + 1):
        for z in range(-6, 1):
            if r.random() < 0.85:
                p.set(x, -1, z, p.pick(PATH))
    for z in range(1, Z + 1):
        for x in (-1, 0, 1):
            p.set(x, -1, z, p.pick(PATH))
    door_house = house(p, -20, -17, 9, 8, SOUTH, 2, "home", LOOT_FARM_BURNT if burnt else LOOT_FARM, wood)
    door_barn = house(p, 6, -19, 13, 10, SOUTH, 1, "barn", LOOT_FARM_BURNT if burnt else LOOT_FARM, wood)
    p.clear(11, 0, -10, 13, 2, -10)                   # grande porte de grange
    p.set(12, 3, -10, f"{wood}_Beam")
    well(p, -6, -3)
    # deux champs clos et un potager
    state = {"zombies": "fine", "ruins": "wild", "burnt": "burnt"}[variant]
    fences = "Wood_Blackwood_Fence" if burnt else "Wood_Deadwood_Fence"
    broken = {"zombies": 0.12, "ruins": 0.3, "burnt": 0.45}[variant]
    for fx0, fz0, fx1, fz1 in ((-22, 3, -4, 19), (4, 3, 22, 19)):
        field(p, fx0 + 1, fz0 + 1, fx1 - 1, fz1 - 1, "wheat", state)
        gate = (fx1, (fz0 + fz1) // 2) if fx0 < 0 else (fx0, (fz0 + fz1) // 2)
        fence_rect(p, fx0, fz0, fx1, fz1, gates={gate}, broken=broken, fence=fences)
        for fx, fz in ((fx0, fz0), (fx1, fz0), (fx0, fz1), (fx1, fz1)):
            p.set(fx, 0, fz, f"{wood}_Beam")
            p.set(fx, 1, fz, "Deco_Lantern" if not burnt else f"{wood}_Beam")
        sx = (fx0 + fx1) // 2
        scarecrow(p, sx, (fz0 + fz1) // 2, face_toward(sx, 0, 0, 0) if state != "burnt" else SOUTH)
    field(p, -10, -13, -5, -8, "pumpkin", state)
    fence_rect(p, -11, -14, -4, -7, gates={(-7, -7)}, broken=broken, fence=fences)
    # meules de foin et tas de bois dans la cour
    for hx, hz in ((19, -6), (20, -6), (19, -5), (-2, -6)):
        p.set(hx, 0, hz, "Ingredient_Hay" if not burnt else "Soil_Ash")
    p.set(20, 1, -6, "Plant_Hay_Bundle" if not burnt else "Deco_Trash_Pile_Small")
    for x in range(-23, -20):
        p.set(x, 0, -6, "Wood_Ash_Trunk" if not burnt else "Wood_Burnt_Trunk", ALONG_X)
    if variant == "zombies":
        p.scatter(-X + 2, 0, -Z + 2, X - 2, Z - 2, 16, [(BLOOD, 3), ("Deco_Bone_Pile", 1)], rot=0)
        p.set(door_house[0], 0, door_house[1], "Wood_Deadwood_Planks_Half")
        spawners(p, SPAWN_FARMER, [(-13, 11), (13, 11), (-3, -3), (0, 8)])
        spawners(p, SPAWN_ABOMINATION, [(12, -14)])          # dans la grange
    elif variant == "ruins":
        p.ruin(60, keep_below=1, names={n for n, _ in COBBLE_WALL + TIMBER} | {"Wood_Deadwood_Roof", "Wood_Deadwood_Planks", "Wood_Deadwood_Beam"})
        overgrow(p, -X + 1, -Z + 1, X - 1, Z - 1, 140)
        p.scatter(-X + 2, 0, -Z + 2, X - 2, Z - 2, 20, RUBBLE, rot=0)
    else:  # incendiée
        p.ruin(45, keep_below=1, names={n for n, _ in COBBLE_WALL} | {f"{wood}_Roof", f"{wood}_Planks", f"{wood}_Decorative",
                                                                      f"*{wood}_Roof_State_Definitions_Topper", "Furniture_Ancient_Window"})
        for pos, (name, rot) in list(p.blocks.items()):
            if name == f"{wood}_Beam" and r.random() < 0.5:
                p.set(*pos, "Wood_Burnt_Trunk", UPRIGHT)
            elif name.startswith("Furniture_Ancient_Door") and r.random() < 0.7:
                p.set(*pos, AIR)
        p.scatter(-X + 2, 0, -Z + 2, X - 2, Z - 2, 30, [("Deco_Trash_Pile_Small", 2), ("Soil_Ash", 2), ("Wood_Burnt_Branch_Short", 1)], rot=0)
        p.scatter(-20, 0, -17, 18, -9, 4, [("Deco_Fire", 1)], rot=0)   # braises encore rouges dans les décombres
    return p


def prison_cells(p, x0, z0, count=3, door="Furniture_Temple_Dark_Door"):
    """Rangée de cellules le long de z : intérieur 2 × 2 (x0 + 1..x0 + 2), barreaux et porte côté ouest
    (x0), mur du fond en x0 + 3. Le bloc PRISON_CELL au sol de chaque cellule sert au Capitaine."""
    zs = []
    for i in range(count):
        cz = z0 + 3 * i
        for z in range(cz - 1, cz + 3):
            for y in range(0, 4):
                p.set(x0 + 3, y, z, p.pick(STONE_WALL))
        for z in (cz - 1, cz + 2):
            for x in range(x0, x0 + 4):
                p.fill(x, 0, z, x, 3, z, p.pick(STONE_WALL))
        p.fill(x0 + 1, 3, cz, x0 + 2, 3, cz + 1, "Rock_Stone_Brick")
        p.clear(x0 + 1, 0, cz, x0 + 2, 2, cz + 1)
        p.set(x0, 0, cz, door, 1)
        p.set(x0, 1, cz, AIR)
        p.fill(x0, 0, cz + 1, x0, 2, cz + 1, "Deco_Iron_Bars")
        p.set(x0, 2, cz, "Deco_Iron_Bars")
        p.set(x0, 3, cz, "Rock_Stone_Brick")
        p.set(x0, 3, cz + 1, "Rock_Stone_Brick")
        p.set(x0 + 2, 0, cz + 1, p.rng.choice(["Deco_Bone_Pile", "Deco_Bucket", "Ingredient_Hay"]))
        p.set(x0 + 1, 0, cz, PRISON_CELL)
        p.set(x0 + 2, 2, cz, "Deco_Iron_Chains_Vertical")
        zs.append(cz)
    return zs


def guard_post(seed, variant):
    """Ancien poste de garde : enceinte de pierre, tour de guet, caserne, quartiers du capitaine,
    armurerie, prison à trois cellules, cachot dans l'armurerie, cour d'entraînement. Le Capitaine
    trouve toujours une cellule à moins de 24 blocs de lui, d'où que ce soit dans l'enceinte.

    `variant` : "ruins", "spiders", "rebels" (paysans zombifiés qui ont pris le poste), "garrison"
    (gardes squelettes en armure et leur capitaine).
    """
    p = Prefab(seed)
    r = p.rng
    S = 17
    p.clear(-S - 2, 0, -S - 2, S + 2, 16, S + 2)
    for x in range(-S - 2, S + 3):
        for z in range(-S - 2, S + 3):
            p.set(x, -1, z, p.pick(GROUND))
    for x in range(-S, S + 1):
        for z in range(-S, S + 1):
            p.set(x, -1, z, "Rock_Stone_Cobble" if r.random() < 0.55 else p.pick(PATH))
    curtain_wall(p, -S, -S, S, S, 5, STONE_WALL, gate_half=2)
    gatehouse(p, S, 5, STONE_WALL, "Rock_Stone_Brick_Ornate")
    for z in range(S + 1, S + 3):
        for x in range(-1, 2):
            p.set(x, -1, z, p.pick(PATH))
    tower(p, -S + 1, -S + 1, 3, 14, STONE_WALL, STONE_FLOOR, "Rock_Slate_Cobble", "Rock_Stone_Brick_Ornate", webs=False)
    p.clear(-S + 4, 0, -S + 1, -S + 4, 2, -S + 1)     # porte de la tour sur la cour
    # caserne au nord : lits, coffres, râtelier
    bx0, bz0, bx1, bz1 = -11, -16, 2, -9
    p.floor(bx0, bz0, bx1, bz1, -1, STONE_FLOOR)
    p.hollow(bx0, 0, bz0, bx1, 3, bz1, STONE_WALL)
    roof(p, bx0, bz0, bx1, bz1, 4, "Wood_Deadwood", "x", gable=STONE_WALL)
    p.clear(-4, 0, bz1, -4, 1, bz1)
    p.set(-4, 0, bz1, "Furniture_Human_Ruins_Door", 0)
    for x in range(bx0 + 1, bx1, 3):
        p.set(x, 0, bz0 + 1, "Furniture_Human_Ruins_Bed", SOUTH)
    p.chest(bx1 - 2, 0, bz1 - 1, "Furniture_Human_Ruins_Chest_Large", NORTH, LOOT_BARRACKS)
    p.set(bx0 + 1, 0, bz1 - 1, "Bench_Armory", NORTH)
    p.set(-7, 0, bz1 - 2, "Furniture_Human_Ruins_Table")
    p.set(-8, 0, bz1 - 2, "Furniture_Human_Ruins_Stool")
    p.set(-5, 0, bz1 - 1, "Furniture_Human_Ruins_Stool")
    p.set(-7, 1, bz1 - 2, "Deco_Tankard", SOUTH)
    for x in (-8, -2):
        p.set(x, 2, bz1, "Furniture_Ancient_Window", 0)
    hang_lantern(p, -3, 3, -12)
    # quartiers du capitaine au nord-est : lit, bureau, coffre
    qx0, qz0, qx1, qz1 = 5, -16, 15, -9
    p.floor(qx0, qz0, qx1, qz1, -1, STONE_FLOOR)
    p.hollow(qx0, 0, qz0, qx1, 3, qz1, STONE_WALL)
    roof(p, qx0, qz0, qx1, qz1, 4, "Wood_Deadwood", "x", gable=STONE_WALL)
    p.clear(8, 0, qz1, 8, 1, qz1)
    p.set(8, 0, qz1, "Furniture_Human_Ruins_Door", 0)
    p.set(qx1 - 2, 0, qz0 + 1, "Furniture_Human_Ruins_Bed", SOUTH)
    p.set(qx0 + 2, 0, qz0 + 1, "Furniture_Human_Ruins_Desk", SOUTH)
    p.set(qx0 + 1, 0, qz0 + 2, "Furniture_Human_Ruins_Chair", NORTH)
    p.set(qx0 + 2, 1, qz0 + 1, "Deco_Map", SOUTH)
    p.set(qx0 + 1, 1, qz0 + 1, p.pick(CANDLES))
    p.chest(qx1 - 1, 0, qz1 - 1, "Furniture_Human_Ruins_Chest_Small", WEST, LOOT_CAPTAIN)
    p.set(qx1 - 1, 0, qz1 - 3, "Furniture_Human_Ruins_Bookshelf", WEST)
    p.set(qx0 + 4, 2, qz0, "Furniture_Human_Ruins_Banner", SOUTH)
    p.set(12, 2, qz1, "Furniture_Ancient_Window", 0)
    hang_lantern(p, 10, 3, -12)
    # armurerie à l'ouest
    ax0, az0, ax1, az1 = -16, -4, -10, 6
    p.floor(ax0, az0, ax1, az1, -1, STONE_FLOOR)
    p.hollow(ax0, 0, az0, ax1, 3, az1, STONE_WALL)
    roof(p, ax0, az0, ax1, az1, 4, "Wood_Deadwood", "z", gable=STONE_WALL)
    p.clear(ax1, 0, 1, ax1, 1, 1)
    p.set(ax1, 0, 1, "Furniture_Human_Ruins_Door", 1)
    p.set(ax0 + 1, 0, az0 + 2, "Bench_Weapon", EAST)
    p.set(ax0 + 1, 0, az0 + 6, "Bench_Armour", EAST)
    p.chest(ax0 + 1, 0, az1 - 1, "Furniture_Human_Ruins_Chest_Large", NORTH, LOOT_ARMORY)
    p.set(ax1 - 1, 0, az0 + 1, "Furniture_Ancient_Barrel")
    p.set(ax1 - 1, 0, az0 + 2, "Furniture_Ancient_Crate")
    hang_lantern(p, -13, 3, 1)
    # cachot à l'ouest, dans l'armurerie : le Capitaine cherche une cellule à moins de 24 blocs de
    # lui, où qu'il soit dans le poste (les trois autres sont à l'est)
    prison_cells(p, -13, 3, 1)
    # prison à l'est : couloir, trois cellules, cachot du geôlier
    jx0, jz0, jx1, jz1 = 7, -5, 15, 8
    p.floor(jx0, jz0, jx1, jz1, -1, STONE_FLOOR)
    p.hollow(jx0, 0, jz0, jx1, 3, jz1, STONE_WALL)
    p.fill(jx0 + 1, 4, jz0 + 1, jx1 - 1, 4, jz1 - 1, "Rock_Stone_Brick")
    p.crenellate(jx0, jz0, jx1, jz1, 4, STONE_WALL)
    p.clear(jx0, 0, 0, jx0, 1, 0)
    p.set(jx0, 0, 0, "Furniture_Human_Ruins_Door", 1)
    prison_cells(p, 11, -3, 3)
    p.set(8, 0, jz1 - 2, "Furniture_Human_Ruins_Table")
    p.set(10, 0, jz1 - 1, "Furniture_Human_Ruins_Stool", WEST)
    p.set(8, 1, jz1 - 2, p.pick(CANDLES))
    p.set(9, 3, 0, "Deco_Lantern_Ceiling")
    # cour : mannequins d'entraînement, braseros, bannières, râtelier
    for x, z in ((-5, 3), (-3, 5), (-1, 3)):
        p.set(x, 0, z, "Tinkering_Target_Dummy", NORTH)
    for x, z in ((-4, -6), (4, -6), (-4, 12), (4, 12)):
        p.set(x, 0, z, "Furniture_Human_Ruins_Brazier")
    for x in (-8, 8):
        p.set(x, 3, S - 1, "Furniture_Human_Ruins_Banner", NORTH)
    well(p, 3, 4)
    for x, z in ((-S + 1, S - 1), (S - 1, S - 1)):
        p.set(x, 0, z, "Furniture_Ancient_Barrel")
    p.set(-S + 2, 0, S - 1, "Furniture_Ancient_Crate")
    p.set(14, 0, 14, "Ingredient_Hay")
    # variantes
    if variant == "garrison":
        spawners(p, SPAWN_CAPTAIN, [(0, 0)])
        spawners(p, SPAWN_GUARD, [(0, 13), (-6, -7), (10, -6), (9, 2), (-S + 1, -S + 4), (-13, 1)])
    elif variant == "rebels":
        # le portail a cédé, barricades de charrettes et de foin, caserne incendiée
        for x in range(-2, 3):
            p.set(x, 3, S, AIR)
        for x, z in ((-6, 9), (-5, 9), (5, 8), (6, 8), (0, 10)):
            p.set(x, 0, z, r.choice(["Ingredient_Hay", "Furniture_Ancient_Crate", "Wood_Deadwood_Planks"]))
        for pos, (name, rot) in list(p.blocks.items()):
            if name == "Wood_Deadwood_Roof" and pos[0] < 3 and pos[2] < -8 and r.random() < 0.6:
                p.set(*pos, AIR)
        for pos in floating_blocks(p):                # pans de toit restés en l'air
            p.set(*pos, None)
        p.scatter(-S + 2, 0, -S + 2, S - 2, S - 2, 18, [(BLOOD, 3), ("Deco_Bone_Pile", 1), ("Deco_Trash_Pile_Small", 1)], rot=0)
        spawners(p, SPAWN_REBEL, [(0, 13), (-6, 6), (5, -6), (-3, -12), (10, 3), (-13, 3)])
    elif variant == "spiders":
        p.ruin(88, keep_below=1, names={n for n, _ in STONE_WALL})
        for bx in ((-10, -15, 1, -10), (6, -15, 14, -10), (-15, -3, -11, 5), (8, -4, 14, 7)):
            webs_inside(p, *bx[:2], *bx[2:], 0, 3, 8)
        spider_lair(p, -S + 2, -S + 2, S - 2, S - 2, 7)
        for x in range(-1, 2):
            p.set(x, 1, S, "Deco_SpiderWeb_Full")
        spawners(p, SPAWN_SPIDER, [(0, 0), (-6, 8), (6, 10), (-4, -7), (10, -4)])
    else:  # ruines
        p.ruin(58, keep_below=1, names={n for n, _ in STONE_WALL} | {"Wood_Deadwood_Roof", "*Wood_Deadwood_Roof_State_Definitions_Topper"})
        overgrow(p, -S + 1, -S + 1, S - 1, S - 1, 120)
        p.scatter(-S + 2, 0, -S + 2, S - 2, S - 2, 25, RUBBLE, rot=0)
    return p


# --- small decorations ------------------------------------------------------------------------

def bone_pile(seed):
    p = Prefab(seed)
    r = p.rng
    for _ in range(r.randint(4, 8)):
        x, z = r.randint(-2, 2), r.randint(-2, 2)
        p.set(x, 0, z, p.pick(BONES), r.randint(0, 3))
    p.set(0, 0, 0, "Deco_Bone_Spike_Large" if r.random() < 0.5 else "Deco_Bone_Spike")
    for x, z in ((-1, -1), (1, 1), (1, -2)):
        p.set(x, -1, z, r.choice(["Soil_Dirt_Burnt", "Soil_Ash", "Soil_Gravel"]))
    if r.random() < 0.5:
        p.set(r.choice([-2, 2]), 0, r.choice([-2, 2]), p.pick(GLOW_MUSHROOMS))
    return p


def lone_grave(seed):
    p = Prefab(seed)
    r = p.rng
    grave(p, 0, 0, r, r.choice(["haunted", "undead", "plain"]))
    if r.random() < 0.5:
        p.set(1, 0, 0, p.pick(CANDLES))
    if r.random() < 0.5:
        lantern_post(p, -1, -1, 1)
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
        p.set(r.randint(-2, 2), 0, r.randint(-2, 2), r.choice(["Deco_Spider_Cocoon", "Deco_Spider_Cocoon", "Deco_Bone_Pile"]))
    p.paste(dead_tree(r.randint(0, 1 << 30), "small", webs=True), r.choice([-3, 3]), 0, r.choice([-3, 3]), min_y=0)
    return p


def rock_outcrop(seed):
    """Affleurement rocheux : un tas de blocs de roche moussue, parfois des cristaux qui luisent."""
    p = Prefab(seed)
    r = p.rng
    rock = r.choice([
        [("Rock_Stone", 4), ("Rock_Stone_Mossy", 3), ("Rock_Stone_Cobble_Mossy", 1)],
        [("Rock_Slate", 4), ("Rock_Slate_Cobble", 2), ("Rock_Stone_Mossy", 1)],
        [("Rock_Shale", 4), ("Rock_Shale_Cobble", 2), ("Rock_Basalt", 1)],
    ])
    cx, cz = 0, 0
    for _ in range(r.randint(2, 4)):
        rad = r.uniform(1.5, 3.2)
        h = r.randint(2, 5)
        for x in range(-4, 5):
            for z in range(-4, 5):
                dist = ((x - cx) ** 2 + (z - cz) ** 2) ** 0.5
                if dist > rad:
                    continue
                top = int(round(h * (1 - dist / (rad + 0.5)))) + r.randint(-1, 0)
                for y in range(-2, top):
                    p.set(x, y, z, p.pick(rock))
        cx += r.randint(-2, 2)
        cz += r.randint(-2, 2)
    # dessus : mousse, demi-dalles, herbes ; pied : cailloux et cristaux
    for (x, y, z), (name, _) in list(p.blocks.items()):
        if y >= 0 and p.free(x, y + 1, z):
            roll = r.random()
            if roll < 0.15:
                p.set(x, y + 1, z, "Rock_Stone_Cobble_Mossy_Half")
            elif roll < 0.35:
                p.set(x, y + 1, z, p.pick(DEAD_PLANTS))
    crystal = r.random() < 0.45
    for _ in range(r.randint(3, 7)):
        x, z = r.randint(-5, 5), r.randint(-5, 5)
        if p.free(x, 0, z) and (not p.free(x + 1, 0, z) or not p.free(x - 1, 0, z)):
            p.set(x, 0, z, "Rock_Crystal_Purple_Small" if crystal and r.random() < 0.6 else p.pick(DEAD_PLANTS))
    return p


def mushroom_ring(seed):
    """Cercle de champignons luisants autour d'une pierre levée et de bougies."""
    p = Prefab(seed)
    r = p.rng
    rad = r.choice([2.5, 3.0, 3.5])
    kind = r.choice(["Plant_Crop_Mushroom_Glowing_Purple", "Plant_Crop_Mushroom_Glowing_Violet", "Plant_Crop_Mushroom_Glowing_Green"])
    for x in range(-4, 5):
        for z in range(-4, 5):
            d = (x * x + z * z) ** 0.5
            if abs(d - rad) < 0.6 and r.random() < 0.85:
                p.set(x, 0, z, kind)
            elif d < rad - 0.5:
                p.set(x, -1, z, r.choice(["Soil_Grass_Burnt", "Soil_Ash", "Soil_Dirt_Burnt"]))
    p.set(0, 0, 0, "Rock_Stone_Mossy")
    p.set(0, 1, 0, "Rock_Stone_Cobble_Mossy_Half")
    for x, z in ((1, 0), (-1, 1), (0, -1)):
        if r.random() < 0.7:
            p.set(x, 0, z, p.pick(CANDLES))
    if r.random() < 0.5:
        p.set(r.choice([-1, 1]), 0, r.choice([-1, 1]), p.pick(BONES))
    return p


def wayside_shrine(seed):
    """Petit autel au bord du chemin : stèle, lanterne, offrandes de citrouilles et de bougies."""
    p = Prefab(seed)
    r = p.rng
    for x in range(-1, 2):
        for z in range(-1, 2):
            p.set(x, -1, z, p.pick(PATH))
    p.set(0, 0, -1, "Rock_Stone_Brick_Pillar_Base")
    p.set(0, 1, -1, "Rock_Stone_Brick_Pillar_Middle")
    p.set(0, 2, -1, "Rock_Stone_Brick_Ornate")
    p.set(0, 3, -1, p.pick(CANDLES))
    p.set(-1, 0, -1, p.pick(CANDLES))
    p.set(1, 0, -1, p.pick(CANDLES))
    p.set(0, 0, 0, "Furniture_Village_Tombstone", SOUTH)
    lantern_post(p, 2, 1, 2)
    p.set(-1, 0, 1, r.choice(["Halloween_Basket_Pumpkin", "Halloween_Basket_Straw"]))
    return p


def fallen_log(seed):
    """Tronc mort couché, couvert de champignons et d'herbes."""
    p = Prefab(seed)
    r = p.rng
    species = r.choice(["Ash", "Ash", "Petrified", "Burnt"])
    length = r.randint(4, 7)
    along_x = r.random() < 0.5
    for k in range(length):
        x, z = (k - length // 2, 0) if along_x else (0, k - length // 2)
        p.set(x, 0, z, f"Wood_{species}_Trunk", ALONG_X if along_x else ALONG_Z)
        if r.random() < 0.35:
            p.set(x, 1, z, r.choice(["Plant_Crop_Mushroom_Glowing_Green", "Plant_Crop_Mushroom_Glowing_Purple", "Plant_Grass_Gnarled_Short"]))
    end = (length - length // 2, 0) if along_x else (0, length - length // 2)
    p.set(end[0], 0, end[1], "Wood_Gnarled_Roots")
    for _ in range(3):
        x, z = r.randint(-3, 3), r.choice([-1, 1])
        if not along_x:
            x, z = z, x
        if p.free(x, 0, z):
            p.set(x, 0, z, p.pick(DEAD_PLANTS))
    return p


# --- main -------------------------------------------------------------------------------------

# --- vampire hunter camp ----------------------------------------------------------------------

CAMP_HALF = 12   # palissade de 25 × 25 : les chasseurs (fil des mobs, laisse ~14) restent dedans
CAMP_GROUND = [("Soil_Pathway", 3), ("Soil_Dirt", 2), ("Soil_Grass_Burnt", 2), ("Soil_Gravel", 1)]
PALISADE = "Wood_Dry_Trunk"
# Feu purificateur (blocs du pack, tools/generate_assets.py) : les morts-vivants restent à PURIFY_RADIUS blocs
# de ces blocs (dev.nakasar.hytale.vampires.purifying.PurifyingFireSystem).
PURIFYING_TORCH = "Nakasar_Purifying_Torch"
PURIFYING_LANTERN = "Nakasar_Purifying_Lantern"
PURIFY_RADIUS = 7  # = PurifyingFireSystem.RADIUS
TORCH_STEP = PURIFY_RADIUS - 1  # une torche tous les TORCH_STEP troncs : leurs cercles se chevauchent
CANVAS = [("Cloth_Block_Wool_Black", 3), ("Cloth_Block_Wool_Red", 1)]
TENT_ROOF = "Cloth_Roof_Leather"


def tent(p, x0, z0, depth=5, loot=None):
    """Tente de cuir de 6 de large, faîte nord-sud, ouverte au sud : un lit, un coffre ou un sac."""
    x1, z1 = x0 + 5, z0 + depth - 1
    p.clear(x0, 0, z0, x1, 3, z1)
    p.floor(x0, z0, x1, z1, -1, [("Soil_Dirt", 2), ("Soil_Pathway", 1)])
    roof(p, x0, z0, x1, z1, 0, ridge="z", overhang=0, slope=TENT_ROOF)
    for x in range(x0 + 1, x1):
        p.fill(x, 0, z0, x, min(x - x0, x1 - x) - 1, z0, p.pick(CANVAS))
    p.set(x0 + 2, 0, z0 + 1, "Furniture_Lumberjack_Bed", SOUTH)
    if loot:
        p.chest(x0 + 1, 0, z0 + 1, "Furniture_Lumberjack_Chest_Small", EAST, loot)
    else:
        p.set(x0 + 1, 0, z0 + 1, "Furniture_Ancient_Sack", EAST)
    p.set(x1 - 1, 0, z0 + 1, "Furniture_Crude_Torch")


def hunter_lodge(p, x0, z0, w=11, d=7):
    """Pavillon de rondins et de planches : deux lits, une table, le coffre des chasseurs."""
    x1, z1 = x0 + w - 1, z0 + d - 1
    p.clear(x0 - 1, 0, z0 - 1, x1 + 1, 7, z1 + 1)
    p.floor(x0, z0, x1, z1, -1, "Wood_Softwood_Planks", foundation=FOUNDATION, depth=2)
    p.hollow(x0, 0, z0, x1, 2, z1, [("Wood_Softwood_Planks", 5), ("Wood_Softwood_Decorative", 1)])
    for cx in (x0, x1):
        for cz in (z0, z1):
            p.fill(cx, 0, cz, cx, 2, cz, PALISADE)
    door = (x0 + x1) // 2
    p.set(door, 1, z1, AIR)
    p.set(door, 0, z1, "Furniture_Lumberjack_Door", DOOR_ROT[SOUTH])
    for wz in (z0 + 2, z0 + 4):
        p.set(x0, 1, wz, AIR)
        p.set(x1, 1, wz, AIR)
    roof(p, x0, z0, x1, z1, 3, "Wood_Softwood", "x", gable="Wood_Softwood_Planks")
    for bx in (x0 + 1, x0 + 4):
        p.set(bx, 0, z0 + 1, "Furniture_Lumberjack_Bed", SOUTH)
    p.set(x1 - 3, 0, z0 + 1, "Furniture_Lumberjack_Table")
    for sx, sz in ((x1 - 1, z0 + 1), (x1 - 1, z0 + 2), (x1 - 3, z0 + 3)):
        p.set(sx, 0, sz, "Furniture_Crude_Stool")
    p.set(x1 - 3, 1, z0 + 1, "Furniture_Crude_Candle")
    p.chest(x1 - 1, 0, z1 - 1, "Furniture_Lumberjack_Chest_Small", WEST, LOOT_HUNTER_CAMP)
    p.set(x0 + 1, 0, z1 - 1, "Furniture_Ancient_Sack")
    hang_lantern(p, door, 2, z0 + 3)


def hunter_camp(seed, variant):
    """Camp de chasseurs de vampires : palissade de rondins, feu de camp, tentes de cuir (« tents »)
    ou un pavillon de bois (« lodge »), atelier d'armes à l'ouest, pas de tir à l'est, porte au sud.

    Les chasseurs sont pacifiques envers le joueur et ennemis des mobs du domaine ; leurs blocs
    d'apparition restent à moins de 9 blocs du centre pour qu'ils ne quittent pas l'enceinte.
    """
    p = Prefab(seed)
    r = p.rng
    h = CAMP_HALF
    p.clear(-h - 1, 0, -h - 1, h + 1, 7, h + 1)
    p.floor(-h - 1, -h - 1, h + 1, h + 1, -1, CAMP_GROUND, foundation="Soil_Dirt", depth=3)
    # palissade de troncs, pointes alternées, portail au sud gardé par deux lanternes
    for x in range(-h, h + 1):
        for z in range(-h, h + 1):
            if max(abs(x), abs(z)) != h or (z == h and abs(x) <= 1):
                continue
            top = 2 + (x + z) % 2
            p.fill(x, 0, z, x, top, z, PALISADE)
            # torche de feu blanc sur un tronc sur six, coins compris : le cercle de chacune recouvre la palissade
            if (abs(x) == h and abs(z) == h) or (x % TORCH_STEP == 0 and abs(z) == h) or (z % TORCH_STEP == 0 and abs(x) == h):
                p.set(x, top + 1, z, PURIFYING_TORCH)
    for gx in (-2, 2):
        p.fill(gx, 0, h, gx, 3, h, PALISADE)
        p.set(gx, 4, h, PURIFYING_LANTERN)
    # portail fermé : les PNJ n'ouvrent pas les portillons, les chasseurs restent dans l'enceinte
    for gx in (-1, 0, 1):
        p.set(gx, 0, h, "Wood_Softwood_Fence_Gate")
    for z in range(2, h + 2):
        for x in (-1, 0, 1):
            p.set(x, -1, z, p.pick(PATH))
    # feu de camp et tabourets autour
    p.set(0, -1, 0, "Rock_Stone_Cobble")
    p.set(0, 0, 0, "Bench_Campfire")
    for sx, sz in ((2, 0), (-2, 0), (0, -2), (1, 2)):
        p.set(sx, 0, sz, "Furniture_Crude_Stool")
    # couchage au nord
    if variant == "lodge":
        hunter_lodge(p, -10, -10)
        tent(p, 4, -10, loot=None)
    else:
        tent(p, -10, -10, loot=LOOT_HUNTER_CAMP)
        tent(p, -3, -10)
        tent(p, 4, -10)
    # atelier d'armes à l'ouest : établis, table, caisses, tonneaux, coffre d'armurerie
    p.set(-11, 0, 0, "Bench_Weapon", EAST)
    p.set(-11, 0, 3, "Bench_Armory", EAST)
    p.set(-8, 0, 1, "Furniture_Crude_Table")
    p.set(-8, 1, 1, "Furniture_Crude_Candle")
    p.set(-6, 0, 2, "Furniture_Crude_Stool")
    p.chest(-11, 0, 6, "Furniture_Lumberjack_Chest_Small", EAST, LOOT_HUNTER_ARMORY)
    for z in range(7, 12):
        name = r.choice(["Furniture_Village_Crate", "Furniture_Tavern_Barrel", "Furniture_Ancient_Barrel"])
        p.set(-11, 0, z, name)
        if name == "Furniture_Village_Crate" and r.random() < 0.5:
            p.set(-11, 1, z, "Furniture_Village_Crate")
    p.set(-10, 0, 11, "Furniture_Village_Crate")
    p.set(-8, 0, 11, "Bench_Tannery", NORTH)
    # pas de tir à l'est : cibles contre la palissade, mannequins, foin pour arrêter les carreaux
    for z in range(-3, 4):
        p.set(11, -1, z, "Soil_Pathway")
    for z in (-3, 0, 3):
        p.set(11, 0, z, "Deco_Target", WEST)
    for z in (-5, 5):
        p.fill(11, 0, z, 11, 1, z, "Ingredient_Hay")
    for z in (6, 8):
        p.set(9, 0, z, "Tinkering_Target_Dummy", WEST)
    for cz in (-3, 3):
        p.set(4, 0, cz, "Furniture_Village_Crate")
    p.set(4, 0, 0, "Furniture_Crude_Stool")
    # réserve au sud-est
    for bx, bz in ((11, 10), (11, 11), (10, 11)):
        p.set(bx, 0, bz, r.choice(["Furniture_Tavern_Barrel", "Furniture_Ancient_Barrel"]))
    p.fill(11, 0, 9, 11, 1, 9, "Ingredient_Hay")
    p.set(8, 0, 11, "Furniture_Ancient_Sack")
    # lanternes sur poteaux, herbe folle le long de la palissade
    for lx, lz in ((-4, 4), (4, 4), (-8, -2), (8, -4), (2, -3)):
        lantern_post(p, lx, lz, 2, PURIFYING_LANTERN)
    spawners(p, SPAWN_HUNTER, [(-3, 1), (3, -1), (1, 3), (-7, 4), (6, 1), (-3, -2)])
    p.scatter(-h + 1, 0, -h + 1, h - 1, h - 1, 10, [("Plant_Grass_Gnarled", 3), ("Plant_Grass_Gnarled_Short", 2)], rot=0)
    check_purified(p, h)
    return p


def check_purified(p, h):
    """Chaque case du camp, palissade comprise, doit être à moins de PURIFY_RADIUS d'un feu purificateur."""
    fires = [(x, z) for (x, _, z), block in p.blocks.items() if block[0] in (PURIFYING_TORCH, PURIFYING_LANTERN)]
    for x in range(-h, h + 1):
        for z in range(-h, h + 1):
            assert any((x - fx) ** 2 + (z - fz) ** 2 <= PURIFY_RADIUS ** 2 for fx, fz in fires), \
                f"camp des chasseurs : ({x}, {z}) hors de portée des feux purificateurs"


# --- lore implicite ---------------------------------------------------------------------------
# Notes et épitaphes de tools/generate_lore.py, ajoutées à la fin, avec leur propre tirage (seedé par le nom du
# prefab) : le reste du prefab ne change pas. Une note se pose au sol, sur une case libre à côté d'un coffre ;
# certaines stèles des cimetières deviennent des épitaphes lisibles.

# liste de butin du coffre -> (notes possibles, chance d'en poser une), tiré de generate_lore.LORE_BY_LOOT
LORE_BY_LOOT = {loot: (notes, chance) for loot, (_place, notes, chance, _empty) in lore.LORE_BY_LOOT.items()}
NOTE_FLOOR = re.compile(r"^(Rock|Wood|Soil)_")
NOT_FLOOR = re.compile(r"Half|Stairs|Fence|Wall|Bars|Railing|Pillar|Roof|Ornate|Tilled|Pathway")


def note_spot(p, x, y, z, radius=2, avoid=()):
    """Case libre au sol (bloc plein dessous) la plus proche de (x, y, z), ou None."""
    cells = sorted(((dx, dz) for dx in range(-radius, radius + 1) for dz in range(-radius, radius + 1) if (dx, dz) != (0, 0)),
                   key=lambda d: (abs(d[0]) + abs(d[1]), d))
    for dx, dz in cells:
        cx, cz = x + dx, z + dz
        below = p.get(cx, y - 1, cz) or ""
        if (cx, cz) in avoid or not p.free(cx, y, cz) or not NOTE_FLOOR.match(below) or NOT_FLOOR.search(below):
            continue
        return cx, y, cz
    return None


def add_lore(p, name):
    r = random.Random(f"lore/{name}")
    placed = set()
    for (x, y, z), comp in sorted(p.components.items()):
        droplist = comp.get("Components", {}).get("ItemContainerBlock", {}).get("Droplist")
        notes, chance = LORE_BY_LOOT.get(droplist, ((), 0))
        if notes and r.random() < chance:
            free = [n for n in notes if n not in placed] or list(notes)
            spot = note_spot(p, x, y, z)
            if spot:
                note = r.choice(free)
                placed.add(note)
                p.set(*spot, lore.note_id(note), r.randint(0, 3))
    cells = sorted(pos for pos, (b, _) in p.blocks.items() if b == PRISON_CELL)
    if cells:
        x, y, z = r.choice(cells)
        spot = note_spot(p, x, y, z, radius=1)
        if spot:
            p.set(*spot, lore.note_id("Prisoner"), r.randint(0, 3))
    if name.startswith("SpawnCrypt/"):
        # mot des chasseurs près du point d'arrivée, hors de l'allée centrale (arrivée, portail de retour)
        spot = note_spot(p, 2, 0, 1, avoid={(0, z) for z in range(-5, 6)})
        if spot:
            p.set(*spot, lore.note_id("Arrival"), SOUTH)
    epitaphs = sorted(lore.EPITAPHS)
    stones = sorted(pos for pos, (b, rot) in p.blocks.items() if b == "Furniture_Village_Tombstone" and rot == SOUTH)
    for pos in stones:
        if r.random() < 0.35:
            p.set(*pos, lore.epitaph_id(r.choice(epitaphs)), SOUTH)


def main():
    jobs = []
    sizes = ["small", "small", "medium", "medium", "medium", "large"]
    for i in range(12):
        jobs.append((f"Trees/Dead_Tree_{i + 1}", dead_tree(1000 + i, sizes[i % len(sizes)], webs=i % 4 == 0)))
    for i, hanging in enumerate(("lantern", "cage", "noose", "lantern")):
        jobs.append((f"Trees/Hanging_Tree_{i + 1}", dead_tree(1100 + i, "medium" if i % 2 else "large", hanging=hanging, webs=True)))
    for i in range(3):
        jobs.append((f"PumpkinFields/Plain/Pumpkin_Field_{i + 1}", pumpkin_field(2000 + i, *[(23, 19), (27, 17), (19, 23)][i])))
    for i in range(2):
        jobs.append((f"PumpkinFields/Giant/Pumpkin_Field_Giant_{i + 1}", pumpkin_field(2100 + i, *[(27, 23), (25, 25)][i], giant=True)))
    for i, variant in enumerate(("tents", "lodge")):
        jobs.append((f"HunterCamps/{variant.capitalize()}/Hunter_Camp_{variant.capitalize()}", hunter_camp(9000 + i, variant)))
    for t, theme in enumerate(("haunted", "spiders", "undead")):
        for i in range(2):
            jobs.append((f"Cemeteries/{theme.capitalize()}/Cemetery_{theme.capitalize()}_{i + 1}", cemetery(3000 + t * 100 + i, theme)))
    for i, material in enumerate(("stone", "slate", "shale")):
        jobs.append((f"Crypts/Crypt_{material.capitalize()}", crypt(4000 + i, material)))
    jobs.append(("HauntedCastles/Haunted_Castle_Stone", haunted_castle(5000, "stone")))
    jobs.append(("HauntedCastles/Haunted_Castle_Slate", haunted_castle(5001, "slate")))
    jobs.append(("VampireManor/Vampire_Manor", vampire_manor(6000)))
    jobs.append(("SpawnCrypt/Spawn_Crypt", spawn_crypt(6100)))
    for i, variant in enumerate(("zombies", "ruins", "spiders")):
        jobs.append((f"Villages/{variant.capitalize()}/Village_{variant.capitalize()}", village(8000 + i, variant)))
    for i, variant in enumerate(("zombies", "ruins", "burnt")):
        jobs.append((f"Farms/{variant.capitalize()}/Farm_{variant.capitalize()}", farm(8100 + i, variant)))
    for i, variant in enumerate(("ruins", "spiders", "rebels", "garrison")):
        jobs.append((f"GuardPosts/{variant.capitalize()}/Guard_Post_{variant.capitalize()}", guard_post(8200 + i, variant)))
    for i in range(3):
        jobs.append((f"Decor/BonePiles/Bone_Pile_{i + 1}", bone_pile(7000 + i)))
        jobs.append((f"Decor/Graves/Lone_Grave_{i + 1}", lone_grave(7100 + i)))
        jobs.append((f"Decor/SpiderNests/Spider_Nest_{i + 1}", spider_nest(7200 + i)))
        jobs.append((f"Decor/MushroomRings/Mushroom_Ring_{i + 1}", mushroom_ring(7500 + i)))
        jobs.append((f"Decor/Shrines/Wayside_Shrine_{i + 1}", wayside_shrine(7600 + i)))
        jobs.append((f"Decor/FallenLogs/Fallen_Log_{i + 1}", fallen_log(7700 + i)))
    for i in range(5):
        jobs.append((f"Decor/Outcrops/Rock_Outcrop_{i + 1}", rock_outcrop(7400 + i)))

    if OUT.exists():
        for old in OUT.rglob("*.prefab.json"):
            old.unlink()
    total = 0
    for name, prefab in jobs:
        add_lore(prefab, name)
        count = prefab.write(OUT / f"{name}.prefab.json")
        total += count
        print(f"{name}: {count} blocs")
    print(f"{len(jobs)} prefabs, {total} blocs")


if __name__ == "__main__":
    main()
