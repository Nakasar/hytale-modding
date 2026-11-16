#!/usr/bin/env python3
"""Plans des villages du mod Peuples d'Orbis (étape 2 du plan d'implémentation).

Un plan place des prefabs VANILLA (règle n° 2 d'AGENTS.md : Server/Prefabs/Npc/Kweebec/Oak/...) autour du cœur du
village. Le Java (village/VillageBuilder) aplanit le sol sous chaque emprise, colle le prefab, puis pose le cœur, le
dépôt, le tableau et la bannière sur la place centrale. Seuls les bâtiments dont le palier est atteint sont collés :
le campement (palier 0) dès la génération, les autres avec les chantiers de l'étape 5.

Les emprises viennent de tools/vanilla-prefabs-0.7.2.txt (bornes des blocs relatifs à l'ancre, relevées dans
Assets.zip). Le script vérifie qu'aucune emprise n'en chevauche une autre (marge MARGIN) ni la place, et que tout
tient dans le rayon du plan.

Étape 5 : chaque palier au-delà du campement a son chantier (matériaux pris au dépôt, durée en heures de jeu), et le
plan porte les métiers du village (rôle, dialogue, poste de jour et logis de nuit, calculés devant le bâtiment, du côté
de la place). Les bâtiments gardent leur hauteur (MinY..MaxY) pour l'échafaudage et l'incendie.

Sortie : src/main/resources/Server/Nakasar/VillageLayouts/<Id>.json, et un aperçu PNG (--preview DIR).

    python3 tools/generate_village_layouts.py [--preview /mnt/project-files/peuples/village]
"""
import argparse
import json
import plots
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "src/main/resources/Server/Nakasar/VillageLayouts"
PREFABS = Path(__file__).resolve().parent / "vanilla-prefabs-0.7.2.txt"
# Cœurs de village (place, pièces vanilla par palier, tableau/dépôt/bannière) : tools/generate_village_hearts.py.
HEARTS = Path(__file__).resolve().parent / "village-hearts.json"
# Prefabs du mod collés comme des bâtiments (enclos des peuples) : Server/Prefabs/Nakasar/Peuples/Pens.
MOD_PREFABS = ROOT / "src/main/resources/Server/Prefabs/Nakasar/Peuples/Pens"
PEN = "Nakasar/Peuples/Pens/"

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
            # Palier 0, campement : deux abris, une tour de guet, un potager (lanternes et bancs : cœur du village).
            ("Abri_Ouest", 0, OAK + "Houses_Small/Kweebec_Oak_Houses_Small_001", -20, 2, 0),
            ("Abri_Est", 0, OAK + "Houses_Small/Kweebec_Oak_Houses_Small_001", 20, 2, 2),
            ("Tour_De_Guet", 0, OAK + "Guard_Towers/Kweebec_Oak_Guard_Towers_001", 0, -18, 0),
            ("Potager", 0, OAK + "Garden/Medium/Kweebec_Oak_Garden_Medium_001", -12, -17, 0),
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
        # Chantiers (étape 5) : palier atteint -> matériaux à réunir au dépôt (objets vanilla) et durée en heures de jeu
        # (GDD : « les villageois y travaillent 1 jour de jeu »).
        "Chantiers": [
            (1, 24, [("Wood_Oak_Trunk", 24), ("Rock_Stone_Cobble", 16), ("Ingredient_Fibre", 12)]),
            (2, 24, [("Wood_Oak_Trunk", 48), ("Wood_Hardwood_Planks", 32), ("Soil_Clay_Brick", 24), ("Furniture_Kweebec_Lantern", 4)]),
            (3, 24, [("Wood_Oak_Trunk", 64), ("Plant_Leaves_Oak", 32), ("Plant_Sapling_Oak", 4), ("Ingredient_Life_Essence", 20)]),
        ],
        # Métiers (étape 5) : (id, palier, rôle du mod, animation de travail, bâtiment de travail ou None (place),
        # « front » (devant, côté place) ou « center », bâtiment du logis). Le bâtisseur part sur les chantiers.
        "Jobs": [
            ("Jardiniere", 0, "Gardener", "Potager", "center", "Abri_Ouest"),
            ("Batisseur", 0, "Builder", None, None, "Abri_Est"),
            ("Guetteur", 0, "Watcher", "Tour_De_Guet", "front", "Abri_Est"),
            ("Puisatiere", 1, "WellKeeper", "Puits", "front", "Maison_Sud_Ouest"),
            ("Eleveur", 1, "Breeder", "Enclos", "center", "Maison_Sud_Ouest"),
            ("Garde", 2, "Guard", "Tour_Est", "front", "Maison_Des_Gardes"),
            ("Soigneuse", 2, "Healer", "Grande_Maison", "front", "Grande_Maison"),
            ("Ancien", 3, "Elder", "Grand_Pere", "front", "Grand_Pere"),
            ("Jardinier_Du_Bourg", 3, "Gardener", "Grand_Potager", "center", "Grande_Maison"),
        ],
        # Tas de bois du bâtisseur sur la place, quand il n'a pas de chantier.
        "Woodpile": (-4, -3),
    },
}

TRORK = "Npc/Trork/"

# Étape 7 : le camp trork apprivoisable de la zone 1. Prefabs vanilla Npc/Trork « feuilles » seulement (les
# Encampment vanilla posent des Prefab_Spawner_Block). Les Trorks du camp sont des rôles VANILLA (« @Rôle ») : leur
# IA (Reputation_Switch, viande au sol, sommeil) lit le rang du joueur au camp ; ils n'ont pas de dialogue. Pas de
# bâtisseur : les chantiers se font sans aides.
LAYOUTS["Trork_Camp"] = {
    "People": "Trork",
    "PlazaRadius": 6,
    "Banner": (0, -5),
    "Buildings": [
        # Palier 0, campement : le feu, deux tentes, la tour de guet, le panneau d'avertissement (foyer : cœur du camp).
        ("Feu_De_Camp", 0, TRORK + "Bonfire/Trork_Bonfire_Trork_Bonfire_001", 0, 13, 0),
        ("Tente_Ouest", 0, TRORK + "Tent/Trork_Tent_001", -17, 0, 0),
        ("Tente_Est", 0, TRORK + "Tent/Trork_Tent_001", 17, 0, 2),
        ("Tour_De_Guet", 0, TRORK + "Tier_1/Watchtower/Trork_Tier_1_Watchtower_001", 0, -16, 0),
        ("Avertissement", 0, TRORK + "Warning/Trork_Warning_Trork_Warning_001", 0, 28, 0),
        # Palier 1 : le terrier, le piège, la réserve, une troisième tente.
        ("Terrier", 1, TRORK + "Burrow/Trork_Burrow_Trork_Burrow_001", -18, -18, 0),
        ("Piege", 1, TRORK + "Trap/Trork_Trap_Trork_Trap_001", 22, 22, 0),
        ("Reserve", 1, TRORK + "Tier_2/Store/Trork_Tier_2_Store_001", 18, -18, 0),
        ("Tente_Sud", 1, TRORK + "Tent/Trork_Tent_001", -18, 18, 0),
        # Bâtiments de métier, étape 3 : la fosse aux bêtes du dresseur (enclos du mod en blocs vanilla, barrière à l'est).
        ("Fosse_Aux_Betes", 1, PEN + "Trork_Pen", -32, 14, 1),
        # Palier 2 : la grande tour, l'entrepôt, le bric-à-brac.
        ("Tour_Est", 2, TRORK + "Tier_2/Watchtower/Trork_Tier_2_Watchtower_001", 34, 0, 0),
        ("Entrepot", 2, TRORK + "Warehouse/Trork_Warehouse_Trork_Warehouse_001", -34, 0, 0),
        ("Bric_A_Brac", 2, TRORK + "Misc/Large/Trork_Misc_Large_001", 12, 18, 0),
        # Palier 3 : la réserve du chef, la tour de l'ouest, le grand feu.
        ("Reserve_Du_Chef", 3, TRORK + "Tier_3/Store/Trork_Tier_3_Store_001", 0, -34, 0),
        ("Tour_Ouest", 3, TRORK + "Tier_3/Watchtower/Trork_Tier_3_Watchtower_002", -34, -22, 0),
        ("Grand_Feu", 3, TRORK + "Bonfire/Trork_Bonfire_Trork_Bonfire_002", -12, 32, 0),
    ],
    # Chantiers : viande, peaux et bois (objets vanilla), un jour de jeu.
    "Chantiers": [
        (1, 24, [("Food_Wildmeat_Raw", 16), ("Ingredient_Hide_Light", 12), ("Wood_Oak_Trunk", 24)]),
        (2, 24, [("Food_Wildmeat_Raw", 32), ("Ingredient_Hide_Medium", 16), ("Wood_Oak_Trunk", 48), ("Rock_Stone_Cobble", 24)]),
        (3, 24, [("Food_Wildmeat_Raw", 48), ("Ingredient_Hide_Heavy", 16), ("Wood_Oak_Trunk", 64), ("Ingredient_Bone_Fragment", 24)]),
    ],
    "Jobs": [
        ("Garde", 0, "@Trork_Guard", "Tour_De_Guet", "front", "Tente_Est"),
        ("Guerrier", 0, "@Trork_Warrior", "Feu_De_Camp", "front", "Tente_Ouest"),
        ("Chasseur", 1, "@Trork_Hunter", "Piege", "front", "Tente_Sud"),
        ("Dresseur", 1, "@Trork_Hunter", "Fosse_Aux_Betes", "front", "Tente_Ouest"),
        ("Cogneur", 2, "@Trork_Brawler", "Entrepot", "front", "Entrepot"),
        ("Sentinelle", 2, "@Trork_Sentry", "Tour_Est", "front", "Tour_Est"),
        ("Shaman", 3, "@Trork_Shaman", "Reserve_Du_Chef", "front", "Reserve_Du_Chef"),
    ],
    "Woodpile": (-4, -4),
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
    # Prefabs du mod (enclos des peuples, tools/generate_pens.py) : bornes lues dans le fichier.
    for f in sorted(MOD_PREFABS.glob("**/*.prefab.json")):
        blocks = json.loads(f.read_text(encoding="utf-8"))["blocks"]
        xs, ys, zs = [b["x"] for b in blocks], [b["y"] for b in blocks], [b["z"] for b in blocks]
        key = f.relative_to(MOD_PREFABS.parent.parent.parent).as_posix()[: -len(".prefab.json")]
        bounds[key] = (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))
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


def spot(building, where):
    """Poste devant un bâtiment (2 blocs hors de l'emprise, côté place) ou en son centre, en coordonnées du plan."""
    x0, x1, z0, z1 = (building["X"] + building["MinX"], building["X"] + building["MaxX"],
                      building["Z"] + building["MinZ"], building["Z"] + building["MaxZ"])
    cx, cz = (x0 + x1) // 2, (z0 + z1) // 2
    if where == "center":
        return cx, cz
    if abs(cx) >= abs(cz):
        return (x0 - 2, cz) if cx > 0 else (x1 + 2, cz)
    return (cx, z0 - 2) if cz > 0 else (cx, z1 + 2)


def load_hearts():
    return json.loads(HEARTS.read_text(encoding="utf-8")) if HEARTS.exists() else {}


def build(layout_id, spec, bounds):
    errors = []
    rects = []
    heart = load_hearts().get(layout_id)
    plaza = heart["PlazaRadius"] if heart else spec["PlazaRadius"]
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
            "MinY": b[2],
            "MaxY": b[3],
        })
    # Étape 6 des bâtiments de métier : terrains E1/E2 (tools/plots.py) et leurs projets, deux bâtiments par projet
    # (un par terrain), collés seulement par le chantier d'emplacement (Java village/Plots).
    plot_docs = []
    plot_jobs = []
    plot_dialogues = {}
    for pid, (px_, pz_, ptier) in sorted(plots.PLOTS.get(layout_id, {}).items()):
        prect = plots.plot_rect(px_, pz_)
        if overlaps(prect, plaza_rect, 1):
            errors.append(f"{layout_id}/{pid} : le terrain empiète sur la place {prect}")
        for other_id, other, _ in rects:
            if overlaps(prect, other, MARGIN):
                errors.append(f"{layout_id}/{pid} : le terrain chevauche {other_id} : {prect} / {other}")
        for other in plot_docs:
            if overlaps(prect, plots.plot_rect(other["X"], other["Z"]), MARGIN):
                errors.append(f"{layout_id}/{pid} : le terrain chevauche {other['Id']}")
        far = max(math.hypot(a, c) for a in prect[:2] for c in prect[2:])
        radius = max(radius, math.ceil(far))
        plot_docs.append({"Id": pid, "X": px_, "Z": pz_, "Size": plots.PLOT_SIZE, "Tier": ptier,
                          "Materials": [{"ItemId": i, "Quantity": q} for i, q in plots.MATERIALS[spec["People"]]],
                          "Hours": plots.PLOT_HOURS})
        for project in plots.PROJECTS.get(layout_id, []):
            prefab = project["prefab"]
            if prefab not in bounds or bounds[prefab] is None:
                errors.append(f"{layout_id}/{pid}/{project['id']} : prefab inconnu ou non mesuré {prefab}")
                continue
            b = bounds[prefab]
            r0 = footprint(b, 0, 0, project["rotation"])
            ax = px_ - (r0[0] + r0[1]) // 2
            az = pz_ - (r0[2] + r0[3]) // 2
            rect = footprint(b, ax, az, project["rotation"])
            if rect[0] < prect[0] + 1 or rect[1] > prect[1] - 1 or rect[2] < prect[2] + 1 or rect[3] > prect[3] - 1:
                errors.append(f"{layout_id}/{pid}/{project['id']} : {prefab} ne tient pas dans le terrain ({rect} / {prect})")
            bid = plots.building_id(pid, project["id"])
            buildings.append({
                "Id": bid, "Tier": ptier, "Prefab": prefab, "X": ax, "Z": az, "Rotation": project["rotation"],
                "MinX": rect[0] - ax, "MaxX": rect[1] - ax, "MinZ": rect[2] - az, "MaxZ": rect[3] - az,
                "MinY": b[2], "MaxY": b[3], "Plot": pid,
            })
            plot_jobs.append((plots.job_id(pid, project["job"]), ptier, project["kind"], bid, "front", bid))
            if project.get("dialogue"):
                plot_dialogues[plots.job_id(pid, project["job"])] = project["dialogue"]
    by_id = {b["Id"]: b for b in buildings}
    chantiers = []
    for tier, hours, materials in spec.get("Chantiers", []):
        if not any(b["Tier"] == tier for b in buildings):
            errors.append(f"{layout_id} : chantier du palier {tier} sans bâtiment")
        chantiers.append({"Tier": tier, "Hours": hours,
                          "Materials": [{"ItemId": i, "Quantity": q} for i, q in materials]})
    jobs = []
    wx, wz = heart["Woodpile"] if heart else spec.get("Woodpile", (0, 0))
    for jid, tier, kind, work, where, home in list(spec.get("Jobs", [])) + plot_jobs:
        if work is not None and work not in by_id:
            errors.append(f"{layout_id}/{jid} : bâtiment de travail inconnu {work}")
            continue
        if home not in by_id:
            errors.append(f"{layout_id}/{jid} : logis inconnu {home}")
            continue
        if work is not None and by_id[work]["Tier"] > tier:
            errors.append(f"{layout_id}/{jid} : travaille dans {work} (palier {by_id[work]['Tier']}) avant qu'il existe")
        px, pz = spot(by_id[work], where) if work else (wx, wz)
        hx, hz = spot(by_id[home], "front")
        # Étape 7 : « @Rôle » = rôle VANILLA (Trorks du camp), sans dialogue (le Java ne l'ouvre pas).
        vanilla = kind.startswith("@")
        role = kind[1:] if vanilla else f"Nakasar_Peuples_{spec['People']}_{kind}"
        jobs.append({"Id": jid, "Tier": tier, "Role": role,
                     "Dialogue": "" if vanilla else plot_dialogues.get(jid, f"{spec['People']}_{kind}"), "Building": work or "", "WorkX": px, "WorkZ": pz,
                     "Home": home, "HomeX": hx, "HomeZ": hz, "Builder": kind == "Builder"})
    bx, bz = (heart["Banner"][0], heart["Banner"][2]) if heart else spec["Banner"]
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
        "Chantiers": chantiers,
        "Jobs": jobs,
    }
    if plot_docs:
        doc["Plots"] = plot_docs
    if heart:
        doc["Heart"] = {k: heart[k] for k in ("Board", "Deposit", "DepositWide", "Banner", "Steps") if k in heart}
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
    for job in doc.get("Jobs", []):
        jx, jz = px(job["WorkX"], job["WorkZ"])
        d.ellipse([jx - 4, jz - 4, jx + 4, jz + 4], fill=(255, 255, 255))
        d.text((jx + 6, jz - 6), job["Id"], fill=(255, 240, 200))
    d.rectangle([*px(0, 0), *px(1, 1)], fill=(255, 60, 60))
    d.rectangle([*px(doc["BannerX"], doc["BannerZ"]), *px(doc["BannerX"] + 1, doc["BannerZ"] + 1)], fill=(80, 220, 80))
    legend = "Paliers : 0 jaune (campement), 1 vert (hameau), 2 bleu (village), 3 rose (bourg). Rouge : coeur ; vert vif : banniere ; points blancs : postes des metiers. Nord en haut (-Z)."
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
