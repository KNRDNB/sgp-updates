#!/usr/bin/env bash
set -euo pipefail
JAR=/tmp/spawn-guard.jar
python3 - <<'PY'
import urllib.request
urllib.request.urlretrieve("https://mediafilez.forgecdn.net/files/8986/734/ftb_chunks_mobs_spawn_control-1.0.4-neoforge-1.21.1.jar","/tmp/spawn-guard.jar")
PY
CP="$JAR"
for c in  org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.ClaimHooks  org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.ClaimContext  org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.ProtectionStore  org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.CommandBridge  org.ftb_chunks_mobs_spawn_control.ftb_chunks_mobs_spawn_control.EventBridge; do
 echo "===== $c ====="
 javap -classpath "$CP" -p -c -v "$c"
done
