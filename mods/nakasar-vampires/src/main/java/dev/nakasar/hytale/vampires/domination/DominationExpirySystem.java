package dev.nakasar.hytale.vampires.domination;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.role.support.MarkedEntitySupport;
import dev.nakasar.hytale.vampires.allegiance.Allegiances;

/**
 * Fin d'une Domination sur un PNJ : il oublie les cibles qu'il s'était choisies parmi ses anciens alliés, pour
 * reprendre sa place dans son camp au lieu de finir le combat. Les rôles du mod relâchent déjà une cible devenue
 * amicale ; ce nettoyage couvre aussi les mobs vanilla dominés.
 */
public final class DominationExpirySystem extends TickingSystem<EntityStore> {

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        for (Ref<EntityStore> victim : Dominations.drainExpired(store)) {
            MarkedEntitySupport marked = store.getComponent(victim, MarkedEntitySupport.getComponentType());
            if (marked == null) {
                continue; // un joueur
            }
            for (int slot = 0; slot < marked.getMarkedEntitySlotCount(); slot++) {
                Ref<EntityStore> target = marked.getMarkedEntityRef(slot);
                if (target != null && target.isValid() && Allegiances.wereAllies(victim, target, store)) {
                    marked.clearMarkedEntity(slot);
                }
            }
        }
    }
}
