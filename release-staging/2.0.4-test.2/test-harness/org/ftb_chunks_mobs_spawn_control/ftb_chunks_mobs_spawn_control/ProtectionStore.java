package org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control;

final class ProtectionStore {
    static boolean enabled;
    static int calls;
    static int lastX;
    static int lastZ;
    static Object lastLevel;

    static synchronized boolean set(ClaimContext context, boolean value) {
        enabled = value;
        calls++;
        lastX = context.x;
        lastZ = context.z;
        lastLevel = context.level;
        return true;
    }
}
