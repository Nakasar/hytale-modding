package dev.nakasar.hytale.peuples.workshop;

import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.WorkshopState;

/**
 * Les catégories des projets de terrain (Kevin, 2026-11-16) : au plus un projet par catégorie, sauf l'Artisanat
 * (jusqu'à {@value #CRAFT_MAX}), et leurs effets sur le village.
 * <ul>
 *   <li>{@value #DEFENSE} (Caserne) : 1 + niveau gardes de plus autour du cœur en raid ; spécialité {@value #GARRISON} :
 *   +1 garde dans chaque lieu-dit tenu, chaque ouvrage et chaque expédition ;</li>
 *   <li>{@value #DIPLOMACY} (Ambassade, l'ancienne Maison du conseil) : règles du conseil (world/Allegiance) ;</li>
 *   <li>{@value #KNOWLEDGE} (Bibliothèque) : savoir-faire +{@value #KNOWLEDGE_PERCENT} % pour tous les bâtiments de métier ;</li>
 *   <li>{@value #CULT} (Temple) : essor +{@value #ESSOR_PERCENT} % ; spécialité {@value #PROTECTION} : un raid perdu ne
 *   brûle un bâtiment qu'une fois sur deux ;</li>
 *   <li>{@value #CRAFT} (ateliers) : consomment leurs {@code Inputs} chaque matin (workshop/Inputs).</li>
 * </ul>
 */
public final class Projects {

    public static final String DEFENSE = "Defense";
    public static final String DIPLOMACY = "Diplomatie";
    public static final String KNOWLEDGE = "Savoir";
    public static final String CULT = "Culte";
    public static final String CRAFT = "Artisanat";
    public static final int CRAFT_MAX = 3;
    public static final String GARRISON = "Garnison";
    public static final String MILITIA = "Milice";
    public static final String PROTECTION = "Protection";
    public static final int KNOWLEDGE_PERCENT = 15;
    public static final int ESSOR_PERCENT = 10;

    private Projects() {
    }

    /** Nombre de projets de la catégorie qu'un terrain peut encore accueillir dans ce village. */
    public static int max(String category) {
        return CRAFT.equals(category) ? CRAFT_MAX : 1;
    }

    /** Le projet ouvert (bâti, villageois arrivé) de cette catégorie, ou null. */
    public static Workshop opened(Village village, String category) {
        for (Workshop w : Workshops.opened(village)) {
            if (category.equals(w.category()) && !w.legacy()) {
                return w;
            }
        }
        return null;
    }

    /** Niveau du projet ouvert de la catégorie (0 sans). */
    public static int level(Village village, String category) {
        Workshop w = opened(village, category);
        return w == null ? 0 : village.workshop(w.getId()).level();
    }

    /** Vrai si le projet ouvert de la catégorie a cette spécialité (niveau II et plus). */
    public static boolean specialty(Village village, String category, String specialty) {
        Workshop w = opened(village, category);
        if (w == null) {
            return false;
        }
        WorkshopState s = village.workshop(w.getId());
        return s.level() >= Workshops.SPECIALTY_LEVEL && specialty.equals(s.specialty());
    }

    /** Gardes de plus de la Caserne en raid : 1 + son niveau. */
    public static int raidGuards(Village village) {
        int level = level(village, DEFENSE);
        return level <= 0 ? 0 : 1 + level;
    }

    /** +1 garde (lieux-dits, ouvrages, expéditions) avec la spécialité Garnison de la Caserne. */
    public static int garrisonBonus(Village village) {
        return village != null && specialty(village, DEFENSE, GARRISON) ? 1 : 0;
    }

    /** Savoir-faire gagné avec la Bibliothèque (+15 %, arrondi au-dessus). */
    public static int knowledge(Village village, int gained) {
        return gained > 0 && opened(village, KNOWLEDGE) != null ? (gained * (100 + KNOWLEDGE_PERCENT) + 99) / 100 : gained;
    }

    /** Essor gagné avec le Temple (+10 %, arrondi au-dessus). */
    public static int essor(Village village, int gained) {
        return gained > 0 && opened(village, CULT) != null ? (gained * (100 + ESSOR_PERCENT) + 99) / 100 : gained;
    }

    /** Vrai si le Temple protège le village de l'incendie de ce raid perdu (une fois sur deux). */
    public static boolean spared(Village village) {
        return specialty(village, CULT, PROTECTION) && java.util.concurrent.ThreadLocalRandom.current().nextBoolean();
    }
}
