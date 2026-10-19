package dev.nakasar.hytale.vampires.vampirism;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.SystemGroup;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.protocol.ColorLight;
import com.hypixel.hytale.protocol.ComponentUpdateType;
import com.hypixel.hytale.protocol.DynamicLightUpdate;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.modules.entity.component.DynamicLight;
import com.hypixel.hytale.server.core.modules.entity.tracker.EntityTrackerSystems;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.vampires.VampiresPlugin;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Vision nocturne du vampire, vue de lui seul. La nuit, une faible lumière l'entoure, mais elle n'est envoyée qu'à son
 * propre client : les autres joueurs ne voient rien, un vampire n'est pas reconnaissable à sa lumière.
 *
 * <p>Une lumière d'entité ({@link DynamicLight}) serait envoyée à tous ceux qui voient le joueur
 * ({@code EntitySystems.DynamicLightTracker}). Ce système, dans le même groupe, envoie la mise à jour de lumière au
 * seul spectateur qu'est le joueur lui-même, sans poser de composant. Quand le joueur porte une vraie lumière d'entité
 * (aura de lumière), elle passe avant et ce système se tait.
 *
 * <p>Il suit tous les joueurs, pas seulement les vampires, pour éteindre la lumière d'un joueur guéri. La lumière est
 * renvoyée toutes les {@value #REFRESH_SECONDS} secondes : un retrait du jeu parti dans le même paquet (fin d'une
 * aura) ou une entité reconstruite par le client (mort) ne l'éteint pas pour la nuit. Le retrait est réessayé tant
 * que le client ne l'a pas reçu.
 */
public final class PrivateNightLightSystem extends EntityTickingSystem<EntityStore> {

    /** Faible et froide : elle aide à voir sans colorer la nuit. */
    static final ColorLight NIGHT_LIGHT = new ColorLight((byte) 6, (byte) 3, (byte) 3, (byte) 4);
    static final float REFRESH_SECONDS = 2f;
    /** Au-delà, un vampire jamais visible de lui-même est signalé dans le journal (une fois). */
    private static final float UNSEEN_WARNING_SECONDS = 30f;

    private static final Query<EntityStore> QUERY = Query.and(Player.getComponentType(),
            EntityTrackerSystems.EntityViewer.getComponentType());

    /** Joueurs dont le client a (peut-être) reçu la lumière, et secondes avant le prochain renvoi. */
    private final Map<Ref<EntityStore>, Float> lit = new ConcurrentHashMap<>();
    /** Vampires qui veulent la lumière mais ne sont pas visibles d'eux-mêmes, et depuis combien de secondes. */
    private final Map<Ref<EntityStore>, Float> unseen = new ConcurrentHashMap<>();
    private final AtomicBoolean warned = new AtomicBoolean();

    @Override
    public SystemGroup<EntityStore> getGroup() {
        return EntityTrackerSystems.QUEUE_UPDATE_GROUP;
    }

    @Override
    public Query<EntityStore> getQuery() {
        return QUERY;
    }

    @Override
    public boolean isParallel(int archetypeChunkSize, int taskCount) {
        return false;
    }

    @Override
    public void tick(float dt, int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                     CommandBuffer<EntityStore> buffer) {
        Ref<EntityStore> ref = chunk.getReferenceTo(index);
        boolean ownLight = buffer.getComponent(ref, DynamicLight.getComponentType()) != null;
        boolean wanted = !ownLight && buffer.getComponent(ref, Vampire.getComponentType()) != null
                && !SunExposure.isDay(store);
        if (!wanted && !lit.containsKey(ref)) {
            unseen.remove(ref);
            return; // le cas de presque tous les joueurs
        }
        EntityTrackerSystems.EntityViewer self = chunk.getComponent(index,
                EntityTrackerSystems.EntityViewer.getComponentType());
        EntityTrackerSystems.Visible visible = buffer.getComponent(ref, EntityTrackerSystems.Visible.getComponentType());
        if (visible == null || !visible.visibleTo.containsKey(ref)) {
            if (wanted) {
                warnIfNeverSeen(ref, dt);
            }
            return; // le client ne suit pas (encore) sa propre entité : on réessaiera
        }
        unseen.remove(ref);

        if (!wanted) {
            if (!ownLight) { // une vraie lumière d'entité a remplacé la nôtre chez tout le monde
                self.queueRemove(ref, ComponentUpdateType.DynamicLight);
            }
            lit.remove(ref);
            return;
        }
        Float refreshIn = lit.get(ref);
        float left = refreshIn == null || visible.newlyVisibleTo.containsKey(ref) ? 0f : refreshIn - dt;
        if (left <= 0f) {
            self.queueUpdate(ref, new DynamicLightUpdate(new ColorLight(NIGHT_LIGHT)));
            left = REFRESH_SECONDS;
        }
        lit.put(ref, left);
        if (lit.size() > 64) {
            lit.keySet().removeIf(r -> !r.isValid()); // joueurs partis
        }
    }

    private void warnIfNeverSeen(Ref<EntityStore> ref, float dt) {
        float seconds = unseen.merge(ref, dt, Float::sum);
        if (seconds >= UNSEEN_WARNING_SECONDS && warned.compareAndSet(false, true)) {
            VampiresPlugin.get().getLogger().atWarning().log(
                    "Vision nocturne : un vampire n'est pas visible de lui-même depuis %.0f s, sa lumière privée "
                            + "ne peut pas lui être envoyée", seconds);
        }
        if (unseen.size() > 64) {
            unseen.keySet().removeIf(r -> !r.isValid());
        }
    }
}
