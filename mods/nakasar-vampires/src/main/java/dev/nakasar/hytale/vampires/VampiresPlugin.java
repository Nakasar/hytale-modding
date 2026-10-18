package dev.nakasar.hytale.vampires;

import com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction;
import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;
import dev.nakasar.hytale.vampires.allegiance.AllegianceAttitudeSystem;
import dev.nakasar.hytale.vampires.allegiance.AllegianceDamageFilter;
import dev.nakasar.hytale.vampires.domination.DominateInteraction;
import dev.nakasar.hytale.vampires.domination.DominatePlayerInteraction;
import dev.nakasar.hytale.vampires.domination.DominationExpirySystem;
import dev.nakasar.hytale.vampires.domination.Dominations;
import dev.nakasar.hytale.vampires.prison.ImprisonPlayerInteraction;
import dev.nakasar.hytale.vampires.rune.DrainBeamInteraction;
import dev.nakasar.hytale.vampires.rune.RootNpcInteraction;
import dev.nakasar.hytale.vampires.rune.TeleportCasterToImpactInteraction;

/**
 * Point d'entrée du mod "Vampires".
 *
 * <p>Le contenu (runes, autel, lance, mobs, fragment Halloween) est fait d'assets JSON (voir
 * {@code src/main/resources/Server}). Ce plugin n'ajoute que ce que le JSON vanilla ne sait pas faire :
 * <ul>
 *   <li>{@code Nakasar_TeleportCasterToImpact} : téléporte le lanceur au point d'impact d'un projectile
 *       (rune Téléportation) ;</li>
 *   <li>{@code Nakasar_Dominate} : fait changer de camp un PNJ, amical envers le lanceur et ennemi de ses anciens
 *       alliés, pendant un temps donné (rune Domination) ;</li>
 *   <li>{@code Nakasar_RootNpc} : gèle l'IA d'un PNJ pendant un temps donné, car l'effet de statut
 *       {@code MovementEffects.DisableAll} n'arrête que les joueurs (rune Chaînes spectrales) ;</li>
 *   <li>{@code Nakasar_DrainBeam} : fait voyager des particules de la cible vers le lanceur
 *       (rune Vol de vie) ;</li>
 *   <li>{@code Nakasar_DominatePlayer} : Domination du Comte Vampire sur le joueur visé ;</li>
 *   <li>{@code Nakasar_ImprisonPlayer} : téléporte le joueur visé dans la cellule la plus proche du Capitaine ;</li>
 *   <li>les camps ({@link AllegianceAttitudeSystem}, {@link AllegianceDamageFilter},
 *       {@link DominationExpirySystem}) : les mobs du fragment sont alliés, la Domination retourne leur allégeance.</li>
 * </ul>
 */
public final class VampiresPlugin extends JavaPlugin {

    private static VampiresPlugin instance;

    public VampiresPlugin(JavaPluginInit init) {
        super(init);
        instance = this;
    }

    public static VampiresPlugin get() {
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
        interactions.register(DrainBeamInteraction.TYPE_ID,
                DrainBeamInteraction.class, DrainBeamInteraction.CODEC);
        interactions.register(DominatePlayerInteraction.TYPE_ID,
                DominatePlayerInteraction.class, DominatePlayerInteraction.CODEC);
        interactions.register(ImprisonPlayerInteraction.TYPE_ID,
                ImprisonPlayerInteraction.class, ImprisonPlayerInteraction.CODEC);

        var systems = getEntityStoreRegistry();
        systems.registerSystem(new AllegianceAttitudeSystem());
        systems.registerSystem(new AllegianceDamageFilter());
        systems.registerSystem(new DominationExpirySystem());

        getLogger().atInfo().log("Nakasar Vampires : 6 types d'interaction (%s, %s, %s, %s, %s, %s) et systèmes des camps enregistrés",
                TeleportCasterToImpactInteraction.TYPE_ID, DominateInteraction.TYPE_ID, RootNpcInteraction.TYPE_ID,
                DrainBeamInteraction.TYPE_ID, DominatePlayerInteraction.TYPE_ID, ImprisonPlayerInteraction.TYPE_ID);
    }

    @Override
    protected void shutdown() {
        RootNpcInteraction.clearAll();
        Dominations.clearAll();
    }
}
