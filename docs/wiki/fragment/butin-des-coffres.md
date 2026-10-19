# Butin des coffres

{/* Page générée par mods/nakasar-vampires/tools/generate_wiki_loot.py : ne pas modifier à la main. */}

Chaque coffre du Comté est rempli à l'apparition de la structure. Son contenu se compose de plusieurs **tirages** : chacun est fait un nombre de fois aléatoire, et à chaque fois un objet est choisi selon sa chance. Les noms des objets du jeu de base sont des traductions d'usage ; l'id exact est indiqué entre parenthèses.

| Coffre | Où |
|---|---|
| [Trésor du manoir](#tresor-du-manoir) | [Manoir du Comte](manoir-du-comte.md), crypte |
| [Chambre du manoir](#chambre-du-manoir) | [Manoir du Comte](manoir-du-comte.md), chambres du comte et de la comtesse |
| [Alchimie du manoir](#alchimie-du-manoir) | [Manoir du Comte](manoir-du-comte.md), laboratoire |
| [Bibliothèque du manoir](#bibliotheque-du-manoir) | [Manoir du Comte](manoir-du-comte.md), bibliothèque |
| [Atelier du manoir](#atelier-du-manoir) | [Manoir du Comte](manoir-du-comte.md), atelier |
| [Cuisine du manoir](#cuisine-du-manoir) | [Manoir du Comte](manoir-du-comte.md), cuisine |
| [Quartiers du capitaine](#quartiers-du-capitaine) | [Poste de garde](postes-de-garde.md) |
| [Armurerie](#armurerie) | [Poste de garde](postes-de-garde.md) |
| [Caserne](#caserne) | [Poste de garde](postes-de-garde.md) |
| [Ruines du château](#ruines-du-chateau) | [Château hanté](chateaux-hantes.md), chambre du donjon |
| [Crypte](#crypte) | [Crypte](cryptes.md), salle funéraire |
| [Maison du notable](#maison-du-notable) | [Village](villages.md), maison du notable |
| [Maison du village](#maison-du-village) | [Village](villages.md), 9 coffres |
| [Ferme](#ferme) | [Fermes](fermes.md) (zombies, en ruine) et [champs de citrouilles](champs-de-citrouilles.md) |
| [Ferme incendiée](#ferme-incendiee) | [Ferme](fermes.md) incendiée |
| [Camp de chasseurs](#camp-de-chasseurs) | [Camp de chasseurs](camps-de-chasseurs.md), tente ou pavillon |
| [Armurerie des chasseurs](#armurerie-des-chasseurs) | [Camp de chasseurs](camps-de-chasseurs.md), atelier |

## Trésor du manoir {#tresor-du-manoir}

[Manoir du Comte](manoir-du-comte.md), crypte · liste `Nakasar_Loot_Manor_Treasure`

**Tirage 1** (2 à 4 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Lingot d'or (`Ingredient_Bar_Gold`) | 2 à 5 | 19 % |
| **Lingot d'argent** (`Ingredient_Bar_Silver`) | 2 à 6 | 19 % |
| Rubis (`Rock_Gem_Ruby`) | 1 à 3 | 19 % |
| **Relique du manoir** (`Ingredient_Nakasar_Manor_Relic`) | 1 à 2 | 14 % |
| Émeraude (`Rock_Gem_Emerald`) | 1 à 2 | 10 % |
| Saphir (`Rock_Gem_Sapphire`) | 1 à 2 | 10 % |
| Diamant (`Rock_Gem_Diamond`) | 1 | 5 % |
| Pierre du Vide (`Rock_Gem_Voidstone`) | 1 | 5 % |

**Tirage 2** (1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| **Arc court vampirique** (`Weapon_Shortbow_Vampire`) | 1 | 18 % |
| **Épée en acier d'argent** (`Weapon_Sword_Silversteel`) | 1 | 18 % |
| Plastron de corbeau (`Armor_Leather_Raven_Chest`) | 1 | 18 % |
| Capuche de corbeau (`Armor_Leather_Raven_Head`) | 1 | 18 % |
| **Épée longue spectrale** (`Weapon_Longsword_Spectral`) | 1 | 9 % |
| Dagues maudites (`Weapon_Daggers_Doomed`) | 1 | 9 % |
| Plastron en acier ancien (`Armor_Steel_Ancient_Chest`) | 1 | 9 % |

**Tirage 3** (1 à 2 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Potion de soin (`Potion_Health`) | 1 à 2 | 43 % |
| Potion de régénération (`Potion_Regen_Health`) | 1 | 29 % |
| Potion de poison (`Potion_Poison`) | 1 à 2 | 29 % |

**Tirage 4** (0 à 1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| *rien* | | 38 % |
| Note : [Journal du Comte](notes-et-epitaphes.md) (`Nakasar_Lore_Count_Journal`) | 1 | 12 % |
| Note : [Lettre de la Comtesse](notes-et-epitaphes.md) (`Nakasar_Lore_Countess_Letter`) | 1 | 12 % |
| Note : [Règles de la maison](notes-et-epitaphes.md) (`Nakasar_Lore_Servant_Rules`) | 1 | 12 % |
| Note : [Page de rituel](notes-et-epitaphes.md) (`Nakasar_Lore_Ritual_Page`) | 1 | 12 % |
| Note : [Le pacte](notes-et-epitaphes.md) (`Nakasar_Lore_Blood_Pact`) | 1 | 12 % |

## Chambre du manoir {#chambre-du-manoir}

[Manoir du Comte](manoir-du-comte.md), chambres du comte et de la comtesse · liste `Nakasar_Loot_Manor_Bedroom`

**Tirage 1** (1 à 3 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Rouleau de soie (`Ingredient_Bolt_Silk`) | 1 à 3 | 25 % |
| Rouleau de laine (`Ingredient_Bolt_Wool`) | 1 à 3 | 25 % |
| Chute de soie (`Ingredient_Fabric_Scrap_Silk`) | 2 à 5 | 25 % |
| Rouleau de tisse-ombre (`Ingredient_Bolt_Shadoweave`) | 1 | 8 % |
| Tunique en cuir souple (`Armor_Leather_Soft_Chest`) | 1 | 8 % |
| Capuche en cuir souple (`Armor_Leather_Soft_Head`) | 1 | 8 % |

**Tirage 2** (1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| **Lingot d'argent** (`Ingredient_Bar_Silver`) | 1 à 3 | 27 % |
| Lingot d'or (`Ingredient_Bar_Gold`) | 1 à 2 | 18 % |
| Rubis (`Rock_Gem_Ruby`) | 1 à 2 | 18 % |
| Topaze (`Rock_Gem_Topaz`) | 1 à 2 | 18 % |
| Saphir (`Rock_Gem_Sapphire`) | 1 | 9 % |
| Émeraude (`Rock_Gem_Emerald`) | 1 | 9 % |

**Tirage 3** (0 à 1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| *rien* | | 60 % |
| Potion de régénération (`Potion_Regen_Health`) | 1 | 20 % |
| Dagues en fer (`Weapon_Daggers_Iron`) | 1 | 20 % |

**Tirage 4** (0 à 1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| *rien* | | 44 % |
| Note : [Journal du Comte](notes-et-epitaphes.md) (`Nakasar_Lore_Count_Journal`) | 1 | 11 % |
| Note : [Lettre de la Comtesse](notes-et-epitaphes.md) (`Nakasar_Lore_Countess_Letter`) | 1 | 11 % |
| Note : [Règles de la maison](notes-et-epitaphes.md) (`Nakasar_Lore_Servant_Rules`) | 1 | 11 % |
| Note : [Page de rituel](notes-et-epitaphes.md) (`Nakasar_Lore_Ritual_Page`) | 1 | 11 % |
| Note : [Le pacte](notes-et-epitaphes.md) (`Nakasar_Lore_Blood_Pact`) | 1 | 11 % |

## Alchimie du manoir {#alchimie-du-manoir}

[Manoir du Comte](manoir-du-comte.md), laboratoire · liste `Nakasar_Loot_Manor_Alchemy`

**Tirage 1** (2 à 4 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Fiole vide (`Potion_Empty`) | 1 à 4 | 13 % |
| Essence de vie (`Ingredient_Life_Essence`) | 2 à 6 | 13 % |
| Potion de soin (`Potion_Health`) | 1 à 2 | 10 % |
| Potion de régénération (`Potion_Regen_Health`) | 1 | 7 % |
| Potion de poison (`Potion_Poison`) | 1 à 2 | 7 % |
| Antidote (`Potion_Antidote`) | 1 à 2 | 7 % |
| Potion de mana (`Potion_Mana`) | 1 à 2 | 7 % |
| Cristal rouge (`Ingredient_Crystal_Red`) | 1 à 3 | 7 % |
| Cristal violet (`Ingredient_Crystal_Purple`) | 1 à 2 | 7 % |
| Fruit empoisonné (`Plant_Fruit_Poison`) | 1 à 3 | 7 % |
| Fragment d'os (`Ingredient_Bone_Fragment`) | 2 à 5 | 7 % |
| **Éclat de rune** (`Ingredient_Rune_Shard`) | 1 à 2 | 7 % |
| **Relique du manoir** (`Ingredient_Nakasar_Manor_Relic`) | 1 | 3 % |

**Tirage 2** (0 à 1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| *rien* | | 40 % |
| Recette : graines de soin (`Recipe_Plant_Seeds_Health1`) | 1 | 20 % |
| Recette : graines de mana (`Recipe_Plant_Seeds_Mana1`) | 1 | 20 % |
| Recette : graines d'endurance (`Recipe_Plant_Seeds_Stamina1`) | 1 | 20 % |

**Tirage 3** (0 à 1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| *rien* | | 44 % |
| Note : [Journal du Comte](notes-et-epitaphes.md) (`Nakasar_Lore_Count_Journal`) | 1 | 11 % |
| Note : [Lettre de la Comtesse](notes-et-epitaphes.md) (`Nakasar_Lore_Countess_Letter`) | 1 | 11 % |
| Note : [Règles de la maison](notes-et-epitaphes.md) (`Nakasar_Lore_Servant_Rules`) | 1 | 11 % |
| Note : [Page de rituel](notes-et-epitaphes.md) (`Nakasar_Lore_Ritual_Page`) | 1 | 11 % |
| Note : [Le pacte](notes-et-epitaphes.md) (`Nakasar_Lore_Blood_Pact`) | 1 | 11 % |

## Bibliothèque du manoir {#bibliotheque-du-manoir}

[Manoir du Comte](manoir-du-comte.md), bibliothèque · liste `Nakasar_Loot_Manor_Library`

**Tirage 1** (1 à 3 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Page de recette (`Recipe_Page`) | 1 à 2 | 36 % |
| Carte (`Tool_Map`) | 1 | 14 % |
| Recette : tourte à la viande (`Recipe_Food_Pie_Meat`) | 1 | 7 % |
| Recette : tarte à la citrouille (`Recipe_Food_Pie_Pumpkin`) | 1 | 7 % |
| Recette : graines de soin (`Recipe_Plant_Seeds_Health1`) | 1 | 7 % |
| Recette : graines de mana (`Recipe_Plant_Seeds_Mana1`) | 1 | 7 % |
| Recette : graines d'endurance (`Recipe_Plant_Seeds_Stamina1`) | 1 | 7 % |
| Grimoire violet (`Weapon_Spellbook_Grimoire_Purple`) | 1 | 7 % |
| Grimoire brun (`Weapon_Spellbook_Grimoire_Brown`) | 1 | 7 % |

**Tirage 2** (0 à 1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| *rien* | | 17 % |
| Fiole vide (`Potion_Empty`) | 1 à 4 | 11 % |
| Essence de vie (`Ingredient_Life_Essence`) | 2 à 6 | 11 % |
| Potion de soin (`Potion_Health`) | 1 à 2 | 8 % |
| Potion de régénération (`Potion_Regen_Health`) | 1 | 6 % |
| Potion de poison (`Potion_Poison`) | 1 à 2 | 6 % |
| Antidote (`Potion_Antidote`) | 1 à 2 | 6 % |
| Potion de mana (`Potion_Mana`) | 1 à 2 | 6 % |
| Cristal rouge (`Ingredient_Crystal_Red`) | 1 à 3 | 6 % |
| Cristal violet (`Ingredient_Crystal_Purple`) | 1 à 2 | 6 % |
| Fruit empoisonné (`Plant_Fruit_Poison`) | 1 à 3 | 6 % |
| Fragment d'os (`Ingredient_Bone_Fragment`) | 2 à 5 | 6 % |
| **Éclat de rune** (`Ingredient_Rune_Shard`) | 1 à 2 | 6 % |
| **Relique du manoir** (`Ingredient_Nakasar_Manor_Relic`) | 1 | 3 % |

**Tirage 3** (0 à 1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| *rien* | | 29 % |
| Note : [Journal du Comte](notes-et-epitaphes.md) (`Nakasar_Lore_Count_Journal`) | 1 | 14 % |
| Note : [Lettre de la Comtesse](notes-et-epitaphes.md) (`Nakasar_Lore_Countess_Letter`) | 1 | 14 % |
| Note : [Règles de la maison](notes-et-epitaphes.md) (`Nakasar_Lore_Servant_Rules`) | 1 | 14 % |
| Note : [Page de rituel](notes-et-epitaphes.md) (`Nakasar_Lore_Ritual_Page`) | 1 | 14 % |
| Note : [Le pacte](notes-et-epitaphes.md) (`Nakasar_Lore_Blood_Pact`) | 1 | 14 % |

## Atelier du manoir {#atelier-du-manoir}

[Manoir du Comte](manoir-du-comte.md), atelier · liste `Nakasar_Loot_Manor_Workshop`

**Tirage 1** (2 à 3 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Lingot de fer (`Ingredient_Bar_Iron`) | 2 à 5 | 21 % |
| Lingot de cuivre (`Ingredient_Bar_Copper`) | 2 à 5 | 16 % |
| Cuir moyen (`Ingredient_Leather_Medium`) | 1 à 4 | 16 % |
| Charbon de bois (`Ingredient_Charcoal`) | 2 à 6 | 16 % |
| **Lingot d'argent** (`Ingredient_Bar_Silver`) | 1 à 3 | 11 % |
| Kit de réparation en fer (`Tool_Repair_Kit_Iron`) | 1 | 11 % |
| Cuir sombre (`Ingredient_Leather_Dark`) | 1 à 2 | 5 % |
| Marteau en fer (`Tool_Hammer_Iron`) | 1 | 5 % |

**Tirage 2** (0 à 1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| *rien* | | 24 % |
| Épée en acier rouillée (`Weapon_Sword_Steel_Rusty`) | 1 | 12 % |
| Hache en fer rouillée (`Weapon_Axe_Iron_Rusty`) | 1 | 12 % |
| Casque en fer (`Armor_Iron_Head`) | 1 | 8 % |
| Gants en fer (`Armor_Iron_Hands`) | 1 | 8 % |
| Jambières en fer (`Armor_Iron_Legs`) | 1 | 8 % |
| Plastron en cuir (`Armor_Leather_Medium_Chest`) | 1 | 8 % |
| Casque en cuir (`Armor_Leather_Medium_Head`) | 1 | 8 % |
| Gourdin en fer rouillé (`Weapon_Club_Iron_Rusty`) | 1 | 8 % |
| Plastron en fer (`Armor_Iron_Chest`) | 1 | 4 % |

## Cuisine du manoir {#cuisine-du-manoir}

[Manoir du Comte](manoir-du-comte.md), cuisine · liste `Nakasar_Loot_Manor_Kitchen`

**Tirage 1** (2 à 4 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Tourte à la viande (`Food_Pie_Meat`) | 1 à 2 | 18 % |
| Tarte aux pommes (`Food_Pie_Apple`) | 1 à 2 | 18 % |
| Fromage (`Food_Cheese`) | 1 à 3 | 18 % |
| Pain (`Food_Bread`) | 2 à 4 | 18 % |
| Brochette de viande (`Food_Kebab_Meat`) | 1 à 3 | 12 % |
| Épices (`Ingredient_Spices`) | 1 à 3 | 12 % |
| Salade de champignons (`Food_Salad_Mushroom`) | 1 à 2 | 6 % |

**Tirage 2** (1 à 2 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Blé (`Plant_Crop_Wheat_Item`) | 2 à 6 | 29 % |
| Pomme de terre (`Plant_Crop_Potato_Item`) | 2 à 5 | 21 % |
| Carotte (`Plant_Crop_Carrot_Item`) | 2 à 5 | 21 % |
| Citrouille (`Plant_Crop_Pumpkin_Item`) | 1 à 3 | 14 % |
| Oignon (`Plant_Crop_Onion_Item`) | 1 à 4 | 14 % |

**Tirage 3** (0 à 1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Sel (`Ingredient_Salt`) | 1 à 4 | 40 % |
| Farine (`Ingredient_Flour`) | 2 à 5 | 40 % |
| Pâte (`Ingredient_Dough`) | 1 à 3 | 20 % |

## Quartiers du capitaine {#quartiers-du-capitaine}

[Poste de garde](postes-de-garde.md) · liste `Nakasar_Loot_Guard_Captain`

**Tirage 1** (1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Casque en fer (`Armor_Iron_Head`) | 1 | 18 % |
| Gants en fer (`Armor_Iron_Hands`) | 1 | 18 % |
| Jambières en fer (`Armor_Iron_Legs`) | 1 | 18 % |
| Plastron en cuir (`Armor_Leather_Medium_Chest`) | 1 | 18 % |
| Casque en cuir (`Armor_Leather_Medium_Head`) | 1 | 18 % |
| Plastron en fer (`Armor_Iron_Chest`) | 1 | 9 % |

**Tirage 2** (1 à 2 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| **Lingot d'argent** (`Ingredient_Bar_Silver`) | 1 à 3 | 27 % |
| Lingot d'or (`Ingredient_Bar_Gold`) | 1 à 2 | 18 % |
| Rubis (`Rock_Gem_Ruby`) | 1 à 2 | 18 % |
| Topaze (`Rock_Gem_Topaz`) | 1 à 2 | 18 % |
| Saphir (`Rock_Gem_Sapphire`) | 1 | 9 % |
| Émeraude (`Rock_Gem_Emerald`) | 1 | 9 % |

**Tirage 3** (1 à 2 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Flèche en fer (`Weapon_Arrow_Iron`) | 4 à 12 | 21 % |
| Flèche grossière (`Weapon_Arrow_Crude`) | 6 à 16 | 16 % |
| Lingot de fer (`Ingredient_Bar_Iron`) | 1 à 3 | 16 % |
| Potion de soin mineure (`Potion_Health_Lesser`) | 1 à 2 | 16 % |
| Kit de réparation en fer (`Tool_Repair_Kit_Iron`) | 1 | 11 % |
| Cuir moyen (`Ingredient_Leather_Medium`) | 1 à 3 | 11 % |
| Potion d'endurance mineure (`Potion_Stamina_Lesser`) | 1 à 2 | 11 % |

**Tirage 4** (0 à 1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| *rien* | | 50 % |
| Épée longue en fer (`Weapon_Longsword_Iron`) | 1 | 33 % |
| Épée en acier (`Weapon_Sword_Steel`) | 1 | 17 % |

**Tirage 5** (0 à 1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| *rien* | | 40 % |
| Note : [Consignes de garde](notes-et-epitaphes.md) (`Nakasar_Lore_Guard_Orders`) | 1 | 20 % |
| Note : [Serment de la garde](notes-et-epitaphes.md) (`Nakasar_Lore_Guard_Oath`) | 1 | 20 % |
| Note : [Griffonné sur un bout de toile](notes-et-epitaphes.md) (`Nakasar_Lore_Prisoner`) | 1 | 20 % |

## Armurerie {#armurerie}

[Poste de garde](postes-de-garde.md) · liste `Nakasar_Loot_Guard_Armory`

**Tirage 1** (1 à 2 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Épée en acier rouillée (`Weapon_Sword_Steel_Rusty`) | 1 | 19 % |
| Hache en fer rouillée (`Weapon_Axe_Iron_Rusty`) | 1 | 19 % |
| Bouclier rouillé (`Weapon_Shield_Rusty`) | 1 | 19 % |
| Gourdin en fer rouillé (`Weapon_Club_Iron_Rusty`) | 1 | 12 % |
| Arc court en fer rouillé (`Weapon_Shortbow_Iron_Rusty`) | 1 | 12 % |
| Lance en fer (`Weapon_Spear_Iron`) | 1 | 6 % |
| Hache de bataille rouillée (`Weapon_Battleaxe_Steel_Rusty`) | 1 | 6 % |
| Arbalète en fer (`Weapon_Crossbow_Iron`) | 1 | 6 % |

**Tirage 2** (0 à 1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| *rien* | | 27 % |
| Casque en fer (`Armor_Iron_Head`) | 1 | 13 % |
| Gants en fer (`Armor_Iron_Hands`) | 1 | 13 % |
| Jambières en fer (`Armor_Iron_Legs`) | 1 | 13 % |
| Plastron en cuir (`Armor_Leather_Medium_Chest`) | 1 | 13 % |
| Casque en cuir (`Armor_Leather_Medium_Head`) | 1 | 13 % |
| Plastron en fer (`Armor_Iron_Chest`) | 1 | 7 % |

**Tirage 3** (1 à 2 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Flèche en fer (`Weapon_Arrow_Iron`) | 4 à 12 | 21 % |
| Flèche grossière (`Weapon_Arrow_Crude`) | 6 à 16 | 16 % |
| Lingot de fer (`Ingredient_Bar_Iron`) | 1 à 3 | 16 % |
| Potion de soin mineure (`Potion_Health_Lesser`) | 1 à 2 | 16 % |
| Kit de réparation en fer (`Tool_Repair_Kit_Iron`) | 1 | 11 % |
| Cuir moyen (`Ingredient_Leather_Medium`) | 1 à 3 | 11 % |
| Potion d'endurance mineure (`Potion_Stamina_Lesser`) | 1 à 2 | 11 % |

## Caserne {#caserne}

[Poste de garde](postes-de-garde.md) · liste `Nakasar_Loot_Guard_Barracks`

**Tirage 1** (1 à 2 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Flèche en fer (`Weapon_Arrow_Iron`) | 4 à 12 | 21 % |
| Flèche grossière (`Weapon_Arrow_Crude`) | 6 à 16 | 16 % |
| Lingot de fer (`Ingredient_Bar_Iron`) | 1 à 3 | 16 % |
| Potion de soin mineure (`Potion_Health_Lesser`) | 1 à 2 | 16 % |
| Kit de réparation en fer (`Tool_Repair_Kit_Iron`) | 1 | 11 % |
| Cuir moyen (`Ingredient_Leather_Medium`) | 1 à 3 | 11 % |
| Potion d'endurance mineure (`Potion_Stamina_Lesser`) | 1 à 2 | 11 % |

**Tirage 2** (1 à 2 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Pain (`Food_Bread`) | 1 à 3 | 27 % |
| Fromage (`Food_Cheese`) | 1 à 2 | 20 % |
| Pomme (`Plant_Fruit_Apple`) | 2 à 5 | 20 % |
| Légumes cuits (`Food_Vegetable_Cooked`) | 1 à 2 | 13 % |
| Gibier cuit (`Food_Wildmeat_Cooked`) | 1 à 2 | 13 % |
| Tourte à la viande (`Food_Pie_Meat`) | 1 | 7 % |

**Tirage 3** (0 à 1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| *rien* | | 27 % |
| Épée en acier rouillée (`Weapon_Sword_Steel_Rusty`) | 1 | 14 % |
| Hache en fer rouillée (`Weapon_Axe_Iron_Rusty`) | 1 | 14 % |
| Bouclier rouillé (`Weapon_Shield_Rusty`) | 1 | 14 % |
| Gourdin en fer rouillé (`Weapon_Club_Iron_Rusty`) | 1 | 9 % |
| Arc court en fer rouillé (`Weapon_Shortbow_Iron_Rusty`) | 1 | 9 % |
| Lance en fer (`Weapon_Spear_Iron`) | 1 | 5 % |
| Hache de bataille rouillée (`Weapon_Battleaxe_Steel_Rusty`) | 1 | 5 % |
| Arbalète en fer (`Weapon_Crossbow_Iron`) | 1 | 5 % |

**Tirage 4** (0 à 1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| *rien* | | 62 % |
| Note : [Consignes de garde](notes-et-epitaphes.md) (`Nakasar_Lore_Guard_Orders`) | 1 | 12 % |
| Note : [Serment de la garde](notes-et-epitaphes.md) (`Nakasar_Lore_Guard_Oath`) | 1 | 12 % |
| Note : [Griffonné sur un bout de toile](notes-et-epitaphes.md) (`Nakasar_Lore_Prisoner`) | 1 | 12 % |

## Ruines du château {#ruines-du-chateau}

[Château hanté](chateaux-hantes.md), chambre du donjon · liste `Nakasar_Loot_Castle_Ruins`

**Tirage 1** (1 à 2 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Épée en acier rouillée (`Weapon_Sword_Steel_Rusty`) | 1 | 19 % |
| Hache en fer rouillée (`Weapon_Axe_Iron_Rusty`) | 1 | 19 % |
| Bouclier rouillé (`Weapon_Shield_Rusty`) | 1 | 19 % |
| Gourdin en fer rouillé (`Weapon_Club_Iron_Rusty`) | 1 | 12 % |
| Arc court en fer rouillé (`Weapon_Shortbow_Iron_Rusty`) | 1 | 12 % |
| Lance en fer (`Weapon_Spear_Iron`) | 1 | 6 % |
| Hache de bataille rouillée (`Weapon_Battleaxe_Steel_Rusty`) | 1 | 6 % |
| Arbalète en fer (`Weapon_Crossbow_Iron`) | 1 | 6 % |

**Tirage 2** (1 à 2 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| **Lingot d'argent** (`Ingredient_Bar_Silver`) | 1 à 3 | 27 % |
| Lingot d'or (`Ingredient_Bar_Gold`) | 1 à 2 | 18 % |
| Rubis (`Rock_Gem_Ruby`) | 1 à 2 | 18 % |
| Topaze (`Rock_Gem_Topaz`) | 1 à 2 | 18 % |
| Saphir (`Rock_Gem_Sapphire`) | 1 | 9 % |
| Émeraude (`Rock_Gem_Emerald`) | 1 | 9 % |

**Tirage 3** (0 à 2 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Fragment d'os (`Ingredient_Bone_Fragment`) | 2 à 6 | 35 % |
| Chute de lin (`Ingredient_Fabric_Scrap_Linen`) | 1 à 3 | 18 % |
| **Éclat de rune** (`Ingredient_Rune_Shard`) | 1 | 12 % |
| Potion de soin mineure (`Potion_Health_Lesser`) | 1 | 12 % |
| Topaze (`Rock_Gem_Topaz`) | 1 | 6 % |
| **Lingot d'argent** (`Ingredient_Bar_Silver`) | 1 à 2 | 6 % |
| Épée en os (`Weapon_Sword_Bone`) | 1 | 6 % |
| Dagues en os (`Weapon_Daggers_Bone`) | 1 | 6 % |

## Crypte {#crypte}

[Crypte](cryptes.md), salle funéraire · liste `Nakasar_Loot_Crypt`

**Tirage 1** (1 à 3 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Fragment d'os (`Ingredient_Bone_Fragment`) | 2 à 6 | 35 % |
| Chute de lin (`Ingredient_Fabric_Scrap_Linen`) | 1 à 3 | 18 % |
| **Éclat de rune** (`Ingredient_Rune_Shard`) | 1 | 12 % |
| Potion de soin mineure (`Potion_Health_Lesser`) | 1 | 12 % |
| Topaze (`Rock_Gem_Topaz`) | 1 | 6 % |
| **Lingot d'argent** (`Ingredient_Bar_Silver`) | 1 à 2 | 6 % |
| Épée en os (`Weapon_Sword_Bone`) | 1 | 6 % |
| Dagues en os (`Weapon_Daggers_Bone`) | 1 | 6 % |

## Maison du notable {#maison-du-notable}

[Village](villages.md), maison du notable · liste `Nakasar_Loot_Village_Rich`

**Tirage 1** (2 à 3 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Chute de lin (`Ingredient_Fabric_Scrap_Linen`) | 1 à 4 | 21 % |
| Chute de laine (`Ingredient_Fabric_Scrap_Wool`) | 1 à 3 | 16 % |
| Fibre (`Ingredient_Fibre`) | 2 à 6 | 16 % |
| Bâton (`Ingredient_Stick`) | 2 à 5 | 16 % |
| Charbon de bois (`Ingredient_Charcoal`) | 1 à 4 | 11 % |
| Farine (`Ingredient_Flour`) | 1 à 3 | 11 % |
| Sel (`Ingredient_Salt`) | 1 à 2 | 5 % |
| Cuir léger (`Ingredient_Leather_Light`) | 1 à 2 | 5 % |

**Tirage 2** (1 à 2 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Tourte à la viande (`Food_Pie_Meat`) | 1 à 2 | 18 % |
| Tarte aux pommes (`Food_Pie_Apple`) | 1 à 2 | 18 % |
| Fromage (`Food_Cheese`) | 1 à 3 | 18 % |
| Pain (`Food_Bread`) | 2 à 4 | 18 % |
| Brochette de viande (`Food_Kebab_Meat`) | 1 à 3 | 12 % |
| Épices (`Ingredient_Spices`) | 1 à 3 | 12 % |
| Salade de champignons (`Food_Salad_Mushroom`) | 1 à 2 | 6 % |

**Tirage 3** (1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| **Lingot d'argent** (`Ingredient_Bar_Silver`) | 1 à 3 | 43 % |
| Lingot d'or (`Ingredient_Bar_Gold`) | 1 à 2 | 29 % |
| *rien* | | 29 % |

**Tirage 4** (0 à 1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Page de recette (`Recipe_Page`) | 1 à 2 | 50 % |
| *rien* | | 30 % |
| Recette : tourte à la viande (`Recipe_Food_Pie_Meat`) | 1 | 10 % |
| Recette : tarte à la citrouille (`Recipe_Food_Pie_Pumpkin`) | 1 | 10 % |

**Tirage 5** (0 à 1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| *rien* | | 43 % |
| Note : [Lettre jamais envoyée](notes-et-epitaphes.md) (`Nakasar_Lore_Village_Letter`) | 1 | 14 % |
| Note : [Avis du bailli](notes-et-epitaphes.md) (`Nakasar_Lore_Village_Curfew`) | 1 | 14 % |
| Note : [Registre de la ferme](notes-et-epitaphes.md) (`Nakasar_Lore_Farm_Ledger`) | 1 | 14 % |
| Note : [Mot gratté sur une porte](notes-et-epitaphes.md) (`Nakasar_Lore_Village_Last`) | 1 | 14 % |

## Maison du village {#maison-du-village}

[Village](villages.md), 9 coffres · liste `Nakasar_Loot_Village_House`

**Tirage 1** (1 à 3 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Chute de lin (`Ingredient_Fabric_Scrap_Linen`) | 1 à 4 | 21 % |
| Chute de laine (`Ingredient_Fabric_Scrap_Wool`) | 1 à 3 | 16 % |
| Fibre (`Ingredient_Fibre`) | 2 à 6 | 16 % |
| Bâton (`Ingredient_Stick`) | 2 à 5 | 16 % |
| Charbon de bois (`Ingredient_Charcoal`) | 1 à 4 | 11 % |
| Farine (`Ingredient_Flour`) | 1 à 3 | 11 % |
| Sel (`Ingredient_Salt`) | 1 à 2 | 5 % |
| Cuir léger (`Ingredient_Leather_Light`) | 1 à 2 | 5 % |

**Tirage 2** (1 à 2 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Pain (`Food_Bread`) | 1 à 3 | 27 % |
| Fromage (`Food_Cheese`) | 1 à 2 | 20 % |
| Pomme (`Plant_Fruit_Apple`) | 2 à 5 | 20 % |
| Légumes cuits (`Food_Vegetable_Cooked`) | 1 à 2 | 13 % |
| Gibier cuit (`Food_Wildmeat_Cooked`) | 1 à 2 | 13 % |
| Tourte à la viande (`Food_Pie_Meat`) | 1 | 7 % |

**Tirage 3** (0 à 1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Blé (`Plant_Crop_Wheat_Item`) | 2 à 6 | 16 % |
| Graines de blé (`Plant_Seeds_Wheat`) | 2 à 5 | 16 % |
| Pomme de terre (`Plant_Crop_Potato_Item`) | 2 à 5 | 12 % |
| Carotte (`Plant_Crop_Carrot_Item`) | 2 à 5 | 12 % |
| Citrouille (`Plant_Crop_Pumpkin_Item`) | 1 à 3 | 8 % |
| Oignon (`Plant_Crop_Onion_Item`) | 1 à 4 | 8 % |
| Plant de pomme de terre (`Plant_Seeds_Potato`) | 1 à 3 | 8 % |
| Graines de carotte (`Plant_Seeds_Carrot`) | 1 à 3 | 8 % |
| Graines de citrouille (`Plant_Seeds_Pumpkin`) | 1 à 3 | 8 % |
| Graines d'oignon (`Plant_Seeds_Onion`) | 1 à 3 | 4 % |

**Tirage 4** (0 à 1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| *rien* | | 67 % |
| Potion de soin mineure (`Potion_Health_Lesser`) | 1 | 22 % |
| Kit de réparation grossier (`Tool_Repair_Kit_Crude`) | 1 | 11 % |

**Tirage 5** (0 à 1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| *rien* | | 60 % |
| Note : [Lettre jamais envoyée](notes-et-epitaphes.md) (`Nakasar_Lore_Village_Letter`) | 1 | 10 % |
| Note : [Avis du bailli](notes-et-epitaphes.md) (`Nakasar_Lore_Village_Curfew`) | 1 | 10 % |
| Note : [Registre de la ferme](notes-et-epitaphes.md) (`Nakasar_Lore_Farm_Ledger`) | 1 | 10 % |
| Note : [Mot gratté sur une porte](notes-et-epitaphes.md) (`Nakasar_Lore_Village_Last`) | 1 | 10 % |

## Ferme {#ferme}

[Fermes](fermes.md) (zombies, en ruine) et [champs de citrouilles](champs-de-citrouilles.md) · liste `Nakasar_Loot_Farm`

**Tirage 1** (1 à 3 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Blé (`Plant_Crop_Wheat_Item`) | 2 à 6 | 29 % |
| Pomme de terre (`Plant_Crop_Potato_Item`) | 2 à 5 | 21 % |
| Carotte (`Plant_Crop_Carrot_Item`) | 2 à 5 | 21 % |
| Citrouille (`Plant_Crop_Pumpkin_Item`) | 1 à 3 | 14 % |
| Oignon (`Plant_Crop_Onion_Item`) | 1 à 4 | 14 % |

**Tirage 2** (1 à 2 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Graines de blé (`Plant_Seeds_Wheat`) | 2 à 5 | 36 % |
| Plant de pomme de terre (`Plant_Seeds_Potato`) | 1 à 3 | 18 % |
| Graines de carotte (`Plant_Seeds_Carrot`) | 1 à 3 | 18 % |
| Graines de citrouille (`Plant_Seeds_Pumpkin`) | 1 à 3 | 18 % |
| Graines d'oignon (`Plant_Seeds_Onion`) | 1 à 3 | 9 % |

**Tirage 3** (0 à 1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| *rien* | | 33 % |
| Houe grossière (`Tool_Hoe_Crude`) | 1 | 17 % |
| Pelle grossière (`Tool_Shovel_Crude`) | 1 | 11 % |
| Seau (`Container_Bucket`) | 1 | 11 % |
| Engrais (`Tool_Fertilizer`) | 1 à 3 | 11 % |
| Houe en cuivre (`Tool_Hoe_Copper`) | 1 | 6 % |
| Faucille en cuivre (`Tool_Sickle_Copper`) | 1 | 6 % |
| Musette (`Tool_Feedbag`) | 1 | 6 % |

**Tirage 4** (0 à 2 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Pain (`Food_Bread`) | 1 à 3 | 27 % |
| Fromage (`Food_Cheese`) | 1 à 2 | 20 % |
| Pomme (`Plant_Fruit_Apple`) | 2 à 5 | 20 % |
| Légumes cuits (`Food_Vegetable_Cooked`) | 1 à 2 | 13 % |
| Gibier cuit (`Food_Wildmeat_Cooked`) | 1 à 2 | 13 % |
| Tourte à la viande (`Food_Pie_Meat`) | 1 | 7 % |

**Tirage 5** (0 à 1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| *rien* | | 67 % |
| Note : [Registre de la ferme](notes-et-epitaphes.md) (`Nakasar_Lore_Farm_Ledger`) | 1 | 11 % |
| Note : [Carnet d'une fermière](notes-et-epitaphes.md) (`Nakasar_Lore_Farm_Diary`) | 1 | 11 % |
| Note : [Lettre jamais envoyée](notes-et-epitaphes.md) (`Nakasar_Lore_Village_Letter`) | 1 | 11 % |

## Ferme incendiée {#ferme-incendiee}

[Ferme](fermes.md) incendiée · liste `Nakasar_Loot_Farm_Burnt`

**Tirage 1** (1 à 3 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Charbon de bois (`Ingredient_Charcoal`) | 2 à 8 | 38 % |
| *rien* | | 25 % |
| Fragment d'os (`Ingredient_Bone_Fragment`) | 1 à 3 | 12 % |
| Bâton (`Ingredient_Stick`) | 1 à 3 | 12 % |
| Graines de blé (`Plant_Seeds_Wheat`) | 1 à 3 | 12 % |

**Tirage 2** (0 à 1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| *rien* | | 75 % |
| Houe grossière (`Tool_Hoe_Crude`) | 1 | 25 % |

**Tirage 3** (0 à 1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| *rien* | | 57 % |
| Note : [Registre de la ferme](notes-et-epitaphes.md) (`Nakasar_Lore_Farm_Ledger`) | 1 | 14 % |
| Note : [Carnet d'une fermière](notes-et-epitaphes.md) (`Nakasar_Lore_Farm_Diary`) | 1 | 14 % |
| Note : [Lettre jamais envoyée](notes-et-epitaphes.md) (`Nakasar_Lore_Village_Letter`) | 1 | 14 % |

## Camp de chasseurs {#camp-de-chasseurs}

[Camp de chasseurs](camps-de-chasseurs.md), tente ou pavillon · liste `Nakasar_Loot_Hunter_Camp`

**Tirage 1** (1 à 3 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Flèche en fer (`Weapon_Arrow_Iron`) | 6 à 16 | 26 % |
| Potion de soin mineure (`Potion_Health_Lesser`) | 1 à 2 | 16 % |
| **Lingot d'argent** (`Ingredient_Bar_Silver`) | 1 à 3 | 16 % |
| Antidote (`Potion_Antidote`) | 1 à 2 | 11 % |
| Potion d'endurance mineure (`Potion_Stamina_Lesser`) | 1 à 2 | 11 % |
| Cuir moyen (`Ingredient_Leather_Medium`) | 1 à 3 | 11 % |
| Potion de soin (`Potion_Health`) | 1 | 5 % |
| Kit de réparation en fer (`Tool_Repair_Kit_Iron`) | 1 | 5 % |

**Tirage 2** (1 à 2 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Gibier cuit (`Food_Wildmeat_Cooked`) | 1 à 3 | 43 % |
| Pain (`Food_Bread`) | 1 à 3 | 43 % |
| Fromage (`Food_Cheese`) | 1 à 2 | 14 % |

**Tirage 3** (0 à 1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| *rien* | | 38 % |
| Arbalète en fer (`Weapon_Crossbow_Iron`) | 1 | 14 % |
| Dagues en fer (`Weapon_Daggers_Iron`) | 1 | 10 % |
| Capuche de corbeau (`Armor_Leather_Raven_Head`) | 1 | 10 % |
| Plastron en cuir (`Armor_Leather_Medium_Chest`) | 1 | 10 % |
| Casque en cuir (`Armor_Leather_Medium_Head`) | 1 | 10 % |
| **Épée en acier d'argent** (`Weapon_Sword_Silversteel`) | 1 | 5 % |
| Plastron de corbeau (`Armor_Leather_Raven_Chest`) | 1 | 5 % |

**Tirage 4** (0 à 1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| *rien* | | 44 % |
| Note : [Journal de traque, page arrachée](notes-et-epitaphes.md) (`Nakasar_Lore_Hunter_Log`) | 1 | 11 % |
| Note : [Note sur l'argent](notes-et-epitaphes.md) (`Nakasar_Lore_Hunter_Silver`) | 1 | 11 % |
| Note : [Liste des disparus](notes-et-epitaphes.md) (`Nakasar_Lore_Hunter_Missing`) | 1 | 11 % |
| Note : [Avertissement griffonné](notes-et-epitaphes.md) (`Nakasar_Lore_Hunter_Pumpkins`) | 1 | 11 % |
| Note : [Ordres du camp](notes-et-epitaphes.md) (`Nakasar_Lore_Hunter_Orders`) | 1 | 11 % |

## Armurerie des chasseurs {#armurerie-des-chasseurs}

[Camp de chasseurs](camps-de-chasseurs.md), atelier · liste `Nakasar_Loot_Hunter_Armory`

**Tirage 1** (2 à 3 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Flèche en fer (`Weapon_Arrow_Iron`) | 6 à 16 | 26 % |
| Potion de soin mineure (`Potion_Health_Lesser`) | 1 à 2 | 16 % |
| **Lingot d'argent** (`Ingredient_Bar_Silver`) | 1 à 3 | 16 % |
| Antidote (`Potion_Antidote`) | 1 à 2 | 11 % |
| Potion d'endurance mineure (`Potion_Stamina_Lesser`) | 1 à 2 | 11 % |
| Cuir moyen (`Ingredient_Leather_Medium`) | 1 à 3 | 11 % |
| Potion de soin (`Potion_Health`) | 1 | 5 % |
| Kit de réparation en fer (`Tool_Repair_Kit_Iron`) | 1 | 5 % |

**Tirage 2** (1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| Arbalète en fer (`Weapon_Crossbow_Iron`) | 1 | 19 % |
| *rien* | | 19 % |
| Dagues en fer (`Weapon_Daggers_Iron`) | 1 | 12 % |
| Capuche de corbeau (`Armor_Leather_Raven_Head`) | 1 | 12 % |
| Plastron en cuir (`Armor_Leather_Medium_Chest`) | 1 | 12 % |
| Casque en cuir (`Armor_Leather_Medium_Head`) | 1 | 12 % |
| **Épée en acier d'argent** (`Weapon_Sword_Silversteel`) | 1 | 6 % |
| Plastron de corbeau (`Armor_Leather_Raven_Chest`) | 1 | 6 % |

**Tirage 3** (0 à 1 fois)

| Objet | Quantité | Chance par tirage |
|---|---|---|
| *rien* | | 38 % |
| Note : [Journal de traque, page arrachée](notes-et-epitaphes.md) (`Nakasar_Lore_Hunter_Log`) | 1 | 12 % |
| Note : [Note sur l'argent](notes-et-epitaphes.md) (`Nakasar_Lore_Hunter_Silver`) | 1 | 12 % |
| Note : [Liste des disparus](notes-et-epitaphes.md) (`Nakasar_Lore_Hunter_Missing`) | 1 | 12 % |
| Note : [Avertissement griffonné](notes-et-epitaphes.md) (`Nakasar_Lore_Hunter_Pumpkins`) | 1 | 12 % |
| Note : [Ordres du camp](notes-et-epitaphes.md) (`Nakasar_Lore_Hunter_Orders`) | 1 | 12 % |
