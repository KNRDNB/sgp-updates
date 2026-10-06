#!/usr/bin/env bash
set -euo pipefail
REPO="KNRDNB/sgp-updates"

TEST_TAG="v1.10.0-test.4"
TEST_ASSET="SGP_ClientPatch_1.10.0-test.4.zip"
TEST_SHA="08cee43906d18ed02b588c826061d2ed535686606a87bcbbb3edd7349e4f8ef2"
TAG="v2.0.0"
ASSET="SGP_ClientPatch_2.0.0.zip"

SERVER_BASE_ARTIFACT_ID="11380771092"
SERVER_BASE_SHA="7c9eb7d2f9ededa396f71d932f1a47c5c6c1492a960a6d0c8b811d66b20a7f31"
SERVER_ASSET="SGP_ServerPatch_2.0.0.zip"

# Owner explicitly skipped stable 1.10.0 and chose stable 2.0.0.
! gh api "repos/$REPO/releases/tags/v1.10.0" >/dev/null 2>&1
! gh api "repos/$REPO/git/ref/tags/v1.10.0" >/dev/null 2>&1
! gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1

TREL="$(gh api "repos/$REPO/releases/tags/$TEST_TAG")"
test "$(printf '%s' "$TREL" | jq -r '.draft')" = false
test "$(printf '%s' "$TREL" | jq -r '.prerelease')" = true
TASSETS="$(gh api "repos/$REPO/releases/$(printf '%s' "$TREL" | jq -r '.id')/assets")"
test "$(printf '%s' "$TASSETS" | jq -r '.[0].digest')" = "sha256:$TEST_SHA"

gh release download "$TEST_TAG" --repo "$REPO" -p "$TEST_ASSET"
echo "$TEST_SHA  $TEST_ASSET" | sha256sum -c -
unzip -t "$TEST_ASSET" >/dev/null

# Retrieve exact previously-audited server 1.3.2 overlay only as a parity-file source.
gh api "repos/$REPO/actions/artifacts/$SERVER_BASE_ARTIFACT_ID/zip" > server132-artifact.zip
unzip -t server132-artifact.zip >/dev/null
unzip -o server132-artifact.zip -d server132-artifact >/dev/null
cp server132-artifact/SGP_ServerPatch_1.3.2.zip .
echo "$SERVER_BASE_SHA  SGP_ServerPatch_1.3.2.zip" | sha256sum -c -
unzip -t SGP_ServerPatch_1.3.2.zip >/dev/null

python3 release-staging/2.0.0/build_client_200.py | tee client-build.txt
python3 release-staging/2.0.0/build_server_200.py | tee server-build.txt

python3 - <<'PY'
import hashlib,io,json,zipfile
accepted=[
 "1.0.0","1.0.1","1.0.2","1.0.3","1.1.0","1.2.0","1.2.1",
 "1.3.0","1.3.1","1.3.2","1.3.3","1.4.0","1.5.0","1.5.1","1.5.2","1.5.3",
 "1.6.0","1.6.1","1.6.2","1.7.0","1.7.1","1.8.0","1.8.1","1.8.2","1.9.1"
]
tests=["1.10.0-test.1","1.10.0-test.2","1.10.0-test.3","1.10.0-test.4"]
with zipfile.ZipFile('SGP_ClientPatch_2.0.0.zip') as z:
    assert z.testzip() is None
    p=json.loads(z.read('patch.json'))
    assert p['patchId']=='sgp-client-2.0.0' and p['toVersion']=='2.0.0'
    for v in accepted+tests: assert v in p['fromVersions'],v
    assert not any(a.get('target')=='mods/unbreakablecatalyst-1.0.2.jar' for a in p['actions'])
    assert [e['value'] for e in next(a for a in p['actions'] if a.get('actionId')=='shift-right-armorhud-8px')['edits']]==[-111,-111,-111,-111]

with zipfile.ZipFile('SGP_ServerPatch_2.0.0.zip') as z:
    assert z.testzip() is None
    expected=sorted([
      '.sgp/history.json','.sgp/pack.json','config/curios-common.toml',
      'config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip',
      'mods/SGP-Apotheosis-Soulbound-Compat-1.0.0.jar',
      'mods/SGP-Shapeless-Nether-Portals-1.1.3.jar',
      'mods/PermanentSponges-v21.1.0-1.21.1-NeoForge.jar',
      'mods/puzzleslib-v21.1.62-mc1.21.1+neoforge.jar'
    ])
    assert sorted(z.namelist())==expected
    assert json.loads(z.read('.sgp/pack.json'))['version']=='2.0.0'
    h=json.loads(z.read('.sgp/history.json'))
    assert [e['version'] for e in h['entries']]==['1.0.0','1.2.0','1.2.1','2.0.0']
    assert 'mods/unbreakablecatalyst-1.0.2.jar' not in z.namelist()
    with zipfile.ZipFile(io.BytesIO(z.read('config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip'))) as fz:
      assert json.loads(fz.read('pack.mcmeta'))['pack']['description'].endswith('internal rev 1.15')
print('RELEASE_200_SERVER_200_EXACT_PACKAGE_AUDIT_PASS')
PY

SHA="$(cat client200_sha.txt)"
SIZE="$(cat client200_size.txt)"
SERVER_SHA="$(cat server200_sha.txt)"
SERVER_SIZE="$(cat server200_size.txt)"
{
 echo '## SGP Client 2.0.0'; echo
 echo 'Owner-runtime-PASS 1.10.0-test.4 promoted with identical payload/actions. Owner explicitly chose final stable identity 2.0.0; stable 1.10.0 is intentionally skipped.'; echo
 echo '- ArmorHUD right-side spacing fix.'
 echo '- Permanent Sponges 21.1.0 + Puzzles Lib 21.1.62.'
 echo '- SGP Fixes rev 1.15: Soulbound compatibility for both sponge sticks.'
 echo '- Existing Unbreakable Catalyst remains untouched.'
 echo '- SGP RU Localization 1.10: Permanent Sponges Russian localization.'
 echo '- Cumulative from every accepted stable client through 1.9.1; forward repair supports the 1.10.0 TEST line.'; echo
 printf 'Client SHA-256: %s (%s bytes)\n' "$SHA" "$SIZE"
 printf 'Matching manual server 2.0.0 SHA-256: %s (%s bytes)\n' "$SERVER_SHA" "$SERVER_SIZE"
} > notes.md

gh release create "$TAG" "$ASSET" --repo "$REPO" --target "$GITHUB_SHA"   --title 'SGP Client 2.0.0' --notes-file notes.md

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
import json,zipfile
with zipfile.ZipFile('verify.zip') as z:
    assert z.testzip() is None
    p=json.loads(z.read('patch.json'))
    assert p['patchId']=='sgp-client-2.0.0' and p['toVersion']=='2.0.0'
    assert p['fromVersions'][-1]=='1.10.0-test.4'
    assert not any(a.get('target')=='mods/unbreakablecatalyst-1.0.2.jar' for a in p['actions'])
print('LIVE_STABLE_200_VERIFY_PASS')
PY

# Keep the successful test.4 prerelease as the temporary reference fixture until the next TEST.
echo SUCCESSFUL_TEST4_RETAINED_REFERENCE_PASS

echo "PUBLISHED_RELEASE_ID=$RID"
echo "PUBLISHED_ASSET_ID=$AID"
echo "PUBLISHED_SHA=$SHA"
echo "PUBLISHED_SIZE=$SIZE"
echo "SERVER_SHA=$SERVER_SHA"
echo "SERVER_SIZE=$SERVER_SIZE"
echo "SERVER_PACK_SHA=$(cat server200_pack_sha.txt)"
echo "SERVER_PACK_SIZE=$(cat server200_pack_size.txt)"
echo "SERVER_HISTORY_SHA=$(cat server200_history_sha.txt)"
echo "SERVER_HISTORY_SIZE=$(cat server200_history_size.txt)"
