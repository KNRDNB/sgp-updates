package sgp.createchippedcutting;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

import com.simibubi.create.content.kinetics.saw.CuttingRecipe;
import com.simibubi.create.content.processing.recipe.StandardProcessingRecipe;

import net.minecraft.core.Holder;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.tags.TagKey;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.Recipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.level.Level;

public final class DynamicCuttingBridge {
    private static final int PROCESSING_TIME = 50;

    private DynamicCuttingBridge() {
    }

    public static List<RecipeHolder<? extends Recipe<?>>> appendDynamicRecipes(
            Level level,
            ItemStack input,
            List<RecipeHolder<? extends Recipe<?>>> baseRecipes) {
        if (input.isEmpty())
            return baseRecipes;

        List<RecipeHolder<? extends Recipe<?>>> dynamic = createRuntimeRecipes(input);
        if (dynamic.isEmpty())
            return baseRecipes;

        ArrayList<RecipeHolder<? extends Recipe<?>>> merged =
                new ArrayList<>(baseRecipes.size() + dynamic.size());
        merged.addAll(baseRecipes);
        merged.addAll(dynamic);
        return merged;
    }

    static List<RecipeHolder<? extends Recipe<?>>> createRuntimeRecipes(ItemStack input) {
        ArrayList<RecipeHolder<? extends Recipe<?>>> recipes = new ArrayList<>();

        for (TagKey<Item> family : ChippedFamilies.TAGS) {
            if (!input.is(family))
                continue;

            BuiltInRegistries.ITEM.getTag(family).ifPresent(members -> {
                for (Holder<Item> holder : members) {
                    Item output = holder.value();
                    ResourceLocation outputId = BuiltInRegistries.ITEM.getKey(output);
                    if (!"chipped".equals(outputId.getNamespace()))
                        continue;

                    ResourceLocation recipeId = ResourceLocation.fromNamespaceAndPath(
                            SgpCreateChippedCutting.MOD_ID,
                            "dynamic/" + family.location().getPath() + "/" + outputId.getPath());

                    CuttingRecipe recipe =
                            new StandardProcessingRecipe.Builder<CuttingRecipe>(CuttingRecipe::new, recipeId)
                                    .require(input.getItem())
                                    .output(output)
                                    .duration(PROCESSING_TIME)
                                    .build();

                    recipes.add(new RecipeHolder<>(recipeId, recipe));
                }
            });
        }

        recipes.sort(Comparator.comparing(r -> r.id().toString()));
        return recipes;
    }

    public static List<RecipeHolder<CuttingRecipe>> createJeiRecipes() {
        ArrayList<RecipeHolder<CuttingRecipe>> recipes = new ArrayList<>();

        for (TagKey<Item> family : ChippedFamilies.TAGS) {
            BuiltInRegistries.ITEM.getTag(family).ifPresent(members -> {
                for (Holder<Item> holder : members) {
                    Item output = holder.value();
                    ResourceLocation outputId = BuiltInRegistries.ITEM.getKey(output);
                    if (!"chipped".equals(outputId.getNamespace()))
                        continue;

                    ResourceLocation recipeId = ResourceLocation.fromNamespaceAndPath(
                            SgpCreateChippedCutting.MOD_ID,
                            "jei/" + family.location().getPath() + "/" + outputId.getPath());

                    CuttingRecipe recipe =
                            new StandardProcessingRecipe.Builder<CuttingRecipe>(CuttingRecipe::new, recipeId)
                                    .require(family)
                                    .output(output)
                                    .duration(PROCESSING_TIME)
                                    .build();

                    recipes.add(new RecipeHolder<>(recipeId, recipe));
                }
            });
        }

        recipes.sort(Comparator.comparing(r -> r.id().toString()));
        return recipes;
    }
}
