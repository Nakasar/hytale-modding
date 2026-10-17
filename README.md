# hytale-modding

Mods pour **Hytale** (serveur `0.7.x`, « Update 7 »), développés par Nakasar.

| Mod | Type | Artefact | Contenu |
|-----|------|----------|---------|
| `mods/nakasar-runes` | plugin Java + pack d'assets | `Nakasar-Runes-<version>.jar` | 4 runes d'abilities (Baiser du Vampire, Domination, Téléportation, Chaînes spectrales) et l'autel sacrificiel qui les fabrique |
| `mods/nakasar-spear` | pack d'assets pur | `Nakasar-Spear-<version>.zip` | Lance de fer à deux mains : enchaînement, coup chargé, compétence ultime |
| `mods/nakasar-halloween` | pack d'assets pur | `Nakasar-Halloween-<version>.zip` | Fragment d'Orbis « Halloween » ouvert depuis l'Ancienne passerelle : cryptes, châteaux hantés, château du comte vampire, cimetières, champs de citrouilles |

Le détail de chaque mod (fichiers, chaînes d'interactions, réglages) est dans [docs/mods.md](docs/mods.md).
Les points d'API serveur vérifiés dans le jar `Server-0.7.2` sont notés dans [docs/api-0.7.2.md](docs/api-0.7.2.md).

## Prérequis

- **JDK 25** (les classes du serveur 0.7.2 sont compilées en Java 25). Le build utilise une
  *toolchain* Gradle : si aucun JDK 25 n'est installé, le plugin `foojay-resolver` le télécharge.
- Rien d'autre : le wrapper Gradle (`./gradlew`) télécharge Gradle 9.8.1, et l'artefact serveur
  `com.hypixel.hytale:Server:0.7.2` vient du Maven officiel `https://maven.hytale.com/release`.

## Construire

```bash
./gradlew build
```

- `mods/nakasar-runes/build/libs/Nakasar-Runes-0.1.0.jar`
- `mods/nakasar-spear/build/distributions/Nakasar-Spear-0.1.0.zip`
- `mods/nakasar-halloween/build/distributions/Nakasar-Halloween-0.1.0.zip`

`build` lance aussi `validateJson`, qui vérifie la syntaxe de tous les JSON d'assets (le parseur du
serveur est strict : une virgule en trop fait échouer le chargement du mod).

Pour le fragment Halloween, `build` lance aussi `validateAssets` : il décode chaque asset du pack
(biome, structure de monde, instance, portail, clé, environnements, météo, spawns) avec les codecs
du jar serveur et signale les clés inconnues et les valeurs invalides, sans démarrer le jeu. Les ids
vanilla référencés (PNJ, blocs, `PortalKey_Taiga`, `Env_Zone1_Plains`) ne sont pas vérifiés.

Les prefabs et la génération du monde sont produits par des scripts (déterministes) :

```bash
python3 mods/nakasar-halloween/tools/generate_prefabs.py    # 35 prefabs dans pack/Server/Prefabs/Nakasar/Halloween
python3 mods/nakasar-halloween/tools/generate_worldgen.py   # biome + structure de monde
```

## Déployer sur un serveur local

Indiquez le dossier `mods/` de votre serveur dans `gradle-local.properties` (fichier non versionné) :

```properties
hytale.modsDir=/chemin/vers/Server/mods
```

puis :

```bash
./gradlew deployToServer
```

(ou en une fois : `./gradlew deployToServer -Phytale.modsDir=/chemin/vers/Server/mods`).

## Tester en jeu

Démarrer le serveur avec `--validate-assets` la première fois : il vérifie les références d'assets et les
« promesses » des mots-clés de runes, et s'arrête avec la liste des erreurs s'il y en a.

```text
/abilities give                      # donne toutes les runes (dont les 4 du mod)
/give Rune_Nakasar_VampireKiss       # ou une seule
/give Rune_Nakasar_Domination
/give Rune_Nakasar_Blink
/give Rune_Nakasar_SpectralChains
/give Weapon_Nakasar_Spear_Iron      # la lance
/give Nakasar_Sacrificial_Altar      # l'autel sacrificiel
/give Ingredient_Rune_Shard 8        # éclats de rune pour tester les recettes
```

Fragment Halloween :

```text
/give PortalKey_Nakasar_Halloween    # la clé, à poser dans une Ancienne passerelle (Portal_Device)
/instances spawn Nakasar_Halloween_Fragment   # ou ouvrir l'instance directement, sans portail
```

### Recettes

- **Autel sacrificiel** (`Nakasar_Sacrificial_Altar`) : à l'atelier de base (`Workbench`, onglet
  `Workbench_Crafting`, palier 1) avec 10 pierres (ressource `Rock`), 2 lingots de fer et 1 éclat de rune.
  Une fois posé, un clic d'utilisation ouvre son interface de craft.
- **Runes** : chaque rune du mod coûte **2 éclats de rune** (`Ingredient_Rune_Shard`) sur l'autel, comme les
  runes de capacités du jeu.
- **Lance** : à l'établi de forgeron de base (`Weapon_Bench`, onglet « Épées » `Weapon_Sword`, palier 1 ; il n'y a
  pas d'onglet lance) avec 4 lingots de fer, 2 bûches (ressource `Wood_Trunk`) et 2 cuirs légers.

Les recettes sont des fichiers séparés (`Server/Item/Recipes/Nakasar/`), `KnowledgeRequired: false` (visibles sans
avoir été apprises). Séparées plutôt qu'inline dans les objets : le serveur valide chaque `ItemId` d'ingrédient et
rejette l'asset entier en cas d'id inconnu, donc un id d'ingrédient faux ne fait perdre que la recette, pas la rune.

Les runes se lancent avec les touches d'abilities (Ability2 / Ability3) en tenant une arme. La lance :
clic pour l'enchaînement, maintenir le clic (~0,8 s) pour le coup circulaire, touche Ability1 quand la
jauge de signature est pleine pour l'ultime.

## Points à vérifier en jeu (non vérifiables hors jeu)

Les assets client (modèles, animations, icônes) ne sont pas dans le jar serveur, donc quelques ids sont
repris de la documentation communautaire sans avoir pu être contrôlés :

- **Animations de la lance** : les ids `SwingLeft`, `SwingRight`, `SwingDown` existent sur les rigs
  standards mais pas forcément sur le rig `Spear`. Si un coup ne joue pas d'animation, remplacer l'id
  dans `Nakasar_Spear_Swing_*.json` / `Nakasar_Spear_Thrust.json`.
- **Modèle / icône de la lance** : `Items/Weapons/Spear/Iron.blockymodel` et
  `Icons/ItemsGenerated/Weapon_Spear_Iron.png` sont les chemins de la lance vanilla. Un modèle dédié
  pourra être ajouté ensuite dans le pack.
- **Visuel des runes** : les 4 runes réutilisent l'icône et la texture de `Rune_Fireball`.
- **Ruée de l'ultime** (`Nakasar_Spear_Signature_Dash.json`) : poussée continue de 0,55 s (`Duration`)
  lancée en parallèle des estocs. `Z: -1` doit pousser vers l'avant ; inverser le signe si le joueur
  recule. Régler la distance avec `Force` (vitesse) et `Duration`.
- **Identifiants vanilla** : `Weapon_Bench` / `Weapon_Sword`, `Workbench` / `Workbench_Crafting`,
  `Ingredient_Bar_Iron`, `Ingredient_Leather_Light`, ressources `Rock` et `Wood_Trunk`, `PlayerAnimationsId: Block`,
  `BlockSoundSetId: Stone`, `BlockParticleSetId: Stone`, `ISS_Blocks_Wood`, `GatherType: Benches` et
  `Furniture.Benches` sont lus dans `Server/Item/Items/Bench/Bench_Weapon.json` des assets 0.7.2 du jeu ;
  `Ingredient_Rune_Shard` existe (`Server/Item/Items/Ingredient/Goblin/Ingredient_Rune_Shard.json`).
  Restent non vérifiés : `BlockBreakingDecalId: Breaking_Decals_Rock` et les sons `SFX_Workbench_Open` /
  `SFX_Workbench_Craft` (documentation communautaire). Le serveur valide ces ids au
  chargement : un id inconnu rejette l'asset entier et le journal le nomme.
- **Modèle de l'autel** : modèle, texture, hitbox et icône sont générés par
  `mods/nakasar-runes/tools/generate_altar.py` (format JSON du plugin Blockbench officiel, 32 unités = 1 bloc).
  À vérifier en jeu : l'autel occupe 2×2×1 blocs (large × haut × profond) et doit se poser avec ses blocs de
  remplissage ; le sens des pièces pivotées (`orientation`), le côté « avant » (crâne et dague d'un côté de la
  dalle) et le cadrage de l'icône 3D (`IconProperties`, repris de l'établi d'alchimie). Si le rendu ou les UV
  sont faux, ouvrir le `.blockymodel` dans Blockbench avec le plugin Hytale, ou corriger le script et le
  relancer.

Fragment Halloween :

- **Ids des PNJ** : `Skeleton`, `Skeleton_Archer`, `Skeleton_Soldier`, `Skeleton_Archmage`,
  `Skeleton_Elite`, `Zombie`, `Zombie_Aberrant`, `Spider`, `Spider_Cave`, `Ghoul`, `Wraith`,
  `Werewolf`, `Bat`, `Crow` viennent du wiki. `/npc spawn` sans argument liste les vrais ids : corriger
  `NPC/Spawn/World/Nakasar_Halloween_*.json` si l'un manque.
- **Clé de fragment** : elle hérite de `PortalKey_Taiga` (modèle, icône) et ne change que le texte et le
  type de portail.
- **Météo** : `Nakasar_Weather_Halloween` définit brouillard, ciel et lumière (violet / orange) mais
  pas de nuages, d'étoiles ni de texture de lune (chemins inconnus). La densité du brouillard
  (`FogDensities`, `FogDistance`) et la densité de spawn des environnements sont à régler à l'œil.
- **Prefabs** : l'orientation par défaut des meubles (cercueils, chaises, bancs) et des escaliers n'est
  pas connue ; les toits et escaliers sont faits de blocs pleins et de demi-dalles pour l'éviter.
  Les châteaux et cryptes sont posés à plat grâce à un terrain aplani autour des structures.
- **Temps** : l'instance démarre à 20 h, avec des jours de 5 min et des nuits de 20 min.

## Organisation du dépôt

```text
build.gradle.kts            # config commune : toolchain Java 25, dépendance serveur, validateJson, deployToServer
settings.gradle.kts         # dépôts Maven (Hytale), liste des mods
gradle.properties           # version serveur ciblée, identité des mods
mods/<mod>/                 # un sous-projet Gradle par mod
  src/main/java             # (plugin) code Java
  src/main/resources        # (plugin) manifest.json + Server/** (pack d'assets embarqué)
  pack/                     # (pack pur) manifest.json + Server/**
  tools/                    # (halloween) générateurs de prefabs / worldgen, validateur d'assets
docs/                       # notes de conception et d'API
```

## Ajouter un mod

1. Créer `mods/<nom>` avec un `build.gradle.kts` (copier `nakasar-runes` pour un plugin,
   `nakasar-spear` pour un pack pur).
2. L'ajouter dans `settings.gradle.kts` (`include(":mods:<nom>")`).
3. Préfixer tous les ids d'assets par `Nakasar_` (ou `<Mod>_`) pour éviter les collisions avec le jeu.
