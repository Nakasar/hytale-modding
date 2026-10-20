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
import dev.nakasar.hytale.fractals.command.FractalCommand;
import dev.nakasar.hytale.fractals.observatory.DialInteraction;
import dev.nakasar.hytale.fractals.observatory.HarmonyCircleSystem;
import dev.nakasar.hytale.fractals.observatory.LeaveInteraction;
import dev.nakasar.hytale.fractals.observatory.Observatory;
import dev.nakasar.hytale.fractals.observatory.OpenArchInteraction;
import dev.nakasar.hytale.fractals.observatory.TrialDemoInteraction;
import dev.nakasar.hytale.fractals.observatory.TrialGolemSystem;
import dev.nakasar.hytale.fractals.observatory.TrialHitSystem;
import dev.nakasar.hytale.fractals.party.FallRescueSystem;
import dev.nakasar.hytale.fractals.party.FractalRuns;
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
 *
 * <p>Étape 2, l'entrée : le Fragment des Brumes ouvre l'Observatoire ({@code observatory}), où le cercle
 * d'harmonisation ({@link HarmonyCircleSystem}) forme le groupe, le cadran de l'Astrolabe ({@code Nakasar_Fractal_Dial})
 * règle le niveau et les arches ({@code Nakasar_Fractal_OpenArch}) ouvrent une instance par groupe ({@link FractalRuns}) ;
 * la pierre de retour ({@code Nakasar_Fractal_Leave}) y ramène. Golem d'essai ({@link TrialGolemSystem}) et son pupitre
 * ({@code Nakasar_Fractal_TrialDemo}), filet anti-chute ({@link FallRescueSystem}), commande {@code /fractale}.
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
        interactions.register(DialInteraction.TYPE_ID, DialInteraction.class, DialInteraction.CODEC);
        interactions.register(OpenArchInteraction.TYPE_ID, OpenArchInteraction.class, OpenArchInteraction.CODEC);
        interactions.register(LeaveInteraction.TYPE_ID, LeaveInteraction.class, LeaveInteraction.CODEC);
        interactions.register(TrialDemoInteraction.TYPE_ID, TrialDemoInteraction.class, TrialDemoInteraction.CODEC);

        var systems = getEntityStoreRegistry();
        systems.registerSystem(new TelegraphSystem());
        systems.registerSystem(new BossStun.Unload());
        systems.registerSystem(new MinionShieldSystem());
        systems.registerSystem(new ShieldUnloadSystem());
        systems.registerSystem(new BossBarSystem());
        systems.registerSystem(new HarmonyCircleSystem());
        systems.registerSystem(new TrialGolemSystem());
        systems.registerSystem(new TrialHitSystem());
        systems.registerSystem(new FallRescueSystem());

        getCommandRegistry().registerCommand(new FractalCommand());

        getLogger().atInfo().log("Nakasar Fractales : 9 types d'interaction (%s, %s, %s, %s, %s, %s, %s, %s, %s), systèmes et /fractale enregistrés",
                TelegraphInteraction.TYPE_ID, ChargeInteraction.TYPE_ID, StunSelfInteraction.TYPE_ID,
                SummonMinionsInteraction.TYPE_ID, CagePlayerInteraction.TYPE_ID, DialInteraction.TYPE_ID,
                OpenArchInteraction.TYPE_ID, LeaveInteraction.TYPE_ID, TrialDemoInteraction.TYPE_ID);
    }

    @Override
    protected void shutdown() {
        TelegraphSystem.clearAll();
        BossStun.clearAll();
        SummonMinionsInteraction.clearAll();
        BossBarSystem.clearAll();
        Observatory.clearAll();
        FractalRuns.clearAll();
    }
}
