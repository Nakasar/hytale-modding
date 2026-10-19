package dev.nakasar.hytale.vampires.vampirism;

import com.hypixel.hytale.builtin.weather.components.WeatherTracker;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.util.ChunkUtil;
import com.hypixel.hytale.protocol.Opacity;
import com.hypixel.hytale.server.core.asset.type.blocktype.config.BlockType;
import com.hypixel.hytale.server.core.asset.type.weather.config.Weather;
import com.hypixel.hytale.server.core.modules.time.WorldTimeResource;
import com.hypixel.hytale.server.core.universe.world.chunk.section.BlockSection;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import org.joml.Vector3d;

import java.util.Locale;

/**
 * Le soleil qui frappe un joueur, de 0 (nuit, toit, orage) à 1 (plein jour, ciel ouvert, temps clair).
 *
 * <ul>
 *   <li>Heure : facteur d'ensoleillement du monde ({@link WorldTimeResource#getSunlightFactor()}, 0,2 ou moins la
 *       nuit, 1 à midi), ramené à 0 à l'aube et au crépuscule.</li>
 *   <li>Ciel ouvert : aucun bloc opaque ou ajouré (feuillage compris) dans les {@value #SKY_CHECK} blocs au-dessus de
 *       la tête. Le verre (transparent) laisse passer le soleil.</li>
 *   <li>Météo vue par le joueur ({@link WeatherTracker}) : l'orage annule le soleil, la pluie, la neige, les nuages et
 *       le brouillard l'atténuent de moitié. Le jeu ne classe pas ses météos : on lit leur id.</li>
 * </ul>
 */
final class SunExposure {

    /** Blocs examinés au-dessus de la tête. */
    static final int SKY_CHECK = 48;
    /** Atténuation de la pluie, des nuages... */
    static final float CLOUDY = 0.5f;

    private static final String[] STORM_WORDS = {"storm", "thunder", "lightning"};
    private static final String[] CLOUDY_WORDS = {"rain", "snow", "cloud", "overcast", "fog", "mist", "blizzard",
            "drizzle", "shower", "ash"};

    private SunExposure() {
    }

    /** Soleil sur le joueur avant ses protections. */
    static float at(Ref<EntityStore> ref, Vector3d position, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
        float daylight = daylight(store);
        if (daylight <= 0f) {
            return 0f;
        }
        float weather = weather(ref, buffer);
        if (weather <= 0f) {
            return 0f;
        }
        ChunkStore chunks = buffer.getExternalData().getWorld().getChunkStore();
        if (roofed(chunks, position)) {
            return 0f;
        }
        return daylight * weather;
    }

    /** Vrai s'il fait jour (le soleil compte) dans ce monde. */
    static boolean isDay(Store<EntityStore> store) {
        return daylight(store) > 0f;
    }

    /** 0 la nuit et jusqu'au lever, 1 dès que le soleil est franchement levé. */
    private static float daylight(Store<EntityStore> store) {
        WorldTimeResource time = store.getResource(WorldTimeResource.getResourceType());
        if (time == null) {
            return 0f;
        }
        double factor = time.getSunlightFactor();
        return (float) Math.max(0.0, Math.min(1.0, (factor - 0.25) / 0.45));
    }

    private static float weather(Ref<EntityStore> ref, CommandBuffer<EntityStore> buffer) {
        WeatherTracker tracker = buffer.getComponent(ref, WeatherTracker.getComponentType());
        if (tracker == null) {
            return 1f;
        }
        Weather weather = Weather.getAssetMap().getAsset(tracker.getWeatherIndex());
        return weather == null || weather.getId() == null ? 1f : weatherFactor(weather.getId());
    }

    /** Facteur d'une météo d'après son id : 0 pour un orage, {@value #CLOUDY} pour un temps couvert, 1 sinon. */
    static float weatherFactor(String weatherId) {
        String id = weatherId.toLowerCase(Locale.ROOT);
        for (String word : STORM_WORDS) {
            if (id.contains(word)) {
                return 0f;
            }
        }
        for (String word : CLOUDY_WORDS) {
            if (id.contains(word)) {
                return CLOUDY;
            }
        }
        return 1f;
    }

    /** Vrai si un bloc qui fait de l'ombre se trouve au-dessus de la tête du joueur. */
    private static boolean roofed(ChunkStore chunks, Vector3d position) {
        Store<ChunkStore> store = chunks.getStore();
        int x = (int) Math.floor(position.x);
        int z = (int) Math.floor(position.z);
        int fromY = (int) Math.floor(position.y) + 2;
        int toY = fromY + SKY_CHECK;
        int y = fromY;
        while (y < toY) {
            int sectionBase = (y >> ChunkUtil.BITS) << ChunkUtil.BITS;
            Ref<ChunkStore> sectionRef = chunks.getChunkSectionReferenceAtBlock(x, y, z);
            BlockSection section = sectionRef == null || !sectionRef.isValid()
                    ? null : store.getComponent(sectionRef, BlockSection.getComponentType());
            int sectionTop = Math.min(toY, sectionBase + (1 << ChunkUtil.BITS));
            if (section != null) {
                for (int by = y; by < sectionTop; by++) {
                    if (shades(section.get(x, by, z))) {
                        return true;
                    }
                }
            }
            y = sectionTop;
        }
        return false;
    }

    private static boolean shades(int blockId) {
        if (blockId == BlockType.EMPTY_ID) {
            return false;
        }
        BlockType block = BlockType.getAssetMap().getAsset(blockId);
        return block != null && block.getOpacity() != Opacity.Transparent;
    }
}
