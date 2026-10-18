"""Hook MkDocs du wiki joueur : publie les icônes du pack sans les copier dans docs/wiki.

Les pages citent images/jeu/<chemin sous Common>, par exemple
images/jeu/Icons/Items/Nakasar/Sacrificial_Altar.png ; ce hook ajoute ces fichiers au site depuis
mods/nakasar-vampires/src/main/resources/Common, pour que les icônes restent celles du mod.
"""
from pathlib import Path

from mkdocs.structure.files import File

COMMON = Path(__file__).resolve().parent.parent / "mods" / "nakasar-vampires" / "src" / "main" / "resources" / "Common"
FOLDERS = ("Icons", "UI/StatusEffects", "UI/WorldMap/MapMarkers")


def on_files(files, config):
    for folder in FOLDERS:
        for png in sorted((COMMON / folder).rglob("*.png")):
            src_uri = "images/jeu/" + png.relative_to(COMMON).as_posix()
            files.append(File.generated(config, src_uri, abs_src_path=str(png)))
    return files
