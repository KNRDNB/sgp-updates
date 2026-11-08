package sgp.wandspaxel;

import java.util.Set;

public final class PaxelIdsHarness {
    public static void main(String[] args) {
        Set<String> exact = Set.of(
                "copper_paxel", "bronze_paxel", "brass_paxel", "iron_paxel",
                "gold_paxel", "diamond_paxel", "steel_paxel", "netherite_paxel"
        );
        assert PaxelIds.PATHS.equals(exact);
        for (String path : exact) {
            assert PaxelIds.isCreateIronworksPaxel("create_ironworks", path);
        }
        assert !PaxelIds.isCreateIronworksPaxel("create_ironworks", "steel_pickaxe");
        assert !PaxelIds.isCreateIronworksPaxel("create_ironworks", "steel_hoe");
        assert !PaxelIds.isCreateIronworksPaxel("other_mod", "steel_paxel");
        System.out.println("PAXEL_ID_MATRIX_PASS");
    }
}
