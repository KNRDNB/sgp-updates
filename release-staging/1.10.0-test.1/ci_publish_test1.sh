#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
BASE_TAG="v1.9.1"
BASE_ASSET="SGP_ClientPatch_1.9.1.zip"
BASE_SHA="74cc8f88725588548f6ffa1a8cc902ce8a967835a47aa08aa84adb4441093ad2"
TAG="v1.10.0-test.1"
ASSET="SGP_ClientPatch_1.10.0-test.1.zip"
PERM="PermanentSponges-v21.1.0-1.21.1-NeoForge.jar"
PUZ="puzzleslib-v21.1.62-mc1.21.1+neoforge.jar"

if gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1; then
  echo "TEST release already exists" >&2
  exit 1
fi

gh release download "$BASE_TAG" --repo "$REPO" -p "$BASE_ASSET"
echo "$BASE_SHA  $BASE_ASSET" | sha256sum -c -
unzip -t "$BASE_ASSET" >/dev/null

python3 release-staging/1.10.0-test.1/fetch_mods.py
unzip -t "$PERM" >/dev/null
unzip -t "$PUZ" >/dev/null

# Exact loader/content preflight: NeoForge 1.21.1, required Puzzles Lib, stick tools present.
unzip -p "$PERM" META-INF/neoforge.mods.toml > permanent.mods.toml
grep -Eq 'modId *= *"permanentsponges"' permanent.mods.toml
grep -Eq 'modId *= *"puzzleslib"' permanent.mods.toml
grep -Eq 'displayTest *= *"MATCH_VERSION"' permanent.mods.toml
unzip -l "$PERM" > permanent.files.txt
grep -Fq 'assets/permanentsponges/models/item/aqueous_sponge_on_a_stick.json' permanent.files.txt
grep -Fq 'assets/permanentsponges/models/item/magmatic_sponge_on_a_stick.json' permanent.files.txt
grep -Fq 'data/permanentsponges/recipe/aqueous_sponge_on_a_stick.json' permanent.files.txt
grep -Fq 'data/permanentsponges/recipe/magmatic_sponge_on_a_stick.json' permanent.files.txt

unzip -p "$PUZ" META-INF/neoforge.mods.toml > puzzles.mods.toml
grep -Eq 'modId *= *"puzzleslib"' puzzles.mods.toml

python3 release-staging/1.10.0-test.1/build_client_1100_test1.py | tee client-build.txt

python3 - <<'PY'
import hashlib,json,zipfile
asset='SGP_ClientPatch_1.10.0-test.1.zip'
with zipfile.ZipFile(asset) as z:
    assert z.testzip() is None
    p=json.loads(z.read('patch.json'))
    assert p['patchId']=='sgp-client-1.10.0-test.1'
    assert p['toVersion']=='1.10.0-test.1'
    assert p['fromVersions'][-1]=='1.9.1'
    h=next(a for a in p['actions'] if a.get('actionId')=='shift-right-armorhud-8px')
    assert h['target']=='config/inventoryhud-client.toml'
    assert h['edits']==[
      {'op':'set','path':'positions.legPosX','value':-111,'createIfMissing':False},
      {'op':'set','path':'positions.bootPosX','value':-111,'createIfMissing':False},
      {'op':'set','path':'positions.offPosX','value':-111,'createIfMissing':False},
      {'op':'set','path':'positions.invPosX','value':-111,'createIfMissing':False},
    ]
    for target in [
      'mods/PermanentSponges-v21.1.0-1.21.1-NeoForge.jar',
      'mods/puzzleslib-v21.1.62-mc1.21.1+neoforge.jar'
    ]:
      a=next(x for x in p['actions'] if x.get('type')=='copy' and x.get('target')==target)
      b=z.read(a['source'])
      assert len(b)==a['size']
      assert hashlib.sha256(b).hexdigest()==a['sha256']
print('TEST1100_TEST1_EXACT_PACKAGE_AUDIT_PASS')
PY

SHA="$(cat client1100test1_sha.txt)"
SIZE="$(cat client1100test1_size.txt)"
PERM_SHA="$(cat perm_sha.txt)"
PERM_SIZE="$(cat perm_size.txt)"
PUZ_SHA="$(cat puzzles_sha.txt)"
PUZ_SIZE="$(cat puzzles_size.txt)"

{
  echo '## SGP Client 1.10.0-test.1'
  echo
  echo 'Runtime TEST: ArmorHUD spacing + Permanent Sponges.'
  echo
  echo '- ArmorHUD right-side leggings/boots/offhand/inventory icon: X -103 -> -111 (8-unit nudge only).'
  echo '- Existing opposite-side 103 -> 136 adjustment remains unchanged.'
  echo '- Adds Permanent Sponges 21.1.0 for NeoForge 1.21.1, including aqueous and magmatic sponges on sticks.'
  echo '- Adds required Puzzles Lib 21.1.62 for NeoForge 1.21.1.'
  echo '- Permanent Sponges is required on BOTH client and server. Test sponge gameplay in singleplayer/integrated server.'
  echo '- Per SGP workflow, no dedicated-server patch is built during client TEST.'
  echo
  printf 'Permanent Sponges SHA-256: %s (%s bytes)\n' "$PERM_SHA" "$PERM_SIZE"
  printf 'Puzzles Lib SHA-256: %s (%s bytes)\n' "$PUZ_SHA" "$PUZ_SIZE"
  printf 'Client TEST SHA-256: %s (%s bytes)\n' "$SHA" "$SIZE"
} > notes.md

gh release create "$TAG" "$ASSET" --repo "$REPO" --target "$GITHUB_SHA"   --title 'SGP Client 1.10.0-test.1' --notes-file notes.md --prerelease

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
    assert p['patchId']=='sgp-client-1.10.0-test.1'
    assert p['toVersion']=='1.10.0-test.1'
    h=next(a for a in p['actions'] if a.get('actionId')=='shift-right-armorhud-8px')
    assert [e['value'] for e in h['edits']]==[-111,-111,-111,-111]
    for target in [
      'mods/PermanentSponges-v21.1.0-1.21.1-NeoForge.jar',
      'mods/puzzleslib-v21.1.62-mc1.21.1+neoforge.jar'
    ]:
      a=next(x for x in p['actions'] if x.get('target')==target)
      b=z.read(a['source'])
      assert hashlib.sha256(b).hexdigest()==a['sha256']
print('LIVE_CLIENT_1100_TEST1_VERIFY_PASS')
PY

echo "PUBLISHED_RELEASE_ID=$RID"
echo "PUBLISHED_ASSET_ID=$AID"
echo "PUBLISHED_SHA=$SHA"
echo "PUBLISHED_SIZE=$SIZE"
echo "PERM_SHA=$PERM_SHA"
echo "PERM_SIZE=$PERM_SIZE"
echo "PUZZLES_SHA=$PUZ_SHA"
echo "PUZZLES_SIZE=$PUZ_SIZE"
