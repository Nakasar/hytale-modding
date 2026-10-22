package dev.nakasar.hytale.fractals.instability;

import com.hypixel.hytale.server.core.Message;

/** Les 8 instabilités de la saison 1 (GDD, « Instabilités et groupes de 1 à 5 »), d'après celles de GW2. */
public enum Instability {
    /** Les ennemis explosent à leur mort (cercle rouge de 1,5 s). */
    LAST_LAUGH("LastLaugh", false),
    /** Les joueurs laissent des flaques de poison derrière eux. */
    TOXIC_TRAIL("ToxicTrail", false),
    /** Dégâts si un allié est à moins de 2 blocs (en groupe seulement). */
    SOCIAL_AWKWARDNESS("SocialAwkwardness", true),
    /** Dégâts infligés +15 % près d'un allié, -15 % loin de tous (en groupe seulement). */
    STICK_TOGETHER("StickTogether", true),
    /** Un joueur au hasard pulse des dégâts autour de lui. */
    FLUX_BOMB("FluxBomb", false),
    /** À la mort d'un ennemi, ses alliés proches frappent plus fort. */
    VENGEANCE("Vengeance", false),
    /** Les coups ennemis repoussent beaucoup plus fort. */
    SLIPPERY_SLOPE("SlipperySlope", false),
    /** Des nuées de corbeaux arrivent en combat. */
    BIRDS("Birds", false);

    public static final String LANG = "nakasar_fractals_instabilities.";

    private final String id;
    private final boolean groupOnly;

    Instability(String id, boolean groupOnly) {
        this.id = id;
        this.groupOnly = groupOnly;
    }

    public String id() {
        return id;
    }

    /** Vrai si elle n'a pas de sens seul : un joueur seul en tire une autre. */
    public boolean groupOnly() {
        return groupOnly;
    }

    public Message title() {
        return Message.translation(LANG + id + ".name");
    }

    public Message description() {
        return Message.translation(LANG + id + ".description");
    }
}
