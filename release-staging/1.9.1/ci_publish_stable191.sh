#!/usr/bin/env bash
set -euo pipefail
REPO="KNRDNB/sgp-updates"
BASE_TAG="v1.8.2"; BASE_ASSET="SGP_ClientPatch_1.8.2.zip"
BASE_SHA="d98e8a24eb297e6caea115e5e758d34c9237c0b7c294c0a804ac08282a2f83cd"
TEST_TAG="v1.9.1-test.3"; TAG="v1.9.1"; ASSET="SGP_ClientPatch_1.9.1.zip"
PORTAL_JAR="SGP-Shapeless-Nether-Portals-1.1.3.jar"
SERVER_BASE_ARTIFACT_ID="11361553958"
SERVER_BASE_SHA="2dc63bc7122fc9d0fe033bc063d6cd5d7a8fb5f64e2ed2ea236fe083cc99b571"

for OLD in v1.9.0 v1.9.1-test.1 v1.9.1-test.2; do
  ! gh api "repos/$REPO/releases/tags/$OLD" >/dev/null 2>&1
  ! gh api "repos/$REPO/git/ref/tags/$OLD" >/dev/null 2>&1
done
TREL="$(gh api "repos/$REPO/releases/tags/$TEST_TAG")"
test "$(printf '%s' "$TREL" | jq -r '.draft')" = false
test "$(printf '%s' "$TREL" | jq -r '.prerelease')" = true
! gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1

gh release download "$BASE_TAG" --repo "$REPO" -p "$BASE_ASSET"
echo "$BASE_SHA  $BASE_ASSET" | sha256sum -c -
unzip -t "$BASE_ASSET" >/dev/null

gh api "repos/$REPO/actions/artifacts/$SERVER_BASE_ARTIFACT_ID/zip" > server122-artifact.zip
unzip -t server122-artifact.zip >/dev/null
unzip -o server122-artifact.zip -d server122-artifact >/dev/null
cp server122-artifact/SGP_ServerPatch_1.2.2.zip .
echo "$SERVER_BASE_SHA  SGP_ServerPatch_1.2.2.zip" | sha256sum -c -
unzip -t SGP_ServerPatch_1.2.2.zip >/dev/null

python3 release-staging/1.9.1/prepare_portal_113.py
P="release-staging/1.9.1/portalmod"
gradle -p "$P" build --no-daemon --stacktrace
cp "$P/build/libs/$PORTAL_JAR" "$PORTAL_JAR"
unzip -t "$PORTAL_JAR" >/dev/null
CP="$(gradle -q -p "$P" printRuntimeClasspath --no-daemon | tail -n 1)"

javap -classpath "$CP" -p -s net.minecraft.world.level.portal.PortalShape > portalshape.txt
grep -Fq 'public net.minecraft.world.level.portal.PortalShape(net.minecraft.world.level.LevelAccessor, net.minecraft.core.BlockPos, net.minecraft.core.Direction$Axis);' portalshape.txt
grep -A2 -F 'public boolean isValid();' portalshape.txt | grep -Fq 'descriptor: ()Z'
grep -A2 -F 'public boolean isComplete();' portalshape.txt | grep -Fq 'descriptor: ()Z'
grep -A2 -F 'public void createPortalBlocks();' portalshape.txt | grep -Fq 'descriptor: ()V'
grep -Fq 'private static final net.minecraft.world.level.block.state.BlockBehaviour$StatePredicate FRAME;' portalshape.txt
javap -classpath "$CP" -p -c -s net.minecraft.world.level.block.NetherPortalBlock > netherportal.txt
grep -Fq 'EntityType.ZOMBIFIED_PIGLIN' netherportal.txt
grep -Fq 'EntityType.spawn' netherportal.txt

unzip -l "$PORTAL_JAR" > jarfiles.txt
grep -Fq 'sgp/shapelessportals/mixin/PortalShapeMixin.class' jarfiles.txt
grep -Fq 'sgp/shapelessportals/mixin/PortalShapeAccessor.class' jarfiles.txt
grep -Fq 'sgp/shapelessportals/mixin/NetherPortalBlockMixin.class' jarfiles.txt
grep -Fq 'META-INF/NOTICE-NICER-PORTALS.txt' jarfiles.txt
! grep -Fq 'PortalFrameRules.class' jarfiles.txt
! grep -Fq 'BaseFireBlockMixin.class' jarfiles.txt
! grep -Fq 'data/c/tags/block/nether_pframe.json' jarfiles.txt
unzip -p "$PORTAL_JAR" META-INF/neoforge.mods.toml > portalmod.toml
grep -Fq 'version="1.1.3"' portalmod.toml
! grep -Eqi 'crying_obsidian|betternether|nether_pframe' portalmod.toml
unzip -p "$PORTAL_JAR" sgp_shapeless_nether_portals.mixins.json > mixins.json
python3 - <<'PY'
import json
m=json.load(open('mixins.json',encoding='utf-8'))
assert m['mixins']==['NetherPortalBlockMixin','PortalShapeAccessor','PortalShapeMixin']
print('PORTALMOD_113_MIXIN_SET_PASS')
PY
javap -classpath "$CP:$PORTAL_JAR" -p -v sgp.shapelessportals.mixin.PortalShapeMixin > pmix.txt
grep -Fq 'major version: 65' pmix.txt
! grep -Fq 'PortalFrameRules' pmix.txt
javap -classpath "$CP:$PORTAL_JAR" -p -c sgp.shapelessportals.mixin.PortalShapeMixin > pmix-code.txt
grep -Fq '2304' pmix-code.txt
grep -Fq 'BlockBehaviour$StatePredicate.test' pmix-code.txt
javap -classpath "$CP:$PORTAL_JAR" -p -v sgp.shapelessportals.mixin.NetherPortalBlockMixin > nmix.txt
grep -Fq 'ZOMBIFIED_PIGLIN' nmix.txt
grep -Fq 'EntityType.spawn' nmix.txt
echo PORTALMOD_113_STABLE_FINAL_PREFLIGHT_PASS

python3 release-staging/1.9.1/build_client_191.py | tee client-build.txt
python3 release-staging/1.9.1/build_server_132.py | tee server-build.txt

python3 - <<'PY'
import hashlib,io,json,zipfile
accepted=["1.0.0","1.0.1","1.0.2","1.0.3","1.1.0","1.2.0","1.2.1","1.3.0","1.3.1","1.3.2","1.3.3","1.4.0","1.5.0","1.5.1","1.5.2","1.5.3","1.6.0","1.6.1","1.6.2","1.7.0","1.7.1","1.8.0","1.8.1","1.8.2"]
forward=['1.9.0','1.9.1-test.1','1.9.1-test.2','1.9.1-test.3']
olds=[f'mods/SGP-Shapeless-Nether-Portals-{v}.jar' for v in ['1.0.0','1.1.0','1.1.1','1.1.2']]
target='mods/SGP-Shapeless-Nether-Portals-1.1.3.jar'
with zipfile.ZipFile('SGP_ClientPatch_1.9.1.zip') as z:
 p=json.loads(z.read('patch.json')); assert z.testzip() is None
 assert p['patchId']=='sgp-client-1.9.1' and p['toVersion']=='1.9.1'
 for v in accepted+forward: assert v in p['fromVersions'],v
 for old in olds:
  assert any(a.get('type')=='delete' and a.get('target')==old and a.get('optional') is True for a in p['actions'])
 a=next(a for a in p['actions'] if a.get('target')==target); b=z.read(a['source'])
 assert hashlib.sha256(b).hexdigest()==a['sha256'] and len(b)==a['size']
 with zipfile.ZipFile(io.BytesIO(b)) as j:
  names=set(j.namelist())
  assert 'sgp/shapelessportals/PortalFrameRules.class' not in names
  assert 'sgp/shapelessportals/mixin/BaseFireBlockMixin.class' not in names
  assert 'data/c/tags/block/nether_pframe.json' not in names
with zipfile.ZipFile('SGP_ServerPatch_1.3.2.zip') as z:
 assert z.testzip() is None
 expected=sorted(['.sgp/pack.json','.sgp/history.json','config/curios-common.toml','config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip','mods/SGP-Apotheosis-Soulbound-Compat-1.0.0.jar',target])
 assert sorted(z.namelist())==expected
 assert json.loads(z.read('.sgp/pack.json'))['version']=='1.3.2'
 h=json.loads(z.read('.sgp/history.json')); assert [e['version'] for e in h['entries']]==['1.0.0','1.2.0','1.2.1','1.3.2']
print('RELEASE_191_SERVER_132_EXACT_PACKAGE_AUDIT_PASS')
PY

SHA="$(sha256sum "$ASSET" | awk '{print $1}')"; SIZE="$(stat -c %s "$ASSET")"
MOD_SHA="$(cat portal_mod_sha.txt)"; MOD_SIZE="$(cat portal_mod_size.txt)"
SERVER_SHA="$(cat server132_sha.txt)"; SERVER_SIZE="$(cat server132_size.txt)"
{
 echo '## SGP Client 1.9.1'; echo
 echo 'Owner runtime showed the requested crying/BetterNether frame expansion did not work reliably. The owner explicitly removed that scope and authorized stable release after this deletion-only scope reduction.'; echo
 echo '- SGP Shapeless Nether Portals 1.1.3.'
 echo '- Arbitrary enclosed vertical Nether portal shapes remain supported.'
 echo '- SGP adds no crying obsidian or BetterNether obsidian variants as portal-frame materials; intended SGP frame material is normal obsidian.'
 echo '- Only the exact vanilla portal-generated zombified-piglin spawn call is suppressed.'
 echo '- Vanilla Nether portal blocks and vanilla travel/linking remain in use.'
 echo '- Cumulative from every accepted stable client through 1.8.2; forward repair supports retired 1.9.0 and 1.9.1 TEST states through test.3.'; echo
 printf 'Portal mod SHA-256: %s (%s bytes)\n' "$MOD_SHA" "$MOD_SIZE"
 printf 'Client SHA-256: %s (%s bytes)\n' "$SHA" "$SIZE"
 printf 'Matching server 1.3.2 SHA-256: %s (%s bytes)\n' "$SERVER_SHA" "$SERVER_SIZE"
} > notes.md

gh release create "$TAG" "$ASSET" --repo "$REPO" --target "$GITHUB_SHA" --title 'SGP Client 1.9.1' --notes-file notes.md
REL="$(gh api "repos/$REPO/releases/tags/$TAG")"
test "$(printf '%s' "$REL" | jq -r '.draft')" = false
test "$(printf '%s' "$REL" | jq -r '.prerelease')" = false
RID="$(printf '%s' "$REL" | jq -r '.id')"
ASSETS="$(gh api "repos/$REPO/releases/$RID/assets")"
test "$(printf '%s' "$ASSETS" | jq 'length')" = 1
test "$(printf '%s' "$ASSETS" | jq -r '.[0].name')" = "$ASSET"
test "$(printf '%s' "$ASSETS" | jq -r '.[0].digest')" = "sha256:$SHA"
AID="$(printf '%s' "$ASSETS" | jq -r '.[0].id')"
gh api -H 'Accept: application/octet-stream' "repos/$REPO/releases/assets/$AID" > verify.zip
echo "$SHA  verify.zip" | sha256sum -c -
unzip -t verify.zip >/dev/null
python3 - <<'PY'
import hashlib,io,json,zipfile
with zipfile.ZipFile('verify.zip') as z:
 p=json.loads(z.read('patch.json')); assert z.testzip() is None
 assert p['patchId']=='sgp-client-1.9.1' and p['toVersion']=='1.9.1'
 a=next(a for a in p['actions'] if a.get('target')=='mods/SGP-Shapeless-Nether-Portals-1.1.3.jar')
 b=z.read(a['source']); assert hashlib.sha256(b).hexdigest()==a['sha256']
 with zipfile.ZipFile(io.BytesIO(b)) as j:
  names=set(j.namelist())
  assert 'data/c/tags/block/nether_pframe.json' not in names
  assert 'sgp/shapelessportals/PortalFrameRules.class' not in names
  assert 'sgp/shapelessportals/mixin/BaseFireBlockMixin.class' not in names
print('LIVE_STABLE_191_VERIFY_PASS')
PY

TID="$(printf '%s' "$TREL" | jq -r '.id')"
gh api -X DELETE "repos/$REPO/releases/$TID"
if gh api "repos/$REPO/git/ref/tags/$TEST_TAG" >/dev/null 2>&1; then gh api -X DELETE "repos/$REPO/git/refs/tags/$TEST_TAG"; fi
! gh api "repos/$REPO/releases/tags/$TEST_TAG" >/dev/null 2>&1
! gh api "repos/$REPO/git/ref/tags/$TEST_TAG" >/dev/null 2>&1
echo FAILED_TEST3_REMOVED_PASS

echo "PUBLISHED_RELEASE_ID=$RID"
echo "PUBLISHED_ASSET_ID=$AID"
echo "PUBLISHED_SHA=$SHA"; echo "PUBLISHED_SIZE=$SIZE"
echo "PORTAL_MOD_SHA=$MOD_SHA"; echo "PORTAL_MOD_SIZE=$MOD_SIZE"
echo "SERVER_SHA=$SERVER_SHA"; echo "SERVER_SIZE=$SERVER_SIZE"
echo "SERVER_PACK_SHA=$(cat server132_pack_sha.txt)"; echo "SERVER_PACK_SIZE=$(cat server132_pack_size.txt)"
echo "SERVER_HISTORY_SHA=$(cat server132_history_sha.txt)"; echo "SERVER_HISTORY_SIZE=$(cat server132_history_size.txt)"
