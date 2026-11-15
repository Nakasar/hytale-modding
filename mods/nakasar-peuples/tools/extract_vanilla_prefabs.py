#!/usr/bin/env python3
"""Extrait d'Assets.zip les prefabs vanilla des cœurs de village (generate_village_hearts.py --list) et, avec
--palette, les couleurs moyennes des blocs pour les aperçus. À lancer là où se trouve Assets.zip (PC du jeu).

    python3 generate_village_hearts.py --list > pieces.txt
    python3 extract_vanilla_prefabs.py Assets.zip pieces.txt vanilla-heart-prefabs.json [--palette pal.json]
"""
import argparse
import io
import json
import zipfile


def prefabs(z, names):
    out = {}
    for p in names:
        d = json.loads(z.read(f"Server/Prefabs/{p}.prefab.json"))
        out[p] = {
            "anchor": [d["anchorX"], d["anchorY"], d["anchorZ"]],
            "blocks": [[b["x"], b["y"], b["z"], b["name"], b.get("rotation", 0)] for b in d["blocks"]
                       if b["name"] != "Empty" and not b.get("filler")],
            "fluids": [[b["x"], b["y"], b["z"], b["name"]] for b in d.get("fluids", [])],
        }
    return out


def palette(z):
    from PIL import Image
    names = set(z.namelist())
    items = {n.split("/")[-1][:-5]: n for n in names if n.startswith("Server/Item/Items/") and n.endswith(".json")}
    cache = {}

    def load(k):
        if k not in cache:
            try:
                cache[k] = json.loads(z.read(items[k]).decode("utf-8", "replace"))
            except Exception:
                cache[k] = None
        return cache[k]

    def get(k, key, depth=0):
        j = load(k) if k in items else None
        if j is None or depth > 8:
            return None
        bt = j.get("BlockType") or {}
        if bt.get(key) is not None:
            return bt[key]
        return get(j.get("Parent"), key, depth + 1) if j.get("Parent") else None

    def avg(path, accent=False):
        path = "Common/" + path
        if path not in names:
            return None
        px = [p for p in Image.open(io.BytesIO(z.read(path))).convert("RGBA").getdata() if p[3] > 128]
        if not px:
            return None
        if accent:
            px = sorted(px, key=lambda p: min(p[:3]) - max(p[:3]))[:max(1, len(px) // 5)]
        return [sum(p[i] for p in px) // len(px) for i in range(3)]

    def bbox(model):
        p = "Common/" + model
        if p not in names:
            return None
        m = json.loads(z.read(p))
        lo, hi = [1e9] * 3, [-1e9] * 3

        def walk(n, o):
            pos = n.get("position", {"x": 0, "y": 0, "z": 0})
            c = [o[0] + pos["x"], o[1] + pos["y"], o[2] + pos["z"]]
            s = n.get("shape", {})
            if s.get("type") == "box" and s.get("visible", True):
                off, size = s.get("offset", {"x": 0, "y": 0, "z": 0}), s["settings"]["size"]
                st = s.get("stretch", {"x": 1, "y": 1, "z": 1})
                for i, a in enumerate("xyz"):
                    half = abs(size[a] * st[a]) / 2
                    lo[i] = min(lo[i], c[i] + off[a] - half)
                    hi[i] = max(hi[i], c[i] + off[a] + half)
            for ch in n.get("children", []):
                walk(ch, c)

        for n in m.get("nodes", []):
            walk(n, [0, 0, 0])
        return [round(v, 1) for v in lo + hi] if lo[0] < 1e8 else None

    out = {}
    for k in sorted(items):
        if not get(k, "DrawType") and not get(k, "Textures") and not get(k, "CustomModel"):
            continue
        e = {"dt": get(k, "DrawType")}
        tex = get(k, "Textures")
        if tex:
            t = tex[0]
            up = t.get("Up") or t.get("UpDown") or t.get("All") or t.get("Sides")
            sd = t.get("Sides") or t.get("All") or up
            e["top"], e["side"] = avg(up) if up else None, avg(sd) if sd else None
        cm, cmt = get(k, "CustomModel"), get(k, "CustomModelTexture")
        if cm:
            e["model"], e["bbox"] = 1, bbox(cm)
            if cmt:
                e["mtex"], e["macc"] = avg(cmt[0]["Texture"]), avg(cmt[0]["Texture"], True)
        tint = get(k, "TintUp") or get(k, "Tint")
        if tint:
            h = (tint[0] if isinstance(tint, list) else tint).lstrip("#")
            e["tint"] = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
        if get(k, "Light"):
            e["light"] = 1
        out[k] = e
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("assets")
    ap.add_argument("pieces")
    ap.add_argument("out")
    ap.add_argument("--palette")
    a = ap.parse_args()
    z = zipfile.ZipFile(a.assets)
    names = [l.strip() for l in open(a.pieces, encoding="utf-8") if l.strip()]
    json.dump({"prefabs": prefabs(z, names)}, open(a.out, "w", encoding="utf-8"))
    if a.palette:
        json.dump(palette(z), open(a.palette, "w", encoding="utf-8"))


if __name__ == "__main__":
    main()
