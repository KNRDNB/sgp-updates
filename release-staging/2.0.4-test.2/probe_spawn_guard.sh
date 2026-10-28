#!/usr/bin/env bash
set -euo pipefail

JAR=/tmp/spawn-guard-1.0.4.jar
URL="https://mediafilez.forgecdn.net/files/8986/734/ftb_chunks_mobs_spawn_control-1.0.4-neoforge-1.21.1.jar"
EXPECTED_SHA256="c7df7bdd469237418ce4ef892497793addba84f9c92125b0fde05f8b6e353960"
EXPECTED_SIZE="50538"

python3 - <<'PY'
import urllib.request
u="https://mediafilez.forgecdn.net/files/8986/734/ftb_chunks_mobs_spawn_control-1.0.4-neoforge-1.21.1.jar"
urllib.request.urlretrieve(u,"/tmp/spawn-guard-1.0.4.jar")
PY

test "$(stat -c '%s' "$JAR")" = "$EXPECTED_SIZE"
test "$(sha256sum "$JAR" | awk '{print $1}')" = "$EXPECTED_SHA256"
unzip -t "$JAR" >/dev/null

jar tf "$JAR" | grep -Fxq 'org/ftb_chunks_mobs_spawn_control/ftb_chunks_mobs_spawn_control/ClaimContext.class'
jar tf "$JAR" | grep -Fxq 'org/ftb_chunks_mobs_spawn_control/ftb_chunks_mobs_spawn_control/ProtectionStore.class'

javap -classpath "$JAR" -p org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.ClaimContext > /tmp/claim-context.txt
javap -classpath "$JAR" -p org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.ProtectionStore > /tmp/protection-store.txt

grep -Fq 'static org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.ClaimContext atChunk(java.lang.Object, int, int);' /tmp/claim-context.txt
grep -Fq 'static synchronized boolean set(org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.ClaimContext, boolean);' /tmp/protection-store.txt

echo "SPAWN_GUARD_1_0_4_REFLECTION_API_PASS"
