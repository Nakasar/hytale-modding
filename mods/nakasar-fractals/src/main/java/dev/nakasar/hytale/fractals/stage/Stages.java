package dev.nakasar.hytale.fractals.stage;

import com.hypixel.hytale.server.core.universe.world.World;
import dev.nakasar.hytale.fractals.party.FractalCatalog;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/** Registre des déroulés de fractales ({@link FractalStage}), rempli au démarrage du plugin. */
public final class Stages {

    private static final Map<String, FractalStage> STAGES = new ConcurrentHashMap<>();

    private Stages() {
    }

    public static void register(FractalStage stage) {
        STAGES.put(stage.fractal(), stage);
    }

    /** Déroulé de la fractale jouée dans ce monde, ou null. */
    public static FractalStage of(World world) {
        String fractal = FractalCatalog.fractalOf(world);
        return fractal == null ? null : STAGES.get(fractal);
    }

    public static void clearAll() {
        STAGES.values().forEach(FractalStage::clearAll);
    }
}
