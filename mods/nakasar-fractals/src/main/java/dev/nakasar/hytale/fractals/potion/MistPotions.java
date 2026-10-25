package dev.nakasar.hytale.fractals.potion;

import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.party.FractalCatalog;

/**
 * Potions des Brumes (les « Mist potions » de GW2, Kevin, 25 octobre 2026) : trois buffs de 1 h qui se cumulent
 * jusqu'à {@value #MAX_STACKS} piles et n'agissent que dans une fractale (pas dans l'Observatoire ni dans le monde) :
 * <ul>
 *   <li>Offensive : dégâts infligés +3 % par pile ({@link MistPotionDamageFilter}) ;</li>
 *   <li>Mobilité : course +5 % par pile (effet {@code HorizontalSpeedMultiplier}) et endurance +10 % par pile
 *   ({@link MistPotionSystem}) ;</li>
 *   <li>Défensive : dégâts subis -5 % par pile, sauf l'agonie ({@link MistPotionDamageFilter}).</li>
 * </ul>
 * Retourner dans le monde (hors fractales et Observatoire) retire toutes les piles. Piles et durées sont sauvegardées
 * avec le joueur ({@link MistPotionState}) ; les effets affichés en sont le reflet,
 * posés par {@link MistPotionSystem}. Assets : tools/generate_potions.py.
 */
public final class MistPotions {

    public static final int MAX_STACKS = 5;
    public static final float DURATION = 3600f;
    private static final String EFFECT_PREFIX = "Nakasar_Fractal_Mist_";
    static final String MESSAGES = "nakasar_fractals_potions.";

    /** Les trois potions : id du type (assets et clé JSON {@code Potion}) et bonus par pile. */
    public enum Kind {
        OFFENSIVE("Offensive", 0.03f),
        MOBILITY("Mobility", 0.05f),
        DEFENSIVE("Defensive", 0.05f);

        /** Mobilité : part d'endurance récupérée en plus, par pile. */
        public static final float STAMINA_PER_STACK = 0.10f;

        public final String id;
        public final float perStack;

        Kind(String id, float perStack) {
            this.id = id;
            this.perStack = perStack;
        }

        public static Kind of(String id) {
            for (Kind kind : values()) {
                if (kind.id.equalsIgnoreCase(id)) {
                    return kind;
                }
            }
            return null;
        }

        /** Effet affiché pour `stacks` piles : actif dans une fractale, en sommeil (gris, sans bonus) ailleurs. */
        public String effect(int stacks, boolean active) {
            return EFFECT_PREFIX + id + "_" + stacks + (active ? "" : "_Dormant");
        }

        public Message displayName() {
            return Message.translation(MESSAGES + "kind." + id);
        }
    }

    private MistPotions() {
    }

    /** Vrai dans une instance de fractale (les potions y agissent). */
    public static boolean active(World world) {
        return FractalCatalog.fractalOf(world) != null;
    }

    /** Vrai dans une fractale ou l'Observatoire : ailleurs (le monde), les potions sont retirées. */
    public static boolean kept(World world) {
        return active(world) || FractalCatalog.isObservatory(world);
    }

    /** Piles de `kind` du joueur (0 sans potion ou si ce n'est pas un joueur), sans regarder le monde. */
    public static int stacks(ComponentAccessor<EntityStore> accessor, Ref<EntityStore> player, Kind kind) {
        if (player == null || !player.isValid()) {
            return 0;
        }
        MistPotionState state = accessor.getComponent(player, MistPotionState.getComponentType());
        return state == null ? 0 : state.stacks(kind);
    }
}
