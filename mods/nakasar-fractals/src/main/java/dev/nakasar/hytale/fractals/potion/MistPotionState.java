package dev.nakasar.hytale.fractals.potion;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.Component;
import com.hypixel.hytale.component.ComponentType;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.potion.MistPotions.Kind;

import java.util.Arrays;

/**
 * Potions des Brumes bues par un joueur, sauvegardées avec lui (id {@value #ID}) : piles et secondes restantes de
 * chaque type. Le temps ne s'écoule que quand le joueur est en jeu ({@link MistPotionSystem}), et la mort ne retire
 * rien (comme dans GW2) ; le retour dans le monde, hors fractales et Observatoire, retire tout (Kevin, 25 octobre 2026).
 */
public final class MistPotionState implements Component<EntityStore> {

    public static final String ID = "Nakasar_Fractal_Mist_Potions";

    public static final BuilderCodec<MistPotionState> CODEC = BuilderCodec.builder(MistPotionState.class, MistPotionState::new)
            .append(new KeyedCodec<>("Stacks", Codec.INT_ARRAY), (s, v) -> s.setStacks(v), s -> s.stacks.clone())
            .documentation("Piles par type (Offensive, Mobility, Defensive).")
            .add()
            .append(new KeyedCodec<>("Seconds", Codec.FLOAT_ARRAY), (s, v) -> s.setSeconds(v), s -> s.seconds.clone())
            .documentation("Secondes restantes par type (Offensive, Mobility, Defensive).")
            .add()
            .build();

    private static ComponentType<EntityStore, MistPotionState> componentType;

    private int[] stacks = new int[Kind.values().length];
    private float[] seconds = new float[Kind.values().length];
    /** Endurance relevée au passage précédent de {@link MistPotionSystem} (NaN : pas encore relevée). */
    float lastStamina = Float.NaN;
    /** Effet affiché par type, posé par {@link MistPotionSystem} (null : aucun). */
    final String[] shown = new String[Kind.values().length];
    /** Faux tant que {@link MistPotionSystem} n'a pas retiré les crans restés d'une session précédente. */
    boolean swept;

    public static ComponentType<EntityStore, MistPotionState> getComponentType() {
        return componentType;
    }

    public static void setComponentType(ComponentType<EntityStore, MistPotionState> type) {
        componentType = type;
    }

    public int stacks(Kind kind) {
        return seconds[kind.ordinal()] > 0f ? stacks[kind.ordinal()] : 0;
    }

    public float seconds(Kind kind) {
        return stacks[kind.ordinal()] > 0 ? Math.max(0f, seconds[kind.ordinal()]) : 0f;
    }

    /** Boire : `added` piles de plus (au plus {@link MistPotions#MAX_STACKS}), durée remise à 1 h ; rend les piles. */
    public int drink(Kind kind, int added) {
        int k = kind.ordinal();
        stacks[k] = Math.max(1, Math.min(MistPotions.MAX_STACKS, stacks(kind) + added));
        seconds[k] = MistPotions.DURATION;
        return stacks[k];
    }

    /** Retire toutes les piles (retour dans le monde, hors fractales et Observatoire). */
    public void clear() {
        Arrays.fill(stacks, 0);
        Arrays.fill(seconds, 0f);
    }

    /** Fait passer `dt` secondes ; un type arrivé au bout perd toutes ses piles. */
    public void elapse(float dt) {
        for (int k = 0; k < stacks.length; k++) {
            if (stacks[k] > 0) {
                seconds[k] -= dt;
                if (seconds[k] <= 0f) {
                    stacks[k] = 0;
                    seconds[k] = 0f;
                }
            }
        }
    }

    /** Vrai quand plus aucune potion n'agit ni n'est affichée : {@link MistPotionSystem} n'a plus rien à faire. */
    public boolean isIdle() {
        if (!swept || !isEmpty()) {
            return false;
        }
        for (String id : shown) {
            if (id != null) {
                return false;
            }
        }
        return true;
    }

    public boolean isEmpty() {
        for (int k = 0; k < stacks.length; k++) {
            if (stacks[k] > 0 && seconds[k] > 0f) {
                return false;
            }
        }
        return true;
    }

    private void setStacks(int[] values) {
        stacks = new int[Kind.values().length];
        for (int k = 0; values != null && k < Math.min(values.length, stacks.length); k++) {
            stacks[k] = Math.max(0, Math.min(MistPotions.MAX_STACKS, values[k]));
        }
    }

    private void setSeconds(float[] values) {
        seconds = new float[Kind.values().length];
        for (int k = 0; values != null && k < Math.min(values.length, seconds.length); k++) {
            seconds[k] = Math.max(0f, Math.min(MistPotions.DURATION, values[k]));
        }
    }

    @Override
    public Component<EntityStore> clone() {
        MistPotionState copy = new MistPotionState();
        copy.stacks = stacks.clone();
        copy.seconds = seconds.clone();
        copy.lastStamina = lastStamina;
        System.arraycopy(shown, 0, copy.shown, 0, shown.length);
        copy.swept = swept;
        return copy;
    }
}
