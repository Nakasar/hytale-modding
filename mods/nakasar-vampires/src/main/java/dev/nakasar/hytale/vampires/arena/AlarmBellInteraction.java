package dev.nakasar.hytale.vampires.arena;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.InteractionState;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.vampires.VampiresPlugin;
import dev.nakasar.hytale.vampires.elite.SummonMinionsInteraction;
import dev.nakasar.hytale.vampires.telegraph.Telegraphs;
import org.joml.Vector3d;
import org.joml.Vector3i;

import java.util.concurrent.TimeUnit;

/**
 * {@code "Type": "Nakasar_AlarmBell"} : le Capitaine de la garde, passé sous la moitié de sa vie, crie l'alarme
 * (Kevin, 20 octobre 2026). Si une cloche d'alarme ({@value ArenaBlocks#BELL}) est encore debout à moins de
 * {@code BellRadius} blocs, elle sonne et {@code PerPlayer} gardes ({@code GuardRole}) par joueur présent dans un rayon
 * de {@code PlayerRadius} blocs accourent autour de lui (au plus {@code MaxGuards}). Les joueurs qui ont abattu la
 * cloche avant (elle tombe au bout de quelques coups, {@link ArenaBlocks}) n'ont pas de renforts : la branche
 * {@code Failed} de la chaîne joue alors le cri dans le vide.
 *
 * <p>Les gardes appelés suivent le Capitaine comme ses serviteurs ({@link SummonMinionsInteraction}) : jamais
 * sauvegardés, retirés avec lui.
 */
public class AlarmBellInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_AlarmBell";

    public static final BuilderCodec<AlarmBellInteraction> CODEC = BuilderCodec
            .builder(AlarmBellInteraction.class, AlarmBellInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Fait sonner la cloche d'alarme la plus proche et appelle des gardes par joueur present.")
            .append(new KeyedCodec<>("GuardRole", Codec.STRING), (i, v) -> i.guardRole = v, i -> i.guardRole).add()
            .append(new KeyedCodec<>("PerPlayer", Codec.INTEGER), (i, v) -> i.perPlayer = v, i -> i.perPlayer).add()
            .append(new KeyedCodec<>("MaxGuards", Codec.INTEGER), (i, v) -> i.maxGuards = v, i -> i.maxGuards).add()
            .append(new KeyedCodec<>("BellRadius", Codec.INTEGER), (i, v) -> i.bellRadius = v, i -> i.bellRadius).add()
            .append(new KeyedCodec<>("PlayerRadius", Codec.FLOAT), (i, v) -> i.playerRadius = v, i -> i.playerRadius).add()
            .append(new KeyedCodec<>("TetherParticle", Codec.STRING), (i, v) -> i.tetherParticle = v, i -> i.tetherParticle).add()
            .build();

    private static final String RING_SOUND = "SFX_Goblin_Mace_Club_Slam_Impact";
    private static final String RING_PARTICLE = "Praetorian_Summon_Ground";

    protected String guardRole = "Nakasar_Skeleton_Guard";
    protected int perPlayer = 3;
    protected int maxGuards = 12;
    protected int bellRadius = 40;
    protected float playerRadius = 24f;
    protected String tetherParticle;

    public AlarmBellInteraction() {
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> owner = context.getOwningEntity();
        Ref<EntityStore> captain = owner != null && owner.isValid() ? owner : context.getEntity();
        Vector3d at = buffer == null ? null : Telegraphs.position(buffer, captain);
        if (at == null) {
            context.getState().state = InteractionState.Failed;
            return;
        }
        World world = buffer.getExternalData().getWorld();
        Vector3i bell = ArenaBlocks.bellNear(world.getChunkStore(), at, bellRadius);
        if (bell == null) {
            context.getState().state = InteractionState.Failed;
            return;
        }
        int players = 0;
        for (PlayerRef player : world.getPlayerRefs()) {
            Vector3d p = Telegraphs.position(buffer, player.getReference());
            if (p != null && p.distance(at) <= playerRadius) {
                players++;
            }
        }
        int guards = Math.min(maxGuards, Math.max(1, players) * perPlayer);
        Vector3d center = new Vector3d(at);
        Vector3d bellAt = WorldBlocks.center(bell);
        SummonMinionsInteraction wave = SummonMinionsInteraction.preset(guardRole, guards, guards, 4f, 10f, 1.8f)
                .withTether(tetherParticle);
        world.execute(() -> {
            Store<EntityStore> store = world.getEntityStore().getStore();
            // Trois coups de cloche, puis les gardes accourent.
            for (int k = 0; k < 3; k++) {
                world.scheduleAfter(() -> Telegraphs.sound(world.getEntityStore().getStore(), RING_SOUND, bellAt), k * 400L, TimeUnit.MILLISECONDS);
            }
            Telegraphs.particle(store, RING_PARTICLE, new Vector3d(bellAt.x(), bell.y + 0.1, bellAt.z()), 1.2f);
            SummonMinionsInteraction.summonNow(wave, world, captain, center);
        });
        VampiresPlugin.get().getLogger().atInfo().log("%s : cloche en %s, %d garde(s) pour %d joueur(s)", TYPE_ID, bell, guards, players);
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        // Serveur uniquement.
    }
}
