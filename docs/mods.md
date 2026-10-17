# Conception des mods

## nakasar-runes (plugin Java + assets)

Tout est en JSON sauf trois interactions impossibles en pur asset, écrites en Java et enregistrées sous
les types `Nakasar_TeleportCasterToImpact`, `Nakasar_Dominate` et `Nakasar_RootNpc`.

Fichiers communs : `Server/Abilities/Keywords/Nakasar_*.json` (mots-clés affichés sur les runes),
`Server/Languages/{fr-FR,en-US}/nakasar_runes.lang` (noms et descriptions).

Chaque rune suit le schéma vanilla : objet `Rune_Nakasar_<X>` (`Ability.Slot: Core`, coût en mana,
cooldown, mots-clés, attributs) → `Root_Nakasar_Ability_<X>` → `Nakasar_Ability_<X>_Cast`
(`StatsCondition UseAbilityCost` → `Parallel` [ effet, `TriggerCooldown`, `ChangeStat` ]).

| Rune | Coût / CD | Portée | Effet |
|------|-----------|--------|-------|
| Baiser du Vampire (`Rune_Nakasar_VampireKiss`) | 30 mana / 4 s | mêlée (balayage horizontal 2,8 m) | 18 dégâts physiques (× attribut `Damage`), `EntityStatsOnHit Health +12` au lanceur (vol de vie, dégressif sur plusieurs cibles) |
| Domination (`Rune_Nakasar_Domination`) | 45 mana / 12 s | mêlée (estoc 3 m) | `Nakasar_Dominate` : attitude `FRIENDLY` forcée pendant `Duration` (6 s), effet visuel `Nakasar_Dominated` (teinte violette). PNJ uniquement |
| Téléportation (`Rune_Nakasar_Blink`) | 35 mana / 8 s | distance (projectile) | `Projectile_Config_Nakasar_Blink` ; à l'impact (entité ou terrain) `TriggerAbilityFX` puis `Nakasar_TeleportCasterToImpact` téléporte le lanceur 0,6 m en retrait du point d'impact |
| Chaînes spectrales (`Rune_Nakasar_SpectralChains`) | 40 mana / 10 s | distance (projectile) | `Projectile_Config_Nakasar_Chains` ; sur entité : FX « pointe de terre » bleutée, effet `Nakasar_Spectral_Chains` (`DisableAll`, attaques, abilities et esquive désactivées, knockback nul, particules `Stunned`) pendant `Duration` (3 s) + `Nakasar_RootNpc` (composant `Frozen`) pour les PNJ |

Attributs lisibles par les runes de support : `Damage` (Vampire), `Duration`
(Domination, Chaînes), `Speed` (projectiles).

### Autel sacrificiel (`Nakasar_Sacrificial_Altar`)

Objet-bloc (`Server/Item/Items/Bench/Nakasar/`) avec `BlockType.Bench` de type `Crafting`, id
`Nakasar_Sacrificial_Altar`, un seul onglet `Nakasar_Altar_Runes` et un seul palier. Le bloc déclare
`BlockType.State.Definitions` avec les états `CraftCompleted` et `CraftCompletedInstant` que la fenêtre de craft
bascule (`SimpleCraftingWindow`) ; c'est cet état de bloc qui lui donne une entité de bloc, sur laquelle
`BenchSystems` pose le composant `BenchBlock`. `DrawType: Model`, `VariantRotation: NESW` +
`RotationMode: FACING_PLAYER` (l'autel fait face au joueur), hitbox par défaut (cube plein : le modèle occupe
toute la hauteur du bloc), aucune contrainte de support (se pose comme un bloc plein), et il se redonne
lui-même à la casse (`Gathering.Breaking`).

Recettes dans `Server/Item/Recipes/Nakasar/` (fichiers séparés, voir README pour la raison) :
`Recipe_Nakasar_Sacrificial_Altar` à l'atelier de base `Workbench` / onglet `Workbench_Crafting` (10 `Rock`
ressource, 2 `Ingredient_Bar_Iron`, 1 `Ingredient_Rune_Shard`, 5 s) et `Recipe_Nakasar_Rune_<X>` sur l'autel,
onglet `Nakasar_Altar_Runes` (2 `Ingredient_Rune_Shard`, 1 s).

Modèle `Common/Blocks/Nakasar/Sacrificial_Altar.blockymodel` (3 boîtes, grille centrée, 32 unités = 1 bloc) :
socle 32×4×32 (y 0–4), pilier 16×20×16 (y 4–24), dalle 28×8×28 (y 24–32). Texture
`Common/BlockTextures/Nakasar/Sacrificial_Altar.png` (64×64), générée par script, disposition des UV :

| Zone (x, y, l×h) | Faces |
|------------------|-------|
| 0,0 32×32 | dessus / dessous du socle |
| 32,0 28×28 | dessus / dessous de la dalle (rigole et flaque de sang) |
| 32,28 16×16 | dessus / dessous du pilier |
| 0,32 32×4 | côtés du socle |
| 0,36 28×8 | côtés de la dalle (coulures) |
| 0,44 16×20 et 16,44 16×20 | faces avant/arrière et gauche/droite du pilier (runes rouges) |

Icônes `Common/Icons/Items/Nakasar/Sacrificial_Altar.png` (inventaire) et
`Common/Icons/CraftingCategories/Nakasar/Runes.png` (onglet), 64×64, générées par le même script.

### Interactions Java

- `TeleportCasterToImpactInteraction` : lit la position du projectile (ou `HIT_LOCATION`), recule de
  `BackOffset` vers le lanceur, ajoute `VerticalOffset`, pose un composant `Teleport` sur le lanceur.
- `DominateInteraction` : cible = PNJ avec `WorldSupport` ; `overrideAttitude(lanceur, attitude, durée)`
  ; applique `EffectId` si fourni. Clés JSON : `Duration`, `DurationAttribute`, `EffectId`, `Attitude`.
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
`BenchRequirement.Categories` liste `Sword`, `Weapon_Sword`, `Spear` et `Weapon_Spear` : seules les
catégories qui existent sur l'établi affichent la recette, les autres sont ignorées (voir README,
« Points à vérifier en jeu »).

### Réglages

Toutes les valeurs (dégâts, portées, durées, forces) sont dans les JSON cités ; aucun code.
