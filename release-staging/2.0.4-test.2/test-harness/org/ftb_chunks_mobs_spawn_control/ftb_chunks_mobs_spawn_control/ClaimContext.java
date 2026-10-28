package org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control;

final class ClaimContext {
    final Object level;
    final int x;
    final int z;

    private ClaimContext(Object level, int x, int z) {
        this.level = level;
        this.x = x;
        this.z = z;
    }

    static ClaimContext atChunk(Object level, int x, int z) {
        return new ClaimContext(level, x, z);
    }
}
