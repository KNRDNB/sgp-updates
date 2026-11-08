#!/usr/bin/env bash
set -euo pipefail
ROOT="release-staging/2.1.0-test.1"
MOD="SGP-Wands-Paxel-Compat-1.0.3.jar"

mkdir -p .paxel103-harness
javac -encoding UTF-8 -source 21 -target 21 -d .paxel103-harness \
  "$ROOT/compatmod/src/main/java/sgp/wandspaxel/PaxelIds.java" \
  "$ROOT/compatmod/src/main/java/sgp/wandspaxel/PaxelRules.java" \
  "$ROOT/test-harness/sgp/wandspaxel/PaxelRulesHarness.java"
java -ea -cp .paxel103-harness sgp.wandspaxel.PaxelRulesHarness

gradle -p "$ROOT/compatmod" build --no-daemon --stacktrace
cp "$ROOT/compatmod/build/libs/$MOD" "$MOD"

unzip -t "$MOD" >/dev/null
unzip -Z1 "$MOD" | tee paxel103-files.txt
for p in META-INF/neoforge.mods.toml sgp_wands_paxel_compat.mixins.json \
 sgp/wandspaxel/PaxelIds.class sgp/wandspaxel/PaxelRules.class \
 sgp/wandspaxel/mixin/SgpWandsPaxelCompatMixin.class; do
    grep -Fxq "$p" paxel103-files.txt
done
! grep -E '^net/nicguzzo/wands/|^create_ironworks/' paxel103-files.txt
unzip -p "$MOD" META-INF/neoforge.mods.toml | tee paxel103-mods.toml
grep -Fq 'version="1.0.3"' paxel103-mods.toml
grep -Fq 'versionRange="[3.0.5,3.0.6)"' paxel103-mods.toml
grep -Fq 'versionRange="[4.0.3,4.1)"' paxel103-mods.toml
unzip -p "$MOD" sgp_wands_paxel_compat.mixins.json > paxel103-mixins.json
grep -Fq '"package": "sgp.wandspaxel.mixin"' paxel103-mixins.json
grep -Fq '"defaultRequire": 1' paxel103-mixins.json
javap -p -v -classpath "$MOD" sgp.wandspaxel.mixin.SgpWandsPaxelCompatMixin > paxel103-mixin-javap.txt
grep -Fq 'major version: 65' paxel103-mixin-javap.txt
for p in can_dig can_destroy_or_use place_block Redirect \
 useOn isCorrectToolForDrops getDestroySpeed getToolModifiedState \
 AXE_STRIP AXE_SCRAPE AXE_WAX_OFF SHOVEL_FLATTEN getIntArray Tools \
 PaxelRules TransparentBlock SnowLayerBlock setBlockAndUpdate; do
  grep -Fq "$p" paxel103-mixin-javap.txt || { echo "Missing mixin symbol: $p"; exit 1; }
done
! grep -Fq 'HOE_TILL' paxel103-mixin-javap.txt
! grep -Fq 'SHEARS_' paxel103-mixin-javap.txt

sha256sum "$MOD" | tee paxel103-sha.txt
stat -c '%s' "$MOD" | tee paxel103-size.txt
echo "PAXEL_103_BUILD_RULES_COMPILED_BYTECODE_PASS"
