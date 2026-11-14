package dev.nakasar.hytale.peuples.zone;

import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathSystems;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.peuples.raid.Raids;

/**
 * Tailler la ruche (étape 8) : un Scarak (rôles vanilla {@code Scarak_*}, assaillants {@code Raider_Scarak_*}) abattu
 * par un joueur retire des points à la ruche du monde ({@link Hive}).
 */
public final class HiveDeathSystem extends DeathSystems.OnDeathSystem {

    @Override
    public Query<EntityStore> getQuery() {
        return NPCEntity.getComponentType();
    }

    @Override
    public void onComponentAdded(Ref<EntityStore> ref, DeathComponent death, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
        NPCEntity npc = buffer.getComponent(ref, NPCEntity.getComponentType());
        String role = npc == null ? null : npc.getRoleName();
        int points = points(role);
        if (points <= 0) {
            return;
        }
        Damage info = death.getDeathInfo();
        if (info == null || !(info.getSource() instanceof Damage.EntitySource source)) {
            return;
        }
        Ref<EntityStore> by = source.getRef();
        PlayerRef player = by == null || !by.isValid() ? null : buffer.getComponent(by, PlayerRef.getComponentType());
        if (player == null) {
            return;
        }
        World world = store.getExternalData().getWorld();
        var at = player.getTransform().getPosition();
        world.execute(() -> Hive.cut(world, world.getEntityStore().getStore(), points, at.x(), at.z()));
    }

    static int points(String role) {
        if (role == null) {
            return 0;
        }
        if (role.startsWith(Raids.RAIDER_PREFIX + "Scarak_")) {
            return Hive.RAIDER;
        }
        if (role.equals("Scarak_Broodmother") || role.startsWith("Scarak_Broodmother")) {
            return Hive.BROODMOTHER;
        }
        return role.startsWith("Scarak_") ? Hive.KILL : 0;
    }
}
