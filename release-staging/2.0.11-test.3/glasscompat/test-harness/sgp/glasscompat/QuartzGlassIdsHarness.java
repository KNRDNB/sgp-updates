package sgp.glasscompat;

public final class QuartzGlassIdsHarness {
    public static void main(String[] args) {
        assert QuartzGlassIds.PATHS.size() == 68 : QuartzGlassIds.PATHS.size();
        assert QuartzGlassIds.isQuartzGlassFamily("betternether", "quartz_glass");
        assert QuartzGlassIds.isQuartzGlassFamily("betternether", "quartz_glass_black");
        assert QuartzGlassIds.isQuartzGlassFamily("betternether", "quartz_glass_framed_red");
        assert QuartzGlassIds.isQuartzGlassFamily("betternether", "quartz_glass_pane_cyan");
        assert QuartzGlassIds.isQuartzGlassFamily("betternether", "quartz_glass_framed_pane_light_blue");
        assert !QuartzGlassIds.isQuartzGlassFamily("betternether", "obsidian_glass");
        assert !QuartzGlassIds.isQuartzGlassFamily("betternether", "blue_obsidian_glass_pane");
        assert !QuartzGlassIds.isQuartzGlassFamily("minecraft", "glass");
        System.out.println("QUARTZ_GLASS_68_ID_MATRIX_PASS");
    }
}
