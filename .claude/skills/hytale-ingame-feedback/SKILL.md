---
name: hytale-ingame-feedback
description: Transformer un retour de test en jeu de Kevin (capture d'écran, description, log, "ça ne marche pas", "c'est moche", "trop dur") en diagnostic et en correctifs pour les mods Nakasar, puis tenir à jour les "Points à vérifier en jeu", le wiki joueur et la mémoire du projet. À utiliser dès que Kevin revient d'une session de jeu, envoie une capture ou un log, liste plusieurs remarques sur un lieu/boss/objet, ou demande de mettre à jour le wiki ou la doc après une fonctionnalité, même s'il ne dit pas "retour en jeu".
---

# Retours de test en jeu

Le conteneur ne peut pas lancer Hytale : Kevin est le seul à voir le jeu. Chacun de ses retours est donc
précieux et cher (une session de jeu, des captures, du temps). Le traiter bien, c'est : tout prendre en compte,
distinguer ce qui est su de ce qui est supposé, corriger la cause plutôt que le symptôme, et faire en sorte que
la prochaine session de jeu apprenne quelque chose même si le correctif n'a pas marché.

## 1. Découper le retour

Lister chaque remarque séparément, dans ses mots, et la classer :
- **bug** (ne marche pas, ne charge pas, plante, n'apparaît pas) ;
- **visuel** (moche, mal orienté, trop gros, transparent) → skills `hytale-3d-assets` / `hytale-organic-decor` ;
- **gameplay / équilibrage** (trop dur, illisible, ennuyeux) → skill `hytale-encounter-design` ;
- **décision** (il choisit entre deux options, refuse une idée, exprime un goût) → à **noter en mémoire tout de
  suite**, c'est ce que le prochain fil devrait sinon lui redemander.

Regarder les captures soi-même (les lire), et noter ce qu'elles montrent de plus que le texte.
Mettre la liste dans la checklist : Kevin doit voir chaque point repris, rien d'oublié.

## 2. Diagnostiquer avant de corriger

Pour chaque bug : formuler la cause la plus probable **et la preuve qui la confirmerait**.
- D'abord les pièges connus (skill `hytale-load-pitfalls`, catalogue) : beaucoup de symptômes y sont déjà.
- Ensuite le code et le comportement réel du serveur (skill `hytale-vanilla-research`, décompilation).
- Si la cause reste incertaine, ne pas empiler des corrections au hasard : **ajouter de l'observabilité**.
  Chaque mécanique Java logge en INFO avec une étiquette stable (`Nakasar_Fractal_Cage`, `Nakasar_RootTrap`,
  `Nakasar_Fractal_Hammer`…) ce qu'elle décide et pourquoi. Demander ensuite à Kevin ces lignes précises du log
  serveur (`UserData\Logs` en solo), avec l'étiquette à chercher. C'est ainsi que des bugs « ça n'arrive
  jamais » ont été trouvés (charge du marteau perdue à cause de la durabilité).
- Dire clairement dans la réponse : *cause trouvée* (avec la preuve) ou *cause supposée* (avec ce qu'on a
  ajouté pour la confirmer).

## 3. Corriger

- Corriger la cause dans le générateur ou le Java, régénérer, `./gradlew check`, lint (skill
  `hytale-load-pitfalls`).
- Un retour visuel ou de décor se vérifie sur **aperçu rendu** avant de repartir en jeu (avant/après joint).
- Si le retour révèle un piège général (pas propre à cette rencontre), le rendre automatique : vérification dans
  les validateurs ou le lint, et ligne dans le catalogue des pièges.
- Si une brique est copiée entre les deux mods, corriger les deux copies.
- Respecter la forme de la demande : Kevin qui refuse une approche (« pas un champ de force ») veut une autre
  approche, pas un réglage de la même.

## 4. Tenir les traces à jour

- **README, « Points à vérifier en jeu »** : retirer ce que Kevin a confirmé, corriger ce qui était faux,
  ajouter ce que le correctif rend à vérifier, avec quoi regarder et la commande de test (`/give …`,
  `/instances spawn …`, `/time midnight`, `/worldevent start asset …`). Garder la section courte et à jour.
- **Ids confirmés** en jeu → `tools/vanilla-refs-0.7.2.txt` (ou la liste concernée).
- **Wiki joueur** (`docs/wiki/*.md`, site Docusaurus dans `wiki/`) quand le comportement visible par les joueurs
  change : stats, attaques, butin, recettes, lieux. Règles MDX : échapper `{` `}`, pas de `<img>` brut (images par
  `require` ou markdown), ids d'ancres `{#…}` en ASCII, composant `<Infobox>` en haut des pages, images jamais
  déformées. Les pages générées (butin, portraits) se régénèrent par leur script (`generate_wiki_loot.py`,
  `render_wiki_portraits.py`). Le wiki ne révèle pas les mécaniques que Kevin veut laisser découvrir.
- **Mémoire du projet** : une ligne par PR fusionnée dans l'index, le détail dans le fichier du sujet ; les
  décisions et goûts de Kevin datés ; les pièges avec leur symptôme.

## 5. Répondre

Réponse courte, en français : ce qui est corrigé (cause trouvée), ce qui est tenté (cause supposée + log à
regarder), ce qui attend une décision de sa part, et ce qu'il doit vérifier à la prochaine session (renvoyer à
la liste du README ou de la PR plutôt que de la recopier).
