#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
BASE_TAG="v1.8.2"
BASE_ASSET="SGP_ClientPatch_1.8.2.zip"
BASE_SHA="d98e8a24eb297e6caea115e5e758d34c9237c0b7c294c0a804ac08282a2f83cd"

TAG="v1.9.1-test.3"
ASSET="SGP_ClientPatch_1.9.1-test.3.zip"
PORTAL_JAR="SGP-Shapeless-Nether-Portals-1.1.2.jar"
P="release-staging/1.9.1-test.3/portalmod"

# Failed/retired identities must remain absent before a new TEST is published.
for OLD in v1.9.0 v1.9.1-test.1 v1.9.1-test.2; do
  ! gh api "repos/$REPO/releases/tags/$OLD" >/dev/null 2>&1
  ! gh api "repos/$REPO/git/ref/tags/$OLD" >/dev/null 2>&1
done

if gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1; then
  echo "TEST3 release already exists" >&2
  exit 1
fi

gh release download "$BASE_TAG" --repo "$REPO" -p "$BASE_ASSET"
echo "$BASE_SHA  $BASE_ASSET" | sha256sum -c -
unzip -t "$BASE_ASSET" >/dev/null

# Rebuild exact TEST3 mod source.
gradle -p "$P" build --no-daemon --stacktrace
cp "$P/build/libs/$PORTAL_JAR" "$PORTAL_JAR"
unzip -t "$PORTAL_JAR" >/dev/null

# Exact Minecraft/NeoForge target preflight.
CP="$(gradle -q -p "$P" printRuntimeClasspath --no-daemon | tail -n 1)"

javap -classpath "$CP" -p -c -s net.minecraft.world.level.block.BaseFireBlock > basefire.txt
grep -A2 -F 'private static boolean isPortal(net.minecraft.world.level.Level, net.minecraft.core.BlockPos, net.minecraft.core.Direction);' basefire.txt | grep -Fq 'descriptor: (Lnet/minecraft/world/level/Level;Lnet/minecraft/core/BlockPos;Lnet/minecraft/core/Direction;)Z'
grep -Fq 'BlockState.isPortalFrame' basefire.txt
grep -Fq 'PortalShape.findEmptyPortalShape' basefire.txt

javap -classpath "$CP" -p -c -s net.minecraft.world.level.block.NetherPortalBlock > netherportal.txt
grep -A2 -F 'protected void randomTick(net.minecraft.world.level.block.state.BlockState, net.minecraft.server.level.ServerLevel, net.minecraft.core.BlockPos, net.minecraft.util.RandomSource);' netherportal.txt | grep -Fq 'descriptor: (Lnet/minecraft/world/level/block/state/BlockState;Lnet/minecraft/server/level/ServerLevel;Lnet/minecraft/core/BlockPos;Lnet/minecraft/util/RandomSource;)V'
grep -Fq 'EntityType.ZOMBIFIED_PIGLIN' netherportal.txt
grep -Fq 'EntityType.spawn' netherportal.txt

javap -classpath "$CP" -p -s net.minecraft.world.level.portal.PortalShape > portalshape.txt
grep -Fq 'public net.minecraft.world.level.portal.PortalShape(net.minecraft.world.level.LevelAccessor, net.minecraft.core.BlockPos, net.minecraft.core.Direction$Axis);' portalshape.txt
grep -A2 -F 'public boolean isValid();' portalshape.txt | grep -Fq 'descriptor: ()Z'
grep -A2 -F 'public boolean isComplete();' portalshape.txt | grep -Fq 'descriptor: ()Z'
grep -A2 -F 'public void createPortalBlocks();' portalshape.txt | grep -Fq 'descriptor: ()V'

# Exact final JAR contract.
unzip -l "$PORTAL_JAR" > portal-jar-files.txt
for ENTRY in \
  'sgp/shapelessportals/PortalFrameRules.class' \
  'sgp/shapelessportals/mixin/BaseFireBlockMixin.class' \
  'sgp/shapelessportals/mixin/PortalShapeMixin.class' \
  'sgp/shapelessportals/mixin/PortalShapeAccessor.class' \
  'sgp/shapelessportals/mixin/NetherPortalBlockMixin.class' \
  'data/c/tags/block/nether_pframe.json' \
  'META-INF/NOTICE-NICER-PORTALS.txt'; do
  grep -Fq "$ENTRY" portal-jar-files.txt
done

unzip -p "$PORTAL_JAR" META-INF/neoforge.mods.toml > portal-mod.toml
grep -Fq 'version="1.1.2"' portal-mod.toml
grep -Fq 'modId="sgp_shapeless_nether_portals"' portal-mod.toml
grep -Fq 'versionRange="[21.1.249,21.2)"' portal-mod.toml
grep -Fq 'versionRange="[1.21.1]"' portal-mod.toml

unzip -p "$PORTAL_JAR" data/c/tags/block/nether_pframe.json > frame-tag.json
python3 - <<'PY'
import json
p=json.load(open('frame-tag.json',encoding='utf-8'))
assert p == {
  'replace': False,
  'values': [
    'minecraft:crying_obsidian',
    {'id':'betternether:weeping_obsidian','required':False},
    {'id':'betternether:blue_crying_obsidian','required':False},
    {'id':'betternether:blue_weeping_obsidian','required':False},
  ]
}
print('PORTAL_FRAME_TAG_EXACT_PASS')
PY

javap -classpath "$PORTAL_JAR" -p -v sgp.shapelessportals.PortalFrameRules > rules.txt
grep -Fq 'nether_pframe' rules.txt
grep -Fq 'isPortalFrame' rules.txt

javap -classpath "$PORTAL_JAR" -p -v sgp.shapelessportals.mixin.BaseFireBlockMixin > firemixin.txt
grep -Fq 'PortalFrameRules.isPortalFrame' firemixin.txt
javap -classpath "$PORTAL_JAR" -p -v sgp.shapelessportals.mixin.PortalShapeMixin > shapemixin.txt
grep -Fq 'PortalFrameRules.isPortalFrame' shapemixin.txt

javap -classpath "$PORTAL_JAR" -p -v sgp.shapelessportals.mixin.NetherPortalBlockMixin > piglinmixin.txt
grep -Fq 'ZOMBIFIED_PIGLIN' piglinmixin.txt
grep -Fq 'EntityType.spawn' piglinmixin.txt

echo PORTALMOD_112_TEST3_FINAL_PREFLIGHT_PASS

python3 release-staging/1.9.1-test.3/build_client_191_test3.py | tee client-build.txt

python3 - <<'PY'
import hashlib,json,zipfile,io
accepted=[
 "1.0.0","1.0.1","1.0.2","1.0.3",
 "1.1.0","1.2.0","1.2.1",
 "1.3.0","1.3.1","1.3.2","1.3.3",
 "1.4.0","1.5.0","1.5.1","1.5.2","1.5.3",
 "1.6.0","1.6.1","1.6.2",
 "1.7.0","1.7.1","1.8.0","1.8.1","1.8.2"
]
asset='SGP_ClientPatch_1.9.1-test.3.zip'
with zipfile.ZipFile(asset) as z:
    assert z.testzip() is None
    p=json.loads(z.read('patch.json'))
    assert p['patchId']=='sgp-client-1.9.1-test.3'
    assert p['toVersion']=='1.9.1-test.3'
    for v in accepted:
        assert v in p['fromVersions'],v
    assert p['fromVersions'][-3:]==['1.9.0','1.9.1-test.1','1.9.1-test.2']
    assert '1.5.4' not in p['fromVersions']

    olds=[
      'mods/SGP-Shapeless-Nether-Portals-1.0.0.jar',
      'mods/SGP-Shapeless-Nether-Portals-1.1.0.jar',
      'mods/SGP-Shapeless-Nether-Portals-1.1.1.jar',
    ]
    for old in olds:
        assert any(a.get('type')=='delete' and a.get('target')==old and a.get('optional') is True for a in p['actions'])
        assert 'files/'+old not in z.namelist()

    mod=next(a for a in p['actions'] if a.get('target')=='mods/SGP-Shapeless-Nether-Portals-1.1.2.jar')
    b=z.read(mod['source'])
    assert len(b)==mod['size']
    assert hashlib.sha256(b).hexdigest()==mod['sha256']
    with zipfile.ZipFile(io.BytesIO(b)) as j:
        assert j.testzip() is None
        tag=json.loads(j.read('data/c/tags/block/nether_pframe.json'))
        assert tag['values'][0]=='minecraft:crying_obsidian'
        assert [x['id'] for x in tag['values'][1:]]==[
          'betternether:weeping_obsidian',
          'betternether:blue_crying_obsidian',
          'betternether:blue_weeping_obsidian'
        ]
        assert all(x['required'] is False for x in tag['values'][1:])
print('TEST191_TEST3_EXACT_PACKAGE_AUDIT_PASS')
PY

SHA="$(sha256sum "$ASSET" | awk '{print $1}')"
MOD_SHA="$(cat portal_mod_sha.txt)"
MOD_SIZE="$(cat portal_mod_size.txt)"

{
  echo '## SGP Client 1.9.1-test.3'
  echo
  echo 'Runtime TEST for SGP Shapeless Nether Portals 1.1.2.'
  echo
  echo '- Arbitrary enclosed vertical Nether portal shapes.'
  echo '- One shared portal-frame rule for ignition and arbitrary-shape scanning.'
  echo '- Adds minecraft:crying_obsidian to c:nether_pframe.'
  echo '- Adds BetterNether weeping_obsidian, blue_crying_obsidian and blue_weeping_obsidian as optional c:nether_pframe entries.'
  echo '- Keeps the narrow portal-generated zombified-piglin suppression from 1.1.1.'
  echo '- Forward-repairs retired 1.9.0, test.1 and failed test.2 by deleting portal mod 1.0.0/1.1.0/1.1.1.'
  echo '- No server patch was built for this TEST.'
  echo
  printf 'Portal mod 1.1.2 SHA-256: %s (%s bytes)\n' "$MOD_SHA" "$MOD_SIZE"
  printf 'Client TEST SHA-256: %s\n' "$SHA"
} > notes.md

gh release create "$TAG" "$ASSET" --repo "$REPO" --target "$GITHUB_SHA" \
  --title 'SGP Client 1.9.1-test.3' --notes-file notes.md --prerelease

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
import hashlib,json,zipfile,io
with zipfile.ZipFile('verify.zip') as z:
    assert z.testzip() is None
    p=json.loads(z.read('patch.json'))
    assert p['patchId']=='sgp-client-1.9.1-test.3'
    assert p['toVersion']=='1.9.1-test.3'
    assert p['fromVersions'][-3:]==['1.9.0','1.9.1-test.1','1.9.1-test.2']
    mod=next(a for a in p['actions'] if a.get('target')=='mods/SGP-Shapeless-Nether-Portals-1.1.2.jar')
    b=z.read(mod['source'])
    assert hashlib.sha256(b).hexdigest()==mod['sha256']
    with zipfile.ZipFile(io.BytesIO(b)) as j:
        tag=json.loads(j.read('data/c/tags/block/nether_pframe.json'))
        assert tag['values'][0]=='minecraft:crying_obsidian'
        assert all(x.get('required') is False for x in tag['values'][1:])
print('LIVE_CLIENT_191_TEST3_VERIFY_PASS')
PY

echo "PUBLISHED_RELEASE_ID=$RID"
echo "PUBLISHED_ASSET_ID=$AID"
echo "PUBLISHED_SHA=$SHA"
echo "MOD_SHA=$MOD_SHA"
echo "MOD_SIZE=$MOD_SIZE"
