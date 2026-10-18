package dev.nakasar.hytale.vampires.silver;

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
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.modules.projectile.event.ProjectileLaunchEvent;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.UUID;

/**
 * Marque les projectiles tirés avec une arme en argent, au moment du tir. Deux sortes de projectiles en 0.7.2 :
 * <ul>
 *   <li>{@link Launch} : interaction {@code Projectile} (arc, arbalète, salve), qui envoie un
 *       {@link ProjectileLaunchEvent} au tireur. Le projectile est en argent si l'arme l'est ou si la flèche tirée
 *       l'est ({@link ArrowQuiver}, d'après {@link TakeArrowInteraction}) ;</li>
 *   <li>{@link Legacy} : interaction {@code LaunchProjectile} (lance de jet lancée, tromblon), entité à
 *       {@link ProjectileComponent} qui ne connaît que l'UUID de son tireur.</li>
 * </ul>
 * Limites : la dernière lance de jet lancée ne laisse rien dans la main ; si le jeu la retire de l'inventaire avant
 * de créer le projectile, ce projectile-là n'est pas marqué. Un tir qui ne consomme pas de flèche (gros carreau de
 * l'arbalète) prend quand même la plus ancienne flèche notée.
 */
public final class SilverProjectileSystems {

    private SilverProjectileSystems() {
    }

    public static final class Launch extends EntityEventSystem<EntityStore, ProjectileLaunchEvent> {

        public Launch() {
            super(ProjectileLaunchEvent.class);
        }

        @Override
        public Query<EntityStore> getQuery() {
            return Query.any();
        }

        @Override
        public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                           CommandBuffer<EntityStore> buffer, ProjectileLaunchEvent event) {
            Ref<EntityStore> shooter = chunk.getReferenceTo(index);
            Ref<EntityStore> projectile = event.getProjectileRef();
            if (projectile == null || projectile.equals(shooter)) {
                return;
            }
            // Toujours consommer la flèche notée, même tirée d'un arc en argent, pour garder la liste en phase.
            boolean silverArrow = ArrowQuiver.fire(shooter);
            if (silverArrow || SilverWeapons.isSilver(InventoryComponent.getItemInHand(buffer, shooter))) {
                SilverWeapons.markProjectile(projectile);
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
            if (shooter != null && shooter.isValid()
                    && SilverWeapons.isSilver(InventoryComponent.getItemInHand(buffer, shooter))) {
                SilverWeapons.markProjectile(ref);
            }
        }

        @Override
        public void onEntityRemove(Ref<EntityStore> ref, RemoveReason reason, Store<EntityStore> store,
                                   CommandBuffer<EntityStore> buffer) {
        }
    }
}
