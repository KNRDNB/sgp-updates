#!/usr/bin/env bash
set -euo pipefail
JAR=/tmp/ftbchunks.jar
python3 - <<'PY'
import urllib.request
u="https://www.cursemaven.com/curse/maven/ftb-chunks-forge-314906/8791113/ftb-chunks-forge-314906-8791113.jar"
urllib.request.urlretrieve(u,"/tmp/ftbchunks.jar")
PY
sha1sum "$JAR"
stat -c '%s' "$JAR"
jar tf "$JAR" | grep 'ClaimedChunkEvent' || true
javap -classpath "$JAR" -p -c -v dev.ftb.mods.ftbchunks.api.event.ClaimedChunkEvent
javap -classpath "$JAR" -p -c -v 'dev.ftb.mods.ftbchunks.api.event.ClaimedChunkEvent$After'
