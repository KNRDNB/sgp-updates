package org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control;

final class CommandBridge {
    static Object lastPlayer;
    static ClaimContext lastContext;
    static String lastOperation;

    static Object lastGuiSyncPlayer;
    static Object lastGuiSyncLevel;
    static int lastGuiSyncX;
    static int lastGuiSyncZ;

    private static int executeClaim(Object player, ClaimContext context, String operation) {
        lastPlayer = player;
        lastContext = context;
        lastOperation = operation;
        return 1;
    }

    private static int guiSync(Object player, Object level, int x, int z) {
        lastGuiSyncPlayer = player;
        lastGuiSyncLevel = level;
        lastGuiSyncX = x;
        lastGuiSyncZ = z;
        return 1;
    }
}
