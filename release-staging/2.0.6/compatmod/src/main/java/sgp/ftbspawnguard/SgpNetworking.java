package sgp.ftbspawnguard;

import com.mojang.logging.LogUtils;
import net.minecraft.server.level.ServerPlayer;
import net.neoforged.neoforge.network.event.RegisterPayloadHandlersEvent;
import net.neoforged.neoforge.network.handling.IPayloadContext;
import org.slf4j.Logger;

final class SgpNetworking {
    private static final Logger LOGGER = LogUtils.getLogger();

    private SgpNetworking() {
    }

    static void register(RegisterPayloadHandlersEvent event) {
        event.registrar("1").playToServer(
                ManualTogglePayload.TYPE,
                ManualTogglePayload.STREAM_CODEC,
                SgpNetworking::handleManualToggle
        );
        LOGGER.info("[SGP Auto Protect] Registered command-spam-free manual toggle payload");
    }

    private static void handleManualToggle(ManualTogglePayload payload, IPayloadContext context) {
        if (!(context.player() instanceof ServerPlayer player)) {
            return;
        }

        try {
            SpawnGuardAccess.executeGuiToggle(player, payload.chunkX(), payload.chunkZ());
        } catch (Throwable t) {
            LOGGER.error("[SGP Auto Protect] Manual Mob Control toggle failed for chunk {},{}",
                    payload.chunkX(), payload.chunkZ(), t);
        }
    }
}
