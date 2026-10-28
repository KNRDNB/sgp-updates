package sgp.ftbspawnguard;

import java.lang.reflect.Constructor;
import java.lang.reflect.Method;

final class SpawnGuardAccess {
    private static final String BASE = "org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.";

    private SpawnGuardAccess() {
    }

    static Object contextFromClaim(Object sourceStack, Object claimedChunk) throws Exception {
        if (sourceStack == null || claimedChunk == null) {
            return null;
        }

        Object level = callNoArgs(sourceStack, "getLevel");
        Object pos = callNoArgs(claimedChunk, "getPos");
        Object teamData = callNoArgs(claimedChunk, "getTeamData");
        if (level == null || pos == null || teamData == null) {
            return null;
        }

        int x = readInt(pos, "x", "getX");
        int z = readInt(pos, "z", "getZ");

        Object team = callNoArgs(teamData, "getTeam");
        if (team == null) {
            return null;
        }
        Object teamId = callNoArgsAny(team, "getTeamId", "getId");
        if (teamId == null) {
            return null;
        }

        Object dimensionKey = callNoArgs(level, "dimension");
        if (dimensionKey == null) {
            return null;
        }

        Class<?> claimContextClass = Class.forName(BASE + "ClaimContext");
        Method resourceKeyId = claimContextClass.getDeclaredMethod("resourceKeyId", Object.class);
        resourceKeyId.setAccessible(true);
        String plainDimension = (String) resourceKeyId.invoke(null, dimensionKey);
        if (plainDimension == null) {
            return null;
        }

        Class<?> worldScopeClass = Class.forName(BASE + "WorldScope");
        Method scopeDimension = worldScopeClass.getDeclaredMethod("scopeDimension", Object.class, String.class);
        scopeDimension.setAccessible(true);
        String scopedDimension = (String) scopeDimension.invoke(null, level, plainDimension);
        if (scopedDimension == null) {
            return null;
        }

        Constructor<?> constructor = claimContextClass.getDeclaredConstructor(
                String.class, int.class, int.class, String.class, Object.class
        );
        constructor.setAccessible(true);
        return constructor.newInstance(scopedDimension, x, z, String.valueOf(teamId), teamData);
    }

    static boolean setProtected(Object claimContext, boolean enabled) throws Exception {
        if (claimContext == null) {
            return false;
        }

        Class<?> claimContextClass = Class.forName(BASE + "ClaimContext");
        Class<?> storeClass = Class.forName(BASE + "ProtectionStore");
        Method set = storeClass.getDeclaredMethod("set", claimContextClass, boolean.class);
        set.setAccessible(true);
        return (boolean) set.invoke(null, claimContext, enabled);
    }

    static int executeGuiToggle(Object player, int x, int z) throws Exception {
        if (player == null) {
            return 0;
        }

        Object level = callNoArgsAny(player, "serverLevel", "level");
        if (level == null) {
            return 0;
        }

        Class<?> claimContextClass = Class.forName(BASE + "ClaimContext");
        Method atChunk = claimContextClass.getDeclaredMethod("atChunk", Object.class, int.class, int.class);
        atChunk.setAccessible(true);
        Object claimContext = atChunk.invoke(null, level, x, z);
        if (claimContext == null) {
            return 0;
        }

        Class<?> commandBridgeClass = Class.forName(BASE + "CommandBridge");
        Method executeClaim = commandBridgeClass.getDeclaredMethod(
                "executeClaim", Object.class, claimContextClass, String.class
        );
        executeClaim.setAccessible(true);
        return (int) executeClaim.invoke(null, player, claimContext, "gui_toggle");
    }

    private static Object callNoArgs(Object target, String name) throws Exception {
        Method m = target.getClass().getMethod(name);
        m.setAccessible(true);
        return m.invoke(target);
    }

    private static Object callNoArgsAny(Object target, String... names) throws Exception {
        Exception last = null;
        for (String name : names) {
            try {
                return callNoArgs(target, name);
            } catch (Exception e) {
                last = e;
            }
        }
        if (last != null) {
            throw last;
        }
        return null;
    }

    private static int readInt(Object target, String primary, String fallback) throws Exception {
        try {
            Method m = target.getClass().getMethod(primary);
            m.setAccessible(true);
            return ((Number) m.invoke(target)).intValue();
        } catch (NoSuchMethodException first) {
            Method m = target.getClass().getMethod(fallback);
            m.setAccessible(true);
            return ((Number) m.invoke(target)).intValue();
        }
    }
}
