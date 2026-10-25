package dev.nakasar.hytale.fractals.deepstone;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;

import java.util.List;

/**
 * Deux runes (plaques de pression) à presser ensemble : chacune reste allumée {@value #GRACE} s après qu'on l'a
 * quittée, assez pour qu'un joueur seul coure de l'une à l'autre (GW2 : un portail suffit).
 */
final class RunePair {

    static final float GRACE = 3f;

    private final double[][] runes;
    private final long[] pressed;
    private boolean solved;

    RunePair(double[][] runes) {
        this.runes = runes;
        this.pressed = new long[runes.length];
    }

    boolean solved() {
        return solved;
    }

    /** Vrai la première fois que les deux runes sont allumées ensemble. */
    boolean step(Store<EntityStore> store, Deepstone.State st, List<PlayerRef> players) {
        if (solved) {
            return false;
        }
        long now = System.nanoTime();
        for (int i = 0; i < runes.length; i++) {
            for (PlayerRef p : players) {
                if (Deepstone.onRune(store, p, runes[i])) {
                    if (pressed[i] == 0 || now - pressed[i] > Telegraphs.seconds(1f)) {
                        Telegraphs.particle(store, "Nakasar_Fractal_Rune_Glow", Spawns.point(runes[i]), 1f);
                        Deepstone.tell(st, p, "rune.one");
                    }
                    pressed[i] = now;
                }
            }
        }
        for (long t : pressed) {
            if (t == 0 || now - t > Telegraphs.seconds(GRACE)) {
                return false;
            }
        }
        solved = true;
        for (double[] at : runes) {
            Telegraphs.particle(store, "Nakasar_Fractal_Rune_Glow", Spawns.point(at), 2f);
        }
        return true;
    }
}
