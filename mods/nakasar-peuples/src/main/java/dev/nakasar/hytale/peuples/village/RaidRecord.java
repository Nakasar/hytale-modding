package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;

/**
 * Les raids d'un village (étape 6), sauvegardés avec lui : le raid attendu (nuit de jeu et cause), le raid en cours,
 * le dernier palier vu (un palier gagné attire un raid) et le bilan du dernier raid, affiché au tableau.
 *
 * <p>La nuit d'un raid est le jour de jeu de {@code GameClock.day} pendant cette nuit (le jour commence à 6 h : la nuit
 * du jour D va de 20 h le jour D à 6 h le lendemain). Le déroulé d'un raid (PNJ, minuterie) n'est pas sauvegardé : un
 * raid interrompu par un redémarrage reprend depuis l'annonce, sans pénalité.
 */
public final class RaidRecord {

    /** Aucune nuit. */
    public static final long NONE = Long.MIN_VALUE;

    public static final BuilderCodec<RaidRecord> CODEC = BuilderCodec.builder(RaidRecord.class, RaidRecord::new)
            .append(new KeyedCodec<>("Night", Codec.LONG), (r, v) -> r.night = v == null ? NONE : v, r -> r.night)
            .documentation("Nuit (jour de jeu) du raid attendu, ou absent.")
            .add()
            .append(new KeyedCodec<>("Cause", Codec.STRING), (r, v) -> r.cause = v, r -> r.cause)
            .documentation("Cause du raid attendu : Tier (palier gagné), Random, Request (demande de défense), Chain (veillée), Command.")
            .add()
            .append(new KeyedCodec<>("Active", Codec.BOOLEAN), (r, v) -> r.active = v != null && v, r -> r.active)
            .documentation("Vrai pendant un raid (remis à faux au redémarrage : le raid reprend depuis l'annonce).")
            .add()
            .append(new KeyedCodec<>("LastNight", Codec.LONG), (r, v) -> r.lastNight = v == null ? NONE : v, r -> r.lastNight)
            .documentation("Nuit du dernier raid joué jusqu'au bilan.")
            .add()
            .append(new KeyedCodec<>("TierSeen", Codec.INTEGER), (r, v) -> r.tierSeen = v == null ? -1 : v, r -> r.tierSeen)
            .documentation("Dernier palier vu par le système des raids : un palier plus haut attire un raid la nuit suivante.")
            .add()
            .append(new KeyedCodec<>("Won", Codec.INTEGER), (r, v) -> r.won = v == null ? 0 : v, r -> r.won)
            .add()
            .append(new KeyedCodec<>("Lost", Codec.INTEGER), (r, v) -> r.lost = v == null ? 0 : v, r -> r.lost)
            .add()
            .append(new KeyedCodec<>("LastResult", Codec.STRING), (r, v) -> r.lastResult = v, r -> r.lastResult)
            .documentation("Issue du dernier raid : Won ou Lost.")
            .add()
            .append(new KeyedCodec<>("LastRaiders", Codec.INTEGER), (r, v) -> r.lastRaiders = v == null ? 0 : v, r -> r.lastRaiders)
            .add()
            .append(new KeyedCodec<>("LastKilled", Codec.INTEGER), (r, v) -> r.lastKilled = v == null ? 0 : v, r -> r.lastKilled)
            .add()
            .append(new KeyedCodec<>("LastFallen", Codec.INTEGER), (r, v) -> r.lastFallen = v == null ? 0 : v, r -> r.lastFallen)
            .add()
            .append(new KeyedCodec<>("LastBurnt", Codec.STRING), (r, v) -> r.lastBurnt = v, r -> r.lastBurnt)
            .documentation("Bâtiment brûlé par le dernier raid perdu.")
            .add()
            .build();

    long night = NONE;
    String cause;
    boolean active;
    long lastNight = NONE;
    int tierSeen = -1;
    int won;
    int lost;
    String lastResult;
    int lastRaiders;
    int lastKilled;
    int lastFallen;
    String lastBurnt;

    public RaidRecord() {
    }

    RaidRecord copy() {
        RaidRecord c = new RaidRecord();
        c.night = night;
        c.cause = cause;
        c.active = active;
        c.lastNight = lastNight;
        c.tierSeen = tierSeen;
        c.won = won;
        c.lost = lost;
        c.lastResult = lastResult;
        c.lastRaiders = lastRaiders;
        c.lastKilled = lastKilled;
        c.lastFallen = lastFallen;
        c.lastBurnt = lastBurnt;
        return c;
    }

    public long night() {
        return night;
    }

    public String cause() {
        return cause;
    }

    public boolean scheduled() {
        return night != NONE;
    }

    public boolean active() {
        return active;
    }

    public long lastNight() {
        return lastNight;
    }

    public int tierSeen() {
        return tierSeen;
    }

    public int won() {
        return won;
    }

    public int lost() {
        return lost;
    }

    public String lastResult() {
        return lastResult;
    }

    public int lastRaiders() {
        return lastRaiders;
    }

    public int lastKilled() {
        return lastKilled;
    }

    public int lastFallen() {
        return lastFallen;
    }

    public String lastBurnt() {
        return lastBurnt;
    }

    public void schedule(long value, String why) {
        night = value;
        cause = why;
    }

    public void unschedule() {
        night = NONE;
        cause = null;
    }

    public void setActive(boolean value) {
        active = value;
    }

    public void setTierSeen(int value) {
        tierSeen = value;
    }

    /** Note le bilan d'un raid joué la nuit `value`. */
    public void record(long value, boolean victory, int raiders, int killed, int fallen, String burnt) {
        lastNight = value;
        lastResult = victory ? "Won" : "Lost";
        if (victory) {
            won++;
        } else {
            lost++;
        }
        lastRaiders = raiders;
        lastKilled = killed;
        lastFallen = fallen;
        lastBurnt = burnt;
        active = false;
        unschedule();
    }
}
