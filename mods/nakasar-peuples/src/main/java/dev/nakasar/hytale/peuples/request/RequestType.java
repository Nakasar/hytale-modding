package dev.nakasar.hytale.peuples.request;

import java.util.Locale;

/**
 * Les six types de demandes du tableau (GDD, section Les demandes du tableau), chacun calqué sur une tâche du système
 * d'objectifs vanilla :
 * <ul>
 *   <li>{@link #GATHER} récolte (Gather + dépôt) et {@link #CRAFT} fabrication (Craft + dépôt) : des objets à poser
 *       dans le dépôt du village (ou à rendre depuis son sac) ;</li>
 *   <li>{@link #HUNT} chasse (KillNPC / Bounty) : une bande apparaît à son repaire, chaque mort compte ;</li>
 *   <li>{@link #DELIVERY} livraison (UseEntity + objet marqué) : porter la missive reçue à un guetteur éloigné ;</li>
 *   <li>{@link #ESCORT} escorte (PNJ suiveur + ReachLocation) : ramener un captif jusqu'au cœur du village ;</li>
 *   <li>{@link #DEFENSE} défense (événement de monde) : une nuit, repousser l'attaque qui vient sur le village.
 *       Premier jet d'une veille ; les vrais raids (moteur des brèches) arrivent à l'étape 6.</li>
 * </ul>
 */
public enum RequestType {
    GATHER("Gather"),
    CRAFT("Craft"),
    HUNT("Hunt"),
    DELIVERY("Delivery"),
    ESCORT("Escort"),
    DEFENSE("Defense");

    private final String id;

    RequestType(String id) {
        this.id = id;
    }

    /** Id dans les assets ({@code "Type": "Gather"}). */
    public String id() {
        return id;
    }

    /** Vrai pour les demandes remplies en déposant des objets. */
    public boolean usesDeposit() {
        return this == GATHER || this == CRAFT;
    }

    /** Vrai pour les demandes qui ont un lieu hors du village (repaire, guetteur, captif). */
    public boolean hasSite() {
        return this == HUNT || this == DELIVERY || this == ESCORT;
    }

    /** Clé de traduction du nom du type. */
    public String nameKey() {
        return "nakasar_peuples.request.type." + id;
    }

    public static RequestType byId(String id) {
        if (id != null) {
            for (RequestType t : values()) {
                if (t.id.equalsIgnoreCase(id) || t.name().equals(id.toUpperCase(Locale.ROOT))) {
                    return t;
                }
            }
        }
        return null;
    }
}
