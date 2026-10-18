package dev.nakasar.hytale.vampires.breach;

import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.RefSystem;
import com.hypixel.hytale.server.core.entity.reference.InvalidatablePersistentRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.spawning.spawnmarkers.SpawnMarkerEntity;

/**
 * Fait repartir les chasseurs quand la brèche se referme.
 *
 * <p>Les marqueurs d'apparition {@value #MARKER} sont des entités du prefab de la brèche : à la fin de
 * l'évènement, le serveur restaure le terrain et retire ces marqueurs, mais un marqueur retiré laisse ses PNJ
 * dans le monde : le jeu ne les fait disparaître que 30 s plus tard, et pas tant qu'ils combattent
 * ({@code SpawnReferenceSystems$TickingSpawnMarkerSystem}, « marker lost »). On retire donc ici tout de suite les
 * chasseurs chargés d'un marqueur de brèche supprimé ; ceux d'un chunk déchargé passent par ce délai vanilla quand
 * le chunk revient. Un déchargement de chunk ({@link RemoveReason#UNLOAD}) ne touche à rien.
 */
public final class BreachHunterCleanupSystem extends RefSystem<EntityStore> {

    public static final String MARKER = "Nakasar_Breach_Hunter";

    @Override
    public Query<EntityStore> getQuery() {
        return SpawnMarkerEntity.getComponentType();
    }

    @Override
    public void onEntityAdded(Ref<EntityStore> ref, AddReason reason, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
    }

    @Override
    public void onEntityRemove(Ref<EntityStore> ref, RemoveReason reason, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
        if (reason != RemoveReason.REMOVE) {
            return;
        }
        SpawnMarkerEntity marker = store.getComponent(ref, SpawnMarkerEntity.getComponentType());
        if (marker == null || !MARKER.equals(marker.getSpawnMarkerId())) {
            return;
        }
        for (InvalidatablePersistentRef npc : marker.getNpcReferences()) {
            Ref<EntityStore> npcRef = npc == null ? null : npc.getEntity(store);
            if (npcRef != null && npcRef.isValid()) {
                buffer.tryRemoveEntity(npcRef, RemoveReason.REMOVE);
            }
        }
    }
}
