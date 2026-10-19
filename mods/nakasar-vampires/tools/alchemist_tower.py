"""La Tour de l'Alchimiste elle-même (étape 2 du donjon) : prefab de la tour, utilisé par generate_alchemist_tower.py.

Repère du prefab : centré sur l'axe de la tour, y = 0 = première couche d'air au-dessus du sol de l'île (y = -1 : sol).
Les angles sont en degrés : x = r cos(a), z = r sin(a), donc 0 = est, 90 = sud, 180 = ouest, 270 = nord.

Parcours, de bas en haut (niveaux = première couche d'air du sol de chaque salle) :

- parvis au sud, porte du Hall des Alambics (niveau 0) ; rampe le long du mur de 200 à 300° ;
- Couloir des fuites (11) : anneau autour d'un cœur plein, barré à 240°, on en fait les trois quarts jusqu'à la porte
  ouest ; tuyaux, niches et grilles de vapeur (les jets viendront avec les pièges) ;
- Serre suspendue (11) : balcon extérieur d'ouest en est par le nord, verrière à l'ouest, belvédère au nord ; une rampe
  extérieure monte de 0 à 50° jusqu'à la porte de la bibliothèque ;
- Bibliothèque (18) : rotonde haute de 14 blocs, étagères, salle secrète en encorbellement à 320° ; rampe de 70 à 205° ;
- Salle des Transmutations (33) : salle carrée en quatre quadrants (feu, glace, acide, foudre) ; escalier le long du
  mur nord vers le laboratoire ;
- Laboratoire (42) : cuve centrale ; porte nord vers l'Escalier des vents ;
- Escalier des vents : rampe extérieure de 262 à 602° (presque un tour), de 42 à l'Observatoire (72) ;
- Observatoire (72) : terrasse ronde au sommet, antichambre sur l'arrivée de l'escalier, Bureau de l'Alchimiste au sud.

Toutes les rampes montent en demi-dalles (pas de bloc orienté à deviner) et tous les bords extérieurs ont un parapet de
2 blocs au moins. `walkable_path` vérifie, hors ligne, qu'on va du parvis au bureau en passant par chaque point de
contrôle.
"""
import math
from collections import deque

import generate_prefabs as pf

AIR = pf.AIR
R_IN = 14.5        # intérieur de la tour : d < R_IN
R_OUT = 16.5       # mur : R_IN <= d < R_OUT
F_HALL, F_LEAKS, F_LIBRARY, F_TRANS, F_LAB, F_DECK = 0, 11, 18, 33, 42, 72
DECK_R = 22.5      # terrasse de l'observatoire : d < DECK_R, parapet jusqu'à DECK_R + 1
BALCONY_R = 23.5   # serre : R_OUT <= d < BALCONY_R, parapet jusqu'à BALCONY_R + 1
BALCONY_ARC = (176, 360)
GREENHOUSE_ARC = (195, 285)
SQUARE = 9         # Salle des Transmutations : |x|, |z| <= SQUARE
COURT = (-8, 8, 39)  # parvis : x de -8 à 8, jusqu'à z = 39 (le pont de l'île d'arrivée arrive en z = 40)

WALL = [("Rock_Marble_Brick", 7), ("Rock_Marble_Brick_Smooth", 2), ("Rock_Marble_Cobble", 1)]
FLOOR = [("Rock_Marble_Brick_Smooth", 4), ("Rock_Marble_Brick", 3)]
HALF = "Rock_Marble_Brick_Half"
TRIM = "Rock_Gold_Brick_Decorative"
GOLD = "Rock_Gold_Brick"
PARAPET, PARAPET_TOP = "Rock_Marble_Brick", "Rock_Marble_Brick_Wall"
GLASS = "Nakasar_Stained_Glass_Violet"
STATUE = "Furniture_Temple_Light_Statue"
SHELF = "Furniture_Bookshelf_Single"
LANTERN = "Furniture_Temple_Light_Lantern"
GLOW = "Furniture_Royal_Magic_Potion_Glow"
BRAZIER = "Furniture_Temple_Dark_Brazier"
CHANDELIER = "Furniture_Feran_Chandelier"

DIRS4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
DIRS8 = DIRS4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))
START = (0, 0, 30)  # parvis devant la porte du hall : (x, surface en demi-blocs, z) dans le repère du prefab


def polar(x, z):
    return math.hypot(x, z), math.degrees(math.atan2(z, x)) % 360


def in_arc(a, a0, a1):
    """L'angle a est-il sur l'arc parcouru dans le sens positif de a0 à a1 (a1 - a0 <= 360) ?"""
    return (a - a0) % 360 <= a1 - a0


def ring(r0, r1, reach=30):
    """Cases (x, z) avec r0 <= d < r1."""
    for x in range(-reach, reach + 1):
        for z in range(-reach, reach + 1):
            d, a = polar(x, z)
            if r0 <= d < r1:
                yield x, z, d, a


def facing_center(x, z):
    """Lacet d'un meuble posé en (x, z) pour qu'il regarde l'axe de la tour (0 = sud, 1 = est, 2 = nord, 3 = ouest)."""
    if abs(x) > abs(z):
        return pf.WEST if x > 0 else pf.EAST
    return pf.NORTH if z > 0 else pf.SOUTH


def at(r, a):
    return round(r * math.cos(math.radians(a))), round(r * math.sin(math.radians(a)))


class Tower:
    def __init__(self, seed):
        self.p = pf.Prefab(seed)
        self.rng = self.p.rng
        self.walk = {}       # (x, z) -> {surface en demi-blocs} : sols des rampes, balcons, terrasse, portes
        self.keep_clear = set()  # cases (x, y, z) que le décor ne doit pas prendre
        self.parapets = set()    # blocs (x, y, z) de parapet (tout bloc posé par-dessus les en retire)
        place = self.p.set

        def set_block(x, y, z, *args, **kwargs):
            self.parapets.discard((x, y, z))
            return place(x, y, z, *args, **kwargs)
        self.p.set = set_block
        self.checkpoints = []    # (x, y, z) relatifs, dans l'ordre du parcours

    # --- primitives ---------------------------------------------------------------------------

    def wall(self):
        return self.p.pick(WALL)

    def floor(self):
        return self.p.pick(FLOOR)

    def solid(self, x, y, z):
        b = self.p.get(x, y, z)
        return b not in (None, AIR) and not passable(b)

    def register(self, x, z, s):
        self.walk.setdefault((x, z), set()).add(s)

    def step(self, x, z, s, support=2):
        """Sol de surface s (en demi-blocs) en (x, z) : demi-dalle si s est impair."""
        y = s // 2
        if s % 2:
            self.p.set(x, y, z, HALF)
            self.p.set(x, y - 1, z, self.floor())
        else:
            self.p.set(x, y - 1, z, self.floor())
        base = (y - 2) if s % 2 == 0 else (y - 2)
        for k in range(support):
            if not self.solid(x, base - k, z):
                self.p.set(x, base - k, z, self.wall())
        self.register(x, z, s)

    def carve(self, x, z, s, height=3):
        """Dégage `height` blocs au-dessus de la surface s (seulement les blocs déjà posés)."""
        y0 = (s + 1) // 2
        for y in range(y0, y0 + height):
            if self.p.get(x, y, z) not in (None, AIR):
                self.p.set(x, y, z, AIR)
            self.keep_clear.add((x, y, z))

    def door(self, cells, y, height=3):
        """Ouvre une baie dans un mur : les cases (x, z) deviennent un passage de sol y."""
        for x, z in cells:
            for k in range(height):
                self.p.set(x, y + k, z, AIR)
                self.keep_clear.add((x, y + k, z))
            if not self.solid(x, y - 1, z):
                self.p.set(x, y - 1, z, self.floor())
            self.register(x, z, 2 * y)

    def parapet(self, x, y, z, high=2):
        for k in range(high):
            if self.p.free(x, y + k, z):
                self.p.set(x, y + k, z, PARAPET if k < high - 1 else PARAPET_TOP)
                self.parapets.add((x, y + k, z))

    def helix(self, a0, a1, r0, r1, y0, y1, flat=6.0, support=2):
        """Rampe hélicoïdale de a0 à a1 (sens positif, moins d'un tour) entre les rayons r0 et r1, du sol y0 au sol
        y1 ; `flat` degrés de palier à chaque bout. Renvoie {(x, z): surface en demi-blocs}."""
        span = a1 - a0
        cells = {}
        for x, z, d, a in ring(r0, r1):
            rel = (a - a0) % 360
            if rel > span:
                continue
            t = min(1.0, max(0.0, (rel - flat) / (span - 2 * flat)))
            cells[(x, z)] = round(2 * (y0 + (y1 - y0) * t))
        for (x, z), s in cells.items():
            self.step(x, z, s, support)
        for (x, z), s in cells.items():
            self.carve(x, z, s)
        return cells

    def guard(self, cells):
        """Parapets autour d'un groupe de sols extérieurs : sur chaque voisin vide et sans sol au même niveau, et sur le
        bord haut d'une marche de plus d'un bloc (trémie d'escalier). Le haut de chaque parapet dépasse de 2 blocs la
        plus haute marche voisine, sinon une rampe qui monte le long du parapet permettrait de sauter dessus."""
        need = {}  # (x, z) -> [[bas, haut exclu], ...]
        for (x, z), s in sorted(cells.items()):
            y = (s + 1) // 2
            top = (s + 5) // 2
            for dx, dz in DIRS8:
                n = (x + dx, z + dz)
                levels = self.walk.get(n, set())
                if any(abs(o - s) <= 2 for o in levels):
                    continue
                if any(s - 12 <= o < s - 2 for o in levels):
                    target = (x, z)  # trémie : garde-corps sur la case haute
                elif self.p.get(n[0], y, n[1]) in (None, AIR) and not self.solid(n[0], y - 1, n[1]):
                    target = n
                else:
                    continue
                segs = need.setdefault(target, [])
                for seg in segs:
                    if seg[0] - 4 <= y <= seg[1] + 2:
                        seg[0], seg[1] = min(seg[0], y), max(seg[1], top)
                        break
                else:
                    segs.append([y, top])
                if target == (x, z):
                    break
        for (x, z), segs in need.items():
            for lo, hi in segs:
                for y in range(lo, hi):
                    if self.p.free(x, y, z):
                        self.p.set(x, y, z, PARAPET if y < hi - 1 else PARAPET_TOP)
                        self.parapets.add((x, y, z))

    def light_ring(self, r, y, every, name=LANTERN, skip=()):
        for k in range(0, 360, every):
            if any(in_arc(k, a0, a1) for a0, a1 in skip):
                continue
            x, z = at(r, k)
            if self.place(x, y, z, name):
                pass

    def place(self, x, y, z, name, rot=0):
        """Pose un meuble s'il tient (cases libres, sol plein) et ne gêne aucun passage."""
        cells = pf.footprint(name, rot)
        if any((x + dx, y + dy, z + dz) in self.keep_clear for dx, dy, dz in cells):
            return False
        if not self.p.fits(x, y, z, name, rot):
            return False
        self.p.set(x, y, z, name, rot)
        return True

    # --- gros œuvre ---------------------------------------------------------------------------

    def shell(self):
        p = self.p
        for x, z, d, a in ring(0, R_OUT):
            p.set(x, -1, z, self.floor() if d < R_IN else self.wall())
            for y in range(-4, -1):
                p.set(x, y, z, "Rock_Marble")
            if d >= R_IN:
                for y in range(0, F_DECK - 1):
                    p.set(x, y, z, self.wall())
            for f in (F_LEAKS, F_LIBRARY, F_TRANS, F_LAB, F_LAB + 12, F_DECK):
                p.set(x, f - 1, z, self.floor() if d < R_IN else TRIM)
        # Cœur plein du couloir des fuites, barrage à 240°, remplissage autour de la salle carrée.
        for x, z, d, a in ring(0, R_IN):
            for y in range(F_LEAKS, F_LIBRARY - 1):
                if d < 9 or (d < R_IN and in_arc(a, 234, 246)):
                    p.set(x, y, z, self.wall())
            if max(abs(x), abs(z)) > SQUARE:
                for y in range(F_TRANS, F_LAB - 1):
                    p.set(x, y, z, self.wall())
        # Fenêtres de verre (points de vue fermés) : hall, bibliothèque, laboratoire, fût.
        for y0, y1, step, a_off in ((3, 6, 45, 22), (22, 28, 30, 15), (45, 49, 45, 0), (57, 66, 60, 30)):
            for k in range(a_off, 360 + a_off, step):
                for x, z, d, a in ring(R_IN, R_OUT):
                    if abs(((a - k) + 180) % 360 - 180) < 3.2:
                        for y in range(y0, y1 + 1):
                            p.set(x, y, z, GLASS)

    def court(self):
        """Parvis au pied de la tour : dallage, parapets est, ouest et sud (ouvert sur le pont), porte du hall."""
        p = self.p
        x0, x1, z1 = COURT
        for x in range(x0 - 1, x1 + 2):
            for z in range(8, z1 + 2):
                d, a = polar(x, z)
                if d < R_OUT:
                    continue
                edge = x in (x0 - 1, x1 + 1) or z == z1 + 1
                p.set(x, -1, z, TRIM if (x == 0 and z % 4 == 0) else self.floor())
                if edge and not (z == z1 + 1 and abs(x) <= 2):
                    self.parapet(x, 0, z)
                    if z % 6 == 0 or (z == z1 + 1 and abs(x) in (3, 9)):
                        p.set(x, 2, z, "Deco_Lantern")
                else:
                    self.register(x, z, 0)
        # Porte du hall : arche dorée.
        door = [(x, z) for x in range(-1, 2) for z in range(13, 18)]
        self.door(door, 0, 4)
        for x in (-2, 2):
            for z in (16, 17):
                for y in range(0, 5):
                    p.set(x, y, z, GOLD)
        for x in range(-2, 3):
            p.set(x, 4, 17, "Rock_Gold_Brick_Ornate")

    def hall(self):
        cells = self.helix(200, 300, 11.5, R_IN, F_HALL, F_LEAKS)
        self.hall_ramp = cells
        p = self.p
        # Alambic central : colonne de verre et d'or autour d'un cœur de cristal.
        for y in range(0, 7):
            for x, z, d, a in ring(0, 2.5, 3):
                p.set(x, y, z, "Rock_Crystal_Green_Block" if d < 1 else (GLASS if 1 <= y <= 5 else GOLD))
        for x, z, d, a in ring(0, 1.5, 3):
            p.set(x, 7, z, GOLD)
        p.set(0, 8, 0, "Rock_Gold_Brick_Ornate")
        # Athanors (l'énigme des trois feux viendra avec les pièges), chaudrons, établis d'alchimie.
        for k in (30, 150, 330):
            x, z = at(9, k)
            self.place(x, 0, z, "Bench_Furnace", facing_center(x, z))
        for k in (0, 60, 120, 180):
            x, z = at(12.5, k)
            self.place(x, 0, z, "Alchemy_Cauldron_Big")
        for k in (90 - 28, 90 + 28):
            x, z = at(12.5, k)
            self.place(x, 0, z, "Bench_Alchemy", facing_center(x, z))
        self.light_ring(13.5, 0, 30, skip=((195, 305), (80, 100)))
        for x, z in ((6, 6), (-6, 6), (6, -6), (-6, -6)):
            self.place(x, 9, z, CHANDELIER)

    def leaks(self):
        """Couloir des fuites : anneau de 9 à 14,5, tuyaux au plafond, niches et grilles de vapeur dans le cœur."""
        p = self.p
        y = F_LEAKS
        for x, z, d, a in ring(13.5, R_IN):
            p.set(x, y + 5, z, GOLD)  # conduite qui court au plafond le long du mur
        for k in range(0, 360, 20):
            if in_arc(k, 228, 252) or in_arc(k, 262, 305):
                continue
            x, z = at(8.5, k)
            if self.solid(x, y, z):
                for dy in range(0, 3):
                    p.set(x, y + dy, z, AIR)
                xi, zi = at(7.5, k)
                p.set(xi, y + 1, zi, "Deco_Iron_Bars")  # bouche de vapeur
                p.set(x, y, z, GLOW)
            xo, zo = at(13.8, k + 10)
            for dy in range(0, 5):
                if self.p.free(xo, y + dy, zo):
                    p.set(xo, y + dy, zo, "Rock_Gold_Brick_Pillar_Middle")  # colonne montante
        # Porte ouest vers la serre.
        door = [(x, z) for x in range(-17, -13) for z in range(-1, 2)]
        self.door(door, F_LEAKS)

    def greenhouse(self):
        p = self.p
        cells = {}
        for x, z, d, a in ring(R_OUT, BALCONY_R + 1):
            if not in_arc(a, *BALCONY_ARC):
                continue
            if d < BALCONY_R:
                p.set(x, F_LEAKS - 1, z, TRIM if 19.5 <= d < 20.5 else self.floor())
                p.set(x, F_LEAKS - 2, z, self.wall())
                cells[(x, z)] = 2 * F_LEAKS
                self.register(x, z, 2 * F_LEAKS)
                if d >= 21.5 and int(a) % 24 < 18:  # plates-bandes le long du parapet
                    p.set(x, F_LEAKS, z, "Soil_Grass_Full")
                    del cells[(x, z)]
                    self.walk[(x, z)].discard(2 * F_LEAKS)
                    plant = self.rng.choice(["Plant_Crop_Mushroom_Glowing_Purple", "Plant_Crop_Mushroom_Glowing_Green",
                                             "Plant_Flower_Orchid_Purple", "Plant_Flower_Tall_Cyan", "Plant_Grass_Lush"])
                    p.set(x, F_LEAKS + 1, z, plant)
            else:
                self.parapet(x, F_LEAKS, z)
                if int(a) % 30 == 0 and not in_arc(a, *GREENHOUSE_ARC):
                    p.set(x, F_LEAKS + 2, z, "Deco_Lantern")
            # Corbeaux sous le balcon.
            if d >= BALCONY_R - 1 and int(a) % 15 < 3:
                for k in range(2, 5):
                    p.set(x, F_LEAKS - 1 - k, z, self.wall())
        # Verrière : panneaux sur le parapet et toit de verre, arceaux dorés.
        for x, z, d, a in ring(R_OUT, BALCONY_R + 1):
            if not in_arc(a, *GREENHOUSE_ARC):
                continue
            if d >= BALCONY_R:
                for y in range(F_LEAKS + 2, F_LEAKS + 6):
                    p.set(x, y, z, GOLD if int(a) % 15 < 3 else GLASS)
            p.set(x, F_LEAKS + 6, z, GOLD if int(a) % 15 < 3 else GLASS)
        self.guard(cells)
        # Rampe extérieure de la serre à la porte de la bibliothèque.
        ramp = self.helix(0, 50, R_OUT, 20.5, F_LEAKS, F_LIBRARY, flat=5)
        self.lib_ramp = ramp
        x0, z0 = at(15.5, 50)
        door = {(x, z) for x, z, d, a in ring(R_IN - 0.5, R_OUT + 0.5) if abs(a - 50) < 7}
        self.door(door, F_LIBRARY)
        self.guard(ramp)

    def library(self):
        p = self.p
        ramp = self.helix(70, 205, 11.5, R_IN, F_LIBRARY, F_TRANS, flat=4)
        self.library_ramp = ramp
        # Garde-corps intérieur de la rampe (muret d'un bloc).
        for (x, z), s in ramp.items():
            d, a = polar(x, z)
            if d < 12.5 and s > 2 * F_LIBRARY + 4:
                y = (s + 1) // 2
                if p.free(x, y, z):
                    p.set(x, y, z, PARAPET_TOP)
        # Étagères sur quatre rangs le long du mur, hors rampe, porte et passage secret.
        for x, z, d, a in ring(13.4, R_IN):
            if in_arc(a, 60, 215) or in_arc(a, 40, 60) or in_arc(a, 312, 328) or in_arc(a, 22, 38):
                continue
            for y in range(F_LIBRARY, F_LIBRARY + 4):
                self.place(x, y, z, SHELF, facing_center(x, z))
        # Rayonnages en épis et piles de livres.
        for k in (250, 290, 340):
            for r in range(8, 12):
                x, z = at(r, k)
                for y in (F_LIBRARY, F_LIBRARY + 1):
                    self.place(x, y, z, SHELF, facing_center(x, z))
        for k in range(0, 360, 40):
            x, z = at(6, k + 20)
            self.place(x, F_LIBRARY, z, "Deco_Book_Pile_Large")
        self.place(0, F_TRANS - 2, 0, CHANDELIER)
        self.light_ring(10.5, F_LIBRARY, 45, skip=((60, 215),))
        # Galerie haute : anneau de planches sur corbeaux, avec rayonnages (décor).
        for x, z, d, a in ring(12.5, R_IN):
            if in_arc(a, 60, 215):
                continue
            p.set(x, F_LIBRARY + 7, z, "Wood_Darkwood_Planks")
        for x, z, d, a in ring(13.4, R_IN):
            if in_arc(a, 60, 215):
                continue
            for y in range(F_LIBRARY + 8, F_LIBRARY + 11):
                self.place(x, y, z, SHELF, facing_center(x, z))
        # Salle secrète en encorbellement à 320° (le coffre viendra avec le butin).
        cx, cz = at(19.5, 320)
        y = F_LIBRARY
        for x in range(cx - 3, cx + 4):
            for z in range(cz - 3, cz + 4):
                edge = x in (cx - 3, cx + 3) or z in (cz - 3, cz + 3)
                if polar(x, z)[0] < R_OUT:
                    continue
                p.set(x, y - 1, z, "Wood_Darkwood_Planks")
                p.set(x, y - 2, z, self.wall())
                p.set(x, y + 4, z, self.wall())
                for k in range(0, 4):
                    p.set(x, y + k, z, self.wall() if edge else AIR)
        for x, z, d, a in ring(R_IN - 0.5, R_OUT + 0.6):
            if abs(a - 320) < 4:
                self.door([(x, z)], y, 2)
        self.place(cx, y, cz, GLOW)

    def transmutation(self):
        p = self.p
        y = F_TRANS
        quadrants = {(1, -1): "Rock_Crystal_Red_Block", (-1, -1): "Rock_Crystal_Cyan_Block",
                     (1, 1): "Rock_Crystal_Green_Block", (-1, 1): "Rock_Crystal_Yellow_Block"}
        for x in range(-SQUARE, SQUARE + 1):
            for z in range(-SQUARE, SQUARE + 1):
                if x == 0 or z == 0:
                    p.set(x, y - 1, z, TRIM)
                    continue
                q = quadrants[(1 if x > 0 else -1, 1 if z > 0 else -1)]
                p.set(x, y - 1, z, q if (x + z) % 3 == 0 else self.floor())
        # Couloir depuis la rampe de la bibliothèque, à l'ouest.
        for x in range(-13, -SQUARE):
            for z in range(-6, -2):
                self.door([(x, z)], y)
        # Escalier le long du mur nord, vers le laboratoire.
        stair = {}
        for x in range(-SQUARE, SQUARE + 1):
            for z in (-8, -7):
                stair[(x, z)] = 2 * y + (x + SQUARE)
        for (x, z), s in stair.items():
            self.step(x, z, s, support=0)
            # mur plein sous les marches
            for k in range(y, (s + 1) // 2 - 1):
                p.set(x, k, z, self.wall())
        for (x, z), s in stair.items():
            self.carve(x, z, s)
        for x in range(SQUARE + 1, SQUARE + 4):
            for z in (-8, -7):
                self.register(x, z, 2 * F_LAB)
                self.keep_clear.update((x, F_LAB + k, z) for k in range(3))
        self.trans_stair = stair
        for x, z in ((-SQUARE, SQUARE), (SQUARE, SQUARE), (-SQUARE, -6), (SQUARE, -6)):
            self.place(x, y, z, BRAZIER)
        self.place(0, F_LAB - 2, 0, CHANDELIER)

    def lab(self):
        p = self.p
        y = F_LAB
        # Cuve centrale : liquide vert dans une margelle de verre cerclée d'or.
        for x, z, d, a in ring(0, 4.5, 6):
            if d < 3.5:
                p.set(x, y - 1, z, "Rock_Crystal_Green_Block")
                p.set(x, y - 2, z, self.wall())
            else:
                p.set(x, y, z, GOLD)
                p.set(x, y + 1, z, GLASS)
        for k in range(0, 360, 45):
            x, z = at(9.5, k + 22)
            self.place(x, y, z, "Alchemy_Cauldron", 0)
        for x, z, d, a in ring(13.4, R_IN):
            if in_arc(a, 255, 285) or (x > 0 and -11 <= z <= -5):
                continue
            if int(a) % 40 < 20:
                for k in range(0, 3):
                    self.place(x, y + k, z, SHELF, facing_center(x, z))
        for k in (100, 200):
            x, z = at(12, k)
            self.place(x, y, z, "Bench_Alchemy", facing_center(x, z))
        self.light_ring(11, y, 45, skip=((255, 285), (320, 350)))
        self.place(0, F_LAB + 10, 6, CHANDELIER)
        self.place(0, F_LAB + 10, -6, CHANDELIER)
        # Porte nord vers l'Escalier des vents.
        door = [(x, z) for x in range(-1, 2) for z in range(-17, -13)]
        self.door(door, y)

    def wind_stair(self):
        ramp = self.helix(262, 602, R_OUT, 20.5, F_LAB, F_DECK, flat=8)
        self.wind_ramp = ramp
        p = self.p
        # Corbeaux sous la rampe.
        for (x, z), s in ramp.items():
            d, a = polar(x, z)
            if d >= 19.5 and int(a) % 12 < 2:
                for k in range(2, 5):
                    if p.free(x, s // 2 - 1 - k, z):
                        p.set(x, s // 2 - 1 - k, z, self.wall())
        return ramp

    def observatory(self):
        p = self.p
        y = F_DECK
        for x, z, d, a in ring(0, DECK_R + 1):
            if d < DECK_R:
                p.set(x, y - 1, z, TRIM if 10.5 <= d < 11.5 or 20.5 <= d < 21.5 else self.floor())
                if d >= R_OUT:
                    p.set(x, y - 2, z, self.wall())  # dessous de l'encorbellement
            else:
                self.parapet(x, y, z, 2)
                if int(a) % 30 == 0:
                    p.set(x, y + 2, z, "Deco_Lantern")
        # Trémie : la fin de l'Escalier des vents traverse la terrasse.
        for (x, z), s in self.wind_ramp.items():
            self.carve(x, z, s)
        deck = {}
        for x, z, d, a in ring(0, DECK_R):
            if p.get(x, y - 1, z) not in (None, AIR):
                deck[(x, z)] = 2 * y
                self.register(x, z, 2 * y)
        self.deck = deck
        self.guard(deck)
        self.antechamber()
        self.study()
        self.arches()
        self.chimneys()
        self.crystals()
        self.telescope(340, 17)

    def antechamber(self):
        """Antichambre sur l'arrivée de l'escalier : secteur de 200 à 275°, porte vers la terrasse à 245°."""
        p = self.p
        y = F_DECK
        for x, z, d, a in ring(11, DECK_R):
            if not in_arc(a, 200, 275):
                continue
            edge = d < 12 or not in_arc(a, 202.5, 272.5)
            for k in range(0, 5):
                if edge:
                    p.set(x, y + k, z, self.wall())
            p.set(x, y + 5, z, self.wall())
        for x, z, d, a in ring(11, DECK_R):
            if in_arc(a, 200, 275) and d >= 21.5:
                for k in range(2, 5):
                    p.set(x, y + k, z, self.wall())
        door = [(x, z) for x, z, d, a in ring(10.5, 12.2) if abs(a - 245) < 7]
        self.door(door, y)
        for x, z in door:
            p.set(x, y + 3, z, "Rock_Gold_Brick_Ornate")

    def study(self):
        """Bureau de l'Alchimiste, au sud de la terrasse (ouvert à la mort du boss, plus tard)."""
        p = self.p
        y = F_DECK
        x0, x1, z0, z1 = -5, 5, 13, 21
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                edge = x in (x0, x1) or z in (z0, z1)
                p.set(x, y - 1, z, "Wood_Darkwood_Planks" if not edge else self.wall())
                for k in range(0, 5):
                    p.set(x, y + k, z, self.wall() if edge else AIR)
                p.set(x, y + 5, z, TRIM if edge else self.wall())
                if not edge:
                    self.walk.get((x, z), set()).discard(2 * y)
        for x in (x0 + 1, x1 - 1):
            for z in range(z0 + 1, z1):
                for k in range(0, 3):
                    self.place(x, y + k, z, SHELF, pf.EAST if x < 0 else pf.WEST)
        door = [(x, z0) for x in range(-1, 2)]
        self.door(door, y)
        for x in range(-1, 2):
            self.register(x, z0, 2 * y)
        # Piédestal de la pierre philosophale (la pierre viendra avec le butin), bureau, portail de fin.
        p.set(0, y, 16, "Rock_Gold_Brick_Pillar_Base")
        p.set(0, y + 1, 16, "Rock_Gold_Brick_Ornate")
        self.place(3, y, 15, "Furniture_Human_Ruins_Desk", pf.NORTH)
        self.place(-3, y, 15, GLOW)
        self.place(2, y + 4, 17, "Deco_Lantern_Ceiling")
        self.place(-2, y + 4, 17, "Deco_Lantern_Ceiling")
        for x in range(-1, 2):
            for z in range(18, 21):
                self.keep_clear.update((x, y + k, z) for k in range(4))
        p.set(0, y, 19, "Nakasar_Tower_Exit", pf.NORTH)

    def arches(self):
        """Deux arcs dorés en croix au-dessus de la terrasse, pieds hors de l'antichambre et du bureau."""
        p = self.p
        for k in (10, 155):
            for i in range(-210, 211):
                r = i / 10
                h = math.sqrt(max(0.0, 21.0 ** 2 - r ** 2))
                x, z = round(r * math.cos(math.radians(k))), round(r * math.sin(math.radians(k)))
                y = F_DECK + round(h * 0.9)
                if (x, y, z) not in self.keep_clear and p.get(x, y, z) in (None, AIR):
                    p.set(x, y, z, GOLD)

    def chimneys(self):
        p = self.p
        for k in (35, 125, 300):
            cx, cz = at(25, k)
            for y in range(F_DECK - 14, F_DECK + 16):
                for x in range(cx - 1, cx + 2):
                    for z in range(cz - 1, cz + 2):
                        inner = (x, z) == (cx, cz)
                        if y < F_DECK - 10 and not inner:
                            continue  # pied en encorbellement
                        if not inner or y < F_DECK + 13:
                            p.set(x, y, z, TRIM if y % 8 == 0 else self.wall())
            # bras qui relie la cheminée au bord de la terrasse
            for r in (23, 24):
                x, z = at(r, k)
                p.set(x, F_DECK - 2, z, self.wall())
                p.set(x, F_DECK - 1, z, self.wall())
            p.set(cx, F_DECK + 16, cz, "Nakasar_Tower_Emanation_Smoke")

    def crystals(self):
        """Éclats de cristal en lévitation autour du sommet, et quelques émanations."""
        p = self.p
        for i, k in enumerate(range(15, 360, 60)):
            cx, cz = at(29 + 3 * (i % 2), k)
            cy = F_DECK + 12 + 4 * (i % 3)
            for dy in range(-2, 3):
                w = 1 if abs(dy) < 2 else 0
                for x in range(cx - w, cx + w + 1):
                    for z in range(cz - w, cz + w + 1):
                        p.set(x, cy + dy, z, "Rock_Crystal_Purple_Block" if i % 2 else "Rock_Crystal_Green_Block")
            p.set(cx, cy + 3, cz, "Nakasar_Tower_Emanation_Spiral" if i % 2 else "Nakasar_Tower_Emanation_Motes")
        p.set(0, F_DECK + 22, 0, "Nakasar_Tower_Emanation_Arc")

    def telescope(self, k, r):
        p = self.p
        x0, z0 = at(r, k)
        if (x0, F_DECK, z0) in self.keep_clear:
            return
        p.set(x0, F_DECK, z0, "Rock_Gold_Brick_Pillar_Base")
        p.set(x0, F_DECK + 1, z0, "Rock_Gold_Brick_Pillar_Middle")
        for i in range(0, 5):
            p.set(x0 + (i + 1) // 2, F_DECK + 2 + i // 2, z0 - i // 2, GOLD if i % 2 else "Rock_Gold_Brick_Ornate")

    def checkpoint(self, x, y, z, statue_at):
        """Point de contrôle : statue de lumière entre deux braseros ; le joueur s'arrête en (x, y, z)."""
        sx, sz = statue_at
        for k in range(3):  # la statue peut prendre la place d'un bout de parapet
            if (sx, y + k, sz) in self.parapets:
                self.p.set(sx, y + k, sz, AIR)
        rot = facing_center(sx, sz) if (sx, sz) != (0, 0) else 0
        self.p.set(sx, y - 1, sz, "Rock_Gold_Brick_Ornate")
        if not self.p.fits(sx, y, sz, STATUE, rot):
            raise RuntimeError(f"tour : pas de place pour la statue du point de contrôle {(sx, y, sz)}")
        self.p.set(sx, y, sz, STATUE, rot)
        self.checkpoints.append((x, y, z))

    def build(self):
        self.shell()
        self.court()
        self.hall()
        self.leaks()
        self.greenhouse()
        self.library()
        self.transmutation()
        self.lab()
        self.wind_stair()
        self.observatory()
        self.guard(self.wind_ramp)
        # Points de contrôle : bibliothèque, laboratoire, Escalier des vents, antichambre.
        self.checkpoint(*at3(11, F_LIBRARY, 45), statue_at=at(13.4, 30))
        self.checkpoint(11, F_LAB, -8, statue_at=(9, -10))
        self.checkpoint(*at3(18.5, F_LAB, 272), statue_at=at(19.5, 262))
        self.checkpoint(*at3(16.5, F_DECK, 255), statue_at=at(18.5, 265))
        self.secure()
        return self.p

    def secure(self, rounds=12):
        """Ferme les fuites que le parcours trouve encore : un parapet sur lequel on peut monter (depuis une marche plus
        haute de l'hélice, une jardinière, une lanterne) est rehaussé, et tout bord praticable au-dessus d'une chute de
        plus de 6 blocs reçoit un parapet. Recommence jusqu'à ce que le parcours ne trouve plus rien."""
        p = self.p

        def on_parapet(x, y, z):
            return (x, y, z) in self.parapets or (p.get(x, y, z) == "Deco_Lantern" and (x, y - 1, z) in self.parapets)
        def stack(x, y, z):
            """(bas, haut) de la pile de parapet de la colonne (x, z) qui touche la hauteur y, ou None."""
            for yy in range(y - 2, y + 3):
                if on_parapet(x, yy, z):
                    lo = hi = yy
                    while on_parapet(x, lo - 1, z):
                        lo -= 1
                    while self.solid(x, hi + 1, z) or (x, hi + 1, z) in p.claims:
                        hi += 1  # le parapet peut porter une verrière, un plancher...
                    return lo, hi
            return None

        for _ in range(rounds):
            _, seen = walkable_path(p, START, {})
            raise_to, walls, perched = {}, set(), set()
            for x, s, z in seen:
                foot = s // 2  # bloc des pieds (sur un demi-bloc : le bloc du demi-bloc)
                if on_parapet(x, (s - 1) // 2, z):
                    perched.add((x, s, z))
                    continue
                for dx, dz in DIRS8:
                    nx, nz = x + dx, z + dz
                    st = stack(nx, foot, nz)
                    if st and on_parapet(nx, st[1], nz) and 2 * (st[1] + 1) < s + 4 and p.free(nx, st[1] + 1, nz) and p.free(nx, st[1] + 2, nz):
                        key = (nx, st[0], nz)
                        raise_to[key] = max(raise_to.get(key, st[1]), (s + 5) // 2 - 1)
                        continue
                    if any((nx, foot + k, nz) in self.keep_clear for k in range(2)):
                        continue
                    if foot >= 6 and all(not self.solid(nx, yy, nz) or on_parapet(nx, yy, nz)
                                         for yy in range(foot - 6, foot + 2)):  # vide, ou un parapet où l'on tomberait
                        if p.free(nx, foot + (s % 2), nz):
                            walls.add((nx, foot + (s % 2), nz))
            if not raise_to and not walls:
                if perched:
                    raise RuntimeError(f"tour : on peut marcher sur des parapets {sorted(perched)[:8]}")
                return
            self.secure_log = (sorted(raise_to.items())[:8], sorted(walls)[:8], len(raise_to), len(walls))
            for (x, lo, z), top in raise_to.items():
                hi = lo
                while on_parapet(x, hi + 1, z):
                    hi += 1
                crown = p.get(x, hi, z)
                for y in range(hi, top + 1):
                    if not p.free(x, y + 1, z):
                        break
                    p.set(x, y, z, PARAPET)
                    p.set(x, y + 1, z, crown)
                    self.parapets |= {(x, y, z), (x, y + 1, z)}
            for x, y, z in walls:
                self.parapet(x, y, z, 2)
        raise RuntimeError(f"tour : fuites non refermées {self.secure_log}")


# Salles à atteindre depuis le parvis (x, niveau, z), en plus des points de contrôle.
GOALS = {"hall": (0, F_HALL, 8), "leaks_exit": (-15, F_LEAKS, 0), "balcony_north": (0, F_LEAKS, -20),
         "library": (0, F_LIBRARY, 6), "transmutation": (0, F_TRANS, 0), "lab": (5, F_LAB, 5), "deck": (0, F_DECK, 0),
         "study": (0, F_DECK, 17)}


def build_checked(seed):
    """Construit la tour et vérifie le parcours : chaque salle et chaque point de contrôle est atteignable à pied."""
    tower = Tower(seed)
    prefab = tower.build()
    goals = dict(GOALS)
    for i, c in enumerate(tower.checkpoints):
        goals[f"checkpoint_{i + 1}"] = c
    missing, _ = walkable_path(prefab, START, goals)
    if missing:
        raise RuntimeError(f"tour : inaccessible depuis le parvis : {missing}")
    return tower


def at3(r, y, a):
    x, z = at(r, a)
    return x, y, z


# --- vérification du parcours --------------------------------------------------------------------

PASSABLE_PREFIXES = ("Plant_Grass", "Plant_Flower", "Plant_Crop_Mushroom", "Nakasar_Tower_Emanation", "Deco_Potion")


def passable(name):
    return name in (None, AIR) or name.startswith(PASSABLE_PREFIXES)


def walkable_path(prefab, start, goals, ground_y=0, bounds=(-32, 32, -32, 42)):
    """Parcours en largeur sur les surfaces du prefab (demi-blocs) : un joueur de 2 blocs de haut monte d'un demi-bloc
    en marchant, d'un bloc en sautant, et peut descendre de 4 blocs. Hors du prefab, sous ground_y c'est l'île (plein),
    au-dessus de l'air. Renvoie les buts non atteints."""
    blocks = prefab.blocks
    claims = prefab.claims

    def cell(x, y, z):
        if (x, y, z) in claims:
            return "solid"
        b = blocks.get((x, y, z))
        if b is None:
            return "solid" if y < ground_y else "air"
        name = b[0]
        if passable(name):
            return "air"
        if name.endswith("_Half"):
            return "half"
        return "solid"

    def surfaces(x, z, near):
        """Surfaces praticables (demi-blocs) de la colonne autour de la surface `near`."""
        out = []
        for y in range(near // 2 - 6, near // 2 + 3):
            c = cell(x, y, z)
            if c == "solid" and cell(x, y + 1, z) != "solid":
                s = 2 * (y + 1)
                if cell(x, y + 1, z) == "half":
                    s += 1
                    if cell(x, y + 2, z) == "air" and cell(x, y + 3, z) == "air" and cell(x, y + 4, z) == "air":
                        out.append(s)
                    continue
                if cell(x, y + 1, z) == "air" and cell(x, y + 2, z) == "air":
                    out.append(s)
        return out

    seen = {start}
    queue = deque([start])
    while queue:
        x, s, z = queue.popleft()
        for dx, dz in DIRS4:
            if not (bounds[0] <= x + dx <= bounds[1] and bounds[2] <= z + dz <= bounds[3]):
                continue
            for s2 in surfaces(x + dx, z + dz, s):
                if s2 - s > 2 or s - s2 > 8:
                    continue
                if s2 - s == 2 and cell(x, (s + 1) // 2 + 2, z) == "solid":
                    continue  # pas la place de sauter
                if s2 < s and any(cell(x + dx, y, z + dz) != "air" for y in range((s2 + 1) // 2, s // 2 + 2)):
                    continue  # on ne tombe pas à travers un plancher
                n = (x + dx, s2, z + dz)
                if n not in seen:
                    seen.add(n)
                    queue.append(n)
    reached = {}
    for x, s, z in seen:
        reached.setdefault((x, z), set()).add(s)
    missing = []
    for name, (gx, gy, gz) in goals.items():
        if not any(abs(o - 2 * gy) <= 2 for dx in range(-1, 2) for dz in range(-1, 2)
                   for o in reached.get((gx + dx, gz + dz), ())):
            missing.append(name)
    return missing, seen
