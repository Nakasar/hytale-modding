// Barre du haut d'origine, suivie de la barre de sections du mod ouvert. Pose aussi data-mod sur <html>
// (rendu serveur compris, donc sans flash de couleur) : la teinte du mod vient de src/css/custom.css.
import React from "react";
import Navbar from "@theme-original/Navbar";
import Head from "@docusaurus/Head";
import { useLocation } from "@docusaurus/router";
import useDocusaurusContext from "@docusaurus/useDocusaurusContext";
import ModBar from "@site/src/components/ModBar";
import { modOf } from "@site/src/mods";

export default function NavbarWrapper(props) {
  const { pathname } = useLocation();
  const { siteConfig } = useDocusaurusContext();
  const base = siteConfig.baseUrl.replace(/\/$/, "");
  const path = pathname.startsWith(base) ? pathname.slice(base.length) || "/" : pathname;
  const mod = modOf(path);
  return (
    <>
      <Head>
        <html data-mod={mod ? mod.id : "commun"} />
      </Head>
      <div className="nk-header">
        <Navbar {...props} />
        {mod && <ModBar mod={mod} path={path} />}
      </div>
    </>
  );
}
