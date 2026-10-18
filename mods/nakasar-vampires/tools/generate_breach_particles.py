#!/usr/bin/env python3
"""Génère les particules rouges de la brèche des chasseurs (bloc Nakasar_Breach_Rift).

    python3 mods/nakasar-vampires/tools/generate_breach_particles.py ASSETS_ZIP

ASSETS_ZIP est l'Assets.zip du jeu (sous Windows :
%APPDATA%\\Hytale\\install\\release\\package\\game\\latest\\Assets.zip). Le résultat est versionné, le
script ne sert qu'à le refaire (autre teinte, nouvelle version du jeu).

Le champ « Color » d'une particule de bloc ne teinte pas les systèmes vanilla de la brèche gobeline :
leurs émetteurs portent leurs propres couleurs (vu en jeu le 2026-10-18, la faille restait verte et
bleue). Le script recopie donc sous des ids Nakasar_Breach_* le portail de la brèche gobeline
(GoblinBreach_Portal_Active) et la faille du donjon gobelin (Dungeon_Goblin_Void_Rift), avec chaque
couleur ramenée au rouge sang (même clarté). L'émetteur qui montre le monde des gobelins à travers le
portail (GoblinBreach_Portal_Core8, texture World_Goblin.png) n'est pas repris.

Écrit src/main/resources/Server/Particles/Nakasar/Breach/ : Nakasar_Breach_Portal et Nakasar_Breach_Rift
(.particlesystem) et leurs émetteurs (.particlespawner).
"""
import argparse
import colorsys
import json
import re
import zipfile
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent / "src" / "main" / "resources"
OUT = PACK / "Server" / "Particles" / "Nakasar" / "Breach"

# id vanilla du système -> (chemin dans Assets.zip, nouvel id, préfixe vanilla des émetteurs, nouveau préfixe)
SYSTEMS = {
    "GoblinBreach_Portal_Active": (
        "Server/Particles/Spell/Portal/GoblinBreach_Portal_Active.particlesystem",
        "Nakasar_Breach_Portal", "GoblinBreach_", "Nakasar_Breach_Portal_"),
    "Dungeon_Goblin_Void_Rift": (
        "Server/Particles/Environment/Dungeon_Goblin/Void_Rift/Dungeon_Goblin_Void_Rift.particlesystem",
        "Nakasar_Breach_Rift", "Dungeon_Goblin_Void_Rift_", "Nakasar_Breach_Rift_"),
}
SKIPPED_SPAWNERS = {"GoblinBreach_Portal_Core8"}  # le monde des gobelins vu à travers le portail

COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def redden(color):
    """Même clarté, teinte rouge sang (cramoisi dans l'ombre, rouge orangé dans la lumière)."""
    r, g, b = (int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    if l < 0.02:
        return color  # le noir reste noir (fumées de la faille)
    if s < 0.08:
        s, l = (1.0, 0.88) if l > 0.9 else (0.6, l)  # blancs roses, gris rougis
    else:
        s = max(s, 0.8)
    hue = (345 + 20 * l) % 360 / 360  # 345° (cramoisi) -> 5° (rouge orangé) avec la clarté
    r, g, b = colorsys.hls_to_rgb(hue, l, s)
    return "#%02x%02x%02x" % tuple(round(c * 255) for c in (r, g, b))


def recolor(node):
    if isinstance(node, dict):
        return {k: (redden(v) if isinstance(v, str) and COLOR.match(v) else recolor(v)) for k, v in node.items()}
    if isinstance(node, list):
        return [recolor(v) for v in node]
    return node


def spawner_paths(zf):
    return {Path(n).name.removesuffix(".particlespawner"): n for n in zf.namelist() if n.endswith(".particlespawner")}


def write(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("assets", help="Assets.zip du jeu")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.particle*"):
        old.unlink()
    with zipfile.ZipFile(args.assets) as zf:
        spawners = spawner_paths(zf)
        for vanilla_id, (path, new_id, prefix, new_prefix) in SYSTEMS.items():
            system = json.loads(zf.read(path))
            kept = []
            for entry in system["Spawners"]:
                spawner_id = entry["SpawnerId"]
                if spawner_id in SKIPPED_SPAWNERS:
                    continue
                assert spawner_id.startswith(prefix), spawner_id
                new_spawner = new_prefix + spawner_id.removeprefix(prefix)
                write(OUT / f"{new_spawner}.particlespawner", recolor(json.loads(zf.read(spawners[spawner_id]))))
                kept.append({**entry, "SpawnerId": new_spawner})
            system.pop("$Comment", None)
            system = {"$Comment": f"Copie rouge de {vanilla_id} (vanilla) pour la brèche des chasseurs. "
                                  "Générée par tools/generate_breach_particles.py.", **system, "Spawners": kept}
            write(OUT / f"{new_id}.particlesystem", system)
            print(f"{new_id}: {len(kept)} émetteurs")


if __name__ == "__main__":
    main()
