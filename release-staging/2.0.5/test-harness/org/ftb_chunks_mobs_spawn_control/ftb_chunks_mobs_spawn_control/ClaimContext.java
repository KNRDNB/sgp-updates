package org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control;

public final class ClaimContext {
    public final String dimension;
    public final int chunkX;
    public final int chunkZ;
    public final String teamId;
    public final Object teamData;

    ClaimContext(String dimension, int chunkX, int chunkZ, String teamId, Object teamData) {
        this.dimension = dimension;
        this.chunkX = chunkX;
        this.chunkZ = chunkZ;
        this.teamId = teamId;
        this.teamData = teamData;
    }

    static String resourceKeyId(Object key) {
        return String.valueOf(key);
    }

    static ClaimContext atChunk(Object level, int x, int z) {
        return new ClaimContext("@lookup|" + level, x, z, "lookup-team", new Object());
    }
}
