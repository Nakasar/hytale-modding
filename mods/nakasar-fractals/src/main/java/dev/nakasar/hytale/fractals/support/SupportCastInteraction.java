package dev.nakasar.hytale.fractals.support;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.InteractionState;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.WaitForDataFrom;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.FractalsPlugin;

/**
 * {@code "Type": "Nakasar_Fractal_Support"} : lance une rune ou un objet de soutien ({@link Skills}). Ce qui peut
 * échouer est vérifié ici, tout de suite : la cible visée (allié pour la Transfusion et le bâton, ennemi pour
 * l'Hébètement) et la recharge propre de l'objet. En cas d'échec l'interaction est {@code Failed} et la suite de la
 * chaîne (mana, recharge de la rune, objet consommé) ne passe pas. L'effet lui-même part sur le thread du monde.
 *
 * <p>Clé JSON : {@code Skill} (string), l'un de {@link Skill}.
 */
public class SupportCastInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_Fractal_Support";

    public static final BuilderCodec<SupportCastInteraction> CODEC = BuilderCodec
            .builder(SupportCastInteraction.class, SupportCastInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Lance une rune ou un objet de soutien des fractales.")
            .append(new KeyedCodec<>("Skill", Codec.STRING), (i, v) -> i.skill = v, i -> i.skill)
            .documentation("Effet lance (HealingBreath, Transfusion, Aegis, Reprieve, Shockwave, Daze, GravityWell, Fear, "
                    + "HealingWell, FrostGlyph, Brazier, FrostLine, Sanctuary, Decoy, StaffMend, GrimoireGlyph, WandVines, "
                    + "HealingTotem, SlownessTotem, DazeBomb, SmokeBomb, BannerMight, BannerGuard, Purge).")
            .add()
            .build();

    /** Les effets ; `cooldown` : recharge propre à l'objet (0 : celle de la rune, gérée par le jeu). */
    enum Skill {
        HealingBreath, Transfusion, Aegis, Reprieve, Shockwave, Daze, GravityWell, Fear, HealingWell, FrostGlyph, Brazier,
        FrostLine, Sanctuary, Decoy,
        StaffMend(Skills.STAFF_COOLDOWN), GrimoireGlyph(Skills.GRIMOIRE_COOLDOWN), WandVines(Skills.VINES_COOLDOWN),
        HealingTotem, SlownessTotem, DazeBomb, SmokeBomb,
        BannerMight(Skills.BANNER_COOLDOWN), BannerGuard(Skills.BANNER_COOLDOWN), Purge;

        final float cooldown;

        Skill() {
            this(0f);
        }

        Skill(float cooldown) {
            this.cooldown = cooldown;
        }

        static Skill of(String id) {
            for (Skill s : values()) {
                if (s.name().equals(id)) {
                    return s;
                }
            }
            return null;
        }
    }

    protected String skill;

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> caster = context.getOwningEntity();
        Skill kind = Skill.of(skill);
        if (kind == null) {
            FractalsPlugin.get().getLogger().atWarning().log("Soutien : effet inconnu '%s'", skill);
        }
        if (kind == null || buffer == null || caster == null || !caster.isValid()
                || buffer.getComponent(caster, PlayerRef.getComponentType()) == null) {
            context.getState().state = InteractionState.Failed;
            return;
        }
        World world = buffer.getExternalData().getWorld();
        Store<EntityStore> store = buffer.getStore();
        Ref<EntityStore> target = null;
        switch (kind) {
            case Transfusion, StaffMend -> {
                double range = kind == Skill.Transfusion ? Skills.TRANSFUSION_RANGE : Skills.STAFF_RANGE;
                target = Support.aimEntity(world, store, caster, range, 20, true, false);
                if (target == null) {
                    Support.tell(store, caster, "noAlly");
                }
            }
            case Daze -> {
                target = Support.aimEntity(world, store, caster, Skills.DAZE_RANGE, 16, false, true);
                if (target == null) {
                    Support.tell(store, caster, "noTarget");
                }
            }
            default -> {
            }
        }
        boolean needsTarget = kind == Skill.Transfusion || kind == Skill.StaffMend || kind == Skill.Daze;
        if ((needsTarget && target == null)
                || (kind.cooldown > 0 && !Support.ready(store, caster, kind.name(), kind.cooldown))) {
            context.getState().state = InteractionState.Failed;
            return;
        }
        Ref<EntityStore> aimed = target;
        world.execute(() -> {
            if (!caster.isValid()) {
                return;
            }
            run(kind, world, world.getEntityStore().getStore(), caster, aimed);
        });
    }

    private static void run(Skill kind, World world, Store<EntityStore> store, Ref<EntityStore> caster,
                            Ref<EntityStore> target) {
        switch (kind) {
            case HealingBreath -> Skills.healingBreath(world, store, caster);
            case Transfusion -> Skills.transfusion(world, store, caster, target);
            case Aegis -> Skills.aegis(world, store, caster);
            case Reprieve -> Skills.reprieve(world, store, caster);
            case Shockwave -> Skills.shockwave(world, store, caster);
            case Daze -> Skills.daze(world, store, caster, target);
            case GravityWell -> Skills.gravityWell(world, store, caster);
            case Fear -> Skills.fear(world, store, caster);
            case HealingWell -> Skills.healingWell(world, store, caster);
            case FrostGlyph -> Skills.frostGlyph(world, store, caster);
            case Brazier -> Skills.brazier(world, store, caster);
            case FrostLine -> Skills.frostLine(world, store, caster);
            case Sanctuary -> Skills.sanctuary(world, store, caster);
            case Decoy -> Decoys.decoy(world, store, caster);
            case StaffMend -> Skills.staffMend(world, store, caster, target);
            case GrimoireGlyph -> Skills.grimoireGlyph(world, store, caster);
            case WandVines -> Skills.wandVines(world, store, caster);
            case HealingTotem -> Skills.healingTotem(world, store, caster);
            case SlownessTotem -> Skills.slownessTotem(world, store, caster);
            case DazeBomb -> Skills.dazeBomb(world, store, caster);
            case SmokeBomb -> Skills.smokeBomb(world, store, caster);
            case BannerMight -> Skills.banner(world, store, caster, true);
            case BannerGuard -> Skills.banner(world, store, caster, false);
            case Purge -> Skills.purge(world, store, caster);
        }
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        // Serveur uniquement.
    }

    @Override
    public WaitForDataFrom getWaitForDataFrom() {
        return WaitForDataFrom.Server;
    }
}
