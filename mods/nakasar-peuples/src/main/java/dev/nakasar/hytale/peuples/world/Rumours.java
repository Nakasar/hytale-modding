package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Les rumeurs que racontent voyageurs, aubergistes et campeurs : tirées de l'état du monde vivant (caravanes en route,
 * campements, relations entre villages, prochaine foire, auberges, vestiges pas encore vus par le joueur).
 */
public final class Rumours {

    public static final String KEYS = WorldLife.KEYS + "rumour.";

    private Rumours() {
    }

    public static Message random(World world, Store<EntityStore> store, Ref<EntityStore> player) {
        List<Message> out = new ArrayList<>();
        long day = GameClock.day(store);
        for (Travellers.Traveller t : Travellers.all(world)) {
            Village from = Villages.registry(world).byId(t.from());
            Village to = Villages.registry(world).byId(t.to());
            if (from != null && to != null) {
                out.add(Message.translation(KEYS + "traveller." + t.kind().key()).param("from", from.name()).param("to", to.name()));
            }
        }
        for (Camps.Camp c : Camps.all(world)) {
            Village v = Villages.registry(world).byId(c.village());
            if (v != null) {
                out.add(Message.translation(KEYS + "camp." + c.type().key()).param("village", v.name())
                        .param("direction", Message.translation(Villages.MESSAGES + "dir." + Requests.direction(c.x() - v.x(), c.z() - v.z()))));
            }
        }
        for (Links.Link l : Links.all(world)) {
            int value = Relations.value(world, l.a(), l.b());
            String state = Relations.state(value);
            if (!state.equals("neutral")) {
                out.add(Message.translation(KEYS + "relation." + state).param("a", l.a().name()).param("b", l.b().name()));
            }
        }
        for (Inns.Inn inn : Inns.all(world)) {
            String[] ids = inn.link().split("\\|");
            Village a = Villages.registry(world).byId(ids[0]);
            Village b = ids.length > 1 ? Villages.registry(world).byId(ids[1]) : null;
            if (a != null && b != null && inn.open()) {
                out.add(Message.translation(KEYS + "inn").param("a", a.name()).param("b", b.name()));
            }
        }
        out.addAll(HamletTrips.rumours(world));
        Message hamlet = Hamlets.rumour(world, store, player);
        if (hamlet != null) {
            out.add(hamlet);
        }
        Object[] fair = Calendar.nextFair(world, day);
        if (fair != null && fair[0] != null) {
            out.add(Message.translation(KEYS + "fair").param("village", ((Village) fair[0]).name()).param("days", ((Number) fair[1]).intValue()));
        }
        Traces.Trace trace = Traces.nearestUnknown(world, store, player);
        Vector3d at = Requests.position(store, player);
        if (trace != null && at != null) {
            out.add(Message.translation(KEYS + "trace")
                    .param("distance", (int) Math.round(Math.hypot(trace.x() - at.x(), trace.z() - at.z())))
                    .param("direction", Message.translation(Villages.MESSAGES + "dir." + Requests.direction(trace.x() - at.x(), trace.z() - at.z()))));
        }
        if (out.isEmpty()) {
            return Message.translation(KEYS + "none");
        }
        return out.get(ThreadLocalRandom.current().nextInt(out.size()));
    }
}
