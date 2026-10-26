package dev.nakasar.hytale.fractals.support;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.role.support.MarkedEntitySupport;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

import java.util.HashSet;
import java.util.Set;

/**
 * Leurre des Brumes (rune) : un double immobile du lanceur ({@value #ROLE}, {@value #HP} PV) posé au point visé. Pendant
 * {@value #SECONDS} s, les ennemis ordinaires à {@value #RADIUS} blocs le prennent pour cible ; à sa fin (ou sa mort) ils
 * l'oublient et reprennent la cible que leur IA choisira. Les boss, élites et PNJ de mécanique l'ignorent.
 */
public final class Decoys {

    public static final String ROLE = "Nakasar_Fractal_Decoy";
    static final float SECONDS = 6f;
    static final double RADIUS = 12;
    static final int HP = 80;
    private static final float LURE_EVERY = 0.5f;

    private Decoys() {
    }

    /** Pose le leurre ; faux si le jeu refuse de le faire apparaître. */
    static boolean decoy(World world, Store<EntityStore> store, Ref<EntityStore> caster) {
        Vector3d at = Support.aimGround(world, store, caster, Skills.AIM_RANGE);
        Vector3d from = Telegraphs.position(store, caster);
        if (at == null || from == null) {
            return false;
        }
        Ref<EntityStore> decoy = Spawns.spawn(store, ROLE, new Vector3d(at).add(0, 0.05, 0), Telegraphs.yawToward(at, from));
        if (decoy == null) {
            return false;
        }
        Telegraphs.particle(store, Skills.FX_FLASH, new Vector3d(at).add(0, 1, 0), 1f);
        Set<Ref<EntityStore>> lured = new HashSet<>();
        long end = System.nanoTime() + Telegraphs.seconds(SECONDS);
        long[] next = {0L};
        TelegraphSystem.start(world, (w, s, now) -> {
            boolean over = now >= end || !decoy.isValid() || !Spawns.alive(s, decoy);
            if (over) {
                for (Ref<EntityStore> foe : lured) {
                    clearTarget(s, foe, decoy);
                }
                if (decoy.isValid()) {
                    Vector3d p = Telegraphs.position(s, decoy);
                    if (p != null) {
                        Telegraphs.particle(s, Skills.FX_FLASH, new Vector3d(p).add(0, 1, 0), 1f);
                    }
                    Spawns.remove(s, decoy);
                }
                return true;
            }
            if (now - next[0] < 0) {
                return false;
            }
            next[0] = now + Telegraphs.seconds(LURE_EVERY);
            Vector3d p = Telegraphs.position(s, decoy);
            if (p == null) {
                return false;
            }
            for (Ref<EntityStore> foe : Support.foesNear(w, s, p, RADIUS)) {
                if (Support.immune(s, foe)) {
                    continue;
                }
                MarkedEntitySupport marked = s.getComponent(foe, MarkedEntitySupport.getComponentType());
                if (marked != null) {
                    marked.setMarkedEntity(MarkedEntitySupport.DEFAULT_TARGET_SLOT, decoy);
                    lured.add(foe);
                }
            }
            return false;
        });
        return true;
    }

    /** Fait oublier sa cible à l'ennemi (seulement si c'est `onlyIf`, quand il est donné). */
    static void clearTarget(Store<EntityStore> store, Ref<EntityStore> foe, Ref<EntityStore> onlyIf) {
        if (foe == null || !foe.isValid()) {
            return;
        }
        MarkedEntitySupport marked = store.getComponent(foe, MarkedEntitySupport.getComponentType());
        if (marked == null) {
            return;
        }
        Ref<EntityStore> current = marked.getMarkedEntityRef(MarkedEntitySupport.DEFAULT_TARGET_SLOT);
        if (current != null && (onlyIf == null || onlyIf.equals(current))) {
            marked.setMarkedEntity(MarkedEntitySupport.DEFAULT_TARGET_SLOT, null);
        }
    }
}
