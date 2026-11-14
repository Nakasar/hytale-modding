package dev.nakasar.hytale.peuples.dialogue;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;
import org.joml.Vector3d;

/**
 * Ce qu'une condition ou un effet de dialogue peut lire et changer : le joueur, son monde, et le village où il se
 * trouve (le plus proche à moins de {@value Villages#RADIUS} blocs, ou null). Toujours sur le thread du monde.
 */
public record DialogueContext(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef playerRef, Village village) {

    /** Contexte du joueur `ref` dans `world`, avec le village le plus proche de sa position. */
    public static DialogueContext of(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef playerRef) {
        Vector3d at = playerRef.getTransform() == null ? null : playerRef.getTransform().getPosition();
        Village village = at == null ? null : Villages.registry(world).nearest(at.x(), at.y(), at.z(), Villages.RADIUS);
        return new DialogueContext(world, store, ref, playerRef, village);
    }

    public boolean valid() {
        return ref != null && ref.isValid();
    }

    /** État sauvegardé du joueur, créé au besoin. */
    public PeuplesPlayer player() {
        return PeuplesPlayer.ensure(store, ref);
    }
}
