// Barres latérales du wiki : une par onglet de la barre du haut. Les ids sont les chemins des pages
// sous docs/wiki, sans extension ; un README est l'index de son dossier.

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  fragment: [
    "fragment/README",
    {
      type: "category",
      label: "Structures",
      collapsed: false,
      items: [
        "fragment/crypte-d-arrivee",
        "fragment/manoir-du-comte",
        "fragment/villages",
        "fragment/fermes",
        "fragment/postes-de-garde",
        "fragment/cimetieres",
        "fragment/cryptes",
        "fragment/chateaux-hantes",
        "fragment/champs-de-citrouilles",
        "fragment/camps-de-chasseurs",
        "fragment/decor",
      ],
    },
    "fragment/butin-des-coffres",
    "breches",
  ],
  bestiaire: [
    "pnj/README",
    { type: "category", label: "Boss", collapsed: false, items: ["pnj/comte-vampire", "pnj/comtesse-vampire"] },
    {
      type: "category",
      label: "Élites",
      collapsed: false,
      items: ["pnj/capitaine-de-la-garde", "pnj/abomination-zombie", "pnj/citrouille-geante"],
    },
    {
      type: "category",
      label: "Créatures du Comté",
      collapsed: false,
      items: [
        "pnj/rejeton-de-vampire",
        "pnj/fantome",
        "pnj/villageois-zombifie",
        "pnj/fermier-zombifie",
        "pnj/paysan-rebelle-zombifie",
        "pnj/garde-squelette",
        "pnj/vrille-de-citrouille",
        "pnj/vrilles",
      ],
    },
    {
      type: "category",
      label: "Chasseurs de vampires",
      collapsed: false,
      items: ["pnj/chasseur-epee", "pnj/chasseuse-arbalete", "pnj/chasseur-tromblon"],
    },
  ],
  objets: [
    "objets/README",
    "objets/runes",
    "objets/autel-sacrificiel",
    "objets/etabli-des-chasseurs",
    "objets/armes-en-argent",
    "objets/lance-a-deux-mains",
    "objets/feu-purificateur",
    "objets/cle-du-comte",
    "objets/blocs-decoratifs",
    "effets",
  ],
};

export default sidebars;
