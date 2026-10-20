package dev.nakasar.hytale.fractals;

import com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction;
import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;
import dev.nakasar.hytale.fractals.arena.Restores;
import dev.nakasar.hytale.fractals.boss.BossBarSystem;
import dev.nakasar.hytale.fractals.combat.BossStun;
import dev.nakasar.hytale.fractals.combat.ChargeInteraction;
import dev.nakasar.hytale.fractals.combat.StunSelfInteraction;
import dev.nakasar.hytale.fractals.combat.TelegraphInteraction;
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
import dev.nakasar.hytale.fractals.minions.MinionShieldSystem;
import dev.nakasar.hytale.fractals.minions.ShieldUnloadSystem;
import dev.nakasar.hytale.fractals.minions.SummonMinionsInteraction;
import dev.nakasar.hytale.fractals.prison.CagePlayerInteraction;

/**
 * Point d'entrée du mod « Fractales des Brumes » : les fractales de Guild Wars 2 portées dans Hytale, pour des groupes
 * de 1 à 5 joueurs (docs/fractales/gdd.md).
 *
 * <p>Étape 1 du GDD, le socle : les briques de combat du mod Vampires, copiées sans bibliothèque commune (Kevin,
 * 20 octobre 2026) sous ids {@code Nakasar_Fractal_} ; un correctif d'un côté se reporte à la main de l'autre.
 * <ul>
 *   <li>{@code Nakasar_Fractal_Telegraph} ({@link TelegraphSystem}) : attaque annoncée par une zone rouge au sol
 *       (cercle, cône, ligne, marque) qui touche ce qui s'y trouve encore au moment du coup ;</li>
 *   <li>{@code Nakasar_Fractal_Charge} : charge annoncée par une ligne rouge, étourdit le boss contre un mur ;</li>
 *   <li>{@code Nakasar_Fractal_StunSelf} ({@link BossStun}) : fenêtre de punition, IA gelée et dégâts subis +50 % ;</li>
 *   <li>{@code Nakasar_Fractal_SummonMinions} et {@link MinionShieldSystem} : serviteurs, liens visibles, boss
 *       invulnérable tant qu'ils vivent ;</li>
 *   <li>{@code Nakasar_Fractal_Cage} : envoie le joueur dans la cage la plus proche (cage de l'Archidevin) ;</li>
 *   <li>{@link BossBarSystem} : barre de vie de boss pour les joueurs proches ; {@code boss.GroupHealth} : vie selon
 *       la taille du groupe ;</li>
 *   <li>{@link Restores} : remise en place des blocs du décor, gardée sur disque.</li>
 * </ul>
 */
public final class FractalsPlugin extends JavaPlugin {

    private static FractalsPlugin instance;

    public FractalsPlugin(JavaPluginInit init) {
        super(init);
        instance = this;
    }

    public static FractalsPlugin get() {
        return instance;
    }

    @Override
    protected void setup() {
        Restores.load(getDataDirectory());
        var interactions = getCodecRegistry(Interaction.CODEC);
        interactions.register(TelegraphInteraction.TYPE_ID, TelegraphInteraction.class, TelegraphInteraction.CODEC);
        interactions.register(ChargeInteraction.TYPE_ID, ChargeInteraction.class, ChargeInteraction.CODEC);
        interactions.register(StunSelfInteraction.TYPE_ID, StunSelfInteraction.class, StunSelfInteraction.CODEC);
        interactions.register(SummonMinionsInteraction.TYPE_ID, SummonMinionsInteraction.class, SummonMinionsInteraction.CODEC);
        interactions.register(CagePlayerInteraction.TYPE_ID, CagePlayerInteraction.class, CagePlayerInteraction.CODEC);

        var systems = getEntityStoreRegistry();
        systems.registerSystem(new TelegraphSystem());
        systems.registerSystem(new BossStun.Unload());
        systems.registerSystem(new MinionShieldSystem());
        systems.registerSystem(new ShieldUnloadSystem());
        systems.registerSystem(new BossBarSystem());

        getLogger().atInfo().log("Nakasar Fractales : 5 types d'interaction (%s, %s, %s, %s, %s) et systèmes de combat enregistrés",
                TelegraphInteraction.TYPE_ID, ChargeInteraction.TYPE_ID, StunSelfInteraction.TYPE_ID,
                SummonMinionsInteraction.TYPE_ID, CagePlayerInteraction.TYPE_ID);
    }

    @Override
    protected void shutdown() {
        TelegraphSystem.clearAll();
        BossStun.clearAll();
        SummonMinionsInteraction.clearAll();
        BossBarSystem.clearAll();
    }
}
