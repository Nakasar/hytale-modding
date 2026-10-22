package dev.nakasar.hytale.fractals.snowblind;

import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Carried;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Rencontre 2, la Source élémentaire, d'après GW2 : elle s'éveille quand on entre dans son arène. Cinq foyers
 * l'entourent ; chaque foyer éteint lui donne une pile de bouclier de givre (−{@value #SHIELD_PER_STACK} des dégâts
 * reçus par pile). Un foyer s'allume torche en inventaire (prise au râtelier) puis se nourrit de fagots (tas des
 * huttes) ; il brûle {@value #DRAIN} %/s. Allumé, il réchauffe (Hypothermie).
 * <ul>
 *   <li>à 75, 50 et 25 %, elle frappe les foyers allumés (cercles rouges) : −{@value #STRIKE_LOSS} % de bois chacun ;</li>
 *   <li>tous les foyers éteints : blizzard (le froid monte deux fois plus vite) jusqu'à ce qu'on en rallume un.</li>
 * </ul>
 * Sa vie ne descend pas sous le seuil suivant avant la frappe qui l'attend. Personne de vivant dans l'arène pendant
 * {@value #RESET_SECONDS} s : elle se fige, les foyers s'éteignent.
 */
final class Source {

    enum Outcome { NONE, WON, RESET }

    static final float TORCH_FUEL = 60f;
    static final float WOOD_FUEL = 40f;
    static final float DRAIN = 1f;
    static final float SHIELD_PER_STACK = 0.18f;
    static final float STRIKE_LOSS = 50f;
    static final float STRIKE_WINDUP = 2.5f;
    static final double STRIKE_RADIUS = 2.5;
    static final float STRIKE_PART = 0.2f;
    static final float RESET_SECONDS = 20f;
    static final float[] THRESHOLDS = {0.75f, 0.5f, 0.25f};
    /** Piles de bouclier par Source en vie, pour sa barre de boss. */
    private static final Map<Ref<EntityStore>, Integer> SHIELDS = new ConcurrentHashMap<>();

    private Ref<EntityStore> boss;
    private final float[] fuel = new float[SnowblindLayout.BRAZIERS.length];
    private boolean engaged;
    private volatile boolean dead;
    private boolean blizzard;
    private int stage;
    private float idle;
    private float pulseClock;

    static String label(Ref<EntityStore> ref) {
        Integer stacks = SHIELDS.get(ref);
        return stacks == null || stacks <= 0 ? null : "❄".repeat(stacks);
    }

    static void forgetAll() {
        SHIELDS.clear();
    }

    void down() {
        dead = true;
    }

    boolean blizzard() {
        return blizzard;
    }

    int lit() {
        int n = 0;
        for (float f : fuel) {
            if (f > 0f) {
                n++;
            }
        }
        return n;
    }

    /** Foyers allumés, sources de chaleur. */
    void heats(List<Frost.Heat> out) {
        int[][] braziers = SnowblindLayout.BRAZIERS;
        for (int i = 0; i < braziers.length; i++) {
            if (fuel[i] > 0f) {
                out.add(new Frost.Heat(center(i), SnowblindLayout.BRAZIER_HEAT));
            }
        }
    }

    private static Vector3d center(int i) {
        int[] b = SnowblindLayout.BRAZIERS[i];
        return new Vector3d(b[0] + 0.5, b[1], b[2] + 0.5);
    }

    private static int index(int x, int z) {
        int[][] braziers = SnowblindLayout.BRAZIERS;
        for (int i = 0; i < braziers.length; i++) {
            if (braziers[i][0] == x && braziers[i][2] == z) {
                return i;
            }
        }
        return -1;
    }

    // --- foyers ---------------------------------------------------------------------------------------------

    /** Un joueur utilise un foyer de l'arène : l'allumer (torche) ou le nourrir (fagot). */
    void use(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Snowblind.State st, int x, int z) {
        int i = index(x, z);
        if (i < 0) {
            return;
        }
        if (fuel[i] <= 0f) {
            if (Carried.count(store, ref, Snowblind.TORCH) <= 0) {
                Snowblind.tell(st, player, "brazier.need");
                return;
            }
            fuel[i] = TORCH_FUEL;
            set(world, i, true);
            Telegraphs.particle(store, "Effect_Fire", center(i), 1.2f);
            Spawns.tellAll(world, Message.translation(Snowblind.MESSAGES + "brazier.lit").param("count", lit()));
            return;
        }
        if (fuel[i] > 100f - WOOD_FUEL / 2) {
            Snowblind.tell(st, player, "brazier.full");
            return;
        }
        if (!Carried.takeOne(store, ref, Snowblind.FIREWOOD)) {
            Snowblind.tell(st, player, "brazier.wood");
            return;
        }
        fuel[i] = Math.min(100f, fuel[i] + WOOD_FUEL);
        Telegraphs.particle(store, "Effect_Fire", center(i), 1.2f);
        player.sendMessage(Message.translation(Snowblind.MESSAGES + "brazier.fed").param("fuel", Math.round(fuel[i])));
    }

    private static void set(World world, int i, boolean lit) {
        int[] b = SnowblindLayout.BRAZIERS[i];
        WorldBlocks.swap(world.getChunkStore(), b[0], b[1], b[2], lit ? Snowblind.BRAZIER : Snowblind.BRAZIER_OUT);
    }

    private void burn(World world, Store<EntityStore> store, int i, float amount) {
        if (fuel[i] <= 0f) {
            return;
        }
        fuel[i] -= amount;
        if (fuel[i] <= 0f) {
            fuel[i] = 0f;
            set(world, i, false);
            Telegraphs.particle(store, "Nakasar_Fractal_Fire_Doused", center(i), 1.2f);
            Spawns.tellAll(world, Message.translation(Snowblind.MESSAGES + "brazier.out").param("count", lit()));
        }
    }

    // --- pas de jeu ---------------------------------------------------------------------------------------

    Outcome step(World world, Store<EntityStore> store, List<PlayerRef> players, float dt) {
        List<PlayerRef> inside = Spawns.in(store, players, SnowblindLayout.SOURCE_ARENA);
        if (!engaged) {
            if (!inside.isEmpty()) {
                engage(world, store);
            }
            return Outcome.NONE;
        }
        if (dead) {
            clear(world, store, false);
            return Outcome.WON;
        }
        if (inside.isEmpty()) {
            return idle(world, store, dt) ? Outcome.RESET : Outcome.NONE;
        }
        idle = 0f;
        for (int i = 0; i < fuel.length; i++) {
            burn(world, store, i, DRAIN * dt);
        }
        boolean now = lit() == 0;
        if (now != blizzard) {
            blizzard = now;
            Spawns.tellAll(world, Message.translation(Snowblind.MESSAGES + (now ? "source.blizzard" : "source.calm")));
        }
        if (boss == null || !boss.isValid()) {
            return Outcome.NONE;
        }
        int stacks = fuel.length - lit();
        SHIELDS.put(boss, stacks);
        pulseClock += dt;
        Vector3d at = Telegraphs.position(store, boss);
        if (pulseClock >= 2.5f && at != null && stacks > 0) {
            pulseClock = 0f;
            Telegraphs.particle(store, "Nakasar_Fractal_Source_Pulse", at, 1f + stacks * 0.3f);
        }
        if (stage < THRESHOLDS.length && Hurt.healthFraction(store, boss) <= THRESHOLDS[stage] + 0.001f) {
            stage++;
            strike(world, store);
        }
        return Outcome.NONE;
    }

    private void engage(World world, Store<EntityStore> store) {
        Vector3d at = Spawns.point(SnowblindLayout.SOURCE);
        boss = Spawns.spawnBoss(world, store, Snowblind.SOURCE, at, Telegraphs.yawToward(at, new Vector3d(at).add(0, 0, 1)));
        Telegraphs.particle(store, "Nakasar_Fractal_Source_Pulse", at, 2.5f);
        engaged = true;
        dead = false;
        stage = 0;
        idle = 0f;
        blizzard = lit() == 0;
        Spawns.tellAll(world, Message.translation(Snowblind.MESSAGES + "source.enter"));
    }

    /** Cercles rouges sur les foyers allumés ; au bout de l'annonce, chacun perd {@value #STRIKE_LOSS} % de bois. */
    private void strike(World world, Store<EntityStore> store) {
        float windup = STRIKE_WINDUP * FractalRuns.windupFactor(world);
        long now = System.nanoTime();
        List<Integer> targets = new ArrayList<>();
        List<Telegraphs.Circle> circles = new ArrayList<>();
        for (int i = 0; i < fuel.length; i++) {
            if (fuel[i] > 0f) {
                targets.add(i);
                circles.add(new Telegraphs.Circle(center(i), STRIKE_RADIUS, now, windup));
            }
        }
        Spawns.tellAll(world, Message.translation(Snowblind.MESSAGES + "source.strike"));
        if (targets.isEmpty()) {
            return;
        }
        TelegraphSystem.start(world, (w, s, t) -> {
            boolean done = true;
            for (Telegraphs.Circle c : circles) {
                done &= c.step(s, t);
            }
            if (!done) {
                return false;
            }
            if (!engaged) {
                return true;
            }
            for (int k = 0; k < targets.size(); k++) {
                Telegraphs.Circle c = circles.get(k);
                Telegraphs.particle(s, "Ice_Blast", c.origin(), 1.2f);
                burn(w, s, targets.get(k), STRIKE_LOSS);
                for (PlayerRef p : Spawns.alivePlayers(w, s)) {
                    Vector3d at = Telegraphs.position(s, p.getReference());
                    if (at != null && c.contains(at)) {
                        Hurt.percent(s, p.getReference(), STRIKE_PART, "Physical");
                    }
                }
            }
            Telegraphs.sound(s, "SFX_Ice_Break", circles.get(0).origin());
            return true;
        });
    }

    /** Bouclier de givre et seuils de vie. */
    void filter(ComponentAccessor<EntityStore> accessor, Ref<EntityStore> victim, Damage damage) {
        if (!engaged || !victim.equals(boss)) {
            return;
        }
        int stacks = fuel.length - lit();
        damage.setAmount(damage.getAmount() * Math.max(0.05f, 1f - SHIELD_PER_STACK * stacks));
        if (stage >= THRESHOLDS.length) {
            return;
        }
        EntityStatMap stats = accessor.getComponent(victim, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        if (health != null) {
            float floor = health.getMax() * THRESHOLDS[stage];
            damage.setAmount(Math.max(0f, Math.min(damage.getAmount(), health.get() - floor)));
        }
    }

    // --- remise à zéro -------------------------------------------------------------------------------------

    boolean idle(World world, Store<EntityStore> store, float dt) {
        if (!engaged) {
            return false;
        }
        idle += dt;
        if (idle < RESET_SECONDS) {
            return false;
        }
        clear(world, store, true);
        Spawns.tellAll(world, Message.translation(Snowblind.MESSAGES + "source.reset"));
        return true;
    }

    /** Retire la Source ; `extinguish` : éteint aussi les foyers (sinon, vaincue, ils restent allumés et ne brûlent plus). */
    private void clear(World world, Store<EntityStore> store, boolean extinguish) {
        if (boss != null) {
            SHIELDS.remove(boss);
        }
        Spawns.remove(store, boss);
        boss = null;
        engaged = false;
        blizzard = false;
        idle = 0f;
        if (!extinguish) {
            return;
        }
        ChunkStore chunks = world.getChunkStore();
        for (int i = 0; i < fuel.length; i++) {
            fuel[i] = 0f;
            int[] b = SnowblindLayout.BRAZIERS[i];
            WorldBlocks.swap(chunks, b[0], b[1], b[2], Snowblind.BRAZIER_OUT);
        }
    }
}
