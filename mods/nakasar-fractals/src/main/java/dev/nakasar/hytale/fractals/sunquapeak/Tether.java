package dev.nakasar.hytale.fractals.sunquapeak;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Le Marché des marées (GW2 : l'orbe sombre de la Tristesse, puis Ai dans sa phase d'eau). Un rayon relie l'orbe au
 * joueur le plus proche ; chaque seconde, il prend une charge de Marché des marées (plus lent, mais
 * {@value #MIGHT_PERCENT} % de dégâts en plus par charge : {@link SunquaPeak#filter}). À {@value #MAX_STACKS} charges,
 * la marée le submerge : {@value #DROWN_PART} de ses PV, {@value #SPLASH_PART} à qui est à moins de
 * {@value #SPLASH_RADIUS} blocs. Un autre joueur prend le lien en se tenant dans le rayon ({@value #BEAM_WIDTH} bloc
 * de l'axe) ; qui vient de le passer ne peut le reprendre avant {@value #LOCK} s. Les charges d'un joueur sans lien
 * tombent {@value #FADE} s après la dernière.
 */
final class Tether {

    static final int MAX_STACKS = 10;
    static final float MIGHT = 0.05f;
    static final int MIGHT_PERCENT = 5;
    static final float GAIN_EVERY = 1f;
    static final float FADE = 12f;
    static final float DROWN_PART = 0.5f;
    static final float SPLASH_PART = 0.2f;
    static final double SPLASH_RADIUS = 4;
    static final double BEAM_WIDTH = 0.8;
    static final float LOCK = 6f;
    static final float PAUSE = 4f;

    private static final class Stacks {
        int n;
        long last;
    }

    private final Map<UUID, Stacks> stacks = new HashMap<>();
    private final Map<UUID, Long> locked = new HashMap<>();
    private PlayerRef holder;
    private boolean active;
    private float gain;
    private float pause;

    void begin() {
        active = true;
        holder = null;
        gain = 0f;
        pause = 0f;
    }

    boolean active() {
        return active;
    }

    /** Fin du lien : charges et effets retirés. */
    void stop(World world, Store<EntityStore> store) {
        active = false;
        holder = null;
        for (PlayerRef p : Spawns.alivePlayers(world, store)) {
            clearEffects(store, p);
        }
        stacks.clear();
        locked.clear();
    }

    int stacks(UUID player) {
        Stacks s = stacks.get(player);
        return s == null || System.nanoTime() - s.last > Telegraphs.seconds(FADE) ? 0 : s.n;
    }

    /** Charges de Marché des marées du joueur (Tristesse ou Ai). */
    static int stacksOf(SunquaPeak.State st, UUID player) {
        return Math.max(st.sorrow.tether().stacks(player), st.ai.tether().stacks(player));
    }

    void step(World world, Store<EntityStore> store, Vector3d origin, List<PlayerRef> here, float dt) {
        if (!active) {
            return;
        }
        long now = System.nanoTime();
        if (pause > 0f) {
            pause -= dt;
            return;
        }
        holder = holder == null ? null : find(here, holder.getUuid());
        if (holder == null) {
            holder = nearest(store, origin, here);
            if (holder == null) {
                return;
            }
            holder.sendMessage(Message.translation(SunquaPeak.MESSAGES + "sorrow.tether"));
        }
        Vector3d h = Telegraphs.position(store, holder.getReference());
        if (h == null) {
            return;
        }
        Vector3d chest = new Vector3d(h).add(0, 1, 0);
        for (int k = 1; k < 8; k++) {
            double f = k / 8.0;
            Telegraphs.particle(store, "Nakasar_Fractal_Tidal_Beam", new Vector3d(origin).lerp(chest, f), 0.6f);
        }
        // Interception : un autre joueur dans le rayon prend le lien.
        for (PlayerRef p : here) {
            if (p.getUuid().equals(holder.getUuid())) {
                continue;
            }
            Long lock = locked.get(p.getUuid());
            Vector3d at = Telegraphs.position(store, p.getReference());
            if ((lock != null && now < lock) || at == null || Telegraphs.horizontal(at, h) < 1.5) {
                continue;
            }
            if (toSegment(new Vector3d(at).add(0, 1, 0), origin, chest) <= BEAM_WIDTH + Telegraphs.BODY) {
                locked.put(holder.getUuid(), now + Telegraphs.seconds(LOCK));
                holder = p;
                gain = 0f;
                Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "sorrow.taken").param("name", p.getUsername()));
                return;
            }
        }
        gain += dt;
        if (gain < GAIN_EVERY) {
            return;
        }
        gain = 0f;
        Stacks s = stacks.computeIfAbsent(holder.getUuid(), k -> new Stacks());
        if (now - s.last > Telegraphs.seconds(FADE)) {
            s.n = 0;
        }
        s.n++;
        s.last = now;
        if (s.n < MAX_STACKS) {
            clearEffects(store, holder);
            Hurt.effect(store, holder.getReference(), SunquaPeak.TIDAL + s.n, FADE);
            return;
        }
        // La marée submerge le porteur.
        s.n = 0;
        clearEffects(store, holder);
        Hurt.percent(store, holder.getReference(), DROWN_PART, SunquaPeak.CAUSE);
        for (PlayerRef p : here) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (!p.getUuid().equals(holder.getUuid()) && at != null && at.distance(h) <= SPLASH_RADIUS + Telegraphs.BODY) {
                Hurt.percent(store, p.getReference(), SPLASH_PART, SunquaPeak.CAUSE);
            }
        }
        Telegraphs.particle(store, "Nakasar_Fractal_Tide_Burst", h, 1.5f);
        Telegraphs.sound(store, "SFX_Water_MoveIn", h);
        Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "tide.drowned").param("name", holder.getUsername()));
        holder = null;
        pause = PAUSE;
    }

    private static void clearEffects(Store<EntityStore> store, PlayerRef p) {
        for (int n = 1; n <= MAX_STACKS; n++) {
            Hurt.clear(store, p.getReference(), SunquaPeak.TIDAL + n);
        }
    }

    private static PlayerRef find(List<PlayerRef> here, UUID id) {
        for (PlayerRef p : here) {
            if (p.getUuid().equals(id)) {
                return p;
            }
        }
        return null;
    }

    private static PlayerRef nearest(Store<EntityStore> store, Vector3d origin, List<PlayerRef> here) {
        PlayerRef best = null;
        double bestD = Double.MAX_VALUE;
        for (PlayerRef p : here) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at != null && at.distance(origin) < bestD) {
                bestD = at.distance(origin);
                best = p;
            }
        }
        return best;
    }

    /** Distance du point `p` au segment [a, b]. */
    private static double toSegment(Vector3d p, Vector3d a, Vector3d b) {
        Vector3d ab = new Vector3d(b).sub(a);
        double len2 = ab.lengthSquared();
        double t = len2 < 1e-9 ? 0 : Math.max(0, Math.min(1, new Vector3d(p).sub(a).dot(ab) / len2));
        return new Vector3d(a).add(ab.mul(t)).distance(p);
    }
}
