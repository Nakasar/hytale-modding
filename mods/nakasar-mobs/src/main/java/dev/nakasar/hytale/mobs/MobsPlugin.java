package dev.nakasar.hytale.mobs;

import com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction;
import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;
import dev.nakasar.hytale.mobs.domination.DominatePlayerInteraction;
import dev.nakasar.hytale.mobs.domination.DominationDamageFilter;
import dev.nakasar.hytale.mobs.domination.Dominations;
import dev.nakasar.hytale.mobs.prison.ImprisonPlayerInteraction;

/**
 * Point d'entrée du mod "Mobs".
 *
 * <p>Les mobs eux-mêmes sont des assets JSON (rôles, modèles, attaques : voir {@code src/main/resources/Server}).
 * Ce plugin n'ajoute que ce que le JSON ne sait pas faire : la Domination du Comte Vampire sur un joueur et
 * l'emprisonnement du Capitaine de la garde.
 * <ul>
 *   <li>{@code Nakasar_DominatePlayer} : interaction lancée par le comte sur le joueur visé ;</li>
 *   <li>{@link DominationDamageFilter} : annule les dégâts qu'un joueur dominé inflige à son dominateur ;</li>
 *   <li>{@code Nakasar_ImprisonPlayer} : téléporte le joueur visé dans la cellule la plus proche du capitaine.</li>
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
        getCodecRegistry(Interaction.CODEC).register(ImprisonPlayerInteraction.TYPE_ID,
                ImprisonPlayerInteraction.class, ImprisonPlayerInteraction.CODEC);
        getEntityStoreRegistry().registerSystem(new DominationDamageFilter());
        getLogger().atInfo().log("Nakasar Mobs : interactions %s, %s et filtre de dégâts de la Domination enregistrés",
                DominatePlayerInteraction.TYPE_ID, ImprisonPlayerInteraction.TYPE_ID);
    }

    @Override
    protected void shutdown() {
        Dominations.clearAll();
    }
}
