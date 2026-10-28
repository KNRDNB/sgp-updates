#!/usr/bin/env bash
set -euo pipefail
JAR=/tmp/spawn-guard.jar
python3 - <<'PY'
import urllib.request
u="https://mediafilez.forgecdn.net/files/8986/734/ftb_chunks_mobs_spawn_control-1.0.4-neoforge-1.21.1.jar"
urllib.request.urlretrieve(u,"/tmp/spawn-guard.jar")
PY
test "$(stat -c '%s' "$JAR")" = "50538"
test "$(sha256sum "$JAR" | awk '{print $1}')" = "c7df7bdd469237418ce4ef892497793addba84f9c92125b0fde05f8b6e353960"
jar tf "$JAR" | grep '^org/ftb_chunks_mobs_spawn_control/' | grep '\.class$' | sort > /tmp/classes.txt
echo "===== CLASS LIST ====="
cat /tmp/classes.txt
echo "===== RELEVANT BYTECODE ====="
while IFS= read -r f; do
  c="${f%.class}"
  c="${c//\//.}"
  javap -classpath "$JAR" -p -c -v "$c" > /tmp/javap.txt || true
  if grep -Eqi 'sendCommand|gui_toggle|batch|mouse|middle|ftbmsc|ClientPacketListener|GuiGraphics|ChunkScreen' /tmp/javap.txt; then
    echo "===== $c ====="
    cat /tmp/javap.txt
  fi
done < /tmp/classes.txt
