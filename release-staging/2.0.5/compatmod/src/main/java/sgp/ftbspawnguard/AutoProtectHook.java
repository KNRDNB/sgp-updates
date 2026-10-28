package sgp.ftbspawnguard;

import com.mojang.logging.LogUtils;
import org.slf4j.Logger;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.util.concurrent.atomic.AtomicBoolean;

final class AutoProtectHook {
    private static final Logger LOGGER = LogUtils.getLogger();
    private static final AtomicBoolean REGISTERED = new AtomicBoolean();

    private AutoProtectHook() {
    }

    static void register() {
        if (!REGISTERED.compareAndSet(false, true)) {
            return;
        }

        try {
            Class<?> eventClass = Class.forName("dev.ftb.mods.ftbchunks.api.event.ClaimedChunkEvent");
            Field eventField = eventClass.getField("AFTER_CLAIM");
            Object event = eventField.get(null);

            Class<?> listenerClass = Class.forName("dev.ftb.mods.ftbchunks.api.event.ClaimedChunkEvent$After");
            Object listener = Proxy.newProxyInstance(
                    listenerClass.getClassLoader(),
                    new Class<?>[]{listenerClass},
                    (proxy, method, args) -> {
                        if ("after".equals(method.getName()) && args != null && args.length == 2) {
                            protect(args[0], args[1]);
                        }
                        return null;
                    }
            );

            Method register = null;
            for (Method method : event.getClass().getMethods()) {
                if ("register".equals(method.getName()) && method.getParameterCount() == 1) {
                    register = method;
                    break;
                }
            }

            if (register == null) {
                throw new NoSuchMethodException("FTB AFTER_CLAIM.register(listener)");
            }

            register.invoke(event, listener);
            LOGGER.info("[SGP Auto Protect] Registered dedicated-safe FTB AFTER_CLAIM hook");
        } catch (Throwable t) {
            REGISTERED.set(false);
            throw new IllegalStateException("Unable to register SGP FTB auto-protect hook", t);
        }
    }

    private static void protect(Object sourceStack, Object claimedChunk) {
        try {
            Object claimContext = SpawnGuardAccess.contextFromClaim(sourceStack, claimedChunk);
            if (claimContext == null) {
                LOGGER.error("[SGP Auto Protect] AFTER_CLAIM produced no Spawn Guard context");
                return;
            }

            boolean changed = SpawnGuardAccess.setProtected(claimContext, true);
            if (!changed) {
                LOGGER.warn("[SGP Auto Protect] Claim was already protected or store rejected the write");
            }
        } catch (Throwable t) {
            LOGGER.error("[SGP Auto Protect] Could not auto-enable Mob Control for a newly claimed chunk", t);
        }
    }
}
