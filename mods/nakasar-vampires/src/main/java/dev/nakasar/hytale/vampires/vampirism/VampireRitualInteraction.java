package dev.nakasar.hytale.vampires.vampirism;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.util.ChunkUtil;
import com.hypixel.hytale.protocol.InteractionState;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.SoundCategory;
import com.hypixel.hytale.protocol.WaitForDataFrom;
import com.hypixel.hytale.protocol.packets.interface_.EventTitleStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.asset.type.blocktype.config.BlockType;
import com.hypixel.hytale.server.core.asset.type.soundevent.config.SoundEvent;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.SimpleItemContainer;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.SoundUtil;
import com.hypixel.hytale.server.core.universe.world.chunk.section.BlockSection;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.EventTitleUtil;
import it.unimi.dsi.fastutil.ints.IntList;
import org.joml.Vector3d;

/**
 * {@code "Type": "Nakasar_VampireRitual"} : le rituel de l'autel sacrificiel, qui fait du joueur un vampire
 * ({@code "Mode": "Become"}) ou le guérit ({@code "Mode": "Cure"}). L'objet du rituel (calice ou encensoir) s'utilise
 * à moins de {@code AltarRadius} blocs d'un autel ({@value #ALTAR}) ; sinon, ou si le joueur est déjà dans l'état
 * visé, l'interaction échoue avec un message et l'objet n'est pas consommé (la suite {@code Next} ne s'exécute pas).
 *
 * <p>Le rituel marque le joueur : titre à l'écran, effet {@code EffectId}, son {@code SoundEventId} entendu autour de
 * l'autel, et une note ({@code NoteItemId}) déposée dans son inventaire.
 */
public class VampireRitualInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_VampireRitual";
    public static final String ALTAR = "Nakasar_Sacrificial_Altar";
    /** Sang du vampire qui sort du rituel : à moitié affamé, il doit chasser. */
    static final float BLOOD_AFTER_RITUAL = 0.5f;

    public static final BuilderCodec<VampireRitualInteraction> CODEC = BuilderCodec
            .builder(VampireRitualInteraction.class, VampireRitualInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Rituel de l'autel : devenir vampire (Mode Become) ou en guerir (Mode Cure).")
            .append(new KeyedCodec<>("Mode", Codec.STRING), (i, v) -> i.mode = v, i -> i.mode)
            .documentation("Become ou Cure.")
            .add()
            .append(new KeyedCodec<>("AltarRadius", Codec.INTEGER), (i, v) -> i.altarRadius = v, i -> i.altarRadius)
            .documentation("Distance maximale (blocs) a un autel sacrificiel.")
            .add()
            .append(new KeyedCodec<>("EffectId", Codec.STRING), (i, v) -> i.effectId = v, i -> i.effectId)
            .documentation("Effet de statut pose au joueur (visuel du rituel).")
            .add()
            .append(new KeyedCodec<>("EffectSeconds", Codec.FLOAT), (i, v) -> i.effectSeconds = v, i -> i.effectSeconds)
            .documentation("Duree de l'effet.")
            .add()
            .append(new KeyedCodec<>("SoundEventId", Codec.STRING), (i, v) -> i.soundEventId = v, i -> i.soundEventId)
            .documentation("Son joue a la position du joueur.")
            .add()
            .append(new KeyedCodec<>("NoteItemId", Codec.STRING), (i, v) -> i.noteItemId = v, i -> i.noteItemId)
            .documentation("Note deposee dans l'inventaire du joueur.")
            .add()
            .build();

    protected String mode = "Become";
    protected int altarRadius = 5;
    protected String effectId;
    protected float effectSeconds = 8f;
    protected String soundEventId;
    protected String noteItemId;

    public VampireRitualInteraction() {
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> ref = context.getEntity();
        PlayerRef player = buffer == null || ref == null || !ref.isValid()
                ? null : buffer.getComponent(ref, PlayerRef.getComponentType());
        TransformComponent transform = player == null ? null : buffer.getComponent(ref, TransformComponent.getComponentType());
        if (transform == null) {
            context.getState().state = InteractionState.Failed;
            return;
        }
        boolean become = !"Cure".equalsIgnoreCase(mode);
        String key = become ? "become" : "cure";
        Vampire vampire = Vampires.of(ref, buffer);
        if (become == (vampire != null)) {
            fail(context, player, "nakasar_vampire.ritual." + key + ".already");
            return;
        }
        Vector3d position = transform.getPosition();
        if (!nearAltar(buffer.getExternalData().getWorld().getChunkStore(), position, altarRadius)) {
            fail(context, player, "nakasar_vampire.ritual.noAltar");
            return;
        }

        if (become) {
            Vampire fresh = new Vampire();
            fresh.setBlood(BLOOD_AFTER_RITUAL);
            buffer.putComponent(ref, Vampire.getComponentType(), fresh);
        } else {
            cure(ref, buffer);
        }
        if (effectId != null && !effectId.isBlank()) {
            Vampires.applyEffect(ref, effectId, effectSeconds, buffer);
        }
        int sound = soundEventId == null ? -1 : SoundEvent.getAssetMap().getIndexOrDefault(soundEventId, -1);
        if (sound >= 0) {
            SoundUtil.playSoundEvent3d(sound, SoundCategory.SFX, position.x, position.y, position.z, buffer);
        }
        EventTitleUtil.showEventTitleToPlayer(player,
                Message.translation("nakasar_vampire.ritual." + key + ".title"),
                Message.translation("nakasar_vampire.ritual." + key + ".subtitle"), EventTitleStyle.Major);
        if (noteItemId != null && !noteItemId.isBlank()) {
            SimpleItemContainer.addOrDropItemStack(buffer, ref,
                    InventoryComponent.getCombined(buffer, ref, InventoryComponent.HOTBAR_STORAGE_BACKPACK),
                    new ItemStack(noteItemId, 1));
        }
    }

    /**
     * Défait tout ce que l'état vampire avait posé. La lumière de vision nocturne s'éteint d'elle-même
     * ({@link PrivateNightLightSystem}).
     */
    private static void cure(Ref<EntityStore> ref, CommandBuffer<EntityStore> buffer) {
        for (BloodStage stage : BloodStage.values()) {
            Vampires.removeEffect(ref, stage.effectId, buffer);
        }
        Vampires.removeEffect(ref, VampireSystem.SUNBURN, buffer);
        Vampires.removeEffect(ref, VampireSystem.SUNBURN_LIGHT, buffer);
        buffer.tryRemoveComponent(ref, Vampire.getComponentType());
    }

    private static void fail(InteractionContext context, PlayerRef player, String messageKey) {
        context.getState().state = InteractionState.Failed;
        player.sendMessage(Message.translation(messageKey));
    }

    /** Vrai si un autel sacrificiel est posé à moins de {@code radius} blocs (cube autour de la position). */
    static boolean nearAltar(ChunkStore chunks, Vector3d position, int radius) {
        int altar = BlockType.getAssetMap().getIndexOrDefault(ALTAR, -1);
        if (altar < 0) {
            return false;
        }
        Store<ChunkStore> store = chunks.getStore();
        int cx = (int) Math.floor(position.x);
        int cy = (int) Math.floor(position.y);
        int cz = (int) Math.floor(position.z);
        int minY = Math.max(0, cy - radius);
        int maxY = cy + radius;
        // Une recherche par section (16³), comme PurifyingFireSystem.scan, puis les autels de la section.
        for (int sx = (cx - radius) >> ChunkUtil.BITS; sx <= (cx + radius) >> ChunkUtil.BITS; sx++) {
            for (int sy = minY >> ChunkUtil.BITS; sy <= maxY >> ChunkUtil.BITS; sy++) {
                for (int sz = (cz - radius) >> ChunkUtil.BITS; sz <= (cz + radius) >> ChunkUtil.BITS; sz++) {
                    int baseX = sx << ChunkUtil.BITS;
                    int baseY = sy << ChunkUtil.BITS;
                    int baseZ = sz << ChunkUtil.BITS;
                    Ref<ChunkStore> sectionRef = chunks.getChunkSectionReferenceAtBlock(baseX, baseY, baseZ);
                    if (sectionRef == null || !sectionRef.isValid()) {
                        continue;
                    }
                    BlockSection section = store.getComponent(sectionRef, BlockSection.getComponentType());
                    if (section == null || !section.contains(altar)) {
                        continue;
                    }
                    boolean[] found = {false};
                    section.find(IntList.of(altar), blockIndex -> {
                        int x = baseX + ChunkUtil.xFromIndex(blockIndex);
                        int y = baseY + ChunkUtil.yFromIndex(blockIndex);
                        int z = baseZ + ChunkUtil.zFromIndex(blockIndex);
                        if (Math.abs(x - cx) <= radius && Math.abs(z - cz) <= radius && y >= minY && y <= maxY) {
                            found[0] = true;
                        }
                    });
                    if (found[0]) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        // Serveur uniquement.
    }

    @Override
    public WaitForDataFrom getWaitForDataFrom() {
        return WaitForDataFrom.Server;
    }
}
