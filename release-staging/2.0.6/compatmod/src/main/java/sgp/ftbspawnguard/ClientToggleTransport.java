package sgp.ftbspawnguard;

import net.neoforged.neoforge.network.PacketDistributor;

public final class ClientToggleTransport {
    private static final String PREFIX = "ftbmsc chunk ";
    private static final String SUFFIX = " gui_toggle";

    private ClientToggleTransport() {
    }

    public static boolean replaceSingleToggle(String command) {
        if (command == null || !command.startsWith(PREFIX) || !command.endsWith(SUFFIX)) {
            throw new IllegalStateException("Unexpected Spawn Guard single-toggle command: " + command);
        }

        String coordinates = command.substring(PREFIX.length(), command.length() - SUFFIX.length()).trim();
        String[] parts = coordinates.split("\\s+");
        if (parts.length != 2) {
            throw new IllegalStateException("Unexpected Spawn Guard coordinates: " + command);
        }

        int x = Integer.parseInt(parts[0]);
        int z = Integer.parseInt(parts[1]);
        PacketDistributor.sendToServer(new ManualTogglePayload(x, z));
        return true;
    }
}
