package sgp.ftbspawnguard;

import io.netty.buffer.ByteBuf;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.ResourceLocation;

public record ManualTogglePayload(int chunkX, int chunkZ) implements CustomPacketPayload {
    public static final Type<ManualTogglePayload> TYPE = new Type<>(
            ResourceLocation.fromNamespaceAndPath(SgpFtbSpawnGuardAutoProtect.MOD_ID, "manual_toggle")
    );

    public static final StreamCodec<ByteBuf, ManualTogglePayload> STREAM_CODEC = StreamCodec.composite(
            ByteBufCodecs.VAR_INT,
            ManualTogglePayload::chunkX,
            ByteBufCodecs.VAR_INT,
            ManualTogglePayload::chunkZ,
            ManualTogglePayload::new
    );

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return TYPE;
    }
}
