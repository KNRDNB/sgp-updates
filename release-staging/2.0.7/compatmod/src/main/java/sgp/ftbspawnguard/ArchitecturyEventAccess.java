package sgp.ftbspawnguard;

import java.lang.reflect.Method;

final class ArchitecturyEventAccess {
    private ArchitecturyEventAccess() {
    }

    static void register(Object event, Object listener) throws ReflectiveOperationException {
        if (event == null) {
            throw new NullPointerException("Architectury event is null");
        }

        Class<?> eventApi = Class.forName("dev.architectury.event.Event");
        if (!eventApi.isInstance(event)) {
            throw new IllegalArgumentException("Object does not implement dev.architectury.event.Event: " + event.getClass().getName());
        }

        Method register = eventApi.getMethod("register", Object.class);
        register.invoke(event, listener);
    }
}
