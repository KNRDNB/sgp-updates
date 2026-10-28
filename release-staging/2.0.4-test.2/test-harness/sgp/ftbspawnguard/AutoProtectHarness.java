package sgp.ftbspawnguard;

import dev.ftb.mods.ftbchunks.api.event.ClaimedChunkEvent;

import java.lang.reflect.Field;
import java.lang.reflect.Method;

public final class AutoProtectHarness {
    public static void main(String[] args) throws Exception {
        FakeLevel level = new FakeLevel("test-level");
        FakeSource source = new FakeSource(level);
        FakeClaimedChunk chunk = new FakeClaimedChunk(new FakePos(12, -34));

        AutoProtectHook.register();
        ClaimedChunkEvent.AFTER_CLAIM.listener().after(source, chunk);

        Class<?> store = Class.forName(
                "org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.ProtectionStore");
        assertBoolean(store, "enabled", true);
        assertInt(store, "calls", 1);
        assertInt(store, "lastX", 12);
        assertInt(store, "lastZ", -34);
        assertSame(store, "lastLevel", level);

        Field enabled = store.getDeclaredField("enabled");
        enabled.setAccessible(true);
        enabled.setBoolean(null, false);

        // No claim event means a manual user override remains untouched.
        assertBoolean(store, "enabled", false);
        assertInt(store, "calls", 1);

        // Re-claim/new claim event enables protection again.
        ClaimedChunkEvent.AFTER_CLAIM.listener().after(source, chunk);
        assertBoolean(store, "enabled", true);
        assertInt(store, "calls", 2);

        // Double registration must be harmless.
        AutoProtectHook.register();
        ClaimedChunkEvent.AFTER_CLAIM.listener().after(source, chunk);
        assertInt(store, "calls", 3);

        System.out.println("SGP_FTB_AUTO_PROTECT_SYNTHETIC_PASS");
    }

    private static void assertBoolean(Class<?> type, String fieldName, boolean expected) throws Exception {
        Field f = type.getDeclaredField(fieldName);
        f.setAccessible(true);
        boolean actual = f.getBoolean(null);
        if (actual != expected) throw new AssertionError(fieldName + "=" + actual + " expected " + expected);
    }

    private static void assertInt(Class<?> type, String fieldName, int expected) throws Exception {
        Field f = type.getDeclaredField(fieldName);
        f.setAccessible(true);
        int actual = f.getInt(null);
        if (actual != expected) throw new AssertionError(fieldName + "=" + actual + " expected " + expected);
    }

    private static void assertSame(Class<?> type, String fieldName, Object expected) throws Exception {
        Field f = type.getDeclaredField(fieldName);
        f.setAccessible(true);
        Object actual = f.get(null);
        if (actual != expected) throw new AssertionError(fieldName + " did not preserve level identity");
    }

    public record FakePos(int x, int z) {
    }

    public static final class FakeClaimedChunk {
        private final FakePos pos;
        FakeClaimedChunk(FakePos pos) { this.pos = pos; }
        public FakePos getPos() { return pos; }
    }

    public static final class FakeSource {
        private final FakeLevel level;
        FakeSource(FakeLevel level) { this.level = level; }
        public FakeLevel getLevel() { return level; }
    }

    public record FakeLevel(String id) {
    }
}
