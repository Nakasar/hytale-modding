package dev.nakasar.hytale.fractals.party;

import com.hypixel.hytale.builtin.instances.InstancesPlugin;
import com.hypixel.hytale.builtin.instances.config.InstanceWorldConfig;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.world.World;

import java.util.List;
import java.util.Locale;

/**
 * Les fractales de la saison 1 (docs/fractales/gdd.md) : leur id, l'instance qui les porte
 * ({@code Server/Instances/Nakasar_Fractal_<Id>}) et leur nom traduit. Une fractale est « ouverte » quand son instance
 * existe dans le pack : le noyau des autres annonce qu'elles arrivent.
 */
public final class FractalCatalog {

    /** Préfixe des instances du mod. */
    public static final String INSTANCE_PREFIX = "Nakasar_Fractal_";
    /** Instance (et type de portail) de l'Observatoire. */
    public static final String OBSERVATORY = "Nakasar_Fractal_Observatory";
    /** Fractales connues, dans l'ordre du distributeur de noyaux. */
    public static final List<String> IDS = List.of("Cliffside", "Uncategorized", "Volcanic", "SolidOcean", "Swampland", "Snowblind", "SilentSurf", "SirensReef", "Deepstone");

    private FractalCatalog() {
    }

    /** Id d'une fractale tapé par un joueur (casse ignorée), ou null. */
    public static String resolve(String input) {
        if (input == null) {
            return null;
        }
        String wanted = input.trim().toLowerCase(Locale.ROOT);
        for (String id : IDS) {
            if (id.toLowerCase(Locale.ROOT).equals(wanted)) {
                return id;
            }
        }
        return null;
    }

    public static String instance(String id) {
        return INSTANCE_PREFIX + id;
    }

    public static Message name(String id) {
        return Message.translation("nakasar_fractals.fractal." + id + ".name");
    }

    /** Vrai si l'instance de la fractale est dans le pack. */
    public static boolean isOpen(String id) {
        try {
            return InstancesPlugin.doesInstanceAssetExist(instance(id));
        } catch (IllegalArgumentException e) {
            return false;
        }
    }

    /** Fractale jouée dans ce monde (instance {@code Nakasar_Fractal_<Id>}), ou null. */
    public static String fractalOf(World world) {
        String name = instanceName(world);
        if (name == null || !name.startsWith(INSTANCE_PREFIX)) {
            return null;
        }
        String id = name.substring(INSTANCE_PREFIX.length());
        return IDS.contains(id) ? id : null;
    }

    public static boolean isObservatory(World world) {
        return OBSERVATORY.equals(instanceName(world));
    }

    private static String instanceName(World world) {
        InstanceWorldConfig config = world == null ? null : InstanceWorldConfig.get(world.getWorldConfig());
        return config == null ? null : config.getInstanceName();
    }
}
