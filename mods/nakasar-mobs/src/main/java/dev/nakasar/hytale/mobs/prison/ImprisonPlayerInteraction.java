package dev.nakasar.hytale.mobs.prison;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.util.ChunkUtil;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.protocol.InteractionState;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.asset.type.blocktype.config.BlockType;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.EntityEffect;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.OverlapBehavior;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.entity.effect.EffectControllerComponent;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.modules.entity.component.HeadRotation;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.world.chunk.section.BlockSection;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.mobs.MobsPlugin;
import it.unimi.dsi.fastutil.ints.IntList;
import org.joml.Vector3d;

/**
 * {@code "Type": "Nakasar_ImprisonPlayer"} : envoie le joueur ciblé dans la cellule la plus proche du lanceur
 * (le Capitaine de la garde).
 *
 * <p>Une cellule est un bloc invisible et traversable ({@code CellBlock}) posé au niveau des pieds dans le prefab
 * du poste de garde. On cherche le plus proche dans un cube de {@code Radius} blocs autour du lanceur, section
 * par section : une section chargée qui ne contient pas ce bloc est écartée, les autres sont lues par leur palette. Le joueur est
 * téléporté au centre du bloc trouvé. Sans cellule à portée, il reçoit seulement l'effet.
 *
 * <p>La cible est l'entité fournie par la chaîne (le {@code HitEntity} d'un {@code Selector}). Échoue (branche
 * {@code Failed}) si ce n'est pas un joueur.
 *
 * <p>Clés JSON :
 * <ul>
 *   <li>{@code CellBlock} (string, défaut {@code Nakasar_Prison_Cell}) : id du bloc qui marque une cellule ;</li>
 *   <li>{@code Radius} (int, défaut 24) : rayon de recherche autour du lanceur ;</li>
 *   <li>{@code EffectId} (string, optionnel) : effet de statut appliqué au joueur ;</li>
 *   <li>{@code Duration} (float, défaut 5) : durée de cet effet en secondes.</li>
 * </ul>
 */
public class ImprisonPlayerInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_ImprisonPlayer";

    public static final BuilderCodec<ImprisonPlayerInteraction> CODEC = BuilderCodec
            .builder(ImprisonPlayerInteraction.class, ImprisonPlayerInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Teleporte le joueur cible sur le bloc de cellule le plus proche du lanceur.")
            .append(new KeyedCodec<>("CellBlock", Codec.STRING), (i, v) -> i.cellBlock = v, i -> i.cellBlock)
            .documentation("Id du bloc invisible qui marque une cellule.")
            .add()
            .append(new KeyedCodec<>("Radius", Codec.INTEGER), (i, v) -> i.radius = v, i -> i.radius)
            .documentation("Rayon (blocs) de recherche d'une cellule autour du lanceur.")
            .add()
            .append(new KeyedCodec<>("EffectId", Codec.STRING), (i, v) -> i.effectId = v, i -> i.effectId)
            .documentation("Effet de statut applique au joueur (optionnel).")
            .add()
            .append(new KeyedCodec<>("Duration", Codec.FLOAT), (i, v) -> i.duration = v, i -> i.duration)
            .documentation("Duree en secondes de l'effet.")
            .add()
            .build();

    protected String cellBlock = "Nakasar_Prison_Cell";
    protected int radius = 24;
    protected String effectId;
    protected float duration = 5f;

    public ImprisonPlayerInteraction() {
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> owner = context.getOwningEntity();
        Ref<EntityStore> caster = owner != null && owner.isValid() ? owner : context.getEntity();
        Ref<EntityStore> target = context.getTargetEntity();
        if (buffer == null || caster == null || !caster.isValid() || target == null || !target.isValid()
                || target.equals(caster) || buffer.getComponent(target, Player.getComponentType()) == null) {
            context.getState().state = InteractionState.Failed;
            return;
        }

        TransformComponent casterTransform = buffer.getComponent(caster, TransformComponent.getComponentType());
        Vector3d cell = casterTransform == null ? null
                : findNearestCell(buffer.getExternalData().getWorld().getChunkStore(), casterTransform.getPosition());
        if (cell != null) {
            TransformComponent targetTransform = buffer.getComponent(target, TransformComponent.getComponentType());
            Rotation3f rotation = targetTransform != null ? targetTransform.getRotation() : new Rotation3f();
            Teleport teleport = Teleport.createForPlayer(cell, rotation);
            HeadRotation head = buffer.getComponent(target, HeadRotation.getComponentType());
            if (head != null) {
                teleport.setHeadRotation(head.getRotation());
            }
            buffer.putComponent(target, Teleport.getComponentType(), teleport);
        }

        if (effectId != null && !effectId.isBlank() && duration > 0) {
            EntityEffect effect = EntityEffect.getAssetMap().getAsset(effectId);
            EffectControllerComponent effects = buffer.getComponent(target, EffectControllerComponent.getComponentType());
            if (effect != null && effects != null) {
                effects.addEffect(target, effect, duration, OverlapBehavior.OVERWRITE, buffer, caster);
            } else if (effect == null) {
                MobsPlugin.get().getLogger().atWarning().log("%s : effet '%s' introuvable", TYPE_ID, effectId);
            }
        }
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        // Serveur uniquement.
    }

    /** Centre (pieds) du bloc de cellule chargé le plus proche de {@code from}, ou null s'il n'y en a pas. */
    private Vector3d findNearestCell(ChunkStore chunks, Vector3d from) {
        int blockId = BlockType.getAssetMap().getIndexOrDefault(cellBlock, -1);
        if (blockId < 0) {
            MobsPlugin.get().getLogger().atWarning().log("%s : bloc '%s' introuvable", TYPE_ID, cellBlock);
            return null;
        }
        Store<ChunkStore> store = chunks.getStore();
        int cx = (int) Math.floor(from.x);
        int cy = (int) Math.floor(from.y);
        int cz = (int) Math.floor(from.z);
        int minY = Math.max(0, cy - radius);
        int maxY = Math.min(ChunkUtil.HEIGHT_MINUS_1, cy + radius);
        long[] best = {Long.MAX_VALUE};
        Vector3d[] result = {null};
        for (int sx = (cx - radius) >> ChunkUtil.BITS; sx <= (cx + radius) >> ChunkUtil.BITS; sx++) {
            for (int sy = minY >> ChunkUtil.BITS; sy <= maxY >> ChunkUtil.BITS; sy++) {
                for (int sz = (cz - radius) >> ChunkUtil.BITS; sz <= (cz + radius) >> ChunkUtil.BITS; sz++) {
                    int baseX = sx << ChunkUtil.BITS;
                    int baseY = sy << ChunkUtil.BITS;
                    int baseZ = sz << ChunkUtil.BITS;
                    Ref<ChunkStore> ref = chunks.getChunkSectionReferenceAtBlock(baseX, baseY, baseZ);
                    if (ref == null || !ref.isValid()) {
                        continue;
                    }
                    BlockSection section = store.getComponent(ref, BlockSection.getComponentType());
                    if (section == null || !section.contains(blockId)) {
                        continue;
                    }
                    section.find(IntList.of(blockId), index -> {
                        int x = baseX + ChunkUtil.xFromIndex(index);
                        int y = baseY + ChunkUtil.yFromIndex(index);
                        int z = baseZ + ChunkUtil.zFromIndex(index);
                        long dx = x - cx;
                        long dy = y - cy;
                        long dz = z - cz;
                        long distance = dx * dx + dy * dy + dz * dz;
                        if (distance < best[0] && Math.abs(dx) <= radius && Math.abs(dy) <= radius && Math.abs(dz) <= radius) {
                            best[0] = distance;
                            result[0] = new Vector3d(x + 0.5, y + 0.05, z + 0.5);
                        }
                    });
                }
            }
        }
        return result[0];
    }
}
