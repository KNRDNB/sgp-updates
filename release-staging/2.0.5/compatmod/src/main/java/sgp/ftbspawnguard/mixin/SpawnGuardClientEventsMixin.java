package sgp.ftbspawnguard.mixin;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;
import sgp.ftbspawnguard.ClientToggleTransport;

@Mixin(targets = "org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.ClientEvents", remap = false)
abstract class SpawnGuardClientEventsMixin {
    @Redirect(
            method = "pressed",
            at = @At(
                    value = "INVOKE",
                    target = "Lorg/ftb_chunks_mobs_spawn_control/ftb_chunks_mobs_spawn_control/ClientEvents;send(Ljava/lang/String;)Z",
                    remap = false
            )
    )
    private static boolean sgp$replaceSingleToggleTransport(String command) {
        return ClientToggleTransport.replaceSingleToggle(command);
    }
}
