package sgp.wandspaxel;

/** Pure decision rules shared by the mixin and offline regression harness. */
public final class PaxelRules {
    private PaxelRules() {}

    public static boolean isToolMenuSlot(int slot) {
        return slot >= 0 && slot < 36;
    }

    public static boolean hasSafeDurability(int maxDamage, int damage) {
        return maxDamage > 0 && damage >= 0 && maxDamage - damage > 5;
    }

    public static boolean canMine(boolean miningDomain, boolean realCorrectForDrops,
                                  float realSpeed, boolean wandsException) {
        return wandsException || (miningDomain && realCorrectForDrops && realSpeed > 1.0F);
    }

    public static boolean canOfferUse(boolean axeAction, boolean shovelAction) {
        return axeAction || shovelAction;
    }
}
