package dev.nakasar.hytale.vampires.tower;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.protocol.ColorLight;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.modules.entity.component.DynamicLight;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.vampires.purifying.LightAura;

import java.util.Collections;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.WeakHashMap;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Lanterne élémentaire (objet unique du sac de l'Alchimiste) : tenue en main ou dans la main secondaire, elle éclaire
 * son porteur d'une lumière qui passe du feu au givre, à la foudre puis aux racines, en fondu, en
 * {@value #CYCLE_SECONDS} s. Rangée, la lumière s'éteint. Un porteur sous aura de lumière ({@link LightAura}) garde
 * la lumière de l'aura.
 *
 * <p>La lumière est un {@link DynamicLight} (vue de tous, jamais sauvegardée). Un porteur qui a déjà une autre
 * lumière la garde : la lanterne ne la remplace pas et ne la retire pas. La couleur est changée sur place, seulement
 * quand elle change.
 */
public final class ElementalLanternSystem extends TickingSystem<EntityStore> {

    public static final String LANTERN = "Nakasar_Elemental_Lantern";
    private static final float INTERVAL = 0.25f;
    private static final float CYCLE_SECONDS = 8f;
    private static final byte RADIUS = 12;
    /** Feu, givre, foudre, racines (rouge, vert, bleu sur 0 à 15). */
    private static final int[][] COLOURS = {{15, 6, 2}, {6, 12, 15}, {15, 14, 5}, {6, 15, 4}};

    private final Map<World, Float> wait = Collections.synchronizedMap(new WeakHashMap<>());
    /** Porteurs que la lanterne éclaire, par UUID (la lumière suit le joueur d'un monde à l'autre, pas sa Ref). */
    private final Set<UUID> lit = ConcurrentHashMap.newKeySet();

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        float left = wait.getOrDefault(world, 0f) - dt;
        if (left > 0f) {
            wait.put(world, left);
            return;
        }
        wait.put(world, INTERVAL);
        world.execute(() -> step(world));
    }

    private void step(World world) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        double seconds = System.nanoTime() / 1e9;
        ColorLight light = colour((float) (seconds % CYCLE_SECONDS / CYCLE_SECONDS));
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            if (ref == null || !ref.isValid() || store.getComponent(ref, LightAura.getComponentType()) != null) {
                continue;
            }
            UUID uuid = player.getUuid();
            DynamicLight current = store.getComponent(ref, DynamicLight.getComponentType());
            boolean ours = lit.contains(uuid);
            if (holdsLantern(store, ref)) {
                if (current == null) {
                    lit.add(uuid);
                    store.putComponent(ref, DynamicLight.getComponentType(), new DynamicLight(light));
                } else if (ours && !light.equals(current.getColorLight())) {
                    current.setColorLight(light);
                }
                // Une autre lumière (pas la nôtre) : on la laisse.
            } else if (ours) {
                lit.remove(uuid);
                if (current != null) {
                    store.tryRemoveComponent(ref, DynamicLight.getComponentType());
                }
            }
        }
    }

    private static boolean holdsLantern(Store<EntityStore> store, Ref<EntityStore> ref) {
        if (isLantern(InventoryComponent.getItemInHand(store, ref))) {
            return true;
        }
        InventoryComponent.Utility utility = store.getComponent(ref, InventoryComponent.Utility.getComponentType());
        return utility != null && isLantern(utility.getActiveItem());
    }

    private static boolean isLantern(ItemStack stack) {
        return stack != null && !ItemStack.isEmpty(stack) && LANTERN.equals(stack.getItemId());
    }

    /** Couleur au point {@code t} du cycle (0 à 1), en fondu d'un élément au suivant. */
    static ColorLight colour(float t) {
        float position = t * COLOURS.length;
        int from = (int) position % COLOURS.length;
        int to = (from + 1) % COLOURS.length;
        float blend = position - (int) position;
        byte[] rgb = new byte[3];
        for (int i = 0; i < 3; i++) {
            rgb[i] = (byte) Math.round(COLOURS[from][i] + (COLOURS[to][i] - COLOURS[from][i]) * blend);
        }
        return new ColorLight(RADIUS, rgb[0], rgb[1], rgb[2]);
    }
}
