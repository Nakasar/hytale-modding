"""Cartes des fractales pour le wiki des joueurs (Kevin, 25 octobre 2026 : « des images des cartes des fractales en
rendus ») : chaque carte est rendue depuis le prefab que produit le générateur de la fractale (aucun fichier du mod
n'est écrit), vue de dessus, en relief ombré (lumière du nord-ouest, ombres portées), avec des repères numérotés
expliqués dans la page du wiki.

Les fractales sous une voûte (Volcanique) sont vues voûte retirée : on y montre le sol des galeries.

Usage : python3 mods/nakasar-fractals/tools/render_wiki_maps.py [fractale ...]
        (sans argument : toutes ; images dans docs/wiki/images/fractales/carte-<fractale>.png)"""

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parents[3] / "docs" / "wiki" / "images" / "fractales"
AIR = "Empty"
WALL = "#paroi"           # colonne pleine sous une voûte
WALL_COLOR = (38, 34, 36)
SKY = (16, 18, 36)
MAX_SIDE = 1600        # plus grand côté d'une carte (pixels)
LIGHT = (-0.55, 0.62, -0.55)   # (x, y, z) vers la lumière : nord-ouest et en hauteur


def _font(size):
    for name in ("DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def is_small_plant(name):
    """Herbes, fleurs et fougères : un semis de points qui brouille la carte, on montre le sol dessous."""
    return name.startswith(("Plant_Grass", "Plant_Flower", "Plant_Fern", "Plant_Bush", "Plant_Reeds", "Plant_Moss"))


def is_canopy(name):
    """Feuillage et troncs : ils cachent les chemins, la carte montre le sol dessous (et l'ombre des arbres)."""
    return "Leaves" in name or name.endswith("Trunk") or "_Trunk_" in name or name.startswith("Plant_Vine")


def main_area(top, gap=7, margin=6):
    """Cadre de la plus grande zone d'un seul tenant (des trous de moins de `gap` blocs comptent comme reliés) :
    les îlots de décor lointains restent hors de la carte."""
    cells = set(top)
    seen, best = set(), []
    for start in cells:
        if start in seen:
            continue
        group, todo = [], [start]
        seen.add(start)
        while todo:
            x, z = todo.pop()
            group.append((x, z))
            for dx in range(-gap, gap + 1):
                for dz in range(-gap, gap + 1):
                    n = (x + dx, z + dz)
                    if n in cells and n not in seen and dx * dx + dz * dz <= gap * gap:
                        seen.add(n)
                        todo.append(n)
        if len(group) > len(best):
            best = group
    xs = [c[0] for c in best]
    zs = [c[1] for c in best]
    return min(xs) - margin, min(zs) - margin, max(xs) + margin, max(zs) + margin


def with_markers(crop, markers, margin=14):
    """Le cadre `crop` agrandi aux repères qui en sortent (Pic de Sunqua : îlots du départ et plateau de la Voix
    détachés du massif)."""
    x0, z0, x1, z1 = crop
    for x, z, _ in markers:
        if not (x0 <= x <= x1 and z0 <= z <= z1):
            x0, z0, x1, z1 = min(x0, x - margin), min(z0, z - margin), max(x1, x + margin), max(z1, z + margin)
    return x0, z0, x1, z1


def surface(prefabs, roofed=False, canopy=None):
    """Bloc vu d'en haut par colonne : (hauteur, nom). Sous une voûte, la première couche pleine qui a de l'air
    dessous est ignorée (on voit le sol)."""
    columns = {}
    for p in prefabs:
        for (x, y, z), (name, _) in p.blocks.items():
            if name == AIR or is_small_plant(name):
                continue
            if is_canopy(name):
                if canopy is not None:
                    canopy[(x, z)] = max(canopy.get((x, z), y), y)
                continue
            columns.setdefault((x, z), {})[y] = name
        for (x, y, z), (name, _) in getattr(p, "fluids", {}).items():
            columns.setdefault((x, z), {})[y] = name
    top = {}
    for key, col in columns.items():
        ys = sorted(col, reverse=True)
        y = ys[0]
        if roofed:
            # Descend la voûte jusqu'à son dessous ; s'il y a de l'air puis du sol, on prend ce sol.
            k = 0
            while k + 1 < len(ys) and ys[k + 1] == ys[k] - 1:
                k += 1
            if k + 1 < len(ys) and ys[k] - ys[k + 1] > 2:
                y = ys[k + 1]
            else:
                top[key] = (y, WALL)     # roche pleine jusqu'à la voûte : paroi
                continue
        top[key] = (y, col[y])
    return top


def render(top, color_of, path, markers=(), scale=None, crop=None, shadows=True, canopy=None, compass=True):
    """Relief ombré vu de dessus ; `markers` = [(x, z, numéro)] ; rend l'échelle (pixels par bloc) et l'origine."""
    xs = [k[0] for k in top]
    zs = [k[1] for k in top]
    if crop:
        x0, z0, x1, z1 = crop
    else:
        x0, x1, z0, z1 = min(xs) - 4, max(xs) + 4, min(zs) - 4, max(zs) + 4
    w, h = x1 - x0 + 1, z1 - z0 + 1
    s = scale or max(2, min(6, MAX_SIDE // max(w, h)))
    img = Image.new("RGB", (w * s, h * s), SKY)
    px = img.load()
    height = {k: v[0] for k, v in top.items()}
    lo, hi = min(height.values()), max(height.values())
    lx, ly, lz = LIGHT
    norm = math.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / norm, ly / norm, lz / norm
    for (x, z), (y, name) in top.items():
        if not (x0 <= x <= x1 and z0 <= z <= z1):
            continue
        c = WALL_COLOR if name == WALL else color_of(name)
        if c is None:
            continue
        # Normale par différences finies (le vide compte comme une falaise vers le bas).
        hx = height.get((x + 1, z), y - 6) - height.get((x - 1, z), y - 6)
        hz = height.get((x, z + 1), y - 6) - height.get((x, z - 1), y - 6)
        nx, ny, nz = -hx / 2, 1.0, -hz / 2
        n = math.sqrt(nx * nx + ny * ny + nz * nz)
        light = max(0.0, (nx * lx + ny * ly + nz * lz) / n)
        # Ombre portée : un bloc plus haut au nord-ouest masque la lumière (pas sous une voûte).
        shadow = shadows and any(height.get((x - d, z - d), -10 ** 6) > y + d * 0.9 for d in range(1, 9))
        depth = 0.62 + 0.38 * (y - lo) / max(1, hi - lo)
        f = (0.42 + 0.75 * light) * depth * (0.7 if shadow else 1.0)
        col = tuple(max(0, min(255, int(v * f))) for v in c[:3])
        bx, bz = (x - x0) * s, (z - z0) * s
        for i in range(s):
            for j in range(s):
                px[bx + i, bz + j] = col
    # Couronnes des arbres : voile vert sombre, les chemins restent visibles dessous.
    if canopy:
        veil = Image.new("L", img.size, 0)
        vd = ImageDraw.Draw(veil)
        for (x, z), y in canopy.items():
            if x0 <= x <= x1 and z0 <= z <= z1 and y >= top.get((x, z), (-10 ** 6,))[0]:
                bx, bz = (x - x0) * s, (z - z0) * s
                vd.rectangle((bx, bz, bx + s - 1, bz + s - 1), fill=85)
        img.paste(Image.new("RGB", img.size, (20, 60, 24)), mask=veil.filter(ImageFilter.GaussianBlur(s * 0.8)))
    # Liseré sombre au bord du vide, pour détacher les îles.
    edges = Image.new("L", img.size, 0)
    ed = ImageDraw.Draw(edges)
    for (x, z) in top:
        if any((x + dx, z + dz) not in top for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            bx, bz = (x - x0) * s, (z - z0) * s
            ed.rectangle((bx, bz, bx + s - 1, bz + s - 1), fill=120)
    img.paste(Image.new("RGB", img.size, (6, 6, 14)), mask=edges.filter(ImageFilter.GaussianBlur(s * 0.6)).point(lambda v: v // 2))
    draw = ImageDraw.Draw(img)
    r = max(11, s * 3)
    font = _font(int(r * 1.15))
    for mx, mz, label in markers:
        cx, cz = (mx - x0 + 0.5) * s, (mz - z0 + 0.5) * s
        draw.ellipse((cx - r - 2, cz - r - 2, cx + r + 2, cz + r + 2), fill=(20, 20, 28))
        draw.ellipse((cx - r, cz - r, cx + r, cz + r), fill=(250, 214, 92))
        draw.text((cx, cz), str(label), fill=(20, 20, 28), font=font, anchor="mm")
    _compass(draw, img.size, s, compass)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, optimize=True)
    return s


def _compass(draw, size, s, north=True):
    """Flèche du nord (-z) et barre de 20 blocs, en bas à droite."""
    w, h = size
    font = _font(16)
    x, y = w - 40, h - 70
    if north:
        draw.polygon([(x, y - 24), (x - 10, y + 6), (x + 10, y + 6)], fill=(240, 240, 240))
        draw.text((x, y + 20), "N", fill=(240, 240, 240), font=font, anchor="mm")
    bar = 20 * s
    draw.rectangle((w - 70 - bar, h - 26, w - 70, h - 20), fill=(240, 240, 240))
    draw.text((w - 70 - bar / 2, h - 36), "20 blocs", fill=(240, 240, 240), font=font, anchor="mm")


# --- fractales -----------------------------------------------------------------------------------------

def _observatory():
    import generate_observatory as g
    colors = {}

    def color_of(name):
        c = _known(name)
        if c:
            return c
        if name not in colors:
            h = sum(map(ord, name)) % 360
            colors[name] = tuple(int(120 + 70 * math.sin(math.radians(h + k * 120))) for k in range(3))
        return colors[name]

    return [g.observatory_prefab()], color_of, False


def _known(name):
    """Couleurs des blocs vanilla courants (les générateurs n'ont d'aperçu que pour leurs propres blocs)."""
    import fractal_nature as fn
    c = fn.nature_color(name)
    if c:
        return c
    for key, col in (("Lava", (240, 100, 30)), ("Gold", (230, 190, 70)), ("Marble", (225, 222, 214)),
                     ("Quartzite", (220, 214, 200)), ("Basalt", (60, 58, 62)), ("Volcanic", (72, 64, 64)),
                     ("Sandstone", (210, 180, 120)), ("Sand", (220, 200, 140)), ("Wood", (140, 100, 60)),
                     ("Brick", (150, 80, 60)), ("Glass", (170, 210, 230)), ("Water", (60, 110, 200)),
                     ("Stone", (128, 128, 128)), ("Rock", (118, 118, 118))):
        if key in name:
            return col
    return None


def _generator(module, roof=False):
    def load():
        g = __import__(module)
        prefabs = [g.course_prefab()]
        if module == "generate_cliffside":
            prefabs = [g.cliff_prefab(), g.colossus_prefab(set(prefabs[0].blocks)), prefabs[0]]
        def color_of(name):
            if not name.startswith("Nakasar_"):
                c = _known(name)
                if c:
                    return c
            return g.color_of(name)
        return prefabs, color_of, roof
    return load


FRACTALS = {
    "observatoire": _observatory,
    "falaise": _generator("generate_cliffside"),
    "inclassable": _generator("generate_uncategorized"),
    "volcanique": _generator("generate_volcanic", roof=True),
    "ocean-solide": _generator("generate_solid_ocean"),
    "marais": _generator("generate_swampland"),
    "tempete-de-neige": _generator("generate_snowblind"),
    "ressac-silencieux": _generator("generate_silent_surf"),
    "recif-de-la-sirene": _generator("generate_sirens_reef"),
    "pierre-profonde": _generator("generate_deepstone", roof=True),
    "pic-de-sunqua": _generator("generate_sunqua_peak"),
}

def face(prefabs):
    """Vue de face depuis le sud (la Falaise se grimpe) : par case (x, y), le bloc le plus au sud ; rendu comme une
    carte dont la « hauteur » est la profondeur (z) et la ligne la hauteur (y vers le haut)."""
    best = {}
    for p in prefabs:
        for (x, y, z), (name, _) in p.blocks.items():
            if name == AIR or is_small_plant(name):
                continue
            if (x, -y) not in best or z > best[(x, -y)][0]:
                best[(x, -y)] = (z, name)
    return best


def _markers(name):
    """Repères numérotés (x, z, numéro) dans l'ordre du « Déroulé » de la page du wiki."""
    if name == "observatoire":
        import generate_observatory as g
        return [(0, g.RETURN_PORTAL[2], 1), (0, g.CORE_DISTRIBUTOR_SPOT[2], 2), (0, 0, 3),
                (g.ARCHIVIST_SPOT[0], g.ARCHIVIST_SPOT[2], 4), (g.GOLEM_SPOT[0], g.GOLEM_SPOT[2], 5)]
    if name == "falaise":
        import generate_cliffside as g
        return [(g.CAMP_CENTER[0], 0, 1), (0, -g.KNEES, 2), (sum(g.GARGOYLE_X) // 2, -(g.KNEES + g.CHEST) // 2, 3),
                (0, -g.CHEST, 4), (int(g.WRIST_SEALS[0][0]), -g.SHOULDERS, 5), (int(g.WRIST_SEALS[1][0]), -g.SHOULDERS, 5),
                (0, -g.ARENA - 4, 6)]
    if name == "inclassable":
        import generate_uncategorized as g
        return [(0, (g.START[1] + g.GENERATOR_AT[2]) // 2 + 8, 1), (g.GENERATOR_AT[0], g.GENERATOR_AT[2], 2),
                (0, (g.STAIRS[2] + g.STAIRS[3]) // 2, 3), (0, int(g.TOM_AT[2]), 4),
                (0, (g.ROOM[2] + g.ARENA_CENTER[1] + g.ARENA_RADIUS) // 2, 5), g.ARENA_CENTER + (6,)]
    if name == "volcanique":
        import generate_volcanic as g
        mid = g.CORRIDOR_PATH[len(g.CORRIDOR_PATH) // 2]
        return [(0, (g.CAMP[2] + g.CAMP[3]) // 2, 1), (mid[0], mid[1], 2), g.CH_CENTER + (3,),
                g.MINE_CURVE[len(g.MINE_CURVE) // 2] + (4,), g.AR_CENTER + (5,)]
    if name == "ocean-solide":
        import generate_solid_ocean as g
        mid = g.PATH[len(g.PATH) // 2]
        return [(mid[0], mid[1], 1), g.AR_CENTER + (2,)]
    if name == "marais":
        import generate_swampland as g
        return [(0, (g.SPAWN[2] + g.ROOM[3]) // 2, 1), (g.MOSSMAN_AT[0], g.MOSSMAN_AT[2], 2), g.CL_CENTER + (3,)]
    if name == "tempete-de-neige":
        import generate_snowblind as g
        return [(g.BONFIRE_AT[0], g.BONFIRE_AT[2], 1), g.SOURCE_C + (2,), (g.ss.PACKS[2][0][0], g.ss.PACKS[2][0][1], 3),
                (g.VILLAGE_C[0], g.VILLAGE_C[1], 4)]
    if name == "ressac-silencieux":
        import silent_surf_scenery as sc
        rings = [cp[1] for cp in sc.CHECKPOINTS]
        return ([(rings[0][0], rings[0][1], 1)] + [(x, z, k + 2) for k, (x, z, _) in enumerate(rings[1:])]
                + [sc.ARENA_C + (6,)])
    if name == "recif-de-la-sirene":
        import sirens_reef_scenery as sc
        maze = ((sc.MAZE[0] + sc.MAZE[1]) // 2, (sc.MAZE[2] + sc.MAZE[3]) // 2)
        return [(sc.SPAWN[0], sc.SPAWN[2], 1), (sc.CLEARING[0], sc.CLEARING[1], 2), (sc.WALL1_AT[0], sc.WALL1_AT[1], 3),
                (sc.FORT_C[0], sc.FORT_C[1], 4), (sc.PLAZA[0], sc.PLAZA[1], 5), maze + (6,),
                ((sc.SHIP_X[0] + sc.SHIP_X[1]) // 2, sc.SHIP_Z, 7)]
    if name == "pierre-profonde":
        import deepstone_scenery as sc
        return [(sc.SPAWN[0], sc.SPAWN[2], 1), (sc.CRYSTAL_AT[0], sc.CRYSTAL_AT[2], 2),
                ((sc.WEST_HALL[0] + sc.WEST_HALL[1]) // 2, (sc.WEST_HALL[2] + sc.GRID_END[2]) // 2, 3),
                sc.SENTINEL_C + (4,), (sc.EAST_RUNES[0][0], sc.EAST_RUNES[0][2] + 4, 5), sc.QUEEN_C + (6,),
                (sc.MINOTAUR_AT[0], sc.MINOTAUR_AT[2], 7), (0, (sc.PIT_ROOM[2] + sc.PIT_ROOM[3]) // 2, 8),
                (0, (sc.LIFT[2] + sc.LIFT[3]) // 2, 9), sc.ARENA_C + (10,)]
    if name == "pic-de-sunqua":
        import sunqua_peak_scenery as sc
        water = sc.polar(171, 62)
        return [(sc.SPAWN[0], sc.SPAWN[2], 1), sc.PLINTH_C + (2,), sc.VOICE_C + (3,),
                (round(water[0]), round(water[1]), 4), sc.SORROW_C + (5,), sc.CRATER_C + (6,), sc.SUMMIT_C + (7,)]
    return []


def main():
    names = sys.argv[1:] or list(FRACTALS)
    for name in names:
        prefabs, color_of, roofed = FRACTALS[name]()
        path = OUT / f"carte-{name}.png"
        if name == "falaise":
            top = face(prefabs)
            s = render(top, color_of, path, _markers(name), crop=main_area(top), shadows=False, compass=False)
        else:
            canopy = {}
            top = surface(prefabs, roofed, canopy)
            s = render(top, color_of, path, _markers(name), crop=with_markers(main_area(top), _markers(name)),
                       shadows=not roofed, canopy=canopy)
        print(f"{path} ({s} px par bloc)")


if __name__ == "__main__":
    main()
