// Wiki joueur des mods Nakasar (Vampires, Fractales des Brumes, Peuples d'Orbis). Les pages sont le Markdown de ../docs/wiki ; le site est publié sur
// GitHub Pages par .github/workflows/wiki.yml. Aperçu local : npm ci puis npm start. Chaque mod a son dossier
// (docs/wiki/vampires, fractales, peuples), son onglet, sa barre latérale et sa teinte (src/mods.js).
import { themes as prismThemes } from "prism-react-renderer";

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: "Wiki des mods Nakasar",
  tagline: "Guide du joueur des mods Nakasar Vampires, Fractales des Brumes et Peuples d'Orbis pour Hytale",
  favicon: "img/logo.svg",
  url: "https://hunters.nakasar.xyz",
  baseUrl: "/",
  organizationName: "Nakasar",
  projectName: "hytale-modding",
  trailingSlash: false,
  onBrokenLinks: "throw",
  onBrokenAnchors: "throw",
  markdown: { hooks: { onBrokenMarkdownLinks: "throw" } },
  i18n: { defaultLocale: "fr", locales: ["fr"] },
  stylesheets: [
    "https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700&family=Inter:wght@400;500;600;700&display=swap",
  ],

  presets: [
    [
      "classic",
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          path: "../docs/wiki",
          routeBasePath: "/",
          sidebarPath: "./sidebars.js",
          editUrl: "https://github.com/Nakasar/hytale-modding/edit/main/docs/wiki/",
        },
        blog: false,
        theme: { customCss: "./src/css/custom.css" },
      }),
    ],
  ],

  plugins: [
    [
      "@docusaurus/plugin-client-redirects",
      {
        // Les pages du mod Vampires étaient à la racine du site (/fragment/..., /pnj/..., /breches) avant
        // d'aller sous /vampires : les anciennes adresses redirigent vers les nouvelles.
        createRedirects(path) {
          if (path.startsWith("/vampires/")) return [path.slice("/vampires".length)];
          return undefined;
        },
      },
    ],
  ],

  themes: [
    [
      "@easyops-cn/docusaurus-search-local",
      /** @type {import('@easyops-cn/docusaurus-search-local').PluginOptions} */
      ({ language: ["fr"], docsDir: "../docs/wiki", docsRouteBasePath: "/", indexBlog: false, hashed: true }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      colorMode: { defaultMode: "dark", respectPrefersColorScheme: false },
      docs: { sidebar: { autoCollapseCategories: true } },
      navbar: {
        title: "Wiki Nakasar",
        logo: { alt: "Accueil du wiki", src: "img/logo.svg" },
        items: [
          { type: "docSidebar", sidebarId: "vampires", label: "Vampires & Chasseurs", position: "left", className: "nk-mod-tab nk-mod-tab--vampires" },
          { type: "docSidebar", sidebarId: "fractales", label: "Fractales des Brumes", position: "left", className: "nk-mod-tab nk-mod-tab--fractales" },
          { type: "docSidebar", sidebarId: "peuples", label: "Peuples d'Orbis", position: "left", className: "nk-mod-tab nk-mod-tab--peuples" },
          { href: "https://github.com/Nakasar/hytale-modding", label: "GitHub", position: "right" },
        ],
      },
      footer: {
        style: "dark",
        links: [
          { label: "Vampires & Chasseurs", to: "/vampires" },
          { label: "Fractales des Brumes", to: "/fractales" },
          { label: "Peuples d'Orbis", to: "/peuples" },
          { label: "GitHub", href: "https://github.com/Nakasar/hytale-modding" },
        ],
        copyright: "Mods Nakasar pour Hytale. Chiffres lus dans les fichiers des mods.",
      },
      prism: { theme: prismThemes.github, darkTheme: prismThemes.dracula },
    }),
};

export default config;
