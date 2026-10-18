package dev.nakasar.hytale.mobs;

import com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction;
import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;
import dev.nakasar.hytale.mobs.domination.DominatePlayerInteraction;
import dev.nakasar.hytale.mobs.domination.DominationDamageFilter;
import dev.nakasar.hytale.mobs.domination.Dominations;

/**
 * Point d'entrée du mod "Mobs".
 *
 * <p>Les mobs eux-mêmes sont des assets JSON (rôles, modèles, attaques : voir {@code src/main/resources/Server}).
 * Ce plugin n'ajoute que ce que le JSON ne sait pas faire : la Domination du Comte Vampire sur un joueur.
 * <ul>
 *   <li>{@code Nakasar_DominatePlayer} : interaction lancée par le comte sur le joueur visé ;</li>
 *   <li>{@link DominationDamageFilter} : annule les dégâts qu'un joueur dominé inflige à son dominateur.</li>
 * </ul>
 */
public final class MobsPlugin extends JavaPlugin {

    private static MobsPlugin instance;

    public MobsPlugin(JavaPluginInit init) {
        super(init);
        instance = this;
    }

    public static MobsPlugin get() {
        return instance;
    }

    @Override
    protected void setup() {
        getCodecRegistry(Interaction.CODEC).register(DominatePlayerInteraction.TYPE_ID,
                DominatePlayerInteraction.class, DominatePlayerInteraction.CODEC);
        getEntityStoreRegistry().registerSystem(new DominationDamageFilter());
        getLogger().atInfo().log("Nakasar Mobs : interaction %s et filtre de dégâts de la Domination enregistrés",
                DominatePlayerInteraction.TYPE_ID);
    }

    @Override
    protected void shutdown() {
        Dominations.clearAll();
    }
}
