package sgp.shapelessportals.mixin;

import net.minecraft.core.BlockPos;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.block.BaseFireBlock;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

@Mixin(BaseFireBlock.class)
abstract class BaseFireBlockMixin {
    @Redirect(
            method = "isPortal",
            at = @At(
                    value = "INVOKE",
                    target = "Lnet/minecraft/world/level/block/state/BlockState;isPortalFrame(Lnet/minecraft/world/level/BlockGetter;Lnet/minecraft/core/BlockPos;)Z"))
    private static boolean sgp$allowCryingObsidianPortalFrame(
            BlockState state,
            BlockGetter level,
            BlockPos pos) {
        return state.is(Blocks.CRYING_OBSIDIAN) || state.isPortalFrame(level, pos);
    }
}
