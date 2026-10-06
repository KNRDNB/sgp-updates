#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
BASE_TAG="v1.10.0-test.2"
BASE_ASSET="SGP_ClientPatch_1.10.0-test.2.zip"
BASE_SHA="3b589a66ac22af5c53950a2dda6e5778911ea437ce6e4b33272d2fb2b1047fe8"
TAG="v1.10.0-test.3"
ASSET="SGP_ClientPatch_1.10.0-test.3.zip"
CAT_TARGET="mods/unbreakablecatalyst-1.0.2.jar"

T2="$(gh api "repos/$REPO/releases/tags/$BASE_TAG")"
test "$(printf '%s' "$T2" | jq -r '.draft')" = false
test "$(printf '%s' "$T2" | jq -r '.prerelease')" = true
! gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1

gh release download "$BASE_TAG" --repo "$REPO" -p "$BASE_ASSET"
echo "$BASE_SHA  $BASE_ASSET" | sha256sum -c -
unzip -t "$BASE_ASSET" >/dev/null

python3 release-staging/1.10.0-test.3/build_client_1100_test3.py | tee client-build.txt

python3 - <<'PY'
import hashlib,io,json,zipfile
asset='SGP_ClientPatch_1.10.0-test.3.zip'
cat_target='mods/unbreakablecatalyst-1.0.2.jar'
with zipfile.ZipFile(asset) as z:
    assert z.testzip() is None
    p=json.loads(z.read('patch.json'))
    assert p['patchId']=='sgp-client-1.10.0-test.3'
    assert p['toVersion']=='1.10.0-test.3'
    assert p['fromVersions'][-3:]==['1.9.1','1.10.0-test.1','1.10.0-test.2']
    assert not any(a.get('target')==cat_target for a in p['actions'])
    assert not any(name.endswith('/unbreakablecatalyst-1.0.2.jar') for name in z.namelist())

    h=next(a for a in p['actions'] if a.get('actionId')=='shift-right-armorhud-8px')
    assert [e['value'] for e in h['edits']]==[-111,-111,-111,-111]
    assert any(a.get('target')=='mods/PermanentSponges-v21.1.0-1.21.1-NeoForge.jar' for a in p['actions'])
    assert any(a.get('target')=='mods/puzzleslib-v21.1.62-mc1.21.1+neoforge.jar' for a in p['actions'])

    fix=next(a for a in p['actions'] if a.get('type')=='copy' and a.get('target')=='config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip')
    fb=z.read(fix['source'])
    assert hashlib.sha256(fb).hexdigest()==fix['sha256']
    with zipfile.ZipFile(io.BytesIO(fb)) as fz:
      tag=json.loads(fz.read('data/soulbound/tags/item/enchantable.json'))
      assert tag['values'][-2:]==[
        'permanentsponges:aqueous_sponge_on_a_stick',
        'permanentsponges:magmatic_sponge_on_a_stick'
      ]
print('TEST1100_TEST3_EXACT_PACKAGE_AUDIT_PASS')
PY

SHA="$(cat client1100test3_sha.txt)"
SIZE="$(cat client1100test3_size.txt)"
{
  echo '## SGP Client 1.10.0-test.3'
  echo
  echo 'Correction of TEST2 packaging scope.'
  echo
  echo '- Unbreakable Catalyst 1.0.2 already belongs to the SGP baseline; this patch does not install, replace, or delete it.'
  echo '- Keeps ArmorHUD right-side X -111.'
  echo '- Keeps Permanent Sponges 21.1.0 + Puzzles Lib 21.1.62.'
  echo '- Keeps SGP Fixes rev 1.15 Soulbound eligibility for both sponge sticks.'
  echo '- Runtime check uses the existing SGP Unbreakable Catalyst on both sticks.'
  echo '- No dedicated-server patch during TEST.'
  echo
  printf 'Client TEST SHA-256: %s (%s bytes)\n' "$SHA" "$SIZE"
} > notes.md

gh release create "$TAG" "$ASSET" --repo "$REPO" --target "$GITHUB_SHA"   --title 'SGP Client 1.10.0-test.3' --notes-file notes.md --prerelease

REL="$(gh api "repos/$REPO/releases/tags/$TAG")"
test "$(printf '%s' "$REL" | jq -r '.draft')" = false
test "$(printf '%s' "$REL" | jq -r '.prerelease')" = true
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
import json,zipfile
with zipfile.ZipFile('verify.zip') as z:
  assert z.testzip() is None
  p=json.loads(z.read('patch.json'))
  assert p['patchId']=='sgp-client-1.10.0-test.3'
  assert not any(a.get('target')=='mods/unbreakablecatalyst-1.0.2.jar' for a in p['actions'])
  assert not any('unbreakablecatalyst-1.0.2.jar' in n for n in z.namelist())
print('LIVE_CLIENT_1100_TEST3_VERIFY_PASS')
PY

# Single-current-TEST: remove flawed TEST2 only after TEST3 is live-verified.
T2ID="$(printf '%s' "$T2" | jq -r '.id')"
gh api -X DELETE "repos/$REPO/releases/$T2ID"
if gh api "repos/$REPO/git/ref/tags/$BASE_TAG" >/dev/null 2>&1; then
  gh api -X DELETE "repos/$REPO/git/refs/tags/$BASE_TAG"
fi
! gh api "repos/$REPO/releases/tags/$BASE_TAG" >/dev/null 2>&1
! gh api "repos/$REPO/git/ref/tags/$BASE_TAG" >/dev/null 2>&1
echo SUPERSEDED_TEST2_REMOVED_PASS

echo "PUBLISHED_RELEASE_ID=$RID"
echo "PUBLISHED_ASSET_ID=$AID"
echo "PUBLISHED_SHA=$SHA"
echo "PUBLISHED_SIZE=$SIZE"
