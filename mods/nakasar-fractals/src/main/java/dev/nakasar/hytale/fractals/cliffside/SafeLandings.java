package dev.nakasar.hytale.fractals.cliffside;

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
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Retours de saut : dans une zone de saut ({@link CliffsideLayout#JUMP_ZONES}), la dernière plate-forme sûre
 * ({@value #LANDING}) où chaque joueur s'est tenu est retenue ; tombé plus de {@value #DROP} blocs plus bas au-dessus
 * de la même zone, il y est ramené. Hors des zones (ou avant toute plate-forme), rien ne change : la chute normale et le
 * filet anti-chute s'appliquent.
 */
final class SafeLandings {

    static final String LANDING = "Nakasar_Fractal_Landing";
    static final double DROP = 4;

    private record Landing(int zone, Vector3d at) {
    }

    private final Map<UUID, Landing> last = new HashMap<>();

    void step(World world, Store<EntityStore> store, List<PlayerRef> players) {
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
            if (zone >= 0 && LANDING.equals(WorldBlocks.name(chunks, x, (int) Math.floor(at.y() - 0.1), z))) {
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
            player.sendMessage(Message.translation(Cliffside.MESSAGES + "landing.back"));
        }
    }

    /** Index de la zone de saut qui contient `at`, -1 sinon. */
    private static int zone(Vector3d at) {
        List<CliffsideLayout.Box> zones = CliffsideLayout.JUMP_ZONES;
        for (int i = 0; i < zones.size(); i++) {
            if (zones.get(i).contains(at.x(), at.y(), at.z())) {
                return i;
            }
        }
        return -1;
    }

    /** Vrai si `at` est à l'aplomb de la zone `zone` (même emprise au sol, toute hauteur sous son sommet). */
    private static boolean above(int zone, Vector3d at) {
        CliffsideLayout.Box box = CliffsideLayout.JUMP_ZONES.get(zone);
        return at.y() < box.y1() + 1 && box.contains(at.x(), Math.max(at.y(), box.y0()), at.z());
    }
}
