# hytale-modding

Mods pour **Hytale** (serveur `0.7.x`, « Update 7 »), développés par Nakasar.

Un seul mod, **Vampires** (`mods/nakasar-vampires`, plugin Java + pack d'assets, artefact
`Nakasar-Vampires-<version>.jar`) : le domaine du Comte vampire.

| Partie | Contenu |
|--------|---------|
| Fragment Halloween | Fragment d'Orbis ouvert depuis l'Ancienne passerelle : manoir du Comte, village abandonné, fermes délaissées, ancien poste de garde, cryptes, châteaux hantés, cimetières, forêts mortes |
| Mobs | Comte et Comtesse Vampire (boss qui lancent les sorts des runes), rejetons, fantômes, morts-vivants du domaine et leurs élites ; tous les mobs du fragment sont alliés entre eux |
| Runes et autel | 4 runes d'abilities (Baiser du Vampire, Domination, Téléportation, Chaînes spectrales) et l'autel sacrificiel qui les fabrique ; la Domination fait changer de camp le mob visé |
| Établi des chasseurs | Établi à 2 niveaux : torches et lanternes de feu purificateur, runes Aura de lumière et Invisibilité, fragment du Comté Vampire |
| Lance | Lance de fer à deux mains : enchaînement, coup chargé, compétence ultime |
| Armes en argent | Version en argent de chaque arme standard, de la lance du mod et des flèches : double dégâts contre les vampires (Comte, Comtesse, rejetons) |

Le guide du joueur (fragment, structures, bestiaire, brèches, objets) est un wiki publié sur GitHub Pages : https://nakasar.github.io/hytale-modding/ (sources Markdown dans [docs/wiki](docs/wiki/README.md), site Docusaurus dans [wiki](wiki/), aperçu local : `cd wiki && npm ci && npm start`).
Le détail du mod (fichiers, chaînes d'interactions, camps, réglages) est dans [docs/mods.md](docs/mods.md).
L'histoire et la progression visées (voie des chasseurs, voie occulte, joueur vampire, zones à venir) : [docs/histoire-progression.md](docs/histoire-progression.md).
Les points d'API serveur vérifiés dans le jar `Server-0.7.2` sont notés dans [docs/api-0.7.2.md](docs/api-0.7.2.md).
Création de PNJ (rôles, IA, modèles, apparitions) : [docs/npc-0.7.2.md](docs/npc-0.7.2.md), et la référence complète des 179 briques d'IA générée depuis le jar : [docs/npc-reference-0.7.2.md](docs/npc-reference-0.7.2.md).

## Prérequis

- **JDK 25** (les classes du serveur 0.7.2 sont compilées en Java 25). Le build utilise une
  *toolchain* Gradle : si aucun JDK 25 n'est installé, le plugin `foojay-resolver` le télécharge.
- Rien d'autre : le wrapper Gradle (`./gradlew`) télécharge Gradle 9.8.1, et l'artefact serveur
  `com.hypixel.hytale:Server:0.7.2` vient du Maven officiel `https://maven.hytale.com/release`.

## Construire

```bash
./gradlew build
```

- `mods/nakasar-vampires/build/libs/Nakasar-Vampires-0.1.0.jar`

`build` lance aussi `validateJson`, qui vérifie la syntaxe de tous les JSON d'assets (le parseur du
serveur est strict : une virgule en trop fait échouer le chargement du mod).

`build` lance aussi `validateRoles` (`mods/nakasar-vampires/tools/ValidateRoles.java`, rôles de PNJ) et
`validateAssets` (`mods/nakasar-vampires/tools/ValidateAssets.java`) :
il décode chaque asset du pack (biome, structure de monde, instance, portail, objets, environnements, météo,
spawns, modèles, effets, butins, interactions, y compris celles écrites en ligne dans `Next` ou `Parallel`)
avec les codecs du jar serveur et signale les clés inconnues et les valeurs invalides (par exemple un
`Parallel` à une seule branche), sans démarrer le jeu. Il vérifie aussi que
chaque bloc des prefabs et du générateur existe dans `tools/vanilla-block-ids-0.7.2.txt` (un id inconnu
devient un damier rose et noir en jeu). Il vérifie enfin les références vers les listes de butin (`DropList`, `DroplistId`, coffres des prefabs), les rôles
de PNJ (marqueurs et apparitions, invocations `Kind`) et les marqueurs d'apparition (`SpawnMarker`) : chaque id doit
exister dans le pack ou figurer dans `tools/vanilla-refs-0.7.2.txt`. En jeu, une liste de butin inconnue rejette le
rôle qui la cite, puis le marqueur qui fait apparaître ce rôle fait échouer tout le mod. Les autres ids référencés (sons, stats, `PortalKey_Taiga`,
`Env_Zone1_Plains`) ne sont pas vérifiés, ni les interactions de type Java de nos plugins et les assets
qui héritent d'un parent vanilla (notés « non vérifiable hors jeu »).

Les prefabs et la génération du monde sont produits par des scripts (déterministes) :

```bash
python3 mods/nakasar-vampires/tools/generate_prefabs.py    # 65 prefabs dans src/main/resources/Server/Prefabs/Nakasar/Halloween
python3 mods/nakasar-vampires/tools/generate_loot.py       # listes de butin des coffres
python3 mods/nakasar-vampires/tools/generate_worldgen.py   # biome + structure de monde
python3 mods/nakasar-vampires/tools/generate_pumpkin_models.py  # modèles animés de la citrouille géante et de ses vrilles (--preview DOSSIER : rendus)
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

Dans un monde solo, activez **Vampires** dans la liste des mods du monde.

**Mise à jour depuis les anciens mods séparés** : supprimez du dossier `mods/` les fichiers `Nakasar-Runes-*.jar`,
`Nakasar-Spear-*.zip`, `Nakasar-Halloween-*.zip` et `Nakasar-Mobs-*.jar` avant d'y mettre `Nakasar-Vampires-*.jar`
(ils déclarent les mêmes assets), puis activez Vampires dans les mondes qui utilisaient les anciens mods. Les ids
d'objets, de blocs, de PNJ et de prefabs n'ont pas changé : runes, autels posés, coffres et fragments déjà générés
restent valides.

### Pack de tous les mods

`./gradlew packMods` construit `build/distributions/Nakasar-Mods-Pack-<version>.zip`, qui contient les jars et
zips de tous les mods à sa racine (aujourd'hui le seul `Nakasar-Vampires-<version>.jar`) : il s'extrait directement dans le dossier `mods/` d'une save ou d'un serveur.
La CI publie le même contenu dans l'artefact `Nakasar-Mods-Pack` (onglet « Actions », en bas du run) : le zip
téléchargé s'extrait lui aussi directement dans `mods/`.

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
/give Weapon_Nakasar_Spear_Silver    # la lance en argent (toutes les armes en argent : Weapon_Nakasar_*_Silver)
/give Weapon_Nakasar_Arrow_Silver 40 # flèches en argent, munitions de tous les arcs et arbalètes
/give Ingredient_Bar_Silver 20       # lingots d'argent vanilla pour tester les recettes
/give Nakasar_Sacrificial_Altar      # l'autel sacrificiel
/give Ingredient_Rune_Shard 8        # éclats de rune pour tester les recettes
```

Fragment Halloween :

```text
/give PortalKey_Nakasar_Halloween    # la clé, à poser dans une Ancienne passerelle (Portal_Device)
/instances spawn Nakasar_Halloween_Fragment   # ou ouvrir l'instance directement, sans portail
```

Mobs (le manoir du comte, dans le fragment, contient déjà le Comte ou la Comtesse, une chance sur deux, et deux rejetons dans sa crypte) :

```text
/npc spawn Nakasar_Vampire_Count     # le boss
/npc spawn Nakasar_Vampire_Countess  # la boss
/npc spawn Nakasar_Vampire_Spawn     # un rejeton
/npc spawn Nakasar_Ghost             # un fantôme
/npc spawn Nakasar_Zombie_Villager   # villageois zombifié (aussi _Zombie_Farmer, _Zombie_Rebel, _Skeleton_Guard)
/npc spawn Nakasar_Zombie_Abomination  # élite des fermes : écrasement annoncé
/npc spawn Nakasar_Guard_Captain     # élite du poste de garde : fendant, tourbillon, emprisonnement
/npc spawn Nakasar_Giant_Pumpkin     # élite du champ de citrouilles : vrilles combattantes, poison, piège annoncé
/npc spawn Nakasar_Vampire_Hunter_Crossbow  # chasseurs de vampires (aussi _Gunner, _Blade) : neutres, ennemis des mobs du fragment
/give Nakasar_Prison_Cell            # bloc invisible : cellule où le capitaine envoie le joueur
/give Nakasar_Spawner_Vampire_Count  # bloc invisible qui fait (ré)apparaître le comte là où il est posé
```

Brèches des chasseurs de vampires (monde principal, toutes les 30 min, la nuit). Le monde doit autoriser les
évènements de monde et l'apparition des PNJ, sinon le camp reste vide (vu en jeu le 2026-10-18) :

```text
/time midnight                                       # les brèches ne s'ouvrent que la nuit
/worldevent start asset Nakasar_Hunter_Breach_Test   # ouvre tout de suite un campement près de vous, une fois
/worldevent list                                     # l'évènement Nakasar_Hunter_Breach et son étape en cours
```

### Recettes

- **Autel sacrificiel** (`Nakasar_Sacrificial_Altar`) : à l'atelier de base (`Workbench`, onglet
  `Workbench_Crafting`, palier 1) avec 10 pierres (ressource `Rock`), 2 lingots de fer et 1 éclat de rune.
  Une fois posé, un clic d'utilisation ouvre son interface de craft.
- **Runes** : chaque rune du mod coûte **2 éclats de rune** (`Ingredient_Rune_Shard`) sur l'autel, comme les
  runes de capacités du jeu.
- **Lance** : à l'établi de forgeron de base (`Weapon_Bench`, onglet « Épées » `Weapon_Sword`, palier 1 ; il n'y a
  pas d'onglet lance) avec 4 lingots de fer, 2 bûches (ressource `Wood_Trunk`) et 2 cuirs légers.

- **Armes en argent** : au `Weapon_Bench` (onglets Épées, Massues, Haches de combat, Dagues et Arcs), avec des
  lingots d'argent vanilla (`Ingredient_Bar_Silver`) à la place des lingots de fer de l'arme en fer. Flèches en
  argent : 8 flèches grossières + 1 lingot d'argent donnent 8 flèches en argent. Liste et recettes dans
  `mods/nakasar-vampires/tools/generate_silver_weapons.py`.

Les recettes (sauf celles des armes en argent, voir plus bas) sont des fichiers séparés (`Server/Item/Recipes/Nakasar/`), `KnowledgeRequired: false` (visibles sans
avoir été apprises). Séparées plutôt qu'inline dans les objets : le serveur valide chaque `ItemId` d'ingrédient et
rejette l'asset entier en cas d'id inconnu, donc un id d'ingrédient faux ne fait perdre que la recette, pas la rune.

Les armes en argent héritent (`Parent`) de l'arme en fer : elles portent donc leur recette dans l'objet, sinon elles
hériteraient de la recette en fer. Elles sont générées par `tools/generate_silver_weapons.py` (à relancer avec le
chemin de l'`Assets.zip` du jeu : il y lit les textures et icônes en fer à repeindre en argent).

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
- **Particules des runes** (chaînes vertes, gouttes de sang) : le format est celui du serveur 0.7.2 (décodé
  sans erreur par ses codecs), mais l'unité de `Scale` n'est pas documentée. Si les chaînes sont trop
  grandes ou trop petites, ajuster `InitialAnimationFrame.Scale` dans
  `Server/Particles/Nakasar/Nakasar_Spectral_Chain_Rise.particlespawner` (idem `Nakasar_Blood_Drain`).
  La hauteur de départ (sous le sol) est le `PositionOffset.Y` du `.particlesystem`.
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
  `mods/nakasar-vampires/tools/generate_altar.py` (format JSON du plugin Blockbench officiel, 32 unités = 1 bloc).
  À vérifier en jeu : l'autel occupe 2×2×1 blocs (large × haut × profond) et doit se poser avec ses blocs de
  remplissage ; le sens des pièces pivotées (`orientation`), le côté « avant » (crâne et dague d'un côté de la
  dalle) et le cadrage de l'icône 3D (`IconProperties`, repris de l'établi d'alchimie). Si le rendu ou les UV
  sont faux, ouvrir le `.blockymodel` dans Blockbench avec le plugin Hytale, ou corriger le script et le
  relancer.
- **Établi des chasseurs** (`tools/generate_hunter_bench.py`) : à vérifier en jeu, le bouton d'amélioration vers
  le niveau 2 et son coût, `BlockParticleSetId: Wood` (id supposé), le cadrage de l'icône, et pour les runes :
  la lumière portée par l'Aura (copie de la torche), le rendu des particules autour du lanceur, la disparition du
  lanceur invisible pour les autres joueurs et le retour à la normale quand il bouge, frappe ou se déconnecte.

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
- **Prefabs** : orientation des meubles déduite des hitboxes et des villages du jeu (lacet 0 = sud) :
  à vérifier en jeu sur le village, la ferme et le poste de garde (portes, lits, chaises autour des
  tables, toits à 45°). Les troncs tombés utilisent les rotations 4 (nord-sud) et 5 (est-ouest) :
  s'ils apparaissent debout, inverser `ALONG_Z` et `ALONG_X` dans `generate_prefabs.py`.
- **Coffres** : remplis à la pose du prefab par le serveur (`ItemContainerBlock.Droplist`) ; si un
  coffre apparaît vide, vérifier que `IsBlockSpawnersEnabled` n'est pas désactivé dans la config du monde.
- **Arbres du jeu** : le worldgen pioche surtout dans les arbres vanilla (sapins et frênes morts,
  chênes moussus en forêt ; frênes tordus, calcinés, pétrifiés isolés), dossiers lus dans Assets.zip
  0.7.2 et listés dans `FOREST_TREES` et `LONE_TREES` (`generate_worldgen.py`). Un dossier renommé par une mise à jour ne place
  plus rien, sans erreur : vérifier cette liste après chaque mise à jour du jeu. Les châteaux et cryptes sont posés à plat grâce à un terrain aplani autour des structures.
- **Manoir et crypte d'arrivée** : les blocs générés par `tools/generate_assets.py` (vitraux,
  gargouille, grille à lances, vantail de portail) sont à vérifier en jeu : transparence des vitraux,
  sens des gargouilles (elles doivent regarder vers l'extérieur : sinon, corriger `FACING` dans
  `generate_prefabs.py`), grille alignée avec le muret, vantaux ouverts. On doit apparaître au centre
  de la crypte, portail de retour compris, la porte donnant au nord vers le manoir.
- **Liste des blocs** : `tools/vanilla-block-ids-0.7.2.txt` vient des fichiers du jeu publiés par
  hytale.isaacguru.com (ids d'objets qui ont un `BlockType`, états compris). Si un bloc récent manque,
  l'ajouter à la main ; si un bloc de la liste s'affiche en damier rose, le signaler pour l'en retirer.
- **Temps** : l'instance démarre à 20 h, avec des jours de 5 min et des nuits de 20 min.

Mobs (voir [docs/npc-0.7.2.md](docs/npc-0.7.2.md)) :

- **Apparence** : le Comte, la Comtesse et le rejeton sont des humanoïdes sur le squelette du joueur
  (vêtements du créateur de personnage recolorés, peau blafarde, yeux rouges) avec un col victorien dédié
  généré par `mods/nakasar-vampires/tools/generate_vampire_models.py`. À vérifier : place et orientation du
  col, couleurs des vêtements. Le fantôme reste sur le modèle vanilla `Wraith`.
- **Icônes d'effets** : Domination, Chaînes spectrales et Toucher glacial ont une icône dédiée
  (`Common/UI/StatusEffects/Nakasar/`) ; elle doit remplacer la croix rouge.
- **Attaques** : les animations (`SwingRight`, `SwingDown`) et le visé des sorts à distance (sélecteur
  `Stab` en ligne droite depuis le regard du PNJ, joueurs seulement) sont à confirmer.
- **Domination** : quand le comte vous fixe (teinte violette), vos coups ne doivent plus le blesser
  pendant 6 s ; ceux des autres joueurs, si.
- **Téléportation** : le comte et les fantômes doivent réapparaître face à leur cible.
- **Marqueurs du manoir** : le bloc invisible `Nakasar_Spawner_*` (composant `SpawnMarkerBlock`) n'a pas
  pu être décodé hors jeu. Si le boss n'apparaît pas au manoir, le poser à la main avec `/give`.
- **Densité** : poids des fantômes et rejetons dans l'environnement hanté à régler à l'œil.
- **Camps** : dans le fragment, aucun mob ne doit en attaquer un autre, et une flèche de squelette perdue ne doit
  plus blesser un zombie. Si un mob vanilla du fragment en attaque encore un autre, son id manque dans
  `NPC/Groups/Nakasar_Halloween_Faction.json` (le journal signale aussi les ids de ce groupe qui n'existent pas).
- **Domination sur un mob** (rune) : pendant l'effet, le mob visé doit se détourner de vous et attaquer les mobs
  du fragment à moins de 16 blocs, qui doivent riposter ; à la fin, il redevient hostile envers vous et cesse de
  frapper ses alliés. Les mobs du mod sont réglés pour ça ; pour les mobs vanilla (squelettes, zombies...), cela
  dépend de leurs rôles : s'ils restent passifs une fois dominés, il faudra leur donner un coup de pouce en Java.

- **Armes en argent** : contre le Comte, la Comtesse ou un rejeton, un coup doit faire environ le double des dégâts
  de la même arme en fer (le bonus vient de `SilverDamageSystem`, qui lit le tag `Material: Silver` de l'arme tenue).
  Flèches en argent : tout arc ou arbalète (vanilla compris), en mode Aventure, doit les tirer avant les flèches
  simples ; relâcher l'arc sans tirer ou changer d'objet arbalète chargée doit rendre les mêmes flèches (argent ou
  simples). Au chargement, le journal ne doit pas signaler d'erreur sur `Nakasar_TakeArrow` / `Nakasar_ReturnArrow`. Teinte des textures repeintes à juger à l'œil.

- **Brèches** : au démarrage du monde principal, la carte doit afficher « Brèche des chasseurs : prochaine dans
  30:00 ». La nuit, un message prévient, puis un campement s'ouvre à 48–160 blocs d'un joueur, avec titre, son
  et épingle sur la carte et la boussole (icône `Nakasar_HunterBreach.png`). À vérifier : que la faille est bien
  rouge (copies rouges des particules de la brèche gobeline), que la traverser mène dans la crypte d'un Comté Vampire
  et que son portail de retour ramène devant l'arche, que le campement est posé au ras du sol et tourné dans tous les
  sens sans chasseur dans un mur, que les chasseurs ne vous attaquent pas mais ripostent, et qu'à la fermeture
  (10 min) le terrain revient et les chasseurs disparaissent. Si rien ne démarre, chercher `Nakasar_Hunter_Breach`
  et `Nakasar_NightCondition` dans le journal.
- **Citrouille géante et vrilles** (`tools/generate_pumpkin_models.py`) : premiers modèles animés écrits à la main
  (sans Blockbench). À vérifier : sens des rotations (la vrille doit se pencher vers sa cible pour le coup normal,
  le haut de la citrouille se soulever par l'avant), yeux et bouche lumineux (plaque `*_Glow` transparente hors des
  découpes), animations d'attaque jouées par `ItemAnimationId` (`Server/Item/Animations/Nakasar/`). Si un sens est
  inversé, changer le signe dans la pose de l'animation concernée et relancer le script.
- **Joueur vampire** (`vampirism/`, `tools/generate_occult.py`) : améliorer l'autel au niveau 3, fabriquer le
  calice et le boire près de l'autel. À vérifier : la nourriture du jeu ne régénère plus (ses effets commencent
  par `Food_` et sont retirés ; sinon chercher le vrai préfixe dans Assets.zip), la régénération naturelle est
  coupée, le palier de soif s'affiche et baisse (`/time` pour avancer), la brûlure au soleil cesse sous un toit et
  pendant l'orage (ids de météo reconnus par mots-clés `storm`/`thunder`/`rain`... dans `SunExposure`),
  l'éblouissement (`ScreenEffects/Nakasar/Sun_Glare.png`), la lumière de nuit visible par soi, le battement de
  cœur quand affamé, l'état gardé après reconnexion, les potions bues au clic droit (modèle de fiole et prise en
  main), la capuche et le voile portés. Le malus de vitesse d'attaque réduit les dégâts des coups trop rapprochés
  (le serveur ne peut pas ralentir l'animation).

## Organisation du dépôt

```text
build.gradle.kts            # config commune : toolchain Java 25, dépendance serveur, validateJson, deployToServer, packMods
settings.gradle.kts         # dépôts Maven (Hytale), liste des mods
gradle.properties           # version serveur ciblée, identité des mods
mods/<mod>/                 # un sous-projet Gradle par mod
  src/main/java             # (plugin) code Java
  src/main/resources        # (plugin) manifest.json + Server/** (pack d'assets embarqué)
  pack/                     # (pack pur) manifest.json + Server/**
  tools/                    # générateurs (prefabs, worldgen, butin, modèles), validateurs hors jeu
                            # ValidateAssets.java (assets) et ValidateRoles.java (rôles PNJ)
docs/                       # notes de conception et d'API
```

## Ajouter un mod

1. Créer `mods/<nom>` avec un `build.gradle.kts` (copier `nakasar-vampires` pour un plugin ; pour un pack pur,
   une tâche `Zip` sur un dossier `pack/`, voir l'historique de `mods/nakasar-spear`).
2. L'ajouter dans `settings.gradle.kts` (`include(":mods:<nom>")`).
3. Préfixer tous les ids d'assets par `Nakasar_` (ou `<Mod>_`) pour éviter les collisions avec le jeu.
