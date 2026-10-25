package dev.nakasar.hytale.fractals.snowblind;

import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.combat.BossStun;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.defiance.Defiance;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Rencontre 4, le Chaman légendaire, d'après GW2. Il s'éveille quand on entre dans le village, dont la porte se ferme.
 * <ul>
 *   <li>à chaque phase au sol, trois cristaux corrompus l'entourent : tant qu'il en reste un, il ne prend aucun
 *   dégât ;</li>
 *   <li>ses coups d'épée ajoutent {@value #SLASH_STACKS} piles d'hypothermie ({@link Snowblind#filter}) ;</li>
 *   <li>à 75 % et 50 %, il saute sur son balcon, invulnérable, et fait pleuvoir des pics de glace (cercle rouge sous
 *   chaque joueur toutes les {@value #RAIN_EVERY} s : {@value #RAIN_PART} des PV et une pile) ; l'Effigie de glace
 *   apparaît au centre, défiance ouverte : brisée ou détruite, il redescend ;</li>
 *   <li>à 25 %, il prend sa forme d'ours (bonds qui renversent longtemps).</li>
 * </ul>
 * Personne de vivant dans le village pendant {@value #RESET_SECONDS} s : il se retire et la porte se rouvre.
 */
final class Shaman {

    enum Outcome { NONE, WON, RESET }

    static final int SLASH_STACKS = 2;
    static final int CRYSTALS = 3;
    static final double CRYSTAL_RADIUS = 10;
    static final float RAIN_EVERY = 3.5f;
    static final float RAIN_WINDUP = 1.6f;
    static final double RAIN_RADIUS = 2.5;
    static final float RAIN_PART = 0.15f;
    static final float BEAR_AT = 0.25f;
    static final float RESET_SECONDS = 20f;
    static final float[] BALCONY_AT = {0.75f, 0.5f};

    private Ref<EntityStore> boss;
    private Ref<EntityStore> effigy;
    private final List<Ref<EntityStore>> crystals = new ArrayList<>();
    private boolean engaged;
    private boolean shielded;
    private boolean balcony;
    private boolean bear;
    private volatile boolean dead;
    /** Balcons passés (0, 1, 2). */
    private int stage;
    private float rainClock;
    private float idle;

    void down() {
        dead = true;
    }

    boolean engaged() {
        return engaged;
    }

    void engage(World world, Store<EntityStore> store) {
        Vector3d at = Spawns.point(SnowblindLayout.SHAMAN);
        boss = Spawns.spawnBoss(world, store, Snowblind.SHAMAN, at, Telegraphs.yawToward(at, new Vector3d(at).add(1, 0, 0)));
        engaged = true;
        dead = false;
        balcony = false;
        bear = false;
        stage = 0;
        idle = 0f;
        Spawns.tellAll(world, Message.translation(Snowblind.MESSAGES + "shaman.enter"));
        crystals(world, store);
    }

    private void crystals(World world, Store<EntityStore> store) {
        Spawns.removeAll(store, crystals);
        crystals.clear();
        Vector3d c = Spawns.point(SnowblindLayout.VILLAGE_CENTER);
        double start = ThreadLocalRandom.current().nextDouble(0, Math.PI * 2);
        for (int i = 0; i < CRYSTALS; i++) {
            double a = start + i * Math.PI * 2 / CRYSTALS;
            Vector3d at = new Vector3d(c.x() + Math.cos(a) * CRYSTAL_RADIUS, c.y(), c.z() + Math.sin(a) * CRYSTAL_RADIUS);
            Ref<EntityStore> ref = Spawns.spawnFoe(world, store, Snowblind.CRYSTAL, at, 0f);
            if (ref != null) {
                crystals.add(ref);
                Telegraphs.particle(store, "Impact_Ice", at, 1.5f);
            }
        }
        shielded = !crystals.isEmpty();
        Spawns.tellAll(world, Message.translation(Snowblind.MESSAGES + "shaman.crystals"));
    }

    Outcome step(World world, Store<EntityStore> store, Snowblind.State st, List<PlayerRef> players, float dt) {
        if (!engaged) {
            return Outcome.NONE;
        }
        if (dead) {
            clear(store);
            return Outcome.WON;
        }
        List<PlayerRef> inside = Spawns.in(store, players, SnowblindLayout.VILLAGE);
        if (inside.isEmpty()) {
            return idle(world, store, dt) ? Outcome.RESET : Outcome.NONE;
        }
        idle = 0f;
        if (boss == null || !boss.isValid()) {
            return Outcome.NONE;
        }
        crystals.removeIf(ref -> !Spawns.alive(store, ref));
        if (shielded && crystals.isEmpty()) {
            shielded = false;
            Spawns.tellAll(world, Message.translation(Snowblind.MESSAGES + "shaman.exposed"));
        }
        if (balcony) {
            balcony(world, store, st, inside, dt);
            return Outcome.NONE;
        }
        if (bear) {
            return Outcome.NONE;
        }
        float health = Hurt.healthFraction(store, boss);
        if (stage < BALCONY_AT.length && health <= BALCONY_AT[stage] + 0.001f) {
            stage++;
            leap(world, store);
        } else if (stage >= BALCONY_AT.length && health <= BEAR_AT + 0.001f) {
            swap(world, store);
        }
        return Outcome.NONE;
    }

    // --- balcon et Effigie ----------------------------------------------------------------------------------

    private void leap(World world, Store<EntityStore> store) {
        Spawns.removeAll(store, crystals);
        crystals.clear();
        shielded = false;
        Vector3d from = Telegraphs.position(store, boss);
        if (from != null) {
            Telegraphs.particle(store, "Effect_Snow", from, 2f);
        }
        Vector3d top = Spawns.point(SnowblindLayout.BALCONY);
        BossStun.hold(world, store, boss);
        store.ensureAndGetComponent(boss, Invulnerable.getComponentType());
        store.putComponent(boss, Teleport.getComponentType(),
                new Teleport(top, new Rotation3f(0f, Telegraphs.yawToward(top, Spawns.point(SnowblindLayout.VILLAGE_CENTER)), 0f)));
        Vector3d at = Spawns.point(SnowblindLayout.EFFIGY);
        effigy = Spawns.spawnFoe(world, store, Snowblind.EFFIGY, at, Telegraphs.yawToward(at, top));
        if (effigy != null) {
            Defiance.open(world, effigy, 3600f);
            Telegraphs.particle(store, "Impact_Ice", at, 2f);
        }
        balcony = true;
        rainClock = RAIN_EVERY - 1.5f;
        Spawns.tellAll(world, Message.translation(Snowblind.MESSAGES + "shaman.balcony"));
    }

    private void balcony(World world, Store<EntityStore> store, Snowblind.State st, List<PlayerRef> inside, float dt) {
        if (effigy == null || !Spawns.alive(store, effigy) || !Defiance.isOpen(effigy)) {
            descend(world, store);
            return;
        }
        rainClock += dt;
        if (rainClock < RAIN_EVERY) {
            return;
        }
        rainClock = 0f;
        float windup = RAIN_WINDUP * FractalRuns.windupFactor(world);
        long now = System.nanoTime();
        List<Telegraphs.Circle> circles = new ArrayList<>();
        for (PlayerRef p : inside) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at != null) {
                circles.add(new Telegraphs.Circle(at, RAIN_RADIUS, now, windup));
            }
        }
        TelegraphSystem.start(world, (w, s, t) -> {
            boolean done = true;
            for (Telegraphs.Circle c : circles) {
                done &= c.step(s, t);
            }
            if (!done) {
                return false;
            }
            for (Telegraphs.Circle c : circles) {
                Telegraphs.particle(s, "Ability_GroundSlam_Spike", c.origin(), 1f);
                for (PlayerRef p : Spawns.alivePlayers(w, s)) {
                    Vector3d at = Telegraphs.position(s, p.getReference());
                    if (at != null && c.contains(at)) {
                        Hurt.percent(s, p.getReference(), RAIN_PART, "Physical");
                        st.frost.add(p.getUuid(), 1);
                    }
                }
            }
            if (!circles.isEmpty()) {
                Telegraphs.sound(s, "SFX_Ability_Ground_Slam_Spike_Erupt", circles.get(0).origin());
            }
            return true;
        });
    }

    private void descend(World world, Store<EntityStore> store) {
        balcony = false;
        if (effigy != null) {
            Vector3d at = Telegraphs.position(store, effigy);
            if (at != null) {
                Telegraphs.particle(store, "Nakasar_Fractal_Shard_Break", at, 2f);
            }
            Defiance.forget(effigy);
            Spawns.remove(store, effigy);
            effigy = null;
        }
        Vector3d at = Spawns.point(SnowblindLayout.SHAMAN);
        store.tryRemoveComponent(boss, Invulnerable.getComponentType());
        store.putComponent(boss, Teleport.getComponentType(),
                new Teleport(at, new Rotation3f(0f, Telegraphs.yawToward(at, new Vector3d(at).add(1, 0, 0)), 0f)));
        BossStun.release(store, boss);
        Telegraphs.particle(store, "Stick_Slam_Ground_Large", at, 1.2f);
        Spawns.tellAll(world, Message.translation(Snowblind.MESSAGES + "shaman.down"));
        crystals(world, store);
    }

    // --- forme d'ours ---------------------------------------------------------------------------------------

    private void swap(World world, Store<EntityStore> store) {
        Vector3d at = Telegraphs.position(store, boss);
        float fraction = Hurt.healthFraction(store, boss);
        if (at == null) {
            return;
        }
        at = new Vector3d(at);
        Spawns.removeAll(store, crystals);
        crystals.clear();
        shielded = false;
        Spawns.remove(store, boss);
        boss = Spawns.spawnBoss(world, store, Snowblind.BEAR, at, (float) ThreadLocalRandom.current().nextDouble(-Math.PI, Math.PI));
        bear = true;
        EntityStatMap stats = boss == null ? null : store.getComponent(boss, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        if (health != null) {
            stats.setStatValue(DefaultEntityStatTypes.getHealth(), Math.max(1f, health.getMax() * fraction));
        }
        Telegraphs.particle(store, "Effect_Snow", at, 2.5f);
        Spawns.tellAll(world, Message.translation(Snowblind.MESSAGES + "shaman.bear"));
    }

    // --- coups ------------------------------------------------------------------------------------------------

    /** Cristaux debout ou balcon : aucun dégât ; sinon sa vie ne passe pas le seuil suivant avant le balcon ou l'ours. */
    void filter(ComponentAccessor<EntityStore> accessor, Ref<EntityStore> victim, Damage damage) {
        if (!engaged || bear || !victim.equals(boss)) {
            return;
        }
        if (balcony || !crystals.isEmpty()) {
            damage.setCancelled(true);
            return;
        }
        float threshold = stage < BALCONY_AT.length ? BALCONY_AT[stage] : BEAR_AT;
        EntityStatMap stats = accessor.getComponent(victim, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        if (health != null) {
            float floor = health.getMax() * threshold;
            damage.setAmount(Math.max(0f, Math.min(damage.getAmount(), health.get() - floor)));
        }
    }

    // --- remise à zéro -----------------------------------------------------------------------------------------

    boolean idle(World world, Store<EntityStore> store, float dt) {
        if (!engaged) {
            return false;
        }
        idle += dt;
        if (idle < RESET_SECONDS) {
            return false;
        }
        clear(store);
        Spawns.tellAll(world, Message.translation(Snowblind.MESSAGES + "shaman.reset"));
        return true;
    }

    private void clear(Store<EntityStore> store) {
        if (boss != null) {
            BossStun.release(store, boss);
        }
        if (effigy != null) {
            Defiance.forget(effigy);
        }
        Spawns.remove(store, boss);
        Spawns.remove(store, effigy);
        Spawns.removeAll(store, crystals);
        crystals.clear();
        boss = null;
        effigy = null;
        engaged = false;
        balcony = false;
        bear = false;
        shielded = false;
        idle = 0f;
    }
}
