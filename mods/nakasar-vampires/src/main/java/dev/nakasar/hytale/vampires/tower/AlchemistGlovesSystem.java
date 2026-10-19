package dev.nakasar.hytale.vampires.tower;

import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.RefSystem;
import com.hypixel.hytale.server.core.entity.entities.ProjectileComponent;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.modules.physics.SimplePhysicsProvider;
import com.hypixel.hytale.server.core.modules.physics.util.ForceProviderStandardState;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import org.joml.Vector3d;

import java.lang.reflect.Field;
import java.util.UUID;

/**
 * Gants de l'Alchimiste (objet unique du sac de l'Alchimiste) : les fioles et bombes lancées par leur porteur partent
 * {@value #SPEED}× plus vite, donc plus loin. Les jets d'objets du jeu ({@code Item_Throw}, interaction
 * {@code LaunchProjectile}) créent une entité à {@link ProjectileComponent} qui ne connaît que l'UUID de son lanceur :
 * on la reconnaît à son asset (dossier {@code Projectiles/Player/Bomb} : {@code Bomb*}, dont la fiole de poison
 * {@code Bomb_Potion_Poison}) dès sa création.
 *
 * <p>{@code ProjectileComponent.shoot} range la vitesse de départ dans {@code nextTickVelocity}, appliquée au premier
 * tick de physique ({@code SimplePhysicsProvider.getVelocity()} vaut encore zéro à la création, et le composant
 * {@code Velocity} est écrasé à ce tick). Ce champ n'a pas d'accesseur public : on le lit par réflexion.
 */
public final class AlchemistGlovesSystem extends RefSystem<EntityStore> {

    public static final String GLOVES = "Armor_Nakasar_Alchemist_Gloves";
    private static final double SPEED = 1.4;
    private static final Field FORCE_STATE = forceStateField();

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
        String asset = projectile == null ? null : projectile.getProjectileAssetName();
        UUID creator = projectile == null ? null : projectile.getCreatorUuid();
        if (asset == null || !asset.startsWith("Bomb") || creator == null) {
            return;
        }
        Ref<EntityStore> thrower = store.getExternalData().getRefFromUUID(creator);
        if (thrower == null || !thrower.isValid() || !wearsGloves(buffer, thrower)) {
            return;
        }
        Vector3d launch = launchVelocity(projectile.getSimplePhysicsProvider());
        if (launch != null) {
            launch.mul(SPEED);
        }
    }

    @Override
    public void onEntityRemove(Ref<EntityStore> ref, RemoveReason reason, Store<EntityStore> store,
                               CommandBuffer<EntityStore> buffer) {
    }

    /** Vitesse de départ en attente du projectile (modifiable sur place), ou {@code null}. */
    private static Vector3d launchVelocity(SimplePhysicsProvider physics) {
        if (physics == null || FORCE_STATE == null) {
            return null;
        }
        try {
            return ((ForceProviderStandardState) FORCE_STATE.get(physics)).nextTickVelocity;
        } catch (IllegalAccessException | ClassCastException e) {
            return null;
        }
    }

    private static Field forceStateField() {
        try {
            Field field = SimplePhysicsProvider.class.getDeclaredField("forceProviderStandardState");
            field.setAccessible(true);
            return field;
        } catch (ReflectiveOperationException | RuntimeException e) {
            return null;
        }
    }

    private static boolean wearsGloves(CommandBuffer<EntityStore> buffer, Ref<EntityStore> ref) {
        InventoryComponent.Armor armor = buffer.getComponent(ref, InventoryComponent.Armor.getComponentType());
        ItemContainer worn = armor == null ? null : armor.getInventory();
        if (worn == null) {
            return false;
        }
        for (short slot = 0; slot < worn.getCapacity(); slot++) {
            ItemStack stack = worn.getItemStack(slot);
            if (stack != null && !ItemStack.isEmpty(stack) && GLOVES.equals(stack.getItemId())) {
                return true;
            }
        }
        return false;
    }
}
