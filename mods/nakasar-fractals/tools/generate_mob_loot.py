#!/usr/bin/env python3
"""Butin des mobs des fractales : objets vanilla de Hytale, selon le mob et sa fractale (Kevin, 25 octobre 2026).

    python3 mods/nakasar-fractals/tools/generate_mob_loot.py

Seuls les mobs présents de base ou apparus sur un événement (cercle atteint, palier de vie, phase) ont un butin. Les
rôles qui ne reviennent qu'en boucle (grawls du rituel, vétérans, élémentaires du feu, loups du Moussu, esprits de
Carnasse, harpies, corbeaux de la Nuée, dévoreurs, colosses) n'en ont pas. Un rôle qui apparaît des deux façons a un
butin, et le Java le retire aux exemplaires qui reviennent en boucle ({@code Spawns.noLoot}) : vagues des sceaux de la
Falaise, vagues du grand feu de Tempête de neige, araignées pondues par la Mère de couvée, tentacules qui repoussent en
phase 3 de l'Abîme de Jade.

Écrit Server/Drops/Nakasar/Fractals/Mobs/<liste>.json et ajoute DropList aux rôles déjà générés ; les générateurs de
rôles l'ajoutent aussi d'eux-mêmes (fractal_roles.write_json appelle drop_list). Chaque id est vérifié contre
tools/vanilla-item-ids-0.7.2.txt : un id inconnu ferait rejeter la liste et le rôle.
"""

import json
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
SERVER = TOOLS.parent / "src/main/resources/Server"
DROPS = SERVER / "Drops/Nakasar/Fractals/Mobs"
ROLES = SERVER / "NPC/Roles/Nakasar/Fractals"
PREFIX = "Nakasar_Fractal_"


def item(item_id, low, high=None, chance=100):
    return (item_id, low, high or low, chance)


# Rôle (sans le préfixe) -> (commentaire, objets). Un objet : (id vanilla, quantité min, max, chance en %).
LOOT = {
    # --- Falaise : cultistes en robes violettes ---------------------------------------------------
    "Cultist_Fanatic": ("Fanatique du culte (camp de départ) : chutes de lin de sa robe, parfois de l'ombretisse, du pain.", [
        item("Ingredient_Fabric_Scrap_Linen", 1, 2),
        item("Ingredient_Fabric_Scrap_Shadoweave", 1, chance=25),
        item("Food_Bread", 1, chance=15),
    ]),
    "Cultist_Chanter": ("Incantateur du culte (camp de départ, renforts de l'Archidevin) : soie de sa robe, essence du "
                        "Vide de ses incantations, pétales violets.", [
        item("Ingredient_Fabric_Scrap_Silk", 1, 2),
        item("Ingredient_Void_Essence", 1, chance=30),
        item("Plant_Petals_Purple", 1, 2, chance=30),
    ]),
    "Archdiviner": ("L'Archidevin : rouleaux d'ombretisse de sa cape, essence du Vide, cristal violet, pierre de Vide.", [
        item("Ingredient_Bolt_Shadoweave", 2, 3),
        item("Ingredient_Void_Essence", 3, 5),
        item("Ingredient_Crystal_Purple", 1, 2, chance=60),
        item("Rock_Gem_Voidstone", 1, chance=35),
    ]),
    # --- Volcanique et Ressac silencieux : bêtes des cavernes ---------------------------------------
    "Cave_Bat": ("Chauve-souris (mine du Volcanique, grotte du Ressac silencieux) : peau souple, éclat d'os.", [
        item("Ingredient_Hide_Soft", 1, chance=50),
        item("Ingredient_Bone_Fragment", 1, chance=30),
    ]),
    "Champion_Shaman": ("Champion chaman des grawls : essence de feu, cuir lourd, plumes rouges de sa parure, or de la "
                        "falaise.", [
        item("Ingredient_Fire_Essence", 2, 4),
        item("Ingredient_Hide_Heavy", 2, 3),
        item("Ingredient_Feathers_Red", 2, 4, chance=70),
        item("Ore_Gold", 1, 2, chance=40),
    ]),
    "Imbued_Shaman": ("Le Chamane imprégné : essence de feu, rouleau de tisse-cendre, charbon du volcan, rubis.", [
        item("Ingredient_Fire_Essence", 4, 6),
        item("Ingredient_Bolt_Cindercloth", 1, 2),
        item("Ingredient_Charcoal", 3, 6),
        item("Rock_Gem_Ruby", 1, chance=40),
    ]),
    "Ember_Larva": ("Larve de braise (boucliers du Chamane imprégné) : essence de feu, charbon.", [
        item("Ingredient_Fire_Essence", 1, chance=60),
        item("Ingredient_Charcoal", 1, 2, chance=50),
    ]),
    # --- Tempête de neige : Svanir et bêtes du froid -------------------------------------------------
    "Frost_Cultist": ("Fils de Svanir (groupes de la forêt) : laine de sa cape, peau de bête.", [
        item("Ingredient_Fabric_Scrap_Wool", 1, 2),
        item("Ingredient_Hide_Medium", 1, chance=30),
    ]),
    "Frost_Caster": ("Incantateur de Svanir (groupes de la forêt) : essence de glace, laine, graine de givre.", [
        item("Ingredient_Ice_Essence", 1, 2),
        item("Ingredient_Fabric_Scrap_Wool", 1),
        item("Plant_Seeds_Ice", 1, chance=10),
    ]),
    "Frost_Wolf": ("Loup des neiges (groupes de la forêt) : peau, viande sauvage, os.", [
        item("Ingredient_Hide_Light", 1, 2, chance=80),
        item("Food_Wildmeat_Raw", 1, chance=60),
        item("Ingredient_Bone_Fragment", 1, chance=30),
    ]),
    "Elemental_Source": ("La Source élémentaire : essence de glace, cristal cyan, saphir.", [
        item("Ingredient_Ice_Essence", 4, 6),
        item("Ingredient_Crystal_Cyan", 1, 2, chance=70),
        item("Rock_Gem_Sapphire", 1, chance=30),
    ]),
    "Shaman_Bear": ("Le Chaman légendaire, vaincu sous sa forme d'ours : cuir lourd, essence de glace, laine, saphir.", [
        item("Ingredient_Hide_Heavy", 3, 4),
        item("Ingredient_Ice_Essence", 3, 5),
        item("Ingredient_Bolt_Wool", 1, 2, chance=70),
        item("Rock_Gem_Sapphire", 1, chance=35),
    ]),
    "Corrupted_Crystal": ("Cristal de glace corrompu (grotte du Chaman) : cristal cyan, essence de glace.", [
        item("Ingredient_Crystal_Cyan", 1, chance=60),
        item("Ingredient_Ice_Essence", 1, chance=40),
    ]),
    "Ice_Effigy": ("Effigie de glace (balcon du Chaman) : gravats de glace, essence de glace.", [
        item("Rubble_Ice", 2, 3),
        item("Ingredient_Ice_Essence", 1, 2),
    ]),
    # --- Ressac silencieux ---------------------------------------------------------------------------
    "Brood_Mother": ("Mère de couvée des cavernes : chitine, poches de venin, soie de sa toile.", [
        item("Ingredient_Chitin_Sturdy", 2, 3),
        item("Ingredient_Sac_Venom", 1, 2),
        item("Ingredient_Fabric_Scrap_Silk", 2, 4),
    ]),
    "Cave_Spiderling": ("Araignée des cavernes (cercle de la Mère de couvée, pas celles qu'elle pond) : soie, chitine.", [
        item("Ingredient_Fabric_Scrap_Silk", 1, chance=50),
        item("Ingredient_Chitin_Sturdy", 1, chance=20),
    ]),
    "Naga_Raider": ("Pillard naga : peau écailleuse, poisson, essence d'eau.", [
        item("Ingredient_Hide_Scaled", 1, chance=60),
        item("Food_Fish_Raw", 1, chance=40),
        item("Ingredient_Water_Essence", 1, chance=20),
    ]),
    "Naga_Stormcaller": ("Mande-tempête naga : essence de foudre, peau écailleuse.", [
        item("Ingredient_Lightning_Essence", 1, 2),
        item("Ingredient_Hide_Scaled", 1, chance=40),
    ]),
    "Naga_Venomcaller": ("Mande-venin naga : poches de venin, fruit empoisonné.", [
        item("Ingredient_Sac_Venom", 1, 2),
        item("Plant_Fruit_Poison", 1, chance=30),
    ]),
    "Naga_Wavecaller": ("Mande-vague naga corrompu : essence d'eau, peau écailleuse, beau poisson.", [
        item("Ingredient_Water_Essence", 2, 3),
        item("Ingredient_Hide_Scaled", 2),
        item("Food_Fish_Raw_Rare", 1, chance=40),
    ]),
    "Luxon_Sailor": ("Marin luxon corrompu (épave) : coton de sa tenue, poudre, flèches de fer, sangle.", [
        item("Ingredient_Fabric_Scrap_Cotton", 1, 2),
        item("Ingredient_Powder_Boom", 1, chance=30),
        item("Weapon_Arrow_Iron", 2, 4, chance=30),
        item("Ingredient_Strap_Leather", 1, chance=20),
    ]),
    "First_Mate_Dolus": ("Le second Dolus : rouleaux de coton, poudre de la cale, argent du bord, émeraude (jade).", [
        item("Ingredient_Bolt_Cotton", 2),
        item("Ingredient_Powder_Boom", 2, 4),
        item("Ingredient_Bar_Silver", 1, 2, chance=50),
        item("Rock_Gem_Emerald", 1, chance=30),
    ]),
    "Kanaxai": ("Kanaxai : essence du Vide, ombretisse, pierre de Vide, rarement un cœur du Vide.", [
        item("Ingredient_Void_Essence", 4, 6),
        item("Ingredient_Bolt_Shadoweave", 2, 3),
        item("Rock_Gem_Voidstone", 1, chance=50),
        item("Ingredient_Voidheart", 1, chance=10),
    ]),
    # --- Océan solide --------------------------------------------------------------------------------
    "Irukandji": ("Irukandji (chemin de jade, arène) : essence d'eau, de foudre (piqûre), cristal vert.", [
        item("Ingredient_Water_Essence", 1, chance=50),
        item("Ingredient_Lightning_Essence", 1, chance=20),
        item("Ingredient_Crystal_Green", 1, chance=15),
    ]),
    "Jade_Maw": ("L'Abîme de Jade : cristal vert, émeraudes, essence d'eau, poisson des grands fonds.", [
        item("Ingredient_Crystal_Green", 3, 5),
        item("Ingredient_Water_Essence", 3, 5),
        item("Rock_Gem_Emerald", 1, 2, chance=70),
        item("Food_Fish_Raw_Epic", 1, chance=25),
    ]),
    "Jade_Tentacle": ("Tentacule de l'Abîme (sauf ceux qui repoussent en phase 3) : cristal vert, essence d'eau.", [
        item("Ingredient_Crystal_Green", 1, chance=50),
        item("Ingredient_Water_Essence", 1, chance=40),
    ]),
    # --- Marais --------------------------------------------------------------------------------------
    "Mossman_Beast": ("Le Moussu, vaincu sous sa forme sauvage : cuir lourd, mousse, essence de vie, bois de saule.", [
        item("Ingredient_Hide_Heavy", 2, 3),
        item("Plant_Moss_Green", 3, 5),
        item("Ingredient_Life_Essence", 2, 4),
        item("Wood_Sallow_Trunk", 2, 4, chance=60),
    ]),
    "Bloomhunger": ("Carnasse : essence de vie, bois empoisonné, sève, fleurs empoisonnées, graines de saule.", [
        item("Ingredient_Life_Essence", 4, 6),
        item("Wood_Poisoned_Trunk", 3, 5),
        item("Ingredient_Tree_Sap", 2, 3),
        item("Plant_Flower_Common_Poisoned", 2, 3, chance=70),
        item("Plant_Seeds_Sallow", 1, 2, chance=60),
    ]),
    "Poison_Bloom": ("Fleur de poison (après les assauts de Carnasse) : fleur empoisonnée, poche de venin.", [
        item("Plant_Flower_Bushy_Poisoned", 1, 2),
        item("Ingredient_Sac_Venom", 1, chance=25),
    ]),
    # --- Inclassable ---------------------------------------------------------------------------------
    "Prison_Generator": ("Générateur de la prison : fer de sa carcasse, essence de foudre, cristal bleu de son cœur.", [
        item("Ingredient_Bar_Iron", 1, 2),
        item("Ingredient_Lightning_Essence", 1, 2, chance=70),
        item("Ingredient_Crystal_Blue", 1, chance=40),
    ]),
    "Rabid_Rabbit": ("Lapin enragé : peau souple, viande, carottes.", [
        item("Ingredient_Hide_Soft", 2),
        item("Food_Wildmeat_Raw", 1, 2),
        item("Plant_Crop_Carrot_Item", 2, 4, chance=60),
    ]),
    "Saboteur": ("Saboteur : ses bombes, de la poudre, chutes de lin de son manteau.", [
        item("Weapon_Bomb", 2, 4),
        item("Ingredient_Powder_Boom", 2, 3),
        item("Ingredient_Fabric_Scrap_Linen", 1, 2, chance=50),
    ]),
    "Fire_Shaman": ("Chaman du feu : essence de feu, chutes de tisse-cendre, charbon.", [
        item("Ingredient_Fire_Essence", 2, 3),
        item("Ingredient_Fabric_Scrap_Cindercloth", 1, 2),
        item("Ingredient_Charcoal", 2, 3, chance=50),
    ]),
    "Ettin": ("Ettin : cuir lourd, os, viande de bœuf.", [
        item("Ingredient_Hide_Heavy", 2, 3),
        item("Ingredient_Bone_Fragment", 2, 4),
        item("Food_Beef_Raw", 1, 2, chance=50),
    ]),
    "Old_Tom": ("Vieux Tom : fer, rivets, charbon de sa chaudière, essence de feu.", [
        item("Ingredient_Bar_Iron", 3, 5),
        item("Ingredient_Stud_Iron", 3, 5),
        item("Ingredient_Charcoal", 3, 5),
        item("Ingredient_Fire_Essence", 1, 2, chance=50),
    ]),
    "Crystal_Golem": ("Golem de cristal de l'Asura : cristal bleu, essence de foudre.", [
        item("Ingredient_Crystal_Blue", 1, 2),
        item("Ingredient_Lightning_Essence", 1, chance=40),
    ]),
}


def vanilla_items():
    lines = (TOOLS / "vanilla-item-ids-0.7.2.txt").read_text(encoding="utf-8").splitlines()
    return {line.strip() for line in lines if line.strip() and not line.startswith("#")}


def single(item_id, low, high):
    return {"Type": "Single", "Item": {"ItemId": item_id, "QuantityMin": low, "QuantityMax": high}}


def drop_doc(comment, items):
    containers = []
    for item_id, low, high, chance in items:
        entry = single(item_id, low, high)
        if chance >= 100:
            containers.append(entry)
        else:
            entry["Weight"] = chance
            containers.append({"Type": "Choice", "Containers": [entry, {"Type": "Empty", "Weight": 100 - chance}]})
    return {"$Comment": comment + " Généré par tools/generate_mob_loot.py.",
            "Container": {"Type": "Multiple", "Containers": containers}}


def drop_list(role_id):
    """Id de la liste de butin du rôle `role_id`, ou None s'il n'en a pas."""
    key = role_id[len(PREFIX):] if role_id.startswith(PREFIX) else role_id
    return f"{PREFIX}Loot_{key}" if key in LOOT else None


def with_drop_list(role_id, doc):
    """Le rôle `doc` avec sa DropList (placée après MaxHealth), ou tel quel s'il n'a pas de butin."""
    drop = drop_list(role_id)
    if drop is None:
        return doc
    out = {}
    for k, v in doc.items():
        if k == "DropList":
            continue
        out[k] = v
        if k == "MaxHealth":
            out["DropList"] = drop
    out.setdefault("DropList", drop)
    return out


def main():
    known = vanilla_items()
    unknown = sorted({i[0] for _, items in LOOT.values() for i in items} - known)
    assert not unknown, f"ids vanilla inconnus : {unknown}"
    for key, (_, items) in LOOT.items():
        # Au moins un objet sûr : une liste faite seulement de tirages peut ne rien donner, mais reste valide.
        assert (ROLES / f"{PREFIX}{key}.json").exists(), f"rôle absent : {key}"
    DROPS.mkdir(parents=True, exist_ok=True)
    for old in DROPS.glob("*.json"):
        old.unlink()
    for key, (comment, items) in LOOT.items():
        path = DROPS / f"{drop_list(PREFIX + key)}.json"
        path.write_text(json.dumps(drop_doc(comment, items), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for path in sorted(ROLES.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        ours = str(doc.get("DropList", "")).startswith(PREFIX + "Loot_")
        new = with_drop_list(path.stem, {k: v for k, v in doc.items() if not (k == "DropList" and ours)})
        if new != doc:
            path.write_text(json.dumps(new, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(LOOT)} listes de butin écrites dans {DROPS.relative_to(TOOLS.parent)}")


if __name__ == "__main__":
    main()
