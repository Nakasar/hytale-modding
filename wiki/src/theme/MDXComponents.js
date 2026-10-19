// Composants disponibles dans toutes les pages du wiki sans import.
import MDXComponents from "@theme-original/MDXComponents";
import Infobox, { Info, InfoSection } from "@site/src/components/Infobox";

export default { ...MDXComponents, Infobox, Info, InfoSection };
