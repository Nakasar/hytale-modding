package dev.nakasar.hytale.fractals.silentsurf;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Carried;
import dev.nakasar.hytale.fractals.arena.Moves;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.combat.Delayed;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;
import org.joml.Vector3i;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/**
 * L'équipement de prospection des Luxons (GW2 : Survey Gear), quatre objets de la barre d'action ; clic droit
 * ({@link SurveyGearInteraction}). Les charges sont le nombre d'objets portés ; les provisions abandonnées des points
 * de contrôle les rendent ({@link #refill}).
 * <ul>
 *   <li>grappin : le crochet file vers la roche visée ({@value #GRAPPLE_RANGE} blocs) et tire le joueur jusqu'à elle,
 *   puis un petit élan pour se hisser sur le rebord ;</li>
 *   <li>parachute : en l'air seulement, descente lente vers où l'on regarde jusqu'au sol (s'accroupir le referme) ;
 *   Hytale n'a pas de planeur pour les joueurs : la vitesse est posée à chaque tick ;</li>
 *   <li>poudre noire : l'explosion projette loin devant et vers le haut, sans dégâts de chute ;</li>
 *   <li>fusée éclairante : illimitée ; elle file droit devant et pose une lueur ({@value #FLARE_SECONDS} s) où elle se
 *   plante.</li>
 * </ul>
 */
final class SurveyGear {

    static final String GRAPPLE = "Nakasar_Fractal_Survey_Grapple";
    static final String PARACHUTE = "Nakasar_Fractal_Survey_Parachute";
    static final String POWDER = "Nakasar_Fractal_Survey_Powder";
    static final String FLARE = "Nakasar_Fractal_Survey_Flare";
    static final String FLARE_LIGHT = "Nakasar_Fractal_Flare_Light";
    static final String[] ITEMS = {GRAPPLE, PARACHUTE, POWDER, FLARE};
    static final int[] MAX = {3, 3, 2, 1};
    static final double GRAPPLE_RANGE = 32;
    static final double GRAPPLE_SPEED = 20;
    static final float GRAPPLE_MAX = 3f;
    static final double GLIDE_SPEED = 5.5;
    static final double GLIDE_FALL = -2.5;
    static final float GLIDE_MAX = 15f;
    static final double POWDER_FORWARD = 12;
    static final double POWDER_UP = 10;
    static final double FLARE_RANGE = 48;
    static final float FLARE_SECONDS = 40f;
    static final float FLARE_COOLDOWN = 1f;

    /** Joueurs sous un grappin ou un parachute en cours (une seule tâche par joueur). */
    private final Set<UUID> busy = new HashSet<>();
    private final Set<UUID> cancelled = new HashSet<>();
    private final Map<UUID, Long> flareReady = new HashMap<>();
    /** Lueurs posées (position du bloc) -> fin ; une nouvelle fusée au même endroit la prolonge. */
    private final Map<Vector3i, Long> lights = new HashMap<>();

    void cancel(UUID player) {
        if (busy.contains(player)) {
            cancelled.add(player);
        }
    }

    /** Toutes les charges ; la poudre noire seulement après le repaire des araignées (Thess la donne là). */
    static void refill(Store<EntityStore> store, Ref<EntityStore> ref, boolean powder) {
        for (int i = 0; i < ITEMS.length; i++) {
            if (ITEMS[i].equals(POWDER) && !powder) {
                continue;
            }
            int missing = MAX[i] - Carried.count(store, ref, ITEMS[i]);
            if (missing > 0) {
                Carried.giveIfRoom(store, ref, ITEMS[i], missing);     // sac plein : rien au sol
            }
        }
    }

    void use(World world, Store<EntityStore> store, SilentSurf.State st, PlayerRef player, String gear) {
        Ref<EntityStore> ref = player.getReference();
        if (ref == null || !ref.isValid() || st.rides.riding(player.getUuid())) {
            return;
        }
        switch (gear) {
            case "Grapple" -> grapple(world, store, st, player, ref);
            case "Parachute" -> parachute(world, store, st, player, ref);
            case "Powder" -> powder(store, st, player, ref);
            case "Flare" -> flare(world, store, player, ref);
            default -> {
            }
        }
    }

    // --- grappin ----------------------------------------------------------------------------------------------

    private void grapple(World world, Store<EntityStore> store, SilentSurf.State st, PlayerRef player, Ref<EntityStore> ref) {
        Vector3d eye = eye(store, ref);
        Vector3d look = Moves.look(store, ref);
        if (eye == null || look == null || busy.contains(player.getUuid())) {
            return;
        }
        Vector3d hit = Moves.cast(world.getChunkStore(), eye, look, GRAPPLE_RANGE);
        if (hit == null) {
            SilentSurf.tell(st, player, "grapple.miss");
            return;
        }
        if (!Carried.takeOne(store, ref, GRAPPLE)) {
            return;
        }
        UUID id = player.getUuid();
        busy.add(id);
        cancelled.remove(id);
        Vector3d anchor = new Vector3d(hit);
        long[] begin = {-1};
        Telegraphs.sound(store, "SFX_Spear_Throw_Charge", eye);
        TelegraphSystem.start(world, (w, s, now) -> {
            if (begin[0] < 0) {
                begin[0] = now;
            }
            Vector3d at = Telegraphs.position(s, ref);
            if (at == null || cancelled.remove(id)) {
                busy.remove(id);
                return true;
            }
            Vector3d feet = new Vector3d(anchor).sub(0, 0.6, 0);
            Vector3d to = new Vector3d(feet).sub(at);
            boolean late = now - begin[0] > Telegraphs.seconds(GRAPPLE_MAX);
            st.safe(id, 2f);
            if (to.length() < 1.4 || late) {
                // arrivé : un petit élan vers l'avant et le haut pour passer le rebord
                Moves.velocity(s, ref, Moves.flatLook(s, ref).mul(4).add(0, 7, 0));
                busy.remove(id);
                return true;
            }
            Moves.velocity(s, ref, to.normalize().mul(GRAPPLE_SPEED));
            Vector3d hand = new Vector3d(at).add(0, 1.2, 0);
            for (int k = 1; k <= 5; k++) {
                Telegraphs.particle(s, "Nakasar_Fractal_Grapple_Line", new Vector3d(hand).lerp(anchor, k / 6.0), 1f);
            }
            return false;
        });
    }

    // --- parachute --------------------------------------------------------------------------------------------

    private void parachute(World world, Store<EntityStore> store, SilentSurf.State st, PlayerRef player, Ref<EntityStore> ref) {
        UUID id = player.getUuid();
        if (busy.contains(id)) {
            return;
        }
        if (Moves.onGround(store, ref)) {
            SilentSurf.tell(st, player, "parachute.ground");
            return;
        }
        if (!Carried.takeOne(store, ref, PARACHUTE)) {
            return;
        }
        busy.add(id);
        cancelled.remove(id);
        long[] begin = {-1};
        int[] tick = {0};
        TelegraphSystem.start(world, (w, s, now) -> {
            if (begin[0] < 0) {
                begin[0] = now;
            }
            Vector3d at = Telegraphs.position(s, ref);
            boolean started = now - begin[0] > Telegraphs.seconds(0.3f);
            if (at == null || cancelled.remove(id) || now - begin[0] > Telegraphs.seconds(GLIDE_MAX)
                    || started && (Moves.onGround(s, ref) || Moves.crouching(s, ref))) {
                Hurt.clear(s, ref, "Nakasar_Fractal_Parachute_Open");
                busy.remove(id);
                st.safe(id, 1f);
                return true;
            }
            st.safe(id, 1.5f);
            Moves.velocity(s, ref, Moves.flatLook(s, ref).mul(GLIDE_SPEED).add(0, GLIDE_FALL, 0));
            if (tick[0]++ % 8 == 0) {
                Hurt.effect(s, ref, "Nakasar_Fractal_Parachute_Open", 1f);
                Telegraphs.particle(s, "Nakasar_Fractal_Parachute", at, 1f);
            }
            return false;
        });
    }

    // --- poudre noire -----------------------------------------------------------------------------------------

    private void powder(Store<EntityStore> store, SilentSurf.State st, PlayerRef player, Ref<EntityStore> ref) {
        if (!Carried.takeOne(store, ref, POWDER)) {
            SilentSurf.tell(st, player, st.cleared[2] ? "gear.empty" : "gear.noPowder");
            return;
        }
        Vector3d at = Telegraphs.position(store, ref);
        cancel(player.getUuid());
        Moves.velocity(store, ref, Moves.flatLook(store, ref).mul(POWDER_FORWARD).add(0, POWDER_UP, 0));
        st.safe(player.getUuid(), 5f);
        if (at != null) {
            Telegraphs.particle(store, "Nakasar_Fractal_Powder_Blast", at, 1f);
            Telegraphs.sound(store, "SFX_Goblin_Feastmaster_Slam", at);
        }
    }

    // --- fusée éclairante -------------------------------------------------------------------------------------

    private void flare(World world, Store<EntityStore> store, PlayerRef player, Ref<EntityStore> ref) {
        long now = System.nanoTime();
        Long ready = flareReady.get(player.getUuid());
        if (ready != null && now < ready) {
            return;
        }
        flareReady.put(player.getUuid(), now + Telegraphs.seconds(FLARE_COOLDOWN));
        Vector3d eye = eye(store, ref);
        Vector3d look = Moves.look(store, ref);
        if (eye == null || look == null) {
            return;
        }
        ChunkStore chunks = world.getChunkStore();
        Vector3d hit = Moves.cast(chunks, eye, look, FLARE_RANGE);
        Vector3d end = hit != null ? hit : new Vector3d(look).mul(FLARE_RANGE).add(eye);
        long[] begin = {-1};
        float flight = (float) Math.max(0.2, eye.distance(end) / 40.0);
        TelegraphSystem.start(world, (w, s, t) -> {
            if (begin[0] < 0) {
                begin[0] = t;
            }
            float f = Math.min(1f, (t - begin[0]) / (float) Telegraphs.seconds(flight));
            Telegraphs.particle(s, "Nakasar_Fractal_Flare_Trail", new Vector3d(eye).lerp(end, f), 1f);
            if (f < 1f) {
                return false;
            }
            Telegraphs.particle(s, "Nakasar_Fractal_Flare_Burst", end, 1f);
            int x = (int) Math.floor(end.x());
            int y = (int) Math.floor(end.y());
            int z = (int) Math.floor(end.z());
            ChunkStore c = w.getChunkStore();
            String there = WorldBlocks.name(c, x, y, z);
            if (hit != null && (there == null || FLARE_LIGHT.equals(there))) {
                Vector3i spot = new Vector3i(x, y, z);
                lights.put(spot, t + Telegraphs.seconds(FLARE_SECONDS));
                if (there == null) {
                    WorldBlocks.set(c, x, y, z, FLARE_LIGHT, 0);
                }
                Delayed.later(w, FLARE_SECONDS, st2 -> {
                    Long until = lights.get(spot);
                    if (until != null && System.nanoTime() >= until - Telegraphs.seconds(0.5f)) {
                        lights.remove(spot);
                        if (FLARE_LIGHT.equals(WorldBlocks.name(w.getChunkStore(), x, y, z))) {
                            WorldBlocks.clear(w.getChunkStore(), x, y, z);
                        }
                    }
                });
            }
            return true;
        });
    }

    // --- outils -----------------------------------------------------------------------------------------------

    private static Vector3d eye(Store<EntityStore> store, Ref<EntityStore> ref) {
        Vector3d at = Telegraphs.position(store, ref);
        return at == null ? null : new Vector3d(at).add(0, 1.6, 0);
    }
}
