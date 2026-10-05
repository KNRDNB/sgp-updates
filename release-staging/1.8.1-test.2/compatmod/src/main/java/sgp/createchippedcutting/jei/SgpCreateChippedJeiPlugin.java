package sgp.createchippedcutting.jei;

import java.util.List;

import com.simibubi.create.content.kinetics.saw.CuttingRecipe;

import mezz.jei.api.IModPlugin;
import mezz.jei.api.JeiPlugin;
import mezz.jei.api.recipe.RecipeType;
import mezz.jei.api.registration.IRecipeRegistration;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.crafting.RecipeHolder;
import sgp.createchippedcutting.DynamicCuttingBridge;
import sgp.createchippedcutting.SgpCreateChippedCutting;

@JeiPlugin
public final class SgpCreateChippedJeiPlugin implements IModPlugin {
    private static final ResourceLocation UID =
            ResourceLocation.fromNamespaceAndPath(SgpCreateChippedCutting.MOD_ID, "jei_plugin");

    private static final RecipeType<RecipeHolder<CuttingRecipe>> CREATE_SAWING =
            RecipeType.createRecipeHolderType(
                    ResourceLocation.fromNamespaceAndPath("create", "sawing"));

    @Override
    public ResourceLocation getPluginUid() {
        return UID;
    }

    @Override
    public void registerRecipes(IRecipeRegistration registration) {
        List<RecipeHolder<CuttingRecipe>> recipes = DynamicCuttingBridge.createJeiRecipes();
        registration.addRecipes(CREATE_SAWING, recipes);
    }
}
