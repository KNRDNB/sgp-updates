#!/usr/bin/env bash
set -euo pipefail

MOD="SGP-FTB-Spawn-Guard-Auto-Protect-1.0.0.jar"
ROOT="release-staging/2.0.4-test.2"

rm -rf .auto-protect-harness
mkdir -p .auto-protect-harness

javac -encoding UTF-8 -source 21 -target 21 -d .auto-protect-harness   "$ROOT/compatmod/src/main/java/sgp/ftbspawnguard/AutoProtectHook.java"   $(find "$ROOT/test-harness" -name '*.java' -print)

java -ea -cp .auto-protect-harness sgp.ftbspawnguard.AutoProtectHarness

gradle -p "$ROOT/compatmod" build --no-daemon --stacktrace
cp "$ROOT/compatmod/build/libs/$MOD" "$MOD"

unzip -t "$MOD" >/dev/null
unzip -l "$MOD" > auto-protect-files.txt

grep -Fq 'META-INF/neoforge.mods.toml' auto-protect-files.txt
grep -Fq 'sgp/ftbspawnguard/AutoProtectHook.class' auto-protect-files.txt
grep -Fq 'sgp/ftbspawnguard/SgpFtbSpawnGuardAutoProtect.class' auto-protect-files.txt
! grep -Fq 'dev/ftb/mods/ftbchunks/' auto-protect-files.txt
! grep -Fq 'org/ftb_chunks_mobs_spawn_control/' auto-protect-files.txt
! grep -Fq 'test-harness' auto-protect-files.txt

unzip -p "$MOD" META-INF/neoforge.mods.toml > auto-protect-mod.toml
grep -Fq 'modId="sgp_ftb_spawn_guard_auto_protect"' auto-protect-mod.toml
grep -Fq 'version="1.0.0"' auto-protect-mod.toml
grep -Fq 'modId="ftbchunks"' auto-protect-mod.toml
grep -Fq 'versionRange="[2101.1.22,2101.2)"' auto-protect-mod.toml
grep -Fq 'modId="ftb_chunks_mobs_spawn_control"' auto-protect-mod.toml
grep -Fq 'versionRange="[1.0.4,1.1)"' auto-protect-mod.toml

javap -classpath "$MOD" -p -v sgp.ftbspawnguard.AutoProtectHook > auto-protect-javap.txt
grep -Fq 'major version: 65' auto-protect-javap.txt
grep -Fq 'dev.ftb.mods.ftbchunks.api.event.ClaimedChunkEvent' auto-protect-javap.txt
grep -Fq 'AFTER_CLAIM' auto-protect-javap.txt
grep -Fq 'org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.ClaimContext' auto-protect-javap.txt
grep -Fq 'org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.ProtectionStore' auto-protect-javap.txt
grep -Fq 'atChunk' auto-protect-javap.txt
grep -Fq 'set' auto-protect-javap.txt

sha256sum "$MOD" | tee auto_protect_sha.txt
stat -c '%s' "$MOD" | tee auto_protect_size.txt

echo SGP_FTB_AUTO_PROTECT_BUILD_PREFLIGHT_PASS
