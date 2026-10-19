"""La Tour de l'Alchimiste elle-même (étape 2 du donjon) : prefab de la tour, utilisé par generate_alchemist_tower.py.

Échelle Deepworks (Kevin, 19 octobre 2026) : environ 67 blocs de diamètre (balcons 95) et 220 de haut ;
generate_alchemist_tower.py coupe le prefab en tranches empilées.

Repère du prefab : centré sur l'axe de la tour, y = 0 = première couche d'air au-dessus du sol de l'île (y = -1 : sol).
Les angles sont en degrés : x = r cos(a), z = r sin(a), donc 0 = est, 90 = sud, 180 = ouest, 270 = nord.

Parcours, de bas en haut (niveaux = première couche d'air du sol de chaque salle) :

- parvis au sud, porte du Hall des Alambics (niveau 0) ; rampe le long du mur de 200 à 300° ;
- Couloir des fuites (22) : anneau autour d'un cœur plein, barré à 240°, on en fait les trois quarts jusqu'à la porte
  ouest ; tuyaux, niches et grilles de vapeur (jets et niches de refuge : `traps`) ;
- Serre suspendue (22) : balcon extérieur d'ouest en est par le nord, verrière à l'ouest, belvédère au nord ; une rampe
  extérieure monte de 0 à 50° jusqu'à la porte de la bibliothèque ;
- Bibliothèque (36) : rotonde à deux galeries, étagères, salle secrète en encorbellement à 320° ; rampe de 70 à 205° ;
- Salle des Transmutations (66) : salle carrée en quatre quadrants (feu, glace, acide, foudre) ; escalier le long du
  mur nord vers le laboratoire ;
- Laboratoire (84) : cuve centrale ; porte nord vers l'Escalier des vents ;
- Escalier des vents : rampe extérieure de 262 à 602° (presque un tour), de 84 à l'Observatoire (144) ;
- Observatoire (144) : terrasse ronde au sommet, antichambre sur l'arrivée de l'escalier, Bureau de l'Alchimiste au sud.

Toutes les rampes montent en demi-dalles (pas de bloc orienté à deviner) et tous les bords extérieurs ont un parapet de
2 blocs au moins. `walkable_path` vérifie, hors ligne, qu'on va du parvis au bureau en passant par chaque point de
contrôle. Au bord du vide extérieur, des blocs Barrier marquent au-dessus des parapets, jusqu'à 4 blocs au-dessus de
la plus haute surface voisine, la barrière nécessaire (Kevin, 19 octobre 2026 : on ne saute pas des coursives) ;
generate_alchemist_tower.py les remplace par des volumes de repoussée comme dans Deepworks ; chaque
salle est meublée selon son thème (`decorate`), sans gêner le parcours.
"""
import math
from collections import deque

import generate_prefabs as pf

AIR = pf.AIR
# Échelle de Deepworks (Kevin, 19 octobre 2026) : tout est deux fois plus grand que le premier jet, en largeur comme en
# hauteur, pour garder la pente des rampes (au plus un demi-bloc par bloc).
R_IN = 29.5        # intérieur de la tour : d < R_IN
R_OUT = 33.5       # mur : R_IN <= d < R_OUT
F_HALL, F_LEAKS, F_LIBRARY, F_TRANS, F_LAB, F_DECK = 0, 22, 36, 66, 84, 144
DECK_R = 45.5      # terrasse de l'observatoire : d < DECK_R, parapet jusqu'à DECK_R + 1
BALCONY_R = 47.5   # serre : R_OUT <= d < BALCONY_R, parapet jusqu'à BALCONY_R + 1
BALCONY_ARC = (176, 360)
GREENHOUSE_ARC = (195, 285)
SQUARE = 18        # Salle des Transmutations : |x|, |z| <= SQUARE
COURT_HALF = 16    # parvis : x de -16 à 16
COURT_END = 79     # le parvis va jusqu'à z = 79 ; le pont arrive en z = 80
BRIDGE_HALF = 3    # demi-largeur du pont (generate_alchemist_tower.BRIDGE_HALF)

WALL = [("Rock_Marble_Brick", 7), ("Rock_Marble_Brick_Smooth", 2), ("Rock_Marble_Cobble", 1)]
FLOOR = [("Rock_Marble_Brick_Smooth", 4), ("Rock_Marble_Brick", 3)]
HALF = "Rock_Marble_Brick_Half"
TRIM = "Rock_Gold_Brick_Decorative"
GOLD = "Rock_Gold_Brick"
PARAPET, PARAPET_TOP = "Rock_Marble_Brick", "Rock_Marble_Brick_Wall"
GLASS = "Nakasar_Stained_Glass_Violet"
# Statue des points de contrôle de Deepworks, éteinte ; le volume du point de contrôle la fait changer d'état.
STATUE = "*Dungeon_Checkpoint_Statue_State_Definitions_Inactive"
SHELF = "Furniture_Bookshelf_Single"
LANTERN = "Furniture_Temple_Light_Lantern"
GLOW = "Furniture_Royal_Magic_Potion_Glow"
BRAZIER = "Furniture_Temple_Dark_Brazier"
CHANDELIER = "Furniture_Feran_Chandelier"
BARRIER = "Barrier"  # bloc vanilla plein et invisible (Server/Item/Items/Hypixel/Barrier.json)
# Pièges et énigmes (étape 4, tools/alchemist_traps.py écrit leurs volumes) : sceau alchimique et haie de ronces ferment
# un passage jusqu'à ce que l'énigme soit résolue ; on allume un brasero éteint (athanor, foyer) ou on tire le levier.
SEAL = "Nakasar_Alchemical_Seal"
HEDGE = "Nakasar_Thorn_Hedge"
LEVER = "Nakasar_Valve_Lever"
VALVE = "Nakasar_Tower_Valve"   # vanne de la conduite de gaz du Couloir des fuites (deux blocs de haut)
FOYER = "*Furniture_Temple_Dark_Brazier_State_Definitions_Off"
DOOR = "Nakasar_Tower_Door"   # portes de la tour : elles tombent quand les gardiens d'airain de la cour sont abattus
GATE_BLOCKS = (SEAL, HEDGE, DOOR)
# Hall des Alambics : trois athanors autour du grand alambic, reliés à lui par des conduits d'or incrustés dans le
# sol ; chaque athanor allumé fait briller son conduit et remplit son tube de l'alambic, et les trois ensemble allument
# le conduit et la colonne relais qui montent jusqu'au sceau du Couloir des fuites.
HALL_ATHANOR_ANGLES = (30, 150, 270)
HALL_ATHANOR_R = 13            # brasero de l'athanor
HALL_FURNACE_R = 17    # four de l'athanor, derrière le brasero
ALEMBIC_R = 5             # grand alambic : verre pour 2,5 <= d < ALEMBIC_R
ALEMBIC_TOP = 13
CONDUIT = "Rock_Gold_Brick"            # conduit éteint (incrusté dans le sol)
CONDUIT_LIT = "Rock_Crystal_Purple_Block"
EMANATION_LIT = "Nakasar_Tower_Emanation_Spiral"   # posée au-dessus d'un athanor allumé
EMANATION_FED = "Nakasar_Tower_Emanation_Arc"      # au sommet de l'alambic quand les trois athanors brûlent
RELAY = (306, 20.5)       # colonne relais (angle, rayon), sous le sceau du Couloir des fuites (HALL_SEAL_ARC)
PIPE = "Metal_Goblin_Iron_Pipe_Large"
PIPE_GLOW = "Metal_Goblin_Iron_Pipe_Large_Glowy"   # luit tant que la vanne est ouverte (état Off une fois coupée)
PIPE_THIN = "Metal_Goblin_Iron_Pipe_Long"
LEAK = "VFX_Dungeon_Goblin_Leaking_Pipe"
# Cour : gardiens d'airain sur leurs socles (x, z).
GUARDIANS = ((-8, 44), (8, 44), (-8, 60), (8, 60))
RUBBLE = "Nakasar_Codex_Rubble"  # éboulis de livres et d'étagères, posé en jeu par les volumes du combat du Codex
HALL_SEAL_ARC = (304, 308)    # sceau du couloir des fuites, juste après l'arrivée de la rampe du hall (300°)
JET_ARC = (310, 530)          # bouches de vapeur actives : de l'arrivée à la porte ouest (180°)
SHORTCUT_ARC = (236.5, 243.5)  # barrage du couloir : le levier y ouvre un raccourci
HEDGE_ARC = (72, 84)          # haie de ronces au pied de la rampe de la bibliothèque (elle part de 70°)
FOYERS = {"Fire": (6, -11), "Ice": (-6, -11), "Acid": (14, 14), "Lightning": (-14, 14)}
FLAME_ANGLES = (295, 340, 385, 430, 475, 520, 565)  # angles de l'Escalier des vents (262 à 602°)
GUST_SECTORS = (318, 408, 498, 585)
STRIKE_ANGLES = tuple(range(282, 595, 22))
# Codex vivant (étape 5) : trois pupitres autour de la rotonde, sceau en haut de la rampe de la bibliothèque, pans
# d'étagères qui s'effondrent sous 50 % de vie (hors rampe, portes, point de contrôle et passage secret).
LECTERN = "Rock_Gold_Brick_Ornate"
LECTERN_R = 9.5
LECTERN_ANGLES = (30, 150, 270)
CODEX_SEAL_ARC = (190, 199)
COLLAPSE_ARCS = ((220, 248), (252, 282), (286, 312), (328, 358), (2, 24))
COLLAPSE_R = (21.5, 28.4)
# Chimère du laboratoire (étape 6) : étagères de réactifs (PNJ posés par tower.ChimeraSystem, les homoncules y prennent
# de quoi la régénérer), cases où elle ressort de la cuve, sceau de la porte nord jusqu'à sa mort.
CHIMERA_SHELF_R = 21
CHIMERA_SHELF_ANGLES = (20, 110, 175, 235)
CHIMERA_EXIT_R = 12.5
CHIMERA_EXIT_ANGLES = (30, 120, 150, 210, 240, 330)
CHIMERA_DOOR_Z = -30
# Combat de l'Alchimiste (étape 7), sur la terrasse de l'Observatoire.
ATHANOR_R = 3.6          # athanor central : murs pour d < ATHANOR_R, chambre (où il s'enferme) pour d < ATHANOR_ROOM
ATHANOR_ROOM = 1.6
ALCHEMIST_EXIT_R = 6
PILLAR_R = 17
PILLAR_ANGLES = (20, 150, 295, 340)   # piliers de la Convergence : feu, glace, foudre, racine
HEAL_R = 26
HEAL_ANGLES = (0, 45, 130, 165, 300, 325)
SAFE_R = 28              # points de retour sur la terrasse pour qui tombe dans un trou
DECK_COLLAPSE_ARCS = ((282, 322), (346, 362), (18, 52))  # loin de l'antichambre, du bureau, des pieds des arcs
DECK_COLLAPSE_R = (34.5, 41.4)
STUDY_DOOR_Z = 26
ANTECHAMBER_ARC = (200, 275)

DIRS4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
DIRS8 = DIRS4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))
START = (0, 0, 70)  # parvis devant la porte du hall : (x, surface en demi-blocs, z) dans le repère du prefab


def polar(x, z):
    return math.hypot(x, z), math.degrees(math.atan2(z, x)) % 360


def in_arc(a, a0, a1):
    """L'angle a est-il sur l'arc parcouru dans le sens positif de a0 à a1 (a1 - a0 <= 360) ?"""
    return (a - a0) % 360 <= a1 - a0


def ring(r0, r1, reach=None):
    """Cases (x, z) avec r0 <= d < r1."""
    reach = math.ceil(r1) + 1 if reach is None else reach
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
        self.statues = []        # ((x, y, z), lacet) des statues, dans le même ordre

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
            for y in range(-6, -1):
                p.set(x, y, z, "Rock_Marble")
            if d >= R_IN:
                for y in range(0, F_DECK - 1):
                    p.set(x, y, z, self.wall())
            for f in (F_LEAKS, F_LIBRARY, F_TRANS, F_LAB, F_LAB + 24, F_DECK):
                p.set(x, f - 1, z, self.floor() if d < R_IN else TRIM)
        # Cœur plein du couloir des fuites, barrage à 240°, remplissage autour de la salle carrée.
        for x, z, d, a in ring(0, R_IN):
            for y in range(F_LEAKS, F_LIBRARY - 1):
                if d < 18 or (d < R_IN and in_arc(a, 237, 243)):
                    p.set(x, y, z, self.wall())
            if max(abs(x), abs(z)) > SQUARE:
                for y in range(F_TRANS, F_LAB - 1):
                    p.set(x, y, z, self.wall())
        # Fenêtres de verre (points de vue fermés) : hall, bibliothèque, laboratoire, fût.
        for y0, y1, step, a_off in ((5, 13, 30, 15), (42, 56, 20, 10), (89, 98, 30, 0), (112, 132, 30, 15)):
            for k in range(a_off, 360 + a_off, step):
                for x, z, d, a in ring(R_IN, R_OUT):
                    if abs(((a - k) + 180) % 360 - 180) < 2.2:
                        for y in range(y0, y1 + 1):
                            p.set(x, y, z, GLASS)

    def court(self):
        """Parvis au pied de la tour : dallage, parapets est, ouest et sud (ouvert sur le pont), porte du hall."""
        p = self.p
        x0, x1, z1 = -COURT_HALF, COURT_HALF, COURT_END
        for x in range(x0 - 1, x1 + 2):
            for z in range(16, z1 + 2):
                d, a = polar(x, z)
                if d < R_OUT:
                    continue
                edge = x in (x0 - 1, x1 + 1) or z == z1 + 1
                p.set(x, -1, z, TRIM if (x == 0 and z % 4 == 0) else self.floor())
                if edge and not (z == z1 + 1 and abs(x) <= BRIDGE_HALF):
                    self.parapet(x, 0, z)
                    if z % 8 == 0 or (z == z1 + 1 and abs(x) in (BRIDGE_HALF + 1, x1 + 1)):
                        p.set(x, 2, z, "Deco_Lantern")
                else:
                    self.register(x, z, 0)
        # Porte du hall : arche dorée, fermée par les portes de la tour (5 × 8) au nu extérieur du mur.
        door = [(x, z) for x in range(-2, 3) for z in range(27, 35)]
        self.door(door, 0, 8)
        for x in (-3, 3):
            for z in (32, 33, 34):
                for y in range(0, 9):
                    p.set(x, y, z, GOLD)
        for x in range(-3, 4):
            for z in (32, 33, 34):
                p.set(x, 8, z, "Rock_Gold_Brick_Ornate")
        self.court_door = [(x, y, 33) for x in range(-2, 3) for y in range(0, 8)]
        for x, y, z in self.court_door:
            p.set(x, y, z, DOOR)
        # Socles des gardiens d'airain : dalle d'or ouvragée, lanternes de part et d'autre.
        for gx, gz in GUARDIANS:
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    p.set(gx + dx, -1, gz + dz, "Rock_Gold_Brick_Ornate" if (dx, dz) == (0, 0) else TRIM)

    def hall(self):
        """Hall des Alambics : le grand alambic au centre, trois athanors autour, reliés à lui par des conduits d'or
        incrustés dans le sol, et la colonne relais sous le sceau du Couloir des fuites. Le sol est dégagé autour des
        athanors pour qu'on les voie en entrant."""
        cells = self.helix(200, 300, 23, R_IN, F_HALL, F_LEAKS)
        self.hall_ramp = cells
        p = self.p
        h = self.hall_parts = {"tubes": [], "conduits": [], "athanors": []}
        # Mosaïque du sol : deux cercles d'or autour de l'alambic et au pied des athanors.
        for x, z, d, a in ring(0, 22):
            if 7 <= d < 7.8 or 17.6 <= d < 18.4:
                p.set(x, -1, z, TRIM)
        # Grand alambic : socle, panse de verre, trois tubes vides (un par athanor) autour d'une âme d'or, col et chapiteau.
        for x, z, d, a in ring(0, ALEMBIC_R + 1.5):
            p.set(x, 0, z, "Rock_Gold_Brick_Ornate" if d < ALEMBIC_R else HALF)
        tubes = [at(1.6, k) for k in HALL_ATHANOR_ANGLES]
        for y in range(1, ALEMBIC_TOP):
            for x, z, d, a in ring(0, ALEMBIC_R):
                if (x, z) in tubes:
                    p.set(x, y, z, AIR)
                elif d < 1:
                    p.set(x, y, z, "Rock_Gold_Brick_Pillar_Middle")
                else:
                    p.set(x, y, z, GLASS if (d >= 2.5 or y % 4) else GOLD)
        for x, z in tubes:
            h["tubes"].append([(x, y, z) for y in range(1, ALEMBIC_TOP)])
        for x, z, d, a in ring(0, ALEMBIC_R):
            p.set(x, ALEMBIC_TOP, z, GOLD)
        for x, z, d, a in ring(0, 3.5):
            p.set(x, ALEMBIC_TOP + 1, z, GOLD)
        for x, z, d, a in ring(0, 2):
            p.set(x, ALEMBIC_TOP + 2, z, GLASS)
        p.set(0, ALEMBIC_TOP + 3, 0, "Rock_Gold_Brick_Ornate")
        p.set(0, ALEMBIC_TOP + 4, 0, "Nakasar_Tower_Emanation_Spiral")
        # Athanors : four de marbre cerclé d'or derrière un brasero (l'énigme : `traps`), sur une estrade dorée ; une
        # cheminée d'or monte au plafond, des émanations flottent autour pour qu'on les remarque.
        for k in HALL_ATHANOR_ANGLES:
            fx, fz = at(HALL_FURNACE_R, k)
            for dx in range(-1, 2):
                for dz in range(-1, 2):
                    for y in range(0, 5):
                        corner = abs(dx) == 1 and abs(dz) == 1
                        p.set(fx + dx, y, fz + dz, (GOLD if y in (0, 4) else "Rock_Marble_Brick") if corner or y in (0, 4)
                              else "Rock_Marble_Brick_Smooth")
            mx, mz = at(HALL_FURNACE_R - 1.5, k)
            p.set(mx, 1, mz, "Furniture_Royal_Magic_Potion_Glow")  # gueule du four
            for y in range(5, F_LEAKS - 1):
                p.set(fx, y, fz, "Metal_Gold_Pipe_Large")  # cheminée jusqu'au plafond
            for x, z, d, a in ring(0, 3.6):
                bx, bz = at(HALL_ATHANOR_R, k)
                if not self.solid(bx + x, -1, bz + z) or self.p.get(bx + x, -1, bz + z) != CONDUIT:
                    p.set(bx + x, -1, bz + z, TRIM if d >= 2.6 else "Rock_Marble_Brick_Smooth")
            for j, off in enumerate((-40, 40)):
                ex, ez = at(HALL_ATHANOR_R + 1.5, k + off * 0.35)
                p.set(ex, 2 + j, ez, "Nakasar_Tower_Emanation_Motes")
            # Conduit d'or de l'estrade au pied de l'alambic.
            conduit = sorted({at(r / 2, k) for r in range(2 * (ALEMBIC_R + 2), 2 * (HALL_ATHANOR_R - 3) + 1)})
            for x, z in conduit:
                p.set(x, -1, z, CONDUIT)
            h["conduits"].append([(x, -1, z) for x, z in conduit])
        # Conduit maître et colonne relais : de l'alambic au pied du sceau, la colonne de verre monte au plafond.
        ra, rr = RELAY
        main = sorted({at(r / 2, ra) for r in range(2 * (ALEMBIC_R + 2), int(2 * (rr - 1)) + 1)})
        for x, z in main:
            p.set(x, -1, z, CONDUIT)
        h["main"] = [(x, -1, z) for x, z in main]
        rx, rz = at(rr, ra)
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                p.set(rx + dx, -1, rz + dz, "Rock_Gold_Brick_Ornate")
                for y in range(0, F_LEAKS - 1):
                    if (dx, dz) == (0, 0):
                        p.set(rx, y, rz, AIR if y else "Rock_Gold_Brick_Ornate")
                    else:
                        p.set(rx + dx, y, rz + dz, GOLD if (abs(dx) + abs(dz) == 2 or y % 5 == 0) else GLASS)
        h["relay"] = [(rx, y, rz) for y in range(1, F_LEAKS - 1)]
        floor = h["main"] + [c for cs in h["conduits"] for c in cs]
        self.keep_clear.update((x, y, z) for x, _, z in floor for y in range(0, 3))
        self.light_ring(27.5, 0, 15, skip=((195, 305), (82, 98)))
        for x, z in ((12, 12), (-12, 12), (12, -12), (-12, -12), (0, 18), (0, -18), (18, 0), (-18, 0)):
            self.place(x, 18, z, CHANDELIER)

    def leaks(self):
        """Couloir des fuites : anneau de 9 à 14,5, tuyaux au plafond, niches et grilles de vapeur dans le cœur."""
        p = self.p
        y = F_LEAKS
        for x, z, d, a in ring(27.5, R_IN):
            for dy in (9, 10):
                p.set(x, y + dy, z, GOLD)  # conduite qui court au plafond le long du mur
        for k in range(0, 360, 10):
            if in_arc(k, 232, 248) or in_arc(k, 262, 305):
                continue
            x, z = at(17.5, k)
            if self.solid(x, y, z):
                for dy in range(0, 4):
                    p.set(x, y + dy, z, AIR)
                xi, zi = at(16.5, k)
                p.set(xi, y + 1, zi, "Deco_Iron_Bars")  # bouche de vapeur
                p.set(xi, y + 2, zi, "Deco_Iron_Bars")
                p.set(x, y, z, GLOW)
            xo, zo = at(28, k + 5)
            for dy in range(0, 9):
                if self.p.free(xo, y + dy, zo):
                    p.set(xo, y + dy, zo, "Rock_Gold_Brick_Pillar_Middle")  # colonne montante
        # Porte ouest vers la serre.
        door = [(x, z) for x in range(-35, -27) for z in range(-2, 3)]
        self.door(door, F_LEAKS, 5)

    def greenhouse(self):
        p = self.p
        cells = {}
        for x, z, d, a in ring(R_OUT, BALCONY_R + 1):
            if not in_arc(a, *BALCONY_ARC):
                continue
            if d < BALCONY_R:
                p.set(x, F_LEAKS - 1, z, TRIM if 39.5 <= d < 40.5 else self.floor())
                p.set(x, F_LEAKS - 2, z, self.wall())
                cells[(x, z)] = 2 * F_LEAKS
                self.register(x, z, 2 * F_LEAKS)
                if d >= 44.5 and int(a) % 12 < 9:  # plates-bandes le long du parapet
                    p.set(x, F_LEAKS, z, "Soil_Grass_Full")
                    del cells[(x, z)]
                    self.walk[(x, z)].discard(2 * F_LEAKS)
                    plant = self.rng.choice(["Plant_Crop_Mushroom_Glowing_Purple", "Plant_Crop_Mushroom_Glowing_Green",
                                             "Plant_Flower_Orchid_Purple", "Plant_Flower_Tall_Cyan", "Plant_Grass_Lush"])
                    p.set(x, F_LEAKS + 1, z, plant)
            else:
                self.parapet(x, F_LEAKS, z)
                if int(a) % 15 == 0 and not in_arc(a, *GREENHOUSE_ARC):
                    p.set(x, F_LEAKS + 2, z, "Deco_Lantern")
            # Corbeaux sous le balcon.
            if d >= BALCONY_R - 1 and int(a) % 8 < 2:
                for k in range(2, 9):
                    p.set(x, F_LEAKS - 1 - k, z, self.wall())
        # Verrière : panneaux sur le parapet et toit de verre, arceaux dorés.
        for x, z, d, a in ring(R_OUT, BALCONY_R + 1):
            if not in_arc(a, *GREENHOUSE_ARC):
                continue
            if d >= BALCONY_R:
                for y in range(F_LEAKS + 2, F_LEAKS + 11):
                    p.set(x, y, z, GOLD if int(a) % 8 < 2 else GLASS)
            p.set(x, F_LEAKS + 11, z, GOLD if int(a) % 8 < 2 else GLASS)
        self.guard(cells)
        # Rampe extérieure de la serre à la porte de la bibliothèque.
        ramp = self.helix(0, 50, R_OUT, 41, F_LEAKS, F_LIBRARY, flat=5)
        self.lib_ramp = ramp
        door = {(x, z) for x, z, d, a in ring(R_IN - 0.5, R_OUT + 0.5) if abs(a - 50) < 5}
        self.door(door, F_LIBRARY, 5)
        self.guard(ramp)

    def library(self):
        p = self.p
        ramp = self.helix(70, 205, 23, R_IN, F_LIBRARY, F_TRANS, flat=4)
        self.library_ramp = ramp
        self.library_vault()
        # Garde-corps intérieur de la rampe (muret d'un bloc).
        for (x, z), s in ramp.items():
            d, a = polar(x, z)
            if d < 24.5 and s > 2 * F_LIBRARY + 8:
                y = (s + 1) // 2
                if p.free(x, y, z):
                    p.set(x, y, z, PARAPET_TOP)
        # Étagères sur quatre rangs le long du mur, hors rampe, porte et passage secret.
        for x, z, d, a in ring(28.4, R_IN):
            if in_arc(a, 60, 215) or in_arc(a, 44, 56) or in_arc(a, 315, 325) or in_arc(a, 25, 35):
                continue
            for y in range(F_LIBRARY, F_LIBRARY + 8):
                self.place(x, y, z, SHELF, facing_center(x, z))
        # Rayonnages en épis et piles de livres.
        for k in (235, 255, 275, 295, 340, 0):
            for r in range(15, 24):
                x, z = at(r, k)
                for y in range(F_LIBRARY, F_LIBRARY + 4):
                    self.place(x, y, z, SHELF, facing_center(x, z))
        for k in range(0, 360, 30):
            x, z = at(11, k + 15)
            self.place(x, F_LIBRARY, z, "Deco_Book_Pile_Large")
        self.place(0, F_TRANS - 4, 0, CHANDELIER)
        for x, z in ((12, 0), (-12, 0), (0, 12), (0, -12)):
            self.place(x, F_TRANS - 6, z, CHANDELIER)
        self.light_ring(21, F_LIBRARY, 30, skip=((60, 215),))
        # Galeries hautes : anneaux de planches sur corbeaux, avec rayonnages (décor).
        for g in (14, 22):
            for x, z, d, a in ring(25, R_IN):
                if in_arc(a, 60, 215):
                    continue
                p.set(x, F_LIBRARY + g, z, "Wood_Darkwood_Planks")
            for x, z, d, a in ring(28.4, R_IN):
                if in_arc(a, 60, 215):
                    continue
                for y in range(F_LIBRARY + g + 1, F_LIBRARY + g + 6):
                    self.place(x, y, z, SHELF, facing_center(x, z))
        # Salle secrète en encorbellement à 320° (le coffre viendra avec le butin).
        cx, cz = at(39, 320)
        y = F_LIBRARY
        for x in range(cx - 6, cx + 7):
            for z in range(cz - 6, cz + 7):
                edge = x in (cx - 6, cx + 6) or z in (cz - 6, cz + 6)
                if polar(x, z)[0] < R_OUT:
                    continue
                p.set(x, y - 1, z, "Wood_Darkwood_Planks")
                p.set(x, y - 2, z, self.wall())
                p.set(x, y + 7, z, self.wall())
                for k in range(0, 7):
                    p.set(x, y + k, z, self.wall() if edge else AIR)
        for x, z, d, a in ring(R_IN - 0.5, R_OUT + 0.6):
            if abs(a - 320) < 2.2:
                self.door([(x, z)], y, 3)
        self.place(cx, y, cz, GLOW)

    def library_vault(self):
        """Coupole à gradins sous le plancher de la Salle des Transmutations (Kevin, 19 octobre 2026 : on ne doit plus
        voir le dessous de la salle du dessus) : oculus d'or, trois gradins de caissons clairs semés d'étoiles de
        cristal, seize nervures d'or en saillie, anneaux dorés à chaque gradin. Hors de la coupole, un bandeau ferme le
        haut, sauf au-dessus de la rampe (sa trémie reste ouverte). `vault_low` donne le bloc le plus bas par colonne."""
        p = self.p
        rng = self.rng
        top = F_TRANS - 2
        tiers = ((7, top), (14, top - 1), (20, top - 2), (23, top - 3))
        stars = ["Rock_Crystal_Blue_Block", "Rock_Crystal_Purple_Block", "Rock_Crystal_White_Block"]
        self.vault_low = {}
        for x, z, d, a in ring(0, R_IN):
            if (x, z) in self.library_ramp:
                continue
            if d >= 23:
                if self.p.free(x, top, z) and (x, top, z) not in self.keep_clear:
                    p.set(x, top, z, self.wall())
                    self.vault_low[(x, z)] = top
                continue
            k = next(i for i, (r, _) in enumerate(tiers) if d < r)
            low = tiers[k][1]
            edge = k > 0 and d >= tiers[k - 1][0] and d < tiers[k - 1][0] + 1  # gradin : anneau doré
            rib = k > 0 and min(abs(((a - n) + 180) % 360 - 180) for n in range(0, 360, 360 // 16)) * d * math.pi / 180 < 0.6
            for y in range(low, top + 1):
                p.set(x, y, z, "Rock_Quartzite_Brick")
            if d < 2.5:
                p.set(x, top, z, "Rock_Gold_Brick_Ornate")
            elif d < 4:
                p.set(x, top, z, GOLD)
            elif rib or edge:
                p.set(x, low, z, TRIM if edge else GOLD)
                if k >= 2:
                    p.set(x, low - 1, z, GOLD if rib else TRIM)
                    low -= 1
            else:
                p.set(x, low, z, rng.choice(stars) if rng.random() < 0.05 else "Rock_Quartzite_Brick_Smooth")
            self.vault_low[(x, z)] = low

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
        # Couloir depuis la rampe de la bibliothèque, à l'ouest. Pas de plancher au-dessus des marches de la rampe encore
        # sous ce niveau : il refermait la trémie et l'on butait en haut de l'escalier (Kevin, 19 octobre 2026).
        for x in range(-27, -SQUARE):
            for z in range(-13, -5):
                if self.library_ramp.get((x, z), 2 * y) < 2 * y:
                    for k in range(5):
                        p.set(x, y + k, z, AIR)
                        self.keep_clear.add((x, y + k, z))
                    continue
                self.door([(x, z)], y, 5)
        # Escalier le long du mur nord, vers le laboratoire.
        stair = {}
        for x in range(-SQUARE, SQUARE + 1):
            for z in (-17, -16, -15, -14):
                stair[(x, z)] = 2 * y + (x + SQUARE)
        for (x, z), s in stair.items():
            self.step(x, z, s, support=0)
            # mur plein sous les marches
            for k in range(y, (s + 1) // 2 - 1):
                p.set(x, k, z, self.wall())
        for (x, z), s in stair.items():
            self.carve(x, z, s)
        for x in range(SQUARE + 1, SQUARE + 7):
            for z in (-17, -16, -15, -14):
                self.register(x, z, 2 * F_LAB)
                self.keep_clear.update((x, F_LAB + k, z) for k in range(3))
        self.trans_stair = stair
        for x, z in ((-SQUARE, SQUARE), (SQUARE, SQUARE), (-SQUARE, -12), (SQUARE, -12), (0, SQUARE), (-SQUARE, 0),
                     (SQUARE, 0)):
            self.place(x, y, z, BRAZIER)
        for x, z in ((0, 0), (9, 9), (-9, 9), (9, -9), (-9, -9)):
            self.place(x, F_LAB - 4, z, CHANDELIER)

    def lab(self):
        p = self.p
        y = F_LAB
        # Cuve centrale : liquide vert dans une margelle de verre cerclée d'or.
        for x, z, d, a in ring(0, 9):
            if d < 7.5:
                p.set(x, y - 1, z, "Rock_Crystal_Green_Block")
                p.set(x, y - 2, z, self.wall())
            else:
                p.set(x, y, z, GOLD)
                p.set(x, y + 1, z, GLASS)
        for k in range(0, 360, 30):
            x, z = at(16, k + 15)
            self.place(x, y, z, "Alchemy_Cauldron", 0)
        for x, z, d, a in ring(28.4, R_IN):
            if in_arc(a, 255, 285) or (x > 0 and -22 <= z <= -10):
                continue
            if int(a) % 20 < 10:
                for k in range(0, 6):
                    self.place(x, y + k, z, SHELF, facing_center(x, z))
        for k in (100, 130, 200, 230):
            x, z = at(24, k)
            self.place(x, y, z, "Bench_Alchemy", facing_center(x, z))
        self.light_ring(22, y, 30, skip=((255, 285), (320, 355)))
        for x, z in ((0, 12), (0, -12), (12, 0), (-12, 0)):
            self.place(x, F_LAB + 20, z, CHANDELIER)
        # Porte nord vers l'Escalier des vents.
        door = [(x, z) for x in range(-2, 3) for z in range(-35, -27)]
        self.door(door, y, 5)

    def wind_stair(self):
        ramp = self.helix(262, 602, R_OUT, 41, F_LAB, F_DECK, flat=8)
        self.wind_ramp = ramp
        p = self.p
        # Corbeaux sous la rampe.
        for (x, z), s in ramp.items():
            d, a = polar(x, z)
            if d >= 39.5 and int(a) % 6 < 1:
                for k in range(2, 9):
                    if p.free(x, s // 2 - 1 - k, z):
                        p.set(x, s // 2 - 1 - k, z, self.wall())
        return ramp

    def observatory(self):
        p = self.p
        y = F_DECK
        for x, z, d, a in ring(0, DECK_R + 1):
            if d < DECK_R:
                p.set(x, y - 1, z, TRIM if 21.5 <= d < 22.5 or 41.5 <= d < 42.5 else self.floor())
                if d >= R_OUT:
                    p.set(x, y - 2, z, self.wall())  # dessous de l'encorbellement
            else:
                self.parapet(x, y, z, 2)
                if int(a) % 15 == 0:
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
        self.telescope(340, 34)

    def antechamber(self):
        """Antichambre sur l'arrivée de l'escalier : secteur de 200 à 275°, porte vers la terrasse à 245°."""
        p = self.p
        y = F_DECK
        for x, z, d, a in ring(22, DECK_R):
            if not in_arc(a, 200, 275):
                continue
            edge = d < 24 or not in_arc(a, 201.5, 273.5)
            for k in range(0, 10):
                if edge:
                    p.set(x, y + k, z, self.wall())
            p.set(x, y + 10, z, self.wall())
        for x, z, d, a in ring(22, DECK_R):
            if in_arc(a, 200, 275) and d >= 43.5:
                for k in range(3, 10):
                    p.set(x, y + k, z, self.wall())
        door = [(x, z) for x, z, d, a in ring(21.5, 24.6) if abs(a - 245) < 5]
        self.door(door, y, 5)
        for x, z in door:
            p.set(x, y + 5, z, "Rock_Gold_Brick_Ornate")

    def study(self):
        """Bureau de l'Alchimiste, au sud de la terrasse (ouvert à la mort du boss, plus tard)."""
        p = self.p
        y = F_DECK
        x0, x1, z0, z1 = -10, 10, 26, 42
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                edge = x in (x0, x1) or z in (z0, z1)
                p.set(x, y - 1, z, "Wood_Darkwood_Planks" if not edge else self.wall())
                for k in range(0, 10):
                    p.set(x, y + k, z, self.wall() if edge else AIR)
                p.set(x, y + 10, z, TRIM if edge else self.wall())
                if not edge:
                    self.walk.get((x, z), set()).discard(2 * y)
        for x in (x0 + 1, x1 - 1):
            for z in range(z0 + 1, z1):
                for k in range(0, 6):
                    self.place(x, y + k, z, SHELF, pf.EAST if x < 0 else pf.WEST)
        door = [(x, z0) for x in range(-2, 3)]
        self.door(door, y, 5)
        for x in range(-2, 3):
            self.register(x, z0, 2 * y)
        # Piédestal de la pierre philosophale (la pierre viendra avec le butin), bureau, portail de fin.
        p.set(0, y, 32, "Rock_Gold_Brick_Pillar_Base")
        p.set(0, y + 1, 32, "Rock_Gold_Brick_Ornate")
        self.place(6, y, 30, "Furniture_Human_Ruins_Desk", pf.NORTH)
        self.place(-6, y, 30, GLOW)
        for x in (-5, 5):
            for z in (31, 37):
                self.place(x, y + 9, z, "Deco_Lantern_Ceiling")
        for x in range(-1, 2):
            for z in range(37, 41):
                self.keep_clear.update((x, y + k, z) for k in range(4))
        p.set(0, y, 38, "Nakasar_Tower_Exit", pf.NORTH)

    def arches(self):
        """Deux arcs dorés en croix au-dessus de la terrasse, pieds hors de l'antichambre et du bureau."""
        p = self.p
        for k in (10, 155):
            for i in range(-420, 421):
                r = i / 10
                h = math.sqrt(max(0.0, 42.0 ** 2 - r ** 2))
                x, z = round(r * math.cos(math.radians(k))), round(r * math.sin(math.radians(k)))
                y = F_DECK + round(h * 0.9)
                for dy in (0, 1):
                    if (x, y + dy, z) not in self.keep_clear and p.get(x, y + dy, z) in (None, AIR):
                        p.set(x, y + dy, z, GOLD)

    def chimneys(self):
        p = self.p
        for k in (35, 125, 300):
            cx, cz = at(50, k)
            for y in range(F_DECK - 28, F_DECK + 32):
                for x in range(cx - 2, cx + 3):
                    for z in range(cz - 2, cz + 3):
                        inner = abs(x - cx) <= 1 and abs(z - cz) <= 1
                        if y < F_DECK - 20 and not inner:
                            continue  # pied en encorbellement
                        if not inner or y < F_DECK + 26:
                            p.set(x, y, z, TRIM if y % 8 == 0 else self.wall())
            # bras qui relie la cheminée au bord de la terrasse
            for r in range(46, 49):
                for w in (-1, 0, 1):
                    x, z = at(r, k + w * 1.2)
                    p.set(x, F_DECK - 2, z, self.wall())
                    p.set(x, F_DECK - 1, z, self.wall())
            p.set(cx, F_DECK + 32, cz, "Nakasar_Tower_Emanation_Smoke")

    def crystals(self):
        """Éclats de cristal en lévitation autour du sommet, et quelques émanations."""
        p = self.p
        for i, k in enumerate(range(15, 360, 60)):
            cx, cz = at(58 + 6 * (i % 2), k)
            cy = F_DECK + 24 + 8 * (i % 3)
            for dy in range(-5, 6):
                w = 2 if abs(dy) < 3 else (1 if abs(dy) < 5 else 0)
                for x in range(cx - w, cx + w + 1):
                    for z in range(cz - w, cz + w + 1):
                        p.set(x, cy + dy, z, "Rock_Crystal_Purple_Block" if i % 2 else "Rock_Crystal_Green_Block")
            p.set(cx, cy + 6, cz, "Nakasar_Tower_Emanation_Spiral" if i % 2 else "Nakasar_Tower_Emanation_Motes")
        p.set(0, F_DECK + 44, 0, "Nakasar_Tower_Emanation_Arc")

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
        """Point de contrôle : statue de Deepworks sur un socle doré (son volume est écrit par generate_alchemist_tower) ;
        le joueur s'arrête en (x, y, z)."""
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
        self.statues.append(((sx, y, sz), rot))
        # Le décor laisse libre l'arrêt du joueur.
        self.keep_clear.update((x + dx, y + k, z + dz) for dx in range(-1, 2) for dz in range(-1, 2) for k in range(3)
                               if self.p.free(x + dx, y + k, z + dz))

    # --- mobs (étape 3) ---------------------------------------------------------------------------

    def spawn_cell(self, x, y, z, height=3, reach=6):
        """Case libre la plus proche de (x, y, z) au même niveau : sol plein dessous, `height` blocs d'air au-dessus."""
        best = None
        for dx in range(-reach, reach + 1):
            for dz in range(-reach, reach + 1):
                cx, cz = x + dx, z + dz
                if not self.solid(cx, y - 1, cz) or (cx, y, cz) in self.keep_clear:
                    continue
                if all(self.p.free(cx, y + k, cz) for k in range(height)):
                    d = dx * dx + dz * dz
                    if best is None or d < best[0]:
                        best = (d, cx, cz)
        if best is None:
            raise RuntimeError(f"tour : pas de place pour un mob près de {(x, y, z)}")
        return best[1], best[2]

    def spawner(self, role, x, y, z, height=3):
        cx, cz = self.spawn_cell(x, y, z, height)
        self.p.set(cx, y, cz, SPAWNER_PREFIX + role)
        self.spawners.append((role, (cx, y, cz)))

    def ramp_cell(self, angle, d_target=37.0):
        """Case de l'Escalier des vents la plus proche de l'angle donné (degrés), et son premier bloc d'air."""
        best = None
        for (x, z), s in self.wind_ramp.items():
            d, a = polar(x, z)
            score = abs((a - angle + 180) % 360 - 180) * 2 + abs(d - d_target)
            if best is None or score < best[0]:
                best = (score, x, (s + 1) // 2, z)
        return best[1:]

    def mobs(self):
        """Blocs d'apparition des mobs (tools/generate_tower_mobs.py), salle par salle. Peu de mobs dans les phases de
        pièges (Couloir des fuites, Escalier des vents) pour qu'on lise bien le rythme des pièges."""
        self.spawners = []
        for role, (r, y, a), h in MOB_LAYOUT:
            self.spawner(role, *at3(r, y, a), height=h)
        for role, xyz, h in MOB_FIXED:
            self.spawner(role, *xyz, height=h)
        # Gardiens d'airain sur leurs socles de la cour : les abattre tous ouvre les portes de la tour (CourtGuardSystem).
        for gx, gz in GUARDIANS:
            self.spawner("Brass_Guardian", gx, 0, gz, height=5)
        # Le Codex vivant flotte au centre de la rotonde, entre ses trois pupitres (case réservée par `codex`).
        self.p.set(0, F_LIBRARY, 0, SPAWNER_PREFIX + "Living_Codex")
        self.spawners.append(("Living_Codex", (0, F_LIBRARY, 0)))
        # La Chimère rôde au sud de la cuve, face à l'arrivée de l'escalier des transmutations.
        sx, sy, sz = self.trap["chimera"]["spawn"]
        self.p.set(sx, sy, sz, SPAWNER_PREFIX + "Lab_Chimera")
        self.spawners.append(("Lab_Chimera", (sx, sy, sz)))
        # L'Alchimiste attend sur la terrasse, face à la porte de l'antichambre (case réservée par `alchemist`).
        sx, sy, sz = self.trap["alchemist"]["spawn"]
        self.p.set(sx, sy, sz, SPAWNER_PREFIX + "Alchemist")
        self.spawners.append(("Alchemist", (sx, sy, sz)))
        # Gargouilles au-dessus de l'Escalier des vents : elles volent, on les pose deux blocs au-dessus des marches.
        for angle in GARGOYLE_ANGLES:
            x, y, z = self.ramp_cell(angle)
            if not all(self.p.free(x, y + k, z) for k in range(4)):
                raise RuntimeError(f"tour : pas de place pour une gargouille en {(x, y, z)}")
            self.p.set(x, y + 2, z, SPAWNER_PREFIX + "Tower_Gargoyle")
            self.spawners.append(("Tower_Gargoyle", (x, y + 2, z)))

    # --- pièges et énigmes (étape 4) --------------------------------------------------------------

    def seal(self, cells, y0, y1, force=False):
        """Sceau alchimique sur les colonnes (x, z), de y0 à y1 exclu (sur l'air seulement, sauf force) ; renvoie ses
        blocs. Le volume du sceau le dissout quand l'énigme est résolue."""
        out = []
        for x, z in cells:
            for y in range(y0, y1):
                if force or self.p.free(x, y, z):
                    self.p.set(x, y, z, SEAL)
                    out.append((x, y, z))
        return out

    def usable(self, x, y, z, name, rot=0, plinth="Rock_Gold_Brick_Ornate"):
        """Bloc à utiliser (brasero éteint, levier), sur un socle doré ; décor et mobs lui laissent la place autour."""
        if plinth:
            self.p.set(x, y - 1, z, plinth)
        if not self.p.fits(x, y, z, name, rot):
            raise RuntimeError(f"tour : pas de place pour {name} en {(x, y, z)}")
        self.p.set(x, y, z, name, rot)
        self.keep_clear.update((x + dx, y + k, z + dz) for dx in range(-1, 2) for dz in range(-1, 2) for k in range(3)
                               if self.p.free(x + dx, y + k, z + dz))
        return x, y, z

    def traps(self):
        """Blocs des pièges et des énigmes ; `self.trap` garde leurs positions pour tools/alchemist_traps.py."""
        t = self.trap = {}
        p = self.p
        # Hall des Alambics : trois athanors éteints devant les fours. Tant qu'ils ne brûlent pas tous les trois, le
        # sceau ferme le Couloir des fuites juste après l'arrivée de la rampe.
        t["athanors"] = [self.usable(*at3(HALL_ATHANOR_R, F_HALL, k), FOYER) for k in HALL_ATHANOR_ANGLES]
        t["hall"] = self.hall_parts
        t["court_door"] = self.court_door
        t["hall_seal"] = self.seal([(x, z) for x, z, d, a in ring(18, R_IN) if in_arc(a, *HALL_SEAL_ARC)],
                                   F_LEAKS, F_LIBRARY - 1)
        # Couloir des fuites : les bouches de vapeur jettent par groupes de trois (A et B en alternance) ; entre deux
        # groupes, une niche de refuge creusée dans le mur extérieur (la colonne montante qui la masquait part).
        vents = sorted((k for k in range(0, 360, 10)
                        if in_arc(k, *JET_ARC) and p.get(*at3(17.5, F_LEAKS, k)) == GLOW),
                       key=lambda k: (k - JET_ARC[0]) % 360)
        t["jets"] = [(k, "A" if (i // 3) % 2 == 0 else "B") for i, k in enumerate(vents)]
        t["niches"] = []
        for i in range(3, len(vents), 3):
            b = (vents[i] - 5) % 360
            px, pz = at(28, b)
            for y in range(F_LEAKS, F_LEAKS + 9):
                if p.get(px, y, pz) == "Rock_Gold_Brick_Pillar_Middle":
                    p.set(px, y, pz, AIR)
            for x, z, d, a in ring(R_IN - 0.5, 32.3):
                if abs((a - b + 180) % 360 - 180) * d * math.pi / 180 >= 1.6:
                    continue
                for y in range(F_LEAKS, F_LEAKS + 3):
                    p.set(x, y, z, AIR)
                    self.keep_clear.add((x, y, z))
                if not self.solid(x, F_LEAKS - 1, z):
                    p.set(x, F_LEAKS - 1, z, TRIM)
            p.set(*at3(31, F_LEAKS + 2, b), "Furniture_Royal_Magic_Potion_Glow_Ceiling")
            t["niches"].append(b)
        # Au fond, derrière la porte ouest, le levier coupe la vanne : les jets cessent et le barrage de 240° s'ouvre
        # en raccourci vers l'arrivée de la rampe du hall.
        lx, lz = at(25, 220)
        t["lever"] = self.usable(lx, F_LEAKS, lz, VALVE, facing_center(lx, lz), plinth=None)
        # Tuyauterie de la vanne : la conduite de gaz luisante monte du sol au plafond juste derrière la vanne, entre deux
        # grosses conduites et deux tuyaux fins ; deux fuites crachent de la vapeur tant que la vanne est ouverte.
        top = F_LIBRARY - 2
        for y in range(F_LEAKS + 2, top + 1):  # la vanne (deux blocs de haut) est montée sur sa conduite
            p.set(lx, y, lz, PIPE)
        glow, leaks = [], []
        for r, da, name in ((26.6, 0, PIPE_GLOW), (27.4, -5, PIPE), (27.4, 5, PIPE), (28.4, -9, PIPE_THIN),
                            (28.4, 9, PIPE_THIN)):
            px, pz = at(r, 220 + da)
            for y in range(F_LEAKS, top + 1):
                p.set(px, y, pz, name)
                if name == PIPE_GLOW:
                    glow.append((px, y, pz))
        for da, dy in ((-3, 3), (3, 6)):
            vx, vz = at(25.6, 220 + da)
            if p.free(vx, F_LEAKS + dy, vz):
                p.set(vx, F_LEAKS + dy, vz, LEAK)
                leaks.append((vx, F_LEAKS + dy, vz))
        t["valve_pipes"], t["valve_leaks"] = glow, leaks
        t["shortcut_seal"] = self.seal([(x, z) for x, z, d, a in ring(20.5, 27.5) if in_arc(a, *SHORTCUT_ARC)],
                                       F_LEAKS, F_LEAKS + 4, force=True)
        # Serre suspendue : nappes de spores qui ralentissent.
        t["spores"] = [(x, F_LEAKS, z) for x, z in (self.spawn_cell(*at3(40, F_LEAKS, a), reach=3)
                                                    for a in (205, 225, 245, 265, 285))]
        # Bibliothèque : une haie de ronces barre le pied de la rampe, jusqu'à ce que la rampe soit trop haute pour qu'on
        # y saute depuis le sol ; le brasero éteint devant elle y met le feu. Des livres tombent des rayonnages.
        hedge = []
        for x, z, d, a in ring(18, R_IN):
            if not in_arc(a, *HEDGE_ARC):
                continue
            s = self.library_ramp.get((x, z))
            y0 = (s + 1) // 2 if s is not None else F_LIBRARY
            for y in range(y0, y0 + 4):
                if p.free(x, y, z):
                    p.set(x, y, z, HEDGE)
                    hedge.append((x, y, z))
        t["hedge"] = hedge
        t["hedge_brazier"] = self.usable(*at3(20, F_LIBRARY, 62), FOYER)
        t["books"] = [(x, F_LIBRARY, z) for x, z in
                      (self.spawn_cell(*at3(13 if i % 2 else 18, F_LIBRARY, a), reach=3)
                       for i, a in enumerate((15, 50, 100, 145, 190, 225, 245, 265, 290, 315)))]
        # Salle des Transmutations : un foyer éteint par quadrant ; le sceau ferme le pied de l'escalier du laboratoire
        # (les marches de x = -15 et -14, trop hautes pour qu'on y saute depuis le sol de la salle).
        t["foyers"] = {el: self.usable(x, F_TRANS, z, FOYER) for el, (x, z) in FOYERS.items()}
        t["trans_seal"] = []
        for (x, z), s in sorted(self.trans_stair.items()):
            if x in (-15, -14):
                t["trans_seal"] += self.seal([(x, z)], (s + 1) // 2, F_LAB - 1)
        # Escalier des vents : bouches de flammes dans le mur de la tour, secteurs de rafales (vers le mur, jamais vers le
        # vide), points d'impact de la foudre.
        t["flames"] = []
        for i, a in enumerate(FLAME_ANGLES):
            cells = [self.ramp_cell(a, r) for r in (35.5, 39.0)]
            nx, nz = at(33, a)
            ny = cells[0][1] + 1
            p.set(nx, ny, nz, "Rock_Gold_Brick_Ornate")
            t["flames"].append((a, "A" if i % 2 == 0 else "B", cells, (nx, ny, nz)))
        t["gusts"] = [(a, "A" if i % 2 == 0 else "B", [self.ramp_cell(a + k, 37.2) for k in (-10, -5, 0, 5, 10)])
                      for i, a in enumerate(GUST_SECTORS)]
        t["strikes"] = [self.ramp_cell(a, 35.5 if i % 2 else 38.8) for i, a in enumerate(STRIKE_ANGLES)]

    # --- Codex vivant (étape 5) -------------------------------------------------------------------

    def codex(self):
        """Arène du Codex vivant, au centre de la rotonde de la bibliothèque ; `self.trap["codex"]` garde ses positions
        pour tools/alchemist_traps.py et TowerLayout.java : trois pupitres (le Codex y ouvre ses chapitres), le sceau
        qui ferme le haut de la rampe jusqu'à sa mort, et les éboulis des pans d'étagères qui s'effondrent."""
        p = self.p
        y = F_LIBRARY
        lecterns = []
        for a in LECTERN_ANGLES:
            x, z = at(LECTERN_R, a)
            if not p.free(x, y, z):
                raise RuntimeError(f"tour : pas de place pour un pupitre du Codex en {(x, y, z)}")
            p.set(x, y, z, LECTERN)
            lecterns.append((x, y, z))
            # Le chapitre flotte au-dessus du pupitre : le décor laisse la place et le passage autour.
            self.keep_clear.update((x + dx, y + k, z + dz) for dx in range(-1, 2) for dz in range(-1, 2)
                                   for k in range(4) if (dx, dz, k) != (0, 0, 0))
        # Le Codex flotte au centre : rien n'y est posé.
        self.keep_clear.update((x, y + k, z) for x in range(-3, 4) for z in range(-3, 4) for k in range(5)
                               if math.hypot(x, z) < 3.5)
        seal = []
        for (x, z), s in sorted(self.library_ramp.items()):
            if in_arc(polar(x, z)[1], *CODEX_SEAL_ARC):
                seal += self.seal([(x, z)], (s + 1) // 2, F_TRANS + 3)
        rubble = []
        for a0, a1 in COLLAPSE_ARCS:
            cells = []
            for x, z, d, a in ring(*COLLAPSE_R):
                if not in_arc(a, a0, a1) or not self.solid(x, y - 1, z):
                    continue
                for k in range(2 if d >= 25 else 1):
                    if not p.free(x, y + k, z) or (x, y + k, z) in self.keep_clear:
                        break
                    cells.append((x, y + k, z))
                    self.keep_clear.add((x, y + k, z))
            rubble.append(cells)
        self.trap["codex"] = {"center": (0, y, 0), "lecterns": lecterns, "seal": seal, "rubble": rubble}

    # --- Chimère du laboratoire (étape 6) ---------------------------------------------------------

    def chimera(self):
        """Arène de la Chimère, tout le laboratoire autour de la cuve centrale ; `self.trap["chimera"]` garde ses
        positions pour tools/alchemist_traps.py et TowerLayout.java : les étagères de réactifs (PNJ posés en jeu), les
        cases libres où elle ressort de la cuve, et le sceau de la porte nord (vers l'Escalier des vents) qui tient
        jusqu'à sa mort."""
        y = F_LAB
        shelves = []
        for a in CHIMERA_SHELF_ANGLES:
            x, z = self.spawn_cell(*at3(CHIMERA_SHELF_R, y, a), height=3, reach=3)
            shelves.append((x, y, z))
            # L'étagère tient sur une case ; le décor laisse la place et le passage autour.
            self.keep_clear.update((x + dx, y + k, z + dz) for dx in range(-1, 2) for dz in range(-1, 2) for k in range(3))
        exits = []
        for a in CHIMERA_EXIT_ANGLES:
            x, z = self.spawn_cell(*at3(CHIMERA_EXIT_R, y, a), height=3, reach=3)
            exits.append((x, y, z))
            self.keep_clear.update((x + dx, y + k, z + dz) for dx in range(-2, 3) for dz in range(-2, 3) for k in range(3))
        # Elle rôde au sud de la cuve, face à l'arrivée de l'escalier des transmutations : place libre pour sa carrure.
        sx, sz = self.spawn_cell(*at3(18, y, 70), height=4, reach=3)
        self.keep_clear.update((sx + dx, y + k, sz + dz) for dx in range(-2, 3) for dz in range(-3, 4) for k in range(4))
        seal = self.seal([(x, CHIMERA_DOOR_Z) for x in range(-2, 3)], y, y + 5)
        if len(seal) != 25:
            raise RuntimeError(f"tour : le sceau de la Chimère ne ferme pas la porte nord ({len(seal)} blocs)")
        self.trap["chimera"] = {"vat": (0, y, 0), "spawn": (sx, y, sz), "shelves": shelves, "exits": exits, "seal": seal}

    # --- l'Alchimiste (étape 7) --------------------------------------------------------------------

    def alchemist(self):
        """Arène de l'Alchimiste, toute la terrasse de l'Observatoire ; `self.trap["alchemist"]` garde ses positions pour
        tools/alchemist_traps.py et TowerLayout.java :
        - l'athanor au centre : un four d'or et de verre dont la chambre (3 × 3, 5 de haut) l'enferme au Grand Œuvre ;
        - les cases libres autour où il en ressort, les quatre piliers de la Convergence, les fioles de soin ;
        - les pans du rebord en encorbellement qui s'effondrent (blocs du sol et du dessous), loin de l'antichambre, du
          bureau et de l'arrivée de l'Escalier des vents ;
        - le levier du mode difficile dans l'antichambre et le sceau de la porte du bureau, qui tient jusqu'à sa mort."""
        p = self.p
        y = F_DECK
        # Athanor : murs d'or, fenêtres de verre violet, coupole et cheminée.
        for x, z, d, a in ring(0, ATHANOR_R):
            if d < ATHANOR_ROOM:
                p.set(x, y - 1, z, "Rock_Crystal_Purple_Block")
                for k in range(5):
                    p.set(x, y + k, z, AIR)
                    self.keep_clear.add((x, y + k, z))
                p.set(x, y + 5, z, GOLD)
            else:
                window = int(a + 22.5) % 90 < 30
                for k in range(6):
                    p.set(x, y + k, z, GLASS if window and 1 <= k <= 3 else (TRIM if k in (0, 5) else GOLD))
                if d < ATHANOR_R - 1:
                    p.set(x, y + 6, z, TRIM)
            self.keep_clear.update((x, y + k, z) for k in range(12))
        for k in range(6, 11):
            p.set(0, y + k, 0, "Rock_Gold_Brick_Pillar_Middle")
        p.set(0, y + 11, 0, "Nakasar_Tower_Emanation_Smoke")
        # Le décor laisse un tour libre autour de l'athanor.
        self.keep_clear.update((x, y + k, z) for x, z, d, a in ring(ATHANOR_R, ATHANOR_R + 2.5) for k in range(4))

        def spot(r, a, height=3, reach=2, clear=1):
            x, z = self.spawn_cell(*at3(r, y, a), height=height, reach=reach)
            self.keep_clear.update((x + dx, y + k, z + dz) for dx in range(-clear, clear + 1)
                                   for dz in range(-clear, clear + 1) for k in range(height))
            return x, y, z

        exits = [spot(ALCHEMIST_EXIT_R, a) for a in range(0, 360, 45)]
        pillars = [spot(PILLAR_R, a, height=4) for a in PILLAR_ANGLES]
        heals = [spot(HEAL_R, a) for a in HEAL_ANGLES]
        spawn = spot(10, 245, height=3, clear=1)
        # Pans du rebord : le sol (y - 1) et le dessous de l'encorbellement (y - 2), seulement là où le sol est libre.
        collapse = []
        for a0, a1 in DECK_COLLAPSE_ARCS:
            cells = []
            for x, z, d, a in ring(*DECK_COLLAPSE_R):
                if not in_arc(a, a0, a1) or p.get(x, y - 1, z) not in [n for n, _ in FLOOR]:
                    continue
                if any(not p.free(x, y + k, z) for k in range(3)):
                    continue
                cells.append((x, y - 1, z))
                if p.get(x, y - 2, z) in [n for n, _ in WALL]:
                    cells.append((x, y - 2, z))
                self.keep_clear.update((x, y + k, z) for k in range(4))
            if len(cells) < 40:
                raise RuntimeError(f"tour : pan du rebord trop petit ({a0}-{a1}° : {len(cells)} blocs)")
            collapse.append(cells)
        safe = []
        for a in range(0, 360, 15):
            if in_arc(a, *ANTECHAMBER_ARC) or in_arc(a, 60, 120):
                continue
            x, z = at(SAFE_R, a)
            if self.solid(x, y - 1, z) and all(p.free(x, y + k, z) for k in range(2)):
                safe.append((x, y, z))
        # Levier du mode difficile, dans l'antichambre, avant la porte de la terrasse.
        lx, lz = at(31, 228)
        lever = self.usable(lx, y, lz, LEVER, facing_center(lx, lz), plinth=None)
        seal = self.seal([(x, STUDY_DOOR_Z) for x in range(-2, 3)], y, y + 5)
        if len(seal) != 25:
            raise RuntimeError(f"tour : le sceau du bureau ne ferme pas sa porte ({len(seal)} blocs)")
        self.trap["alchemist"] = {"center": (0, y, 0), "exits": exits, "pillars": pillars, "heals": heals,
                                  "spawn": spawn, "collapse": collapse, "safe": safe, "lever": lever, "seal": seal}

    # --- décor -----------------------------------------------------------------------------------

    def hang(self, x, y, z, name, rot=0):
        """Pend un lustre ou une lanterne au plafond : cases libres, plafond plein juste au-dessus de (x, y, z)."""
        cells = pf.footprint(name, rot)
        if any((x + dx, y + dy, z + dz) in self.keep_clear or not self.p.free(x + dx, y + dy, z + dz)
               or (x + dx, y + dy, z + dz) in self.p.claims for dx, dy, dz in cells):
            return False
        if not self.solid(x, y + 1, z):
            return False
        self.p.set(x, y, z, name, rot)
        return True

    def chain(self, x, y, z, length, name="Deco_Iron_Chains_Vertical", end=None):
        """Chaîne (ou liane) qui pend du plafond plein en y + 1, terminée par `end` (lanterne...)."""
        if not self.solid(x, y + 1, z):
            return
        for k in range(length):
            cell = (x, y - k, z)
            if cell in self.keep_clear or not self.p.free(*cell):
                return
            self.p.set(*cell, end if (end and k == length - 1) else name)

    def table(self, x, y, z, name, tops, chairs=None):
        """Table de 2 × 2 (coin nord-ouest en x, z) garnie de `tops` (un objet par case du dessus), chaises autour."""
        if not self.place(x, y, z, name):
            return False
        for (dx, dz), top in zip(((0, 0), (1, 0), (0, 1), (1, 1)), tops):
            if top:
                self.place(x + dx, y + 1, z + dz, top)
        if chairs:
            for cx, cz, rot in ((x - 1, z, pf.EAST), (x + 2, z + 1, pf.WEST), (x + 1, z - 1, pf.SOUTH),
                                (x, z + 2, pf.NORTH)):
                self.place(cx, y, cz, chairs, rot)
        return True

    def flask(self, cx, y, cz, liquid="Rock_Crystal_Green_Block", height=4):
        """Alambic : socle d'or, panse de verre au cœur de cristal coloré, col d'or et émanation au sommet."""
        cells = [(cx + dx, y + k, cz + dz) for dx in range(-1, 2) for dz in range(-1, 2) for k in range(height + 4)]
        if any(c in self.keep_clear or not self.p.free(*c) for c in cells):
            return False
        p = self.p
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                p.set(cx + dx, y, cz + dz, GOLD if (dx, dz) != (0, 0) else "Rock_Gold_Brick_Ornate")
                for k in range(1, height):
                    p.set(cx + dx, y + k, cz + dz, liquid if (dx, dz) == (0, 0) else GLASS)
                p.set(cx + dx, y + height, cz + dz, TRIM if (dx * dz) else GOLD)
        p.set(cx, y + height + 1, cz, GLASS)
        p.set(cx, y + height + 2, cz, "Rock_Gold_Brick_Pillar_Middle")
        p.set(cx, y + height + 3, cz, "Nakasar_Tower_Emanation_Motes")
        return True

    def wall_ring(self, y0, y1, arcs_out, every=20, fill=12, names=(SHELF,)):
        """Meubles adossés au mur intérieur (r 28,4 à 29,5) de y0 à y1, par tronçons de `fill` degrés sur `every`."""
        for x, z, d, a in ring(28.4, R_IN):
            if any(in_arc(a, a0, a1) for a0, a1 in arcs_out) or int(a) % every >= fill:
                continue
            name = names[(int(a) // every) % len(names)]
            for y in range(y0, y1):
                self.place(x, y, z, name, facing_center(x, z))

    def scatter(self, y, r0, r1, density, names, arcs_out=()):
        """Petit bric-à-brac d'un bloc semé sur le sol (r0 <= d < r1), hors des arcs `arcs_out` et des passages."""
        rng = self.rng
        for x, z, d, a in ring(r0, r1):
            if any(in_arc(a, a0, a1) for a0, a1 in arcs_out) or rng.random() >= density:
                continue
            self.place(x, y, z, rng.choice(names))

    def stations(self, y, r, angles, potions):
        """Postes d'alchimiste : établi tourné vers le centre, chaudron, tonneau et fioles de part et d'autre."""
        for k in angles:
            x, z = at(r, k)
            self.place(x, y, z, "Bench_Alchemy", facing_center(x, z))
            for dk, name in ((-6, "Alchemy_Cauldron"), (6, "Furniture_Ancient_Barrel"), (9, "Furniture_Temple_Wind_Pot")):
                cx, cz = at(r, k + dk)
                self.place(cx, y, cz, name)
            for dk in (-3, 3):
                cx, cz = at(r + 1.5, k + dk)
                self.place(cx, y, cz, self.rng.choice(potions))

    def decor_hall(self):
        """Hall dégagé : le regard va de la porte au grand alambic et aux trois athanors. Le mobilier reste contre le
        mur (étagères, postes d'alchimiste, chaudrons), hors des estrades des athanors et de la colonne relais."""
        y = F_HALL
        rng = self.rng
        potions = ["Deco_Potion", "Potion_Mana_Large", "Potion_Health_Large", "Potion_Poison_Large",
                   "Potion_Stamina_Large", "Potion_Empty_Large", "Potion_Regen_Mana_Large", "Potion_Signature_Greater"]
        busy = [(k - 22, k + 22) for k in HALL_ATHANOR_ANGLES] + [(RELAY[0] - 10, RELAY[0] + 10), (75, 105), (195, 305)]
        # Alambics de verre entre les athanors, loin des passages.
        for k, liquid in ((60, "Rock_Crystal_Green_Block"), (120, "Rock_Crystal_Cyan_Block"),
                          (210, "Rock_Crystal_Pink_Block"), (345, "Rock_Crystal_Yellow_Block")):
            x, z = at(21, k)
            self.flask(x, y, z, liquid)
        # Étagères de réactifs le long du mur, fioles dessus.
        self.wall_ring(y, y + 4, ((195, 305), (78, 102)), every=18, fill=12,
                       names=("Furniture_Village_Shelf_Full", SHELF, "Furniture_Village_Shelf_Full"))
        for x, z, d, a in ring(28.4, R_IN):
            if self.p.get(x, y + 3, z) in ("Furniture_Village_Shelf_Full", SHELF) and rng.random() < 0.6:
                self.place(x, y + 4, z, rng.choice(potions + ["Deco_Book_Pile_Small", "Furniture_Royal_Magic_Potion_Glow"]))
        # Postes d'alchimiste et chaudrons contre le mur, de part et d'autre de la porte et entre les athanors.
        self.stations(y, 24.5, (60, 120, 190, 330), potions)
        for k in (0, 45, 135, 180):
            x, z = at(26, k)
            self.place(x, y, z, "Alchemy_Cauldron_Big")
        self.scatter(y, 22, 27.5, 0.03, ["Deco_Book_Pile_Small", "Deco_Bucket", "Furniture_Ancient_Sack",
                                         "Rock_Crystal_Purple_Small"], busy)
        # Tapis du portail au grand alambic.
        for z in range(8, 26, 2):
            for x in (-2, 0):
                self.place(x, y, z, "Furniture_Royal_Magic_Carpet")
        # Lustres et fioles lumineuses au plafond (le plafond est le sol du couloir des fuites).
        top = F_LEAKS - 2
        for r, step, off in ((10, 60, 0), (22, 30, 15)):
            for k in range(off, 360 + off, step):
                x, z = at(r, k)
                self.hang(x, top, z, CHANDELIER)
        for k in range(10, 370, 30):
            x, z = at(17, k + 15)
            self.chain(x, top, z, 3, end="Furniture_Royal_Magic_Potion_Glow_Ceiling")

    def decor_leaks(self):
        y = F_LEAKS
        rng = self.rng
        top = F_LIBRARY - 2
        # Tonneaux, caisses et sacs de réactifs contre le mur extérieur, par grappes.
        for k in range(5, 360, 22):
            if in_arc(k, 225, 255) or in_arc(k, 165, 195):
                continue
            for j, name in enumerate(rng.sample(["Furniture_Ancient_Barrel", "Furniture_Tavern_Barrel",
                                                 "Furniture_Ancient_Crate", "Furniture_Ancient_Sack",
                                                 "Furniture_Ancient_Pot"], 3)):
                x, z = at(26.5 + (j % 2), k + 2.5 * j)
                self.place(x, y, z, name)
                if name == "Furniture_Ancient_Crate" and rng.random() < 0.7:
                    self.place(x, y + 1, z, rng.choice(["Furniture_Ancient_Barrel", "Deco_Bucket", "Furniture_Ancient_Crate"]))
        # Vapeur qui s'échappe des niches et flaques de réactif.
        for k in range(0, 360, 30):
            if in_arc(k, 232, 248) or in_arc(k, 262, 305):
                continue
            x, z = at(17.5, k)
            if self.p.get(x, y, z) == GLOW:
                self.p.set(x, y + 2, z, "Nakasar_Tower_Emanation_Mist")
            px, pz = at(20, k + 15)
            self.place(px, y, pz, rng.choice(["Rock_Crystal_Green_Small", "Plant_Crop_Mushroom_Glowing_Green",
                                              "Rock_Crystal_Yellow_Small"]))
        self.scatter(y, 24, 28.4, 0.08, ["Deco_Bucket", "Furniture_Ancient_Sack",                                          "Rock_Crystal_Green_Small", "Deco_Bone_Pile", "Deco_Trash_Pile_Small"], ((228, 252),))
        # Chaînes et lanternes qui pendent du plafond.
        for k in range(0, 360, 15):
            if in_arc(k, 232, 248):
                continue
            x, z = at(23, k)
            if k % 30:
                self.chain(x, top, z, 2 + (k // 15) % 3)
            else:
                self.chain(x, top, z, 2, end="Deco_Lantern_Ceiling")

    def decor_greenhouse(self):
        y = F_LEAKS
        rng = self.rng
        # Pots et jarres contre le mur de la tour.
        for x, z, d, a in ring(R_OUT, R_OUT + 1):
            if in_arc(a, *BALCONY_ARC) and int(a) % 9 == 0:
                self.place(x, y, z, "Furniture_Temple_Wind_Pot" if int(a) % 18 == 0 else "Furniture_Royal_Magic_Pot")
        # Sous la verrière : massifs de champignons et de fleurs lumineuses, lianes qui pendent du toit de verre.
        plants = ["Plant_Crop_Mushroom_Glowing_Purple", "Plant_Crop_Mushroom_Glowing_Green", "Plant_Crop_Mushroom_Glowing_Blue",
                  "Plant_Flower_Tall_Cyan", "Plant_Flower_Orchid_Purple", "Plant_Crop_Mushroom_Glowing_Violet"]
        for k in range(GREENHOUSE_ARC[0] + 8, GREENHOUSE_ARC[1] - 4, 16):
            cx, cz = at(39.5, k)
            bed = [(cx + dx, cz + dz) for dx in range(-1, 2) for dz in range(-1, 2)]
            if any((bx, y + kk, bz) in self.keep_clear or not self.p.free(bx, y, bz) for bx, bz in bed for kk in range(2)):
                continue
            for bx, bz in bed:
                self.p.set(bx, y, bz, "Soil_Grass_Full" if (bx, bz) != (cx, cz) else "Plant_Crop_Mushroom_Block_Purple_Trunk")
                if (bx, bz) != (cx, cz):
                    self.p.set(bx, y + 1, bz, rng.choice(plants))
                if (bx, bz) in self.walk:
                    self.walk[(bx, bz)].discard(2 * y)
            for kk in range(1, 4):
                self.p.set(cx, y + kk, cz, "Plant_Crop_Mushroom_Block_Purple_Trunk")
            for dx in range(-1, 2):
                for dz in range(-1, 2):
                    self.p.set(cx + dx, y + 4, cz + dz, "Plant_Crop_Mushroom_Block_Purple")
        for x, z, d, a in ring(R_OUT, BALCONY_R):
            if in_arc(a, *GREENHOUSE_ARC) and rng.random() < 0.18:
                self.chain(x, y + 10, z, rng.randint(1, 4), name="Plant_Vine_Hanging")
            elif in_arc(a, *BALCONY_ARC) and d < 44 and rng.random() < 0.06:
                self.place(x, y, z, rng.choice(["Plant_Moss_Rug_Green", "Plant_Moss_Rug_Blue", "Plant_Moss_Rug_Pink"]))
        # Bancs au belvédère nord, tournés vers le large.
        for k in (262, 278):
            x, z = at(42, k)
            self.place(x, y, z, "Furniture_Temple_Light_Bench", pf.NORTH)

    def decor_library(self):
        y = F_LIBRARY
        rng = self.rng
        reading = ["Deco_Book_Pile_Small", "Deco_Scroll", "Furniture_Temple_Wind_Candle", "Deco_Book_Pile_Small",
                   "Furniture_Ancient_Candle", "Deco_Scroll", "Potion_Mana_Large"]
        # Tables de lecture entre les rayonnages en épis.
        for k in (245, 265, 285, 318, 350, 15):
            x, z = at(19, k)
            self.table(x, y, z, "Furniture_Temple_Light_Table", rng.sample(reading, 4), "Furniture_Ancient_Chair")
        # Au centre, l'arène du Codex vivant : cercle d'or incrusté dans le sol, tapis autour.
        for x in range(-4, 5):
            for z in range(-4, 5):
                d = math.hypot(x, z)
                if d < 1:
                    self.p.set(x, y - 1, z, "Rock_Gold_Brick_Ornate")
                elif 2.6 <= d < 3.6:
                    self.p.set(x, y - 1, z, TRIM)
        for x in range(-8, 8, 2):
            for z in range(-8, 8, 2):
                if 4.5 <= math.hypot(x + 0.5, z + 0.5) < 8.5:
                    self.place(x, y, z, "Furniture_Royal_Magic_Carpet")
        # Échelles contre les étagères, piles de livres au pied des murs.
        for k in (232, 300, 345):
            x, z = at(27.4, k)
            for yy in range(y, y + 6):
                self.place(x, yy, z, "Furniture_Temple_Light_Ladder", facing_center(x, z))
        for x, z, d, a in ring(26.5, 28.4):
            if not in_arc(a, 60, 215) and rng.random() < 0.12:
                self.place(x, y, z, rng.choice(["Deco_Book_Pile_Small", "Deco_Book_Pile_Large", "Deco_Scroll"]))
        # Lustres sous la coupole, fioles lumineuses sous les galeries.
        low = self.vault_low
        self.hang(0, low[(0, 0)] - 1, 0, "Furniture_Temple_Wind_Chandelier")
        for r, step, off in ((10, 60, 30), (18, 45, 0)):
            for k in range(off, 360 + off, step):
                x, z = at(r, k)
                self.chain(x, low[(x, z)] - 1, z, 5, end="Furniture_Royal_Magic_Potion_Glow_Ceiling")
        for g in (14, 22):
            for k in range(0, 360, 20):
                if not in_arc(k, 60, 215):
                    x, z = at(26, k)
                    self.chain(x, y + g - 1, z, 1, name="Furniture_Royal_Magic_Potion_Glow_Ceiling")
        # Salle secrète : crânes, grimoires, rouleaux, bougies.
        cx, cz = at(39, 320)
        for (dx, dz), name in zip(((-4, -4), (4, -4), (-4, 4), (4, 4), (-2, -4), (2, 4), (0, -4)),
                                  ("Deco_Bone_Skulls", "Deco_Book_Pile_Large", "Furniture_Ancient_Candle",
                                   "Deco_Scroll", "Deco_Book_Pile_Small", "Furniture_Ancient_Candle", "Deco_Treasure_Pile_Small")):
            self.place(cx + dx, y, cz + dz, name)

    def decor_transmutation(self):
        y = F_TRANS
        p = self.p
        rng = self.rng
        # Cercle de transmutation : deux anneaux d'or au sol, sceau au centre.
        for x in range(-SQUARE, SQUARE + 1):
            for z in range(-13, SQUARE + 1):
                d = math.hypot(x, z)
                if 4.5 <= d < 5.4 or 9.5 <= d < 10.4:
                    p.set(x, y - 1, z, GOLD)
        p.set(0, y - 1, 0, "Rock_Gold_Brick_Ornate")
        for k in range(45, 360, 90):
            x, z = at(7.5, k)
            self.place(x, y, z, "Furniture_Royal_Magic_Potion_Glow")
        # Feu (nord-est) : sol de magma refroidi, braseros autour d'un grand brasier, cristaux rouges.
        fx, fz = 11, -7
        for x in range(fx - 3, fx + 4):
            for z in range(fz - 3, fz + 4):
                if math.hypot(x - fx, z - fz) <= 3.2:
                    p.set(x, y - 1, z, "Rock_Magma_Cooled")
        self.place(fx, y, fz, "Furniture_Dungeon_Earth_Brazier")
        for k in range(0, 360, 90):
            x, z = at(2.5, k)
            self.place(fx + x, y, fz + z, BRAZIER)
        for dx, dz in ((4, 3), (-4, -3), (5, -2)):
            self.place(fx + dx, y, fz + dz, rng.choice(["Rock_Crystal_Red_Large", "Rock_Crystal_Red_Medium"]))
        # Glace (nord-ouest) : aiguilles de cristal blanc et cyan, glace au sol.
        ix, iz = -10, -7
        for x in range(ix - 3, ix + 4):
            for z in range(iz - 3, iz + 4):
                d = math.hypot(x - ix, z - iz)
                if d <= 3.2:
                    p.set(x, y - 1, z, "Rock_Ice")
                if d <= 1.5:
                    for k in range(0, 4 - int(2 * d)):
                        if (x, y + k, z) not in self.keep_clear and p.free(x, y + k, z):
                            p.set(x, y + k, z, "Rock_Crystal_Cyan_Block" if (x + z) % 2 else "Rock_Crystal_White_Block")
        for dx, dz in ((3, 2), (-3, 2), (2, -3)):
            self.place(ix + dx, y, iz + dz, rng.choice(["Rock_Crystal_White_Large", "Rock_Crystal_Cyan_Large"]))
        # Acide (sud-est) : bassin de cristal vert, grand chaudron, champignons lumineux.
        ax, az = 10, 10
        for x in range(ax - 3, ax + 4):
            for z in range(az - 3, az + 4):
                d = math.hypot(x - ax, z - az)
                if d <= 2.2:
                    p.set(x, y - 1, z, "Rock_Crystal_Green_Block")
                elif d <= 3.2 and p.free(x, y, z) and (x, y, z) not in self.keep_clear:
                    p.set(x, y, z, "Rock_Gold_Brick_Half")
        self.place(ax, y, az, "Alchemy_Cauldron_Big")
        for dx, dz in ((4, -2), (-4, 2), (2, 4), (-2, -4)):
            self.place(ax + dx, y, az + dz, rng.choice(["Plant_Crop_Mushroom_Glowing_Green", "Rock_Crystal_Green_Large",
                                                        "Rock_Crystal_Green_Medium"]))
        # Foudre (sud-ouest) : paratonnerre d'or coiffé de cristal, arc électrique, cristaux jaunes et bleus.
        lx, lz = -10, 10
        for k in range(0, 7):
            p.set(lx, y + k, lz, "Rock_Gold_Brick_Pillar_Base" if k == 0 else "Rock_Gold_Brick_Pillar_Middle")
        p.set(lx, y + 7, lz, "Rock_Crystal_Yellow_Block")
        p.set(lx, y + 8, lz, "Nakasar_Tower_Emanation_Arc")
        for dx, dz in ((2, 0), (-2, 0), (0, 2), (0, -2), (3, 3), (-3, -3)):
            self.place(lx + dx, y, lz + dz, rng.choice(["Rock_Crystal_Yellow_Large", "Rock_Crystal_Blue_Large",
                                                        "Rock_Crystal_Yellow_Medium"]))
        # Chaque quadrant semé de son élément ; le couloir d'arrivée (ouest) et le pied de l'escalier restent libres.
        themes = {(1, -1): ["Rock_Crystal_Red_Medium", "Rock_Crystal_Red_Small", BRAZIER, "Rock_Magma_Cooled_Half"],
                  (-1, -1): ["Rock_Crystal_White_Medium", "Rock_Crystal_Cyan_Medium", "Rock_Crystal_Cyan_Small", "Rock_Ice"],
                  (1, 1): ["Rock_Crystal_Green_Medium", "Rock_Crystal_Green_Small", "Alchemy_Cauldron",
                           "Plant_Crop_Mushroom_Glowing_Green"],
                  (-1, 1): ["Rock_Crystal_Yellow_Medium", "Rock_Crystal_Blue_Medium", "Rock_Crystal_Yellow_Small",
                            "Rock_Crystal_Blue_Small"]}
        for x in range(-SQUARE + 1, SQUARE):
            for z in range(-12, SQUARE):
                if abs(x) < 3 or abs(z) < 3 or (x < -11 and z < -3) or rng.random() >= 0.09:
                    continue
                self.place(x, y, z, rng.choice(themes[(1 if x > 0 else -1, 1 if z > 0 else -1)]))
        # Colonnes d'angle coiffées du cristal de leur quadrant.
        for (sx, sz), crystal in (((1, 1), "Rock_Crystal_Green_Block"), ((-1, 1), "Rock_Crystal_Yellow_Block"),
                                  ((1, -1), "Rock_Crystal_Red_Block")):
            cx, cz = sx * (SQUARE - 1), sz * (SQUARE - 1) if sz > 0 else -12
            for k in range(0, 10):
                if p.free(cx, y + k, cz) and (cx, y + k, cz) not in self.keep_clear:
                    p.set(cx, y + k, cz, "Rock_Gold_Brick_Pillar_Base" if k == 0 else
                          crystal if k == 9 else "Rock_Gold_Brick_Pillar_Middle")
        # Lustres au plafond (sol du laboratoire).
        top = F_LAB - 2
        for x, z in ((0, 0), (9, 9), (-9, 9), (9, -9), (-9, -9)):
            self.hang(x, top, z, CHANDELIER)

    def decor_lab(self):
        y = F_LAB
        p = self.p
        rng = self.rng
        top = F_LAB + 22
        # Condenseur : colonnes d'or de la cuve au plafond, bulbe de verre au cœur de cristal suspendu au centre.
        for k in (45, 135, 225, 315):
            x, z = at(8, k)
            for yy in range(y + 2, top + 1):
                if p.free(x, yy, z):
                    p.set(x, yy, z, "Rock_Gold_Brick_Pillar_Middle" if yy % 6 else TRIM)
        for x, z, d, a in ring(0, 3.6):
            for yy in range(top - 7, top + 1):
                edge = d >= 2.5 or yy in (top - 7, top)
                p.set(x, yy, z, (GOLD if yy in (top - 7, top - 3, top) else GLASS) if edge else "Rock_Crystal_Green_Block")
        p.set(0, top - 8, 0, "Nakasar_Tower_Emanation_Motes")
        # Tables de manipulation et établis arcaniques.
        potions = ["Potion_Empty_Large", "Potion_Empty", "Deco_Potion", "Potion_Poison_Large", "Potion_Mana",
                   "Potion_Regen_Health_Large", "Potion_Morph_Frog", "Deco_Scroll"]
        for k in (0, 90, 180):
            x, z = at(12, k)
            self.table(x, y, z, "Furniture_Royal_Magic_Table", rng.sample(potions, 4), "Furniture_Temple_Light_Stool")
        for k in (45, 160):
            x, z = at(24, k)
            self.place(x, y, z, "Bench_Arcane", facing_center(x, z))
        self.stations(y, 22.5, (60, 80, 215, 245), potions)
        self.scatter(y, 18, 27, 0.05, potions + ["Deco_Bone_Skulls", "Deco_Book_Pile_Small", "Rock_Crystal_Green_Small",
                                                 "Furniture_Royal_Magic_Potion_Glow"], ((255, 350),))
        # Fioles sur les étagères, jarres et tonneaux le long du mur.
        for x, z, d, a in ring(28.4, R_IN):
            if p.get(x, y + 5, z) == SHELF and rng.random() < 0.5:
                self.place(x, y + 6, z, rng.choice(potions[:6] + ["Furniture_Royal_Magic_Potion_Glow", "Deco_Bone_Skulls"]))
        for k in range(140, 192, 8):
            x, z = at(26.5, k)
            self.place(x, y, z, rng.choice(["Furniture_Temple_Wind_Pot", "Furniture_Ancient_Barrel", "Furniture_Ancient_Crate"]))
        # Lustres et lanternes au plafond.
        for k in range(0, 360, 45):
            x, z = at(17, k + 22)
            self.hang(x, top, z, CHANDELIER)
        for k in range(0, 360, 20):
            x, z = at(23, k)
            self.chain(x, top, z, 4, end="Furniture_Royal_Magic_Potion_Glow_Ceiling")

    def decor_observatory(self):
        y = F_DECK
        rng = self.rng
        # Le centre est l'arène de l'Alchimiste, autour de son athanor : le décor reste au pourtour.
        for k in (20, 160, 300):
            self.telescope(k, 38)
        # Massifs de fleurs lumineuses entre les arcs, braseros le long du parapet, cristaux sur socles d'or.
        flowers = ["Plant_Flower_Tall_Cyan", "Plant_Flower_Orchid_Purple", "Plant_Crop_Mushroom_Glowing_Blue",
                   "Plant_Crop_Mushroom_Glowing_Purple", "Plant_Grass_Lush"]
        for k in (0, 45, 135, 170, 300, 330):
            cx, cz = at(31, k)
            bed = [(cx + dx, cz + dz) for dx in range(-2, 3) for dz in range(-1, 2)]
            if any((bx, y + kk, bz) in self.keep_clear or not self.p.free(bx, y, bz) for bx, bz in bed for kk in range(2)):
                continue
            for bx, bz in bed:
                edge = abs(bx - cx) == 2 or abs(bz - cz) == 1
                self.p.set(bx, y, bz, TRIM if edge else "Soil_Grass_Full")
                if not edge:
                    self.p.set(bx, y + 1, bz, rng.choice(flowers))
                self.walk.get((bx, bz), set()).discard(2 * y)
        for k in range(0, 360, 12):
            if in_arc(k, 195, 280) or in_arc(k, 70, 110):
                continue
            x, z = at(43, k)
            self.place(x, y, z, "*Furniture_Temple_Light_Brazier_State_Definitions_On")
        for k, crystal in ((25, "Rock_Crystal_Purple_Large"), (115, "Rock_Crystal_Blue_Large"),
                           (155, "Rock_Crystal_Pink_Large"), (290, "Rock_Crystal_Green_Large")):
            x, z = at(36, k)
            if self.place(x, y, z, "Rock_Gold_Brick_Ornate"):
                self.place(x, y + 1, z, crystal)
        # Lanternes sur l'anneau d'or, pots de fleurs le long du parapet.
        for k in range(0, 360, 20):
            if in_arc(k, 195, 280) or in_arc(k, 60, 120):
                continue
            x, z = at(22, k)
            self.place(x, y, z, LANTERN)
        for x, z, d, a in ring(DECK_R - 1.5, DECK_R):
            if int(a) % 16 == 0 and not in_arc(a, 195, 280):
                self.place(x, y, z, "Furniture_Royal_Magic_Pot")

    def decor_antechamber(self):
        y = F_DECK
        top = F_DECK + 9
        for k in range(204, 274, 10):
            x, z = at(25.5, k)
            self.place(x, y, z, "*Furniture_Temple_Light_Brazier_State_Definitions_On")
        for k in (212, 262):
            x, z = at(28, k)
            self.place(x, y, z, "Furniture_Temple_Wind_Statue", facing_center(-x, -z))
        for k in (215, 235, 255):
            x, z = at(40, k)
            self.hang(x, top, z, "Furniture_Temple_Wind_Chandelier")
        for k in range(205, 272, 8):
            x, z = at(43, k)
            self.place(x, y, z, "Furniture_Temple_Wind_Pot")

    def decor_study(self):
        y = F_DECK
        rng = self.rng
        # Le piédestal de la pierre (étape du butin) reste dégagé.
        self.keep_clear.update((x, y + k, z) for x in range(-1, 2) for z in range(31, 34) for k in range(4))
        # Bibliothèque du fond, de part et d'autre du portail de fin.
        for x in range(-8, 9):
            if abs(x) <= 2:
                continue
            for k in range(0, 4):
                self.place(x, y + k, 41, SHELF, pf.NORTH)
            if rng.random() < 0.6:
                self.place(x, y + 4, 41, rng.choice(["Deco_Bone_Skulls", "Potion_Signature_Greater", "Deco_Book_Pile_Small",
                                                     "Furniture_Royal_Magic_Potion_Glow", "Deco_Treasure_Pile_Small"]))
        # Bureau garni, tapis, curiosités.
        for x, top in ((6, "Deco_Scroll"), (7, "Furniture_Temple_Wind_Candle")):
            self.place(x, y + 1, 30, top)
        self.place(6, y, 29, "Furniture_Royal_Magic_Chair", pf.SOUTH)
        for x in (-6, -4, 2, 4):
            for z in (34, 36):
                self.place(x, y, z, "Furniture_Royal_Magic_Carpet")
        self.place(-7, y, 40, "Furniture_Temple_Emerald_Statue", pf.EAST)
        self.place(7, y, 40, "Furniture_Temple_Emerald_Statue", pf.WEST)
        self.place(-7, y, 27, "Deco_Treasure_Pile_Large")
        self.place(7, y, 37, "Alchemy_Cauldron")
        self.place(-7, y, 33, "Furniture_Temple_Wind_Pot")
        self.place(-6, y, 37, "Deco_Bone_Skulls")
        self.hang(0, y + 9, 35, "Furniture_Temple_Wind_Chandelier")

    def decorate(self):
        self.decor_hall()
        self.decor_leaks()
        self.decor_greenhouse()
        self.decor_library()
        self.decor_transmutation()
        self.decor_lab()
        self.decor_observatory()
        self.decor_antechamber()
        self.decor_study()

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
        self.checkpoint(*at3(22, F_LIBRARY, 45), statue_at=at(27, 36))
        self.checkpoint(22, F_LAB, -16, statue_at=(18, -20))
        self.checkpoint(*at3(37, F_LAB, 272), statue_at=at(39, 262))
        self.checkpoint(*at3(33, F_DECK, 255), statue_at=at(37, 265))
        self.traps()
        self.codex()
        self.chimera()
        self.alchemist()
        self.decorate()
        self.mobs()
        self.secure()
        self.barriers()
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


    # --- murs invisibles ---------------------------------------------------------------------------

    def ground_solid(self, x, y, z):
        """Plein, en comptant l'île sous le prefab (y < 0 hors des blocs posés)."""
        return self.solid(x, y, z) or (y < 0 and self.p.get(x, y, z) is None)

    def barrier_needs(self):
        """Piles au bord du vide extérieur trop basses pour un joueur à côté : {(x, haut actuel, z): haut voulu}.

        Pour chaque surface atteignable, une colonne voisine pleine à hauteur des pieds (parapet, verrière, lanterne...)
        doit l'être jusqu'à 4 blocs au-dessus de la surface si, à 2 cases au plus, une colonne hors de la tour (d >=
        R_OUT) n'a rien de plein de 6 blocs sous les pieds à 3 au-dessus : le vide. Les trémies intérieures n'en ont pas
        besoin."""
        _, seen = walkable_path(self.p, START, {})
        levels = {}
        for x, s, z in seen:
            levels.setdefault((x, z), set()).add(s)
        void = {}

        def is_void(x, z, fy):
            key = (x, z, fy)
            if key not in void:
                void[key] = polar(x, z)[0] >= R_OUT and not any(self.ground_solid(x, yy, z)
                                                               for yy in range(fy - 6, fy + 4))
            return void[key]

        need = {}
        for x, s, z in seen:
            fy = (s + 1) // 2           # premier bloc d'air au-dessus de la surface
            want = fy + 3               # dernier bloc plein voulu : 4 blocs au-dessus de la surface
            for dx, dz in DIRS8:
                nx, nz = x + dx, z + dz
                # voisin au même niveau, marche plus haute de la même rampe, ou trou : pas un mur
                if any(-2 <= o - s <= 16 for o in levels.get((nx, nz), ())) or not self.ground_solid(nx, fy, nz):
                    continue
                if not any(is_void(nx + ex, nz + ez, fy) for ex in range(-2, 3) for ez in range(-2, 3)):
                    continue
                top = fy
                while self.ground_solid(nx, top + 1, nz) or (nx, top + 1, nz) in self.p.claims:
                    top += 1
                if top < want:
                    need[(nx, top, nz)] = max(want, need.get((nx, top, nz), want))
        return need

    def barriers(self):
        """Murs invisibles (bloc vanilla Barrier : plein, sans rendu) au-dessus des parapets qui bordent le vide, pour
        qu'on ne puisse sauter par-dessus ni des coursives, ni des rampes extérieures, ni de la terrasse."""
        for _ in range(3):
            need = self.barrier_needs()
            if not need:
                return
            for (x, top, z), want in need.items():
                for y in range(top + 1, want + 1):
                    if (x, y, z) in self.keep_clear or not self.p.free(x, y, z):
                        break
                    self.p.set(x, y, z, BARRIER)
        need = self.barrier_needs()
        if need:
            raise RuntimeError(f"tour : murs invisibles trop bas au bord du vide {sorted(need.items())[:8]}")
        _, seen = walkable_path(self.p, START, {})
        perched = [(x, s, z) for x, s, z in seen if self.p.get(x, (s - 1) // 2, z) == BARRIER]
        if perched:
            raise RuntimeError(f"tour : on peut marcher sur des murs invisibles {perched[:8]}")


# Mobs (alchemist_tower.Tower.mobs, rôles de tools/generate_tower_mobs.py) : (rôle sans le préfixe Nakasar_,
# (rayon, niveau, angle), hauteur libre demandée). La case exacte est la plus proche libre au même niveau.
SPAWNER_PREFIX = "Nakasar_Spawner_"
MOB_LAYOUT = [
    # Hall des Alambics : deux groupes d'homoncules, deux golems de plomb, une fiole de poison.
    ("Homunculus", (12, F_HALL, 40), 2), ("Homunculus", (13, F_HALL, 52), 2), ("Homunculus", (11, F_HALL, 64), 2),
    ("Homunculus", (14, F_HALL, 150), 2), ("Homunculus", (15, F_HALL, 162), 2),
    ("Lead_Golem", (16, F_HALL, 345), 4), ("Lead_Golem", (17, F_HALL, 210), 4),
    ("Living_Flask_Poison", (9, F_HALL, 265), 2),
    # Couloir des fuites (pièges) : deux fioles seulement.
    ("Living_Flask_Poison", (25, F_LEAKS, 120), 2), ("Living_Flask_Fire", (25, F_LEAKS, 30), 2),
    # Serre suspendue : plantes carnivores (vrilles et Snapdragons) sous la verrière, élémentaires de racine.
    ("Snapdragon", (41, F_LEAKS, 205), 2), ("Carnivorous_Vine", (40, F_LEAKS, 222), 3),
    ("Snapdragon", (42, F_LEAKS, 240), 2), ("Carnivorous_Vine", (40, F_LEAKS, 258), 3),
    ("Snapdragon", (41, F_LEAKS, 276), 2),
    ("Elemental_Root", (40, F_LEAKS, 300), 3), ("Elemental_Root", (40, F_LEAKS, 330), 3),
    # Bibliothèque : apprentis et homoncules.
    ("Alchemist_Apprentice", (14, F_LIBRARY, 150), 2), ("Alchemist_Apprentice", (14, F_LIBRARY, 300), 2),
    ("Homunculus", (10, F_LIBRARY, 220), 2), ("Homunculus", (11, F_LIBRARY, 235), 2),
    ("Elemental_Frost", (16, F_LIBRARY, 20), 3),
    # Laboratoire : l'arène de la Chimère, sans autre mob.
]
# Salle des Transmutations : un élémentaire par quadrant (feu, glace, racine, foudre) et le golem de cristal au centre.
MOB_FIXED = [
    ("Elemental_Fire", (10, F_TRANS, 10), 3), ("Elemental_Frost", (-10, F_TRANS, 10), 3),
    ("Elemental_Root", (-10, F_TRANS, -10), 3), ("Elemental_Thunder", (10, F_TRANS, -10), 3),
    ("Crystal_Golem", (0, F_TRANS, 4), 5),
]
GARGOYLE_ANGLES = (320, 40, 130, 220)


# Salles à atteindre depuis le parvis (x, niveau, z), en plus des points de contrôle.
GOALS = {"hall": (0, F_HALL, 16), "leaks_exit": (-31, F_LEAKS, 0), "balcony_north": (0, F_LEAKS, -40),
         "library": (0, F_LIBRARY, 12), "transmutation": (0, F_TRANS, 0), "lab": (10, F_LAB, 10),
         "deck": (0, F_DECK, -10), "study": (0, F_DECK, 34)}


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
    # Chaque énigme ferme bien son passage : sceaux et ronces fermés, on ne va pas plus loin que la salle.
    cps = tower.checkpoints
    for name, start, goal in (("portail de la cour", START, GOALS["hall"]),
                              ("sceau du hall", (0, 2 * F_HALL, 16), GOALS["leaks_exit"]),
                              ("ronces de la bibliothèque", (cps[0][0], 2 * cps[0][1], cps[0][2]), GOALS["transmutation"]),
                              ("sceau des transmutations", (0, 2 * F_TRANS, 4), cps[1])):
        missing, _ = walkable_path(prefab, start, {"goal": goal}, gates_open=False)
        if not missing:
            raise RuntimeError(f"tour : le {name} ne ferme pas le passage")
    # Le sceau du Codex seul (ronces brûlées) ferme le haut de la rampe ; les éboulis de toutes les étagères effondrées
    # ne ferment ni la rampe ni le centre de l'arène.
    codex = tower.trap["codex"]
    library = (cps[0][0], 2 * cps[0][1], cps[0][2])
    missing, _ = walkable_path(prefab, library, {"goal": GOALS["transmutation"]}, solid_cells=codex["seal"])
    if not missing:
        raise RuntimeError("tour : le sceau du Codex ne ferme pas la rampe de la bibliothèque")
    rubble = [c for cells in codex["rubble"] for c in cells]
    missing, _ = walkable_path(prefab, library, {"transmutation": GOALS["transmutation"], "arena": (0, F_LIBRARY, 3),
                                                 "vault": at3(37, F_LIBRARY, 320)}, solid_cells=rubble)
    if missing:
        raise RuntimeError(f"tour : les éboulis du Codex ferment le passage : {missing}")
    # Le sceau de la Chimère seul ferme la porte nord du laboratoire (vers l'Escalier des vents).
    missing, _ = walkable_path(prefab, (cps[1][0], 2 * cps[1][1], cps[1][2]), {"goal": cps[2]},
                               solid_cells=tower.trap["chimera"]["seal"])
    if not missing:
        raise RuntimeError("tour : le sceau de la Chimère ne ferme pas la porte nord du laboratoire")
    # Le sceau de l'Alchimiste seul ferme la porte du bureau depuis la terrasse.
    deck = GOALS["deck"]
    missing, _ = walkable_path(prefab, (deck[0], 2 * deck[1], deck[2]), {"goal": GOALS["study"]},
                               solid_cells=tower.trap["alchemist"]["seal"])
    if not missing:
        raise RuntimeError("tour : le sceau de l'Alchimiste ne ferme pas la porte du bureau")
    return tower


def at3(r, y, a):
    x, z = at(r, a)
    return x, y, z


# --- vérification du parcours --------------------------------------------------------------------

PASSABLE_PREFIXES = ("Nakasar_Spawner_", "VFX_", "Plant_Grass", "Plant_Flower", "Plant_Crop_Mushroom_Glowing", "Nakasar_Tower_Emanation", "Deco_Potion",
                     "Deco_Scroll", "Plant_Moss_Rug", "Plant_Vine", "Furniture_Royal_Magic_Carpet")


def passable(name):
    return name in (None, AIR) or name.startswith(PASSABLE_PREFIXES)


def walkable_path(prefab, start, goals, ground_y=0, bounds=(-70, 70, -70, 82), gates_open=True, solid_cells=()):
    """Parcours en largeur sur les surfaces du prefab (demi-blocs) : un joueur de 2 blocs de haut monte d'un demi-bloc
    en marchant, d'un bloc en sautant, et peut descendre de 4 blocs. Hors du prefab, sous ground_y c'est l'île (plein),
    au-dessus de l'air. Sceaux et ronces (GATE_BLOCKS) sont ouverts si gates_open, comme une fois les énigmes
    résolues ; `solid_cells` sont pleins quoi qu'il y ait (un sceau seul, des éboulis posés en jeu). Renvoie les buts
    non atteints."""
    blocks = prefab.blocks
    claims = prefab.claims
    solid_cells = set(solid_cells)

    def cell(x, y, z):
        if (x, y, z) in solid_cells:
            return "solid"
        if (x, y, z) in claims:
            return "air" if passable(blocks[claims[(x, y, z)]][0]) else "solid"
        b = blocks.get((x, y, z))
        if b is None:
            return "solid" if y < ground_y else "air"
        name = b[0]
        if name in GATE_BLOCKS:
            return "air" if gates_open else "solid"
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
