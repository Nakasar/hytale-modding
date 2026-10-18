# Conception du mod Vampires

Un seul mod, `mods/nakasar-vampires` (plugin Java `dev.nakasar.hytale.vampires.VampiresPlugin` + pack d'assets
embarqué dans le jar, manifest `Nakasar:Vampires`). Il réunit ce qui était auparavant quatre mods (Runes, Spear,
Mobs, Halloween) ; les ids d'assets n'ont pas changé (préfixe `Nakasar_`, fichiers de langue `nakasar_runes`,
`nakasar_spear`, `nakasar_mobs`, `nakasar_halloween`), donc les mondes et prefabs existants restent valides.
Validation hors jeu : `./gradlew :mods:nakasar-vampires:check` (rôles avec `tools/ValidateRoles.java`, tous les
autres assets avec `tools/ValidateAssets.java`).

## Runes et autel

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
`mods/nakasar-vampires/tools/generate_altar.py` (relancer le script après toute retouche, `--preview DOSSIER`
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
  Avec une attitude amicale (`Friendly`, défaut), le PNJ change aussi de camp (voir « Camps et Domination »).
- `DrainBeamInteraction` : joue `SystemId` (`ParticleUtil.spawnParticleEffect`) sur `Steps` points entre la
  cible et le lanceur, un pas toutes les `StepDelay` s (`world.scheduleAfter`), à `HeightOffset` au-dessus des pieds.
- `RootNpcInteraction` : ajoute `Frozen` à la cible PNJ et programme son retrait (`world.scheduleAfter`)
  ; une seconde application prolonge la durée, et un PNJ déjà gelé par quelqu'un d'autre (`/npc freeze`) n'est pas touché. Clés : `Duration`, `DurationAttribute`.

## Lance

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

## Fragment Halloween (« Comté Vampire »)

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
- **Structures (domaine du Comte)** : quatorze emplacements fixes (`SLOTS`, trois grands pour le
  village), décalés d'au plus 16 blocs selon la graine du monde (`Jitter2d`). Le type de chaque
  emplacement change d'un monde à l'autre : huit répartitions sont tirées une fois par le script
  (`layouts()`, le village toujours sur un grand emplacement, deux structures du même type à plus
  de 140 blocs), et le monde en choisit une selon un bruit lu en un point fixe (`XOverride` /
  `ZOverride`, donc une valeur par graine). Le premier exemplaire de chaque type est toujours là, le
  second une fois sur deux (bruit propre à l'emplacement) : 0 ou 1 village (60 %), 0 ou 1 camp de
  chasseurs de vampires (50 %, toujours sur le 14e emplacement, en 20 / 110 : il ne fait que
  25 × 25 et c'est le seul type qui y tient sans chevaucher ses voisins), 1 ou 2 fermes,
  postes de garde, cimetières, cryptes, champs de citrouilles et châteaux hantés, toujours un seul
  manoir. Au moins 9 blocs entre deux structures dans le pire décalage. La variante (village
  zombies / ruines / araignées, etc.) et l'orientation sont tirées au hasard.
- **Manoir du comte** : toujours à 220 blocs au nord du point d'apparition (objectif du portail).
- **Arrivée** : `PortalTypes/Nakasar_Halloween` fixe le point d'apparition (`Spawn.SpawnProviderOverride`,
  fournisseur `Global`) en 0,5 / 81 / 0,5 ; sans lui, le jeu tire un point au hasard dans le tronçon
  (x et z entre 2 et 13). Le joueur apparaît au centre de la crypte d'arrivée (`SpawnCrypt`) posée au
  même endroit. Le portail de retour (`Portal_Return`) fait partie de la crypte, 3 blocs au sud
  (`Spawn.SpawnReturnPortal: false`) : posé par le jeu, il tomberait sur le point d'arrivée, et le
  portail renvoie dans le monde normal tout joueur présent depuis plus de 15 secondes, donc aussi
  celui dont l'écran a chargé lentement (écran noir puis retour, vu en jeu le 2026-10-18).
- **Coût de génération** : les distances aux structures et au manoir (relief, ambiance) ne dépendent
  pas de la hauteur ; elles sont calculées une fois par colonne (`YOverride` à 81 puis `Cache`) et les
  positions exportées sont mémorisées par sections (`Cache` de positions). Calculées bloc par bloc,
  elles retardaient l'ouverture du portail d'une trentaine de secondes.
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

### Prefabs (`tools/generate_prefabs.py`, 69 fichiers)

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
| `PumpkinFields/{Plain,Giant}` | 3 + 2 | Champ de citrouilles mûres (états de culture) clôturé de bois mort : allée à lanternes, épouvantails, charrette de récolte, meules de foin, cabane, arbre de pendu. Variante `Giant` (une fois sur deux) : clairière de terre pourrie de rayon 7 au centre (portée des attaques en cercle), bordée de ronces, de citrouilles entières et de citrouilles sculptées, avec le bloc d'apparition de la citrouille géante (élite immobile) |
| `HunterCamps/{Tents,Lodge}` | 2 | Camp de chasseurs de vampires 25×25 clos d'une palissade de troncs, portail de bois au sud (les chasseurs ne sortent pas) : feu de camp et tabourets, trois tentes de cuir (ou un pavillon de rondins et une tente) au nord, atelier d'armes et armurerie à l'ouest, pas de tir (cibles, mannequins) à l'est, réserve ; six blocs d'apparition de chasseurs à moins de 9 blocs du centre |
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
cuisine, chambres, atelier ; camp de chasseurs (vivres, flèches, potions, argent) et son armurerie. Objets du jeu 0.7.2 (vérifiés dans `Server/Item/Items`).

Blocs des mobs posés dans les prefabs : spawners `Nakasar_Spawner_Zombie_Villager`,
`_Zombie_Farmer`, `_Zombie_Abomination` (élite, un par ferme zombie), `_Zombie_Rebel`,
`_Skeleton_Guard`, `_Guard_Captain` (élite, un par garnison), `_Spider`, `_Giant_Pumpkin` (élite, au centre
des champs `Giant`), `_Vampire_Hunter` (six par camp de chasseurs), et `Nakasar_Prison_Cell`
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
- Mobs du mod : fantômes à toute heure et rejetons de vampire la nuit
  (`Nakasar_Halloween_Ghosts`, `Nakasar_Halloween_Vampire_Spawns_Dusk` / `_Dawn`, environnement hanté), et
  marqueurs d'apparition dans le manoir du comte (le Comte ou la Comtesse devant le trône, une chance sur deux, deux rejetons dans la crypte).

## Mobs

Les boss réutilisent les interactions et particules des runes.

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
| `Nakasar_Giant_Pumpkin` | 600 | Élite du champ de citrouilles (citrouille sculptée vanilla ×4), immobile. Coup de vrille devant elle (18, 4,5 blocs) ; trois épines (9 chacune, 18 blocs, toutes les 2,5 à 3,5 s) ; crachat de poison orange (8 + poison 4/s pendant 6 s, 16 blocs, 6 à 8 s) ; Balayage annoncé (zone rouge de 5 blocs pendant 1,2 s, 26 dégâts et projection, 8 à 11 s) ; Piège de vrilles annoncé (zone rouge de 6,5 blocs qui se charge 2,2 s, 16 à 20 s) : chaque ennemi resté dedans est retenu par une `Nakasar_Pumpkin_Tendril` (12 PV) à ses pieds jusqu'à ce qu'elle soit détruite (20 s au plus). Elle et ses vrilles prennent double dégâts de feu. Se rendort et regagne sa vie si la cible s'éloigne à plus de 20 blocs. |
| `Nakasar_Vampire_Hunter_Crossbow` | 160 | Chasseuse de vampires, arbalète (carreaux 16, 18 blocs). |
| `Nakasar_Vampire_Hunter_Gunner` | 170 | Chasseur de vampires, tromblon (balles 22, 14 blocs, lent). |
| `Nakasar_Vampire_Hunter_Blade` | 200 | Chasseur de vampires, épée d'argent vanilla (`Weapon_Sword_Silversteel`), mêlée 20. |

- **Domination** (Java, `domination/`) : l'interaction `Nakasar_DominatePlayer` enregistre « ce joueur est
  dominé par ce PNJ » pendant `Duration` secondes et applique l'effet `Nakasar_Count_Domination`. Le système
  `AllegianceDamageFilter` (groupe de filtrage des dégâts) annule tout dégât de ce joueur, projectiles
  compris, contre ce PNJ tant que l'effet dure.
- **Emprisonnement** (Java, `prison/`) : l'interaction `Nakasar_ImprisonPlayer` cherche le bloc invisible
  `Nakasar_Prison_Cell` le plus proche du capitaine (24 blocs, sous la portée de 32 blocs où il abandonne sa cible) et y téléporte le joueur, puis applique
  `Nakasar_Imprisoned` (ralenti 5 s). Le bloc se pose au niveau des pieds dans la cellule, bloc du dessus libre.
  Sans cellule à portée, seul l'effet s'applique.
- **Attaques annoncées** (abomination, capitaine) : même schéma que les gobelins du donjon Deepworks
  (`Dungeon_Goblin_Mace_Slam`) : effet d'immobilisation, lueur rouge `Dungeon_Goblin_Mace_Slam_Charge`, particules
  d'alerte au sol, puis frappe et temps de récupération.
- **Piège de vrilles** (Java, `pumpkin/RootTrapInteraction`) : l'interaction `Nakasar_RootTrap`, lancée sur chaque
  entité du cercle (`Selector` `AOECircle`), fait apparaître le PNJ `Nakasar_Pumpkin_Tendril` à ses pieds (après
  le tick, `NPCPlugin.spawnNPC`) et l'immobilise : effet `Nakasar_Tendril_Rooted` (`DisableAll`) pour un joueur,
  composant `Frozen` pour un PNJ. Toutes les 250 ms on vérifie la vrille : morte ou disparue, la victime est libérée ;
  au bout de 20 s la vrille est retirée. L'immobilisation est reconduite à chaque vérification (effet d'1 s pour un
  joueur, gel reposé s'il a été retiré). La vrille n'est pas sauvegardée ; une victime qui quitte le monde en plein
  piège perd le gel posé par le piège (`RootTrapped` + `RootTrapUnloadSystem`). Les alliés de la citrouille (camp du
  fragment, ou sous Domination son maître et les PNJ du même maître) et les vrilles sont épargnés.
- **Faiblesse au feu** (Java, `pumpkin/FireWeaknessSystem`) : dans le groupe de filtrage des dégâts, après
  `AllegianceDamageFilter`, les dégâts de cause `Fire` (ou qui en hérite) sur un membre de `Nakasar_Pumpkin_Patch`
  sont doublés.
- **Chasseurs de vampires** : `DefaultPlayerAttitude: Neutral`, ils ne ripostent que si on les frappe (capteur
  `Damage`) et oublient le joueur une fois revenus au camp. Ennemis jurés des mobs du fragment (voir Camps). Ils ne
  s'éloignent jamais à plus de 14 blocs de leur poste (capteur `Leash` en combat : ils lâchent la cible et
  reviennent, puis regagnent leur vie). Tenues de cuir « chasseur de démons » (chapeaux, longs manteaux, masque,
  bandoulière) en vêtements vanilla. Carreaux et balles : `Projectiles/Nakasar/`.
- **Groupes** : `Nakasar_Domain_Undead` (morts-vivants du domaine), `Nakasar_Vampires` et `Nakasar_Ghosts` (`DisableDamageGroups`, ils ne se blessent pas entre eux),
  `Nakasar_Vampire_Spawns` (compté par le comte avant d'invoquer), `Nakasar_Pumpkin_Patch` (citrouille géante et
  vrilles : faiblesse au feu), `Nakasar_Vampire_Hunters` (ne se blessent pas entre eux), `Nakasar_Halloween_Faction`
  (tous les mobs du fragment, voir ci-dessous).
- **Apparence** : modèles humanoïdes sur le squelette du joueur (`Parent: Player`), vêtements vanilla du créateur de
  personnage recolorés et col victorien généré par `tools/generate_vampire_models.py` (modèles et texture dans
  `Common/NPC/Nakasar/Vampire/`, icônes d'effets dans `Common/UI/StatusEffects/Nakasar/`).
- **Butin** : éclats de rune ; le Comte et la Comtesse donnent aussi une des 4 runes du mod.
- **Apparition** : spawns de monde dans le pack Halloween (voir plus haut), et marqueurs `NPC/Spawn/Markers/Nakasar_Vampire_Count` (Comte ou Comtesse à poids égaux, réapparition 30 min) /
  `Nakasar_Vampire_Spawn` (5 min), posés via les blocs invisibles `Nakasar_Spawner_*`. Un marqueur fait apparaître
  un seul PNJ : `Nakasar_Zombie_Villager`, `_Zombie_Farmer`, `_Zombie_Rebel`, `_Skeleton_Guard` (10 min),
  `_Zombie_Abomination`, `_Guard_Captain`, `_Giant_Pumpkin` (30 min), `Nakasar_Spider` (araignée ou araignée des
  cavernes, vanilla) et `Nakasar_Vampire_Hunter` (un chasseur tiré au hasard : arbalète 4, tromblon 3, épée 3 ;
  20 min).

## Camps et Domination

Java, `allegiance/` et `domination/`. Les mobs du fragment (groupe `Nakasar_Halloween_Faction` : les trois groupes
du mod et les mobs vanilla de ses apparitions) forment un seul camp ; la Domination fait changer de camp un PNJ le
temps de son effet.

- **Attitudes** (`AllegianceAttitudeSystem`) : deux fournisseurs ajoutés à l'`AttitudeView` des PNJ, comme le
  module de réputation du jeu. Priorité -10 (avant les `OverrideAttitude` des rôles, priorité 0) : un PNJ dominé
  est `Friendly` envers son dominateur et les autres PNJ du même dominateur, `Hostile` envers ses anciens alliés,
  qui le voient aussi `Hostile`. Priorité 140 : un chasseur de vampires (`Nakasar_Vampire_Hunters`) et un membre
  du camp sont `Hostile` l'un envers l'autre ; leurs capteurs `Mob` (filtre `Attitude: Hostile`) les lancent au
  combat à vue. Priorité 150 (après la lignée d'apparition, avant les groupes d'attitude des
  rôles) : deux membres du camp sont `Friendly`. Anciens alliés : deux membres du camp, ou deux PNJ dont le rôle
  est amical envers l'autre dans les groupes d'attitude du jeu (`AttitudeMap`). Les PNJ gardent leurs attitudes
  en cache 0,1 s.
- **Rôles du mod** : en plus du capteur `Player`, l'état `Idle` a un capteur `Mob` (même portée, filtre
  `Attitude: Hostile`) qui passe en combat ; en combat, la cible est relâchée si elle sort de portée **ou devient
  amicale** (filtre `Attitude: Hostile/Neutral/Ignore` sur le test de perte de cible). Hors Domination, aucun mob
  du camp n'est hostile à un autre : rien ne change.
- **Dégâts** (`AllegianceDamageFilter`, groupe de filtrage, juste après le filtre des rôles
  `NPCDamageSystems.FilterDamageSystem` et avant `FilterUnkillable` / `FilterNPCWorldConfig`) : une victime de la
  Domination ne blesse pas son dominateur ; un PNJ dominé et un ancien allié se blessent de nouveau (on lève
  l'annulation posée par `DisableDamageGroups`, seulement quand c'est elle qui a annulé) ; deux membres du camp en
  paix ne se blessent pas (flèche perdue, coup de zone).
- **Fin de l'effet** (`DominationExpirySystem`) : le PNJ libéré oublie les cibles prises parmi ses anciens alliés
  (emplacements de `MarkedEntitySupport`) ; utile pour les mobs vanilla, dont on ne contrôle pas les rôles.
- La Domination du Comte sur un joueur ne change que les dégâts du joueur contre le Comte.
