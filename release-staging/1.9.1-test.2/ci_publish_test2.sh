#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
BASE_TAG="v1.8.2"
BASE_ASSET="SGP_ClientPatch_1.8.2.zip"
BASE_SHA="d98e8a24eb297e6caea115e5e758d34c9237c0b7c294c0a804ac08282a2f83cd"

TAG="v1.9.1-test.2"
ASSET="SGP_ClientPatch_1.9.1-test.2.zip"
PORTAL_JAR="SGP-Shapeless-Nether-Portals-1.1.1.jar"

SERVER_BASE_ARTIFACT_ID="11361553958"
SERVER_BASE_SHA="2dc63bc7122fc9d0fe033bc063d6cd5d7a8fb5f64e2ed2ea236fe083cc99b571"

# Retired/superseded public identities must remain absent.
! gh api "repos/$REPO/releases/tags/v1.9.0" >/dev/null 2>&1
! gh api "repos/$REPO/git/ref/tags/v1.9.0" >/dev/null 2>&1
! gh api "repos/$REPO/releases/tags/v1.9.1-test.1" >/dev/null 2>&1
! gh api "repos/$REPO/git/ref/tags/v1.9.1-test.1" >/dev/null 2>&1

if gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1; then
  echo "TEST release already exists" >&2
  exit 1
fi

gh release download "$BASE_TAG" --repo "$REPO" -p "$BASE_ASSET"
echo "$BASE_SHA  $BASE_ASSET" | sha256sum -c -
unzip -t "$BASE_ASSET" >/dev/null

# Recover exact never-installed 1.2.2 server payload only as a cumulative content base.
gh api "repos/$REPO/actions/artifacts/$SERVER_BASE_ARTIFACT_ID/zip" > server122-artifact.zip
unzip -t server122-artifact.zip >/dev/null
rm -rf server122-artifact
mkdir server122-artifact
unzip -o server122-artifact.zip -d server122-artifact >/dev/null
test -f server122-artifact/SGP_ServerPatch_1.2.2.zip
cp server122-artifact/SGP_ServerPatch_1.2.2.zip SGP_ServerPatch_1.2.2.zip
echo "$SERVER_BASE_SHA  SGP_ServerPatch_1.2.2.zip" | sha256sum -c -
unzip -t SGP_ServerPatch_1.2.2.zip >/dev/null

# Build exact final portal mod from immutable TEST2 source.
gradle -p release-staging/1.9.1-test.2/portalmod build --no-daemon --stacktrace
cp release-staging/1.9.1-test.2/portalmod/build/libs/SGP-Shapeless-Nether-Portals-1.1.1.jar "$PORTAL_JAR"
unzip -t "$PORTAL_JAR" >/dev/null

# Exact Minecraft 1.21.1 / NeoForge 21.1.249 target preflight.
CP="$(gradle -q -p release-staging/1.9.1-test.2/portalmod printRuntimeClasspath --no-daemon | tail -n 1)"

javap -classpath "$CP" -p -s net.minecraft.world.level.portal.PortalShape > portalshape.txt
grep -Fq 'public net.minecraft.world.level.portal.PortalShape(net.minecraft.world.level.LevelAccessor, net.minecraft.core.BlockPos, net.minecraft.core.Direction$Axis);' portalshape.txt
grep -A2 -F 'public boolean isValid();' portalshape.txt | grep -Fq 'descriptor: ()Z'
grep -A2 -F 'public boolean isComplete();' portalshape.txt | grep -Fq 'descriptor: ()Z'
grep -A2 -F 'public void createPortalBlocks();' portalshape.txt | grep -Fq 'descriptor: ()V'
grep -A2 -F 'private static boolean isEmpty(net.minecraft.world.level.block.state.BlockState);' portalshape.txt | grep -Fq 'descriptor: (Lnet/minecraft/world/level/block/state/BlockState;)Z'
grep -Fq 'private final net.minecraft.world.level.LevelAccessor level;' portalshape.txt
grep -Fq 'private final net.minecraft.core.Direction$Axis axis;' portalshape.txt
grep -Fq 'private final net.minecraft.core.Direction rightDir;' portalshape.txt
grep -Fq 'private static final net.minecraft.world.level.block.state.BlockBehaviour$StatePredicate FRAME;' portalshape.txt

javap -classpath "$CP" -p -c -s net.minecraft.world.level.block.BaseFireBlock > basefire.txt
grep -A2 -F 'private static boolean isPortal(net.minecraft.world.level.Level, net.minecraft.core.BlockPos, net.minecraft.core.Direction);' basefire.txt | grep -Fq 'descriptor: (Lnet/minecraft/world/level/Level;Lnet/minecraft/core/BlockPos;Lnet/minecraft/core/Direction;)Z'
grep -Fq 'BlockState.isPortalFrame' basefire.txt
grep -Fq 'PortalShape.findEmptyPortalShape' basefire.txt

javap -classpath "$CP" -p -c -s net.minecraft.world.level.block.NetherPortalBlock > netherportalblock.txt
grep -A2 -F 'protected void randomTick(net.minecraft.world.level.block.state.BlockState, net.minecraft.server.level.ServerLevel, net.minecraft.core.BlockPos, net.minecraft.util.RandomSource);' netherportalblock.txt | grep -Fq 'descriptor: (Lnet/minecraft/world/level/block/state/BlockState;Lnet/minecraft/server/level/ServerLevel;Lnet/minecraft/core/BlockPos;Lnet/minecraft/util/RandomSource;)V'
grep -Fq 'EntityType.ZOMBIFIED_PIGLIN' netherportalblock.txt
grep -Fq 'EntityType.spawn' netherportalblock.txt

# Final-JAR mixin / classfile / attribution preflight.
unzip -l "$PORTAL_JAR" > portal-jar-files.txt
grep -Fq 'sgp/shapelessportals/mixin/PortalShapeMixin.class' portal-jar-files.txt
grep -Fq 'sgp/shapelessportals/mixin/PortalShapeAccessor.class' portal-jar-files.txt
grep -Fq 'sgp/shapelessportals/mixin/BaseFireBlockMixin.class' portal-jar-files.txt
grep -Fq 'sgp/shapelessportals/mixin/NetherPortalBlockMixin.class' portal-jar-files.txt
grep -Fq 'META-INF/NOTICE-NICER-PORTALS.txt' portal-jar-files.txt
grep -Fq 'sgp_shapeless_nether_portals.mixins.json' portal-jar-files.txt

unzip -p "$PORTAL_JAR" META-INF/neoforge.mods.toml > portal-mod.toml
grep -Fq 'version="1.1.1"' portal-mod.toml
grep -Fq 'modId="sgp_shapeless_nether_portals"' portal-mod.toml
grep -Fq 'versionRange="[21.1.249,21.2)"' portal-mod.toml
grep -Fq 'versionRange="[1.21.1]"' portal-mod.toml

unzip -p "$PORTAL_JAR" sgp_shapeless_nether_portals.mixins.json > portal-mixins.json
grep -Fq '"BaseFireBlockMixin"' portal-mixins.json
grep -Fq '"NetherPortalBlockMixin"' portal-mixins.json
grep -Fq '"PortalShapeAccessor"' portal-mixins.json
grep -Fq '"PortalShapeMixin"' portal-mixins.json

javap -classpath "$PORTAL_JAR" -p -v sgp.shapelessportals.mixin.PortalShapeMixin > portalshape-mixin.txt
grep -Fq 'major version: 65' portalshape-mixin.txt
grep -Fq 'CRYING_OBSIDIAN' portalshape-mixin.txt
grep -Fq 'createPortalBlocks' portalshape-mixin.txt

javap -classpath "$PORTAL_JAR" -p -v sgp.shapelessportals.mixin.BaseFireBlockMixin > basefire-mixin.txt
grep -Fq 'BaseFireBlock' basefire-mixin.txt
grep -Fq 'isPortal' basefire-mixin.txt
grep -Fq 'isPortalFrame' basefire-mixin.txt
grep -Fq 'CRYING_OBSIDIAN' basefire-mixin.txt

javap -classpath "$PORTAL_JAR" -p -v sgp.shapelessportals.mixin.NetherPortalBlockMixin > netherportal-mixin.txt
grep -Fq 'NetherPortalBlock' netherportal-mixin.txt
grep -Fq 'randomTick' netherportal-mixin.txt
grep -Fq 'ZOMBIFIED_PIGLIN' netherportal-mixin.txt
grep -Fq 'EntityType.spawn' netherportal-mixin.txt

echo PORTALMOD_111_FINAL_PREFLIGHT_PASS

python3 release-staging/1.9.1-test.2/build_client_191_test2.py | tee client-build.txt
python3 release-staging/1.9.1-test.2/build_server_132.py | tee server-build.txt

python3 - <<'PY'
import hashlib, json, zipfile

accepted=[
 "1.0.0","1.0.1","1.0.2","1.0.3",
 "1.1.0","1.2.0","1.2.1",
 "1.3.0","1.3.1","1.3.2","1.3.3",
 "1.4.0","1.5.0","1.5.1","1.5.2","1.5.3",
 "1.6.0","1.6.1","1.6.2",
 "1.7.0","1.7.1","1.8.0","1.8.1","1.8.2"
]
with zipfile.ZipFile('SGP_ClientPatch_1.9.1-test.2.zip') as z:
    assert z.testzip() is None
    p=json.loads(z.read('patch.json'))
    assert p['patchId']=='sgp-client-1.9.1-test.2'
    assert p['toVersion']=='1.9.1-test.2'
    for v in accepted:
        assert v in p['fromVersions'],v
    assert p['fromVersions'][-2:]==['1.9.0','1.9.1-test.1']
    assert '1.5.4' not in p['fromVersions']
    for old in [
        'mods/SGP-Shapeless-Nether-Portals-1.0.0.jar',
        'mods/SGP-Shapeless-Nether-Portals-1.1.0.jar'
    ]:
        assert any(a.get('type')=='delete'
                   and a.get('target')==old
                   and a.get('optional') is True for a in p['actions'])
    mod=next(a for a in p['actions']
             if a.get('target')=='mods/SGP-Shapeless-Nether-Portals-1.1.1.jar')
    b=z.read(mod['source'])
    assert len(b)==mod['size']
    assert hashlib.sha256(b).hexdigest()==mod['sha256']

with zipfile.ZipFile('SGP_ServerPatch_1.3.2.zip') as z:
    assert z.testzip() is None
    assert sorted(z.namelist())==sorted([
      '.sgp/pack.json','.sgp/history.json',
      'config/curios-common.toml',
      'config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip',
      'mods/SGP-Apotheosis-Soulbound-Compat-1.0.0.jar',
      'mods/SGP-Shapeless-Nether-Portals-1.1.1.jar'
    ])
    assert json.loads(z.read('.sgp/pack.json'))['version']=='1.3.2'
    h=json.loads(z.read('.sgp/history.json'))
    assert h['currentVersion']=='1.3.2'
    assert [e['version'] for e in h['entries']]==['1.0.0','1.2.0','1.2.1','1.3.2']
print('TEST191_TEST2_EXACT_PACKAGE_AUDIT_PASS')
PY

SHA="$(sha256sum "$ASSET" | awk '{print $1}')"
MOD_SHA="$(cat portal_mod_sha.txt)"
MOD_SIZE="$(cat portal_mod_size.txt)"
SERVER_SHA="$(cat server132_sha.txt)"

{
  echo '## SGP Client 1.9.1-test.2'
  echo
  echo 'Runtime TEST for SGP Shapeless Nether Portals 1.1.1.'
  echo
  echo '- Arbitrary enclosed vertical Nether portal shapes.'
  echo '- Obsidian + crying obsidian frame support, including mixed frames and ignition.'
  echo '- Suppresses only the exact vanilla zombified-piglin spawn call from NetherPortalBlock.randomTick.'
  echo '- Keeps vanilla nether_portal blocks, travel and portal linking.'
  echo '- Forward-repairs deleted 1.9.0 and superseded 1.9.1-test.1 by deleting portal mods 1.0.0/1.1.0.'
  echo '- Matching server 1.3.2 is CI evidence only and is NOT handed off until owner client runtime PASS.'
  echo
  printf 'Portal mod 1.1.1 SHA-256: %s (%s bytes)\n' "$MOD_SHA" "$MOD_SIZE"
  printf 'Client TEST SHA-256: %s\n' "$SHA"
  printf 'Withheld server 1.3.2 SHA-256: %s\n' "$SERVER_SHA"
} > notes.md

gh release create "$TAG" "$ASSET" --repo "$REPO" --target "$GITHUB_SHA" \
  --title 'SGP Client 1.9.1-test.2' --notes-file notes.md --prerelease

REL="$(gh api "repos/$REPO/releases/tags/$TAG")"
test "$(printf '%s' "$REL" | jq -r '.draft')" = 'false'
test "$(printf '%s' "$REL" | jq -r '.prerelease')" = 'true'
RID="$(printf '%s' "$REL" | jq -r '.id')"
ASSETS="$(gh api "repos/$REPO/releases/$RID/assets")"
test "$(printf '%s' "$ASSETS" | jq 'length')" = '1'
test "$(printf '%s' "$ASSETS" | jq -r '.[0].name')" = "$ASSET"
test "$(printf '%s' "$ASSETS" | jq -r '.[0].digest')" = "sha256:$SHA"
AID="$(printf '%s' "$ASSETS" | jq -r '.[0].id')"

gh api -H 'Accept: application/octet-stream' "repos/$REPO/releases/assets/$AID" > verify.zip
echo "$SHA  verify.zip" | sha256sum -c -
unzip -t verify.zip >/dev/null

python3 - <<'PY'
import hashlib,json,zipfile
with zipfile.ZipFile('verify.zip') as z:
    assert z.testzip() is None
    p=json.loads(z.read('patch.json'))
    assert p['patchId']=='sgp-client-1.9.1-test.2'
    assert p['toVersion']=='1.9.1-test.2'
    assert p['fromVersions'][-2:]==['1.9.0','1.9.1-test.1']
    for old in [
        'mods/SGP-Shapeless-Nether-Portals-1.0.0.jar',
        'mods/SGP-Shapeless-Nether-Portals-1.1.0.jar'
    ]:
        assert any(a.get('type')=='delete' and a.get('target')==old for a in p['actions'])
    mod=next(a for a in p['actions']
             if a.get('target')=='mods/SGP-Shapeless-Nether-Portals-1.1.1.jar')
    b=z.read(mod['source'])
    assert hashlib.sha256(b).hexdigest()==mod['sha256']
print('LIVE_CLIENT_191_TEST2_VERIFY_PASS')
PY

echo "PUBLISHED_RELEASE_ID=$RID"
echo "PUBLISHED_ASSET_ID=$AID"
echo "PUBLISHED_SHA=$SHA"
echo "MOD_SHA=$MOD_SHA"
echo "MOD_SIZE=$MOD_SIZE"
echo "SERVER_SHA=$SERVER_SHA"
