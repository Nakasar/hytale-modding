package dev.nakasar.hytale.fractals.stage;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.WaitForDataFrom;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.entity.component.HeadRotation;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.fractals.arena.Carried;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * {@code "Type": "Nakasar_Fractal_ThrowItem"} : lancer l'objet tenu ({@code Item}, consommé) sur un PNJ visé (pierre
 * imprégnée du Volcanique sur le chaman champion). Le PNJ dont le rôle est dans {@code Roles} (séparés par des
 * virgules), à moins de {@code Range} blocs, dans un cône de {@code Cone} degrés autour du regard et en vue, est
 * touché : la pierre file vers lui ({@code Particle} le long du trajet, {@value #FLIGHT} s), puis le déroulé de la
 * fractale reçoit le coup ({@link FractalStage#thrown}, action {@code Action}). Sans cible : rien n'est lancé, le joueur
 * reçoit {@code NoTargetMessage}.
 */
public class ThrowItemInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_Fractal_ThrowItem";
    static final float FLIGHT = 0.5f;

    public static final BuilderCodec<ThrowItemInteraction> CODEC = BuilderCodec
            .builder(ThrowItemInteraction.class, ThrowItemInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Lance l'objet tenu sur un PNJ vise ; le Java de la fractale recoit le coup.")
            .append(new KeyedCodec<>("Item", Codec.STRING), (i, v) -> i.item = v, i -> i.item).add()
            .append(new KeyedCodec<>("Roles", Codec.STRING), (i, v) -> i.roles = v, i -> i.roles).add()
            .append(new KeyedCodec<>("Range", Codec.FLOAT), (i, v) -> i.range = v, i -> i.range).add()
            .append(new KeyedCodec<>("Cone", Codec.FLOAT), (i, v) -> i.cone = v, i -> i.cone).add()
            .append(new KeyedCodec<>("Particle", Codec.STRING), (i, v) -> i.particle = v, i -> i.particle).add()
            .append(new KeyedCodec<>("Action", Codec.STRING), (i, v) -> i.action = v, i -> i.action).add()
            .append(new KeyedCodec<>("NoTargetMessage", Codec.STRING), (i, v) -> i.noTarget = v, i -> i.noTarget).add()
            .build();

    private String item;
    private String roles = "";
    private float range = 24f;
    private float cone = 30f;
    private String particle;
    private String action;
    private String noTarget;

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> ref = context.getEntity();
        if (buffer == null || ref == null || !ref.isValid() || item == null) {
            return;
        }
        PlayerRef player = buffer.getComponent(ref, PlayerRef.getComponentType());
        World world = buffer.getExternalData().getWorld();
        FractalStage stage = Stages.of(world);
        if (player == null || stage == null) {
            return;
        }
        world.execute(() -> {
            if (ref.isValid()) {
                throwAt(world, world.getEntityStore().getStore(), stage, ref, player);
            }
        });
    }

    private void throwAt(World world, Store<EntityStore> store, FractalStage stage, Ref<EntityStore> ref, PlayerRef player) {
        Vector3d eye = Telegraphs.position(store, ref);
        HeadRotation head = store.getComponent(ref, HeadRotation.getComponentType());
        if (eye == null || head == null) {
            return;
        }
        eye = new Vector3d(eye).add(0, 1.6, 0);
        Vector3d look = new Vector3d(head.getDirection()).normalize();
        Ref<EntityStore> target = aim(world, store, eye, look);
        if (target == null) {
            if (noTarget != null && !noTarget.isBlank()) {
                player.sendMessage(Message.translation(noTarget));
            }
            return;
        }
        if (!Carried.takeOne(store, ref, item)) {
            return;
        }
        Vector3d start = eye;
        long[] begin = {-1};
        TelegraphSystem.start(world, (w, s, now) -> {
            if (begin[0] < 0) {
                begin[0] = now;
            }
            Vector3d end = Telegraphs.position(s, target);
            if (end == null) {
                return true;
            }
            end = new Vector3d(end).add(0, 1.2, 0);
            float t = Math.min(1f, (now - begin[0]) / (float) Telegraphs.seconds(FLIGHT));
            if (particle != null && !particle.isBlank()) {
                Telegraphs.particle(s, particle, new Vector3d(start).lerp(end, t), 0.8f);
            }
            if (t < 1f) {
                return false;
            }
            if (ref.isValid()) {
                stage.thrown(w, s, ref, player, action, target);
            }
            return true;
        });
    }

    /** PNJ visé : rôle accepté, à portée, dans le cône, sans bloc plein entre l'œil et lui ; le plus proche de l'axe. */
    private Ref<EntityStore> aim(World world, Store<EntityStore> store, Vector3d eye, Vector3d look) {
        Set<String> wanted = Set.of(roles.split("\\s*,\\s*"));
        List<Ref<EntityStore>> refs = new ArrayList<>();
        List<Vector3d> positions = new ArrayList<>();
        store.forEachChunk(NPCEntity.getComponentType(), (ArchetypeChunk<EntityStore> chunk, CommandBuffer<EntityStore> b) -> {
            for (int i = 0; i < chunk.size(); i++) {
                NPCEntity npc = chunk.getComponent(i, NPCEntity.getComponentType());
                TransformComponent transform = chunk.getComponent(i, TransformComponent.getComponentType());
                if (npc != null && transform != null && wanted.contains(npc.getRoleName())) {
                    refs.add(chunk.getReferenceTo(i));
                    positions.add(new Vector3d(transform.getPosition()).add(0, 1.2, 0));
                }
            }
        });
        double cos = Math.cos(Math.toRadians(cone / 2));
        Ref<EntityStore> best = null;
        double bestDot = cos;
        for (int i = 0; i < refs.size(); i++) {
            Vector3d to = new Vector3d(positions.get(i)).sub(eye);
            double d = to.length();
            if (d > range || d < 0.5) {
                continue;
            }
            double dot = to.dot(look) / d;
            if (dot >= bestDot && WorldBlocks.clearLine(world.getChunkStore(), eye, positions.get(i))) {
                bestDot = dot;
                best = refs.get(i);
            }
        }
        return best;
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
