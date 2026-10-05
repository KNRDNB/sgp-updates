package sgp.shapelessportals.mixin;

import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobSpawnType;
import net.minecraft.world.level.block.NetherPortalBlock;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

@Mixin(NetherPortalBlock.class)
abstract class NetherPortalBlockMixin {
    @Redirect(
            method = "randomTick",
            at = @At(
                    value = "INVOKE",
                    target = "Lnet/minecraft/world/entity/EntityType;spawn(Lnet/minecraft/server/level/ServerLevel;Lnet/minecraft/core/BlockPos;Lnet/minecraft/world/entity/MobSpawnType;)Lnet/minecraft/world/entity/Entity;"))
    private Entity sgp$preventPortalGeneratedZombifiedPiglin(
            EntityType<?> entityType,
            ServerLevel level,
            BlockPos pos,
            MobSpawnType spawnType) {
        if (entityType == EntityType.ZOMBIFIED_PIGLIN) {
            return null;
        }
        return entityType.spawn(level, pos, spawnType);
    }
}
