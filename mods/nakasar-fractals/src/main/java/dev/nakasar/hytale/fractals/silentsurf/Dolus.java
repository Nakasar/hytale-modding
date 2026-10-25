package dev.nakasar.hytale.fractals.silentsurf;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Leash;
import dev.nakasar.hytale.fractals.combat.BossStun;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

/**
 * Le second Dolus corrompu, au quatrième point de contrôle, après ses marins (GW2) : coups de hache (rôle JSON), et
 * en Java le Visage de l'effroi toutes les {@value #DREAD_EVERY} s et la Vitesse effrayante toutes les
 * {@value #SPEED_EVERY} s, sur la plate-forme ({@link Nightmare}).
 */
final class Dolus {

    static final float DREAD_EVERY = 18f;
    static final float SPEED_EVERY = 27f;
    static final double SPEED_RADIUS = 9;
    static final float RETRY = 5f;

    private Ref<EntityStore> boss;
    private Vector3d home;
    private float dreadClock;
    private float speedClock;
    private boolean dashing;
    private volatile boolean dead;
    private long retryAt;

    boolean engaged() {
        return boss != null;
    }

    void down() {
        dead = true;
    }

    /** Apparition de Dolus ; si elle échoue, nouvel essai {@value #RETRY} s plus tard, sans rien annoncer. */
    void engage(World world, Store<EntityStore> store) {
        long now = System.nanoTime();
        if (now < retryAt) {
            return;
        }
        Vector3d c = Spawns.point(SilentSurfLayout.RINGS[4]);
        Vector3d at = new Vector3d(c).add(3, 0, 3);
        boss = Spawns.spawnBoss(world, store, SilentSurf.DOLUS, at, Telegraphs.yawToward(at, c));
        home = at;
        if (boss == null) {
            retryAt = now + Telegraphs.seconds(RETRY);
            return;
        }
        dead = false;
        dashing = false;
        dreadClock = 8f;
        speedClock = 0f;
        Telegraphs.particle(store, "Nakasar_Fractal_Aspect_Rise", at, 1.5f);
        Spawns.tellAll(world, Message.translation(SilentSurf.MESSAGES + "cp4.dolus"));
    }

    /** Vrai quand Dolus est tombé. */
    boolean step(World world, Store<EntityStore> store, float dt) {
        if (boss == null) {
            return false;
        }
        if (dead || !Spawns.alive(store, boss)) {
            BossStun.release(store, boss);
            boss = null;
            return true;
        }
        Leash.keepAbove(store, boss, home, SilentSurf.FALL_LIMIT);
        if (dashing || BossStun.isStunned(boss)) {
            return false;
        }
        dreadClock += dt;
        speedClock += dt;
        if (speedClock >= SPEED_EVERY) {
            speedClock = 0f;
            dreadClock = Math.min(dreadClock, DREAD_EVERY - 6f);
            dashing = true;
            Nightmare.speed(world, store, boss, name(), Spawns.point(SilentSurfLayout.RINGS[4]), SPEED_RADIUS,
                    () -> dashing = false);
        } else if (dreadClock >= DREAD_EVERY) {
            dreadClock = 0f;
            Nightmare.dread(world, store, boss, name());
        }
        return false;
    }

    static String name() {
        return SilentSurf.MESSAGES + "npc.First_Mate_Dolus.name";
    }
}
