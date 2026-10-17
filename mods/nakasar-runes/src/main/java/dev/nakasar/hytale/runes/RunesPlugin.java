package dev.nakasar.hytale.runes;

import com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction;
import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;
import dev.nakasar.hytale.runes.interaction.DominateInteraction;
import dev.nakasar.hytale.runes.interaction.RootNpcInteraction;
import dev.nakasar.hytale.runes.interaction.TeleportCasterToImpactInteraction;

/**
 * Point d'entrée du mod "Runes".
 *
 * <p>Les runes elles-mêmes sont des assets JSON (voir {@code src/main/resources/Server}). Ce plugin
 * n'ajoute que les trois types d'interaction que le JSON vanilla ne sait pas faire :
 * <ul>
 *   <li>{@code Nakasar_TeleportCasterToImpact} : téléporte le lanceur au point d'impact d'un projectile
 *       (rune Téléportation) ;</li>
 *   <li>{@code Nakasar_Dominate} : rend un PNJ amical envers le lanceur pendant un temps donné
 *       (rune Domination) ;</li>
 *   <li>{@code Nakasar_RootNpc} : gèle l'IA d'un PNJ pendant un temps donné, car l'effet de statut
 *       {@code MovementEffects.DisableAll} n'arrête que les joueurs (rune Chaînes spectrales).</li>
 * </ul>
 */
public final class RunesPlugin extends JavaPlugin {

    private static RunesPlugin instance;

    public RunesPlugin(JavaPluginInit init) {
        super(init);
        instance = this;
    }

    public static RunesPlugin get() {
        return instance;
    }

    @Override
    protected void setup() {
        var interactions = getCodecRegistry(Interaction.CODEC);
        interactions.register(TeleportCasterToImpactInteraction.TYPE_ID,
                TeleportCasterToImpactInteraction.class, TeleportCasterToImpactInteraction.CODEC);
        interactions.register(DominateInteraction.TYPE_ID,
                DominateInteraction.class, DominateInteraction.CODEC);
        interactions.register(RootNpcInteraction.TYPE_ID,
                RootNpcInteraction.class, RootNpcInteraction.CODEC);
        getLogger().atInfo().log("Nakasar Runes : 3 types d'interaction enregistrés (%s, %s, %s)",
                TeleportCasterToImpactInteraction.TYPE_ID, DominateInteraction.TYPE_ID, RootNpcInteraction.TYPE_ID);
    }

    @Override
    protected void shutdown() {
        RootNpcInteraction.clearAll();
    }
}
