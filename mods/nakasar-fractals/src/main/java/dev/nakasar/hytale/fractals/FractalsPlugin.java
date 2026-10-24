package dev.nakasar.hytale.fractals;

import com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction;
import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;
import dev.nakasar.hytale.fractals.arena.Restores;
import dev.nakasar.hytale.fractals.boss.BossBarSystem;
import dev.nakasar.hytale.fractals.boss.PinnedHealth;
import dev.nakasar.hytale.fractals.cliffside.Cliffside;
import dev.nakasar.hytale.fractals.cliffside.CliffsideDamageFilter;
import dev.nakasar.hytale.fractals.cliffside.CliffsideSystem;
import dev.nakasar.hytale.fractals.cliffside.CliffsideUseInteraction;
import dev.nakasar.hytale.fractals.combat.BossStun;
import dev.nakasar.hytale.fractals.combat.ChargeInteraction;
import dev.nakasar.hytale.fractals.combat.HealFoesInteraction;
import dev.nakasar.hytale.fractals.combat.HitShield;
import dev.nakasar.hytale.fractals.combat.PullInteraction;
import dev.nakasar.hytale.fractals.instability.Instabilities;
import dev.nakasar.hytale.fractals.instability.InstabilitySystem;
import dev.nakasar.hytale.fractals.stage.FoeDeathSystem;
import dev.nakasar.hytale.fractals.stage.StageDamageFilter;
import dev.nakasar.hytale.fractals.stage.StageSystem;
import dev.nakasar.hytale.fractals.stage.StageUseInteraction;
import dev.nakasar.hytale.fractals.stage.Stages;
import dev.nakasar.hytale.fractals.stage.ThrowItemInteraction;
import dev.nakasar.hytale.fractals.uncategorized.Uncategorized;
import dev.nakasar.hytale.fractals.solidocean.SolidOcean;
import dev.nakasar.hytale.fractals.snowblind.Snowblind;
import dev.nakasar.hytale.fractals.swampland.Swampland;
import dev.nakasar.hytale.fractals.volcanic.Volcanic;
import dev.nakasar.hytale.fractals.combat.StunSelfInteraction;
import dev.nakasar.hytale.fractals.combat.TelegraphInteraction;
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
import dev.nakasar.hytale.fractals.minions.MinionShieldSystem;
import dev.nakasar.hytale.fractals.minions.ShieldUnloadSystem;
import dev.nakasar.hytale.fractals.minions.SummonMinionsInteraction;
import dev.nakasar.hytale.fractals.command.FractalCommand;
import dev.nakasar.hytale.fractals.defiance.Defiance;
import dev.nakasar.hytale.fractals.defiance.DefianceDamageSystem;
import dev.nakasar.hytale.fractals.defiance.OpenDefianceInteraction;
import dev.nakasar.hytale.fractals.hammer.Hammer;
import dev.nakasar.hytale.fractals.hammer.HammerDamageSystem;
import dev.nakasar.hytale.fractals.hammer.HammerDropSystem;
import dev.nakasar.hytale.fractals.hammer.HammerPickupSystem;
import dev.nakasar.hytale.fractals.hammer.HammerSystem;
import dev.nakasar.hytale.fractals.observatory.HarmonyCircleSystem;
import dev.nakasar.hytale.fractals.observatory.LeaveInteraction;
import dev.nakasar.hytale.fractals.observatory.Observatory;
import dev.nakasar.hytale.fractals.observatory.HarmonizeInteraction;
import dev.nakasar.hytale.fractals.observatory.OpenConsoleInteraction;
import dev.nakasar.hytale.fractals.observatory.OpenShopInteraction;
import dev.nakasar.hytale.fractals.observatory.DailyBoardInteraction;
import dev.nakasar.hytale.fractals.observatory.TrialDemoInteraction;
import dev.nakasar.hytale.fractals.observatory.ObservatoryNpcSystem;
import dev.nakasar.hytale.fractals.observatory.TrialHitSystem;
import dev.nakasar.hytale.fractals.observatory.SelectionItemsSystem;
import dev.nakasar.hytale.fractals.party.ClaimRewardInteraction;
import dev.nakasar.hytale.fractals.party.FallRescueSystem;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import dev.nakasar.hytale.fractals.prison.CagePlayerInteraction;
import dev.nakasar.hytale.fractals.progress.AgonySystem;
import dev.nakasar.hytale.fractals.progress.FractalProgress;
import dev.nakasar.hytale.fractals.progress.OpenBagInteraction;
import dev.nakasar.hytale.fractals.progress.OpenInfusionsInteraction;

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
 * d'harmonisation ({@link HarmonyCircleSystem}) forme le groupe, la console de sélection
 * ({@code Nakasar_Fractal_OpenConsole}) reçoit le noyau et le diapason pris aux distributeurs (boutiques gratuites), et
 * le meneur lance depuis un résonateur ({@code Nakasar_Fractal_Harmonize}) une instance par groupe ({@link FractalRuns}) ;
 * la pierre de retour ({@code Nakasar_Fractal_Leave}) y ramène. Golem d'essai ({@link ObservatoryNpcSystem}) et son pupitre
 * ({@code Nakasar_Fractal_TrialDemo}), filet anti-chute ({@link FallRescueSystem}), commande {@code /fractale}.
 *
 * <p>Étape 3, la progression ({@code progress}) : niveau débloqué et emplacements d'infusion sauvegardés avec le joueur
 * ({@link FractalProgress}), Autel des infusions ({@code Nakasar_Fractal_OpenInfusions}), agonie ({@link AgonySystem}),
 * coffre de fin par joueur ({@code Nakasar_Fractal_ClaimReward}) et coffres de rang ({@code Nakasar_Fractal_OpenBag}),
 * boutique de l'Archiviste ({@code Nakasar_Fractal_OpenShop}, et le PNJ posé par {@link ObservatoryNpcSystem}).
 *
 * <p>Étape 4, la Falaise ({@code cliffside}) : marteau du culte et sa Corruption ({@link HammerSystem},
 * {@link HammerDamageSystem}), barre de défiance ({@code Nakasar_Fractal_OpenDefiance}, {@link DefianceDamageSystem}),
 * soin des incantateurs ({@code Nakasar_Fractal_HealFoes}), et le déroulé de la fractale ({@link CliffsideSystem} :
 * sceaux, vagues, pièges du saut, cages et Archidevin ; {@link CliffsideDamageFilter} ; blocs utilisables
 * {@code Nakasar_Fractal_CliffsideUse}).
 *
 * <p>Étape 5, les instabilités ({@code instability}) : tirage quotidien par fractale et par rang, effets aux coups et
 * aux morts ({@link Instabilities}, branchés sur {@link StageDamageFilter} et {@link FoeDeathSystem}) et dans le temps
 * ({@link InstabilitySystem}), commande {@code /fractale instabilites}.
 *
 * <p>Étape 6 : les déroulés communs ({@code stage} : {@link StageSystem}, blocs {@code Nakasar_Fractal_Use}, objet
 * lancé {@code Nakasar_Fractal_ThrowItem}), l'attraction {@code Nakasar_Fractal_Pull}, et les fractales Inclassable
 * ({@link Uncategorized}) et Volcanique ({@link Volcanic}).
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
        interactions.register(OpenConsoleInteraction.TYPE_ID, OpenConsoleInteraction.class, OpenConsoleInteraction.CODEC);
        interactions.register(HarmonizeInteraction.TYPE_ID, HarmonizeInteraction.class, HarmonizeInteraction.CODEC);
        interactions.register(LeaveInteraction.TYPE_ID, LeaveInteraction.class, LeaveInteraction.CODEC);
        interactions.register(TrialDemoInteraction.TYPE_ID, TrialDemoInteraction.class, TrialDemoInteraction.CODEC);
        interactions.register(OpenInfusionsInteraction.TYPE_ID, OpenInfusionsInteraction.class, OpenInfusionsInteraction.CODEC);
        interactions.register(OpenBagInteraction.TYPE_ID, OpenBagInteraction.class, OpenBagInteraction.CODEC);
        interactions.register(ClaimRewardInteraction.TYPE_ID, ClaimRewardInteraction.class, ClaimRewardInteraction.CODEC);
        interactions.register(DailyBoardInteraction.TYPE_ID, DailyBoardInteraction.class, DailyBoardInteraction.CODEC);
        interactions.register(OpenShopInteraction.TYPE_ID, OpenShopInteraction.class, OpenShopInteraction.CODEC);
        interactions.register(OpenDefianceInteraction.TYPE_ID, OpenDefianceInteraction.class, OpenDefianceInteraction.CODEC);
        interactions.register(HealFoesInteraction.TYPE_ID, HealFoesInteraction.class, HealFoesInteraction.CODEC);
        interactions.register(CliffsideUseInteraction.TYPE_ID, CliffsideUseInteraction.class, CliffsideUseInteraction.CODEC);
        interactions.register(PullInteraction.TYPE_ID, PullInteraction.class, PullInteraction.CODEC);
        interactions.register(StageUseInteraction.TYPE_ID, StageUseInteraction.class, StageUseInteraction.CODEC);
        interactions.register(ThrowItemInteraction.TYPE_ID, ThrowItemInteraction.class, ThrowItemInteraction.CODEC);

        var systems = getEntityStoreRegistry();
        FractalProgress.setComponentType(systems.registerComponent(FractalProgress.class, FractalProgress.ID, FractalProgress.CODEC));
        systems.registerSystem(new TelegraphSystem());
        systems.registerSystem(new BossStun.Unload());
        systems.registerSystem(new MinionShieldSystem());
        systems.registerSystem(new ShieldUnloadSystem());
        systems.registerSystem(new BossBarSystem());
        systems.registerSystem(new PinnedHealth());
        systems.registerSystem(new HarmonyCircleSystem());
        systems.registerSystem(new SelectionItemsSystem());
        systems.registerSystem(new ObservatoryNpcSystem());
        systems.registerSystem(new TrialHitSystem());
        systems.registerSystem(new FallRescueSystem());
        systems.registerSystem(new AgonySystem());
        systems.registerSystem(new HammerSystem());
        systems.registerSystem(new HammerDamageSystem());
        systems.registerSystem(new HammerDropSystem());
        systems.registerSystem(new HammerPickupSystem());
        systems.registerSystem(new DefianceDamageSystem());
        systems.registerSystem(new CliffsideSystem());
        systems.registerSystem(new CliffsideDamageFilter());
        systems.registerSystem(new StageSystem());
        systems.registerSystem(new StageDamageFilter());
        systems.registerSystem(new FoeDeathSystem());
        systems.registerSystem(new InstabilitySystem());
        Cliffside.registerBossBars();
        Instabilities.exempt(Cliffside.SEAL_ROLES);
        Instabilities.exempt(Cliffside.SEEKER);
        Uncategorized.register();
        Stages.register(new Uncategorized());
        Volcanic.register();
        Stages.register(new Volcanic());
        SolidOcean.register();
        Stages.register(new SolidOcean());
        Swampland.register();
        Stages.register(new Swampland());
        Snowblind.register();
        Stages.register(new Snowblind());

        getCommandRegistry().registerCommand(new FractalCommand());

        getLogger().atInfo().log("Nakasar Fractales : 20 types d'interaction (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s), progression, fractales du jour, Falaise, instabilités, Inclassable, Volcanique, Océan solide, Marais, Tempête de neige, systèmes et /fractale enregistrés",
                TelegraphInteraction.TYPE_ID, ChargeInteraction.TYPE_ID, StunSelfInteraction.TYPE_ID,
                SummonMinionsInteraction.TYPE_ID, CagePlayerInteraction.TYPE_ID, OpenConsoleInteraction.TYPE_ID,
                HarmonizeInteraction.TYPE_ID, LeaveInteraction.TYPE_ID, TrialDemoInteraction.TYPE_ID,
                OpenInfusionsInteraction.TYPE_ID, OpenBagInteraction.TYPE_ID, ClaimRewardInteraction.TYPE_ID,
                OpenShopInteraction.TYPE_ID, OpenDefianceInteraction.TYPE_ID, HealFoesInteraction.TYPE_ID,
                CliffsideUseInteraction.TYPE_ID, PullInteraction.TYPE_ID, StageUseInteraction.TYPE_ID,
                ThrowItemInteraction.TYPE_ID, DailyBoardInteraction.TYPE_ID);
    }

    @Override
    protected void shutdown() {
        TelegraphSystem.clearAll();
        BossStun.clearAll();
        SummonMinionsInteraction.clearAll();
        BossBarSystem.clearAll();
        PinnedHealth.clearAll();
        Observatory.clearAll();
        FractalRuns.clearAll();
        AgonySystem.clearAll();
        Defiance.clearAll();
        Hammer.clearAll();
        Cliffside.clearAll();
        Stages.clearAll();
        InstabilitySystem.clearAll();
        HitShield.clearAll();
    }
}
