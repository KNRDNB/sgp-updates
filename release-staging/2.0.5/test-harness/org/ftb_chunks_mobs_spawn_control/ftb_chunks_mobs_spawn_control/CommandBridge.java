package org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control;

final class CommandBridge {
    static Object lastPlayer;
    static ClaimContext lastContext;
    static String lastOperation;

    private static int executeClaim(Object player, ClaimContext context, String operation) {
        lastPlayer = player;
        lastContext = context;
        lastOperation = operation;
        return 1;
    }
}
