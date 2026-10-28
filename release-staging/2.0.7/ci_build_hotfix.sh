#!/usr/bin/env bash
set -euxo pipefail

ROOT="release-staging/2.0.7"
MODROOT="$ROOT/compatmod"
MOD="SGP-FTB-Spawn-Guard-Auto-Protect-1.0.3.jar"

# Exact upstream bytecode guard: verify the remaining command-spam path and target signatures.
python3 - <<'PY'
import urllib.request
u="https://mediafilez.forgecdn.net/files/8986/734/ftb_chunks_mobs_spawn_control-1.0.4-neoforge-1.21.1.jar"
urllib.request.urlretrieve(u,"/tmp/spawn-guard-1.0.4.jar")
PY
test "$(stat -c '%s' /tmp/spawn-guard-1.0.4.jar)" = "50538"
test "$(sha256sum /tmp/spawn-guard-1.0.4.jar | awk '{print $1}')" = "c7df7bdd469237418ce4ef892497793addba84f9c92125b0fde05f8b6e353960"
javap -classpath /tmp/spawn-guard-1.0.4.jar -p -c -v   org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.ClientEvents > sgp207-upstream-clientevents-javap.txt
javap -classpath /tmp/spawn-guard-1.0.4.jar -p -c -v   org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.CommandBridge > sgp207-upstream-commandbridge-javap.txt
grep -Fq 'private static void render(java.lang.Object);' sgp207-upstream-clientevents-javap.txt
grep -Fq 'ftbmsc gui_sync' sgp207-upstream-clientevents-javap.txt
grep -Fq 'send:(Ljava/lang/String;)Z' sgp207-upstream-clientevents-javap.txt
grep -Fq 'private static int guiSync(java.lang.Object, java.lang.Object, int, int);' sgp207-upstream-commandbridge-javap.txt

rm -rf .sgp207-event-harness
mkdir -p .sgp207-event-harness
javac -encoding UTF-8 -source 21 -target 21 -d .sgp207-event-harness   "$MODROOT/src/main/java/sgp/ftbspawnguard/ArchitecturyEventAccess.java"   "$ROOT/test-harness/dev/architectury/event/Event.java"   "$ROOT/test-harness/dev/architectury/event/EventFactory.java"   "$ROOT/test-harness/sgp/ftbspawnguard/ArchitecturyEventAccessHarness.java"
java -ea -cp .sgp207-event-harness sgp.ftbspawnguard.ArchitecturyEventAccessHarness

rm -rf .sgp207-spawnguard-harness
mkdir -p .sgp207-spawnguard-harness
javac -encoding UTF-8 -source 21 -target 21 -d .sgp207-spawnguard-harness   "$MODROOT/src/main/java/sgp/ftbspawnguard/SpawnGuardAccess.java"   $(find "$ROOT/test-harness/org" -name '*.java' -print)   "$ROOT/test-harness/sgp/ftbspawnguard/SpawnGuardAccessHarness.java"
java -ea -cp .sgp207-spawnguard-harness sgp.ftbspawnguard.SpawnGuardAccessHarness

grep -Fq 'method = "pressed"' "$MODROOT/src/main/java/sgp/ftbspawnguard/mixin/SpawnGuardClientEventsMixin.java"
grep -Fq 'method = "render"' "$MODROOT/src/main/java/sgp/ftbspawnguard/mixin/SpawnGuardClientEventsMixin.java"
grep -Fq 'ClientToggleTransport.replaceSingleToggle(command)' "$MODROOT/src/main/java/sgp/ftbspawnguard/mixin/SpawnGuardClientEventsMixin.java"
grep -Fq 'ClientToggleTransport.replaceGuiSync(command)' "$MODROOT/src/main/java/sgp/ftbspawnguard/mixin/SpawnGuardClientEventsMixin.java"
grep -Fq 'new GuiSyncRequestPayload' "$MODROOT/src/main/java/sgp/ftbspawnguard/ClientToggleTransport.java"
grep -Fq 'executeGuiSync(player, payload.chunkX(), payload.chunkZ())' "$MODROOT/src/main/java/sgp/ftbspawnguard/SgpNetworking.java"
grep -Fq '"guiSync", Object.class, Object.class, int.class, int.class' "$MODROOT/src/main/java/sgp/ftbspawnguard/SpawnGuardAccess.java"

gradle -p "$MODROOT" build --no-daemon --stacktrace
cp "$MODROOT/build/libs/$MOD" "$MOD"

unzip -t "$MOD" >/dev/null
unzip -l "$MOD" > sgp207-addon-files.txt
grep -Fq 'META-INF/neoforge.mods.toml' sgp207-addon-files.txt
grep -Fq 'sgp/ftbspawnguard/GuiSyncRequestPayload.class' sgp207-addon-files.txt
grep -Fq 'sgp/ftbspawnguard/ManualTogglePayload.class' sgp207-addon-files.txt
grep -Fq 'sgp/ftbspawnguard/mixin/SpawnGuardClientEventsMixin.class' sgp207-addon-files.txt
! grep -Fq 'dev/architectury/' sgp207-addon-files.txt
! grep -Fq 'org/ftb_chunks_mobs_spawn_control/' sgp207-addon-files.txt
! grep -Fq 'test-harness' sgp207-addon-files.txt

unzip -p "$MOD" META-INF/neoforge.mods.toml > sgp207-addon-mod.toml
grep -Fq 'version="1.0.3"' sgp207-addon-mod.toml
grep -Fq 'versionRange="[2101.1.22,2101.1.23)"' sgp207-addon-mod.toml
grep -Fq 'versionRange="[1.0.4,1.0.5)"' sgp207-addon-mod.toml

javap -classpath "$MOD" -p -c -v sgp.ftbspawnguard.SgpNetworking > sgp207-networking-javap.txt
javap -classpath "$MOD" -p -c -v sgp.ftbspawnguard.SpawnGuardAccess > sgp207-access-javap.txt
javap -classpath "$MOD" -p -c -v sgp.ftbspawnguard.mixin.SpawnGuardClientEventsMixin > sgp207-mixin-javap.txt
grep -Fq 'GuiSyncRequestPayload' sgp207-networking-javap.txt
grep -Fq 'executeGuiSync' sgp207-networking-javap.txt
grep -Fq 'guiSync' sgp207-access-javap.txt
grep -Fq 'sgp$replaceGuiSyncTransport' sgp207-mixin-javap.txt
grep -Fq 'sgp$replaceSingleToggleTransport' sgp207-mixin-javap.txt

sha256sum "$MOD" | tee sgp207_addon_sha.txt
stat -c '%s' "$MOD" | tee sgp207_addon_size.txt

echo "SGP_FTB_103_CANDIDATE_BUILD_PASS"
