"""Textures et icônes tirées d'assets vanilla (passe « vanilla très proche », Kevin, 25 octobre 2026).

    python3 mods/nakasar-fractals/tools/generate_vanilla_recolors.py --assets CHEMIN/Assets.zip

`--assets` : Assets.zip du jeu 0.7.2 (ou un dossier où il est extrait). Les PNG produits sont versionnés : les autres
générateurs n'ont pas besoin d'Assets.zip, ils pointent vers ces fichiers.

- Potions des Brumes : flacon d'antidote du jeu (Potion_Onion + Potion_Onion_Poison) dont le liquide vert prend la
  couleur de la potion et dont l'étiquette perd sa tête de mort pour le glyphe de la potion (épée, plume, bouclier) ;
  les grandes ont un bouchon doré. Texture du modèle et icône (Weapon_Bomb_Potion_Poison) repeintes de la même façon.
- Éclat de Brume : fragment de cristal violet du jeu (Crystal_Fragment) repeint en dégradé indigo → pervenche → blanc
  bleuté, texture et icône.
- Canon à vent : icône rendue depuis le canon du Gobliterator (le bloc garde le modèle vanilla).
- Fleur de poison (PNJ) : copie de la fleur empoisonnée du jeu (Plant_Flower_Poisoned_Orange : Alien.blockymodel,
  texture Poisoned) dans NPC/, seul dossier où un modèle de PNJ peut lire ses fichiers (Characters/, NPC/, Items/, VFX/).

Seconde passe (Kevin, 25 octobre 2026, 22 h 19) :
- Cristal de glace corrompu et Éclat de glace (PNJ) : grands cristaux vanilla des blocs Rock_Crystal_Void_Large
  (Crystal_Large_Pointy, texture Void) et Rock_Crystal_White_Large (Crystal_Big, texture White), copiés dans NPC/.
- Cosmétiques de la saison 1 (Items/Nakasar/Fractals/Cosmetics/<Nom>/, icônes comprises ; generate_cosmetics.py n'écrit
  plus que les objets et la langue) : capuche = Hoodie_LongEnd du jeu (capuche du Sorcier de Blazen, violette) au liseré
  doré ; couronne = KingsCrown, velours violet des Brumes ; mantelet = Cape_King_NoNeck, drap indigo de l'Archidevin
  (fourrure et or d'origine). Les textures « greyscale » du jeu sont teintées ici, une pièce d'armure n'a pas de dégradé.

Style Hytale (Kevin, 25 octobre 2026, 22 h 36) : échantillons de textures de blocs vanilla copiés dans tools/materials/
(fractal_materials.SWATCHES), lus par nos peintres de modèles.
"""
import colorsys
import io
import json
import sys
import zipfile
from pathlib import Path

from PIL import Image

import blockymodel_render as br
import fractal_materials as fmat
from generate_potions import KINDS

PACK = Path(__file__).resolve().parent.parent / "src/main/resources/Common"
TEXTURES = PACK / "Items/Nakasar/Fractals/Vanilla"
ICONS = PACK / "Icons/Items/Nakasar/Fractals/Vanilla"

POTION_TEXTURE = "Common/Items/Weapons/Bomb/Potion_Onion_Poison.png"
POTION_ICON = "Common/Icons/ItemsGenerated/Weapon_Bomb_Potion_Poison.png"
SHARD_TEXTURE = "Common/Resources/Crystals/Crystal_Fragment_Textures/Purple.png"
SHARD_ICON = "Common/Icons/ItemsGenerated/Ingredient_Crystal_Fragments_Purple.png"
CANNON = "Common/NPC/Boss/Goblin_Gobliterator/Models/Goblin_Cannon"
PLANT = "Common/Blocks/Foliage/Plants/Alien"
BLOOM = PACK / "NPC/Nakasar/Fractals/Poison_Bloom"
CRYSTALS = {"Corrupted_Crystal": ("Crystal_Large_Pointy", "Void"), "Ice_Shard": ("Crystal_Big", "White")}
COSMETICS = PACK / "Items/Nakasar/Fractals/Cosmetics"
COSMETIC_ICONS = PACK / "Icons/Items/Nakasar/Fractals/Cosmetics"
HOOD = ("Common/Cosmetics/Head/Hoodie_LongEnd", "Common/Cosmetics/Head/Blazen_Wizard_Hoodie_Texture.png")
CROWN = ("Common/Cosmetics/Head/KingsCrown", "Common/Cosmetics/Head/KingsCrown_Red.png")
MANTLE = ("Common/Cosmetics/Capes/Cape_King_NoNeck", "Common/Cosmetics/Capes/Cape_King_Texture.png")

PARCHMENT = (236, 220, 178)
PARCHMENT_EDGE = (196, 172, 124)
GOLD = [(110, 70, 20), (200, 150, 50), (250, 214, 110), (255, 246, 200)]
MIST = [(40, 30, 90), (140, 150, 240), (225, 240, 255)]
VELVET = [(34, 16, 60), (96, 52, 168), (176, 134, 255), (226, 208, 255)]
ROBE = [(18, 12, 34), (52, 36, 78), (98, 76, 150), (150, 130, 210)]

# Glyphes de l'étiquette (7 × 7), haut = côté du goulot.
GLYPHS = {
    "sword": ["...#...", "...#...", "...#...", "...#...", ".#####.", "...#...", "...#..."],
    "feather": ["....###", "...####", "..####.", ".####..", ".##....", "#......", "#......"],
    "shield": ["#######", "#######", "#######", ".#####.", ".#####.", "..###..", "...#..."],
}


class Assets:
    def __init__(self, path):
        self.path = Path(path)
        self.zip = zipfile.ZipFile(self.path) if self.path.is_file() else None

    def read(self, name):
        return self.zip.read(name) if self.zip else (self.path / name).read_bytes()

    def image(self, name):
        return Image.open(io.BytesIO(self.read(name))).convert("RGBA")


def hsv(p):
    return colorsys.rgb_to_hsv(p[0] / 255, p[1] / 255, p[2] / 255)


def is_liquid(p):
    h, s, _ = hsv(p)
    return p[3] >= 16 and 60 / 360 <= h < 170 / 360 and s > 0.25


def is_label(p):
    h, s, _ = hsv(p)
    return p[3] >= 16 and 20 / 360 < h < 60 / 360 and s > 0.15


def ramp(stops, t):
    t = min(1.0, max(0.0, t)) * (len(stops) - 1)
    k = min(int(t), len(stops) - 2)
    f = t - k
    return tuple(round(a + (b - a) * f) for a, b in zip(stops[k], stops[k + 1]))


def cells_of(img, select, box=None):
    px = img.load()
    x0, y0, x1, y1 = box or (0, 0, img.width, img.height)
    return [(x, y) for y in range(y0, y1) for x in range(x0, x1) if select(px[x, y])]


def gradient_map(img, cells, stops):
    """Repeint les pixels `cells` selon leur valeur (min → max de ces pixels) le long du dégradé `stops`."""
    px = img.load()
    values = [hsv(px[x, y])[2] for x, y in cells]
    lo, hi = min(values), max(values)
    for (x, y), v in zip(cells, values):
        px[x, y] = ramp(stops, (v - lo) / max(hi - lo, 1e-6)) + (px[x, y][3],)


def tint(color):
    return [tuple(round(c * f) for c in color) for f in (0.3, 0.6)] + [color, tuple(round(c + (255 - c) * 0.55) for c in color)]


def paint_label(img, cells, glyph, ink):
    """Étiquette : parchemin uni (bord plus sombre) à la place de la tête de mort, puis le glyphe à l'encre au centre."""
    px = img.load()
    cells = set(cells)
    for x, y in cells:
        edge = any((x + dx, y + dy) not in cells for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        px[x, y] = (PARCHMENT_EDGE if edge else PARCHMENT) + (255,)
    mark = Image.new("RGBA", (7, 7))
    for y, row in enumerate(GLYPHS[glyph]):
        for x, c in enumerate(row):
            if c == "#":
                mark.putpixel((x, y), ink + (255,))
    cx = sum(x for x, _ in cells) / len(cells)
    cy = sum(y for _, y in cells) / len(cells)
    ox, oy = round(cx - mark.width / 2 + 0.5), round(cy - mark.height / 2 + 0.5)
    for y in range(mark.height):
        for x in range(mark.width):
            if mark.getpixel((x, y))[3] and (ox + x, oy + y) in cells:
                px[ox + x, oy + y] = mark.getpixel((x, y))


def is_grey(p):
    return p[3] >= 16 and hsv(p)[1] < 0.1


def is_trim(p):
    h, s, v = hsv(p)
    return p[3] >= 16 and 20 / 360 < h < 55 / 360 and s > 0.12 and v > 0.35


def is_cloth(p):
    """Drap gris foncé de la cape royale ; la fourrure, gris très clair, garde sa teinte."""
    return is_grey(p) and hsv(p)[2] < 0.6


def cosmetic(assets, name, source, select, stops, yaw=-25):
    """Modèle porté du jeu copié tel quel, texture repeinte (pixels `select` le long de `stops`), icône rendue."""
    model, texture = source
    out = COSMETICS / name
    out.mkdir(parents=True, exist_ok=True)
    doc = json.loads(assets.read(f"{model}.blockymodel"))
    doc["format"] = "character"
    (out / "Model.blockymodel").write_text(json.dumps(doc, indent=2) + "\n")
    img = assets.image(texture)
    gradient_map(img, cells_of(img, select), stops)
    img.save(out / "Texture.png")
    COSMETIC_ICONS.mkdir(parents=True, exist_ok=True)
    br.render(br.boxes(doc), img, 256, yaw=yaw, pitch=12).resize((64, 64), Image.LANCZOS).save(COSMETIC_ICONS / f"{name}.png")


def potion(src, color, glyph, large, icon):
    # Zones lues sur le flacon d'origine (le liquide repeint peut prendre la teinte du parchemin). Icône : flacon couché
    # à 45° (goulot en haut à droite), étiquette en bas à gauche, bouchon en haut à droite.
    label = cells_of(src, is_label, (6, 20, 32, 38) if icon else (18, 20, 36, 34))
    cork = cells_of(src, is_label, (38, 0, 64, 20) if icon else (40, 0, 64, 32))
    img = src.copy()
    gradient_map(img, cells_of(src, is_liquid), tint(color))
    paint_label(img, label, glyph, tuple(round(c * 0.35) for c in color))
    if large:
        gradient_map(img, cork, GOLD)
    return img


def main():
    if "--assets" not in sys.argv:
        sys.exit(__doc__)
    assets = Assets(sys.argv[sys.argv.index("--assets") + 1])
    TEXTURES.mkdir(parents=True, exist_ok=True)
    ICONS.mkdir(parents=True, exist_ok=True)
    texture, icon = assets.image(POTION_TEXTURE), assets.image(POTION_ICON)
    for kind, _, _, color, glyph, *_ in KINDS:
        for large in (False, True):
            name = f"Mist_Potion_{'Large_' if large else ''}{kind}"
            potion(texture, color, glyph, large, False).save(TEXTURES / f"{name}.png")
            potion(icon, color, glyph, large, True).save(ICONS / f"{name}.png")
    for src, out in ((SHARD_TEXTURE, TEXTURES), (SHARD_ICON, ICONS)):
        img = assets.image(src)
        gradient_map(img, cells_of(img, lambda p: p[3] >= 16), MIST)
        img.save(out / "Mist_Shard.png")
    model = json.loads(assets.read(f"{CANNON}.blockymodel"))
    big = br.render(br.boxes(model), assets.image(f"{CANNON}.png"), 256)
    big.resize((64, 64), Image.LANCZOS).save(ICONS / "Wind_Cannon.png")
    BLOOM.mkdir(parents=True, exist_ok=True)
    plant = json.loads(assets.read(f"{PLANT}.blockymodel"))
    plant["format"] = "character"
    (BLOOM / "Model.blockymodel").write_text(json.dumps(plant, indent=2) + "\n")
    (BLOOM / "Texture.png").write_bytes(assets.read(f"{PLANT}_Textures/Poisoned.png"))
    for name, (model, texture) in CRYSTALS.items():
        out = PACK / f"NPC/Nakasar/Fractals/{name}"
        out.mkdir(parents=True, exist_ok=True)
        doc = json.loads(assets.read(f"Common/Resources/Crystals/{model}.blockymodel"))
        doc["format"] = "character"
        (out / "Model.blockymodel").write_text(json.dumps(doc, indent=2) + "\n")
        (out / "Texture.png").write_bytes(assets.read(f"Common/Resources/Crystals/Crystal_Big_Textures/{texture}.png"))
    fmat.DIR.mkdir(exist_ok=True)
    for key, name in fmat.SWATCHES.items():
        (fmat.DIR / f"{key}.png").write_bytes(assets.read(f"Common/BlockTextures/{name}.png"))
    cosmetic(assets, "Archdiviner_Hood", HOOD, is_trim, GOLD)
    cosmetic(assets, "Mist_Crown", CROWN, is_grey, VELVET)
    cosmetic(assets, "Mist_Mantle", MANTLE, is_cloth, ROBE, yaw=155)
    print(f"{len(KINDS) * 2} potions, éclat de Brume, icône du canon à vent, fleur de poison, 2 cristaux, 3 cosmétiques, {len(fmat.SWATCHES)} échantillons de matières")


if __name__ == "__main__":
    main()
