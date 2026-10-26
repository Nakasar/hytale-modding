package dev.nakasar.hytale.fractals.support;

import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.component.system.RefSystem;
import com.hypixel.hytale.server.core.entity.entities.ProjectileComponent;
import com.hypixel.hytale.server.core.modules.projectile.event.ProjectileLaunchEvent;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Sanctuaire (rune) : un dôme de {@link Skills#SANCTUARY_RADIUS} blocs qui détruit les projectiles des ennemis qui y
 * entrent. Les projectiles des PNJ sont notés au tir, sous leurs deux formes de la 0.7.2 :
 * <ul>
 *   <li>{@link Launch} : interaction {@code Projectile}, un {@link ProjectileLaunchEvent} sur le tireur ;</li>
 *   <li>{@link Legacy} : interaction {@code LaunchProjectile}, une entité à {@link ProjectileComponent} qui ne connaît que
 *   l'UUID de son tireur.</li>
 * </ul>
 * Les projectiles des boss et des élites passent : leurs attaques sont des règles de combat, pas des tirs ordinaires.
 */
public final class SanctuarySystem {

    /** Un dôme levé (centre au sol, rayon de la sphère), jusqu'à {@code until}. */
    public record Dome(World world, Vector3d center, double radius, long until) {
    }

    /** Projectiles ennemis vivants, notés au tir → monde. */
    private static final Map<Ref<EntityStore>, World> HOSTILE = new ConcurrentHashMap<>();
    private static final Map<World, Integer> DOMES = new ConcurrentHashMap<>();

    private SanctuarySystem() {
    }

    /** Lève un dôme : à chaque tick, les projectiles ennemis dans la sphère sont détruits. */
    static Dome raise(World world, Vector3d center, double radius, float seconds) {
        Dome dome = new Dome(world, new Vector3d(center), radius, System.nanoTime() + Telegraphs.seconds(seconds));
        DOMES.merge(world, 1, Integer::sum);
        TelegraphSystem.start(world, (w, s, now) -> {
            if (now >= dome.until()) {
                DOMES.computeIfPresent(w, (k, n) -> n <= 1 ? null : n - 1);
                return true;
            }
            for (var it = HOSTILE.entrySet().iterator(); it.hasNext(); ) {
                var e = it.next();
                Ref<EntityStore> projectile = e.getKey();
                if (!projectile.isValid()) {
                    it.remove();
                    continue;
                }
                if (e.getValue() != w) {
                    continue;
                }
                Vector3d at = Telegraphs.position(s, projectile);
                if (at != null && at.distance(dome.center()) <= dome.radius()) {
                    it.remove();
                    Telegraphs.particle(s, Skills.FX_WARD, at, 0.8f);
                    Spawns.remove(s, projectile);
                }
            }
            return false;
        });
        return dome;
    }

    private static void note(Store<EntityStore> store, CommandBuffer<EntityStore> buffer, Ref<EntityStore> shooter,
                             Ref<EntityStore> projectile) {
        if (shooter == null || !shooter.isValid() || projectile == null) {
            return;
        }
        NPCEntity npc = buffer.getComponent(shooter, NPCEntity.getComponentType());
        if (npc == null || Support.immune(store, shooter)) {
            return;
        }
        World world = store.getExternalData().getWorld();
        HOSTILE.put(projectile, world);
        if (HOSTILE.size() > 256) {
            HOSTILE.keySet().removeIf(r -> !r.isValid());
        }
    }

    public static void clearAll() {
        HOSTILE.clear();
        DOMES.clear();
    }

    public static final class Launch extends EntityEventSystem<EntityStore, ProjectileLaunchEvent> {

        public Launch() {
            super(ProjectileLaunchEvent.class);
        }

        @Override
        public Query<EntityStore> getQuery() {
            return NPCEntity.getComponentType();
        }

        @Override
        public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                           CommandBuffer<EntityStore> buffer, ProjectileLaunchEvent event) {
            Ref<EntityStore> shooter = chunk.getReferenceTo(index);
            Ref<EntityStore> projectile = event.getProjectileRef();
            if (projectile != null && !projectile.equals(shooter)) {
                note(store, buffer, shooter, projectile);
            }
        }
    }

    public static final class Legacy extends RefSystem<EntityStore> {

        @Override
        public Query<EntityStore> getQuery() {
            return ProjectileComponent.getComponentType();
        }

        @Override
        public void onEntityAdded(Ref<EntityStore> ref, AddReason reason, Store<EntityStore> store,
                                  CommandBuffer<EntityStore> buffer) {
            if (reason != AddReason.SPAWN) {
                return;
            }
            ProjectileComponent projectile = buffer.getComponent(ref, ProjectileComponent.getComponentType());
            UUID creator = projectile == null ? null : projectile.getCreatorUuid();
            Ref<EntityStore> shooter = creator == null ? null : store.getExternalData().getRefFromUUID(creator);
            note(store, buffer, shooter, ref);
        }

        @Override
        public void onEntityRemove(Ref<EntityStore> ref, RemoveReason reason, Store<EntityStore> store,
                                   CommandBuffer<EntityStore> buffer) {
            HOSTILE.remove(ref);
        }
    }
}
