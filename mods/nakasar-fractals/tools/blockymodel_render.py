"""Rendu isométrique générique d'un .blockymodel (boîtes texturées) + texture atlas."""
import json, math
from PIL import Image

def qmat(q):
    x, y, z, w = q["x"], q["y"], q["z"], q["w"]
    n = math.sqrt(x*x+y*y+z*z+w*w) or 1
    x, y, z, w = x/n, y/n, z/n, w/n
    return ((1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)),
            (2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)),
            (2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)))

def mul(a, b):
    return tuple(tuple(sum(a[i][k]*b[k][j] for k in range(3)) for j in range(3)) for i in range(3))

def ap(m, p):
    return tuple(sum(m[i][k]*p[k] for k in range(3)) for i in range(3))

def v3(d):
    return (d["x"], d["y"], d["z"])

def boxes(model):
    out = []
    I = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    def walk(n, pc, pm):
        s = n.get("shape", {})
        m = mul(pm, qmat(n["orientation"]))
        o = tuple(pc[k] + ap(pm, v3(n["position"]))[k] for k in range(3))
        off = ap(m, v3(s.get("offset", {"x": 0, "y": 0, "z": 0})))
        c = tuple(o[k] + off[k] for k in range(3))
        if s.get("type") == "box" and s.get("visible", True):
            size = v3(s["settings"]["size"])
            st = v3(s.get("stretch", {"x": 1, "y": 1, "z": 1}))
            out.append(dict(c=c, m=m, size=size, real=tuple(size[k]*st[k] for k in range(3)),
                            layout=s.get("textureLayout", {}), glow=s.get("shadingMode") == "fullbright"))
        for ch in n.get("children", []):
            walk(ch, c, m)
    for n in model["nodes"]:
        walk(n, (0, 0, 0), I)
    return out

def face_size(size, f):
    sx, sy, sz = size
    return (sx, sz) if f in ("top", "bottom") else (sx, sy) if f in ("front", "back") else (sz, sy)

def tex_size(size, f):
    return tuple(max(1, math.ceil(v - 1e-6)) for v in face_size(size, f))

def quads(b):
    hx, hy, hz = (v/2 for v in b["real"])
    defs = {
        "top": ((-hx, hy, -hz), (2*hx, 0, 0), (0, 0, 2*hz), (0, 1, 0)),
        "bottom": ((-hx, -hy, hz), (2*hx, 0, 0), (0, 0, -2*hz), (0, -1, 0)),
        "front": ((-hx, hy, hz), (2*hx, 0, 0), (0, -2*hy, 0), (0, 0, 1)),
        "back": ((hx, hy, -hz), (-2*hx, 0, 0), (0, -2*hy, 0), (0, 0, -1)),
        "right": ((hx, hy, hz), (0, 0, -2*hz), (0, -2*hy, 0), (1, 0, 0)),
        "left": ((-hx, hy, -hz), (0, 0, 2*hz), (0, -2*hy, 0), (-1, 0, 0)),
    }
    m, c = b["m"], b["c"]
    for f, (o, u, v, n) in defs.items():
        if f not in b["layout"]:
            continue
        o = ap(m, o)
        off = b["layout"][f].get("offset", {"x": 0, "y": 0})
        yield (f, tuple(o[k]+c[k] for k in range(3)), ap(m, u), ap(m, v), ap(m, n),
               (off["x"], off["y"]), tex_size(b["size"], f))

def shade(c, f):
    return tuple(max(0, min(255, int(round(v*f)))) for v in c[:3])

def render(bxs, atlas, size=256, yaw=-35, pitch=26, bg=None, fill=0.78):
    a, bb = math.radians(yaw), math.radians(pitch)
    def view(p, center):
        x, y, z = p[0]-center[0], p[1]-center[1], p[2]-center[2]
        x, z = x*math.cos(a)+z*math.sin(a), -x*math.sin(a)+z*math.cos(a)
        return (x, y*math.cos(bb)-z*math.sin(bb), y*math.sin(bb)+z*math.cos(bb))
    # cadrage sur la projection des coins
    pts = []
    for b in bxs:
        hx, hy, hz = (v/2 for v in b["real"])
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    q = ap(b["m"], (sx*hx, sy*hy, sz*hz))
                    pts.append(tuple(b["c"][k]+q[k] for k in range(3)))
    if not pts:
        return Image.new("RGBA", (size, size), bg or (0, 0, 0, 0))
    vp = [view(p, (0, 0, 0)) for p in pts]
    lo = [min(p[k] for p in vp) for k in range(2)]
    hi = [max(p[k] for p in vp) for k in range(2)]
    scale = size*fill/max(hi[0]-lo[0], hi[1]-lo[1], 1e-6)
    cx, cy = (lo[0]+hi[0])/2, (lo[1]+hi[1])/2
    W = H = size
    zbuf = [[-1e18]*W for _ in range(H)]
    img = Image.new("RGBA", (W, H), bg or (0, 0, 0, 0))
    px, tex = img.load(), atlas.load()
    def lum(n):
        if n[1] > 0.7: return 1.0
        if n[1] < -0.7: return 0.5
        return 0.72 + 0.16*max(-1, min(1, 0.8*n[0]+0.6*n[2]))
    for clear in (False, True):
        for b in bxs:
            for f, o, u, v, n, (tu, tv), (fw, fh) in quads(b):
                nv = view(n, (0, 0, 0))
                lu, lv = math.hypot(*u), math.hypot(*v)
                thin = min(b["real"]) < 1e-6
                if nv[2] <= 1e-6 and not thin:
                    continue
                l = 1.0 if b["glow"] else lum(n)
                su = max(2, int(lu*scale*1.6)+2)
                sv = max(2, int(lv*scale*1.6)+2)
                done = set()
                for j in range(sv):
                    fv = (j+0.5)/sv
                    for i in range(su):
                        fu = (i+0.5)/su
                        q = view(tuple(o[k]+u[k]*fu+v[k]*fv for k in range(3)), (0, 0, 0))
                        sx, sy = int(W/2+(q[0]-cx)*scale), int(H/2-(q[1]-cy)*scale)
                        if 0 <= sx < W and 0 <= sy < H and q[2] > zbuf[sy][sx]:
                            tx, ty = int(tu+fu*fw), int(tv+fv*fh)
                            if not (0 <= tx < atlas.width and 0 <= ty < atlas.height):
                                continue
                            t = tex[tx, ty]
                            if t[3] < 16 or (t[3] < 250) != clear:
                                continue
                            if not clear:
                                zbuf[sy][sx] = q[2]
                                px[sx, sy] = shade(t, l)+(255,)
                            elif (sx, sy) not in done:
                                done.add((sx, sy))
                                k, d = t[3]/255, px[sx, sy]
                                c = shade(t, l)
                                px[sx, sy] = tuple(int(c[m]*k+d[m]*(1-k)) for m in range(3))+(max(d[3], t[3]),)
    return img

def cube(textures, size=256, bg=None):
    """Cube plein texturé : textures = {'top': img, 'side': img}."""
    top, side = textures["top"].convert("RGBA"), textures["side"].convert("RGBA")
    w = max(top.width, side.width)
    atlas = Image.new("RGBA", (w*2, w))
    atlas.paste(top.resize((w, w), Image.NEAREST), (0, 0))
    atlas.paste(side.resize((w, w), Image.NEAREST), (w, 0))
    lay = {f: {"offset": {"x": 0 if f in ("top", "bottom") else w, "y": 0}} for f in ("top", "bottom", "front", "back", "left", "right")}
    b = dict(c=(0, 0, 0), m=((1, 0, 0), (0, 1, 0), (0, 0, 1)), size=(w, w, w), real=(w, w, w), layout=lay, glow=False)
    return render([b], atlas, size, bg=bg, fill=0.72)
