package dev.nakasar.hytale.peuples.zone;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.entities.player.movement.MovementManager;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.village.Blocks;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Terrain;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;
import org.joml.Vector3d;

import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Les climats des zones 2 et 3 (étape 8, GDD Progression des zones) et les objets de passage portés.
 *
 * <ul>
 *   <li>Soif (zone 2, de {@value #THIRST_FROM} h à {@value #THIRST_UNTIL} h) : hors de l'ombre (un bloc au-dessus de la
 *   tête), loin de l'eau, d'un abri d'Écho et d'une oasis feran, l'endurance ne remonte plus. L'Outre d'oasis l'annule
 *   ({@value #QUENCH_SECONDS} s, effet {@value #QUENCHED}).</li>
 *   <li>Froid (zone 3) : l'hypothermie de la fractale Tempête de neige, sans éclat de glace. Hors d'un abri et loin d'un
 *   feu (feu de camp, brasero, lave), une pile toutes les {@value #GAIN_EVERY} s jusqu'à {@value #MAX_COLD} ; à l'abri
 *   ou au chaud, une pile de moins toutes les {@value #WARM_EVERY} s. Chaque pile retire {@value #PART_PER_STACK} des PV
 *   max par seconde (cause {@value #COLD}). Le Manteau du givre porté l'annule.</li>
 *   <li>Bracelet de vent porté dans l'inventaire : saut x{@value #JUMP_FACTOR} (force de saut envoyée au client, comme
 *   le Saut chargé des fractales).</li>
 *   <li>Révélations (GDD : l'objet de passage « révèle le village suivant ») : porter la Graine d'Écho donne la position de
 *   l'oasis feran, porter le Bracelet de vent celle du hameau des Renoncés, une fois par joueur.</li>
 * </ul>
 */
public final class Climate {

    public static final String KEYS = "nakasar_peuples.climate.";
    public static final int THIRST_FROM = 9;
    public static final int THIRST_UNTIL = 18;
    public static final float QUENCH_SECONDS = 1200f;
    public static final String THIRST = "Nakasar_Peuples_Thirst";
    public static final String QUENCHED = "Nakasar_Peuples_Quenched";
    public static final int MAX_COLD = 10;
    public static final float GAIN_EVERY = 6f;
    public static final float WARM_EVERY = 1.2f;
    public static final float PART_PER_STACK = 0.002f;
    public static final String COLD = "Nakasar_Peuples_Cold";
    public static final String HYPOTHERMIA = "Nakasar_Peuples_Hypothermia_";
    public static final String WARMTH = "Nakasar_Peuples_Warmth";
    public static final float JUMP_FACTOR = 1.35f;

    public static final String BRACELET = "Nakasar_Peuples_Wind_Bracelet";
    public static final String MANTLE = "Nakasar_Peuples_Frost_Mantle";
    public static final String WATERSKIN = "Nakasar_Peuples_Oasis_Waterskin";
    public static final String ECHO_SEED = "Nakasar_Peuples_Echo_Seed";

    /** Rayon de chaleur d'un feu, et d'eau ou d'abri d'Écho qui étanche la soif. */
    static final int HEAT_RADIUS = 5;
    static final int WATER_RADIUS = 2;
    static final int SHELTER_RADIUS = 10;
    /** Hauteur sondée au-dessus de la tête pour l'ombre ou le toit. */
    static final int ROOF_HEIGHT = 24;

    private static final class State {
        float clock;
        // Soif
        boolean thirsty;
        float stamina = -1f;
        // Froid
        int stacks;
        float gain;
        float warm;
        int tier;
        boolean coldTold;
        // Bracelet
        boolean boosted;
    }

    private static final Map<UUID, State> STATES = new ConcurrentHashMap<>();
    /** Climat imposé par la commande d'essai ({@code /village climat}) : 2 (soif) ou 3 (froid). */
    private static final Map<UUID, Integer> FORCED = new ConcurrentHashMap<>();

    private Climate() {
    }

    public static void force(UUID player, int zone) {
        if (zone == 2 || zone == 3) {
            FORCED.put(player, zone);
        } else {
            FORCED.remove(player);
        }
    }

    public static Integer forced(UUID player) {
        return FORCED.get(player);
    }

    public static void clearAll() {
        STATES.clear();
        FORCED.clear();
    }

    /** Ce que le climat fait au joueur, en une ligne (commande {@code /village zone}). */
    public static Message describe(Store<EntityStore> store, PlayerRef player) {
        State s = STATES.get(player.getUuid());
        Ref<EntityStore> ref = player.getReference();
        if (s != null && s.thirsty) {
            return Message.translation(KEYS + "status.thirsty");
        }
        if (s != null && s.stacks > 0) {
            return Message.translation(KEYS + "status.cold").param("stacks", s.stacks).param("max", MAX_COLD);
        }
        if (ref != null && ref.isValid() && Effects.has(store, ref, QUENCHED)) {
            return Message.translation(KEYS + "status.quenched");
        }
        return Message.translation(KEYS + "status.fine");
    }

    static void step(World world, Store<EntityStore> store, float dt) {
        Set<UUID> seen = new HashSet<>();
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            if (ref == null || !ref.isValid()) {
                continue;
            }
            seen.add(player.getUuid());
            State s = STATES.computeIfAbsent(player.getUuid(), u -> new State());
            if (s.thirsty) {
                holdStamina(store, ref, s);
            }
            s.clock += dt;
            if (s.clock < 1f) {
                continue;
            }
            float elapsed = s.clock;
            s.clock = 0f;
            second(world, store, player, ref, s, elapsed);
        }
        STATES.keySet().removeIf(u -> !seen.contains(u) && !FORCED.containsKey(u));
    }

    private static void second(World world, Store<EntityStore> store, PlayerRef player, Ref<EntityStore> ref, State s, float dt) {
        Vector3d at = player.getTransform().getPosition();
        Integer forced = FORCED.get(player.getUuid());
        int zone = forced != null ? forced : Zones.at(world, at.x(), at.z());
        bracelet(store, player, ref, s);
        reveal(world, store, player, ref);

        boolean thirsty = zone == 2 && thirsty(world, store, ref, at);
        if (thirsty != s.thirsty) {
            s.thirsty = thirsty;
            s.stamina = -1f;
            NotificationUtil.sendNotification(player.getPacketHandler(),
                    Message.translation(KEYS + (thirsty ? "thirst.start" : "thirst.stop")),
                    thirsty ? NotificationStyle.Warning : NotificationStyle.Success);
            if (!thirsty) {
                Effects.clear(store, ref, THIRST);
            }
        }
        if (thirsty) {
            Effects.apply(store, ref, THIRST, 1.5f);
        }

        if (zone == 3 && !wears(store, ref, MANTLE)) {
            cold(world, store, player, ref, s, at, dt);
        } else if (s.stacks > 0 || s.tier > 0) {
            s.stacks = 0;
            tier(store, ref, s, 0);
        }
    }

    // ---- Soif ----

    private static boolean thirsty(World world, Store<EntityStore> store, Ref<EntityStore> ref, Vector3d at) {
        int hour = GameClock.hour(store);
        if (hour < THIRST_FROM || hour >= THIRST_UNTIL || Effects.has(store, ref, QUENCHED)) {
            return false;
        }
        int x = (int) Math.floor(at.x());
        int y = (int) Math.floor(at.y());
        int z = (int) Math.floor(at.z());
        if (roofed(world.getChunkStore(), x, y, z) || nearWater(world, x, y, z)) {
            return false;
        }
        for (int[] shelter : ZoneRegistry.get(world).shelters()) {
            double dx = shelter[0] - at.x();
            double dz = shelter[2] - at.z();
            if (dx * dx + dz * dz <= SHELTER_RADIUS * SHELTER_RADIUS) {
                return false;
            }
        }
        return Villages.registry(world).nearestOf(People.FERAN, at.x(), at.z(), Villages.RADIUS) == null;
    }

    /** L'endurance ne remonte pas : toute hausse depuis le dernier pas est reprise. */
    private static void holdStamina(Store<EntityStore> store, Ref<EntityStore> ref, State s) {
        EntityStatMap stats = store.getComponent(ref, EntityStatMap.getComponentType());
        EntityStatValue stamina = stats == null ? null : stats.get(DefaultEntityStatTypes.getStamina());
        if (stamina == null) {
            return;
        }
        float now = stamina.get();
        if (s.stamina >= 0f && now > s.stamina) {
            stats.setStatValue(DefaultEntityStatTypes.getStamina(), s.stamina);
        } else {
            s.stamina = now;
        }
    }

    private static boolean nearWater(World world, int x, int y, int z) {
        Terrain terrain = new Terrain(world);
        for (int dx = -WATER_RADIUS; dx <= WATER_RADIUS; dx++) {
            for (int dz = -WATER_RADIUS; dz <= WATER_RADIUS; dz++) {
                for (int dy = -1; dy <= 1; dy++) {
                    if (terrain.hasFluid(x + dx, y + dy, z + dz)) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    /** Un bloc (feuillage compris) au-dessus de la tête : ombre au désert, toit dans la neige. */
    static boolean roofed(ChunkStore chunks, int x, int y, int z) {
        for (int dy = 2; dy <= ROOF_HEIGHT; dy++) {
            int id = Blocks.id(chunks, x, y + dy, z);
            if (id == Blocks.UNLOADED) {
                return false;
            }
            if (id != 0) {
                return true;
            }
        }
        return false;
    }

    // ---- Froid ----

    private static void cold(World world, Store<EntityStore> store, PlayerRef player, Ref<EntityStore> ref, State s, Vector3d at, float dt) {
        int x = (int) Math.floor(at.x());
        int y = (int) Math.floor(at.y());
        int z = (int) Math.floor(at.z());
        boolean warm = roofed(world.getChunkStore(), x, y, z) || nearHeat(world.getChunkStore(), x, y, z)
                || Villages.registry(world).nearestOf(People.RENONCE, at.x(), at.z(), Villages.RADIUS) != null;
        if (warm) {
            s.gain = 0f;
            s.warm += dt;
            while (s.warm >= WARM_EVERY && s.stacks > 0) {
                s.warm -= WARM_EVERY;
                s.stacks--;
            }
            if (s.stacks == 0) {
                s.warm = 0f;
            }
            Effects.apply(store, ref, WARMTH, 1.5f);
        } else {
            s.warm = 0f;
            s.gain += dt;
            if (s.gain >= GAIN_EVERY) {
                s.gain = 0f;
                s.stacks = Math.min(MAX_COLD, s.stacks + 1);
                if (!s.coldTold) {
                    s.coldTold = true;
                    NotificationUtil.sendNotification(player.getPacketHandler(), Message.translation(KEYS + "cold.start"),
                            NotificationStyle.Warning);
                }
            }
        }
        if (s.stacks > 0) {
            Effects.percent(store, ref, PART_PER_STACK * s.stacks, COLD);
        }
        tier(store, ref, s, (s.stacks + 1) / 2);
    }

    static boolean nearHeat(ChunkStore chunks, int x, int y, int z) {
        for (int dx = -HEAT_RADIUS; dx <= HEAT_RADIUS; dx++) {
            for (int dz = -HEAT_RADIUS; dz <= HEAT_RADIUS; dz++) {
                for (int dy = -2; dy <= 2; dy++) {
                    String name = Blocks.name(chunks, x + dx, y + dy, z + dz);
                    if (name != null && (name.contains("Campfire") || name.contains("Brazier") || name.startsWith("Fluid_Lava"))
                            && !name.startsWith("Deco_Campfire_Off")) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    /** Effet du palier (piles 1-2 : palier 1… 9-10 : palier 5), rafraîchi chaque seconde. */
    private static void tier(Store<EntityStore> store, Ref<EntityStore> ref, State s, int tier) {
        if (tier != s.tier && s.tier > 0) {
            Effects.clear(store, ref, HYPOTHERMIA + s.tier);
        }
        if (tier > 0) {
            Effects.apply(store, ref, HYPOTHERMIA + tier, 1.5f);
        }
        s.tier = tier;
    }

    // ---- Objets portés ----

    static boolean carries(Store<EntityStore> store, Ref<EntityStore> ref, String itemId) {
        return InventoryComponent.getCombined(store, ref, InventoryComponent.HOTBAR_STORAGE_BACKPACK)
                .canRemoveItemStack(new ItemStack(itemId, 1));
    }

    static boolean wears(Store<EntityStore> store, Ref<EntityStore> ref, String itemId) {
        InventoryComponent.Armor armor = store.getComponent(ref, InventoryComponent.Armor.getComponentType());
        ItemContainer worn = armor == null ? null : armor.getInventory();
        if (worn == null) {
            return false;
        }
        for (short slot = 0; slot < worn.getCapacity(); slot++) {
            ItemStack stack = worn.getItemStack(slot);
            if (stack != null && !ItemStack.isEmpty(stack) && itemId.equals(stack.getItemId())) {
                return true;
            }
        }
        return false;
    }

    private static void bracelet(Store<EntityStore> store, PlayerRef player, Ref<EntityStore> ref, State s) {
        boolean wanted = carries(store, ref, BRACELET);
        MovementManager movement = store.getComponent(ref, MovementManager.getComponentType());
        if (movement == null) {
            return;
        }
        float base = movement.getDefaultSettings() == null ? 0f : movement.getDefaultSettings().jumpForce;
        if (wanted && base > 0f) {
            // Rappliquée si un autre système (Saut chargé des fractales, changement de mode) l'a remise.
            if (!s.boosted || Math.abs(movement.getSettings().jumpForce - base * JUMP_FACTOR) > 0.01f) {
                movement.getSettings().jumpForce = base * JUMP_FACTOR;
                movement.update(player.getPacketHandler());
                s.boosted = true;
            }
        } else if (s.boosted) {
            movement.resetDefaultsAndUpdate(ref, store);
            s.boosted = false;
        }
    }

    /** Révèle une fois le village suivant à qui porte l'objet de passage du peuple précédent. */
    private static void reveal(World world, Store<EntityStore> store, PlayerRef player, Ref<EntityStore> ref) {
        PeuplesPlayer data = PeuplesPlayer.get(store, ref);
        if (data == null) {
            return;
        }
        reveal(world, player, data, ref, store, ECHO_SEED, People.FERAN);
        reveal(world, player, data, ref, store, BRACELET, People.RENONCE);
    }

    private static void reveal(World world, PlayerRef player, PeuplesPlayer data, Ref<EntityStore> ref, Store<EntityStore> store,
                               String item, People people) {
        String flag = "Reveal_" + people.id();
        if (data.hasFlag(flag) || !carries(store, ref, item)) {
            return;
        }
        Village village = Villages.registry(world).all().stream().filter(v -> v.people() == people).findFirst().orElse(null);
        if (village == null) {
            return;   // pas encore posé : on réessaiera
        }
        data.setFlag(flag, true);
        Vector3d at = player.getTransform().getPosition();
        int distance = (int) Math.round(Math.sqrt(village.horizontalDistanceSquared(at.x(), at.z())));
        player.sendMessage(Message.translation(KEYS + "reveal." + people.id()).param("village", village.name())
                .param("x", village.x()).param("z", village.z()).param("distance", distance));
    }
}
