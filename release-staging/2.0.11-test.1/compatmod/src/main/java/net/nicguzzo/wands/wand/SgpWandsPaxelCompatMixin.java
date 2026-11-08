package net.nicguzzo.wands.wand;

import net.minecraft.core.BlockPos;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.Tool;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.SnowLayerBlock;
import net.minecraft.world.level.block.TransparentBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.nicguzzo.wands.config.WandsConfig;
import net.nicguzzo.wands.utils.WandUtils;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import sgp.wandspaxel.PaxelIds;

@Mixin(Wand.class)
abstract class SgpWandsPaxelCompatMixin {
    @Shadow ItemStack digger_item;
    @Shadow public int digger_item_slot;
    @Shadow Wand.WandTool[] tools;
    @Shadow public boolean use;
    @Shadow public Level level;
    @Shadow public boolean has_axe;
    @Shadow public boolean has_shovel;

    @Unique private boolean sgp$restoreToolFlags;
    @Unique private boolean sgp$oldHasAxe;
    @Unique private boolean sgp$oldHasShovel;

    @Unique
    private static boolean sgp$isPaxel(ItemStack stack) {
        if (stack == null || stack.isEmpty()) {
            return false;
        }
        ResourceLocation id = BuiltInRegistries.ITEM.getKey(stack.getItem());
        return id != null && PaxelIds.isCreateIronworksPaxel(id.getNamespace(), id.getPath());
    }

    @Unique
    private static boolean sgp$wouldBreak(ItemStack stack) {
        if (stack == null || stack.isEmpty()) {
            return true;
        }
        return (stack.getMaxDamage() - stack.getDamageValue()) <= 5;
    }

    @Unique
    private int sgp$findUsablePaxelSlot() {
        if (this.tools == null) {
            return -1;
        }
        for (int i = 0; i < this.tools.length; i++) {
            Wand.WandTool tool = this.tools[i];
            if (tool != null && !tool.empty && sgp$isPaxel(tool.tool) && !sgp$wouldBreak(tool.tool)) {
                return i;
            }
        }
        return -1;
    }

    @Inject(method = "can_dig", at = @At("RETURN"), cancellable = true)
    private void sgp$preserveWandsDigSemantics(
            BlockState state,
            boolean checkSpeed,
            ItemStack digger,
            CallbackInfoReturnable<Boolean> cir
    ) {
        if (Boolean.TRUE.equals(cir.getReturnValue()) || !sgp$isPaxel(digger)) {
            return;
        }

        Tool tool = digger.get(DataComponents.TOOL);
        if (tool == null) {
            return;
        }

        if (!checkSpeed) {
            cir.setReturnValue(true);
            return;
        }

        boolean glass = state.getBlock() instanceof TransparentBlock;
        boolean snowLayer = state.getBlock() instanceof SnowLayerBlock snow
                && state.getValue(SnowLayerBlock.LAYERS) == 1;
        boolean explicitlyAllowed =
                WandsConfig.pickaxe_allowed.contains(state.getBlock())
                || WandsConfig.axe_allowed.contains(state.getBlock())
                || WandsConfig.shovel_allowed.contains(state.getBlock());

        float destroySpeed = digger.getItem().getDestroySpeed(digger, state);
        boolean correctForDrops = tool.isCorrectForDrops(state);

        if ((destroySpeed > 1.0F && correctForDrops) || glass || snowLayer || explicitlyAllowed) {
            cir.setReturnValue(true);
        }
    }

    @Inject(method = "can_destroy_or_use", at = @At("RETURN"), cancellable = true)
    private void sgp$allowPaxelAxeAndShovelUse(
            BlockState state,
            boolean checkSpeed,
            CallbackInfoReturnable<Boolean> cir
    ) {
        if (Boolean.TRUE.equals(cir.getReturnValue()) || !this.use) {
            return;
        }

        if (!WandUtils.can_axe_use(state) && !WandUtils.is_flattenable(state)) {
            return;
        }

        int slot = sgp$findUsablePaxelSlot();
        if (slot >= 0) {
            this.digger_item = this.tools[slot].tool;
            this.digger_item_slot = slot;
            cir.setReturnValue(true);
        }
    }

    @Inject(method = "place_block", at = @At("HEAD"))
    private void sgp$preparePaxelUseFlags(
            BlockPos blockPos,
            BlockState state,
            CallbackInfoReturnable<Boolean> cir
    ) {
        this.sgp$restoreToolFlags = false;
        this.sgp$oldHasAxe = this.has_axe;
        this.sgp$oldHasShovel = this.has_shovel;

        if (!this.use || sgp$findUsablePaxelSlot() < 0) {
            return;
        }

        BlockState target = this.level.getBlockState(blockPos);
        boolean axeAction = WandUtils.can_axe_use(target);
        boolean shovelAction = WandUtils.is_flattenable(target);

        if (axeAction || shovelAction) {
            this.sgp$restoreToolFlags = true;
            if (axeAction) {
                this.has_axe = true;
            }
            if (shovelAction) {
                this.has_shovel = true;
            }
        }
    }

    @Inject(method = "place_block", at = @At("RETURN"))
    private void sgp$restorePaxelUseFlags(
            BlockPos blockPos,
            BlockState state,
            CallbackInfoReturnable<Boolean> cir
    ) {
        if (this.sgp$restoreToolFlags) {
            this.has_axe = this.sgp$oldHasAxe;
            this.has_shovel = this.sgp$oldHasShovel;
            this.sgp$restoreToolFlags = false;
        }
    }
}
