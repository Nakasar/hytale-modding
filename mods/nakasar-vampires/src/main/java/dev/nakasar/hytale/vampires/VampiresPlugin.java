package dev.nakasar.hytale.vampires;

import com.hypixel.hytale.builtin.adventure.worldevents.WorldEventsPlugin;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction;
import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;
import dev.nakasar.hytale.vampires.allegiance.AllegianceAttitudeSystem;
import dev.nakasar.hytale.vampires.allegiance.AllegianceDamageFilter;
import dev.nakasar.hytale.vampires.boss.BossBarSystem;
import dev.nakasar.hytale.vampires.breach.BreachHunterCleanupSystem;
import dev.nakasar.hytale.vampires.breach.HunterBreachStarter;
import dev.nakasar.hytale.vampires.breach.NightCondition;
import dev.nakasar.hytale.vampires.contract.ClaimBreachContractInteraction;
import dev.nakasar.hytale.vampires.contract.ContractBounties;
import dev.nakasar.hytale.vampires.contract.OpenBountyBagInteraction;
import dev.nakasar.hytale.vampires.domination.DominateInteraction;
import dev.nakasar.hytale.vampires.domination.DominatePlayerInteraction;
import dev.nakasar.hytale.vampires.domination.DominationExpirySystem;
import dev.nakasar.hytale.vampires.domination.Dominations;
import dev.nakasar.hytale.vampires.invisibility.Invisibility;
import dev.nakasar.hytale.vampires.invisibility.InvisibilityInteraction;
import dev.nakasar.hytale.vampires.invisibility.InvisibilitySystem;
import dev.nakasar.hytale.vampires.lords.LordsWrath;
import dev.nakasar.hytale.vampires.lords.LordsWrathSystem;
import dev.nakasar.hytale.vampires.prison.ImprisonPlayerInteraction;
import dev.nakasar.hytale.vampires.pumpkin.FireWeaknessSystem;
import dev.nakasar.hytale.vampires.pumpkin.PumpkinShieldSystem;
import dev.nakasar.hytale.vampires.purifying.LightAura;
import dev.nakasar.hytale.vampires.purifying.LightAuraInteraction;
import dev.nakasar.hytale.vampires.purifying.LightAuraSystem;
import dev.nakasar.hytale.vampires.purifying.PurifyingFireSystem;
import dev.nakasar.hytale.vampires.purifying.PurifyingFires;
import dev.nakasar.hytale.vampires.purifying.PurifyingSteeringSystem;
import dev.nakasar.hytale.vampires.pumpkin.RootTrapInteraction;
import dev.nakasar.hytale.vampires.pumpkin.RootTrapUnloadSystem;
import dev.nakasar.hytale.vampires.pumpkin.RootTrapped;
import dev.nakasar.hytale.vampires.pumpkin.SummonVinesInteraction;
import dev.nakasar.hytale.vampires.rune.DrainBeamInteraction;
import dev.nakasar.hytale.vampires.rune.RootNpcInteraction;
import dev.nakasar.hytale.vampires.rune.TeleportCasterToImpactInteraction;
import dev.nakasar.hytale.vampires.silver.ArrowQuiver;
import dev.nakasar.hytale.vampires.silver.ReturnArrowInteraction;
import dev.nakasar.hytale.vampires.silver.SilverDamageSystem;
import dev.nakasar.hytale.vampires.silver.SilverProjectileSystems;
import dev.nakasar.hytale.vampires.silver.SilverWeapons;
import dev.nakasar.hytale.vampires.silver.TakeArrowInteraction;
import dev.nakasar.hytale.vampires.vampirism.BloodFeedInteraction;
import dev.nakasar.hytale.vampires.vampirism.DrinkBloodInteraction;
import dev.nakasar.hytale.vampires.vampirism.Vampire;
import dev.nakasar.hytale.vampires.vampirism.VampireDamageSystem;
import dev.nakasar.hytale.vampires.vampirism.VampireRitualInteraction;
import dev.nakasar.hytale.vampires.vampirism.VampireSystem;

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
 *   <li>{@code Nakasar_RootTrap} : piège de vrilles de la citrouille géante (une vrille-PNJ retient la cible
 *       jusqu'à sa destruction) ;</li>
 *   <li>{@code Nakasar_SummonVines} : la citrouille géante fait sortir de terre ses vrilles combattantes ;</li>
 *   <li>{@link FireWeaknessSystem} : la citrouille géante et ses vrilles prennent double dégâts de feu ;</li>
 *   <li>{@link PumpkinShieldSystem} : la citrouille géante est invulnérable tant qu'il lui reste des vrilles, et fait
 *       sortir sa première vague dès le premier coup ;</li>
 *   <li>{@link BossBarSystem} : barre de vie de boss des élites (citrouille géante, Abomination, Capitaine de la
 *       garde, Comte et Comtesse) pour les joueurs proches pendant le combat ;</li>
 *   <li>les camps ({@link AllegianceAttitudeSystem}, {@link AllegianceDamageFilter},
 *       {@link DominationExpirySystem}) : les mobs du fragment sont alliés, ennemis des chasseurs de vampires, et la
 *       Domination retourne leur allégeance ;</li>
 *   <li>{@code Nakasar_ClaimBreachContract} : le tableau de contrats de la brèche porte une seule prime (le premier
 *       contrat) par brèche, pour tout le serveur (les notes de lore elles-mêmes sont des blocs vanilla : page
 *       {@code OpenCustomUI} « BlockLore ») ;</li>
 *   <li>{@link LordsWrathSystem} (et le fournisseur d'attitude -5 d'{@link AllegianceAttitudeSystem}) : le Comte et la Comtesse laissent passer les joueurs,
 *       mais un coup porté contre eux les retourne contre tous les joueurs présents ({@link LordsWrath}) ;</li>
 *   <li>{@link SilverDamageSystem} et {@link SilverProjectileSystems} : les armes en argent (et leurs projectiles)
 *       infligent le double de dégâts aux vampires ;</li>
 *   <li>{@link PurifyingFireSystem} et {@link PurifyingSteeringSystem} : les morts-vivants évitent les torches et
 *       lanternes de feu purificateur du camp des chasseurs ;</li>
 *   <li>{@code Nakasar_LightAura} ({@link LightAuraSystem}) : aura de feu purificateur autour du lanceur, que les
 *       morts-vivants fuient comme une torche (rune Aura de lumière) ;</li>
 *   <li>{@code Nakasar_Invisibility} ({@link InvisibilitySystem}) : le lanceur disparaît pour les joueurs et les PNJ
 *       tant qu'il reste immobile (rune Invisibilité) ;</li>
 *   <li>la voie occulte ({@link VampireSystem}, {@link VampireDamageSystem}, {@code Nakasar_VampireRitual},
 *       {@code Nakasar_BloodFeed}, {@code Nakasar_DrinkBlood}) : le rituel de l'autel fait du joueur un vampire
 *       (composant {@link Vampire} sauvegardé avec lui) : faim de sang, soleil, argent, lumière purificatrice,
 *       vision nocturne ;</li>
 *   <li>la brèche des chasseurs ({@link HunterBreachStarter}, {@link NightCondition},
 *       {@link BreachHunterCleanupSystem}) : la nuit, toutes les demi-heures, un campement de chasseurs de vampires
 *       s'ouvre près d'un joueur du monde principal, annoncé dans le chat et sur la carte ;</li>
 *   <li>{@link ContractBounties} : la mort de la cible d'un contrat de chasseurs, dans son mini-fragment, lui fait lâcher
 *       le sac de prime du groupe, que {@code Nakasar_OpenBountyBag} ouvre.</li>
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
        interactions.register(RootTrapInteraction.TYPE_ID,
                RootTrapInteraction.class, RootTrapInteraction.CODEC);
        interactions.register(SummonVinesInteraction.TYPE_ID,
                SummonVinesInteraction.class, SummonVinesInteraction.CODEC);
        interactions.register(TakeArrowInteraction.TYPE_ID,
                TakeArrowInteraction.class, TakeArrowInteraction.CODEC);
        interactions.register(ReturnArrowInteraction.TYPE_ID,
                ReturnArrowInteraction.class, ReturnArrowInteraction.CODEC);
        interactions.register(LightAuraInteraction.TYPE_ID,
                LightAuraInteraction.class, LightAuraInteraction.CODEC);
        interactions.register(InvisibilityInteraction.TYPE_ID,
                InvisibilityInteraction.class, InvisibilityInteraction.CODEC);
        interactions.register(ClaimBreachContractInteraction.TYPE_ID,
                ClaimBreachContractInteraction.class, ClaimBreachContractInteraction.CODEC);
        interactions.register(VampireRitualInteraction.TYPE_ID,
                VampireRitualInteraction.class, VampireRitualInteraction.CODEC);
        interactions.register(BloodFeedInteraction.TYPE_ID,
                BloodFeedInteraction.class, BloodFeedInteraction.CODEC);
        interactions.register(DrinkBloodInteraction.TYPE_ID,
                DrinkBloodInteraction.class, DrinkBloodInteraction.CODEC);
        interactions.register(OpenBountyBagInteraction.TYPE_ID,
                OpenBountyBagInteraction.class, OpenBountyBagInteraction.CODEC);

        var systems = getEntityStoreRegistry();
        RootTrapped.setComponentType(systems.registerComponent(RootTrapped.class, RootTrapped::new));
        LightAura.setComponentType(systems.registerComponent(LightAura.class, LightAura::new));
        Invisibility.setComponentType(systems.registerComponent(Invisibility.class, Invisibility::new));
        Vampire.setComponentType(systems.registerComponent(Vampire.class, Vampire.ID, Vampire.CODEC));
        systems.registerSystem(new AllegianceAttitudeSystem());
        systems.registerSystem(new AllegianceDamageFilter());
        systems.registerSystem(new LordsWrathSystem());
        systems.registerSystem(new DominationExpirySystem());
        systems.registerSystem(new FireWeaknessSystem());
        systems.registerSystem(new PumpkinShieldSystem());
        systems.registerSystem(new BossBarSystem());
        systems.registerSystem(new RootTrapUnloadSystem());
        systems.registerSystem(new SilverProjectileSystems.Launch());
        systems.registerSystem(new SilverProjectileSystems.Legacy());
        systems.registerSystem(new SilverDamageSystem());
        PurifyingFires purifyingFires = new PurifyingFires();
        PurifyingFireSystem purifyingFireSystem = new PurifyingFireSystem(purifyingFires);
        systems.registerSystem(purifyingFireSystem);
        systems.registerSystem(new PurifyingSteeringSystem(purifyingFires));
        systems.registerSystem(new LightAuraSystem(purifyingFires));
        systems.registerSystem(new LightAuraSystem.Unload());
        systems.registerSystem(new InvisibilitySystem());
        systems.registerSystem(new InvisibilitySystem.BreakOnAttack());
        systems.registerSystem(new InvisibilitySystem.ForgetInvisible());
        systems.registerSystem(new InvisibilitySystem.Unload());
        systems.registerSystem(new VampireSystem(purifyingFireSystem));
        systems.registerSystem(new VampireDamageSystem());

        // Brèche des chasseurs : évènement de monde (Server/WorldEvent) avec notre condition « nuit ».
        WorldEventsPlugin.registerCondition(this, NightCondition.TYPE, NightCondition.CODEC, NightCondition.Config.CODEC);
        systems.registerSystem(new HunterBreachStarter());
        systems.registerSystem(new BreachHunterCleanupSystem());
        systems.registerSystem(new ContractBounties());

        getLogger().atInfo().log("Nakasar Vampires : 17 types d'interaction (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s), systèmes des camps, de l'argent, du feu purificateur, de la voie occulte, de la brèche et des contrats des chasseurs enregistrés",
                TeleportCasterToImpactInteraction.TYPE_ID, DominateInteraction.TYPE_ID, RootNpcInteraction.TYPE_ID,
                DrainBeamInteraction.TYPE_ID, DominatePlayerInteraction.TYPE_ID, ImprisonPlayerInteraction.TYPE_ID,
                RootTrapInteraction.TYPE_ID, TakeArrowInteraction.TYPE_ID, ReturnArrowInteraction.TYPE_ID,
                SummonVinesInteraction.TYPE_ID, LightAuraInteraction.TYPE_ID, InvisibilityInteraction.TYPE_ID,
                VampireRitualInteraction.TYPE_ID, BloodFeedInteraction.TYPE_ID, DrinkBloodInteraction.TYPE_ID,
                OpenBountyBagInteraction.TYPE_ID, ClaimBreachContractInteraction.TYPE_ID);
    }

    @Override
    protected void shutdown() {
        RootNpcInteraction.clearAll();
        RootTrapInteraction.clearAll();
        SummonVinesInteraction.clearAll();
        PumpkinShieldSystem.clearAll();
        BossBarSystem.clearAll();
        Dominations.clearAll();
        LordsWrath.clearAll();
        SilverWeapons.clearAll();
        ArrowQuiver.clearAll();
        ContractBounties.clearAll();
        ClaimBreachContractInteraction.clearAll();
    }
}
