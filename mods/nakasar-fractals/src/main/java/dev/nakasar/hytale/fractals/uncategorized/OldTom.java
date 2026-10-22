package dev.nakasar.hytale.fractals.uncategorized;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Box;
import dev.nakasar.hytale.fractals.arena.Carried;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

import java.util.List;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Vieux Tom, boss de l'Inclassable. Son IA (JSON) frappe, sème la rafale, attire et lance l'éclair qui rebondit ; le
 * Java mène la salle :
 * <ul>
 *   <li>le gaz : toutes les {@value #CYCLE} s, alerte à {@value #WARNING} s, puis il monte à {@value #RISE} s et
 *   retire {@value #GAS_PART} des PV max par seconde à toute la salle jusqu'à ce qu'on allume le ventilateur ;</li>
 *   <li>dès le niveau {@value #BATTERY_LEVEL}, le ventilateur exige ses deux batteries chargées : deux larmes de Brume
 *   tombent dans la salle à chaque cycle, on les verse dans les batteries (vidées après chaque évacuation) ;</li>
 *   <li>personne dans la salle pendant {@value #RESET_SECONDS} s : Tom revient, vie pleine.</li>
 * </ul>
 */
final class OldTom {

    static final float CYCLE = 40f;
    static final float WARNING = 28f;
    static final float RISE = 34f;
    static final float GAS_PART = 0.05f;
    static final int BATTERY_LEVEL = 12;
    static final float RESET_SECONDS = 20f;
    static final String GAS_CAUSE = "Nakasar_Fractal_Gas";
    static final String BATTERY = "Nakasar_Fractal_Battery";
    static final String BATTERY_ON = "Nakasar_Fractal_Battery_Charged";

    Ref<EntityStore> ref;
    volatile boolean down;
    private boolean engaged;
    private boolean warned;
    private boolean gas;
    private float clock;
    private float tick;
    private float idle;
    private int charged;

    /** Un pas de jeu ; vrai quand Tom est vaincu (une seule fois). */
    boolean step(World world, Store<EntityStore> store, Uncategorized.State st, List<PlayerRef> players, float dt) {
        if (down) {
            finish(world, store);
            return true;
        }
        if (ref == null || !ref.isValid()) {
            double[] at = UncategorizedLayout.TOM;
            ref = Spawns.spawnBoss(world, store, Uncategorized.TOM, Spawns.point(at), 0f);
            if (ref == null) {
                return false;
            }
        }
        List<PlayerRef> inRoom = Spawns.in(store, players, UncategorizedLayout.ROOM);
        if (inRoom.isEmpty()) {
            idle(world, store, st, dt);
            return false;
        }
        idle = 0f;
        if (!engaged) {
            engaged = true;
            Spawns.tellAll(world, Message.translation(Uncategorized.MESSAGES + "tom.enter"));
            if (needsBatteries(world)) {
                Spawns.tellAll(world, Message.translation(Uncategorized.MESSAGES + "tom.batteries"));
            }
            newCycle(world, store);
        }
        clock += dt;
        Vector3d vent = Spawns.point(UncategorizedLayout.VENT);
        if (!warned && clock >= WARNING) {
            warned = true;
            Spawns.tellAll(world, Message.translation(Uncategorized.MESSAGES + "gas.warning"));
        }
        if (warned && !gas) {
            Telegraphs.particle(store, "Nakasar_Fractal_Gas_Warning", vent, 1.5f);
        }
        if (!gas && clock >= RISE) {
            gas = true;
            Spawns.tellAll(world, Message.translation(Uncategorized.MESSAGES + "gas.rising"));
        }
        tick += dt;
        if (gas && tick >= 1f) {
            tick = 0f;
            Box room = UncategorizedLayout.ROOM;
            ThreadLocalRandom random = ThreadLocalRandom.current();
            for (int k = 0; k < 3; k++) {
                Telegraphs.particle(store, "Nakasar_Fractal_Gas", new Vector3d(random.nextDouble(room.x0(), room.x1()),
                        room.y0() + 1, random.nextDouble(room.z0(), room.z1())), 2.5f);
            }
            for (PlayerRef player : inRoom) {
                Hurt.percent(store, player.getReference(), GAS_PART, GAS_CAUSE);
            }
        }
        return false;
    }

    private boolean needsBatteries(World world) {
        return FractalRuns.level(world) >= BATTERY_LEVEL;
    }

    /** Nouveau cycle de gaz : horloge à zéro, larmes de Brume dans la salle si les batteries comptent. */
    private void newCycle(World world, Store<EntityStore> store) {
        clock = 0f;
        warned = false;
        gas = false;
        if (!needsBatteries(world)) {
            return;
        }
        Box room = UncategorizedLayout.ROOM;
        ThreadLocalRandom random = ThreadLocalRandom.current();
        for (int k = 0; k < 2; k++) {
            Vector3d at = new Vector3d(random.nextDouble(room.x0() + 2, room.x1() - 1), room.y0() + 1,
                    random.nextDouble(room.z0() + 2, room.z1() - 1));
            Carried.drop(store, Uncategorized.TEAR, at);
            Telegraphs.particle(store, "Nakasar_Fractal_Tear_Glint", at, 1f);
        }
        Spawns.tellAll(world, Message.translation(Uncategorized.MESSAGES + "tear.drop"));
    }

    /** Ventilateur : évacue le gaz (batteries chargées dès le niveau 12) et relance le cycle. */
    void useFan(World world, Store<EntityStore> store, Uncategorized.State st, PlayerRef player) {
        if (st.step != Uncategorized.Step.TOM || !engaged) {
            return;
        }
        if (!warned) {
            Uncategorized.tell(st, player, "gas.calm");
            return;
        }
        if (needsBatteries(world) && charged < UncategorizedLayout.BATTERIES.length) {
            Uncategorized.tell(st, player, "fan.batteries");
            return;
        }
        Vector3d vent = Spawns.point(UncategorizedLayout.VENT);
        Telegraphs.particle(store, "Nakasar_Fractal_Fan_Gust", vent, 2f);
        Telegraphs.particle(store, "Nakasar_Fractal_Fan_Gust", Spawns.point(UncategorizedLayout.ROOM_CENTER), 2.5f);
        Telegraphs.sound(store, "SFX_Spirit_Root_Spawn", vent);
        Spawns.tellAll(world, Message.translation(Uncategorized.MESSAGES + "gas.vented"));
        emptyBatteries(world);
        newCycle(world, store);
    }

    /** Batterie : y verser une larme de Brume. */
    void useBattery(World world, Store<EntityStore> store, Uncategorized.State st, Ref<EntityStore> ref, PlayerRef player,
                    int x, int y, int z) {
        if (st.step != Uncategorized.Step.TOM) {
            return;
        }
        ChunkStore chunks = world.getChunkStore();
        if (BATTERY_ON.equals(WorldBlocks.name(chunks, x, y, z))) {
            Uncategorized.tell(st, player, "battery.full");
            return;
        }
        if (!Carried.takeOne(store, ref, Uncategorized.TEAR)) {
            Uncategorized.tell(st, player, "battery.needTear");
            return;
        }
        WorldBlocks.swap(chunks, x, y, z, BATTERY_ON);
        charged++;
        Telegraphs.particle(store, "Nakasar_Fractal_Battery_Charge", new Vector3d(x + 0.5, y + 1, z + 0.5), 1f);
        Spawns.tellAll(world, Message.translation(Uncategorized.MESSAGES + "battery.charged").param("count", charged));
    }

    private void emptyBatteries(World world) {
        ChunkStore chunks = world.getChunkStore();
        for (int[] b : UncategorizedLayout.BATTERIES) {
            WorldBlocks.swap(chunks, b[0], b[1], b[2], BATTERY);
        }
        charged = 0;
    }

    /** Personne dans la salle : au bout de {@value #RESET_SECONDS} s, le combat repart de zéro. */
    void idle(World world, Store<EntityStore> store, Uncategorized.State st, float dt) {
        if (!engaged || down) {
            return;
        }
        idle += dt;
        if (idle < RESET_SECONDS) {
            return;
        }
        engaged = false;
        idle = 0f;
        Spawns.remove(store, ref);
        ref = null;
        emptyBatteries(world);
        clock = 0f;
        warned = gas = false;
        Spawns.tellAll(world, Message.translation(Uncategorized.MESSAGES + "tom.reset"));
    }

    /** Victoire : batteries vidées, larmes reprises (elles ne servent qu'ici). */
    private void finish(World world, Store<EntityStore> store) {
        emptyBatteries(world);
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> r = player.getReference();
            if (r != null && r.isValid()) {
                Carried.removeAll(store, r, Uncategorized.TEAR);
            }
        }
    }
}
