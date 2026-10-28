package org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control;

final class ProtectionStore {
    static ClaimContext last;
    static boolean enabled;
    static int calls;

    static synchronized boolean set(ClaimContext context, boolean value) {
        last = context;
        enabled = value;
        calls++;
        return true;
    }
}
