package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.Resource;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * L'état du monde vivant entre les villages (ressource du monde, id {@value #ID}), sauvegardé avec lui. Chaque partie
 * (voyageurs, relations, campements, auberges, traces, calendrier...) garde ses entrées sous forme de textes
 * « clé = valeur » qu'elle lit et écrit elle-même, comme les balises de route du registre des villages : le format
 * reste lisible dans la sauvegarde et une partie nouvelle n'oblige pas à changer le codec.
 *
 * <p>Tout accès passe par le thread du monde.
 */
public final class WorldLifeRegistry implements Resource<EntityStore> {

    public static final String ID = "Nakasar_Peuples_WorldLife";

    /** Les parties sauvegardées (une clé du codec chacune). */
    public enum Part {
        /** Voyageurs en route : id = état ({@link Travellers}). */
        TRAVELLERS("Travellers"),
        /** Relations entre villages : « a|b » = état ({@link Relations}). */
        RELATIONS("Relations"),
        /** Passages par liaison et par jour : « a|b » = jours ({@link Links}). */
        TRAFFIC("Traffic"),
        /** Campements temporaires et de réfugiés : id = état ({@link Camps}). */
        CAMPS("Camps"),
        /** Auberges de relais : « a|b » = état ({@link Inns}). */
        INNS("Inns"),
        /** Traces anciennes : id = état ({@link Traces}). */
        TRACES("Traces"),
        /** Structures temporaires collées (blocs à rendre) : id = blocs ({@link TempStructures}). */
        STRUCTURES("Structures"),
        /** Calendrier : nom = valeur ({@link Calendar}). */
        CALENDAR("Calendar");

        final String key;

        Part(String key) {
            this.key = key;
        }
    }

    public static final BuilderCodec<WorldLifeRegistry> CODEC = BuilderCodec.builder(WorldLifeRegistry.class, WorldLifeRegistry::new)
            .append(new KeyedCodec<>(Part.TRAVELLERS.key, Codec.STRING_ARRAY), (r, a) -> r.read(Part.TRAVELLERS, a), r -> r.write(Part.TRAVELLERS))
            .documentation("Monde vivant : « clé=valeur », lu par le Java du mod.")
            .add()
            .append(new KeyedCodec<>(Part.RELATIONS.key, Codec.STRING_ARRAY), (r, a) -> r.read(Part.RELATIONS, a), r -> r.write(Part.RELATIONS))
            .documentation("Monde vivant : « clé=valeur », lu par le Java du mod.")
            .add()
            .append(new KeyedCodec<>(Part.TRAFFIC.key, Codec.STRING_ARRAY), (r, a) -> r.read(Part.TRAFFIC, a), r -> r.write(Part.TRAFFIC))
            .documentation("Monde vivant : « clé=valeur », lu par le Java du mod.")
            .add()
            .append(new KeyedCodec<>(Part.CAMPS.key, Codec.STRING_ARRAY), (r, a) -> r.read(Part.CAMPS, a), r -> r.write(Part.CAMPS))
            .documentation("Monde vivant : « clé=valeur », lu par le Java du mod.")
            .add()
            .append(new KeyedCodec<>(Part.INNS.key, Codec.STRING_ARRAY), (r, a) -> r.read(Part.INNS, a), r -> r.write(Part.INNS))
            .documentation("Monde vivant : « clé=valeur », lu par le Java du mod.")
            .add()
            .append(new KeyedCodec<>(Part.TRACES.key, Codec.STRING_ARRAY), (r, a) -> r.read(Part.TRACES, a), r -> r.write(Part.TRACES))
            .documentation("Monde vivant : « clé=valeur », lu par le Java du mod.")
            .add()
            .append(new KeyedCodec<>(Part.STRUCTURES.key, Codec.STRING_ARRAY), (r, a) -> r.read(Part.STRUCTURES, a), r -> r.write(Part.STRUCTURES))
            .documentation("Monde vivant : « clé=valeur », lu par le Java du mod.")
            .add()
            .append(new KeyedCodec<>(Part.CALENDAR.key, Codec.STRING_ARRAY), (r, a) -> r.read(Part.CALENDAR, a), r -> r.write(Part.CALENDAR))
            .documentation("Monde vivant : « clé=valeur », lu par le Java du mod.")
            .add()
            .build();

    private final Map<Part, Map<String, String>> parts = new LinkedHashMap<>();

    public WorldLifeRegistry() {
        for (Part part : Part.values()) {
            parts.put(part, new LinkedHashMap<>());
        }
    }

    private void read(Part part, String[] entries) {
        Map<String, String> map = parts.get(part);
        map.clear();
        if (entries == null) {
            return;
        }
        for (String e : entries) {
            if (e == null) {
                continue;
            }
            int cut = e.indexOf('=');
            if (cut > 0) {
                map.put(e.substring(0, cut), e.substring(cut + 1));
            }
        }
    }

    private String[] write(Part part) {
        Map<String, String> map = parts.get(part);
        String[] out = new String[map.size()];
        int i = 0;
        for (Map.Entry<String, String> e : map.entrySet()) {
            out[i++] = e.getKey() + "=" + e.getValue();
        }
        return out;
    }

    /** Les entrées d'une partie (modifiables). */
    public Map<String, String> part(Part part) {
        return parts.get(part);
    }

    public String get(Part part, String key) {
        return parts.get(part).get(key);
    }

    public void put(Part part, String key, String value) {
        if (value == null) {
            parts.get(part).remove(key);
        } else {
            parts.get(part).put(key, value);
        }
    }

    public long getLong(Part part, String key, long fallback) {
        String v = get(part, key);
        if (v == null) {
            return fallback;
        }
        try {
            return Long.parseLong(v.trim());
        } catch (NumberFormatException e) {
            return fallback;
        }
    }

    @Override
    public Resource<EntityStore> clone() {
        WorldLifeRegistry copy = new WorldLifeRegistry();
        for (Part part : Part.values()) {
            copy.parts.get(part).putAll(parts.get(part));
        }
        return copy;
    }
}
