import sgp.client.branding.PostCutoverReleaseFinder;

public final class BrandingFinderProbe {
    private static void expect(String name, String json, String expected) {
        String actual = PostCutoverReleaseFinder.find(json);
        if (!java.util.Objects.equals(actual, expected)) {
            throw new IllegalStateException(name + ": expected=" + expected + " actual=" + actual);
        }
    }

    public static void main(String[] args) {
        String legacy = """
            [
              {"draft":false,"prerelease":false,"tag_name":"v2.0.0",
               "assets":[{"name":"SGP_ClientPatch_2.0.0.zip"}]}
            ]
            """;
        expect("legacy bridge", legacy, "2.0.0");

        String post = """
            [
              {"draft":false,"prerelease":false,"tag_name":"v2.0.0",
               "assets":[{"name":"SGP_ClientPatch_2.0.0.zip"}]},
              {"draft":false,"prerelease":false,"tag_name":"client-v2.0.1",
               "assets":[
                 {"name":"SGP_ClientPatch_2.0.1.zip"},
                 {"name":"SGP_ClientPatch_2.0.1.meta.json"}
               ]}
            ]
            """;
        expect("post-cutover pair", post, "2.0.1");

        String brokenPair = """
            [
              {"draft":false,"prerelease":false,"tag_name":"v2.0.0",
               "assets":[{"name":"SGP_ClientPatch_2.0.0.zip"}]},
              {"draft":false,"prerelease":false,"tag_name":"client-v2.0.1",
               "assets":[{"name":"SGP_ClientPatch_2.0.1.zip"}]}
            ]
            """;
        expect("missing metadata rejected", brokenPair, "2.0.0");

        String prerelease = """
            [
              {"draft":false,"prerelease":false,"tag_name":"v2.0.0",
               "assets":[{"name":"SGP_ClientPatch_2.0.0.zip"}]},
              {"draft":false,"prerelease":true,"tag_name":"client-v2.0.2",
               "assets":[
                 {"name":"SGP_ClientPatch_2.0.2.zip"},
                 {"name":"SGP_ClientPatch_2.0.2.meta.json"}
               ]}
            ]
            """;
        expect("prerelease ignored", prerelease, "2.0.0");

        String illegalLegacy = """
            [
              {"draft":false,"prerelease":false,"tag_name":"v2.0.2",
               "assets":[{"name":"SGP_ClientPatch_2.0.2.zip"}]},
              {"draft":false,"prerelease":false,"tag_name":"v2.0.0",
               "assets":[{"name":"SGP_ClientPatch_2.0.0.zip"}]}
            ]
            """;
        expect("legacy greater than bridge rejected", illegalLegacy, "2.0.0");

        String extraAsset = """
            [
              {"draft":false,"prerelease":false,"tag_name":"v2.0.0",
               "assets":[{"name":"SGP_ClientPatch_2.0.0.zip"}]},
              {"draft":false,"prerelease":false,"tag_name":"client-v2.0.3",
               "assets":[
                 {"name":"SGP_ClientPatch_2.0.3.zip"},
                 {"name":"SGP_ClientPatch_2.0.3.meta.json"},
                 {"name":"unexpected.txt"}
               ]}
            ]
            """;
        expect("unexpected asset rejected", extraAsset, "2.0.0");

        String highest = """
            [
              {"draft":false,"prerelease":false,"tag_name":"client-v2.0.2",
               "assets":[
                 {"name":"SGP_ClientPatch_2.0.2.zip"},
                 {"name":"SGP_ClientPatch_2.0.2.meta.json"}
               ]},
              {"draft":false,"prerelease":false,"tag_name":"client-v2.1.0",
               "assets":[
                 {"name":"SGP_ClientPatch_2.1.0.meta.json"},
                 {"name":"SGP_ClientPatch_2.1.0.zip"}
               ]}
            ]
            """;
        expect("highest stable and asset order independent", highest, "2.1.0");

        System.out.println("BRANDING_POST_CUTOVER_DISCOVERY_PROBE_PASS");
    }
}
