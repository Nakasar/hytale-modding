// Encadré résumé façon wiki, flottant en haut à droite d'une page (pleine largeur sur mobile).
// Utilisable dans toutes les pages sans import (voir src/theme/MDXComponents.js) :
//
//   <Infobox title="Comte Vampire" image={require("../images/pnj/Nakasar_Vampire_Count.jpg").default}
//            caption="Le Comte en jeu" kind="Boss">
//   <Info label="Points de vie">**600**</Info>
//   <Info label="Lieu">[Manoir du Comte](../fragment/manoir-du-comte.md)</Info>
//   </Infobox>
//
// image : une image importée avec require(...).default, ou un chemin du site (/jeu/Icons/...) ;
// icon : image affichée petite et pixelisée (icônes d'objets). Les images gardent toujours leurs
// proportions (object-fit: contain), quelle que soit leur taille d'origine. pending : pas encore de
// capture en jeu, l'encadré l'indique à la place de l'image.
import React from "react";
import clsx from "clsx";
import useBaseUrl from "@docusaurus/useBaseUrl";
import styles from "./styles.module.css";

function imageSrc(image) {
  if (image && typeof image === "object") return image.default ?? image.src ?? image;
  return image;
}

function Picture({ image, alt, icon }) {
  const raw = imageSrc(image);
  const src = useBaseUrl(typeof raw === "string" && raw.startsWith("/") ? raw : "");
  if (!raw) return null;
  return (
    <img
      className={clsx(styles.image, icon && styles.icon)}
      src={typeof raw === "string" && raw.startsWith("/") ? src : raw}
      alt={alt}
      loading="lazy"
    />
  );
}

export default function Infobox({ title, kind, image, icon, caption, pending, children }) {
  return (
    <aside className={styles.infobox} aria-label={title ? `Résumé : ${title}` : "Résumé"}>
      {title && <div className={styles.title}>{title}</div>}
      {kind && <div className={styles.kind}>{kind}</div>}
      {(image || icon) && (
        <figure className={clsx(styles.figure, icon && !image && styles.iconFigure)}>
          <Picture image={image || icon} icon={!image} alt={caption || title || ""} />
          {caption && <figcaption className={styles.caption}>{caption}</figcaption>}
        </figure>
      )}
      {pending && !image && !icon && <div className={styles.pending}>📷 Capture en jeu à venir</div>}
      <dl className={styles.rows}>{children}</dl>
    </aside>
  );
}

export function Info({ label, children }) {
  return (
    <div className={styles.row}>
      <dt className={styles.label}>{label}</dt>
      <dd className={styles.value}>{children}</dd>
    </div>
  );
}

export function InfoSection({ children }) {
  return <div className={styles.section}>{children}</div>;
}
