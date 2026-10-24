#!/usr/bin/env python3
"""Index vivant du code des mods : classes Java, interactions JSON, générateurs Python, copies entre mods.

    python3 .claude/skills/hytale-mod-reuse/scripts/index_code.py [--mod vampires|fractals] [--grep MOT] [--out FICHIER]

Lit le dépôt tel qu'il est (aucune liste figée) :
  - chaque classe Java avec la première phrase de sa Javadoc, groupée par paquet ;
  - les types d'interaction `"Type": "Nakasar_…"` écrits en Java (utilisables depuis le JSON) ;
  - chaque outil Python de `tools/` avec la première phrase de sa docstring et ses fonctions publiques ;
  - les fichiers de même nom présents dans plusieurs mods (copies à garder synchronisées à la main).

`--grep MOT` ne garde que les entrées dont le chemin, le nom ou la description contient MOT (sans casse) :
c'est le moyen rapide de savoir si « télégraphe », « boss bar », « ramasser », « cage »… existent déjà.
"""
import argparse
import ast
import re
import sys
from collections import defaultdict
from pathlib import Path

def repo_root():
    """Dépôt du dossier courant (un worktree a son propre code), sinon celui du script."""
    import subprocess
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
        return Path(out.stdout.strip())
    except Exception:  # noqa: BLE001
        return Path(__file__).resolve().parents[4]


ROOT = repo_root()
MODS = ROOT / "mods"


def first_sentence(text, limit=220):
    text = re.sub(r"\{@(?:code|link|value|linkplain) ([^}]*)\}", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    m = re.search(r"(.+?[.!?])(\s|$)", text)
    s = m.group(1) if m else text
    return s if len(s) <= limit else s[: limit - 1] + "…"


def javadoc(src):
    m = re.search(r"/\*\*(.*?)\*/\s*(?:@\w+(?:\([^)]*\))?\s*)*(?:public\s+)?(?:final\s+|abstract\s+)*(?:class|record|enum|interface)\s", src, re.S)
    if not m:
        return ""
    body = "\n".join(re.sub(r"^\s*\* ?", "", l) for l in m.group(1).splitlines())
    return first_sentence(body)


def java_entries(mod_dir):
    out = []
    base = mod_dir / "src/main/java"
    for f in sorted(base.rglob("*.java")):
        src = f.read_text(encoding="utf-8", errors="replace")
        rel = f.relative_to(base)
        pkg = ".".join(rel.parts[3:-1]) or "(racine)"
        types = re.findall(r'"Type": "(Nakasar_[A-Za-z0-9_]+)"', src)
        out.append({"pkg": pkg, "name": f.stem, "path": f.relative_to(ROOT).as_posix(), "lines": src.count("\n"),
                    "doc": javadoc(src), "types": types})
    return out


def py_entries(mod_dir):
    out = []
    for f in sorted((mod_dir / "tools").glob("*.py")):
        src = f.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        doc = first_sentence(ast.get_docstring(tree) or "")
        funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")]
        out.append({"name": f.stem, "path": f.relative_to(ROOT).as_posix(), "lines": src.count("\n"), "doc": doc,
                    "funcs": funcs})
    return out


def keep(entry, word):
    if not word:
        return True
    hay = " ".join(str(v) for v in entry.values()).lower()
    return word.lower() in hay


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", help="vampires, fractals… (défaut : tous)")
    ap.add_argument("--grep", help="filtre texte")
    ap.add_argument("--out", help="écrit le markdown dans ce fichier")
    a = ap.parse_args()

    mods = sorted(p for p in MODS.iterdir() if p.is_dir() and (p / "build.gradle.kts").exists())
    if a.mod:
        mods = [m for m in mods if a.mod in m.name]
    lines = []
    names = defaultdict(list)
    for mod in mods:
        lines.append(f"# {mod.name}\n")
        java = java_entries(mod)
        for e in java:
            names[e["name"]].append(mod.name)
        by_pkg = defaultdict(list)
        for e in java:
            if keep(e, a.grep):
                by_pkg[e["pkg"]].append(e)
        if by_pkg:
            lines.append("## Java\n")
        for pkg in sorted(by_pkg):
            lines.append(f"### {pkg}")
            for e in by_pkg[pkg]:
                t = f" — types JSON : {', '.join(e['types'])}" if e["types"] else ""
                lines.append(f"- `{e['path']}` ({e['lines']} l.) : {e['doc'] or '(pas de Javadoc)'}{t}")
            lines.append("")
        py = [e for e in py_entries(mod) if keep(e, a.grep)]
        if py:
            lines.append("## Outils Python (tools/)\n")
            for e in py:
                fn = ", ".join(e["funcs"][:40]) + (" …" if len(e["funcs"]) > 40 else "")
                lines.append(f"- `{e['path']}` ({e['lines']} l.) : {e['doc'] or '(pas de docstring)'}")
                if fn:
                    lines.append(f"  - fonctions : {fn}")
            lines.append("")
    dup = {n: m for n, m in names.items() if len(set(m)) > 1}
    if dup and not a.grep:
        lines.append("# Classes de même nom dans plusieurs mods (copies : corriger toutes les copies)\n")
        for n in sorted(dup):
            lines.append(f"- {n} : {', '.join(sorted(set(dup[n])))}")
    text = "\n".join(lines) + "\n"
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"écrit {a.out} ({len(lines)} lignes)")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
