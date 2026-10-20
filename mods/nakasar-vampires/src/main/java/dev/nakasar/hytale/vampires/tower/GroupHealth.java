package dev.nakasar.hytale.vampires.tower;

import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.modules.entitystats.modifier.Modifier;
import com.hypixel.hytale.server.core.modules.entitystats.modifier.StaticModifier;

/**
 * Vie des boss de la tour selon la taille du groupe, comme les rencontres de Deepworks : × (1 + {@value #PER_PLAYER}
 * par joueur de plus dans l'arène), posée à l'engagement et retirée à la remise à zéro. La part de vie déjà perdue
 * est conservée (le premier coup qui engage le combat n'est pas effacé).
 */
final class GroupHealth {

    static final float PER_PLAYER = 0.55f;

    private GroupHealth() {
    }

    static float multiplier(int players) {
        return 1f + PER_PLAYER * (Math.max(1, players) - 1);
    }

    static void apply(EntityStatMap stats, String modifier, float multiplier) {
        if (stats == null) {
            return;
        }
        int healthIndex = DefaultEntityStatTypes.getHealth();
        EntityStatValue health = stats.get(healthIndex);
        float fraction = health == null ? 1f : health.get() / Math.max(1f, health.getMax());
        stats.putModifier(healthIndex, modifier, new StaticModifier(Modifier.ModifierTarget.MAX,
                StaticModifier.CalculationType.MULTIPLICATIVE, multiplier));
        health = stats.get(healthIndex);
        if (health != null) {
            stats.setStatValue(healthIndex, health.getMax() * fraction);
        }
    }

    static void clear(EntityStatMap stats, String modifier) {
        if (stats == null) {
            return;
        }
        int healthIndex = DefaultEntityStatTypes.getHealth();
        stats.removeModifier(healthIndex, modifier);
        stats.maximizeStatValue(healthIndex);
    }
}
