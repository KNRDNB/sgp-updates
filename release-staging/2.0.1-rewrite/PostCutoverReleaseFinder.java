package sgp.client.branding;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class PostCutoverReleaseFinder {
    private static final Pattern LEGACY =
        Pattern.compile("^v(0|[1-9]\\d*)\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)$");
    private static final Pattern POST_CUTOVER =
        Pattern.compile("^client-v(0|[1-9]\\d*)\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)$");
    private static final int[] CUTOVER = new int[]{2, 0, 0};

    private PostCutoverReleaseFinder() {}

    public static String find(String json) {
        try {
            JsonElement root = JsonParser.parseString(json);
            if (root == null || !root.isJsonArray()) return null;

            String best = null;
            for (JsonElement element : root.getAsJsonArray()) {
                if (element == null || !element.isJsonObject()) continue;
                JsonObject release = element.getAsJsonObject();

                Boolean draft = readBoolean(release, "draft");
                Boolean prerelease = readBoolean(release, "prerelease");
                if (draft == null || prerelease == null || draft || prerelease) continue;

                String tag = readString(release, "tag_name");
                if (tag == null) continue;

                boolean postCutover;
                String version;
                Matcher legacy = LEGACY.matcher(tag);
                Matcher post = POST_CUTOVER.matcher(tag);
                if (legacy.matches()) {
                    int[] parsed = parsedGroups(legacy);
                    if (parsed == null || compare(parsed, CUTOVER) > 0) continue;
                    version = format(parsed);
                    postCutover = false;
                } else if (post.matches()) {
                    int[] parsed = parsedGroups(post);
                    if (parsed == null || compare(parsed, CUTOVER) <= 0) continue;
                    version = format(parsed);
                    postCutover = true;
                } else {
                    continue;
                }

                JsonElement assetsElement = release.get("assets");
                if (assetsElement == null || !assetsElement.isJsonArray()) continue;
                JsonArray assets = assetsElement.getAsJsonArray();

                String zipName = "SGP_ClientPatch_" + version + ".zip";
                String metaName = "SGP_ClientPatch_" + version + ".meta.json";
                boolean zip = false;
                boolean meta = false;
                boolean invalid = false;

                for (JsonElement assetElement : assets) {
                    if (assetElement == null || !assetElement.isJsonObject()) {
                        invalid = true;
                        break;
                    }
                    String name = readString(assetElement.getAsJsonObject(), "name");
                    if (zipName.equals(name)) {
                        if (zip) { invalid = true; break; }
                        zip = true;
                    } else if (metaName.equals(name)) {
                        if (meta) { invalid = true; break; }
                        meta = true;
                    } else {
                        invalid = true;
                        break;
                    }
                }

                if (invalid) continue;
                if (postCutover) {
                    if (assets.size() != 2 || !zip || !meta) continue;
                } else {
                    if (assets.size() != 1 || !zip || meta) continue;
                }

                if (best == null || compare(parseVersion(version), parseVersion(best)) > 0) {
                    best = version;
                }
            }
            return best;
        } catch (RuntimeException ignored) {
            return null;
        }
    }

    private static String readString(JsonObject object, String key) {
        JsonElement element = object.get(key);
        if (element == null || !element.isJsonPrimitive()) return null;
        try {
            return element.getAsString();
        } catch (RuntimeException ignored) {
            return null;
        }
    }

    private static Boolean readBoolean(JsonObject object, String key) {
        JsonElement element = object.get(key);
        if (element == null || !element.isJsonPrimitive()) return null;
        try {
            return element.getAsBoolean();
        } catch (RuntimeException ignored) {
            return null;
        }
    }

    private static int[] parsedGroups(Matcher matcher) {
        try {
            return new int[]{
                Integer.parseInt(matcher.group(1)),
                Integer.parseInt(matcher.group(2)),
                Integer.parseInt(matcher.group(3))
            };
        } catch (RuntimeException ignored) {
            return null;
        }
    }

    private static int[] parseVersion(String version) {
        String[] parts = version.split("\\.", -1);
        if (parts.length != 3) return new int[]{0, 0, 0};
        try {
            return new int[]{
                Integer.parseInt(parts[0]),
                Integer.parseInt(parts[1]),
                Integer.parseInt(parts[2])
            };
        } catch (RuntimeException ignored) {
            return new int[]{0, 0, 0};
        }
    }

    private static int compare(int[] left, int[] right) {
        for (int i = 0; i < 3; i++) {
            int value = Integer.compare(left[i], right[i]);
            if (value != 0) return value;
        }
        return 0;
    }

    private static String format(int[] version) {
        return version[0] + "." + version[1] + "." + version[2];
    }
}
