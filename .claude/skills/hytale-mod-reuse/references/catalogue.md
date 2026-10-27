# Catalogue des briques par besoin

État au 24 octobre 2026. L'index (`scripts/index_code.py`) fait foi : si une classe citée ici a bougé, la chercher
par son nom. F = `mods/nakasar-fractals/src/main/java/dev/nakasar/hytale/fractals/`,
V = `mods/nakasar-vampires/src/main/java/dev/nakasar/hytale/vampires/`.

## Combats : annonces, boss, serviteurs

| Besoin | Brique | Notes |
|---|---|---|
| Attaque annoncée au sol (cercle, cône, ligne, marque, colonne) à la taille exacte du coup | F `combat/TelegraphInteraction` + `Telegraphs` + `TelegraphSystem` (copie améliorée de V `telegraph/`) | Zones rouges = négatif uniquement. Particules de zones : `tools/generate_warnings.py` (F), `tools/tower_warnings.py` (V) |
| Charge annoncée en ligne | F `combat/ChargeInteraction` (copie de V `telegraph/ChargeInteraction`, l'Abomination) | |
| Attirer la cible vers le boss | F `combat/PullInteraction` | annonce par marque au-dessus de la tête |
| Boss étourdi (fenêtre de punition) | F `combat/BossStun`, `StunSelfInteraction` ; V `elite/EliteStun` | IA gelée via `Frozen` + effet étoiles |
| Barre de vie de boss à la Deepworks | F/V `boss/BossBarSystem` | `everywhere(role)` montre la barre à tout le monde du monde |
| PV selon la taille du groupe | F/V `GroupHealth` (V dans `tower/`) | × (1 + part par joueur de plus) |
| Vie fixée par le Java (ne baisse que par une mécanique) | F `boss/PinnedHealth` (`pin`, `noRegen`, `heal`) | dépend de `NPCPlugin.NPCEntityRegenerateStatsSystem`, pas du générique non enregistré |
| Barre de défiance (breakbar GW2) | F `defiance/` | |
| Invoquer des serviteurs, boss invulnérable tant qu'ils vivent | F/V `SummonMinionsInteraction` + `MinionShieldSystem` + `ShieldUnloadSystem` | serviteurs jamais sauvegardés ; invulnérabilité retirée au chargement. Lire avant de s'en servir pour « une seule vague » : `summonFirstWave` relance une vague au premier coup si aucune invocation n'est notée (`summonNow` n'en note pas), et un serviteur à plus de 36 blocs est retiré, ce qui lève le bouclier ; sinon s'inspirer du bouclier du Chaman (`snowblind/Shaman`) |
| Bouclier à compteur de coups | F `combat/HitShield` | |
| Soin de groupe d'un incantateur | F `combat/HealFoesInteraction` | |
| Camp d'ennemis qui ne se blessent pas entre eux | F `combat/Foes` ; V `allegiance/` (attitudes + filtre de dégâts) | |
| Filtre de dégâts d'une zone (avant armures) | F `stage/StageDamageFilter`, `cliffside/CliffsideDamageFilter` | modèle de filtre à copier |
| Mort d'un ennemi (après application des dégâts) | F `stage/FoeDeathSystem` | groupe d'inspection : la vie lue est déjà diminuée |
| Effet de zone sur les ennemis du lanceur seulement | V `elite/ApplyEffectToFoesInteraction` | |
| Faiblesse/immunité au feu par groupe | V `elite/FireAffinitySystem` | |
| Agonie (% PV max par seconde) | F `progress/Agony`, `AgonySystem` | |
| Polarités, consoles simultanées | F `combat/Polarity`, `arena/Consoles` | |
| Envoyer un joueur en cage / en cellule | F `prison/CagePlayerInteraction`, `cliffside/Cages` ; V `prison/ImprisonPlayerInteraction` | |
| Piège racines qui immobilise | V `pumpkin/RootTrapInteraction` (+ `RootTrapUnloadSystem`) | composant sans codec : jamais sauvegardé |
| Faire fuir/éviter une zone aux PNJ | V `purifying/PurifyingSteeringSystem` | modifier le steering, pas de knockback (Kevin) |
| Déroulé de rencontre par étapes, 4 fois/s | F `stage/FractalStage`, `StageSystem`, `Stages` | modèle des fractales après la Falaise |
| Barrière d'arène qui se ferme quand on entre | V `tower/ArenaGate` ; F `arena/Gates` | |
| Apparitions non sauvegardées, PV selon groupe et niveau | F `combat/Spawns` | |

## Objets portés, blocs utilisables, décor vivant

| Besoin | Brique | Notes |
|---|---|---|
| Objet de mécanique ramassé accroupi et gardé en main | F `arena/CrouchPickup.register(Item)` + `arena/HandLock` | jamais deux instances du même système |
| Objet porté dans l'inventaire et consommé | F `arena/Carried` | comparer par id, jamais `canRemoveItemStack` (durabilité) |
| Lancer l'objet tenu sur un PNJ | F `stage/ThrowItemInteraction` | |
| Bloc utilisable (levier, console, pupitre) | F `stage/StageUseInteraction`, `observatory/PlayerInteraction` | dans nos instances, les coups sur bloc ne déclenchent rien : passer par Use |
| Changer des blocs du monde depuis le Java | F/V `arena/WorldBlocks` | |
| Remettre en place un décor abîmé (survit aux redémarrages) | F/V `arena/Restores` | |
| Décor d'arène réactif (porte de cellule, cloche, lanternes, braseros, poteaux) | V `arena/ArenaBlocks` + `BarnPosts`, `Braziers` | n'agit qu'à < 40 d'un `Nakasar_Arena_Marker` |
| Retour au dernier sol sûr après une chute | F `arena/SafeLandings`, `party/FallRescueSystem` ; V `tower/TowerFallSystem` | |
| Récompense un coffre par joueur, sac à ouvrir | F `party/ClaimRewardInteraction`, `progress/OpenBagInteraction` ; V `contract/OpenBountyBagInteraction` | |
| Lumière vue par un seul joueur | V `vampirism/PrivateNightLightSystem` | `DynamicLight` est diffusé à tous |
| Invisibilité | V `invisibility/` | |
| Évènement de monde (nuit, brèche) | V `breach/` | voir mémoire `hytale-world-events` |

## Générateurs Python

| Besoin | Module | Fonctions clés |
|---|---|---|
| Bruit lisse, arbres, buissons, rochers, fleurs, îles, bordures naturelles | `nakasar-fractals/tools/fractal_nature.py` | `fbm2`, `vnoise3`, `broadleaf`, `conifer`, `dead_tree`, `boulder`, `flora`, `dress`, `rim`, `natural_ground`, `island`, `islet`, `scatter_islets`, THEMES |
| Passerelles courbes, éperon rocheux naturel | `nakasar-fractals/tools/generate_cliffside.py` | `curve_walkways`, `buttress_rock` |
| Prefab en tronçons, biome, instance, ciel, rôles fixes, effets, aperçu de dessus | `nakasar-fractals/tools/fractal_common.py` | `split_sections`, `write_instance`, `weather`, `static_role`, `effect`, `top_view`, `pick` (bruit sans damier) |
| Classe Prefab, bâtiments, mobilier, toits, clôtures, arbres morts, contrôle des blocs flottants | `nakasar-vampires/tools/generate_prefabs.py` | `Prefab`, `house`, `roof`, `fence_rect`, `dead_tree`, `floating_blocks`, `is_connected`, `stairs_up/down` |
| Worldgen HytaleGenerator (biomes, emplacements, bruit global) | `nakasar-vampires/tools/generate_worldgen.py` | `layout_value`, `slot_positions`, `distance_to` (Y = 81 !) |
| Bloc en modèle 3D (DrawType Model), textures peintes, icône rendue | `nakasar-fractals/tools/fractal_blocks.py` | `planks`, `stone`, `metal`, `crystal`, `glass`, `cloth`, `build_model`, `render`, `write_block_model` |
| Objet tenu en main (format prop) | `fractal_models.py` + `generate_item_models.py` | `write_item_model` |
| PNJ animé (squelette, .blockyanim, attaques) | `nakasar-fractals/tools/fractal_anim.py` (copie de V `generate_pumpkin_models.py`) | `build`, `keys`, `item_animations` |
| PNJ humanoïde sur le rig Player + vêtements | V `tools/generate_vampire_models.py`, mémoire `hytale-npc-models` | |
| Rôles de PNJ et attaques | `nakasar-fractals/tools/fractal_roles.py` (copie de V `generate_elites.py`) | |
| Particules et effets de lecture | V `tools/tower_fx.py`, `elite_fx.py`, `make_particle_textures.py` | |
| Butin, sacs, wiki | V `generate_loot.py`, `generate_wiki_loot.py`, `render_wiki_portraits.py` | |
