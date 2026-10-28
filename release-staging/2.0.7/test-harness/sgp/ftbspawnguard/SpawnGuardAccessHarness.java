package sgp.ftbspawnguard;

import java.lang.reflect.Field;
import java.util.UUID;

public final class SpawnGuardAccessHarness {
    public static void main(String[] args) throws Exception {
        FakeLevel level = new FakeLevel("minecraft:overworld");
        FakeSource source = new FakeSource(level);
        UUID teamId = UUID.fromString("cc80747f-70c0-46a8-9d0c-4d211077ad07");
        FakeTeamData teamData = new FakeTeamData(new FakeTeam(teamId));
        FakeClaimedChunk chunk = new FakeClaimedChunk(new FakePos(-66, 42), teamData);

        Object context = SpawnGuardAccess.contextFromClaim(source, chunk);
        if (context == null) throw new AssertionError("contextFromClaim returned null");
        assertField(context, "dimension", "@world=test|minecraft:overworld");
        assertField(context, "chunkX", -66);
        assertField(context, "chunkZ", 42);
        assertField(context, "teamId", teamId.toString());
        assertField(context, "teamData", teamData);

        if (!SpawnGuardAccess.setProtected(context, true)) throw new AssertionError("setProtected false");
        Class<?> store = Class.forName("org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.ProtectionStore");
        assertStatic(store, "enabled", true);
        assertStatic(store, "calls", 1);
        assertStatic(store, "last", context);

        FakePlayer player = new FakePlayer(level);
        int result = SpawnGuardAccess.executeGuiToggle(player, 7, -9);
        if (result != 1) throw new AssertionError("executeGuiToggle result=" + result);
        Class<?> bridge = Class.forName("org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.CommandBridge");
        assertStatic(bridge, "lastPlayer", player);
        assertStatic(bridge, "lastOperation", "gui_toggle");
        Object toggleContext = readStatic(bridge, "lastContext");
        assertField(toggleContext, "chunkX", 7);
        assertField(toggleContext, "chunkZ", -9);

        int syncResult = SpawnGuardAccess.executeGuiSync(player, -32, 48);
        if (syncResult != 1) throw new AssertionError("executeGuiSync result=" + syncResult);
        assertStatic(bridge, "lastGuiSyncPlayer", player);
        assertStatic(bridge, "lastGuiSyncLevel", level);
        assertStatic(bridge, "lastGuiSyncX", -32);
        assertStatic(bridge, "lastGuiSyncZ", 48);

        System.out.println("SGP_FTB_103_REFLECTION_HARNESS_PASS");
    }

    private static Object readStatic(Class<?> type, String name) throws Exception {
        Field f=type.getDeclaredField(name); f.setAccessible(true); return f.get(null);
    }

    private static void assertStatic(Class<?> type, String name, Object expected) throws Exception {
        Object actual=readStatic(type,name);
        if (!java.util.Objects.equals(actual, expected)) throw new AssertionError(name+"="+actual+" expected="+expected);
    }

    private static void assertField(Object target, String name, Object expected) throws Exception {
        Field f=target.getClass().getDeclaredField(name); f.setAccessible(true);
        Object actual=f.get(target);
        if (!java.util.Objects.equals(actual, expected)) throw new AssertionError(name+"="+actual+" expected="+expected);
    }

    public record FakeDimension(String id) {
        @Override public String toString() { return id; }
    }
    public record FakeLevel(String id) {
        public FakeDimension dimension() { return new FakeDimension(id); }
        @Override public String toString() { return id; }
    }
    public record FakeSource(FakeLevel level) { public FakeLevel getLevel() { return level; } }
    public record FakePlayer(FakeLevel level) { public FakeLevel serverLevel() { return level; } }
    public record FakePos(int x, int z) {}
    public record FakeTeam(UUID id) { public UUID getTeamId() { return id; } }
    public record FakeTeamData(FakeTeam team) { public FakeTeam getTeam() { return team; } }
    public record FakeClaimedChunk(FakePos pos, FakeTeamData teamData) {
        public FakePos getPos() { return pos; }
        public FakeTeamData getTeamData() { return teamData; }
    }
}
