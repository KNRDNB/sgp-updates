#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
BASE_TAG="v1.8.2"
BASE_ASSET="SGP_ClientPatch_1.8.2.zip"
BASE_SHA="d98e8a24eb297e6caea115e5e758d34c9237c0b7c294c0a804ac08282a2f83cd"
TAG="v1.9.0"
ASSET="SGP_ClientPatch_1.9.0.zip"
MOD_JAR="SGP-Shapeless-Nether-Portals-1.0.0.jar"
SERVER_BASE_ARTIFACT_ID="11361553958"
SERVER_BASE_SHA="2dc63bc7122fc9d0fe033bc063d6cd5d7a8fb5f64e2ed2ea236fe083cc99b571"

if gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1; then
  echo "Stable release already exists" >&2
  exit 1
fi

gh release download "$BASE_TAG" --repo "$REPO" -p "$BASE_ASSET"
echo "$BASE_SHA  $BASE_ASSET" | sha256sum -c -
unzip -t "$BASE_ASSET" >/dev/null

gh api "repos/$REPO/actions/artifacts/$SERVER_BASE_ARTIFACT_ID/zip" > server122-artifact.zip
unzip -t server122-artifact.zip >/dev/null
unzip -o server122-artifact.zip -d server122-artifact >/dev/null
cp server122-artifact/SGP_ServerPatch_1.2.2.zip .
echo "$SERVER_BASE_SHA  SGP_ServerPatch_1.2.2.zip" | sha256sum -c -
unzip -t SGP_ServerPatch_1.2.2.zip >/dev/null

gradle -p release-staging/1.9.0/portalmod build --no-daemon --stacktrace
cp release-staging/1.9.0/portalmod/build/libs/SGP-Shapeless-Nether-Portals-1.0.0.jar "$MOD_JAR"
unzip -t "$MOD_JAR" >/dev/null

# Exact MC/NeoForge target descriptor validation.
CP="$(gradle -q -p release-staging/1.9.0/portalmod printRuntimeClasspath --no-daemon | tail -n 1)"
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

unzip -l "$MOD_JAR" > portalmod-files.txt
grep -Fq 'META-INF/NOTICE-NICER-PORTALS.txt' portalmod-files.txt
grep -Fq 'sgp_shapeless_nether_portals.mixins.json' portalmod-files.txt
grep -Fq 'sgp/shapelessportals/mixin/PortalShapeMixin.class' portalmod-files.txt
grep -Fq 'sgp/shapelessportals/mixin/PortalShapeAccessor.class' portalmod-files.txt
unzip -p "$MOD_JAR" META-INF/neoforge.mods.toml > portalmod.toml
grep -Fq 'modId="sgp_shapeless_nether_portals"' portalmod.toml
grep -Fq 'versionRange="[21.1.249,21.2)"' portalmod.toml
! grep -Eqi 'architectury|nightlib' portalmod.toml

javap -classpath "$CP:$MOD_JAR" -p -v sgp.shapelessportals.mixin.PortalShapeMixin > portal-mixin.txt
grep -Fq 'major version: 65' portal-mixin.txt
javap -classpath "$CP:$MOD_JAR" -p -c sgp.shapelessportals.mixin.PortalShapeMixin > portal-mixin-code.txt
grep -Fq 'sipush        2304' portal-mixin-code.txt || grep -Fq '2304' portal-mixin-code.txt
grep -Fq 'BlockBehaviour$StatePredicate.test' portal-mixin-code.txt
grep -Fq 'LevelAccessor.setBlock' portal-mixin-code.txt
echo PORTALMOD_RELEASE_STATIC_VALIDATION_PASS

python3 release-staging/1.9.0/build_client_190.py | tee client-build.txt
python3 release-staging/1.9.0/build_server_130.py | tee server-build.txt

python3 - <<'PY'
import hashlib,io,json,zipfile
accepted=[
 '1.0.0','1.0.1','1.0.2','1.0.3','1.1.0','1.2.0','1.2.1',
 '1.3.0','1.3.1','1.3.2','1.3.3','1.4.0','1.5.0','1.5.1','1.5.2','1.5.3',
 '1.6.0','1.6.1','1.6.2','1.7.0','1.7.1','1.8.0','1.8.1','1.8.2'
]
mod_target='mods/SGP-Shapeless-Nether-Portals-1.0.0.jar'
with zipfile.ZipFile('SGP_ClientPatch_1.9.0.zip') as z:
    assert z.testzip() is None
    p=json.loads(z.read('patch.json'))
    assert p['patchId']=='sgp-client-1.9.0'
    assert p['toVersion']=='1.9.0'
    for v in accepted: assert v in p['fromVersions'],v
    assert p['fromVersions'][-1]=='1.8.2'
    assert '1.5.4' not in p['fromVersions']
    acts=[a for a in p['actions'] if a.get('type')=='copy' and a.get('target')==mod_target]
    assert len(acts)==1
    b=z.read(acts[0]['source'])
    assert hashlib.sha256(b).hexdigest()==acts[0]['sha256']
    assert len(b)==acts[0]['size']
    with zipfile.ZipFile(io.BytesIO(b)) as mz:
        assert mz.testzip() is None
        assert 'META-INF/NOTICE-NICER-PORTALS.txt' in mz.namelist()

with zipfile.ZipFile('SGP_ServerPatch_1.3.0.zip') as z:
    assert z.testzip() is None
    assert sorted(z.namelist())==sorted([
      '.sgp/pack.json','.sgp/history.json',
      'config/curios-common.toml',
      'config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip',
      'mods/SGP-Apotheosis-Soulbound-Compat-1.0.0.jar',
      mod_target
    ])
    pack=json.loads(z.read('.sgp/pack.json'))
    hist=json.loads(z.read('.sgp/history.json'))
    assert pack['version']=='1.3.0'
    assert hist['currentVersion']=='1.3.0'
    assert [e['version'] for e in hist['entries']]==['1.0.0','1.2.0','1.2.1','1.3.0']
print('RELEASE_190_SERVER_130_EXACT_PACKAGE_AUDIT_PASS')
PY

SHA="$(sha256sum "$ASSET" | awk '{print $1}')"
SIZE="$(stat -c %s "$ASSET")"
MOD_SHA="$(cat portal_mod_sha.txt)"
MOD_SIZE="$(cat portal_mod_size.txt)"
SERVER_SHA="$(cat server130_sha.txt)"
SERVER_SIZE="$(cat server130_size.txt)"

{
  echo '## SGP Client 1.9.0'
  echo
  echo 'Direct stable release explicitly requested by the owner; separate Minecraft TEST runtime gate was waived for this release.'
  echo
  echo '- Adds **SGP Shapeless Nether Portals 1.0.0**.'
  echo '- Enclosed vertical obsidian Nether portal frames may be built in arbitrary shapes (circles, arches, irregular outlines, etc.).'
  echo '- Maximum scanned portal interior: 2304 blocks.'
  echo '- Uses vanilla Nether portal blocks and vanilla travel/linking; no worldgen change.'
  echo '- No external library dependencies.'
  echo '- Portal-shape implementation adapts MIT-licensed Nicer Portals logic and ships the required attribution notice.'
  echo '- Cumulative direct update from every accepted stable client through **1.8.2**.'
  echo
  printf 'Portal mod SHA-256: %s (%s bytes)\n' "$MOD_SHA" "$MOD_SIZE"
  printf 'Client SHA-256: %s (%s bytes)\n' "$SHA" "$SIZE"
  printf 'Matching server 1.3.0 SHA-256: %s (%s bytes)\n' "$SERVER_SHA" "$SERVER_SIZE"
} > notes.md

gh release create "$TAG" "$ASSET" --repo "$REPO" --target "$GITHUB_SHA"   --title 'SGP Client 1.9.0' --notes-file notes.md

REL="$(gh api "repos/$REPO/releases/tags/$TAG")"
test "$(printf '%s' "$REL" | jq -r '.draft')" = 'false'
test "$(printf '%s' "$REL" | jq -r '.prerelease')" = 'false'
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
import hashlib,io,json,zipfile
with zipfile.ZipFile('verify.zip') as z:
    assert z.testzip() is None
    p=json.loads(z.read('patch.json'))
    assert p['patchId']=='sgp-client-1.9.0'
    assert p['toVersion']=='1.9.0'
    assert p['fromVersions'][-1]=='1.8.2'
    a=next(a for a in p['actions'] if a.get('target')=='mods/SGP-Shapeless-Nether-Portals-1.0.0.jar')
    b=z.read(a['source'])
    assert hashlib.sha256(b).hexdigest()==a['sha256']
    with zipfile.ZipFile(io.BytesIO(b)) as mz:
        assert mz.testzip() is None
        assert 'sgp/shapelessportals/mixin/PortalShapeMixin.class' in mz.namelist()
        assert 'META-INF/NOTICE-NICER-PORTALS.txt' in mz.namelist()
print('LIVE_STABLE_190_VERIFY_PASS')
PY

echo "PUBLISHED_RELEASE_ID=$RID"
echo "PUBLISHED_ASSET_ID=$AID"
echo "PUBLISHED_SHA=$SHA"
echo "PUBLISHED_SIZE=$SIZE"
echo "PORTAL_MOD_SHA=$MOD_SHA"
echo "PORTAL_MOD_SIZE=$MOD_SIZE"
echo "SERVER_SHA=$SERVER_SHA"
echo "SERVER_SIZE=$SERVER_SIZE"
