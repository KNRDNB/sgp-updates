package sgp.createchippedcutting.mixin;

import java.util.List;
import java.util.function.Predicate;

import com.simibubi.create.content.kinetics.saw.SawBlockEntity;
import com.simibubi.create.content.processing.recipe.ProcessingInventory;
import com.simibubi.create.foundation.recipe.RecipeFinder;

import net.minecraft.world.item.crafting.Recipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.level.Level;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

import sgp.createchippedcutting.DynamicCuttingBridge;

@Mixin(value = SawBlockEntity.class, remap = false)
abstract class SawBlockEntityMixin {
    @Shadow
    public ProcessingInventory inventory;

    @Redirect(
            method = "getRecipes",
            at = @At(
                    value = "INVOKE",
                    target = "Lcom/simibubi/create/foundation/recipe/RecipeFinder;get(Ljava/lang/Object;Lnet/minecraft/world/level/Level;Ljava/util/function/Predicate;)Ljava/util/List;"
            ),
            remap = false
    )
    private List<RecipeHolder<? extends Recipe<?>>> sgp$appendDynamicChippedRecipes(
            Object cacheKey,
            Level level,
            Predicate<RecipeHolder<? extends Recipe<?>>> conditions) {
        List<RecipeHolder<? extends Recipe<?>>> base = RecipeFinder.get(cacheKey, level, conditions);
        return DynamicCuttingBridge.appendDynamicRecipes(level, inventory.getStackInSlot(0), base);
    }
}
