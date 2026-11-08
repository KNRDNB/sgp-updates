package sgp.wandspaxel;

import java.util.Set;

public final class PaxelIds {
    public static final Set<String> PATHS = Set.of(
            "copper_paxel",
            "bronze_paxel",
            "brass_paxel",
            "iron_paxel",
            "gold_paxel",
            "diamond_paxel",
            "steel_paxel",
            "netherite_paxel"
    );

    private PaxelIds() {
    }

    public static boolean isCreateIronworksPaxel(String namespace, String path) {
        return "create_ironworks".equals(namespace) && PATHS.contains(path);
    }
}
