package sgp.apotheosissoulbound.mixin;

import net.minecraft.core.Holder;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.enchantment.Enchantment;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(targets = "dev.shadowsoffire.apotheosis.item.PotionCharmItem", remap = false)
abstract class PotionCharmItemMixin {
    private static final ResourceLocation SGP$SOULBOUND =
            ResourceLocation.fromNamespaceAndPath("soulbound", "soulbound");

    @Inject(method = "supportsEnchantment", at = @At("HEAD"), cancellable = true, remap = false)
    private void sgp$allowOnlySoulbound(
            ItemStack stack,
            Holder<Enchantment> enchantment,
            CallbackInfoReturnable<Boolean> cir) {
        if (enchantment.unwrapKey()
                .map(key -> key.location().equals(SGP$SOULBOUND))
                .orElse(false)) {
            cir.setReturnValue(true);
        }
    }
}
