package sgp.glasscompat.mixin;

import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.tags.FluidTags;
import net.minecraft.world.level.BlockAndTintGetter;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.material.FluidState;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import sgp.glasscompat.QuartzGlassIds;

@Mixin(targets = "net.caffeinemc.mods.sodium.neoforge.block.NeoForgeBlockAccess", remap = false)
abstract class SodiumNeoForgeBlockAccessMixin {
    @Inject(method = "shouldShowFluidOverlay", at = @At("HEAD"), cancellable = true, remap = false)
    private void sgp$useWaterOverlayForQuartzGlass(
            BlockState block,
            BlockAndTintGetter level,
            BlockPos pos,
            FluidState fluidState,
            CallbackInfoReturnable<Boolean> cir
    ) {
        if (!fluidState.is(FluidTags.WATER)) {
            return;
        }

        ResourceLocation id = BuiltInRegistries.BLOCK.getKey(block.getBlock());
        if (id != null && QuartzGlassIds.isQuartzGlassFamily(id.getNamespace(), id.getPath())) {
            cir.setReturnValue(true);
        }
    }
}
