package dev.nakasar.hytale.vampires.vampirism;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.WaitForDataFrom;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.SimpleItemContainer;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageCause;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageSystems;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.vampires.rune.AbilityAttributes;

import java.util.concurrent.ThreadLocalRandom;

/**
 * {@code "Type": "Nakasar_BloodFeed"} : boire le sang de la cible touchée (runes de sang, dans {@code HitEntity}).
 * Rien ne se passe sur une cible sans sang : morts-vivants, vampires, objets ({@link Vampires#isLiving}).
 *
 * <ul>
 *   <li>Lanceur vampire : il se nourrit ({@code BloodGain} de sa réserve) et la rune est plus forte : la cible prend
 *       {@code VampireBonusDamage} dégâts physiques de plus et le vampire récupère {@code VampireBonusHeal} points de
 *       vie de plus.</li>
 *   <li>Tout lanceur joueur : {@code DropChance} de recueillir un {@code DropItem} (sang frais, ingrédient des fioles
 *       de l'autel) dans son inventaire.</li>
 * </ul>
 */
public class BloodFeedInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_BloodFeed";

    public static final BuilderCodec<BloodFeedInteraction> CODEC = BuilderCodec
            .builder(BloodFeedInteraction.class, BloodFeedInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Boit le sang de la cible touchee : nourrit un lanceur vampire, recueille du sang frais.")
            .append(new KeyedCodec<>("BloodGain", Codec.FLOAT), (i, v) -> i.bloodGain = v, i -> i.bloodGain)
            .documentation("Sang rendu a un lanceur vampire (0 a 1 = toute la reserve).")
            .add()
            .append(new KeyedCodec<>("VampireBonusDamage", Codec.FLOAT), (i, v) -> i.bonusDamage = v, i -> i.bonusDamage)
            .documentation("Degats physiques en plus quand le lanceur est vampire.")
            .add()
            .append(new KeyedCodec<>("VampireBonusHeal", Codec.FLOAT), (i, v) -> i.bonusHeal = v, i -> i.bonusHeal)
            .documentation("Points de vie rendus en plus au lanceur vampire.")
            .add()
            .append(new KeyedCodec<>("DropChance", Codec.FLOAT), (i, v) -> i.dropChance = v, i -> i.dropChance)
            .documentation("Chance (0 a 1) de recueillir DropItem.")
            .add()
            .append(new KeyedCodec<>("DropItem", Codec.STRING), (i, v) -> i.dropItem = v, i -> i.dropItem)
            .documentation("Objet recueilli (sang frais).")
            .add()
            .build();

    protected float bloodGain = 0.08f;
    protected float bonusDamage = 8f;
    protected float bonusHeal = 6f;
    protected float dropChance = 0.3f;
    protected String dropItem = "Ingredient_Nakasar_Blood";

    public BloodFeedInteraction() {
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> caster = AbilityAttributes.caster(context);
        Ref<EntityStore> target = context.getTargetEntity();
        if (buffer == null || caster == null || !caster.isValid() || target == null || caster.equals(target)
                || !Vampires.isLiving(target, buffer)) {
            return;
        }
        Vampire vampire = Vampires.of(caster, buffer);
        if (vampire != null) {
            vampire.addBlood(bloodGain);
            if (bonusDamage > 0f) {
                DamageCause physical = DamageCause.getAssetMap().getAsset("Physical");
                if (physical != null) {
                    DamageSystems.executeDamage(target, buffer,
                            new Damage(new Damage.EntitySource(caster), physical, bonusDamage));
                }
            }
            EntityStatMap stats = buffer.getComponent(caster, EntityStatMap.getComponentType());
            if (stats != null && bonusHeal > 0f) {
                stats.addStatValue(DefaultEntityStatTypes.getHealth(), bonusHeal);
            }
        }
        if (dropItem != null && !dropItem.isBlank() && buffer.getComponent(caster, Player.getComponentType()) != null
                && ThreadLocalRandom.current().nextFloat() < dropChance) {
            SimpleItemContainer.addOrDropItemStack(buffer, caster,
                    InventoryComponent.getCombined(buffer, caster, InventoryComponent.HOTBAR_STORAGE_BACKPACK),
                    new ItemStack(dropItem, 1));
        }
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
