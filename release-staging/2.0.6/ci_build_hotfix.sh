#!/usr/bin/env bash
set -euxo pipefail

ROOT="release-staging/2.0.6"
MODROOT="$ROOT/compatmod"
MOD="SGP-FTB-Spawn-Guard-Auto-Protect-1.0.2.jar"

rm -rf .sgp206-event-harness
mkdir -p .sgp206-event-harness
javac -encoding UTF-8 -source 21 -target 21 -d .sgp206-event-harness   "$MODROOT/src/main/java/sgp/ftbspawnguard/ArchitecturyEventAccess.java"   "$ROOT/test-harness/dev/architectury/event/Event.java"   "$ROOT/test-harness/dev/architectury/event/EventFactory.java"   "$ROOT/test-harness/sgp/ftbspawnguard/ArchitecturyEventAccessHarness.java"
java -ea -cp .sgp206-event-harness sgp.ftbspawnguard.ArchitecturyEventAccessHarness

rm -rf .sgp206-spawnguard-harness
mkdir -p .sgp206-spawnguard-harness
javac -encoding UTF-8 -source 21 -target 21 -d .sgp206-spawnguard-harness   "$MODROOT/src/main/java/sgp/ftbspawnguard/SpawnGuardAccess.java"   $(find "$ROOT/test-harness/org" -name '*.java' -print)   "$ROOT/test-harness/sgp/ftbspawnguard/SpawnGuardAccessHarness.java"
java -ea -cp .sgp206-spawnguard-harness sgp.ftbspawnguard.SpawnGuardAccessHarness

grep -Fq 'ArchitecturyEventAccess.register(event, listener);' "$MODROOT/src/main/java/sgp/ftbspawnguard/AutoProtectHook.java"
! grep -Fq 'event.getClass().getMethods()' "$MODROOT/src/main/java/sgp/ftbspawnguard/AutoProtectHook.java"
grep -Fq 'Class.forName("dev.architectury.event.Event")' "$MODROOT/src/main/java/sgp/ftbspawnguard/ArchitecturyEventAccess.java"
grep -Fq 'getMethod("register", Object.class)' "$MODROOT/src/main/java/sgp/ftbspawnguard/ArchitecturyEventAccess.java"

gradle -p "$MODROOT" build --no-daemon --stacktrace
cp "$MODROOT/build/libs/$MOD" "$MOD"

unzip -t "$MOD" >/dev/null
unzip -l "$MOD" > sgp206-addon-files.txt
grep -Fq 'META-INF/neoforge.mods.toml' sgp206-addon-files.txt
grep -Fq 'sgp/ftbspawnguard/AutoProtectHook.class' sgp206-addon-files.txt
grep -Fq 'sgp/ftbspawnguard/ArchitecturyEventAccess.class' sgp206-addon-files.txt
grep -Fq 'sgp/ftbspawnguard/SpawnGuardAccess.class' sgp206-addon-files.txt
grep -Fq 'sgp/ftbspawnguard/ManualTogglePayload.class' sgp206-addon-files.txt
grep -Fq 'sgp/ftbspawnguard/mixin/SpawnGuardClientEventsMixin.class' sgp206-addon-files.txt
! grep -Fq 'dev/architectury/' sgp206-addon-files.txt
! grep -Fq 'org/ftb_chunks_mobs_spawn_control/' sgp206-addon-files.txt
! grep -Fq 'dev/ftb/mods/ftbchunks/' sgp206-addon-files.txt
! grep -Fq 'test-harness' sgp206-addon-files.txt

unzip -p "$MOD" META-INF/neoforge.mods.toml > sgp206-addon-mod.toml
grep -Fq 'version="1.0.2"' sgp206-addon-mod.toml
grep -Fq 'versionRange="[2101.1.22,2101.1.23)"' sgp206-addon-mod.toml
grep -Fq 'versionRange="[1.0.4,1.0.5)"' sgp206-addon-mod.toml

javap -classpath "$MOD" -p -c -v sgp.ftbspawnguard.ArchitecturyEventAccess > sgp206-event-access-javap.txt
javap -classpath "$MOD" -p -c -v sgp.ftbspawnguard.AutoProtectHook > sgp206-auto-hook-javap.txt
grep -Fq 'major version: 65' sgp206-event-access-javap.txt
grep -Fq 'dev.architectury.event.Event' sgp206-event-access-javap.txt
grep -Fq 'register' sgp206-event-access-javap.txt
grep -Fq 'ArchitecturyEventAccess.register' sgp206-auto-hook-javap.txt

sha256sum "$MOD" | tee sgp206_addon_sha.txt
stat -c '%s' "$MOD" | tee sgp206_addon_size.txt

echo "SGP_FTB_102_CANDIDATE_BUILD_PASS"
