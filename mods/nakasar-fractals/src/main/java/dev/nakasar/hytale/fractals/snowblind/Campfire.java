package dev.nakasar.hytale.fractals.snowblind;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.fractals.arena.Carried;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Rencontre 1, le mur de glace : le grand feu du camp, allumé et nourri de fagots (pris sous les arbres), fait fondre
 * le mur rangée par rangée, d'autant plus vite qu'il est bien nourri ({@value #MELT_SECONDS} s à mi-bois). Il brûle
 * son bois ({@value #DRAIN} %/s) et s'éteint à vide.
 * <ul>
 *   <li>toutes les {@value #ELEMENTAL_EVERY} s, des élémentaires de glace sortent de la lisière et marchent vers le
 *   feu ; arrivé, chacun lui retire {@value #DOUSE} % de bois et disparaît ;</li>
 *   <li>toutes les {@value #WAVE_EVERY} s, loups ou cultistes attaquent le camp ({@value #WAVE_CAP} vivants au plus).</li>
 * </ul>
 */
final class Campfire {

    static final float FUEL_START = 40f;
    static final float FUEL_FEED = 30f;
    static final float DRAIN = 1.5f;
    static final float MELT_SECONDS = 90f;
    static final float ELEMENTAL_EVERY = 14f;
    static final float WAVE_EVERY = 25f;
    static final int WAVE_CAP = 8;
    static final float DOUSE = 35f;
    static final double REACH = 2.6;

    private boolean lit;
    private boolean started;
    private float fuel;
    private float melt;
    private int rowsGone;
    private float elementalClock;
    private float waveClock;
    private boolean wolves;
    private final List<Ref<EntityStore>> elementals = new ArrayList<>();
    private final List<Ref<EntityStore>> raiders = new ArrayList<>();

    boolean lit() {
        return lit;
    }

    static Vector3d center() {
        int[] b = SnowblindLayout.BONFIRE;
        return new Vector3d(b[0] + 0.5, b[1], b[2] + 0.5);
    }

    /** Un joueur utilise le grand feu : l'allumer ou le nourrir d'un fagot. */
    void use(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Snowblind.State st) {
        if (lit && fuel > 100f - FUEL_FEED / 2) {
            Snowblind.tell(st, player, "fire.full");
            return;
        }
        if (!Carried.takeOne(store, ref, Snowblind.FIREWOOD)) {
            Snowblind.tell(st, player, "fire.need");
            return;
        }
        Vector3d at = center();
        Telegraphs.particle(store, "Effect_Fire", at, 1.5f);
        if (!lit) {
            lit = true;
            fuel = FUEL_START;
            set(world, Snowblind.BONFIRE);
            if (!started) {
                started = true;
                elementalClock = ELEMENTAL_EVERY - 6f;
                waveClock = WAVE_EVERY - 10f;
            }
            Spawns.tellAll(world, Message.translation(Snowblind.MESSAGES + "fire.lit"));
            return;
        }
        fuel = Math.min(100f, fuel + FUEL_FEED);
        player.sendMessage(Message.translation(Snowblind.MESSAGES + "fire.fed").param("fuel", Math.round(fuel)));
    }

    /** Vrai une fois le mur fondu. */
    boolean step(World world, Store<EntityStore> store, float dt) {
        if (lit) {
            fuel -= DRAIN * dt;
            melt += dt / MELT_SECONDS * (0.5f + fuel / 100f);
            if (fuel <= 0f) {
                extinguish(world);
            }
            meltRows(world, store);
        }
        if (rowsGone >= SnowblindLayout.ICE_WALL.length) {
            Spawns.removeAll(store, elementals);
            elementals.clear();
            raiders.clear();
            return true;
        }
        if (started) {
            elementals(world, store, dt);
            raiders(world, store, dt);
        }
        return false;
    }

    private void extinguish(World world) {
        lit = false;
        fuel = 0f;
        set(world, Snowblind.BONFIRE_OUT);
        Spawns.tellAll(world, Message.translation(Snowblind.MESSAGES + "fire.out"));
    }

    private void meltRows(World world, Store<EntityStore> store) {
        int[][][] rows = SnowblindLayout.ICE_WALL;
        int target = Math.min(rows.length, (int) Math.floor(melt * rows.length));
        ChunkStore chunks = world.getChunkStore();
        while (rowsGone < target) {
            for (int[] c : rows[rowsGone]) {
                WorldBlocks.clear(chunks, c[0], c[1], c[2]);
            }
            int[] mid = rows[rowsGone][rows[rowsGone].length / 2];
            Telegraphs.particle(store, "Nakasar_Fractal_Ice_Melt", new Vector3d(mid[0] + 0.5, mid[1], mid[2] + 0.5), 2f);
            rowsGone++;
        }
        if (rowsGone >= rows.length) {
            Spawns.tellAll(world, Message.translation(Snowblind.MESSAGES + "wall.melted"));
        }
    }

    private static void set(World world, String block) {
        int[] b = SnowblindLayout.BONFIRE;
        WorldBlocks.set(world.getChunkStore(), b[0], b[1], b[2], block, 0);
    }

    // --- élémentaires -----------------------------------------------------------------------------------

    private void elementals(World world, Store<EntityStore> store, float dt) {
        Vector3d fire = center();
        elementals.removeIf(ref -> {
            if (!Spawns.alive(store, ref)) {
                return true;
            }
            Vector3d at = Telegraphs.position(store, ref);
            if (at == null || Telegraphs.horizontal(at, fire) > REACH) {
                return false;
            }
            Telegraphs.particle(store, "Nakasar_Fractal_Fire_Doused", fire, 1.5f);
            Spawns.remove(store, ref);
            if (lit) {
                fuel -= DOUSE;
                Spawns.tellAll(world, Message.translation(Snowblind.MESSAGES + "fire.doused"));
                if (fuel <= 0f) {
                    extinguish(world);
                }
            }
            return true;
        });
        elementalClock += dt;
        if (elementalClock < ELEMENTAL_EVERY) {
            return;
        }
        elementalClock = 0f;
        int count = 1 + FractalRuns.partySize(world) / 2;
        double[][] spawns = SnowblindLayout.ELEMENTAL_SPAWNS;
        int first = ThreadLocalRandom.current().nextInt(spawns.length);
        for (int i = 0; i < count; i++) {
            double[] p = spawns[(first + i * 2) % spawns.length];
            Vector3d at = Spawns.point(p);
            Ref<EntityStore> ref = Spawns.spawnFoe(world, store, Snowblind.ELEMENTAL, at, Telegraphs.yawToward(at, fire));
            if (ref == null) {
                continue;
            }
            NPCEntity npc = store.getComponent(ref, NPCEntity.getComponentType());
            if (npc != null) {
                npc.setLeashPoint(fire);
            }
            Telegraphs.particle(store, "Effect_Snow", at, 1.5f);
            elementals.add(ref);
        }
        Spawns.tellAll(world, Message.translation(Snowblind.MESSAGES + "fire.elementals"));
    }

    // --- vagues -------------------------------------------------------------------------------------------

    private void raiders(World world, Store<EntityStore> store, float dt) {
        raiders.removeIf(ref -> !Spawns.alive(store, ref));
        waveClock += dt;
        if (waveClock < WAVE_EVERY) {
            return;
        }
        waveClock = 0f;
        int count = Math.min(WAVE_CAP - raiders.size(), 2 + FractalRuns.partySize(world) / 2);
        if (count <= 0) {
            return;
        }
        wolves = !wolves;
        double[][] spawns = SnowblindLayout.WAVE_SPAWNS;
        double[] p = spawns[ThreadLocalRandom.current().nextInt(spawns.length)];
        for (int i = 0; i < count; i++) {
            Vector3d at = Spawns.point(p).add((i % 2) * 1.5 - 0.75, 0, (i / 2) * 1.5 - 0.75);
            String role = wolves ? Snowblind.WOLF : i == 0 ? Snowblind.ICE_CASTER : Snowblind.CULTIST;
            Ref<EntityStore> ref = Spawns.spawnFoe(world, store, role, at, Telegraphs.yawToward(at, center()));
            if (ref != null) {
                raiders.add(ref);
            }
        }
        Spawns.tellAll(world, Message.translation(Snowblind.MESSAGES + "fire.wave"));
    }
}
