#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
TEST_TAG="v1.10.0-test.4"
TEST_ASSET="SGP_ClientPatch_1.10.0-test.4.zip"
TEST_SHA="08cee43906d18ed02b588c826061d2ed535686606a87bcbbb3edd7349e4f8ef2"

TAG="v2.0.0"
ASSET="SGP_ClientPatch_2.0.0.zip"
OLD_TAG_SHA="6b23e3ea6069893e84ff36a594a20880f853d459"
OLD_RELEASE_ID="405031806"
OLD_ASSET_ID="616336034"
OLD_ASSET_SHA="aeab5276fcc92ba3f8c2375f87563c7a0ede0a2dee5b94e158b62bdab7ff2ef1"

# Owner manually deleted the defective public release. The old tag must still
# be the exact known tag; fail closed on any unexpected publication state.
! gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1
REF="$(gh api "repos/$REPO/git/ref/tags/$TAG")"
test "$(printf '%s' "$REF" | jq -r '.object.sha')" = "$OLD_TAG_SHA"

TREL="$(gh api "repos/$REPO/releases/tags/$TEST_TAG")"
test "$(printf '%s' "$TREL" | jq -r '.draft')" = false
test "$(printf '%s' "$TREL" | jq -r '.prerelease')" = true
TID="$(printf '%s' "$TREL" | jq -r '.id')"
TASSETS="$(gh api "repos/$REPO/releases/$TID/assets")"
test "$(printf '%s' "$TASSETS" | jq -r '.[0].name')" = "$TEST_ASSET"
test "$(printf '%s' "$TASSETS" | jq -r '.[0].digest')" = "sha256:$TEST_SHA"

gh release download "$TEST_TAG" --repo "$REPO" -p "$TEST_ASSET"
echo "$TEST_SHA  $TEST_ASSET" | sha256sum -c -
unzip -t "$TEST_ASSET" >/dev/null

python3 release-staging/2.0.0/build_client_200.py | tee client-build.txt

python3 - <<'PY'
import json,zipfile
asset='SGP_ClientPatch_2.0.0.zip'
accepted=[
 "1.0.0","1.0.1","1.0.2","1.0.3","1.1.0","1.2.0","1.2.1",
 "1.3.0","1.3.1","1.3.2","1.3.3","1.4.0","1.5.0","1.5.1","1.5.2","1.5.3",
 "1.6.0","1.6.1","1.6.2","1.7.0","1.7.1","1.8.0","1.8.1","1.8.2","1.9.1"
]
tests=["1.10.0-test.1","1.10.0-test.2","1.10.0-test.3","1.10.0-test.4"]
old='mods/PuzzlesLib-v21.1.60-mc1.21.1-NeoForge.jar'
new='mods/puzzleslib-v21.1.62-mc1.21.1+neoforge.jar'
with zipfile.ZipFile(asset) as z:
    assert z.testzip() is None
    p=json.loads(z.read('patch.json'))
    assert p['patchId']=='sgp-client-2.0.0'
    assert p['toVersion']=='2.0.0'
    for v in accepted+tests:
        assert v in p['fromVersions'],v
    assert '1.5.4' not in p['fromVersions']

    deletes=[(i,a) for i,a in enumerate(p['actions'])
             if a.get('type')=='delete' and a.get('target')==old]
    assert len(deletes)==1,deletes
    di,da=deletes[0]
    assert da.get('optional') is True
    copies=[(i,a) for i,a in enumerate(p['actions'])
            if a.get('type')=='copy' and a.get('target')==new]
    assert len(copies)==1,copies
    ni,na=copies[0]
    assert di < ni

    assert not any(a.get('target')=='mods/unbreakablecatalyst-1.0.2.jar' for a in p['actions'])
    assert any(a.get('target')=='mods/PermanentSponges-v21.1.0-1.21.1-NeoForge.jar' for a in p['actions'])
    hud=next(a for a in p['actions'] if a.get('actionId')=='shift-right-armorhud-8px')
    assert [e['value'] for e in hud['edits']]==[-111,-111,-111,-111]
print('CLIENT_200_CORRECTED_EXACT_PACKAGE_AUDIT_PASS')
PY

SHA="$(cat client200_sha.txt)"
SIZE="$(cat client200_size.txt)"

{
  echo '## SGP Client 2.0.0'
  echo
  echo 'Corrected cumulative legacy bridge, republished by explicit owner instruction after the defective first v2.0.0 release was removed.'
  echo
  echo '- Keeps the runtime-PASS 1.10.0-test.4 gameplay/config/resource payload.'
  echo '- Before installing Puzzles Lib 21.1.62, optionally deletes exact baseline JAR: PuzzlesLib-v21.1.60-mc1.21.1-NeoForge.jar.'
  echo '- Remains cumulative from every accepted stable client 1.0.0 through 1.9.1.'
  echo '- Keeps forward repair from 1.10.0-test.1 through 1.10.0-test.4.'
  echo '- Existing Unbreakable Catalyst remains untouched.'
  echo '- Server 2.0.0 is not rebuilt; owner already removed the old server Puzzles Lib manually.'
  echo
  printf 'Corrected client SHA-256: %s (%s bytes)\n' "$SHA" "$SIZE"
  printf 'Retired defective asset: release %s / asset %s / SHA-256 %s\n' "$OLD_RELEASE_ID" "$OLD_ASSET_ID" "$OLD_ASSET_SHA"
} > notes.md

# Candidate is fully built/audited before mutating the remaining old public tag.
gh api -X DELETE "repos/$REPO/git/refs/tags/$TAG"
! gh api "repos/$REPO/git/ref/tags/$TAG" >/dev/null 2>&1

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
old='mods/PuzzlesLib-v21.1.60-mc1.21.1-NeoForge.jar'
new='mods/puzzleslib-v21.1.62-mc1.21.1+neoforge.jar'
with zipfile.ZipFile('verify.zip') as z:
    assert z.testzip() is None
    p=json.loads(z.read('patch.json'))
    assert p['patchId']=='sgp-client-2.0.0' and p['toVersion']=='2.0.0'
    d=next((i,a) for i,a in enumerate(p['actions']) if a.get('type')=='delete' and a.get('target')==old)
    n=next((i,a) for i,a in enumerate(p['actions']) if a.get('type')=='copy' and a.get('target')==new)
    assert d[0] < n[0] and d[1].get('optional') is True
    required=["1.0.0","1.8.2","1.9.1","1.10.0-test.4"]
    for v in required: assert v in p['fromVersions']
print('LIVE_CORRECTED_STABLE_200_VERIFY_PASS')
PY

echo "REPLACED_DEFECTIVE_RELEASE_ID=$OLD_RELEASE_ID"
echo "REPLACED_DEFECTIVE_ASSET_ID=$OLD_ASSET_ID"
echo "PUBLISHED_RELEASE_ID=$RID"
echo "PUBLISHED_ASSET_ID=$AID"
echo "PUBLISHED_SHA=$SHA"
echo "PUBLISHED_SIZE=$SIZE"
