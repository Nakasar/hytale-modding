#!/usr/bin/env python3
"""Plans des villages du mod Peuples d'Orbis (étape 2 du plan d'implémentation).

Un plan place des prefabs VANILLA (règle n° 2 d'AGENTS.md : Server/Prefabs/Npc/Kweebec/Oak/...) autour du cœur du
village. Le Java (village/VillageBuilder) aplanit le sol sous chaque emprise, colle le prefab, puis pose le cœur, le
dépôt, le tableau et la bannière sur la place centrale. Seuls les bâtiments dont le palier est atteint sont collés :
le campement (palier 0) dès la génération, les autres avec les chantiers de l'étape 5.

Les emprises viennent de tools/vanilla-prefabs-0.7.2.txt (bornes des blocs relatifs à l'ancre, relevées dans
Assets.zip). Le script vérifie qu'aucune emprise n'en chevauche une autre (marge MARGIN) ni la place, et que tout
tient dans le rayon du plan.

Sortie : src/main/resources/Server/Nakasar/VillageLayouts/<Id>.json, et un aperçu PNG (--preview DIR).

    python3 tools/generate_village_layouts.py [--preview /mnt/project-files/peuples/village]
"""
import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "src/main/resources/Server/Nakasar/VillageLayouts"
PREFABS = Path(__file__).resolve().parent / "vanilla-prefabs-0.7.2.txt"

# Écart minimal entre deux emprises (blocs) : le Java aplanit chaque emprise avec une marge de 2 blocs et un fondu.
MARGIN = 3
# Petits décors (lanternes, bancs) : posés au bord de la place et près des maisons, un bloc d'écart suffit.
DECOR = ("/Lampposts/", "/Seats/")
DECOR_MARGIN = 1
OAK = "Npc/Kweebec/Oak/"

# Plans : id -> description. Une entrée de bâtiment : (id, palier, prefab, x, z, rotation 0-3 par quarts de tour).
# Rotation 1 = ROTATION_90 du serveur (x' = z, z' = -x), comme PrefabRotation$RotationExecutor_90.
LAYOUTS = {
    "Kweebec_Oak": {
        "People": "Kweebec",
        # Place centrale : cœur, dépôt à l'est, tableau à l'ouest, bannière au nord (rayon aplani autour du cœur).
        "PlazaRadius": 5,
        "Banner": (0, -4),
        "Buildings": [
            # Palier 0, campement : deux abris, une tour de guet, un potager, lanternes et bancs.
            ("Abri_Ouest", 0, OAK + "Houses_Small/Kweebec_Oak_Houses_Small_001", -20, 2, 0),
            ("Abri_Est", 0, OAK + "Houses_Small/Kweebec_Oak_Houses_Small_001", 20, 2, 2),
            ("Tour_De_Guet", 0, OAK + "Guard_Towers/Kweebec_Oak_Guard_Towers_001", 0, -18, 0),
            ("Potager", 0, OAK + "Garden/Medium/Kweebec_Oak_Garden_Medium_001", -12, -17, 0),
            ("Lanterne_Nord_Est", 0, OAK + "Lampposts/Kweebec_Oak_Lampposts_004", 7, -7, 0),
            ("Lanterne_Sud_Ouest", 0, OAK + "Lampposts/Kweebec_Oak_Lampposts_006", -7, 7, 0),
            ("Bancs_Sud_Est", 0, OAK + "Seats/Small/Kweebec_Oak_Seats_Small_001", 9, 9, 0),
            ("Bancs_Nord_Ouest", 0, OAK + "Seats/Small/Kweebec_Oak_Seats_Small_003", -9, -9, 0),
            # Palier 1, hameau : puits, échoppe, une maison de plus, l'enclos des lapins.
            ("Puits", 1, OAK + "Well/Kweebec_Oak_Well_001", 0, 17, 0),
            ("Echoppe", 1, OAK + "Shops/Kweebec_Oak_Shops_002", 12, -18, 0),
            ("Maison_Sud_Ouest", 1, OAK + "Houses_Small/Kweebec_Oak_Houses_Small_002", -26, 30, 0),
            ("Enclos", 1, OAK + "Bunny_Area/Kweebec_Oak_Bunny_Area_003", 37, -16, 0),
            # Palier 2, village : grande maison, maison des gardes, deuxième tour, deuxième échoppe.
            ("Grande_Maison", 2, OAK + "Houses_Large/Kweebec_Oak_Houses_Large_001", 26, 36, 0),
            ("Maison_Des_Gardes", 2, OAK + "Houses_Guard/Kweebec_Oak_Houses_Guard_001", -46, -12, 0),
            ("Tour_Est", 2, OAK + "Guard_Towers/Kweebec_Oak_Guard_Towers_002", 44, 8, 0),
            ("Echoppe_Ouest", 2, OAK + "Shops/Kweebec_Oak_Shops_005", -24, -24, 0),
            # Palier 3, bourg : le Grand-Père, cœur sacré du bosquet, et le grand potager.
            ("Grand_Pere", 3, OAK + "Grandfather/Kweebec_Oak_Grandfather_001", -2, -40, 0),
            ("Grand_Potager", 3, OAK + "Garden/Large/Kweebec_Oak_Garden_Large_001", 0, 32, 0),
        ],
    },
}


def load_bounds():
    bounds = {}
    for line in PREFABS.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) == 7:
            bounds[parts[0]] = tuple(int(v) for v in parts[1:])
        else:
            bounds[parts[0]] = None
    return bounds


def rotate(x, z, rotation):
    """Même convention que PrefabRotation du serveur (quarts de tour)."""
    for _ in range(rotation % 4):
        x, z = z, -x
    return x, z


def footprint(b, cx, cz, rotation):
    """Rectangle (x0, x1, z0, z1) en coordonnées du plan."""
    min_x, max_x, _, _, min_z, max_z = b
    corners = [rotate(x, z, rotation) for x in (min_x, max_x) for z in (min_z, max_z)]
    xs = [c[0] for c in corners]
    zs = [c[1] for c in corners]
    return cx + min(xs), cx + max(xs), cz + min(zs), cz + max(zs)


def overlaps(a, b, margin):
    return not (a[1] + margin < b[0] or b[1] + margin < a[0] or a[3] + margin < b[2] or b[3] + margin < a[2])


def build(layout_id, spec, bounds):
    errors = []
    rects = []
    plaza = spec["PlazaRadius"]
    plaza_rect = (-plaza, plaza, -plaza, plaza)
    buildings = []
    radius = plaza
    for bid, tier, prefab, x, z, rotation in spec["Buildings"]:
        if prefab not in bounds:
            errors.append(f"{layout_id}/{bid} : prefab vanilla inconnu {prefab}")
            continue
        b = bounds[prefab]
        if b is None:
            errors.append(f"{layout_id}/{bid} : prefab {prefab} non mesuré (trop gros)")
            continue
        rect = footprint(b, x, z, rotation)
        if overlaps(rect, plaza_rect, 1):
            errors.append(f"{layout_id}/{bid} : empiète sur la place {rect}")
        decor = any(k in prefab for k in DECOR)
        for other_id, other, other_decor in rects:
            if overlaps(rect, other, DECOR_MARGIN if decor or other_decor else MARGIN):
                errors.append(f"{layout_id}/{bid} chevauche {other_id} : {rect} / {other}")
        rects.append((bid, rect, decor))
        far = max(math.hypot(px, pz) for px in rect[:2] for pz in rect[2:])
        radius = max(radius, math.ceil(far))
        buildings.append({
            "Id": bid,
            "Tier": tier,
            "Prefab": prefab,
            "X": x,
            "Z": z,
            "Rotation": rotation,
            "MinX": rect[0] - x,
            "MaxX": rect[1] - x,
            "MinZ": rect[2] - z,
            "MaxZ": rect[3] - z,
        })
    bx, bz = spec["Banner"]
    doc = {
        "$Comment": "Plan de village généré par tools/generate_village_layouts.py (ne pas modifier à la main) : prefabs "
                    "vanilla collés par village/VillageBuilder autour du cœur, emprises (MinX..MaxZ) relatives au point "
                    "de collage après rotation.",
        "People": spec["People"],
        "Radius": radius,
        "PlazaRadius": plaza,
        "BannerX": bx,
        "BannerZ": bz,
        "Buildings": buildings,
    }
    return doc, rects, errors


def preview(layout_id, doc, rects, out_dir):
    from PIL import Image, ImageDraw

    radius = doc["Radius"] + 4
    scale = 6
    size = (2 * radius + 1) * scale
    img = Image.new("RGB", (size, size + 60), (52, 74, 44))
    d = ImageDraw.Draw(img)
    colors = [(222, 196, 120), (150, 200, 110), (110, 170, 210), (210, 130, 200)]

    def px(x, z):
        return (x + radius) * scale, (z + radius) * scale

    d.ellipse([*px(-doc["Radius"], -doc["Radius"]), *px(doc["Radius"], doc["Radius"])], outline=(90, 110, 80), width=2)
    p = doc["PlazaRadius"]
    d.rectangle([*px(-p, -p), *px(p + 1, p + 1)], fill=(160, 140, 110))
    for building, (_, rect, _) in zip(doc["Buildings"], rects):
        c = colors[building["Tier"]]
        d.rectangle([*px(rect[0], rect[2]), *px(rect[1] + 1, rect[3] + 1)], outline=c, width=3)
        tx, tz = px(building["X"], building["Z"])
        d.text((tx - 20, tz - 6), f"{building['Id']} ({building['Tier']})", fill=(255, 255, 255))
    d.rectangle([*px(0, 0), *px(1, 1)], fill=(255, 60, 60))
    d.rectangle([*px(doc["BannerX"], doc["BannerZ"]), *px(doc["BannerX"] + 1, doc["BannerZ"] + 1)], fill=(80, 220, 80))
    legend = "Paliers : 0 jaune (campement), 1 vert (hameau), 2 bleu (village), 3 rose (bourg). Rouge : coeur ; vert vif : banniere. Nord en haut (-Z)."
    d.text((8, size + 20), f"{layout_id} - rayon {doc['Radius']}", fill=(255, 255, 255))
    d.text((8, size + 38), legend, fill=(230, 230, 230))
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"plan_{layout_id.lower()}.png"
    img.save(path)
    print(f"aperçu : {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", type=Path, help="dossier où écrire l'aperçu PNG des plans")
    args = parser.parse_args()
    bounds = load_bounds()
    OUT.mkdir(parents=True, exist_ok=True)
    failed = False
    for layout_id, spec in LAYOUTS.items():
        doc, rects, errors = build(layout_id, spec, bounds)
        for e in errors:
            print("ERREUR", e)
        failed |= bool(errors)
        path = OUT / f"{layout_id}.json"
        path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{path.relative_to(ROOT)} : {len(doc['Buildings'])} bâtiments, rayon {doc['Radius']}")
        if args.preview:
            preview(layout_id, doc, rects, args.preview)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
