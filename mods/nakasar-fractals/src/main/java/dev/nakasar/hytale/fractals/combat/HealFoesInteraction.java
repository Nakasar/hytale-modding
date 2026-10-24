package dev.nakasar.hytale.fractals.combat;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;

/**
 * {@code "Type": "Nakasar_Fractal_HealFoes"} : soin de groupe d'un incantateur du culte. Rend {@code Amount} PV aux
 * alliés du lanceur ({@link Foes}) à moins de {@code Radius} blocs, lui compris ; ni les sceaux ni les boss
 * ({@value #SEAL_ROLE}, {@value #BOSS_ROLE}) ne sont soignés. {@code Particle} s'affiche sur le lanceur.
 */
public class HealFoesInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_Fractal_HealFoes";
    private static final String SEAL_ROLE = "Nakasar_Fractal_Seal";
    private static final String BOSS_ROLE = "Nakasar_Fractal_Archdiviner";

    public static final BuilderCodec<HealFoesInteraction> CODEC = BuilderCodec
            .builder(HealFoesInteraction.class, HealFoesInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Soigne les allies du lanceur autour de lui.")
            .append(new KeyedCodec<>("Radius", Codec.FLOAT), (i, v) -> i.radius = v, i -> i.radius).add()
            .append(new KeyedCodec<>("Amount", Codec.FLOAT), (i, v) -> i.amount = v, i -> i.amount).add()
            .append(new KeyedCodec<>("Particle", Codec.STRING), (i, v) -> i.particle = v, i -> i.particle).add()
            .build();

    protected float radius = 10f;
    protected float amount = 25f;
    protected String particle;

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> owner = context.getOwningEntity();
        Ref<EntityStore> caster = owner != null && owner.isValid() ? owner : context.getEntity();
        if (buffer == null || caster == null || !caster.isValid()) {
            return;
        }
        World world = buffer.getExternalData().getWorld();
        world.execute(() -> heal(world.getEntityStore().getStore(), caster));
    }

    private void heal(Store<EntityStore> store, Ref<EntityStore> caster) {
        Vector3d center = Telegraphs.position(store, caster);
        if (center == null) {
            return;
        }
        if (particle != null && !particle.isBlank()) {
            Telegraphs.particle(store, particle, new Vector3d(center).add(0, 0.2, 0), 1f);
        }
        List<Ref<EntityStore>> near = new ArrayList<>();
        store.forEachChunk(NPCEntity.getComponentType(), (ArchetypeChunk<EntityStore> chunk, CommandBuffer<EntityStore> b) -> {
            for (int i = 0; i < chunk.size(); i++) {
                NPCEntity npc = chunk.getComponent(i, NPCEntity.getComponentType());
                TransformComponent transform = chunk.getComponent(i, TransformComponent.getComponentType());
                String role = npc == null ? null : npc.getRoleName();
                if (transform != null && (role == null || !role.startsWith(SEAL_ROLE)) && !BOSS_ROLE.equals(role)
                        && transform.getPosition().distance(center) <= radius) {
                    near.add(chunk.getReferenceTo(i));
                }
            }
        });
        int healthIndex = DefaultEntityStatTypes.getHealth();
        for (Ref<EntityStore> ref : near) {
            if ((!ref.equals(caster) && !Foes.allies(caster, ref, store)) || Telegraphs.position(store, ref) == null) {
                continue;
            }
            EntityStatMap stats = store.getComponent(ref, EntityStatMap.getComponentType());
            EntityStatValue health = stats == null ? null : stats.get(healthIndex);
            if (health != null && health.get() < health.getMax()) {
                stats.setStatValue(healthIndex, Math.min(health.getMax(), health.get() + amount));
            }
        }
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        // Serveur uniquement.
    }
}
