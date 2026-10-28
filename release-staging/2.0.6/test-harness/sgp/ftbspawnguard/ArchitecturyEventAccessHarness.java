package sgp.ftbspawnguard;

import dev.architectury.event.Event;
import dev.architectury.event.EventFactory;

public final class ArchitecturyEventAccessHarness {
    public static void main(String[] args) throws Exception {
        Event<Object> event = EventFactory.create();
        Object listener = new Object();

        boolean runtimeClassPathFailed = false;
        try {
            var method = event.getClass().getMethod("register", Object.class);
            method.invoke(event, listener);
        } catch (IllegalAccessException expected) {
            runtimeClassPathFailed = true;
        }
        assert runtimeClassPathFailed : "fixture must reproduce package-private EventImpl access failure";

        ArchitecturyEventAccess.register(event, listener);
        System.out.println("SGP_ARCHITECTURY_EVENT_PUBLIC_INTERFACE_PASS");
    }
}
