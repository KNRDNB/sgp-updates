#!/usr/bin/env bash
set -euo pipefail

ROOT="release-staging/2.0.11-test.1"
MOD="SGP-Wands-Paxel-Compat-1.0.1.jar"

rm -rf .paxel-id-harness
mkdir -p .paxel-id-harness
javac -encoding UTF-8 -source 21 -target 21 -d .paxel-id-harness   "$ROOT/compatmod/src/main/java/sgp/wandspaxel/PaxelIds.java"   "$ROOT/test-harness/sgp/wandspaxel/PaxelIdsHarness.java"
java -ea -cp .paxel-id-harness sgp.wandspaxel.PaxelIdsHarness

gradle -p "$ROOT/compatmod" build --no-daemon --stacktrace
cp "$ROOT/compatmod/build/libs/$MOD" "$MOD"

unzip -t "$MOD" >/dev/null
unzip -l "$MOD" > paxel-compat-files.txt

grep -Fq 'META-INF/neoforge.mods.toml' paxel-compat-files.txt
grep -Fq 'sgp_wands_paxel_compat.mixins.json' paxel-compat-files.txt
grep -Fq 'sgp/wandspaxel/PaxelIds.class' paxel-compat-files.txt
grep -Fq 'net/nicguzzo/wands/wand/SgpWandsPaxelCompatMixin.class' paxel-compat-files.txt
! grep -Fq 'net/nicguzzo/wands/wand/Wand.class' paxel-compat-files.txt

unzip -p "$MOD" META-INF/neoforge.mods.toml > paxel-compat-mod.toml
grep -Fq 'modId="sgp_wands_paxel_compat"' paxel-compat-mod.toml
grep -Fq 'version="1.0.1"' paxel-compat-mod.toml
grep -Fq 'modId="wands"' paxel-compat-mod.toml
grep -Fq 'versionRange="[3.0.5,3.0.6)"' paxel-compat-mod.toml
grep -Fq 'modId="create_ironworks"' paxel-compat-mod.toml
grep -Fq 'versionRange="[4.0.3,4.1)"' paxel-compat-mod.toml

javap -classpath "$MOD" -p -v sgp.wandspaxel.PaxelIds > paxel-ids-javap.txt
javap -classpath "$MOD" -p -v net.nicguzzo.wands.wand.SgpWandsPaxelCompatMixin > paxel-mixin-javap.txt

grep -Fq 'major version: 65' paxel-mixin-javap.txt
for p in copper bronze brass iron gold diamond steel netherite; do
  grep -Fq "${p}_paxel" paxel-ids-javap.txt
done
grep -Fq 'create_ironworks' paxel-ids-javap.txt
grep -Fq 'can_dig' paxel-mixin-javap.txt
grep -Fq 'can_destroy_or_use' paxel-mixin-javap.txt
grep -Fq 'place_block' paxel-mixin-javap.txt
grep -Fq 'TransparentBlock' paxel-mixin-javap.txt
grep -Fq 'SnowLayerBlock' paxel-mixin-javap.txt
grep -Fq 'isCorrectForDrops' paxel-mixin-javap.txt
grep -Fq 'can_axe_use' paxel-mixin-javap.txt
grep -Fq 'is_flattenable' paxel-mixin-javap.txt

sha256sum "$MOD" | tee paxel_compat_sha.txt
stat -c '%s' "$MOD" | tee paxel_compat_size.txt

echo SGP_WANDS_PAXEL_COMPAT_101_BUILD_STATIC_PASS
