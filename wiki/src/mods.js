// Les trois mods du wiki : nom, dossier (= préfixe des URL), pitch et rubriques. Utilisé par l'accueil
// (src/pages/index.js), la barre de sections (src/components/ModBar) et la teinte de chaque mod
// (attribut data-mod sur <html>, couleurs dans src/css/custom.css). Une rubrique est active quand l'URL
// commence par l'un de ses préfixes `match` (par défaut son lien `to`).

export const MODS = [
  {
    id: "vampires",
    name: "Vampires & Chasseurs",
    pack: "Nakasar : Vampires",
    to: "/vampires",
    image: "vampires",
    pitch:
      "Un fragment d'Orbis hanté gouverné par un comte vampire, des chasseurs qui ouvrent des brèches dans votre monde, des armes en argent et des runes de sang.",
    cta: "Entrer dans le Comté",
    stats: [
      ["10", "structures"],
      ["7", "boss et élites"],
      ["7", "runes"],
    ],
    sections: [
      { label: "Présentation", to: "/vampires", exact: true },
      { label: "Comté Vampire", to: "/vampires/fragment" },
      { label: "Bestiaire", to: "/vampires/pnj" },
      { label: "Brèches", to: "/vampires/breches" },
      { label: "Objets", to: "/vampires/objets", match: ["/vampires/objets", "/vampires/effets"] },
      { label: "Donjons", to: "/vampires/donjons" },
    ],
  },
  {
    id: "fractales",
    name: "Fractales des Brumes",
    pack: "Nakasar : Fractales",
    to: "/fractales",
    image: "fractales",
    pitch:
      "Des aventures courtes pour 1 à 5 joueurs, tirées de Guild Wars 2 : puzzles de saut, mécaniques de groupe et boss, depuis l'Observatoire dans les Brumes.",
    cta: "Traverser les Brumes",
    stats: [
      ["11", "fractales"],
      ["1-5", "joueurs"],
      ["100", "niveaux"],
    ],
    sections: [
      { label: "Présentation", to: "/fractales", exact: true },
      { label: "Observatoire", to: "/fractales/observatoire" },
      { label: "Progression", to: "/fractales/progression", match: ["/fractales/progression", "/fractales/instabilites"] },
      {
        label: "Saison 1",
        to: "/fractales/falaise",
        match: ["/fractales/falaise", "/fractales/inclassable", "/fractales/volcanique", "/fractales/ocean-solide", "/fractales/marais", "/fractales/tempete-de-neige"],
      },
      {
        label: "Saison 2",
        to: "/fractales/ressac-silencieux",
        match: ["/fractales/ressac-silencieux", "/fractales/recif-de-la-sirene", "/fractales/roche-des-abysses", "/fractales/pic-de-sunqua", "/fractales/boss-en-fusion"],
      },
      { label: "Équipement", to: "/fractales/potions", match: ["/fractales/potions", "/fractales/runes-et-soutien", "/fractales/cosmetiques"] },
    ],
  },
  {
    id: "peuples",
    name: "Peuples d'Orbis",
    pack: "Nakasar : Peuples",
    to: "https://orbis.nakasar.xyz",
    image: "peuples",
    pitch:
      "Des villages vivants qui grandissent avec votre aide, de la forêt kweebec au monastère slothian au bord du Vide, jusqu'à devenir le Champion d'un peuple.",
    cta: "Rejoindre les villages",
    stats: [
      ["5", "peuples"],
      ["4", "zones"],
      ["6", "rangs"],
    ],
    // Le mod a son propre dépôt (Nakasar/peoples-of-orbis) et son propre wiki : la carte de l'accueil y mène.
    external: true,
    sections: [],
  },
];

function under(path, prefix) {
  return path === prefix || path.startsWith(prefix + "/");
}

/** Le mod d'une URL du site (sans baseUrl), ou null pour les pages communes. */
export function modOf(path) {
  return MODS.find((mod) => !mod.external && under(path, mod.to)) ?? null;
}

/** La rubrique active d'un mod pour cette URL. */
export function sectionOf(mod, path) {
  const clean = path.replace(/\/$/, "") || "/";
  return (
    mod.sections.find((s) => (s.exact ? clean === s.to : (s.match ?? [s.to]).some((p) => under(clean, p)))) ?? null
  );
}
