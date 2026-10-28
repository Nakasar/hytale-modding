package dev.nakasar.hytale.fractals.stage;

import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import org.joml.Vector3d;

/**
 * Le déroulé d'une fractale (Inclassable, Volcanique, et les suivantes), branché sur les systèmes communs du paquet
 * {@code stage} : {@link StageSystem} l'avance quatre fois par seconde, {@link StageDamageFilter} lui passe les coups,
 * {@link StageUseInteraction} les blocs utilisés, {@link FoeDeathSystem} les morts d'ennemis. Chaque fractale garde
 * son état par monde. La Falaise, écrite avant, a encore ses propres systèmes.
 */
public interface FractalStage {

    /** Id de la fractale ({@code party.FractalCatalog#IDS}). */
    String fractal();

    /** Un pas de jeu, sur le thread du monde. */
    void step(World world, float dt);

    /**
     * Un coup dans la fractale (groupe de filtres, avant les armures) : `victimRole` est null pour un joueur,
     * `attacker` null hors coup d'entité. Annuler ou changer `damage` ici.
     */
    default void filter(World world, Store<EntityStore> store, CommandBuffer<EntityStore> buffer, Ref<EntityStore> victim,
                        String victimRole, Ref<EntityStore> attacker, Damage damage) {
    }

    /**
     * Vrai si le boss `ref` (rôle à barre de boss) est protégé en ce moment, tous ses coups annulés par
     * {@link #filter} : {@link StageShieldSystem} lui pose alors l'invulnérabilité vanilla (barre invulnérable).
     */
    default boolean shielded(World world, Store<EntityStore> store, Ref<EntityStore> ref, String role) {
        return false;
    }

    /** Bloc utilisé ({@code Nakasar_Fractal_Use}, action `action`) par `player`, sur le thread du monde. */
    default void use(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, String action,
                     int x, int y, int z) {
    }

    /** Objet lancé ({@link ThrowItemInteraction}, action `action`) par `player` arrivé sur le PNJ `target`. */
    default void thrown(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, String action,
                        Ref<EntityStore> target) {
    }

    /** Un PNJ du camp des fractales vient de recevoir un coup mortel en `at` (avant sa mort, thread du monde). */
    default void onFoeDeath(World world, Store<EntityStore> store, String role, Vector3d at) {
    }

    /** Arrêt du plugin : oublier tous les états. */
    default void clearAll() {
    }
}
