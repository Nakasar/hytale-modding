package dev.nakasar.hytale.fractals.arena;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/**
 * Retours de saut des fractales : dans une zone de saut, la dernière plate-forme sûre ({@value #LANDING}) où chaque
 * joueur s'est tenu est retenue ; tombé plus de {@value #DROP} blocs plus bas au-dessus de la même zone, il y est
 * ramené. Hors des zones (ou avant toute plate-forme), rien ne change : la chute normale et le filet anti-chute
 * s'appliquent. Une zone dont seul le départ porte des plates-formes sûres ramène au départ (harpies de l'Inclassable).
 */
public final class SafeLandings {

    public static final String LANDING = "Nakasar_Fractal_Landing";
    public static final double DROP = 4;

    private record Landing(int zone, Vector3d at) {
    }

    private final List<Box> zones;
    private final String messageKey;
    private final Set<String> landings;
    private final Map<UUID, Landing> last = new HashMap<>();

    /** `zones` : zones de saut ; `messageKey` : message au joueur ramené. */
    public SafeLandings(List<Box> zones, String messageKey) {
        this(zones, messageKey, Set.of(LANDING));
    }

    /** Comme ci-dessus, avec d'autres blocs sûrs que {@value #LANDING} (fragments de jade de l'Océan solide). */
    public SafeLandings(List<Box> zones, String messageKey, Set<String> landings) {
        this.zones = zones;
        this.messageKey = messageKey;
        this.landings = landings;
    }

    public void step(World world, Store<EntityStore> store, List<PlayerRef> players) {
        ChunkStore chunks = world.getChunkStore();
        for (PlayerRef player : players) {
            Ref<EntityStore> ref = player.getReference();
            Vector3d at = Telegraphs.position(store, ref);
            if (at == null) {
                continue;
            }
            int x = (int) Math.floor(at.x());
            int z = (int) Math.floor(at.z());
            int zone = zone(at);
            String below = zone >= 0 ? WorldBlocks.name(chunks, x, (int) Math.floor(at.y() - 0.1), z) : null;
            if (below != null && landings.contains(below)) {
                last.put(player.getUuid(), new Landing(zone, new Vector3d(x + 0.5, Math.floor(at.y() + 0.05), z + 0.5)));
                continue;
            }
            Landing landing = last.get(player.getUuid());
            if (landing == null || at.y() >= landing.at().y() - DROP || !above(landing.zone(), at)) {
                continue;
            }
            TransformComponent transform = store.getComponent(ref, TransformComponent.getComponentType());
            Rotation3f rotation = transform != null ? transform.getRotation() : new Rotation3f();
            store.putComponent(ref, Teleport.getComponentType(), Teleport.createForPlayer(new Vector3d(landing.at()), rotation));
            player.sendMessage(Message.translation(messageKey));
        }
    }

    /** Oublie les plates-formes retenues (nouveau départ d'un saut). */
    public void forget(UUID player) {
        last.remove(player);
    }

    /** Index de la zone de saut qui contient `at`, -1 sinon. */
    private int zone(Vector3d at) {
        for (int i = 0; i < zones.size(); i++) {
            if (zones.get(i).contains(at.x(), at.y(), at.z())) {
                return i;
            }
        }
        return -1;
    }

    /** Vrai si `at` est à l'aplomb de la zone `zone` (même emprise au sol, toute hauteur sous son sommet). */
    private boolean above(int zone, Vector3d at) {
        Box box = zones.get(zone);
        return at.y() < box.y1() + 1 && box.over(at.x(), at.z());
    }
}
