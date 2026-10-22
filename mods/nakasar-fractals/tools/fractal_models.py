"""Petit moteur de modèles d'objets en boîtes, copié du mod Vampires (tools/generate_assets.py et generate_altar.py,
pas de bibliothèque commune) : atlas de textures, fichier .blockymodel et rendu logiciel des icônes.

Une pièce est un tuple (nom, centre, taille, rotation Y en degrés, peintre, ombrage). Le peintre reçoit
(rng, largeur, hauteur, face) et rend une image RGBA ; l'ombrage est "flat" ou "fullbright" (lueur).
Repère : 1 texel par unité, origine au centre du bas de l'objet, face "front" vers +Z.
"""
import json
import math
import random

from PIL import Image, ImageFilter

FACES = ("top", "bottom", "front", "back", "left", "right")


def shade(c, f):
    return tuple(max(0, min(255, int(round(v * f)))) for v in c)


def mix(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def soft_noise(rng, w, h, scale=6, amp=0.12):
    """Bruit basse fréquence flouté : variations douces, pas de grain."""
    gw, gh = max(2, w // scale + 2), max(2, h // scale + 2)
    small = Image.new("L", (gw, gh))
    small.putdata([rng.randint(0, 255) for _ in range(gw * gh)])
    big = small.resize((w + scale * 2, h + scale * 2), Image.BICUBIC)
    big = big.filter(ImageFilter.GaussianBlur(scale / 2)).crop((scale, scale, scale + w, scale + h))
    px = big.load()
    return [[1 + amp * ((px[x, y] - 128) / 128) for x in range(w)] for y in range(h)]


def smooth(base, top=None):
    """Matière lisse : dessus éclairé, côtés plus sombres vers le bas, arête claire."""
    def paint(rng, w, h, face):
        img = Image.new("RGBA", (w, h))
        px = img.load()
        noise = soft_noise(rng, w, h)
        for y in range(h):
            for x in range(w):
                if face == "bottom":
                    f = 0.62
                elif face == "top":
                    f = 1.2 if min(x, y, w - 1 - x, h - 1 - y) == 0 else 1.08
                else:
                    f = 1.0 - 0.28 * y / max(1, h - 1)
                    if y == 0:
                        f = 1.18
                f *= noise[y][x]
                c = top if (face == "top" and top) else base
                px[x, y] = shade(c, f) + (255,)
        return img
    return paint


def crystal(base, light):
    """Facette de cristal : dégradé diagonal du clair au foncé, reflet en coin."""
    def paint(rng, w, h, face):
        img = Image.new("RGBA", (w, h))
        px = img.load()
        for y in range(h):
            for x in range(w):
                t = (x / max(1, w - 1) + y / max(1, h - 1)) / 2
                c = mix(light, base, t)
                if x <= 1 and y <= 1:
                    c = shade(light, 1.2)
                px[x, y] = c + (255,)
        return img
    return paint


def flat(color):
    def paint(rng, w, h, face):
        return Image.new("RGBA", (w, h), shade(color, 0.75 if face == "bottom" else 1.0) + (255,))
    return paint


def face_size(size, face):
    sx, sy, sz = size
    if face in ("top", "bottom"):
        return sx, sz
    if face in ("front", "back"):
        return sx, sy
    return sz, sy


def build_atlas(parts, seed, tex_w=64):
    rng = random.Random(seed)
    regions = []
    for pi, (name, c, size, rot, paint, _) in enumerate(parts):
        for g in (("top",), ("bottom",), ("front", "back"), ("left", "right")):
            w, h = (max(1, math.ceil(v)) for v in face_size(size, g[0]))
            regions.append((pi, g, w, h, paint(rng, w, h, g[0])))
    order = sorted(range(len(regions)), key=lambda k: (-regions[k][3], -regions[k][2]))
    tex_h = 32
    while True:
        atlas = Image.new("RGBA", (tex_w, tex_h), (0, 0, 0, 0))
        uv, x, y, shelf, ok = {}, 0, 0, 0, True
        for k in order:
            pi, g, w, h, img = regions[k]
            if x + w > tex_w:
                x, y, shelf = 0, y + shelf, 0
            if y + h > tex_h:
                ok = False
                break
            atlas.paste(img, (x, y))
            for f in g:
                uv[(pi, f)] = (x, y)
            x += w
            shelf = max(shelf, h)
        if ok:
            return atlas, uv
        tex_h *= 2


def quat_y(deg):
    a = math.radians(deg) / 2
    return {"x": 0, "y": round(math.sin(a), 6), "z": 0, "w": round(math.cos(a), 6)}


def num(v):
    return int(v) if float(v).is_integer() else v


def build_model(name, parts, uv):
    children = []
    for pi, (pname, c, size, rot, _, shading) in enumerate(parts):
        layout = {f: {"offset": {"x": uv[(pi, f)][0], "y": uv[(pi, f)][1]}, "mirror": {"x": False, "y": False}, "angle": 0}
                  for f in FACES}
        children.append({
            "id": str(pi + 2),
            "name": pname,
            "position": {"x": num(c[0]), "y": num(c[1]), "z": num(c[2])},
            "orientation": quat_y(rot),
            "shape": {
                "type": "box",
                "offset": {"x": 0, "y": 0, "z": 0},
                "stretch": {"x": 1, "y": 1, "z": 1},
                "settings": {"size": {"x": num(size[0]), "y": num(size[1]), "z": num(size[2])}, "isStaticBox": True},
                "textureLayout": layout,
                "unwrapMode": "custom",
                "visible": True,
                "doubleSided": False,
                "shadingMode": shading,
            },
        })
    root = {
        "id": "1",
        "name": name,
        "position": {"x": 0, "y": 0, "z": 0},
        "orientation": {"x": 0, "y": 0, "z": 0, "w": 1},
        "shape": {
            "type": "none",
            "offset": {"x": 0, "y": 0, "z": 0},
            "stretch": {"x": 1, "y": 1, "z": 1},
            "settings": {"isPiece": False},
            "textureLayout": {},
            "unwrapMode": "custom",
            "visible": True,
            "doubleSided": False,
            "shadingMode": "flat",
        },
        "children": children,
    }
    return {"format": "prop", "lod": "auto", "nodes": [root]}


def rot_y(p, deg):
    a = math.radians(deg)
    x, y, z = p
    return (x * math.cos(a) + z * math.sin(a), y, -x * math.sin(a) + z * math.cos(a))


def face_quads(part, uv, pi):
    name, c, size, rot, _, shading = part
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    defs = {
        "top": ((-hx, hy, -hz), (2 * hx, 0, 0), (0, 0, 2 * hz), (0, 1, 0)),
        "bottom": ((-hx, -hy, hz), (2 * hx, 0, 0), (0, 0, -2 * hz), (0, -1, 0)),
        "front": ((-hx, hy, hz), (2 * hx, 0, 0), (0, -2 * hy, 0), (0, 0, 1)),
        "back": ((hx, hy, -hz), (-2 * hx, 0, 0), (0, -2 * hy, 0), (0, 0, -1)),
        "right": ((hx, hy, hz), (0, 0, -2 * hz), (0, -2 * hy, 0), (1, 0, 0)),
        "left": ((-hx, hy, -hz), (0, 0, 2 * hz), (0, -2 * hy, 0), (-1, 0, 0)),
    }
    for f, (o, u, v, n) in defs.items():
        o = rot_y(o, rot)
        o = (o[0] + c[0], o[1] + c[1], o[2] + c[2])
        yield f, o, rot_y(u, rot), rot_y(v, rot), rot_y(n, rot), uv[(pi, f)], face_size(size, f), shading


def render(parts, atlas, uv, size, yaw, pitch, scale, center):
    W = H = size
    zbuf = [[-1e9] * W for _ in range(H)]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px, tex = img.load(), atlas.load()
    light = (0.45, 0.8, 0.4)
    ln = math.sqrt(sum(v * v for v in light))
    light = tuple(v / ln for v in light)

    def view(p):
        p = rot_y((p[0] - center[0], p[1] - center[1], p[2] - center[2]), yaw)
        a = math.radians(pitch)
        return (p[0], p[1] * math.cos(a) - p[2] * math.sin(a), p[1] * math.sin(a) + p[2] * math.cos(a))

    for pi, part in enumerate(parts):
        for f, o, u, v, n, (tu, tv), (fw, fh), shading in face_quads(part, uv, pi):
            nv = view((n[0] + center[0], n[1] + center[1], n[2] + center[2]))
            if nv[2] <= 0:
                continue
            lum = 1.0 if shading == "fullbright" else 0.55 + 0.45 * max(0, sum(n[k] * light[k] for k in range(3)))
            su, sv = max(2, int(fw * scale * 1.6) + 2), max(2, int(fh * scale * 1.6) + 2)
            for j in range(sv):
                fv = (j + 0.5) / sv
                for i in range(su):
                    fu = (i + 0.5) / su
                    q = view(tuple(o[k] + u[k] * fu + v[k] * fv for k in range(3)))
                    sx, sy = int(W / 2 + q[0] * scale), int(H / 2 - q[1] * scale)
                    if 0 <= sx < W and 0 <= sy < H and q[2] > zbuf[sy][sx]:
                        zbuf[sy][sx] = q[2]
                        t = tex[min(tu + int(fu * max(1, math.ceil(fw))), atlas.width - 1),
                                min(tv + int(fv * max(1, math.ceil(fh))), atlas.height - 1)]
                        px[sx, sy] = shade(t[:3], lum) + (255,)
    return img


def write_item_model(name, parts, model_dir, icon_dir, seed, center, scale):
    """Écrit <name>.blockymodel et <name>.png (atlas) dans model_dir, l'icône 64×64 dans icon_dir ; rend l'icône."""
    import generate_item_models as items  # modèles détaillés (passe 3D), prioritaires sur la silhouette de base
    if name in items.ITEMS:
        return items.write(name, model_dir, icon_dir)
    atlas, uv = build_atlas(parts, seed)
    model_dir.mkdir(parents=True, exist_ok=True)
    icon_dir.mkdir(parents=True, exist_ok=True)
    atlas.save(model_dir / f"{name}.png")
    (model_dir / f"{name}.blockymodel").write_text(json.dumps(build_model(name, parts, uv), indent=2) + "\n")
    big = render(parts, atlas, uv, 256, yaw=-35, pitch=24, scale=scale, center=center)
    small = big.resize((64, 64), Image.LANCZOS)
    small.save(icon_dir / f"{name}.png")
    return small
