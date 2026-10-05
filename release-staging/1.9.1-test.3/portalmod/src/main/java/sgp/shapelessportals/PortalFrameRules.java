package sgp.shapelessportals;

import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.tags.TagKey;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;

public final class PortalFrameRules {
    public static final TagKey<Block> COMMON_PORTAL_FRAMES =
            TagKey.create(
                    Registries.BLOCK,
                    ResourceLocation.fromNamespaceAndPath("c", "nether_pframe"));

    private PortalFrameRules() {
    }

    public static boolean isPortalFrame(
            BlockState state,
            BlockGetter level,
            BlockPos pos) {
        return state.isPortalFrame(level, pos) || state.is(COMMON_PORTAL_FRAMES);
    }
}
