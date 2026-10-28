package dev.nakasar.hytale.fractals.stage;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.fractals.boss.BossBarSystem;

import java.util.Collections;
import java.util.Map;
import java.util.Set;
import java.util.WeakHashMap;
import java.util.function.BiConsumer;

/**
 * Barre de vie invulnérable des boss protégés (Kevin, 2026-10-28, valable pour tous les boss) : tant que
 * {@link FractalStage#shielded} est vrai pour un PNJ à barre de boss, il porte le composant vanilla
 * {@link Invulnerable}, comme les boss du donjon Deepworks ; le client passe alors sa barre en mode invulnérable.
 * Le filtre de la fractale annule déjà ces coups : le composant ne change que l'affichage (et coupe aussi le vide).
 *
 * <p>Le système ne retire que ce qu'il a posé : les boss qui gèrent eux-mêmes leur invulnérabilité (Mossman, Carnasse,
 * Tête-de-pierre…) gardent la leur. {@code minions.ShieldUnloadSystem} la lève au déchargement et au rechargement.
 */
public final class StageShieldSystem extends TickingSystem<EntityStore> {

    private static final float INTERVAL = 0.1f;

    /** Boss rendus invulnérables par ce système. */
    private static final Set<Ref<EntityStore>> PLACED = Collections.synchronizedSet(Collections.newSetFromMap(new WeakHashMap<>()));

    /** Système partagé par les mondes, chacun sur son thread : un compte à rebours par monde. */
    private final Map<World, Float> wait = Collections.synchronizedMap(new WeakHashMap<>());

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        FractalStage stage = Stages.of(world);
        if (stage == null) {
            return;
        }
        float left = wait.getOrDefault(world, 0f) - dt;
        if (left > 0f) {
            wait.put(world, left);
            return;
        }
        wait.put(world, INTERVAL);
        BiConsumer<ArchetypeChunk<EntityStore>, CommandBuffer<EntityStore>> visit = (chunk, buffer) -> {
            boolean has = chunk.getArchetype().contains(Invulnerable.getComponentType());
            for (int i = 0; i < chunk.size(); i++) {
                NPCEntity npc = chunk.getComponent(i, NPCEntity.getComponentType());
                String role = npc == null ? null : npc.getRoleName();
                if (!BossBarSystem.isElite(role)) {
                    continue;
                }
                Ref<EntityStore> ref = chunk.getReferenceTo(i);
                boolean shielded = stage.shielded(world, store, ref, role);
                if (shielded && !has) {
                    buffer.ensureComponent(ref, Invulnerable.getComponentType());
                    PLACED.add(ref);
                } else if (!shielded && has && PLACED.remove(ref)) {
                    buffer.tryRemoveComponent(ref, Invulnerable.getComponentType());
                }
            }
        };
        store.forEachChunk(NPCEntity.getComponentType(), visit);
    }
}
