#!/usr/bin/env bash
set -euo pipefail
JAR=/tmp/spawn-guard.jar
python3 - <<'PY'
import urllib.request
u="https://mediafilez.forgecdn.net/files/8986/734/ftb_chunks_mobs_spawn_control-1.0.4-neoforge-1.21.1.jar"
urllib.request.urlretrieve(u,"/tmp/spawn-guard.jar")
PY
sha256sum "$JAR"
stat -c '%s' "$JAR"
echo '=== CLASSES ==='
jar tf "$JAR" | grep '\.class$' | sort
echo '=== TOML ==='
unzip -p "$JAR" META-INF/neoforge.mods.toml
echo '=== JAVAP MATCHES ==='
for c in $(jar tf "$JAR" | grep '\.class$' | sed 's#/#.#g;s#\.class$##'); do
  out="$(javap -classpath "$JAR" -p "$c" 2>/dev/null || true)"
  if printf '%s' "$out" | grep -Eqi 'protect|chunk|store|toggle|unclaim|claim'; then
    echo "--- $c ---"
    printf '%s\n' "$out"
  fi
done
