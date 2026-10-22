package dev.nakasar.hytale.fractals.arena;

import java.util.Arrays;

/**
 * Consoles à activer en même temps (escalier mortel de l'Inclassable) : toutes doivent être activées dans une même
 * fenêtre de temps, plus longue en petit groupe ({@link #window}). Une console activée trop tôt s'éteint.
 */
public final class Consoles {

    private final long[] activated;
    private boolean done;

    public Consoles(int count) {
        activated = new long[count];
        Arrays.fill(activated, Long.MIN_VALUE);
    }

    /** Fenêtre (s) : 12 seul, 8 à deux, 4 à trois et plus (GDD : jamais impossible seul). */
    public static float window(int partySize) {
        return partySize <= 1 ? 12f : partySize == 2 ? 8f : 4f;
    }

    /** Active la console `index` à `now` (ns) ; vrai si toutes le sont alors dans la fenêtre. */
    public boolean activate(int index, long now, float windowSeconds) {
        if (done) {
            return true;
        }
        activated[index] = now;
        long limit = (long) (windowSeconds * 1_000_000_000L);
        for (long t : activated) {
            if (t == Long.MIN_VALUE || now - t > limit) {
                return false;
            }
        }
        done = true;
        return true;
    }

    /** Vrai si la console `index` est encore allumée (activée il y a moins de la fenêtre). */
    public boolean lit(int index, long now, float windowSeconds) {
        return done || (activated[index] != Long.MIN_VALUE && now - activated[index] <= (long) (windowSeconds * 1_000_000_000L));
    }

    /** Consoles encore allumées. */
    public int litCount(long now, float windowSeconds) {
        int n = 0;
        for (int i = 0; i < activated.length; i++) {
            if (lit(i, now, windowSeconds)) {
                n++;
            }
        }
        return n;
    }

    public boolean done() {
        return done;
    }

    public int size() {
        return activated.length;
    }

    public void reset() {
        done = false;
        Arrays.fill(activated, Long.MIN_VALUE);
    }
}
