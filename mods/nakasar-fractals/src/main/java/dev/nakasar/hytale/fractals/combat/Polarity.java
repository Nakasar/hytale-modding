package dev.nakasar.hytale.fractals.combat;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Charges positives et négatives (machine de l'Asura délirant, Inclassable) : chaque joueur reçoit une charge, en
 * alternance ; deux joueurs de charges opposées à moins de {@value #RADIUS} blocs l'un de l'autre perdent chacun
 * {@value #PART} de leurs PV max par seconde (arc entre eux). Seul (GDD), la charge du joueur s'inverse toutes les
 * {@value #SOLO_FLIP} s et des pylônes de charge fixe tiennent le rôle de l'allié : il faut s'éloigner de celui qui est
 * devenu opposé. Les charges sont montrées par un effet ({@value #POSITIVE} / {@value #NEGATIVE}).
 */
public final class Polarity {

    public static final String POSITIVE = "Nakasar_Fractal_Charge_Positive";
    public static final String NEGATIVE = "Nakasar_Fractal_Charge_Negative";
    public static final double RADIUS = 3;
    public static final float PART = 0.08f;
    public static final float SOLO_FLIP = 20f;
    private static final String CAUSE = "Nakasar_Fractal_Instability";

    /** Pylône de charge fixe (variante seul). */
    public record Pylon(Vector3d at, int sign) {
    }

    private final Map<UUID, Integer> signs = new HashMap<>();
    private final List<Pylon> pylons = new ArrayList<>();
    private final String messages;
    private boolean solo;
    private float clock;
    private float flip;

    /** `messages` : préfixe des clés de langue ({@code <préfixe>charge.positive}, {@code .negative}, {@code .flip}). */
    public Polarity(String messages) {
        this.messages = messages;
    }

    /** Distribue les charges ; seul, les pylônes `soloPylons` (signe +1 / -1) entrent en jeu. */
    public void start(List<PlayerRef> players, List<Pylon> soloPylons) {
        signs.clear();
        pylons.clear();
        List<PlayerRef> order = new ArrayList<>(players);
        Collections.shuffle(order);
        for (int i = 0; i < order.size(); i++) {
            int sign = i % 2 == 0 ? 1 : -1;
            signs.put(order.get(i).getUuid(), sign);
            tell(order.get(i), sign, false);
        }
        solo = order.size() <= 1;
        if (solo) {
            pylons.addAll(soloPylons);
        }
        clock = 0f;
        flip = 0f;
    }

    public List<Pylon> pylons() {
        return pylons;
    }

    public boolean active() {
        return !signs.isEmpty();
    }

    /** Un pas de jeu : effets, dégâts entre charges opposées, inversion seul. */
    public void step(World world, Store<EntityStore> store, List<PlayerRef> players, float dt) {
        if (signs.isEmpty()) {
            return;
        }
        for (PlayerRef player : players) {
            // Arrivé en cours de combat : la charge qui manque le plus.
            signs.computeIfAbsent(player.getUuid(), id -> {
                int balance = signs.values().stream().mapToInt(Integer::intValue).sum();
                int sign = balance > 0 ? -1 : 1;
                tell(player, sign, false);
                return sign;
            });
        }
        if (solo) {
            flip += dt;
            if (flip >= SOLO_FLIP) {
                flip = 0f;
                signs.replaceAll((id, sign) -> -sign);
                players.forEach(p -> tell(p, signs.get(p.getUuid()), true));
            }
        }
        clock += dt;
        if (clock < 1f) {
            return;
        }
        clock = 0f;
        for (PlayerRef player : players) {
            Ref<EntityStore> ref = player.getReference();
            int sign = signs.getOrDefault(player.getUuid(), 1);
            Hurt.effect(store, ref, sign > 0 ? POSITIVE : NEGATIVE, 1.5f);
            Vector3d at = Telegraphs.position(store, ref);
            if (at == null) {
                continue;
            }
            Vector3d opposite = null;
            for (PlayerRef other : players) {
                Vector3d there = other == player ? null : Telegraphs.position(store, other.getReference());
                if (there != null && signs.getOrDefault(other.getUuid(), 1) != sign && there.distance(at) <= RADIUS) {
                    opposite = there;
                    break;
                }
            }
            for (Pylon pylon : pylons) {
                if (opposite == null && pylon.sign() != sign && Telegraphs.horizontal(pylon.at(), at) <= RADIUS
                        && Math.abs(pylon.at().y() - at.y()) <= 3) {
                    opposite = pylon.at();
                }
            }
            if (opposite != null) {
                Hurt.percent(store, ref, PART, CAUSE);
                Telegraphs.particle(store, "Nakasar_Fractal_Lightning_Arc", new Vector3d(at).lerp(opposite, 0.5).add(0, 1.2, 0), 0.8f);
            }
        }
        for (Pylon pylon : pylons) {
            Telegraphs.particle(store, pylon.sign() > 0 ? "Nakasar_Fractal_Charge_Plus" : "Nakasar_Fractal_Charge_Minus",
                    new Vector3d(pylon.at()).add(0, 1.5, 0), 1f);
        }
    }

    /** Fin du combat : plus de charges. */
    public void stop(Store<EntityStore> store, List<PlayerRef> players) {
        signs.clear();
        pylons.clear();
    }

    private void tell(PlayerRef player, int sign, boolean flipped) {
        String key = messages + (flipped ? "charge.flip." : "charge.") + (sign > 0 ? "positive" : "negative");
        player.sendMessage(Message.translation(key));
    }
}
