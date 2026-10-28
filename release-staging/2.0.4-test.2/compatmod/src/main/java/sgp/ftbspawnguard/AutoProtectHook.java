package sgp.ftbspawnguard;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.logging.Level;
import java.util.logging.Logger;

final class AutoProtectHook {
    private static final Logger LOG = Logger.getLogger("SGP-FTB-Spawn-Guard-Auto-Protect");
    private static final AtomicBoolean REGISTERED = new AtomicBoolean();

    private AutoProtectHook() {
    }

    static void register() {
        if (!REGISTERED.compareAndSet(false, true)) {
            return;
        }

        try {
            Class<?> claimedChunkEvent = Class.forName("dev.ftb.mods.ftbchunks.api.event.ClaimedChunkEvent");
            Object afterClaim = claimedChunkEvent.getField("AFTER_CLAIM").get(null);
            Class<?> afterType = Class.forName("dev.ftb.mods.ftbchunks.api.event.ClaimedChunkEvent$After");

            Object listener = Proxy.newProxyInstance(
                    afterType.getClassLoader(),
                    new Class<?>[]{afterType},
                    (proxy, method, args) -> {
                        if (method.getDeclaringClass() == Object.class) {
                            return handleObjectMethod(proxy, method, args);
                        }

                        if ("after".equals(method.getName()) && args != null && args.length >= 2) {
                            protect(args[0], args[1]);
                        }
                        return null;
                    });

            Method register = findSingleArgumentMethod(afterClaim.getClass(), "register");
            register.invoke(afterClaim, listener);
            LOG.info("Registered AFTER_CLAIM auto-protect hook");
        } catch (Throwable t) {
            REGISTERED.set(false);
            LOG.log(Level.WARNING, "Unable to register FTB Chunks AFTER_CLAIM auto-protect hook; claims remain functional", t);
        }
    }

    private static Object handleObjectMethod(Object proxy, Method method, Object[] args) {
        return switch (method.getName()) {
            case "toString" -> "SGP AutoProtect AFTER_CLAIM listener";
            case "hashCode" -> System.identityHashCode(proxy);
            case "equals" -> proxy == (args == null || args.length == 0 ? null : args[0]);
            default -> null;
        };
    }

    private static void protect(Object source, Object claimedChunk) {
        try {
            Object pos = callNoArgs(claimedChunk, "getPos");
            int x = intValue(callNoArgs(pos, "x", "getX"));
            int z = intValue(callNoArgs(pos, "z", "getZ"));
            Object level = callNoArgs(source, "getLevel");

            Class<?> claimContextClass = Class.forName(
                    "org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.ClaimContext");
            Method atChunk = claimContextClass.getDeclaredMethod("atChunk", Object.class, int.class, int.class);
            atChunk.setAccessible(true);
            Object context = atChunk.invoke(null, level, x, z);
            if (context == null) {
                LOG.warning("Spawn Guard returned no ClaimContext for newly claimed chunk " + x + "," + z);
                return;
            }

            Class<?> protectionStoreClass = Class.forName(
                    "org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.ProtectionStore");
            Method set = protectionStoreClass.getDeclaredMethod("set", claimContextClass, boolean.class);
            set.setAccessible(true);
            set.invoke(null, context, true);
        } catch (Throwable t) {
            LOG.log(Level.WARNING, "Could not auto-enable Spawn Guard for a newly claimed chunk; the claim itself is unchanged", t);
        }
    }

    private static Method findSingleArgumentMethod(Class<?> type, String name) throws NoSuchMethodException {
        for (Method method : type.getMethods()) {
            if (name.equals(method.getName()) && method.getParameterCount() == 1) {
                return method;
            }
        }
        throw new NoSuchMethodException(type.getName() + "#" + name + "(1 arg)");
    }

    private static Object callNoArgs(Object target, String... names) throws ReflectiveOperationException {
        if (target == null) {
            throw new NullPointerException("Reflection target is null");
        }

        Class<?> type = target.getClass();
        for (String name : names) {
            try {
                Method method = type.getMethod(name);
                return method.invoke(target);
            } catch (NoSuchMethodException ignored) {
                try {
                    Method method = type.getDeclaredMethod(name);
                    method.setAccessible(true);
                    return method.invoke(target);
                } catch (NoSuchMethodException ignoredToo) {
                    // try next name
                }
            }
        }

        for (String name : names) {
            try {
                Field field = type.getField(name);
                return field.get(target);
            } catch (NoSuchFieldException ignored) {
                try {
                    Field field = type.getDeclaredField(name);
                    field.setAccessible(true);
                    return field.get(target);
                } catch (NoSuchFieldException ignoredToo) {
                    // try next name
                }
            }
        }

        throw new NoSuchMethodException(type.getName() + " has none of " + String.join(",", names));
    }

    private static int intValue(Object value) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        throw new IllegalArgumentException("Expected numeric chunk coordinate, got " + value);
    }
}
