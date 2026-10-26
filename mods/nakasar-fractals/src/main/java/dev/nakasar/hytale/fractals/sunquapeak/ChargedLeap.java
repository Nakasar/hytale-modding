package dev.nakasar.hytale.fractals.sunquapeak;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.entities.player.movement.MovementManager;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Bond chargé (GW2 : Lightning Orbs / Charged Leap). Les orbes de foudre sont des blocs posés par le Java ; on les prend
 * en passant dessus (pas de clic) : une charge de plus ({@value #MAX} au plus), toutes rafraîchies pour
 * {@value #SECONDS} s. L'orbe revient {@value #RESPAWN} s plus tard. Sauter ne consomme pas de charge.
 *
 * <p>Hytale n'a pas d'effet « saut plus haut » : le serveur change la force de saut du joueur
 * ({@code MovementManager.getSettings().jumpForce}, envoyée au client), multipliée par {@link #FACTORS} (la hauteur
 * suit le carré de la force : environ x2, x3,4 et x4,6). Les charges perdues, la force par défaut revient
 * ({@code resetDefaultsAndUpdate}, aussi fait par le jeu à l'entrée dans un autre monde). Sous Bond chargé, et
 * {@value #LANDING} s après, la chute ne blesse pas ({@link SunquaPeak#filter}).
 */
final class ChargedLeap {

    static final String EFFECT = "Nakasar_Fractal_Charged_Leap_";
    static final float[] FACTORS = {1.45f, 1.85f, 2.15f};
    static final int MAX = 3;
    static final float SECONDS = 20f;
    static final float RESPAWN = 8f;
    static final float LANDING = 3f;
    /** On prend une orbe à moins de cette distance (horizontale) de son centre, pieds dans le bloc ou juste dessus. */
    static final double REACH = 0.5 + 0.5 + Telegraphs.BODY;

    private static final class Site {
        final int[] at;
        boolean lit;
        long back;

        Site(int[] at) {
            this.at = at;
        }
    }

    private static final class Charge {
        int stacks;
        long until;
        float applied = 1f;
    }

    private final List<Site> sites = new ArrayList<>();
    private final Map<UUID, Charge> charges = new HashMap<>();

    /** Une orbe en `at` (bloc), allumée tout de suite ou à {@link #light}. */
    void site(World world, int[] at, boolean lit) {
        Site s = new Site(at);
        sites.add(s);
        if (lit) {
            put(world, s);
        }
    }

    /** Allume l'orbe posée en `at` (si elle ne l'est pas déjà). */
    void light(World world, int[] at) {
        for (Site s : sites) {
            if (s.at == at && !s.lit && s.back == 0) {
                put(world, s);
            }
        }
    }

    /** Éteint et oublie les orbes de `points` (fin d'une rencontre). */
    void remove(World world, int[][] points) {
        for (int[] at : points) {
            for (int i = sites.size() - 1; i >= 0; i--) {
                if (sites.get(i).at == at) {
                    WorldBlocks.clear(world.getChunkStore(), at[0], at[1], at[2]);
                    sites.remove(i);
                }
            }
        }
    }

    /** Vrai si le joueur a encore des charges (ou les a perdues il y a moins de {@value #LANDING} s). */
    boolean charged(UUID player) {
        Charge c = charges.get(player);
        return c != null && System.nanoTime() < c.until + Telegraphs.seconds(LANDING);
    }

    int stacks(UUID player) {
        Charge c = charges.get(player);
        return c == null || System.nanoTime() >= c.until ? 0 : c.stacks;
    }

    void step(World world, Store<EntityStore> store, SunquaPeak.State st, List<PlayerRef> players, float dt) {
        long now = System.nanoTime();
        for (Site s : sites) {
            if (!s.lit && s.back != 0 && now >= s.back) {
                put(world, s);
            }
        }
        for (PlayerRef p : players) {
            Ref<EntityStore> ref = p.getReference();
            Vector3d pos = Telegraphs.position(store, ref);
            if (pos == null) {
                continue;
            }
            for (Site s : sites) {
                if (s.lit && Telegraphs.horizontal(pos, new Vector3d(s.at[0] + 0.5, pos.y(), s.at[2] + 0.5)) <= REACH
                        && pos.y() >= s.at[1] - 0.5 && pos.y() <= s.at[1] + 1.5) {
                    take(world, store, p, s, now);
                }
            }
            apply(store, p, now);
        }
    }

    private void put(World world, Site s) {
        WorldBlocks.set(world.getChunkStore(), s.at[0], s.at[1], s.at[2], SunquaPeak.ORB, 0);
        s.lit = true;
        s.back = 0;
    }

    private void take(World world, Store<EntityStore> store, PlayerRef p, Site s, long now) {
        s.lit = false;
        s.back = now + Telegraphs.seconds(RESPAWN);
        WorldBlocks.clear(world.getChunkStore(), s.at[0], s.at[1], s.at[2]);
        Charge c = charges.computeIfAbsent(p.getUuid(), k -> new Charge());
        c.stacks = Math.min(MAX, (now < c.until ? c.stacks : 0) + 1);
        c.until = now + Telegraphs.seconds(SECONDS);
        Ref<EntityStore> ref = p.getReference();
        for (int n = 1; n <= MAX; n++) {
            if (n != c.stacks) {
                Hurt.clear(store, ref, EFFECT + n);
            }
        }
        Hurt.effect(store, ref, EFFECT + c.stacks, SECONDS);
        Vector3d at = new Vector3d(s.at[0] + 0.5, s.at[1] + 0.5, s.at[2] + 0.5);
        Telegraphs.particle(store, "Nakasar_Fractal_Charged_Leap_Spark", at, 1f);
        Telegraphs.sound(store, "SFX_Crystal_Break", at);
        p.sendMessage(Message.translation(SunquaPeak.MESSAGES + "leap.gain").param("stacks", c.stacks));
    }

    /** Force de saut selon les charges ; envoyée au client seulement quand elle change. */
    private void apply(Store<EntityStore> store, PlayerRef p, long now) {
        Charge c = charges.get(p.getUuid());
        if (c == null) {
            return;
        }
        float wanted = now < c.until && c.stacks > 0 ? FACTORS[c.stacks - 1] : 1f;
        Ref<EntityStore> ref = p.getReference();
        MovementManager movement = store.getComponent(ref, MovementManager.getComponentType());
        if (movement == null) {
            return;
        }
        float base = movement.getDefaultSettings() == null ? 0f : movement.getDefaultSettings().jumpForce;
        boolean drifted = wanted != 1f && base > 0f
                && Math.abs(movement.getSettings().jumpForce - base * wanted) > 0.01f;   // un autre système l'a remise
        if (wanted == c.applied && !drifted) {
            if (wanted == 1f && now >= c.until + Telegraphs.seconds(LANDING)) {
                charges.remove(p.getUuid());
            }
            return;
        }
        if (wanted == 1f) {
            movement.resetDefaultsAndUpdate(ref, store);
        } else if (base > 0f) {
            movement.getSettings().jumpForce = base * wanted;
            movement.update(p.getPacketHandler());
        }
        c.applied = wanted;
    }
}
