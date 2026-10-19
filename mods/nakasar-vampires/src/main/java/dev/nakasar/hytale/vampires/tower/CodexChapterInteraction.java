package dev.nakasar.hytale.vampires.tower;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * {@code "Type": "Nakasar_CodexChapter"} : le Codex vivant « ouvre un chapitre ». Un pupitre de l'arène s'allume, un
 * livre de chapitre y apparaît et un sort se prépare ; le reste (interruption, sort lancé) est suivi par
 * {@link CodexSystem}.
 *
 * <p>Clé JSON : {@code CastTime} (float, défaut 6) : secondes laissées aux joueurs pour détruire le livre.
 */
public class CodexChapterInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_CodexChapter";

    public static final BuilderCodec<CodexChapterInteraction> CODEC = BuilderCodec
            .builder(CodexChapterInteraction.class, CodexChapterInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Le Codex vivant ouvre un chapitre : un livre apparaît sur un pupitre et un sort se prépare.")
            .append(new KeyedCodec<>("CastTime", Codec.FLOAT), (i, v) -> i.castTime = v, i -> i.castTime)
            .documentation("Secondes avant que le sort parte si le livre n'est pas détruit.")
            .add()
            .build();

    protected float castTime = 6f;

    public CodexChapterInteraction() {
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> codex = context.getEntity();
        if (buffer == null || codex == null || !codex.isValid()) {
            return;
        }
        World world = buffer.getExternalData().getWorld();
        float seconds = castTime;
        world.execute(() -> CodexSystem.openChapter(world, codex, seconds));
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        // Serveur uniquement.
    }
}
