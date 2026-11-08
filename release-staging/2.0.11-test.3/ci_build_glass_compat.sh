#!/usr/bin/env bash
set -euo pipefail

GLASS_ROOT="release-staging/2.0.11-test.3/glasscompat"
GLASS_JAR="SGP-BetterNether-Quartz-Glass-Compat-1.0.0.jar"

rm -rf .glass-id-harness
mkdir -p .glass-id-harness
javac -encoding UTF-8 -source 21 -target 21 -d .glass-id-harness   "$GLASS_ROOT/src/main/java/sgp/glasscompat/QuartzGlassIds.java"   "$GLASS_ROOT/test-harness/sgp/glasscompat/QuartzGlassIdsHarness.java"
java -ea -cp .glass-id-harness sgp.glasscompat.QuartzGlassIdsHarness

gradle -p "$GLASS_ROOT" build --no-daemon --stacktrace
cp "$GLASS_ROOT/build/libs/$GLASS_JAR" "$GLASS_JAR"

unzip -t "$GLASS_JAR" >/dev/null
unzip -l "$GLASS_JAR" > glass-compat-files.txt
grep -Fq 'sgp/glasscompat/QuartzGlassIds.class' glass-compat-files.txt
grep -Fq 'sgp/glasscompat/mixin/SodiumNeoForgeBlockAccessMixin.class' glass-compat-files.txt
grep -Fq 'sgp_betternether_quartz_glass_compat.mixins.json' glass-compat-files.txt
! grep -Eq 'assets/betternether/|textures/|net/caffeinemc/mods/sodium/|org/betterx/' glass-compat-files.txt

unzip -p "$GLASS_JAR" sgp_betternether_quartz_glass_compat.mixins.json > glass-mixins.json
grep -Fq '"package": "sgp.glasscompat.mixin"' glass-mixins.json
grep -Fq '"SodiumNeoForgeBlockAccessMixin"' glass-mixins.json

javap -classpath "$GLASS_JAR" -p -v sgp.glasscompat.QuartzGlassIds > glass-ids-javap.txt
javap -classpath "$GLASS_JAR" -p -v sgp.glasscompat.mixin.SodiumNeoForgeBlockAccessMixin > glass-mixin-javap.txt
grep -Fq 'major version: 65' glass-mixin-javap.txt
grep -Fq 'net.caffeinemc.mods.sodium.neoforge.block.NeoForgeBlockAccess' glass-mixin-javap.txt
grep -Fq 'shouldShowFluidOverlay' glass-mixin-javap.txt
grep -Fq 'FluidTags' glass-mixin-javap.txt
grep -Fq 'WATER' glass-mixin-javap.txt
grep -Fq 'betternether' glass-ids-javap.txt
grep -Fq 'quartz_glass_framed_pane' glass-ids-javap.txt
grep -Fq 'black' glass-ids-javap.txt

sha256sum "$GLASS_JAR" | tee glass_compat_sha.txt
stat -c '%s' "$GLASS_JAR" | tee glass_compat_size.txt
echo SGP_BETTERNETHER_QUARTZ_GLASS_COMPAT_100_BUILD_STATIC_PASS
