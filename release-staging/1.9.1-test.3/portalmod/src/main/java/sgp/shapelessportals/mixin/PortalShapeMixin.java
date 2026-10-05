package sgp.shapelessportals.mixin;

import java.util.HashSet;
import java.util.List;
import java.util.Set;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.LevelAccessor;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.NetherPortalBlock;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.portal.PortalShape;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import sgp.shapelessportals.PortalFrameRules;
import sgp.shapelessportals.util.HashSetQueue;

@Mixin(PortalShape.class)
public abstract class PortalShapeMixin {
    @Unique
    private static final int SGP$MAX_PORTAL_BLOCKS = 2304;

    @Shadow @Final private LevelAccessor level;
    @Shadow @Final private Direction.Axis axis;
    @Shadow @Final private Direction rightDir;
    @Shadow @Final private static BlockBehaviour.StatePredicate FRAME;

    @Unique private boolean sgp$scanned;
    @Unique private boolean sgp$valid;
    @Unique private int sgp$portalBlockCount;
    @Unique private Set<BlockPos> sgp$portalPositions = new HashSet<>();

    @Inject(method = "<init>", at = @At("TAIL"))
    private void sgp$scanAnyShape(
            LevelAccessor level,
            BlockPos startPos,
            Direction.Axis axis,
            CallbackInfo ci) {
        this.sgp$scanned = true;
        this.sgp$valid = false;
        this.sgp$portalBlockCount = 0;
        this.sgp$portalPositions.clear();

        Set<BlockPos> framePositions = new HashSet<>();
        HashSetQueue<BlockPos> pending = new HashSetQueue<>();
        boolean[] minimumHeightFound = {false};

        List<Direction> directions = List.of(
                Direction.DOWN,
                Direction.UP,
                this.rightDir,
                this.rightDir.getOpposite());

        pending.push(startPos.immutable());

        while (!pending.isEmpty()) {
            BlockPos pos = pending.pop();
            if (pos == null || this.sgp$portalPositions.contains(pos) || framePositions.contains(pos)) {
                continue;
            }

            if (this.level.isOutsideBuildHeight(pos)) {
                return;
            }

            BlockState state = this.level.getBlockState(pos);
            boolean interior = PortalShapeAccessor.sgp$isEmpty(state);
            boolean frame = FRAME.test(state, this.level, pos) || PortalFrameRules.isPortalFrame(state, this.level, pos);

            if (!interior && !frame) {
                return;
            }

            if (frame) {
                framePositions.add(pos.immutable());
                continue;
            }

            BlockPos immutable = pos.immutable();
            this.sgp$portalPositions.add(immutable);
            if (this.sgp$portalPositions.size() > SGP$MAX_PORTAL_BLOCKS) {
                this.sgp$portalPositions.clear();
                return;
            }

            if (state.is(Blocks.NETHER_PORTAL)) {
                this.sgp$portalBlockCount++;
            }

            if (!minimumHeightFound[0] &&
                    (this.sgp$portalPositions.contains(immutable.above())
                            || this.sgp$portalPositions.contains(immutable.below()))) {
                minimumHeightFound[0] = true;
            }

            for (Direction direction : directions) {
                BlockPos neighbor = immutable.relative(direction);
                if (!this.sgp$portalPositions.contains(neighbor) && !framePositions.contains(neighbor)) {
                    pending.push(neighbor);
                }
            }
        }

        this.sgp$valid = minimumHeightFound[0] && !this.sgp$portalPositions.isEmpty();
    }

    @Inject(method = "isValid", at = @At("HEAD"), cancellable = true)
    private void sgp$isValid(CallbackInfoReturnable<Boolean> cir) {
        if (this.sgp$scanned) {
            cir.setReturnValue(this.sgp$valid);
        }
    }

    @Inject(method = "isComplete", at = @At("HEAD"), cancellable = true)
    private void sgp$isComplete(CallbackInfoReturnable<Boolean> cir) {
        if (this.sgp$scanned) {
            cir.setReturnValue(this.sgp$valid
                    && this.sgp$portalPositions.size() == this.sgp$portalBlockCount);
        }
    }

    @Inject(method = "createPortalBlocks", at = @At("HEAD"), cancellable = true)
    private void sgp$createPortalBlocks(CallbackInfo ci) {
        if (!this.sgp$scanned || !this.sgp$valid) {
            return;
        }

        BlockState portalState = Blocks.NETHER_PORTAL.defaultBlockState()
                .setValue(NetherPortalBlock.AXIS, this.axis);

        for (BlockPos pos : this.sgp$portalPositions) {
            this.level.setBlock(
                    pos,
                    portalState,
                    Block.UPDATE_CLIENTS | Block.UPDATE_KNOWN_SHAPE);
        }
        ci.cancel();
    }
}
