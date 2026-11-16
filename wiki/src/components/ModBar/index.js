// Barre de sections d'un mod, sous la barre du haut, à la teinte du mod (rubriques dans src/mods.js).
import React from "react";
import clsx from "clsx";
import Link from "@docusaurus/Link";
import { sectionOf } from "@site/src/mods";
import styles from "./styles.module.css";

export default function ModBar({ mod, path }) {
  const active = sectionOf(mod, path);
  return (
    <nav className={styles.bar} aria-label={`Rubriques : ${mod.name}`}>
      <div className={styles.inner}>
        <Link to={mod.to} className={styles.name}>
          {mod.name}
        </Link>
        <ul className={styles.list}>
          {mod.sections.map((s) => (
            <li key={s.to}>
              <Link
                to={s.to}
                className={clsx(styles.link, s === active && styles.active)}
                aria-current={s === active ? "page" : undefined}
              >
                {s.label}
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </nav>
  );
}
