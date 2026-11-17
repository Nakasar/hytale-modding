// Barres latérales du wiki : une par mod, chacune ouverte par son onglet de la barre du haut. Les ids sont
// les chemins des pages sous docs/wiki, sans extension ; un README est l'index de son dossier. Les grandes
// rubriques d'un mod sont aussi dans sa barre de sections (src/mods.js) : garder les deux d'accord.

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  vampires: [
    "vampires/README",
    {
      type: "category",
      label: "Comté Vampire",
      link: { type: "doc", id: "vampires/fragment/README" },
      items: [
        {
          type: "category",
          label: "Structures",
          collapsed: false,
          items: [
            "vampires/fragment/crypte-d-arrivee",
            "vampires/fragment/manoir-du-comte",
            "vampires/fragment/villages",
            "vampires/fragment/fermes",
            "vampires/fragment/postes-de-garde",
            "vampires/fragment/cimetieres",
            "vampires/fragment/cryptes",
            "vampires/fragment/chateaux-hantes",
            "vampires/fragment/champs-de-citrouilles",
            "vampires/fragment/camps-de-chasseurs",
            "vampires/fragment/decor",
          ],
        },
        "vampires/fragment/butin-des-coffres",
        "vampires/fragment/notes-et-epitaphes",
      ],
    },
    {
      type: "category",
      label: "Bestiaire",
      link: { type: "doc", id: "vampires/pnj/README" },
      items: [
        { type: "category", label: "Boss", collapsed: false, items: ["vampires/pnj/comte-vampire", "vampires/pnj/comtesse-vampire"] },
        {
          type: "category",
          label: "Élites",
          collapsed: false,
          items: [
            "vampires/pnj/capitaine-de-la-garde",
            "vampires/pnj/abomination-zombie",
            "vampires/pnj/citrouille-geante",
            "vampires/pnj/armure-enchantee",
            "vampires/pnj/spectre",
          ],
        },
        {
          type: "category",
          label: "Créatures du Comté",
          items: [
            "vampires/pnj/rejeton-de-vampire",
            "vampires/pnj/fantome",
            "vampires/pnj/villageois-zombifie",
            "vampires/pnj/fermier-zombifie",
            "vampires/pnj/paysan-rebelle-zombifie",
            "vampires/pnj/garde-squelette",
            "vampires/pnj/vrille-de-citrouille",
            "vampires/pnj/rouage-enchante",
            "vampires/pnj/fantome-spectral",
            "vampires/pnj/vrilles",
          ],
        },
        {
          type: "category",
          label: "Chasseurs de vampires",
          items: ["vampires/pnj/chasseur-epee", "vampires/pnj/chasseuse-arbalete", "vampires/pnj/chasseur-tromblon"],
        },
      ],
    },
    "vampires/breches",
    {
      type: "category",
      label: "Objets",
      link: { type: "doc", id: "vampires/objets/README" },
      items: [
        "vampires/objets/runes",
        "vampires/objets/autel-sacrificiel",
        "vampires/objets/vampirisme",
        "vampires/objets/etabli-des-chasseurs",
        "vampires/objets/trophees",
        "vampires/objets/contrats",
        "vampires/objets/armes-en-argent",
        "vampires/objets/lance-a-deux-mains",
        "vampires/objets/feu-purificateur",
        "vampires/objets/cle-du-comte",
        "vampires/objets/blocs-decoratifs",
        "vampires/objets/tenues",
        "vampires/effets",
      ],
    },
    {
      type: "category",
      label: "Donjons",
      link: { type: "doc", id: "vampires/donjons/README" },
      items: ["vampires/donjons/tour-de-l-alchimiste"],
    },
  ],
  fractales: [
    "fractales/README",
    {
      type: "category",
      label: "Bien commencer",
      collapsed: false,
      items: ["fractales/observatoire", "fractales/progression", "fractales/instabilites"],
    },
    {
      type: "category",
      label: "Saison 1",
      items: [
        "fractales/falaise",
        "fractales/inclassable",
        "fractales/volcanique",
        "fractales/ocean-solide",
        "fractales/marais",
        "fractales/tempete-de-neige",
      ],
    },
    {
      type: "category",
      label: "Saison 2",
      items: [
        "fractales/ressac-silencieux",
        "fractales/recif-de-la-sirene",
        "fractales/roche-des-abysses",
        "fractales/pic-de-sunqua",
        "fractales/boss-en-fusion",
      ],
    },
    {
      type: "category",
      label: "Équipement",
      items: ["fractales/potions", "fractales/runes-et-soutien", "fractales/cosmetiques"],
    },
  ],
  peuples: [
    "peuples/README",
    {
      type: "category",
      label: "Vivre avec les peuples",
      collapsed: false,
      items: [
        "peuples/reputation",
        "peuples/villages",
        "peuples/habitants",
        "peuples/monde-vivant",
        "peuples/lieux-dits",
        "peuples/conquete",
        "peuples/commerce",
        "peuples/climats",
      ],
    },
    {
      type: "category",
      label: "Les peuples",
      items: ["peuples/kweebecs", "peuples/trorks", "peuples/feran", "peuples/renonces", "peuples/slothians"],
    },
    {
      type: "category",
      label: "Bâtiments et métiers",
      items: [
        "peuples/batiments-de-metier",
        "peuples/emplacements",
        "peuples/avant-postes-de-metier",
        {
          type: "category",
          label: "Bâtiments des villages",
          link: { type: "doc", id: "peuples/batiments/README" },
          items: [
            "peuples/batiments/kweebecs",
            "peuples/batiments/trorks",
            "peuples/batiments/feran",
            "peuples/batiments/renonces",
            "peuples/batiments/slothians",
          ],
        },
      ],
    },
    "peuples/avant-poste",
  ],
};

export default sidebars;
