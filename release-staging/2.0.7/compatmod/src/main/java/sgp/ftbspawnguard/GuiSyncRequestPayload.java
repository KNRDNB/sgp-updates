package sgp.ftbspawnguard;

import io.netty.buffer.ByteBuf;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.ResourceLocation;

public record GuiSyncRequestPayload(int chunkX, int chunkZ) implements CustomPacketPayload {
    public static final Type<GuiSyncRequestPayload> TYPE = new Type<>(
            ResourceLocation.fromNamespaceAndPath(SgpFtbSpawnGuardAutoProtect.MOD_ID, "gui_sync_request")
    );

    public static final StreamCodec<ByteBuf, GuiSyncRequestPayload> STREAM_CODEC = StreamCodec.composite(
            ByteBufCodecs.VAR_INT,
            GuiSyncRequestPayload::chunkX,
            ByteBufCodecs.VAR_INT,
            GuiSyncRequestPayload::chunkZ,
            GuiSyncRequestPayload::new
    );

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return TYPE;
    }
}
