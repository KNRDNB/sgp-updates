#!/usr/bin/env bash
set -euxo pipefail

ROOT="release-staging/2.0.5"
MODROOT="$ROOT/compatmod"
MOD="SGP-FTB-Spawn-Guard-Auto-Protect-1.0.1.jar"
SPAWN="/tmp/ftb_chunks_mobs_spawn_control-1.0.4-neoforge-1.21.1.jar"
SPAWN_URL="https://mediafilez.forgecdn.net/files/8986/734/ftb_chunks_mobs_spawn_control-1.0.4-neoforge-1.21.1.jar"
SPAWN_SHA="c7df7bdd469237418ce4ef892497793addba84f9c92125b0fde05f8b6e353960"
SPAWN_SIZE="50538"

rm -rf .sgp205-harness
mkdir -p .sgp205-harness
javac -encoding UTF-8 -source 21 -target 21 -d .sgp205-harness \
  "$MODROOT/src/main/java/sgp/ftbspawnguard/SpawnGuardAccess.java" \
  $(find "$ROOT/test-harness" -name '*.java' -print)
java -ea -cp .sgp205-harness sgp.ftbspawnguard.SpawnGuardAccessHarness

python3 - <<'PY'
import urllib.request
urllib.request.urlretrieve(
    "https://mediafilez.forgecdn.net/files/8986/734/ftb_chunks_mobs_spawn_control-1.0.4-neoforge-1.21.1.jar",
    "/tmp/ftb_chunks_mobs_spawn_control-1.0.4-neoforge-1.21.1.jar"
)
PY
test "$(stat -c '%s' "$SPAWN")" = "$SPAWN_SIZE"
test "$(sha256sum "$SPAWN" | awk '{print $1}')" = "$SPAWN_SHA"
unzip -t "$SPAWN" >/dev/null

javap -classpath "$SPAWN" -p -c -v org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.ClientEvents > spawn-client-events.txt
javap -classpath "$SPAWN" -p -c -v org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.CommandBridge > spawn-command-bridge.txt
javap -classpath "$SPAWN" -p -c -v org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.ClaimContext > spawn-claim-context.txt
javap -classpath "$SPAWN" -p -c -v org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.WorldScope > spawn-world-scope.txt
javap -classpath "$SPAWN" -p -c -v org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.ProtectionStore > spawn-protection-store.txt

grep -Fq 'ftbmsc chunk' spawn-client-events.txt
grep -Fq 'gui_toggle' spawn-client-events.txt
grep -Fq 'send:(Ljava/lang/String;)Z' spawn-client-events.txt
grep -Fq 'sendCommand' spawn-client-events.txt
grep -Fq 'private static int executeClaim(java.lang.Object, org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.ClaimContext, java.lang.String)' spawn-command-bridge.txt
grep -Fq 'ClaimContext(java.lang.String, int, int, java.lang.String, java.lang.Object)' spawn-claim-context.txt
grep -Fq 'resourceKeyId(java.lang.Object)' spawn-claim-context.txt
grep -Fq 'atChunk(java.lang.Object, int, int)' spawn-claim-context.txt
grep -Fq 'scopeDimension(java.lang.Object, java.lang.String)' spawn-world-scope.txt
grep -Fq 'static synchronized boolean set(org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.ClaimContext, boolean)' spawn-protection-store.txt

# The production auto-claim path must not perform the fragile second FTB manager lookup.
! grep -Fq 'atChunk' "$MODROOT/src/main/java/sgp/ftbspawnguard/AutoProtectHook.java"
python3 - <<'PY'
from pathlib import Path
p=Path("release-staging/2.0.5/compatmod/src/main/java/sgp/ftbspawnguard/SpawnGuardAccess.java").read_text()
segment=p.split("static Object contextFromClaim",1)[1].split("static boolean setProtected",1)[0]
assert "atChunk" not in segment, "auto-claim path must not use atChunk"
manual=p.split("static int executeGuiToggle",1)[1]
assert "atChunk" in manual, "manual toggle may use stable post-claim lookup"
print("SGP_FTB_205_CONTEXT_PATH_AUDIT_PASS")
PY
grep -Fq 'contextFromClaim' "$MODROOT/src/main/java/sgp/ftbspawnguard/AutoProtectHook.java"
grep -Fq 'getTeamData' "$MODROOT/src/main/java/sgp/ftbspawnguard/SpawnGuardAccess.java"
grep -Fq 'getDeclaredConstructor' "$MODROOT/src/main/java/sgp/ftbspawnguard/SpawnGuardAccess.java"
grep -Fq '"executeClaim"' "$MODROOT/src/main/java/sgp/ftbspawnguard/SpawnGuardAccess.java"
grep -Fq '"gui_toggle"' "$MODROOT/src/main/java/sgp/ftbspawnguard/SpawnGuardAccess.java"

gradle -p "$MODROOT" build --no-daemon --stacktrace
cp "$MODROOT/build/libs/$MOD" "$MOD"

unzip -t "$MOD" >/dev/null
unzip -l "$MOD" > sgp205-addon-files.txt
grep -Fq 'META-INF/neoforge.mods.toml' sgp205-addon-files.txt
grep -Fq 'sgp_ftb_spawn_guard_auto_protect.mixins.json' sgp205-addon-files.txt
grep -Fq 'sgp/ftbspawnguard/AutoProtectHook.class' sgp205-addon-files.txt
grep -Fq 'sgp/ftbspawnguard/SpawnGuardAccess.class' sgp205-addon-files.txt
grep -Fq 'sgp/ftbspawnguard/ManualTogglePayload.class' sgp205-addon-files.txt
grep -Fq 'sgp/ftbspawnguard/SgpNetworking.class' sgp205-addon-files.txt
grep -Fq 'sgp/ftbspawnguard/mixin/SpawnGuardClientEventsMixin.class' sgp205-addon-files.txt
! grep -Fq 'org/ftb_chunks_mobs_spawn_control/' sgp205-addon-files.txt
! grep -Fq 'dev/ftb/mods/ftbchunks/' sgp205-addon-files.txt
! grep -Fq 'test-harness' sgp205-addon-files.txt

unzip -p "$MOD" META-INF/neoforge.mods.toml > sgp205-addon-mod.toml
grep -Fq 'version="1.0.1"' sgp205-addon-mod.toml
grep -Fq 'versionRange="[2101.1.22,2101.1.23)"' sgp205-addon-mod.toml
grep -Fq 'versionRange="[1.0.4,1.0.5)"' sgp205-addon-mod.toml
grep -Fq 'config="sgp_ftb_spawn_guard_auto_protect.mixins.json"' sgp205-addon-mod.toml

javap -classpath "$MOD" -p -c -v sgp.ftbspawnguard.SpawnGuardAccess > sgp205-access-javap.txt
javap -classpath "$MOD" -p -c -v sgp.ftbspawnguard.SgpNetworking > sgp205-network-javap.txt
javap -classpath "$MOD" -p -c -v sgp.ftbspawnguard.mixin.SpawnGuardClientEventsMixin > sgp205-mixin-javap.txt
grep -Fq 'major version: 65' sgp205-access-javap.txt
grep -Fq 'contextFromClaim' sgp205-access-javap.txt
grep -Fq 'executeGuiToggle' sgp205-access-javap.txt
grep -Fq 'playToServer' sgp205-network-javap.txt
grep -Fq 'replaceSingleToggle' sgp205-mixin-javap.txt

sha256sum "$MOD" | tee sgp205_addon_sha.txt
stat -c '%s' "$MOD" | tee sgp205_addon_size.txt

echo "SGP_FTB_205_HOTFIX_BUILD_PASS"
