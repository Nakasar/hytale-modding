package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.codec.codecs.array.ArrayCodec;

/**
 * Le chantier en cours d'un village (étape 5), sauvegardé avec lui : le palier visé, l'instant de jeu où les travaux
 * finissent, les bâtiments en échafaudage et ceux sautés parce que leur emplacement était occupé.
 */
public final class ChantierState {

    public static final BuilderCodec<ChantierState> CODEC = BuilderCodec.builder(ChantierState.class, ChantierState::new)
            .append(new KeyedCodec<>("Tier", Codec.INTEGER), (c, v) -> c.tier = Tiers.clamp(v), c -> c.tier)
            .documentation("Palier que le chantier fait atteindre.")
            .add()
            .append(new KeyedCodec<>("Start", Codec.LONG), (c, v) -> c.start = v == null ? 0L : v, c -> c.start)
            .documentation("Début des travaux (secondes de jeu, GameClock.seconds).")
            .add()
            .append(new KeyedCodec<>("End", Codec.LONG), (c, v) -> c.end = v == null ? 0L : v, c -> c.end)
            .documentation("Fin des travaux (secondes de jeu).")
            .add()
            .append(new KeyedCodec<>("Buildings", new ArrayCodec<>(Codec.STRING, String[]::new)), (c, v) -> c.buildings = v == null ? new String[0] : v, c -> c.buildings)
            .documentation("Bâtiments en travaux (échafaudés, ou petits décors collés à la fin).")
            .add()
            .append(new KeyedCodec<>("Skipped", new ArrayCodec<>(Codec.STRING, String[]::new)), (c, v) -> c.skipped = v == null ? new String[0] : v, c -> c.skipped)
            .documentation("Bâtiments sautés : leur emplacement est occupé par des blocs posés par un joueur.")
            .add()
            .build();

    int tier;
    long start;
    long end;
    String[] buildings = new String[0];
    String[] skipped = new String[0];

    ChantierState() {
    }

    ChantierState(int tier, long start, long end, String[] buildings, String[] skipped) {
        this.tier = tier;
        this.start = start;
        this.end = end;
        this.buildings = buildings.clone();
        this.skipped = skipped.clone();
    }

    ChantierState copy() {
        return new ChantierState(tier, start, end, buildings, skipped);
    }

    public int tier() {
        return tier;
    }

    public long start() {
        return start;
    }

    public long end() {
        return end;
    }

    public String[] buildings() {
        return buildings.clone();
    }

    public String[] skipped() {
        return skipped.clone();
    }

    void finishAt(long value) {
        end = value;
    }
}
