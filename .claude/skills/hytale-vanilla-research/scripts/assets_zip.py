#!/usr/bin/env python3
"""Fouille de l'Assets.zip vanilla de Hytale (3,9 Go) sans le décompresser.

Se lance là où se trouve le zip : sur le PC de Kevin via device_bash (dossier du jeu connecté), en passant
le script par heredoc :

    python3 - ls 'Server/NPC/Roles/**/Skeleton*' <<'EOF'
    <contenu de ce fichier>
    EOF

ou en local si un Assets.zip a été copié dans le conteneur. Le zip est cherché dans cet ordre : --zip,
$HYTALE_ASSETS_ZIP, puis sous $HOME/mnt/*/ (Assets.zip à une profondeur ≤ 3).

Commandes :
    ls GLOB                      chemins qui correspondent (** = n'importe quels dossiers), avec la taille
    cat CHEMIN [--max N]         contenu texte d'un fichier (JSON réindenté si possible)
    grep REGEX [--glob GLOB]     lignes qui correspondent, fichiers texte seulement (json, lang, txt, ui…)
    refs ID [--glob GLOB]        fichiers qui citent un id exact (entre guillemets) : qui utilise quoi
    keys GLOB                    union des clés JSON de premier niveau des fichiers, avec leur fréquence :
                                 le « schéma réel » d'une famille d'assets
    extract GLOB DEST            copie les fichiers vers DEST (garde l'arborescence), pour les ramener avec
                                 device_stage_files (DEST doit être DANS un dossier connecté)

Sorties volontairement courtes (--limit, défaut 200 lignes) : on ramène des résumés, pas des Mo de JSON.
"""
import argparse
import fnmatch
import glob
import json
import os
import re
import sys
import zipfile
from collections import Counter

TEXT_EXT = (".json", ".lang", ".txt", ".ui", ".md", ".particlesystem", ".particlespawner", ".blockymodel",
            ".blockyanim", ".prefab.json", ".csv", ".xml", ".properties")


def find_zip(explicit):
    for cand in [explicit, os.environ.get("HYTALE_ASSETS_ZIP")]:
        if cand and os.path.isfile(cand):
            return cand
    home = os.path.expanduser("~")
    for depth in ("", "*/", "*/*/", "*/*/*/"):
        hits = glob.glob(os.path.join(home, "mnt", "*", depth + "Assets.zip"))
        if hits:
            return hits[0]
    sys.exit("Assets.zip introuvable : passer --zip CHEMIN ou connecter le dossier du jeu "
             "(…\\Hytale\\install\\release\\package\\game\\latest).")


def match(name, pattern):
    rx = re.escape(pattern).replace(r"\*\*/", "(?:.*/)?").replace(r"\*\*", ".*").replace(r"\*", "[^/]*").replace(r"\?", ".")
    return re.fullmatch(rx, name) is not None


def text_of(z, name):
    data = z.read(name)
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["ls", "cat", "grep", "refs", "keys", "extract"])
    ap.add_argument("arg")
    ap.add_argument("dest", nargs="?")
    ap.add_argument("--zip")
    ap.add_argument("--glob", default="**")
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--max", type=int, default=20000, help="cat : caractères max")
    a = ap.parse_args()
    z = zipfile.ZipFile(find_zip(a.zip))
    infos = [i for i in z.infolist() if not i.is_dir()]
    out = []

    if a.cmd == "ls":
        for i in infos:
            if match(i.filename, a.arg):
                out.append(f"{i.file_size:>9}  {i.filename}")
    elif a.cmd == "cat":
        t = text_of(z, a.arg)
        if t is None:
            sys.exit("fichier binaire")
        try:
            t = json.dumps(json.loads(t), indent=1, ensure_ascii=False)
        except ValueError:
            pass
        sys.stdout.write(t[: a.max] + ("\n… (coupé)\n" if len(t) > a.max else "\n"))
        return
    elif a.cmd in ("grep", "refs"):
        rx = re.compile(a.arg if a.cmd == "grep" else '"' + re.escape(a.arg) + '"')
        for i in infos:
            if not i.filename.lower().endswith(TEXT_EXT) or not match(i.filename, a.glob):
                continue
            t = text_of(z, i.filename)
            if t is None:
                continue
            for n, line in enumerate(t.splitlines(), 1):
                if rx.search(line):
                    out.append(f"{i.filename}:{n}: {line.strip()[:200]}")
                    if a.cmd == "refs":
                        break
            if len(out) >= a.limit:
                break
    elif a.cmd == "keys":
        c = Counter()
        n = 0
        for i in infos:
            if match(i.filename, a.arg) and i.filename.endswith(".json"):
                try:
                    d = json.loads(text_of(z, i.filename) or "")
                except ValueError:
                    continue
                if isinstance(d, dict):
                    n += 1
                    c.update(d.keys())
        out.append(f"{n} fichiers")
        out += [f"{v:>5}  {k}" for k, v in c.most_common()]
    elif a.cmd == "extract":
        if not a.dest:
            sys.exit("extract GLOB DEST")
        for i in infos:
            if match(i.filename, a.arg):
                target = os.path.join(a.dest, i.filename)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, "wb") as f:
                    f.write(z.read(i.filename))
                out.append(target)

    for line in out[: a.limit]:
        print(line)
    if len(out) > a.limit:
        print(f"… {len(out) - a.limit} de plus (--limit)")


if __name__ == "__main__":
    main()
