package dev.nakasar.hytale.vampires.breach;

import com.hypixel.hytale.builtin.adventure.worldevents.WorldEventManager;
import com.hypixel.hytale.builtin.adventure.worldevents.WorldEventRecord;
import com.hypixel.hytale.builtin.adventure.worldevents.WorldEventsWorldConfig;
import com.hypixel.hytale.builtin.adventure.worldevents.action.EventStartAction;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.server.core.universe.Universe;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import java.util.UUID;

/**
 * Lance l'évènement {@value #EVENT} (brèche des chasseurs de vampires) dans le monde principal.
 *
 * <p>Les évènements vanilla sont lancés par la configuration de gameplay {@code Default} ({@code WorldEvents.Events}),
 * qu'un mod ne peut pas compléter sans la remplacer en entier. On le lance donc nous-mêmes, avec un identifiant
 * fixe : le gestionnaire d'évènements refuse un second évènement du même identifiant, et celui qui a été
 * sauvegardé avec le monde reprend où il en était. Seul le monde par défaut de l'univers est concerné (pas les
 * fragments ni les instances), et pas un monde où les évènements sont désactivés.
 */
public final class HunterBreachStarter extends TickingSystem<EntityStore> {

    public static final String EVENT = "Nakasar_Hunter_Breach";
    /** Identifiant fixe de l'évènement dans chaque monde. */
    public static final UUID EVENT_ID = UUID.fromString("6a1c2f3e-8b4d-4e51-9a7c-0d5e3b2f7c19");
    private static final WorldEventRecord RECORD = new WorldEventRecord(EVENT_ID, EVENT, true);
    /** Laisse le stockage des évènements du monde se recharger avant le premier essai. */
    private static final float FIRST_DELAY = 20f;
    private static final float INTERVAL = 10f;

    private float wait = FIRST_DELAY;

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        // Le système est partagé par tous les mondes : seul le monde par défaut fait avancer le compte à rebours.
        World world = store.getExternalData().getWorld();
        if (world != Universe.get().getDefaultWorld()) {
            return;
        }
        wait -= dt;
        if (wait > 0f) {
            return;
        }
        wait = INTERVAL;
        if (!WorldEventsWorldConfig.isEnabled(world)) {
            return;
        }
        if (store.getResource(WorldEventManager.getResourceType()).get(EVENT_ID) != null) {
            return;
        }
        // Hors du passage des systèmes : l'évènement est une entité ajoutée au magasin.
        world.execute(() -> {
            Store<EntityStore> live = world.getEntityStore().getStore();
            if (live.getResource(WorldEventManager.getResourceType()).get(EVENT_ID) == null) {
                EventStartAction.startEvent(live, RECORD);
            }
        });
    }
}
