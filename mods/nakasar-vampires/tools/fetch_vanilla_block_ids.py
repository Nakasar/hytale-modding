#!/usr/bin/env python3
"""Reconstruit tools/vanilla-block-ids-0.7.2.txt : les ids de blocs vanilla et leurs états.

    python3 mods/nakasar-vampires/tools/fetch_vanilla_block_ids.py [dossier-cache]

Source : les fichiers Server/Item/Items/**.json du jeu publiés par hytale.isaacguru.com (liste des
objets, puis le JSON de chacun). Un objet est un bloc s'il a un BlockType, lui-même ou via son
Parent. Chaque état (BlockType.State.Definitions) donne un bloc de plus, dont la clé est générée par
StateData du serveur : « *<objet>_State_Definitions_<état> ».

Les JSON téléchargés sont gardés dans le dossier cache (par défaut build/vanilla-items) : relancer le
script ne retélécharge que ce qui manque. Utilise curl (le site refuse le client HTTP de Python).
"""

import concurrent.futures
import json
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

SITE = "https://hytale.isaacguru.com"
TOOLS = Path(__file__).resolve().parent
OUT = TOOLS / "vanilla-block-ids-0.7.2.txt"


def fetch(url, data=None):
    cmd = ["curl", "-sSL", "-m", "60", "--retry", "3", url]
    if data:
        cmd[1:1] = ["-X", "POST", "-d", data]
    return subprocess.run(cmd, capture_output=True, check=True).stdout.decode("utf-8", "replace")


def item(cache, item_id):
    path = cache / f"{item_id}.json"
    if path.exists():
        cached = json.loads(path.read_text(encoding="utf-8"))
        if cached is not None:
            return cached
    doc = None
    try:
        page = fetch(f"{SITE}/wiki/hytale/item/{item_id}")
        match = re.search(r'(/core/data/hytale/Items/[^"]+\.json)', page)
        if match:
            doc = json.loads(fetch(SITE + urllib.parse.quote(match.group(1))))
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        pass
    path.write_text(json.dumps(doc), encoding="utf-8")
    return doc


def main():
    cache = Path(sys.argv[1]) if len(sys.argv) > 1 else TOOLS.parent / "build" / "vanilla-items"
    cache.mkdir(parents=True, exist_ok=True)
    ids = sorted({i["id"] for i in json.loads(fetch(f"{SITE}/core/includes/ajax/get-php-data.php", "type=get-all-items&mod=hytale"))})
    with concurrent.futures.ThreadPoolExecutor(16) as pool:
        docs = dict(zip(ids, pool.map(lambda i: item(cache, i), ids)))

    def block_type(item_id, depth=0):
        if item_id not in docs:  # parent absent de la liste (gabarit)
            docs[item_id] = item(cache, item_id)
        doc = docs[item_id]
        if not doc:
            return None
        if doc.get("BlockType") is not None:
            parent = doc.get("Parent")
            inherited = block_type(parent, depth + 1) if parent and depth < 8 else None
            return {**(inherited or {}), **doc["BlockType"]}
        parent = doc.get("Parent")
        return block_type(parent, depth + 1) if parent and depth < 8 else None

    lines = []
    missing = 0
    for item_id in ids:
        if docs[item_id] is None:
            missing += 1
            continue
        bt = block_type(item_id)
        if bt is None:
            continue
        lines.append(item_id)
        for state in ((bt.get("State") or {}).get("Definitions") or {}):
            lines.append(f"*{item_id}_State_Definitions_{state}")
    header = [
        "# Ids de blocs vanilla (objets avec un BlockType) et leurs états, pour validateAssets.",
        "# Généré par tools/fetch_vanilla_block_ids.py depuis les fichiers du jeu publiés par hytale.isaacguru.com.",
        "# Un id absent ici devient le bloc « Unknown » (damier rose et noir) dans un prefab : ajouter à la main",
        "# un bloc récent qui manquerait.",
    ]
    OUT.write_text("\n".join(header + lines) + "\n", encoding="utf-8")
    print(f"{len(lines)} blocs et états écrits dans {OUT.name} ({missing} objets sans fichier JSON)")


if __name__ == "__main__":
    main()
