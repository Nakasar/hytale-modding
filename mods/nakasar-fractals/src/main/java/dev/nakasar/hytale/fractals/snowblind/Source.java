package dev.nakasar.hytale.fractals.snowblind;

import com.hypixel.hytale.builtin.weather.resources.WeatherResource;
import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.modules.physics.component.Velocity;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Carried;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.combat.Delayed;
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
import java.util.concurrent.ThreadLocalRandom;

/**
 * Rencontre 2, la Source élémentaire, d'après GW2 : elle s'éveille quand on entre dans son arène. Cinq foyers
 * l'entourent ; chaque foyer éteint lui donne une pile de bouclier de givre (−{@value #SHIELD_PER_STACK} des dégâts
 * reçus par pile). Un foyer s'allume torche en inventaire (prise au râtelier) puis se nourrit de fagots (tas des
 * huttes) ; il brûle {@value #DRAIN} %/s. Allumé, il réchauffe (Hypothermie).
 * <ul>
 *   <li>à 75, 50 et 25 %, elle frappe les foyers allumés (cercles rouges) : −{@value #STRIKE_LOSS} % de bois chacun ;</li>
 *   <li>tous les foyers éteints : blizzard jusqu'à ce qu'on en rallume un (Kevin, 25 octobre 2026). Le temps du monde
 *   passe au blizzard (brume blanche à quelques blocs), le froid monte deux fois plus vite et, au bout de
 *   {@value #SCATTER_AFTER} s puis toutes les {@value #SCATTER_EVERY} s, la tempête jette chaque joueur de l'arène
 *   ailleurs dans le camp.</li>
 * </ul>
 * Sa barre de boss montre ses piles de bouclier et le bois de chaque foyer.
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
    static final float SCATTER_AFTER = 4f;
    static final float SCATTER_EVERY = 9f;
    static final double SCATTER_MIN = 8;
    static final double ANCHOR_SLACK = 0.25;
    /**
     * Lances de glace (Kevin, 25 octobre 2026) : toutes les {@value #LANCE_EVERY} s, une projection de glace en ligne
     * droite vers un joueur de l'arène (un de plus par tranche de deux joueurs, {@value #LANCE_MAX} au plus), annoncée
     * par une bande rouge au sol de la taille exacte du coup ({@value #LANCE_LENGTH} × {@value #LANCE_WIDTH} blocs).
     */
    static final float LANCE_EVERY = 9f;
    static final float LANCE_FIRST = 5f;
    static final float LANCE_WINDUP = 1.8f;
    static final double LANCE_LENGTH = 16;
    static final double LANCE_WIDTH = 2;
    static final float LANCE_PART = 0.18f;
    static final int LANCE_MAX = 3;
    /** Libellé de la barre de boss de chaque Source en vie : piles de bouclier et bois des foyers. */
    private static final Map<Ref<EntityStore>, String> LABELS = new ConcurrentHashMap<>();

    private Ref<EntityStore> boss;
    private final float[] fuel = new float[SnowblindLayout.BRAZIERS.length];
    private boolean engaged;
    private volatile boolean dead;
    private boolean blizzard;
    /** Un foyer a-t-il brûlé depuis l'engagement ? Le blizzard ne se lève que quand le dernier feu allumé meurt. */
    private boolean kindled;
    private String label;
    private int labelKey = -1;
    private int stage;
    private float idle;
    private float pulseClock;
    private float scatterClock;
    private float lanceClock;
    /** Plus bas niveau de vie atteint : la Source ne remonte jamais au-dessus (pas de régénération). */
    private float lowest = -1f;

    static String label(Ref<EntityStore> ref) {
        return LABELS.get(ref);
    }

    static void forgetAll() {
        LABELS.clear();
    }

    /** « ❄❄ | 62 % · 40 % · 0 % · 0 % · 15 % » : bouclier, puis le bois de chaque foyer (leurs barres de vie). */
    private String describe(int stacks) {
        StringBuilder out = new StringBuilder();
        if (stacks > 0) {
            out.append("❄".repeat(stacks)).append(" | ");
        }
        for (int i = 0; i < fuel.length; i++) {
            out.append(i == 0 ? "" : " · ").append(Math.round(fuel[i])).append(" %");
        }
        return out.toString();
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

    Outcome step(World world, Store<EntityStore> store, List<PlayerRef> players, Frost frost, float dt) {
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
            if (blizzard) {
                // le temps est celui de tout le monde : personne dans l'arène, la tempête retombe
                blizzard = false;
                weather(store, false);
            }
            return idle(world, store, dt) ? Outcome.RESET : Outcome.NONE;
        }
        idle = 0f;
        for (int i = 0; i < fuel.length; i++) {
            burn(world, store, i, DRAIN * dt);
        }
        if (lit() > 0) {
            kindled = true;
        }
        boolean now = kindled && lit() == 0;
        if (now != blizzard) {
            blizzard = now;
            scatterClock = SCATTER_EVERY - SCATTER_AFTER;
            weather(store, now);
            Spawns.tellAll(world, Message.translation(Snowblind.MESSAGES + (now ? "source.blizzard" : "source.calm")));
        }
        if (blizzard) {
            scatterClock += dt;
            if (scatterClock >= SCATTER_EVERY) {
                scatterClock = 0f;
                scatter(world, store, inside, frost);
            }
        }
        if (boss == null || !boss.isValid()) {
            return Outcome.NONE;
        }
        anchor(store);
        keepHealth(store);
        int stacks = fuel.length - lit();
        int key = stacks;
        for (float f : fuel) {
            key = key * 101 + Math.round(f);
        }
        if (key != labelKey || label == null) {
            labelKey = key;
            label = describe(stacks);
            LABELS.put(boss, label);
        }
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
        lanceClock += dt;
        if (lanceClock >= LANCE_EVERY && at != null) {
            lanceClock = 0f;
            lances(world, store, new Vector3d(at), inside);
        }
        return Outcome.NONE;
    }

    private void engage(World world, Store<EntityStore> store) {
        Vector3d at = Spawns.point(SnowblindLayout.SOURCE);
        boss = Spawns.spawnBoss(world, store, Snowblind.SOURCE, at, Telegraphs.yawToward(at, new Vector3d(at).add(0, 0, -1)));
        Telegraphs.particle(store, "Nakasar_Fractal_Source_Pulse", at, 2.5f);
        engaged = true;
        dead = false;
        stage = 0;
        idle = 0f;
        blizzard = false;
        lowest = -1f;
        kindled = lit() > 0;
        labelKey = -1;
        scatterClock = SCATTER_EVERY - SCATTER_AFTER;
        lanceClock = LANCE_EVERY - LANCE_FIRST;
        weather(store, false);
        Spawns.tellAll(world, Message.translation(Snowblind.MESSAGES + "source.enter"));
    }

    /**
     * La Source ne bouge pas (Kevin, 25 octobre 2026) : poussée, tirée ou projetée, elle est remise à sa place aussitôt,
     * avec son orientation. {@code KnockbackScale} 0 du rôle ne couvre que le recul des coups ; {@code Frozen} couperait
     * ses attaques. Même ancrage que les tentacules de l'Océan solide.
     */
    private void anchor(Store<EntityStore> store) {
        TransformComponent transform = store.getComponent(boss, TransformComponent.getComponentType());
        if (transform == null || store.getComponent(boss, Teleport.getComponentType()) != null) {
            return;
        }
        Velocity velocity = store.getComponent(boss, Velocity.getComponentType());
        if (velocity != null) {
            velocity.setZero();
        }
        Vector3d home = Spawns.point(SnowblindLayout.SOURCE);
        Vector3d at = transform.getPosition();
        if (Telegraphs.horizontal(at, home) > ANCHOR_SLACK || Math.abs(at.y() - home.y()) > 1.0) {
            store.putComponent(boss, Teleport.getComponentType(),
                    new Teleport(home, new Rotation3f(0f, transform.getRotation().yaw(), 0f)));
        }
    }

    /** Sa vie ne remonte jamais au-dessus du plus bas atteint ; seule la remise à zéro la rend pleine (nouvelle Source). */
    private void keepHealth(Store<EntityStore> store) {
        EntityStatMap stats = store.getComponent(boss, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        if (health == null) {
            return;
        }
        if (lowest < 0f || health.get() < lowest) {
            lowest = health.get();
        } else if (health.get() > lowest) {
            stats.setStatValue(DefaultEntityStatTypes.getHealth(), lowest);
        }
    }

    /** Temps du monde : blizzard (brume blanche à quelques blocs) ou nuit ordinaire de la fractale. */
    private static void weather(Store<EntityStore> store, boolean blizzard) {
        WeatherResource weather = store.getResource(WeatherResource.getResourceType());
        if (weather != null) {
            weather.setForcedWeather(blizzard ? Snowblind.BLIZZARD_WEATHER : Snowblind.WEATHER);
        }
    }

    /** La tempête jette chaque joueur de l'arène sur une tache de neige tirée au hasard, à {@value #SCATTER_MIN} blocs
     * au moins de là où il était. */
    private static void scatter(World world, Store<EntityStore> store, List<PlayerRef> inside, Frost frost) {
        double[][] spots = SnowblindLayout.BLIZZARD_SPOTS;
        ThreadLocalRandom random = ThreadLocalRandom.current();
        for (PlayerRef p : inside) {
            if (frost.encased(p)) {
                continue;               // pris dans la glace : il reste avec son éclat
            }
            Ref<EntityStore> ref = p.getReference();
            Vector3d from = Telegraphs.position(store, ref);
            if (from == null) {
                continue;
            }
            Vector3d to = null;
            for (int tries = 0; tries < 12 && to == null; tries++) {
                Vector3d spot = Spawns.point(spots[random.nextInt(spots.length)]);
                if (Telegraphs.horizontal(spot, from) >= SCATTER_MIN) {
                    to = spot;
                }
            }
            if (to == null) {
                continue;
            }
            Telegraphs.particle(store, "Nakasar_Fractal_Blizzard", new Vector3d(from).add(0, 1, 0), 1.5f);
            store.putComponent(ref, Teleport.getComponentType(),
                    Teleport.createForPlayer(to, new Rotation3f(0f, (float) random.nextDouble(-Math.PI, Math.PI), 0f)));
            Telegraphs.particle(store, "Nakasar_Fractal_Blizzard", new Vector3d(to).add(0, 1, 0), 1.5f);
            p.sendMessage(Message.translation(Snowblind.MESSAGES + "source.scatter"));
        }
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

    /**
     * Lances de glace : une bande rouge part de la Source vers chaque joueur visé et se remplit ; au bout de l'annonce, la
     * glace jaillit le long de la bande (vague d'éclats) et qui s'y trouve perd {@value #LANCE_PART} de ses PV et est
     * ralenti. La bande ne suit pas le joueur : on s'écarte de côté.
     */
    private void lances(World world, Store<EntityStore> store, Vector3d from, List<PlayerRef> inside) {
        if (inside.isEmpty()) {
            return;
        }
        int n = Math.min(LANCE_MAX, 1 + (inside.size() - 1) / 2);
        float windup = LANCE_WINDUP * FractalRuns.windupFactor(world);
        long now = System.nanoTime();
        Vector3d ground = new Vector3d(from.x(), Spawns.point(SnowblindLayout.SOURCE).y(), from.z());
        List<Telegraphs.Strip> strips = new ArrayList<>();
        for (PlayerRef p : Spawns.pick(inside, n)) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at == null || Telegraphs.horizontal(at, ground) < 0.5) {
                continue;
            }
            strips.add(new Telegraphs.Strip(ground, Telegraphs.angle(ground, at), LANCE_LENGTH, LANCE_WIDTH, now, windup));
        }
        if (strips.isEmpty()) {
            return;
        }
        Telegraphs.sound(store, "SFX_Ice_Break", ground);
        TelegraphSystem.start(world, new TelegraphSystem.Task() {
            @Override
            public boolean step(World w, Store<EntityStore> s, long t) {
                boolean done = true;
                for (Telegraphs.Strip strip : strips) {
                    done &= strip.step(s, t);
                }
                if (!done) {
                    return false;
                }
                if (!engaged) {
                    return true;
                }
                for (Telegraphs.Strip strip : strips) {
                    int k = 0;
                    for (double d = 1; d <= LANCE_LENGTH; d += 2, k++) {
                        Vector3d shard = strip.at(d, 0);
                        Delayed.later(w, 0.04f * k, s2 -> Telegraphs.particle(s2, "Ice_Blast", shard, 0.8f));
                    }
                }
                // Une seule touche par joueur, même au pied de la Source où toutes les bandes se croisent.
                for (PlayerRef p : Spawns.alivePlayers(w, s)) {
                    Vector3d at = Telegraphs.position(s, p.getReference());
                    if (at != null && strips.stream().anyMatch(strip -> strip.contains(at))) {
                        Hurt.percent(s, p.getReference(), LANCE_PART, "Physical");
                        Hurt.effect(s, p.getReference(), "Ability_Frost_Slow", 2f);
                    }
                }
                Telegraphs.sound(s, "SFX_Ice_Break", ground);
                return true;
            }

            @Override
            public Ref<EntityStore> caster() {
                return boss;
            }
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
            LABELS.remove(boss);
        }
        Spawns.remove(store, boss);
        boss = null;
        engaged = false;
        if (blizzard) {
            weather(store, false);
        }
        blizzard = false;
        kindled = false;
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
