package sgp.ftbspawnguard;

import net.neoforged.neoforge.network.PacketDistributor;

public final class ClientToggleTransport {
    private static final String TOGGLE_PREFIX = "ftbmsc chunk ";
    private static final String TOGGLE_SUFFIX = " gui_toggle";
    private static final String SYNC_PREFIX = "ftbmsc gui_sync ";

    private ClientToggleTransport() {
    }

    public static boolean replaceSingleToggle(String command) {
        int[] coordinates = parseCoordinates(command, TOGGLE_PREFIX, TOGGLE_SUFFIX);
        PacketDistributor.sendToServer(new ManualTogglePayload(coordinates[0], coordinates[1]));
        return true;
    }

    public static boolean replaceGuiSync(String command) {
        int[] coordinates = parseCoordinates(command, SYNC_PREFIX, "");
        PacketDistributor.sendToServer(new GuiSyncRequestPayload(coordinates[0], coordinates[1]));
        return true;
    }

    private static int[] parseCoordinates(String command, String prefix, String suffix) {
        if (command == null || !command.startsWith(prefix) || !command.endsWith(suffix)) {
            throw new IllegalStateException("Unexpected Spawn Guard command: " + command);
        }

        int end = command.length() - suffix.length();
        String coordinates = command.substring(prefix.length(), end).trim();
        String[] parts = coordinates.split("\\s+");
        if (parts.length != 2) {
            throw new IllegalStateException("Unexpected Spawn Guard coordinates: " + command);
        }

        return new int[]{Integer.parseInt(parts[0]), Integer.parseInt(parts[1])};
    }
}
