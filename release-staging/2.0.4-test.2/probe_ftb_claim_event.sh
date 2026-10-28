#!/usr/bin/env bash
set -euo pipefail

JAR=/tmp/ftbchunks-2101.1.22.jar
URL="https://www.cursemaven.com/curse/maven/ftb-chunks-forge-314906/8791113/ftb-chunks-forge-314906-8791113.jar"
EXPECTED_SHA1="a53f1bb7965c6954a348d4f321f03d3971ad503f"
EXPECTED_SIZE="655807"

python3 - <<'PY'
import urllib.request
u="https://www.cursemaven.com/curse/maven/ftb-chunks-forge-314906/8791113/ftb-chunks-forge-314906-8791113.jar"
urllib.request.urlretrieve(u,"/tmp/ftbchunks-2101.1.22.jar")
PY

test "$(stat -c '%s' "$JAR")" = "$EXPECTED_SIZE"
test "$(sha1sum "$JAR" | awk '{print $1}')" = "$EXPECTED_SHA1"
unzip -t "$JAR" >/dev/null

jar tf "$JAR" | grep -Fxq 'dev/ftb/mods/ftbchunks/api/event/ClaimedChunkEvent.class'
jar tf "$JAR" | grep -Fxq 'dev/ftb/mods/ftbchunks/api/event/ClaimedChunkEvent$After.class'

javap -classpath "$JAR" -p dev.ftb.mods.ftbchunks.api.event.ClaimedChunkEvent > /tmp/claimed-event.txt
javap -classpath "$JAR" -p 'dev.ftb.mods.ftbchunks.api.event.ClaimedChunkEvent$After' > /tmp/claimed-after.txt

grep -Fq 'AFTER_CLAIM' /tmp/claimed-event.txt
grep -Fq 'AFTER_UNCLAIM' /tmp/claimed-event.txt
grep -Fq ' after(' /tmp/claimed-after.txt

echo "FTB_CHUNKS_2101_1_22_AFTER_CLAIM_API_PASS"
