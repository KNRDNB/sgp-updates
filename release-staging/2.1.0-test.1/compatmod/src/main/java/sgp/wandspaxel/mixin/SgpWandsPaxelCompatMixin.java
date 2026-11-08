package sgp.wandspaxel.mixin;

import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.tags.BlockTags;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.SnowLayerBlock;
import net.minecraft.world.level.block.TransparentBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.neoforge.common.ItemAbilities;
import net.neoforged.neoforge.common.ItemAbility;
import net.nicguzzo.wands.config.WandsConfig;
import net.nicguzzo.wands.utils.WandUtils;
import net.nicguzzo.wands.wand.Wand;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.Redirect;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import sgp.wandspaxel.PaxelIds;
import sgp.wandspaxel.PaxelRules;

@Mixin(Wand.class)
abstract class SgpWandsPaxelCompatMixin {
    @Shadow public Player player;
    @Shadow public Level level;
    @Shadow public CompoundTag player_data;
    @Shadow ItemStack digger_item;
    @Shadow public int digger_item_slot;
    @Shadow public boolean use;
    @Shadow public boolean has_axe;
    @Shadow public boolean has_shovel;

    @Unique private boolean sgp$restoreFlags;
    @Unique private boolean sgp$oldAxe;
    @Unique private boolean sgp$oldShovel;

    @Unique
    private static boolean sgp$isPaxel(ItemStack stack) {
        if (stack == null || stack.isEmpty()) return false;
        ResourceLocation id = BuiltInRegistries.ITEM.getKey(stack.getItem());
        return id != null && PaxelIds.isCreateIronworksPaxel(id.getNamespace(), id.getPath());
    }

    @Unique
    private int sgp$selectedPaxelSlot() {
        if (this.player == null || this.player_data == null) return -1;
        for (int slot : this.player_data.getIntArray("Tools")) {
            if (!PaxelRules.isToolMenuSlot(slot)) continue;
            ItemStack stack = this.player.getInventory().getItem(slot);
            if (sgp$isPaxel(stack)
                    && PaxelRules.hasSafeDurability(stack.getMaxDamage(), stack.getDamageValue())) {
                return slot;
            }
        }
        return -1;
    }

    /**
     * Exact Ironworks 4.0.3 paxels are TieredItem and do not have a TOOL
     * data component; Wands 3.0.5 unconditionally rejects them. Delegate
     * capability and tier/drop checks to the real Ironworks item instead.
     */
    @Inject(method = "can_dig", at = @At("RETURN"), cancellable = true)
    private void sgp$mining(BlockState state, boolean checkSpeed, ItemStack digger,
                            CallbackInfoReturnable<Boolean> result) {
        if (Boolean.TRUE.equals(result.getReturnValue()) || !sgp$isPaxel(digger)) return;
        boolean special = state.getBlock() instanceof TransparentBlock
                || (state.getBlock() instanceof SnowLayerBlock
                        && state.getValue(SnowLayerBlock.LAYERS) == 1)
                || WandsConfig.pickaxe_allowed.contains(state.getBlock())
                || WandsConfig.axe_allowed.contains(state.getBlock())
                || WandsConfig.shovel_allowed.contains(state.getBlock());
        boolean domain = state.is(BlockTags.MINEABLE_WITH_PICKAXE)
                || state.is(BlockTags.MINEABLE_WITH_AXE)
                || state.is(BlockTags.MINEABLE_WITH_SHOVEL);
        if (PaxelRules.canMine(domain,
                digger.getItem().isCorrectToolForDrops(digger, state),
                digger.getItem().getDestroySpeed(digger, state), special)) {
            result.setReturnValue(true);
        }
    }

    /** Respect Wands' selected Tools[] and all ordinary tool choices. */
    @Inject(method = "can_destroy_or_use", at = @At("RETURN"), cancellable = true)
    private void sgp$selectForUse(BlockState state, boolean checkSpeed,
                                  CallbackInfoReturnable<Boolean> result) {
        if (Boolean.TRUE.equals(result.getReturnValue()) || !this.use
                || !PaxelRules.canOfferUse(
                        WandUtils.can_axe_use(state), WandUtils.is_flattenable(state))) return;
        int slot = sgp$selectedPaxelSlot();
        if (slot < 0) return;
        this.digger_item = this.player.getInventory().getItem(slot);
        this.digger_item_slot = slot;
        result.setReturnValue(true);
    }

    @Inject(method = "place_block", at = @At("HEAD"))
    private void sgp$beforeUse(BlockPos pos, BlockState state,
                               CallbackInfoReturnable<Boolean> result) {
        this.sgp$restoreFlags = false;
        if (!this.use || this.level == null || sgp$selectedPaxelSlot() < 0) return;
        BlockState actual = this.level.getBlockState(pos);
        boolean axe = WandUtils.can_axe_use(actual);
        boolean shovel = WandUtils.is_flattenable(actual);
        if (!axe && !shovel) return;
        this.sgp$restoreFlags = true;
        this.sgp$oldAxe = this.has_axe;
        this.sgp$oldShovel = this.has_shovel;
        this.has_axe = axe || (this.has_axe && !shovel);
        this.has_shovel = shovel || this.has_shovel;
    }

    /**
     * No Ironworks paxel overrides useOn(), despite advertising NeoForge
     * AXE/SHOVEL abilities. Wands calls ItemStack.useOn directly. Apply only
     * the advertised transformations and leave Wands' single durability,
     * undo, XP, selected slot and sound machinery intact.
     */
    @Redirect(method = "place_block", at = @At(
            value = "INVOKE",
            target = "Lnet/minecraft/world/item/ItemStack;useOn(Lnet/minecraft/world/item/context/UseOnContext;)Lnet/minecraft/world/InteractionResult;"))
    private InteractionResult sgp$useAbility(ItemStack stack, UseOnContext ctx) {
        InteractionResult nativeResult = stack.useOn(ctx);
        if (nativeResult != InteractionResult.PASS || !this.use || !sgp$isPaxel(stack)) {
            return nativeResult;
        }
        Level world = ctx.getLevel();
        BlockPos pos = ctx.getClickedPos();
        BlockState before = world.getBlockState(pos);

        if (WandUtils.can_axe_use(before)) {
            for (ItemAbility ability : new ItemAbility[]{
                    ItemAbilities.AXE_STRIP, ItemAbilities.AXE_SCRAPE, ItemAbilities.AXE_WAX_OFF}) {
                if (!stack.canPerformAction(ability)) continue;
                BlockState modified = before.getToolModifiedState(ctx, ability, false);
                if (modified != null && !modified.equals(before)
                        && world.setBlockAndUpdate(pos, modified)) {
                    return InteractionResult.SUCCESS;
                }
            }
        }
        if (WandUtils.is_flattenable(before)
                && world.getBlockState(pos.above()).isAir()
                && stack.canPerformAction(ItemAbilities.SHOVEL_FLATTEN)) {
            BlockState modified = before.getToolModifiedState(
                    ctx, ItemAbilities.SHOVEL_FLATTEN, false);
            if (modified != null && !modified.equals(before)
                    && world.setBlockAndUpdate(pos, modified)) {
                world.playSound(null, pos, SoundEvents.SHOVEL_FLATTEN, SoundSource.BLOCKS, 1, 1);
                return InteractionResult.SUCCESS;
            }
        }
        return InteractionResult.PASS;
    }

    @Inject(method = "place_block", at = @At("RETURN"))
    private void sgp$afterUse(BlockPos pos, BlockState state,
                              CallbackInfoReturnable<Boolean> result) {
        if (this.sgp$restoreFlags) {
            this.has_axe = this.sgp$oldAxe;
            this.has_shovel = this.sgp$oldShovel;
            this.sgp$restoreFlags = false;
        }
    }
}
