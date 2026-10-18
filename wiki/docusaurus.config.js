// Wiki joueur du mod Vampires. Les pages sont le Markdown de ../docs/wiki ; le site est publié sur
// GitHub Pages par .github/workflows/wiki.yml. Aperçu local : npm ci puis npm start.
import { themes as prismThemes } from "prism-react-renderer";

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: "Wiki du mod Vampires",
  tagline: "Guide du joueur du mod Nakasar Vampires pour Hytale",
  favicon: "img/favicon.png",
  url: "https://nakasar.github.io",
  baseUrl: "/hytale-modding/",
  organizationName: "Nakasar",
  projectName: "hytale-modding",
  trailingSlash: false,
  onBrokenLinks: "throw",
  onBrokenAnchors: "throw",
  markdown: { hooks: { onBrokenMarkdownLinks: "throw" } },
  i18n: { defaultLocale: "fr", locales: ["fr"] },

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
      navbar: {
        title: "Wiki du mod Vampires",
        logo: { alt: "Citrouille géante", src: "img/favicon.png" },
        items: [
          { type: "docSidebar", sidebarId: "fragment", label: "Comté Vampire", position: "left" },
          { type: "docSidebar", sidebarId: "bestiaire", label: "Bestiaire", position: "left" },
          { to: "/breches", label: "Brèches", position: "left" },
          { type: "docSidebar", sidebarId: "objets", label: "Objets", position: "left" },
          { href: "https://github.com/Nakasar/hytale-modding", label: "GitHub", position: "right" },
        ],
      },
      footer: {
        style: "dark",
        copyright: "Mod Nakasar Vampires pour Hytale. Chiffres lus dans les fichiers du mod.",
      },
      prism: { theme: prismThemes.github, darkTheme: prismThemes.dracula },
    }),
};

export default config;
