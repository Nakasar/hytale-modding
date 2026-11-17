// Copie les icônes des packs (Common/Icons et Common/UI des mods Vampires et Fractales) dans static/jeu/ avant
// chaque construction : les pages les citent en /jeu/..., et le site montre ainsi toujours les icônes des mods.
import { cpSync, existsSync, rmSync } from "node:fs";
import { fileURLToPath } from "node:url";

const mods = ["nakasar-vampires", "nakasar-fractals"];
const target = fileURLToPath(new URL("../static/jeu/", import.meta.url));

rmSync(target, { recursive: true, force: true });
for (const mod of mods) {
  const common = fileURLToPath(new URL(`../../mods/${mod}/src/main/resources/Common/`, import.meta.url));
  for (const folder of ["Icons", "UI"]) {
    if (existsSync(common + folder)) {
      cpSync(common + folder, target + folder, { recursive: true });
    }
  }
}
console.log(`Icônes copiées dans ${target}`);
