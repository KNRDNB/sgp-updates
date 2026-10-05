package sgp.shapelessportals.mixin;

import net.minecraft.core.BlockPos;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.block.BaseFireBlock;
import net.minecraft.world.level.block.state.BlockState;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;
import sgp.shapelessportals.PortalFrameRules;

@Mixin(BaseFireBlock.class)
abstract class BaseFireBlockMixin {
    @Redirect(
            method = "isPortal",
            at = @At(
                    value = "INVOKE",
                    target = "Lnet/minecraft/world/level/block/state/BlockState;isPortalFrame(Lnet/minecraft/world/level/BlockGetter;Lnet/minecraft/core/BlockPos;)Z"))
    private static boolean sgp$useSharedPortalFrameRule(
            BlockState state,
            BlockGetter level,
            BlockPos pos) {
        return PortalFrameRules.isPortalFrame(state, level, pos);
    }
}
