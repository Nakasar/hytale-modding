---
name: hytale-vanilla-research
description: Étudier comment Hytale vanilla (0.7.x) fait déjà une chose avant de la coder dans un mod — lire Assets.zip sur le PC de Kevin, décompiler le jar serveur, retrouver un id vanilla (bloc, PNJ, son, particule, drop, animation), le format réel d'un asset ou le comportement d'un système. À utiliser dès qu'une tâche touche une mécanique, un format d'asset ou un id que le dépôt n'a pas encore utilisé, quand un asset est refusé au chargement, ou quand on se demande "est-ce que vanilla a déjà…", "comment Deepworks fait…", "quel est l'id de…", même si la demande ne parle pas de vanilla.
---

# Recherche dans le vanilla

Hytale 0.7.2 n'a presque pas de documentation officielle. Le dépôt a appris que **copier ce que fait vanilla**
marche presque toujours du premier coup, alors qu'une structure inventée ou un id deviné fait souvent tomber
tout l'asset, voire tout le pack, au chargement (un drop inconnu a rejeté un rôle, puis la validation des
marqueurs a abandonné le mod entier). Le vanilla est aussi la référence de style et de feeling : un boss qui
annonce ses coups comme Deepworks, un arbre qui ressemble aux arbres vanilla, se lisent naturellement.

Donc avant d'inventer : trouver l'analogue vanilla le plus proche, lire ses vrais fichiers, en reprendre la
structure et les ids, et noter ce qu'on a appris.

## Où chercher, du moins cher au plus cher

1. **Ce que le dépôt sait déjà.** Souvent suffisant, et sans déranger Kevin.
   - `docs/api-0.7.2.md` (plugin, interactions, systèmes, codecs), `docs/npc-0.7.2.md`, `docs/npc-reference-0.7.2.md`
     (toutes les briques de rôles PNJ avec leurs champs, générée depuis le jar).
   - `mods/*/tools/vanilla-*.txt` : ids de blocs, gradient sets, références vérifiées (drops, rôles, marqueurs),
     sons stéréo. Un id présent là est sûr.
   - la mémoire du projet : `hytale-api-notes`, `hytale-npc-models`, `hytale-block-models`, `hytale-block-ids`,
     `hytale-dungeons` (Deepworks), `hytale-npc-combat`, `hytale-damage-pipeline`, `hytale-world-events`.
   - `grep -r` dans les assets du dépôt : un id vanilla déjà utilisé ici a déjà passé le chargement.
2. **Le jar serveur** (dans le conteneur, sans rien demander) : le vrai comportement des systèmes, des codecs,
   des champs JSON acceptés, des validateurs.
   ```bash
   S=.claude/skills/hytale-vanilla-research/scripts/server_jar.sh
   $S find 'npc.*Despawn'                      # trouver une classe
   $S javap com.hypixel.hytale.server…Classe   # signatures
   $S decompile com.hypixel.hytale.server…Classe   # source lisible (Vineflower), lire le comportement réel
   $S grep 'AimingReference' com.hypixel.hytale.server.npc   # chercher dans tout un paquet décompilé
   ```
   Les `*Codec`/`BuilderCodec` donnent les clés JSON exactes et leur casse (les enums sont en CamelCase :
   `FacingPlayer`, pas `FACING_PLAYER`). Les classes `*Validator` disent ce qui sera refusé en jeu.
   `ValidateRoles.java --descriptors` régénère la référence des briques PNJ.
3. **Assets.zip sur le PC de Kevin** : tout `Server/**` vanilla (rôles, interactions, objets, prefabs, instances,
   particules, worldgen) et `Common/**` (modèles, textures, animations). Le jar ne contient pas ces JSON.
   - Accès en lecture seule, accordé quand on le demande dans le fil avec une raison. Chemin du jeu :
     `C:\Users\User\AppData\Roaming\Hytale\install\release\package\game\latest` (Assets.zip ~3,9 Go).
     `list_devices` d'abord ; demander ce dossier une seule fois avec `device_request_folder_access`.
   - Lire le zip en place avec `device_bash` et le script fourni, passé par heredoc :
     ```bash
     cd "$HOME/mnt/latest" && python3 - grep '"Type": *"Teleport"' --glob 'Server/Item/Interactions/**' <<'EOF'
     <contenu de .claude/skills/hytale-vanilla-research/scripts/assets_zip.py>
     EOF
     ```
     Commandes : `ls GLOB`, `cat CHEMIN`, `grep REGEX --glob`, `refs ID` (qui cite cet id), `keys GLOB` (schéma
     réel d'une famille : clés et fréquences), `extract GLOB DEST`.
   - Ramener des **résumés texte**, pas des Mo de JSON. Pour une image ou un modèle à regarder :
     `extract` vers `latest\_claude_tmp\`, puis `device_stage_files` (seuls les fichiers des dossiers connectés
     se copient) ; dire à Kevin qu'il peut supprimer `_claude_tmp`.
4. **Le web communautaire**, en dernier et avec méfiance : hytale-moddings.github.io, hytale.source.gs,
   hytale.isaacguru.com (liste d'ids fiable, via curl). hytalewiki.org Module:ID donne des clés de traduction,
   pas des ids. docs.hytale.com quand une page existe.

## Méthode

1. **Nommer l'analogue vanilla** de ce qu'on veut faire. Repères déjà connus : donjon et rencontres =
   Deepworks (`Server/Instances/The_Deepworks`, `EncounterManager`) ; attaque annoncée = gobelin
   `Dungeon_Goblin_Mace_Slam` ; volants = `Spirit_*` (Walk en vol stationnaire, pas Fly seul) ; humanoïde =
   modèle `Parent: Player` + `DefaultAttachments` ; bloc animé = coffres/torches ; portail = `Portal_Device`
   et `PortalKey_*` ; arbres = prefabs vanilla de `Trees/` ; village brûlé = `Monuments/Encounter/Zone4/Tier4`.
2. **Lire les vrais fichiers** de cet analogue (pas un résumé de wiki) et le code qui les consomme si le
   comportement compte.
3. **Reprendre la structure**, changer le minimum. Référencer les assets vanilla (modèles, sons, particules,
   animations) plutôt que les recréer, sauf si le style l'exige.
4. **Étiqueter chaque fait** selon sa source, dans les notes comme dans la PR : *vérifié dans le jar*,
   *lu dans Assets.zip*, *vu en jeu par Kevin*, ou *supposé*. Un id supposé va dans « Points à vérifier en jeu »
   du README, jamais dans `tools/vanilla-refs-0.7.2.txt`.
5. **Garder la trouvaille** : un id lu dans les fichiers du jeu → la liste `vanilla-*.txt` concernée (les
   validateurs s'en servent) ; un format ou un comportement → `docs/api-0.7.2.md` ou le fichier mémoire du
   sujet. Sinon le prochain fil refera la même fouille et redemandera l'accès à Kevin.

## Ce qu'on rend

Une courte note de trouvailles : l'analogue vanilla choisi, les chemins lus, les champs/ids repris, leur niveau
de confiance, et ce qui reste à vérifier en jeu. Puis le code, qui suit cette structure.
