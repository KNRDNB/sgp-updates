#!/usr/bin/env bash
set -euo pipefail

CAND_RUN="41298462300"
CAND_ART="sgp-2.0.10-candidates"
RU="regions-unexplored-0.6.3-neoforge-21.1.jar"
MOON="moonlight-1.21.1-3.6.5-neoforge.jar"

rm -rf probe candidates
mkdir -p probe candidates
gh run download "$CAND_RUN" --repo KNRDNB/sgp-updates --name "$CAND_ART" --dir candidates

cp candidates/lithostitched-1.8.1-neoforge-21.1.jar probe/
cp candidates/everycomp-1.21-2.11.55-neoforge.jar probe/
curl -fL --retry 3 --retry-delay 2 "https://mediafilez.forgecdn.net/files/9252/522/$RU" -o "probe/$RU"
curl -fL --retry 3 --retry-delay 2 "https://mediafilez.forgecdn.net/files/8905/916/$MOON" -o "probe/$MOON"

python3 - <<'PY'
import zipfile, pathlib, hashlib
base=pathlib.Path("probe")
ru=base/"regions-unexplored-0.6.3-neoforge-21.1.jar"
assert hashlib.sha256(ru.read_bytes()).hexdigest()=="e7f2edd7bab869c2e566b1b251ea54c6b95834205276bf3a302859d72d9d0c9b"
with zipfile.ZipFile(ru) as z:
    assert "net/regions_unexplored/block/type/shrub/ShrubBlock.class" in z.namelist()
    assert "net/regions_unexplored/world/level/block/plant/tall/ShrubBlock.class" not in z.namelist()
    deps=z.read("META-INF/neoforge.mods.toml").decode("utf-8","replace")
    assert 'modId = "lithostitched"' in deps and 'versionRange = "[1.8.0,)"' in deps

ec=base/"everycomp-1.21-2.11.55-neoforge.jar"
with zipfile.ZipFile(ec) as z:
    old=b"net/regions_unexplored/world/level/block/plant/tall/ShrubBlock"
    new=b"net/regions_unexplored/block/type/shrub/ShrubBlock"
    old_hits=[]; new_hits=[]
    for n in z.namelist():
        if n.endswith(".class"):
            b=z.read(n)
            if old in b: old_hits.append(n)
            if new in b: new_hits.append(n)
    print("EVERYCOMP_OLD_SHRUB_REFS",old_hits)
    print("EVERYCOMP_NEW_SHRUB_REFS",new_hits)
    assert not old_hits
    assert new_hits==["net/mehvahdjukaar/every_compat/modules/neoforge/regions_unexplored/RegionsUnexploredModule.class"]

ls=base/"lithostitched-1.8.1-neoforge-21.1.jar"
with zipfile.ZipFile(ls) as z:
    assert "dev/worldgen/lithostitched/impl/worldgen/modifier/target/HolderSetTarget.class" in z.namelist()
    meta=z.read("META-INF/jarjar/metadata.json").decode("utf-8","replace")
    assert "apollib-1.2.0-neoforge-21.1.jar" in meta
PY

cd probe
curl -fL --retry 3 --retry-delay 2 \
  "https://maven.neoforged.net/releases/net/neoforged/neoforge/21.1.249/neoforge-21.1.249-installer.jar" \
  -o neoforge-installer.jar
java -Xmx1G -jar neoforge-installer.jar --installServer >/dev/null
mkdir -p mods
mv lithostitched-1.8.1-neoforge-21.1.jar everycomp-1.21-2.11.55-neoforge.jar "$RU" "$MOON" mods/
echo "eula=true" > eula.txt
cat > server.properties <<'EOF'
online-mode=false
motd=SGP 2.0.10 runtime probe
level-name=sgp210probe
view-distance=2
simulation-distance=2
spawn-protection=0
EOF

set +e
timeout 180s ./run.sh nogui > probe.log 2>&1
rc=$?
set -e
cat probe.log
if ! grep -Fq "Done (" probe.log; then
  echo "SERVER_STARTUP_PROBE_FAIL rc=$rc" >&2
  exit 1
fi
if grep -Fq "Unknown registry key in ResourceKey[minecraft:root / neoforge:holder_set_type]: lithostitched:holder_set" probe.log; then
  echo "Old Lithostitched holder_set failure still present" >&2
  exit 1
fi
if grep -Fq "world/level/block/plant/tall/ShrubBlock" probe.log; then
  echo "Old Every Compat RU ShrubBlock reference still present" >&2
  exit 1
fi
echo "SERVER_STARTUP_PROBE_PASS"
