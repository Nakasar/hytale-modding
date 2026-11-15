#!/usr/bin/env python3
"""Source de l'Écho : l'oasis que fait naître la Graine d'Écho (fin de la chaîne kweebec) dans les Dunes.

Kevin (2026-11-15) : l'ancien bassin, le prefab kweebec vanilla Kweebec_Oak_Water_Pool_005 collé tel quel, faisait une
dalle d'herbe et de terre posée sur le sable, avec deux pousses kweebec (ses marqueurs de spawn) et sans rien qui dise
à quoi il sert. Ce script écrit :
  * le prefab du mod Server/Prefabs/Nakasar/Peuples/Oasis/Echo_Spring (blocs et eau, blocs VANILLA sauf la jarre) :
    un bassin creusé dans le sable, une margelle de terre sèche et de gravier, roseaux, herbes et buissons arides, deux
    cactus, un dallage de grès avec une colonne à torche feran et la Jarre de la Source ;
  * la Jarre de la Source (Furniture_Feran_Pot vanilla, incassable) et son interaction (zone/EchoSpring) ;
  * le bloc de traductions « Source de l'Écho » en tête des deux .lang.
Le Java (zone/EchoSpring) aplanit d'abord le site en sable (Grading, talus d'un bloc), colle ce prefab, remplace le
sable et le gravier par la variante locale (rouge, blanc), puis colle les palmiers et le rocher d'oasis vanilla.

Repère : x est, z sud, y = 0 surface aplanie (sable), y = 1 premier bloc d'air ; l'ancre (0, 0, 0) est le centre du site.

    python3 tools/generate_echo_spring.py [--preview out.png]
"""
import argparse
import json
import math
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
RES = ROOT / "src/main/resources/Server"
PREFAB = RES / "Prefabs/Nakasar/Peuples/Oasis/Echo_Spring.prefab.json"
BLOCK_IDS = TOOLS / "vanilla-block-ids-0.7.2.txt"

JAR = "Nakasar_Peuples_Echo_Spring_Jar"
INTERACTION = "Nakasar_Peuples_Echo_Spring"
LANG_BEGIN = "# ---- Source de l'Écho (généré par tools/generate_echo_spring.py, ne pas modifier à la main) ----"
LANG_END = "# ---- Fin de la Source de l'Écho ----"

# Le bassin : centre un peu au nord, pour laisser le dallage de la jarre au sud.
POOL = (0, -1)
# Rayon du site aplani (demi-côté), repris par EchoSpring.HALF.
HALF = 6
# Dallage de la jarre (x0, x1, z0, z1), jarre et colonne à torche.
PAVING = (-1, 1, 3, 4)
JAR_AT = (1, 1, 4)        # tournée vers le bassin (lacet 2 = nord)
TORCH_AT = (-1, 4)
CACTI = [(5, -4, "Plant_Cactus_2"), (-5, 5, "Plant_Cactus_1")]
# Pièces vanilla collées par le Java (mêmes valeurs dans EchoSpring.PIECES) : prefab, x, y, z.
PIECES = [("Orbis/Trees/Palm/Stage_3/Palm_Stage3_002", -4, 1, -3),
          ("Orbis/Trees/Palm/Stage_2/Palm_Stage2_001", 3, 1, -4),
          ("Orbis/Trees/Palm/Stage_3/Palm_Stage3_004", 4, 1, 2),
          ("Rock_Formations/Rocks/Sandstone/Oasis/Rock_Oasis_Small_01", -5, 1, 2)]
# Cases laissées libres pour les pièces (troncs, rocher).
KEEP_FREE = {(-4, -3), (3, -4), (4, 2)} | {(x, z) for x in range(-6, -2) for z in range(-1, 6)}

FR, EN = {}, {}


def t(key, fr, en):
    FR[key] = fr
    EN[key] = en


def h(x, z, salt=0):
    """Bruit déterministe 0..1 (même formule que generate_village_hearts.py)."""
    n = (x * 73856093) ^ (z * 19349663) ^ (salt * 83492791)
    n = (n ^ (n >> 13)) * 1274126177
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


def pool_radius(x, z):
    a = math.atan2(z - POOL[1], x - POOL[0])
    return 2.6 + 0.5 * math.sin(3 * a + 1.3) + 0.3 * math.sin(5 * a + 0.4)


def build():
    blocks = {}   # (x, y, z) -> (nom, rotation)
    fluids = {}   # (x, y, z) -> nom

    def put(x, y, z, name, r=0):
        blocks[(x, y, z)] = (name, r)

    water = set()
    for x in range(-HALF, HALF + 1):
        for z in range(-HALF, HALF + 1):
            d = math.hypot(x - POOL[0], z - POOL[1])
            if d <= pool_radius(x, z):
                water.add((x, z))
    deep = {(x, z) for (x, z) in water if math.hypot(x - POOL[0], z - POOL[1]) <= pool_radius(x, z) - 1.1}
    near_water = {(x, z) for x in range(-HALF, HALF + 1) for z in range(-HALF, HALF + 1)
                  if (x, z) not in water and any((x + dx, z + dz) in water for dx in (-1, 0, 1) for dz in (-1, 0, 1))}

    # Bassin : eau sur un ou deux blocs, fond de sable, rien au-dessus.
    for (x, z) in water:
        depth = 2 if (x, z) in deep else 1
        for y in range(1 - depth, 1):
            put(x, y, z, "Empty")
            fluids[(x, y, z)] = "Water_Source"
        put(x, -depth, z, "Soil_Sand")
        put(x, -depth - 1, z, "Soil_Sand")
        for y in range(1, 4):
            put(x, y, z, "Empty")

    px0, px1, pz0, pz1 = PAVING
    for x in range(-HALF, HALF + 1):
        for z in range(-HALF, HALF + 1):
            if (x, z) in water:
                continue
            d = math.hypot(x - POOL[0], z - POOL[1]) - pool_radius(x, z)
            if px0 <= x <= px1 and pz0 <= z <= pz1:
                put(x, 0, z, "Rock_Sandstone_Brick_Smooth" if (x + z) % 2 else "Rock_Sandstone_Cobble")
                continue
            if (x, z) in near_water:
                # Margelle : terre sèche, gravier et un peu d'herbe sèche ; roseaux au bord de l'eau.
                n = h(x, z, 3)
                put(x, 0, z, "Soil_Grass_Dry" if n < 0.4 else "Soil_Dirt_Dry" if n < 0.75 else "Soil_Gravel_Sand")
                if (x, z) in KEEP_FREE:
                    continue
                p = h(x, z, 4)
                if p < 0.5:
                    put(x, 1, z, "Plant_Reeds_Water")
                elif p < 0.75 and n < 0.4:
                    put(x, 1, z, "Plant_Grass_Arid_Tall")
                continue
            # Couronne : l'herbe sèche s'éclaircit en s'éloignant de l'eau, puis le sable reprend.
            chance = max(0.0, 0.75 - 0.22 * d)
            if h(x, z, 5) < chance:
                put(x, 0, z, "Soil_Grass_Dry" if h(x, z, 6) < 0.7 else "Soil_Dirt_Dry")
                if (x, z) not in KEEP_FREE:
                    p = h(x, z, 7)
                    if p < 0.25:
                        put(x, 1, z, "Plant_Grass_Arid")
                    elif p < 0.4:
                        put(x, 1, z, "Plant_Grass_Arid_Short")
                    elif p < 0.5:
                        put(x, 1, z, "Plant_Fern_Arid")
                    elif p < 0.56:
                        put(x, 1, z, "Plant_Bush_Arid")
            elif d > 2.5 and (x, z) not in KEEP_FREE and h(x, z, 8) < 0.08:
                put(x, 1, z, "Plant_Bush_Arid_Sharp")
    for (x, z, name) in CACTI:
        put(x, 1, z, name)

    # Colonne de grès à torche feran (comme le cœur feran) et la jarre.
    tx, tz = TORCH_AT
    put(tx, 1, tz, "Rock_Sandstone_Brick_Pillar_Base")
    put(tx, 2, tz, "Rock_Sandstone_Brick_Pillar_Middle")
    put(tx, 3, tz, "Rock_Sandstone_Brick_Pillar_Base", 8)
    put(tx, 4, tz, "Furniture_Feran_Torch")
    jx, jy, jz = JAR_AT
    put(jx, jy, jz, JAR, 2)
    return blocks, fluids


def check(blocks):
    known = {line.strip() for line in BLOCK_IDS.read_text(encoding="utf-8").splitlines() if line.strip()}
    bad = sorted({n for (n, _) in blocks.values() if n not in known and n not in ("Empty", JAR)})
    if bad:
        raise SystemExit(f"blocs inconnus d'Assets.zip : {bad}")


def write(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prefab(blocks, fluids):
    out = []
    for (x, y, z), (name, r) in sorted(blocks.items(), key=lambda kv: (kv[0][1], kv[0][2], kv[0][0])):
        b = {"x": x, "y": y, "z": z, "name": name}
        if r:
            b["rotation"] = r
        out.append(b)
    return {
        "version": 8,
        "blockIdVersion": 11,
        "anchorX": 0,
        "anchorY": 0,
        "anchorZ": 0,
        "blocks": out,
        "fluids": [{"x": x, "y": y, "z": z, "name": n, "level": 1} for (x, y, z), n in sorted(fluids.items())],
        "entities": [],
    }


def assets():
    write(RES / f"Item/Items/Nakasar/Peuples/{JAR}.json", {
        "$Comment": "Jarre de la Source de l'Écho (generate_echo_spring.py) : jarre feran vanilla ; l'utiliser explique "
                    "la source et remplit une Outre d'oasis par jour de jeu (zone/EchoSpring).",
        "Parent": "Furniture_Feran_Pot",
        "TranslationProperties": {
            "Name": f"nakasar_peuples.items.{JAR}.name",
            "Description": f"nakasar_peuples.items.{JAR}.description",
        },
        "Quality": "Developer",
        "BlockType": {
            "Gathering": {"Breaking": {"GatherType": "Unbreakable"}},
            "Interactions": {"Use": {"Interactions": [INTERACTION]}},
        },
    })
    write(RES / f"Item/Interactions/Nakasar/Peuples/{INTERACTION}.json", {
        "$Comment": "Jarre de la Source de l'Écho : page d'explication et Outre d'oasis du jour (zone/EchoSpring).",
        "Type": "Nakasar_Peuples_EchoSpring",
    })


def texts():
    k = "spring."
    t(f"items.{JAR}.name", "Jarre de la Source", "Spring Jar")
    t(f"items.{JAR}.description", "L'eau de la Source de l'Écho y reste fraîche. Elle remplit une Outre d'oasis par jour.",
      "The water of the Echo Spring stays cool inside. It fills one oasis waterskin a day.")
    t(k + "planted",
      "La Graine d'Écho chante : une source jaillit du sable en {x} {y} {z}. Approche-toi de la jarre au bord de l'eau.",
      "The Echo Seed sings: a spring wells up from the sand at {x} {y} {z}. Go to the jar by the water.")
    t(k + "noRoom", "La graine refuse ce sol : il faut un endroit plus dégagé et moins pentu, loin des autres sources.",
      "The seed refuses this ground: find a clearer, flatter spot, away from other springs.")
    t(k + "enter", "Source de l'Écho : la soif ne te prendra pas ici.", "Echo Spring: thirst will not take you here.")
    t(k + "leave", "Tu quittes l'ombre de la Source de l'Écho.", "You leave the shade of the Echo Spring.")
    t(k + "title", "Source de l'Écho", "Echo Spring")
    t(k + "body1", "La Graine d'Écho a fait jaillir cette source. Elle chante encore la voix du Grand-Père kweebec.",
      "The Echo Seed made this spring well up. It still sings with the voice of the Kweebec Grandfather.")
    t(k + "body2", "Abri : à moins de {radius} blocs de la source, la soif des Dunes ne te prend pas, même en plein jour.",
      "Shelter: within {radius} blocks of the spring, the thirst of the Dunes does not take you, even at midday.")
    t(k + "body3", "Les Feran reconnaissent son chant : tu es au moins Toléré chez eux, leurs marchands te servent.",
      "The Feran know its song: you are at least Tolerated among them, and their merchants serve you.")
    t(k + "body4", "La jarre remplit une Outre d'oasis par jour : bue, elle chasse la soif 20 minutes loin d'ici.",
      "The jar fills one oasis waterskin a day: drunk, it keeps the thirst away for 20 minutes far from here.")
    t(k + "filled", "Tu remplis une Outre d'oasis à la jarre. Reviens demain pour la suivante.",
      "You fill an oasis waterskin at the jar. Come back tomorrow for the next one.")
    t(k + "alreadyFilled", "La jarre se remplit lentement : reviens demain pour une autre outre.",
      "The jar fills slowly: come back tomorrow for another waterskin.")
    t(k + "orphan", "Cette jarre est sèche : aucune Source de l'Écho ici.", "This jar is dry: no Echo Spring here.")
    c = "command."
    t(c + "spring.desc", "Reconstruit la Source de l'Écho la plus proche (ancien bassin kweebec compris, ops)",
      "Rebuild the nearest Echo Spring (old Kweebec pool included, ops)")
    t(c + "spring.none", "Aucune Source de l'Écho à moins de {radius} blocs.", "No Echo Spring within {radius} blocks.")
    t(c + "spring.done", "Source de l'Écho reconstruite en {x} {y} {z}.", "Echo Spring rebuilt at {x} {y} {z}.")
    t(c + "spring.failed", "Reconstruction impossible ici (zone pas chargée ?).", "Could not rebuild here (area not loaded?).")


def write_langs():
    for locale, table in (("fr-FR", FR), ("en-US", EN)):
        path = RES / f"Languages/{locale}/nakasar_peuples.lang"
        text = path.read_text(encoding="utf-8")
        if LANG_BEGIN in text:
            before, rest = text.split(LANG_BEGIN, 1)
            after = rest.split(LANG_END, 1)[1].lstrip("\n")
            text = before + after
        existing = {line.split("=", 1)[0].strip() for line in text.splitlines() if "=" in line and not line.startswith("#")}
        dup = sorted(k for k in table if k in existing)
        if dup:
            raise SystemExit(f"clés déjà présentes dans {locale} (hors bloc Source de l'Écho) : {dup[:10]}")
        block = [LANG_BEGIN] + [f"{k} = {v}" for k, v in table.items()] + [LANG_END, ""]
        path.write_text("\n".join(block) + text, encoding="utf-8")
        print(f"{path.relative_to(ROOT)} : {len(table)} clés de la Source de l'Écho")


def preview(blocks, fluids, out):
    """Vue de dessus (un pixel de 16 par case) : utile pour relire la forme sans lancer le jeu."""
    from PIL import Image, ImageDraw
    colors = {"Soil_Sand": (222, 196, 120), "Soil_Grass_Dry": (150, 150, 70), "Soil_Dirt_Dry": (150, 110, 70),
              "Soil_Gravel_Sand": (190, 170, 130), "Rock_Sandstone_Cobble": (200, 170, 110),
              "Rock_Sandstone_Brick_Smooth": (215, 185, 125), "Plant_Reeds_Water": (90, 140, 60),
              "Plant_Grass_Arid": (170, 160, 80), "Plant_Grass_Arid_Short": (180, 170, 90), "Plant_Grass_Arid_Tall": (160, 150, 70),
              "Plant_Fern_Arid": (110, 140, 60), "Plant_Bush_Arid": (120, 120, 60), "Plant_Bush_Arid_Sharp": (130, 120, 60),
              "Plant_Cactus_1": (60, 130, 60), "Plant_Cactus_2": (60, 130, 60), "Furniture_Feran_Torch": (250, 160, 40),
              JAR: (170, 90, 50)}
    S = 16
    n = 2 * HALF + 1
    img = Image.new("RGB", (n * S, n * S), colors["Soil_Sand"])
    d = ImageDraw.Draw(img)
    for x in range(-HALF, HALF + 1):
        for z in range(-HALF, HALF + 1):
            col = None
            for y in range(4, -4, -1):
                if (x, y, z) in fluids:
                    col = (60, 120, 200)
                    break
                b = blocks.get((x, y, z))
                if b and b[0] != "Empty":
                    col = colors.get(b[0], (120, 120, 120))
                    break
            if col:
                X, Z = (x + HALF) * S, (z + HALF) * S
                d.rectangle([X, Z, X + S - 1, Z + S - 1], fill=col)
    for (_, px, _, pz) in PIECES:
        X, Z = (px + HALF) * S, (pz + HALF) * S
        d.ellipse([X + 2, Z + 2, X + S - 3, Z + S - 3], outline=(40, 90, 40), width=3)
    img.save(out)
    print(f"aperçu : {out}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", type=Path)
    args = parser.parse_args()
    blocks, fluids = build()
    check(blocks)
    write(PREFAB, prefab(blocks, fluids))
    print(f"{PREFAB.relative_to(ROOT)} : {len(blocks)} blocs, {len(fluids)} cases d'eau")
    assets()
    texts()
    write_langs()
    if args.preview:
        preview(blocks, fluids, args.preview)


if __name__ == "__main__":
    main()
