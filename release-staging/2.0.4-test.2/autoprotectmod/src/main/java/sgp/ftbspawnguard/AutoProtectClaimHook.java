package sgp.ftbspawnguard;

import com.mojang.logging.LogUtils;
import org.slf4j.Logger;

import java.lang.reflect.Method;
import java.lang.reflect.Proxy;

final class AutoProtectClaimHook {
    private static final Logger LOGGER = LogUtils.getLogger();

    private static final String CLAIM_EVENT = "dev.ftb.mods.ftbchunks.api.event.ClaimedChunkEvent";
    private static final String AFTER_INTERFACE = "dev.ftb.mods.ftbchunks.api.event.ClaimedChunkEvent$After";
    private static final String CLAIM_CONTEXT = "org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.ClaimContext";
    private static final String PROTECTION_STORE = "org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.ProtectionStore";

    private AutoProtectClaimHook() {
    }

    static void register() {
        try {
            Class<?> eventClass = Class.forName(CLAIM_EVENT);
            Object afterClaim = eventClass.getField("AFTER_CLAIM").get(null);
            Class<?> afterInterface = Class.forName(AFTER_INTERFACE);

            Object listener = Proxy.newProxyInstance(
                afterInterface.getClassLoader(),
                new Class<?>[]{afterInterface},
                (proxy, method, args) -> {
                    if ("after".equals(method.getName()) && args != null && args.length >= 2) {
                        autoProtect(args[0], args[1]);
                    }
                    return null;
                }
            );

            Method register = null;
            for (Method method : afterClaim.getClass().getMethods()) {
                if ("register".equals(method.getName()) && method.getParameterCount() == 1) {
                    register = method;
                    break;
                }
            }
            if (register == null) {
                throw new IllegalStateException("FTB AFTER_CLAIM register(listener) method not found");
            }

            register.invoke(afterClaim, listener);
            LOGGER.info("SGP Spawn Guard auto-protect hook registered");
        } catch (Throwable t) {
            throw new IllegalStateException("Failed to register SGP Spawn Guard auto-protect hook", t);
        }
    }

    private static void autoProtect(Object source, Object claimedChunk) {
        try {
            Object pos = callNoArg(claimedChunk, "getPos");
            if (pos == null) {
                LOGGER.warn("SGP auto-protect: claimed chunk has no position");
                return;
            }

            int chunkX = intValue(callNoArg(pos, "x", "getX"), Integer.MIN_VALUE);
            int chunkZ = intValue(callNoArg(pos, "z", "getZ"), Integer.MIN_VALUE);
            if (chunkX == Integer.MIN_VALUE || chunkZ == Integer.MIN_VALUE) {
                LOGGER.warn("SGP auto-protect: could not read claimed chunk coordinates");
                return;
            }

            Object level = callNoArg(source, "getLevel");
            if (level == null) {
                LOGGER.warn("SGP auto-protect: claim source has no level; leaving claim unchanged");
                return;
            }

            Class<?> contextClass = Class.forName(CLAIM_CONTEXT);
            Method atChunk = contextClass.getDeclaredMethod("atChunk", Object.class, int.class, int.class);
            atChunk.setAccessible(true);
            Object context = atChunk.invoke(null, level, chunkX, chunkZ);
            if (context == null) {
                LOGGER.warn("SGP auto-protect: Spawn Guard could not resolve newly claimed chunk {},{}", chunkX, chunkZ);
                return;
            }

            Class<?> storeClass = Class.forName(PROTECTION_STORE);
            Method set = storeClass.getDeclaredMethod("set", contextClass, boolean.class);
            set.setAccessible(true);
            set.invoke(null, context, true);
        } catch (Throwable t) {
            LOGGER.error("SGP auto-protect failed for a newly claimed chunk", t);
        }
    }

    private static Object callNoArg(Object target, String... names) {
        if (target == null) {
            return null;
        }
        for (String name : names) {
            try {
                Method method = target.getClass().getMethod(name);
                method.setAccessible(true);
                return method.invoke(target);
            } catch (ReflectiveOperationException ignored) {
            }
        }
        return null;
    }

    private static int intValue(Object value, int fallback) {
        return value instanceof Number number ? number.intValue() : fallback;
    }
}
