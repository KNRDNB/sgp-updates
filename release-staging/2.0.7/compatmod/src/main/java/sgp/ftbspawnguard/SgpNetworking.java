package sgp.ftbspawnguard;

import com.mojang.logging.LogUtils;
import net.minecraft.server.level.ServerPlayer;
import net.neoforged.neoforge.network.event.RegisterPayloadHandlersEvent;
import net.neoforged.neoforge.network.handling.IPayloadContext;
import net.neoforged.neoforge.network.registration.PayloadRegistrar;
import org.slf4j.Logger;

final class SgpNetworking {
    private static final Logger LOGGER = LogUtils.getLogger();

    private SgpNetworking() {
    }

    static void register(RegisterPayloadHandlersEvent event) {
        PayloadRegistrar registrar = event.registrar("2");
        registrar.playToServer(
                ManualTogglePayload.TYPE,
                ManualTogglePayload.STREAM_CODEC,
                SgpNetworking::handleManualToggle
        );
        registrar.playToServer(
                GuiSyncRequestPayload.TYPE,
                GuiSyncRequestPayload.STREAM_CODEC,
                SgpNetworking::handleGuiSync
        );
        LOGGER.info("[SGP Auto Protect] Registered command-spam-free Mob Control toggle + GUI sync payloads");
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

    private static void handleGuiSync(GuiSyncRequestPayload payload, IPayloadContext context) {
        if (!(context.player() instanceof ServerPlayer player)) {
            return;
        }

        try {
            SpawnGuardAccess.executeGuiSync(player, payload.chunkX(), payload.chunkZ());
        } catch (Throwable t) {
            LOGGER.error("[SGP Auto Protect] Mob Control GUI sync failed for origin chunk {},{}",
                    payload.chunkX(), payload.chunkZ(), t);
        }
    }
}
