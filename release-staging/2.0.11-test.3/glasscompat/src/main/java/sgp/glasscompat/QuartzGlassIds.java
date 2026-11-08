package sgp.glasscompat;

import java.util.HashSet;
import java.util.Set;

public final class QuartzGlassIds {
    private static final String[] GROUPS = {
            "quartz_glass",
            "quartz_glass_framed",
            "quartz_glass_pane",
            "quartz_glass_framed_pane"
    };

    private static final String[] COLORS = {
            "white","orange","magenta","light_blue","yellow","lime","pink","gray",
            "light_gray","cyan","purple","blue","brown","green","red","black"
    };

    public static final Set<String> PATHS = build();

    private QuartzGlassIds() {}

    private static Set<String> build() {
        Set<String> out = new HashSet<>();
        for (String group : GROUPS) {
            out.add(group);
            for (String color : COLORS) {
                out.add(group + "_" + color);
            }
        }
        return Set.copyOf(out);
    }

    public static boolean isQuartzGlassFamily(String namespace, String path) {
        return "betternether".equals(namespace) && PATHS.contains(path);
    }
}
