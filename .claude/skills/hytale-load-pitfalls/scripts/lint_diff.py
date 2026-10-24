#!/usr/bin/env python3
"""Relit les lignes ajoutées par la branche (contre origin/main) à la recherche des pièges qui ont déjà cassé un
chargement ou un comportement en jeu, et que les validateurs Gradle ne voient pas tous.

    python3 .claude/skills/hytale-load-pitfalls/scripts/lint_diff.py [--base origin/main] [--staged]

Sortie : une ligne par alerte (fichier:ligne, niveau, explication). Code de sortie 1 s'il y a une ERREUR.
Les AVERTISSEMENTS demandent un coup d'œil : ils peuvent être voulus.
"""
import argparse
import re
import subprocess
import sys

RULES = [
    # (niveau, regex fichier, regex ligne ajoutée, explication)
    ("ERREUR", r"manifest\.json$", r'"Dependencies"',
     "dépendance REQUIRED : si le mod cité manque ou est désactivé, AUCUN pack ne charge (même vanilla). "
     "Entre mods Nakasar, utiliser OptionalDependencies."),
    ("ERREUR", r"\.json$", r'"Force"\s*:\s*true',
     "Despawn Force true retire l'entité pendant son propre tick : crash du monde (Invalid entity reference)."),
    ("ERREUR", r"\.json$", r'"WorldSoundEventId"\s*:\s*"[^"]*_Local"',
     "WorldSoundEventId doit être un son MONO ; *_Local est stéréo, l'interaction entière est rejetée."),
    ("ERREUR", r"\.json$", r'"(Path|Prefab)"\s*:\s*"Prefabs/',
     "chemin de prefab relatif à <pack>/Server/Prefabs/ : le préfixe Prefabs/ donne un prop vide, sans erreur."),
    ("ERREUR", r"\.java$", r"EntityStatsSystems\.Regenerate",
     "système jamais enregistré : une SystemDependency dessus fait échouer le setup du plugin. "
     "Utiliser NPCPlugin.NPCEntityRegenerateStatsSystem ou EntityStatsModule.PlayerRegenerateStatsSystem."),
    ("AVERTISSEMENT", r"\.java$", r"canRemoveItemStack\(\s*new ItemStack",
     "canRemoveItemStack compare aussi la DURABILITÉ : un objet usé n'est plus reconnu. Pour un objet à "
     "durabilité, compter par id (countItemStacks / forEach + removeItemStackFromSlot)."),
    ("AVERTISSEMENT", r"\.java$", r"new DynamicLight\(|DynamicLight\.getComponentType",
     "un composant DynamicLight est diffusé à TOUS les spectateurs (et n'est pas sauvegardé) ; pour une "
     "lumière privée, voir vampirism/PrivateNightLightSystem."),
    ("AVERTISSEMENT", r"\.java$", r"KnockbackComponent",
     "Kevin a refusé la répulsion par knockback (« pas un champ de force ») : préférer une modification du "
     "steering (PurifyingSteeringSystem)."),
    ("AVERTISSEMENT", r"\.json$", r'"(RotationMode|DrawType|Opacity|Material|HitboxType|VariantRotation)"\s*:\s*"[A-Z]+_[A-Z_]+"',
     "les enums d'assets sont en CamelCase (FacingPlayer), pas en MAJUSCULES Java."),
]

GENERATED_HINT = re.compile(r"(Layout\.java|\.prefab\.json|TriggerVolumeData\.json|PointData\.json|docs/npc-reference)")


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--staged", action="store_true", help="ne regarder que l'index")
    a = ap.parse_args()
    diff_args = ["diff", "--cached"] if a.staged else ["diff", f"{a.base}...HEAD"]
    alerts = []
    # 1. lignes ajoutées
    current = None
    line_no = 0
    for line in git(*diff_args, "-U0", "--no-color").splitlines():
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            line_no = int(m.group(1)) - 1 if m else 0
        elif line.startswith("+") and current:
            line_no += 1
            if current.startswith(".claude/skills/"):
                continue
            code = line[1:].strip()
            if current.endswith(".java") and code.startswith(("*", "//", "/*")):
                continue  # commentaires et Javadoc : ils citent souvent le piège pour l'expliquer
            for level, frx, lrx, why in RULES:
                if re.search(frx, current) and re.search(lrx, line):
                    alerts.append((level, f"{current}:{line_no}", why))
    # 2. fichiers qui changent anormalement (README réécrit caractère par caractère, générateur non déterministe)
    for row in git(*diff_args, "--numstat").splitlines():
        parts = row.split("\t")
        if len(parts) != 3 or parts[0] == "-":
            continue
        added, removed, path = int(parts[0]), int(parts[1]), parts[2]
        if path.endswith(".md") and added > 3000:
            alerts.append(("ERREUR", path, f"+{added} lignes dans un .md : remplacement raté (chaîne vide insérée "
                                           "entre chaque caractère, déjà arrivé au README) ?"))
        elif added + removed > 20000 and not GENERATED_HINT.search(path):
            alerts.append(("AVERTISSEMENT", path, f"+{added}/-{removed} lignes : voulu ?"))
        elif GENERATED_HINT.search(path) and removed > 0 and added == removed and added > 2000:
            alerts.append(("AVERTISSEMENT", path, "fichier généré entièrement réécrit à l'identique en taille : "
                                                 "générateur non déterministe ? (Tower0.prefab.json l'est : git checkout)"))
    for level, where, why in alerts:
        print(f"{where}: {level}: {why}")
    if not alerts:
        print("aucune alerte")
    sys.exit(1 if any(a[0] == "ERREUR" for a in alerts) else 0)


if __name__ == "__main__":
    main()
