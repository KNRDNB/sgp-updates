package sgp.wandspaxel;

public final class PaxelRulesHarness {
    private static int checks;
    private static void ok(boolean b, String msg) {
        checks++;
        if (!b) throw new AssertionError(msg);
    }
    public static void main(String[] args) {
        String[] tiers = {"copper", "bronze", "brass", "iron",
                          "gold", "diamond", "steel", "netherite"};
        ok(PaxelIds.PATHS.size() == 8, "exact eight IDs");
        for (String t : tiers) {
            ok(PaxelIds.isCreateIronworksPaxel("create_ironworks", t + "_paxel"), t);
            ok(!PaxelIds.isCreateIronworksPaxel("minecraft", t + "_paxel"), "namespace");
            ok(!PaxelIds.isCreateIronworksPaxel("create_ironworks", t + "_axe"), "axe");
        }
        ok(!PaxelIds.isCreateIronworksPaxel("create_ironworks", "diamond_hammer"), "hammer");
        ok(!PaxelIds.isCreateIronworksPaxel("create_ironworks", "netherite_hoe"), "hoe");
        for (int i=0; i<36; i++) ok(PaxelRules.isToolMenuSlot(i), "menu slot " + i);
        for (int i : new int[]{-1,36,37,39,40,100}) {
            ok(!PaxelRules.isToolMenuSlot(i), "outside menu " + i);
        }
        ok(PaxelRules.hasSafeDurability(100,94), "6 left");
        ok(!PaxelRules.hasSafeDurability(100,95), "5 left");
        ok(!PaxelRules.hasSafeDurability(100,99), "1 left");
        ok(!PaxelRules.hasSafeDurability(0,0), "no damage");
        ok(!PaxelRules.hasSafeDurability(100,-1), "negative damage");
        ok(PaxelRules.canMine(true,true,4.0F,false), "normal mining");
        ok(!PaxelRules.canMine(true,false,4.0F,false), "tier-gated");
        ok(!PaxelRules.canMine(true,true,1.0F,false), "speed-gated");
        ok(!PaxelRules.canMine(false,true,4.0F,false), "no unrelated domain");
        ok(PaxelRules.canMine(false,false,0.0F,true), "Wands glass/snow/allowlist");
        ok(PaxelRules.canOfferUse(true,false), "axe");
        ok(PaxelRules.canOfferUse(false,true), "shovel");
        ok(!PaxelRules.canOfferUse(false,false), "not hoe/shears");
        System.out.println("PAXEL_103_RULE_MATRIX_PASS checks=" + checks);
    }
}
