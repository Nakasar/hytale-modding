# Conception des mods

## nakasar-runes (plugin Java + assets)

Tout est en JSON sauf quatre interactions impossibles en pur asset, écrites en Java et enregistrées sous
les types `Nakasar_TeleportCasterToImpact`, `Nakasar_Dominate`, `Nakasar_RootNpc` et `Nakasar_DrainBeam`.

Particules du mod : `Server/Particles/Nakasar/*.particlespawner|.particlesystem`, textures
`Common/Particles/Textures/Nakasar/*.png` (niveaux de gris teintés par `Color`, générées par
`tools/make_particle_textures.py`).

Fichiers communs : `Server/Abilities/Keywords/Nakasar_*.json` (mots-clés affichés sur les runes),
`Server/Languages/{fr-FR,en-US}/nakasar_runes.lang` (noms et descriptions).

Chaque rune suit le schéma vanilla (champs cosmétiques repris de `Rune_Fireball.json` : `Items.Ingredients`,
`PlayerAnimationsId: Item`, `IconProperties`, `Scale 0.8`, `ISS_Items_Gems`) : objet `Rune_Nakasar_<X>` (`Ability.Slot: Core`, coût en mana,
cooldown, mots-clés, attributs) → `Root_Nakasar_Ability_<X>` → `Nakasar_Ability_<X>_Cast`
(`StatsCondition UseAbilityCost` → `Parallel` [ effet, `TriggerCooldown`, `ChangeStat` ]).

| Rune | Coût / CD | Portée | Effet |
|------|-----------|--------|-------|
| Baiser du Vampire (`Rune_Nakasar_VampireKiss`) | 30 mana / 4 s | mêlée (balayage horizontal 2,8 m) | 18 dégâts physiques (× attribut `Damage`), `EntityStatsOnHit Health +12` au lanceur (vol de vie, dégressif sur plusieurs cibles) ; `Nakasar_DrainBeam` fait voyager le système `Nakasar_Blood_Drain` (gouttes rouge sang) de la cible au lanceur en 8 pas de 40 ms |
| Domination (`Rune_Nakasar_Domination`) | 45 mana / 12 s | regard, 8 m | `Nakasar_Dominate` passe **avant** le coût : sans PNJ visé (ou derrière un mur), rien ne se passe, ni mana ni recharge. Sinon attitude `FRIENDLY` forcée pendant `Duration` (6 s), le lanceur est retiré des cibles mémorisées du PNJ (un hostile en combat lâche prise), effet visuel `Nakasar_Dominated` (teinte violette), puis animation, recharge et coût |
| Téléportation (`Rune_Nakasar_Blink`) | 35 mana / 8 s | distance (projectile) | `Projectile_Config_Nakasar_Blink` ; à l'impact (entité ou terrain) `TriggerAbilityFX` puis `Nakasar_TeleportCasterToImpact` téléporte le lanceur 0,6 m en retrait du point d'impact, à 20 blocs au plus (`MaxDistance` : un impact plus lointain ramène l'arrivée à 20 blocs sur la droite lanceur → impact) |
| Chaînes spectrales (`Rune_Nakasar_SpectralChains`) | 40 mana / 10 s | distance (projectile) | `Projectile_Config_Nakasar_Chains` ; sur entité : FX « pointe de terre » verte, effet `Nakasar_Spectral_Chains` (`DisableAll`, attaques, abilities et esquive désactivées, knockback nul, teinte verte, particules `Stunned` et système `Nakasar_Spectral_Chains` : des chaînes vertes jaillissent du sol autour de la cible tant que dure l'effet) pendant `Duration` (3 s) + `Nakasar_RootNpc` (composant `Frozen`) pour les PNJ |

Attributs lisibles par les runes de support : `Damage` (Vampire), `Duration`
(Domination, Chaînes), `Speed` (projectiles).

### Autel sacrificiel (`Nakasar_Sacrificial_Altar`)

Objet-bloc (`Server/Item/Items/Bench/Nakasar/`) avec `BlockType.Bench` de type `Crafting`, id
`Nakasar_Sacrificial_Altar`, un seul onglet `Nakasar_Altar_Runes` et un seul palier. Comme `Bench_Weapon.json`
vanilla, le bloc déclare `BlockEntity.Components.BenchBlock` (l'entité de bloc qui porte l'établi) et
`State.Definitions` avec les états `CraftCompleted` / `CraftCompletedInstant` que la fenêtre de craft bascule
(`SimpleCraftingWindow`). `DrawType: Model`, `VariantRotation: NESW` +
`RotationMode: FacingPlayer` (l'autel fait face au joueur). Comme l'établi d'alchimie vanilla (`Bench_Alchemy`),
il occupe **2 blocs de large, 2 de haut et 1 de profondeur** : `HitboxType: Nakasar_Sacrificial_Altar`
(`Server/Item/Block/Hitboxes/Nakasar/`, boîtes en unités de bloc, bloc d'ancrage = [0,1]³) ; le serveur pose
les blocs de remplissage d'après l'enveloppe de la hitbox (`FillerBlockUtil`, arrondi au bloc supérieur) et la
fait tourner avec le bloc. `Support.Down: Full` comme le vanilla (il faut un bloc plein dessous), et il se
redonne lui-même à la casse (`Gathering.Breaking`).

Recettes dans `Server/Item/Recipes/Nakasar/` (fichiers séparés, voir README pour la raison) :
`Recipe_Nakasar_Sacrificial_Altar` à l'atelier de base `Workbench` / onglet `Workbench_Crafting` (10 `Rock`
ressource, 2 `Ingredient_Bar_Iron`, 1 `Ingredient_Rune_Shard`, 5 s) et `Recipe_Nakasar_Rune_<X>` sur l'autel,
onglet `Nakasar_Altar_Runes` (2 `Ingredient_Rune_Shard`, 1 s).

Modèle `Common/Blocks/Nakasar/Sacrificial_Altar.blockymodel`, texture
`Common/BlockTextures/Nakasar/Sacrificial_Altar.png` (256×128), hitbox et icône d'inventaire sont **générés** par
`mods/nakasar-runes/tools/generate_altar.py` (relancer le script après toute retouche, `--preview DOSSIER`
écrit des rendus de contrôle). Grille : 32 unités = 1 bloc, origine au centre du bas du bloc d'ancrage, le modèle
s'étend vers +X (x de -16 à 48). Pièces : socle à deux marches, corps à bandeau de runes, dalle à rigole, vasque
de sang, deux obélisques surmontés d'un cristal pourpre, bougies (flamme en `shadingMode: fullbright`), crâne et
dague. Chaque pièce porte sa position dans `position` (pivot) et une rotation Y éventuelle dans `orientation`.
La texture est peinte en dégradés doux (biseau clair sur les arêtes, bas des faces assombri, variations floutées)
plutôt qu'en bruit pixel par pixel ; une région par face, faces opposées partagées. Aucune face du dessous ne
porte de rouge (l'ancien modèle réutilisait la flaque de sang sous la dalle).

L'icône de l'onglet `Common/Icons/CraftingCategories/Nakasar/Runes.png` reste celle d'origine.

### Interactions Java

- `TeleportCasterToImpactInteraction` : lit la position du projectile (ou `HIT_LOCATION`), recule de
  `BackOffset` vers le lanceur, ajoute `VerticalOffset`, pose un composant `Teleport` sur le lanceur.
  `MaxDistance` (0 = illimitée) borne la distance au lanceur.
- `DominateInteraction` : cible = PNJ fourni par la chaîne, sinon `TargetUtil.getTargetEntity` dans l'axe du
  regard (`Range`) sans bloc devant ; `overrideAttitude(lanceur, attitude, durée)`, puis efface le lanceur des
  emplacements de `MarkedEntitySupport` (l'attitude n'est relue qu'à l'acquisition d'une cible) ; applique
  `EffectId` si fourni. `WaitForDataFrom.Server` : le client attend le verdict du serveur, la suite (`Next`)
  ne part qu'en cas de réussite. Clés JSON : `Range`, `Duration`, `DurationAttribute`, `EffectId`, `Attitude`.
- `DrainBeamInteraction` : joue `SystemId` (`ParticleUtil.spawnParticleEffect`) sur `Steps` points entre la
  cible et le lanceur, un pas toutes les `StepDelay` s (`world.scheduleAfter`), à `HeightOffset` au-dessus des pieds.
- `RootNpcInteraction` : ajoute `Frozen` à la cible PNJ et programme son retrait (`world.scheduleAfter`)
  ; une seconde application prolonge la durée, et un PNJ déjà gelé par quelqu'un d'autre (`/npc freeze`) n'est pas touché. Clés : `Duration`, `DurationAttribute`.

## nakasar-spear (pack d'assets)

Objet `Weapon_Nakasar_Spear_Iron` : rig `PlayerAnimationsId: Spear` (deux mains), famille `Spear`,
jauge `SignatureEnergy` (+20 max). Les dégâts sont surchargeables par objet via `InteractionVars`
(`Swing_Left_Damage`, `Swing_Right_Damage`, `Thrust_Damage`, `Spin_Charged_Damage`,
`Signature_Rush_Damage`, `Signature_Spin_Damage`), comme les armes vanilla.

### Attaque principale (`Root_Nakasar_Spear_Primary` → `Nakasar_Spear_Primary`)

`Charging` (animation `ThrowCharging`) :

- relâché tout de suite (`"0"`) → `Nakasar_Spear_Combo`, un `Chaining` (fenêtre 1,6 s) :
  1. `Nakasar_Spear_Swing_Left` : balayage horizontal vers la gauche (14 dégâts, +2 signature)
  2. `Nakasar_Spear_Swing_Right` : balayage vers la droite (14, +2)
  3. `Nakasar_Spear_Thrust` : petit pas en avant (`ApplyForce`) + estoc `Stab` 3,8 m (24 dégâts,
     knockback, +4 signature), puis `CancelChain` pour repartir du premier coup
- maintenu 0,8 s (`"0.8"`) → `Nakasar_Spear_Spin_Charged` : coup circulaire `AOECircle` rayon 3,5 m
  (20 dégâts, knockback radial `Point`, +3 signature)

### Ultime (`Root_Nakasar_Spear_Signature` sur `Ability1` → `Nakasar_Spear_Signature`)

`StatsCondition SignatureEnergy 100 %` (sinon son d'erreur) → `Serial` :

0. `ChangeStat SignatureEnergy -100 %` en tête : la jauge est consommée même si la chaîne est
   interrompue ensuite (coup reçu, changement d'objet)
1. préparation 0,2 s (animation `StabDashCharging`)
2. ruée : `ApplyForce` vers l'avant (force 12) puis `Repeat ×4` de `Nakasar_Spear_Signature_Rush_Stab`
   (petite poussée + estoc 3,5 m, 16 dégâts chacun, cadence ~0,28 s)
3. `Nakasar_Spear_Signature_Spin` : coup circulaire rayon 4 m, 40 dégâts, forte projection
4. `CancelChain`

### Recette

`Server/Item/Recipes/Nakasar/Recipe_Nakasar_Spear_Iron.json` : établi de forgeron vanilla (`Bench.Id` `Weapon_Bench`, palier 1),
4 `Ingredient_Bar_Iron`, 2 `Wood_Trunk` (ressource), 2 `Ingredient_Leather_Light`, 3,5 s. Le
L'onglet est `Weapon_Sword` : l'établi vanilla n'a que `Weapon_Sword`, `Weapon_Mace`, `Weapon_Battleaxe`,
`Weapon_Daggers` et `Weapon_Bow` (lu dans `Bench_Weapon.json` des assets 0.7.2).

### Réglages

Toutes les valeurs (dégâts, portées, durées, forces) sont dans les JSON cités ; aucun code.

## nakasar-halloween (pack d'assets)

Fragment d'Orbis ouvert depuis l'Ancienne passerelle vanilla (`Portal_Device`) avec la clé
`PortalKey_Nakasar_Halloween`. Chaîne : clé (`PortalKey.PortalType`) → `PortalTypes/Nakasar_Halloween`
(textes, objectifs, 30 min) → `Instances/Nakasar_Halloween_Fragment/instance.bson` (générateur
`HytaleGenerator`, météo forcée, début à 20 h) → structure de monde `Nakasar_Halloween` → biome
`Nakasar_Halloween_Barrens`.

### Génération (`tools/generate_worldgen.py`)

- **Forme** : île flottante au-dessus du vide, comme les fragments du jeu de base. Rayon
  `ISLAND_RADIUS` = 340 (bord réel vers 320-338 blocs du centre) : le sol s'abaisse de 8 blocs à partir
  de 296 blocs puis finit en falaise d'une dizaine de blocs, au contour dentelé par un bruit (`Rim`) ;
  le dessous est un cône de roche bosselé (jusqu'à y ≈ 17 au centre). Densité du terrain =
  `Min(dessus, dessous)`, la distance au centre venant d'un nœud `Axis` (axe Y).
- **Terrain** : collines autour de y = 81 (deux bruits simplex, sol entre y ≈ 65 et 91), herbe brûlée
  en surface avec des plaques de cendre, de terre brûlée et de gravier moussu (matériau `FieldFunction`
  sur un bruit), puis terre, gravier et pierre / ardoise / schiste.
- **Aplanissement** : les positions des structures sont exportées (`ExportAs`, nœuds flottants
  déclarés avant tout import) et réutilisées par le terrain : le relief tombe à zéro dans un rayon de
  34 blocs (plein relief à 52) autour de chaque structure, 50 (70) autour du village, 24 (40) autour de
  la crypte d'arrivée ; autour du manoir, plat jusqu'à 38 blocs (plein relief à 58).
- **Structures (domaine du Comte)** : treize emplacements fixes (`SLOTS`, trois grands pour le
  village), décalés d'au plus 16 blocs selon la graine du monde (`Jitter2d`). Le type de chaque
  emplacement change d'un monde à l'autre : huit répartitions sont tirées une fois par le script
  (`layouts()`, le village toujours sur un grand emplacement, deux structures du même type à plus
  de 140 blocs), et le monde en choisit une selon un bruit lu en un point fixe (`XOverride` /
  `ZOverride`, donc une valeur par graine). Le premier exemplaire de chaque type est toujours là, le
  second une fois sur deux (bruit propre à l'emplacement) : 0 ou 1 village (60 %), 1 ou 2 fermes,
  postes de garde, cimetières, cryptes, champs de citrouilles et châteaux hantés, toujours un seul
  manoir. Au moins 9 blocs entre deux structures dans le pire décalage. La variante (village
  zombies / ruines / araignées, etc.) et l'orientation sont tirées au hasard.
- **Manoir du comte** : toujours à 220 blocs au nord du point d'apparition (objectif du portail).
- **Arrivée** : `PortalTypes/Nakasar_Halloween` fixe le point d'apparition (`Spawn.SpawnProviderOverride`,
  fournisseur `Global`) en 0,5 / 81 / 0,5 ; sans lui, le jeu tire un point au hasard dans le tronçon
  (x et z entre 2 et 13). Le portail de retour y apparaît (le jeu vide 3 × 3 × 3 blocs autour), au
  centre de la crypte d'arrivée (`SpawnCrypt`) posée au même endroit.
- **Forêts** : là où un bruit à grande échelle (`Forest`, échelle 95) dépasse 0,2 (environ un tiers
  de l'île), maille serrée de 6,5 blocs : sapins et frênes morts du jeu, chênes et frênes moussus,
  souches, troncs couchés (`FOREST_TREES`), quelques-uns de nos arbres morts. Ailleurs, arbres isolés
  (maille de 16, `LONE_TREES` : frênes morts et tordus, quelques calcinés et pétrifiés).
- **Décor** : affleurements rocheux, troncs couchés, quelques cercles de champignons, tas d'os,
  tombes isolées, nids d'araignées et autels (maille de 26) ; herbes et buissons morts, fougères,
  racines, champignons (maille de 3). Arbres et décor restent à moins de 306 blocs du centre, hors du
  domaine du manoir, à 38 blocs d'une structure et 54 du village.
- **Chemins des prefabs** : relatifs à `Server/Prefabs/` (`Nakasar/Halloween/Crypts`), pas à `Server/`.
- **Environnements** : `Nakasar_Env_Halloween_Haunted` à moins de 45 blocs d'une structure (PNJ plus
  dangereux, densité plus forte), `Nakasar_Env_Halloween` ailleurs.

### Prefabs (`tools/generate_prefabs.py`, 65 fichiers)

| Dossier | Nombre | Contenu |
|---------|--------|---------|
| `Crypts` | 3 | Mausolée (pierre, ardoise, schiste) et salle funéraire enterrée : cercueils, braseros, ossements, cristaux, toiles |
| `HauntedCastles` | 2 | Château en ruine 33×33 (pierre ou ardoise) : tours, courtines, donjon (table, lustre, chambre), puits |
| `VampireManor` | 1 | Manoir gothique du comte, domaine 57×51 clos d'une grille à lances (portail en fer forgé entre deux piliers à gargouille). Corps de logis en basalte à étage, toits d'ardoise à 45°, deux ailes à pignon, tour-porche à rosace et flèche, vitraux, gargouilles. Habité : rez-de-chaussée avec hall à piliers et trône (marqueur Comte / Comtesse), grand escalier, cuisine (fourneau, four, réserve), salle à manger, cabinet de travail, bibliothèque ; étage avec galerie, chambre de la comtesse, chambre du comte (lit royal et cercueil), laboratoire d'alchimie (établis d'alchimie et arcanes, chaudrons), atelier (établi, forge d'armes, métier à tisser) ; crypte des rejetons et salle du trésor sous le hall ; jardin |
| `Villages/{Zombies,Ruins,Spiders}` | 3 | Village abandonné 69×69 : dix maisons (rez-de-chaussée en moellons, étage à colombages, toit de bois à 45°, cheminée), grange, forge, place au puits, jardins clos en friche ; envahi par les villageois zombifiés (portes enfoncées, fenêtres condamnées), en ruine et envahi par la végétation, ou envahi par les araignées (toiles, cocons) |
| `Farms/{Zombies,Ruins,Burnt}` | 3 | Ferme délaissée 49×45 : maison, grange, champs de blé, enclos, épouvantail ; envahie par les fermiers zombifiés et un zombie difforme (élite, dans la grange), abandonnée et en ruine, ou carbonisée (bois noirci, blé brûlé, feux) |
| `GuardPosts/{Ruins,Spiders,Rebels,Garrison}` | 4 | Ancien poste de garde 39×39 : enceinte crénelée, tour de guet, caserne, quartiers du capitaine, armurerie, prison à trois cellules (barreaux et porte), cachot dans l'armurerie, cour d'entraînement ; en ruine, envahi par les araignées, pris par les paysans zombifiés révoltés, ou tenu par les gardes squelettes et leur capitaine (élite) |
| `SpawnCrypt` | 1 | Crypte d'arrivée 11×11 fermée autour du portail de retour : porte au nord vers le manoir, rosace et vitraux, cercueils, gargouilles aux angles |
| `Cemeteries/{Haunted,Spiders,Undead}` | 2 × 3 | Cimetière clos (~31×33) : chapelle à clocher (bancs, autel, lustre), caveaux, portail à lanterne, muret à grille et piliers, allées pavées, tombes variées (stèles, croix, obélisques, sarcophages, tombes ouvertes), arbres morts ; hanté (bougies, champignons luisants), araignées (toiles, cocons) ou morts-vivants (fosses à cercueil, ossements) |
| `PumpkinFields` | 3 | Champ de citrouilles mûres (états de culture) clôturé de bois mort : allée à lanternes, épouvantails, charrette de récolte, meules de foin, cabane, arbre de pendu |
| `Trees` | 16 | Arbres morts en frêne, bois pétrifié ou calciné : squelette en troncs pleins comme les arbres du jeu (fût droit, pied 2×2 des grands, contreforts et racines, branches qui montent en escalier et se divisent), tubes fins au bout des rameaux, feuilles mortes de l'essence posées sur les branches, toiles et buissons pendants ; aucun bloc ne flotte (vérifié à la génération) ; 4 portent une lanterne, une cage ou une corde |
| `Decor/*` | 6 × 3 + 5 | Affleurements rocheux (parfois des cristaux), troncs couchés, cercles de champignons luisants, autels, tas d'os, tombes isolées, nids d'araignées |

Les ruines (châteaux hantés, mausolées, chapelles) sont écroulées à la génération, de façon
déterministe : plus on monte, plus il manque de blocs, puis tout bloc qui ne repose plus sur le sol
(contact par une face) est retiré, pour qu'aucun pan de mur ne lévite. Le manoir du comte est
habité, donc intact ; les murets et grilles des cimetières et les clôtures restent entiers.
`floating_blocks` vérifie qu'aucun prefab ne contient de bloc flottant.

Orientation et meubles (vérifiés sur les hitboxes `Server/Item/Block/Hitboxes` et les prefabs de
village du jeu) : le lacet 0 regarde le sud (+Z), 1 l'est, 2 le nord, 3 l'ouest. Les portes et
fenêtres prennent 0 dans un mur le long de X, 1 le long de Z ; les toits (`<Bois>_Roof`,
`Rock_*_Roof`) sont à 45° et descendent vers +Z à 0 (2 vers −Z, 1 vers +X, 3 vers −X), faîtage en
`*<Bois>_Roof_State_Definitions_Topper`. Les meubles de plusieurs cases (`HITBOXES` / `FURNITURE` :
tables 2×2, lits, armoires, établis, lustres…) sont posés avec leurs cases secondaires (`filler`
comme dans les prefabs du jeu) ; la génération échoue si deux meubles se chevauchent ou si un meuble
déborde dans un mur.

Coffres (`Prefab.chest`) : composant `ItemContainerBlock` avec une liste de butin (`Droplist`) que le
serveur tire à la pose du prefab. Listes générées par `tools/generate_loot.py` dans
`Server/Drops/Nakasar/Halloween` : ferme, ferme brûlée, maison, maison du notable, caserne,
armurerie, capitaine, crypte, château en ruine, et au manoir trésor, alchimie, bibliothèque,
cuisine, chambres, atelier. Objets du jeu 0.7.2 (vérifiés dans `Server/Item/Items`).

Blocs de `nakasar-mobs` posés dans les prefabs : spawners `Nakasar_Spawner_Zombie_Villager`,
`_Zombie_Farmer`, `_Zombie_Abomination` (élite, un par ferme zombie), `_Zombie_Rebel`,
`_Skeleton_Guard`, `_Guard_Captain` (élite, un par garnison), `_Spider`, et `Nakasar_Prison_Cell`
(invisible) au sol de chaque cellule du poste de garde (trois à l'est, une à l'ouest : toujours une à moins de 24 blocs du Capitaine), dans toutes les variantes : le Capitaine y
téléporte sa cible (cellule la plus proche à moins de 24 blocs).

Blocs du pack (`tools/generate_assets.py`, modèle, texture, icône et définition générés) :
`Nakasar_Stained_Glass_Red` / `_Violet` (vitraux, cubes translucides), `Nakasar_Gargoyle` (gargouille
sur socle, NESW), `Nakasar_Iron_Railing` (grille à lances, `VariantRotation: Wall` comme les grilles
en fer) et `Nakasar_Iron_Gate` (vantail de portail 1 × 2, NESW). Leurs modèles regardent vers +Z (le
sud) à la rotation 0.

Blocs : tous les autres ids viennent de `tools/vanilla-block-ids-0.7.2.txt` ; `validateAssets` refuse un
prefab ou un matériau de génération qui en utilise un autre (en jeu, un id inconnu devient le bloc
« Unknown », un damier rose et noir). Un état de bloc s'écrit `*<Bloc>_State_Definitions_<État>` (clé
générée par `StateData`), par exemple `*Plant_Crop_Pumpkin_Block_State_Definitions_StageFinal`. Les
tubes (troncs et branches, `VariantRotation: Pipe`) prennent la rotation 0 (debout), 4 (couché
nord-sud) ou 5 (couché est-ouest) : index `RotationTuple` = tangage × 4 + lacet. Les clôtures,
murets (`*_Brick_Wall`) et grilles (`Deco_Iron_Bars`) ne se raccordent pas tout seuls dans un prefab :
rotation 0 pour une ligne est-ouest (le long de X), 1 pour une ligne nord-sud (le long de Z).
`Prefab.orient_lines` choisit la rotation d'après les voisins avant l'écriture.

### PNJ

- `Nakasar_Halloween_Undead` (tout le fragment) : squelettes, archers, zombies, araignées, chauves-souris, corbeaux.
- `Nakasar_Halloween_Haunted` (près des structures) : spectres, goules, soldats et archimages squelettes,
  zombies aberrants, araignées des cavernes, élites et loups-garous (rares).
- Mobs de `nakasar-mobs` (dépendance optionnelle, mais sans lui ces apparitions échouent) : fantômes à toute heure et rejetons de vampire la nuit
  (`Nakasar_Halloween_Ghosts`, `Nakasar_Halloween_Vampire_Spawns_Dusk` / `_Dawn`, environnement hanté), et
  marqueurs d'apparition dans le manoir du comte (le Comte ou la Comtesse devant le trône, une chance sur deux, deux rejetons dans la crypte).

## nakasar-mobs (plugin Java + assets)

Dépend de `nakasar-runes` (ses interactions et particules sont réutilisées). Validation hors jeu :
`./gradlew :mods:nakasar-mobs:check` (rôles avec `tools/ValidateRoles.java`, autres assets avec le
validateur du fragment Halloween).

| PNJ | PV | Comportement |
|-----|----|--------------|
| `Nakasar_Vampire_Count` | 600 | Boss. Mêlée « Baiser du Vampire » (22 dégâts, +30 PV), Chaînes spectrales à 18 blocs (9 à 12 s), Domination à 12 blocs (16 à 20 s), téléportation près de la cible si elle est à plus de 7 blocs (10 à 14 s), sous 50 % de vie invoque 2 ou 3 rejetons (toutes les 30 s, tant qu'il n'y en a pas plus de 2 à moins de 40 blocs). Chaînes et Domination ne visent que les joueurs, sur une ligne droite : un rejeton devant lui ne les bloque pas. Retourne à son point d'apparition et regagne sa vie si la cible s'éloigne à plus de 40 blocs. |
| `Nakasar_Vampire_Countess` | 500 | Boss, plus vive que le Comte (vitesse 5,5). Mêmes Baiser du Vampire, Domination (14 à 18 s), téléportation (6 à 9 s), invocation et retour au point d'apparition ; pas de Chaînes spectrales. |
| `Nakasar_Vampire_Spawn` | 60 | Rapide, morsure 7 dégâts (+4 PV). |
| `Nakasar_Ghost` | 45 | Vole, toucher glacial (6 dégâts, ralenti 50 % pendant 3 s), réapparaît près de sa cible quand elle s'éloigne. |
| `Nakasar_Zombie_Villager` | 80 | Villageois zombifié (village abandonné), mêlée 14 dégâts. |
| `Nakasar_Zombie_Farmer` | 95 | Fermier zombifié (fermes), chapeau de paille et salopette tirés au hasard, mêlée 15. |
| `Nakasar_Zombie_Rebel` | 85 | Paysan rebelle zombifié (poste de garde), plus rapide, faucille, mêlée 17. |
| `Nakasar_Zombie_Abomination` | 450 | Élite des fermes (zombie aberrant géant). Morsure 34 ; Écrasement annoncé toutes les 11 à 14 s (lueur rouge, cercle au sol pendant 1,2 s) : onde en anneau de 7 blocs, 30 dégâts et projection. |
| `Nakasar_Skeleton_Guard` | 120 | Garde squelette en armure rouillée, épée et bouclier, mêlée 18. |
| `Nakasar_Guard_Captain` | 650 | Élite du poste de garde, hache de bataille. Combo gauche/droite (22) ; Fendant annoncé (1,1 s, 45 dégâts devant lui sur 5 blocs, 9 à 12 s) ; Tourbillon annoncé (1,3 s, 32 dégâts autour sur 4 blocs, 14 à 18 s) ; Emprisonnement (1,5 s d'incantation, rayon jusqu'à 16 blocs, 45 à 60 s) qui envoie le joueur touché dans la cellule du poste de garde. Immobile pendant chaque annonce. |

- **Domination** (Java, `domination/`) : l'interaction `Nakasar_DominatePlayer` enregistre « ce joueur est
  dominé par ce PNJ » pendant `Duration` secondes et applique l'effet `Nakasar_Count_Domination`. Le système
  `DominationDamageFilter` (groupe de filtrage des dégâts) annule tout dégât de ce joueur, projectiles
  compris, contre ce PNJ tant que l'effet dure.
- **Emprisonnement** (Java, `prison/`) : l'interaction `Nakasar_ImprisonPlayer` cherche le bloc invisible
  `Nakasar_Prison_Cell` le plus proche du capitaine (24 blocs, sous la portée de 32 blocs où il abandonne sa cible) et y téléporte le joueur, puis applique
  `Nakasar_Imprisoned` (ralenti 5 s). Le bloc se pose au niveau des pieds dans la cellule, bloc du dessus libre.
  Sans cellule à portée, seul l'effet s'applique.
- **Attaques annoncées** (abomination, capitaine) : même schéma que les gobelins du donjon Deepworks
  (`Dungeon_Goblin_Mace_Slam`) : effet d'immobilisation, lueur rouge `Dungeon_Goblin_Mace_Slam_Charge`, particules
  d'alerte au sol, puis frappe et temps de récupération.
- **Groupes** : `Nakasar_Domain_Undead` (morts-vivants du domaine), `Nakasar_Vampires` et `Nakasar_Ghosts` (`DisableDamageGroups`, ils ne se blessent pas entre eux),
  `Nakasar_Vampire_Spawns` (compté par le comte avant d'invoquer).
- **Apparence** : modèles humanoïdes sur le squelette du joueur (`Parent: Player`), vêtements vanilla du créateur de
  personnage recolorés et col victorien généré par `tools/generate_vampire_models.py` (modèles et texture dans
  `Common/NPC/Nakasar/Vampire/`, icônes d'effets dans `Common/UI/StatusEffects/Nakasar/`).
- **Butin** : éclats de rune ; le Comte et la Comtesse donnent aussi une des 4 runes du mod.
- **Apparition** : spawns de monde dans le pack Halloween (voir plus haut), et marqueurs `NPC/Spawn/Markers/Nakasar_Vampire_Count` (Comte ou Comtesse à poids égaux, réapparition 30 min) /
  `Nakasar_Vampire_Spawn` (5 min), posés via les blocs invisibles `Nakasar_Spawner_*`. Un marqueur fait apparaître
  un seul PNJ : `Nakasar_Zombie_Villager`, `_Zombie_Farmer`, `_Zombie_Rebel`, `_Skeleton_Guard` (10 min),
  `_Zombie_Abomination`, `_Guard_Captain` (30 min) et `Nakasar_Spider` (araignée ou araignée des cavernes, vanilla).
