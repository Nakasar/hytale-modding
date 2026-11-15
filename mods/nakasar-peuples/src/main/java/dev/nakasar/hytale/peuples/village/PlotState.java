package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;

/**
 * L'état d'un terrain libre (E1, E2) d'un village (étape 6 des bâtiments de métier), sauvegardé avec le village :
 * projet choisi (bâtiment du plan), chantier en cours, dernière démolition, piquets posés. Modifiable sur le thread du
 * monde ({@link Plots}).
 */
public final class PlotState {

    public static final BuilderCodec<PlotState> CODEC = BuilderCodec.builder(PlotState.class, PlotState::new)
            .append(new KeyedCodec<>("Id", Codec.STRING), (p, v) -> p.id = v == null ? "" : v, p -> p.id)
            .documentation("Terrain du plan (E1, E2).")
            .add()
            .append(new KeyedCodec<>("Project", Codec.STRING), (p, v) -> p.project = v == null || v.isBlank() ? null : v, p -> p.project)
            .documentation("Bâtiment du plan choisi pour le terrain (E1_<Projet>), ou absent.")
            .add()
            .append(new KeyedCodec<>("Start", Codec.LONG), (p, l) -> p.start = l == null ? 0L : l, p -> p.start)
            .documentation("Début du chantier (secondes de jeu), 0 : pas de chantier.")
            .add()
            .append(new KeyedCodec<>("End", Codec.LONG), (p, l) -> p.end = l == null ? 0L : l, p -> p.end)
            .documentation("Fin du chantier (secondes de jeu), 0 : pas de chantier.")
            .add()
            .append(new KeyedCodec<>("Demolished", Codec.LONG), (p, l) -> p.demolished = l == null ? Long.MIN_VALUE : l, p -> p.demolished)
            .documentation("Jour de jeu de la dernière démolition.")
            .add()
            .append(new KeyedCodec<>("Stakes", Codec.BOOLEAN), (p, b) -> p.stakes = b != null && b, p -> p.stakes)
            .documentation("Vrai si les piquets du terrain réservé sont posés.")
            .add()
            .build();

    String id = "";
    String project;
    long start;
    long end;
    long demolished = Long.MIN_VALUE;
    boolean stakes;

    PlotState() {
    }

    PlotState(String id) {
        this.id = id;
    }

    public String id() {
        return id;
    }

    /** Bâtiment du plan choisi, ou null. */
    public String project() {
        return project;
    }

    public long start() {
        return start;
    }

    public long end() {
        return end;
    }

    /** Vrai si le chantier du terrain est en cours. */
    public boolean working() {
        // Les secondes de jeu (GameClock.seconds) sont NÉGATIVES : l'horloge vanilla part de l'an 1 (WorldTimeResource.ZERO_YEAR),
        // avant l'époque Unix. Seul 0 veut dire « aucun » (bug du 2026-11-15 : « > 0 » rendait tout chantier invisible).
        return end != 0L;
    }

    public long demolished() {
        return demolished;
    }

    public boolean stakes() {
        return stakes;
    }

    void setProject(String value) {
        project = value;
    }

    void startWorks(long from, long to) {
        start = from;
        end = to;
    }

    void clearWorks() {
        start = 0;
        end = 0;
    }

    void setDemolished(long day) {
        demolished = day;
    }

    void setStakes(boolean value) {
        stakes = value;
    }
}
