package dev.nakasar.hytale.vampires.arena;

import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import org.joml.Vector3d;
import org.joml.Vector3i;

import java.util.List;

/**
 * Braseros de la salle du Spectre (Kevin, 20 octobre 2026) : les joueurs les allument (clic ou coup, {@link ArenaBlocks}) ;
 * à moins de {@value #SAFE_RADIUS} blocs d'un brasero allumé, le Spectre ne peut ni fondre sur sa cible ni surgir
 * ({@code Nakasar_Telegraph}, clé {@code SafeFromBraziers}). Sous la moitié de sa vie, une bourrasque glacée annoncée
 * en éteint un.
 *
 * <p>Brasero des ruines humaines vanilla (ceux du temple sombre servent aux énigmes de la Tour) : l'état « Off » est un id de bloc à part, comme l'état « On ».
 */
public final class Braziers {

    public static final String BASE = "Furniture_Human_Ruins_Brazier";
    public static final String OFF = "*Furniture_Human_Ruins_Brazier_State_Definitions_Off";
    public static final String ON = "*Furniture_Human_Ruins_Brazier_State_Definitions_On";
    public static final List<String> LIT = List.of(BASE, ON);
    public static final double SAFE_RADIUS = 5.0;

    private Braziers() {
    }

    /** Vrai si un brasero allumé se trouve à moins de `radius` blocs (à l'horizontale, 4 blocs en hauteur) de `at`. */
    public static boolean litNear(ChunkStore chunks, Vector3d at, double radius) {
        for (Vector3i block : WorldBlocks.find(chunks, at, (int) Math.ceil(radius) + 1, LIT)) {
            double dx = block.x + 0.5 - at.x();
            double dz = block.z + 0.5 - at.z();
            if (dx * dx + dz * dz <= radius * radius && Math.abs(block.y - at.y()) <= 4) {
                return true;
            }
        }
        return false;
    }

    public static List<Vector3i> lit(ChunkStore chunks, Vector3d around, int radius) {
        return WorldBlocks.find(chunks, around, radius, LIT);
    }

    public static boolean isUnlit(String name) {
        return OFF.equals(name);
    }

    public static boolean light(ChunkStore chunks, Vector3i at) {
        return WorldBlocks.set(chunks, at.x, at.y, at.z, ON, WorldBlocks.rotation(chunks, at.x, at.y, at.z));
    }

    public static boolean snuff(ChunkStore chunks, Vector3i at) {
        return WorldBlocks.set(chunks, at.x, at.y, at.z, OFF, WorldBlocks.rotation(chunks, at.x, at.y, at.z));
    }
}
