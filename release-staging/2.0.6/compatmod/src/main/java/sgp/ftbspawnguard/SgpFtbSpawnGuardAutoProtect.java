package sgp.ftbspawnguard;

import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;

@Mod(SgpFtbSpawnGuardAutoProtect.MOD_ID)
public final class SgpFtbSpawnGuardAutoProtect {
    public static final String MOD_ID = "sgp_ftb_spawn_guard_auto_protect";

    public SgpFtbSpawnGuardAutoProtect(IEventBus modEventBus) {
        AutoProtectHook.register();
        modEventBus.addListener(SgpNetworking::register);
    }
}
