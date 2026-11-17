// Accueil commun du wiki : les trois mods, chacun avec sa teinte, son image, ses chiffres clés et ses
// rubriques (src/mods.js). Les pages des mods sont le Markdown de docs/wiki/<mod>/.
import React from "react";
import Layout from "@theme/Layout";
import Link from "@docusaurus/Link";
import Heading from "@theme/Heading";
import { MODS } from "@site/src/mods";
import styles from "./index.module.css";

const IMAGES = {
  vampires: {
    src: require("../../../docs/wiki/images/lieux/champ_citrouille_geante.jpg").default,
    alt: "La Citrouille géante et ses vrilles dans le Comté Vampire",
  },
  fractales: {
    src: require("../../../docs/wiki/images/fractales/carte-observatoire.png").default,
    alt: "Carte de l'Observatoire, le hub des fractales",
  },
  peuples: {
    src: require("../../../docs/wiki/images/peuples_kweebec_coeur.jpg").default,
    alt: "Le cœur d'un village kweebec",
  },
};

function ModCard({ mod }) {
  const image = IMAGES[mod.image];
  return (
    <article className={styles.card} data-mod={mod.id}>
      <Link to={mod.to} className={styles.picture} tabIndex={-1} aria-hidden="true">
        <img src={image.src} alt="" loading="lazy" />
      </Link>
      <div className={styles.body}>
        <div className={styles.pack}>{mod.pack}</div>
        <Heading as="h2" className={styles.name}>
          <Link to={mod.to}>{mod.name}</Link>
        </Heading>
        <p className={styles.pitch}>{mod.pitch}</p>
        <dl className={styles.stats}>
          {mod.stats.map(([value, label]) => (
            <div key={label} className={styles.stat}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
        <ul className={styles.sections} aria-label={`Rubriques : ${mod.name}`}>
          {mod.sections
            .filter((s) => !s.exact)
            .map((s) => (
              <li key={s.to}>
                <Link to={s.to}>{s.label}</Link>
              </li>
            ))}
        </ul>
        <Link to={mod.to} className={styles.cta}>
          {mod.cta}
        </Link>
      </div>
    </article>
  );
}

export default function Home() {
  return (
    <Layout title="Accueil" description="Guide du joueur des mods Nakasar pour Hytale : Vampires & Chasseurs, Fractales des Brumes, Peuples d'Orbis.">
      <main className={styles.home}>
        <header className={styles.hero}>
          <div className={styles.eyebrow}>Guide du joueur · Hytale</div>
          <Heading as="h1" className={styles.title}>
            Wiki des mods Nakasar
          </Heading>
          <p className={styles.lead}>
            Trois mods, trois mondes. Chaque mod a son onglet, sa couleur et ses rubriques ; Peuples d'Orbis a son
            propre wiki. Ils se jouent seuls ou ensemble.
          </p>
        </header>
        <section className={styles.cards} aria-label="Les trois mods">
          {MODS.map((mod) => (
            <ModCard key={mod.id} mod={mod} />
          ))}
        </section>
      </main>
    </Layout>
  );
}
