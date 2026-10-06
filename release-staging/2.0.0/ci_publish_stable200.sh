#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
TEST_TAG="v1.10.0-test.4"
TEST_ASSET="SGP_ClientPatch_1.10.0-test.4.zip"
TEST_SHA="08cee43906d18ed02b588c826061d2ed535686606a87bcbbb3edd7349e4f8ef2"

TAG="v2.0.0"
ASSET="SGP_ClientPatch_2.0.0.zip"
STALE_TAG_SHA="6b23e3ea6069893e84ff36a594a20880f853d459"
OLD_PUZ="mods/PuzzlesLib-v21.1.60-mc1.21.1-NeoForge.jar"
NEW_PUZ="mods/puzzleslib-v21.1.62-mc1.21.1+neoforge.jar"

# Owner manually deleted the defective public release. Refuse to overwrite any unexpected replacement.
! gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1
TAG_JSON="$(gh api "repos/$REPO/git/ref/tags/$TAG")"
test "$(printf '%s' "$TAG_JSON" | jq -r '.object.sha')" = "$STALE_TAG_SHA"
gh api -X DELETE "repos/$REPO/git/refs/tags/$TAG"
! gh api "repos/$REPO/git/ref/tags/$TAG" >/dev/null 2>&1
echo STALE_200_TAG_REMOVED_PASS

# Stable 1.10.0 is intentionally skipped.
! gh api "repos/$REPO/releases/tags/v1.10.0" >/dev/null 2>&1
! gh api "repos/$REPO/git/ref/tags/v1.10.0" >/dev/null 2>&1

# Freeze exact runtime-PASS TEST fixture.
TREL="$(gh api "repos/$REPO/releases/tags/$TEST_TAG")"
test "$(printf '%s' "$TREL" | jq -r '.draft')" = false
test "$(printf '%s' "$TREL" | jq -r '.prerelease')" = true
TASSETS="$(gh api "repos/$REPO/releases/$(printf '%s' "$TREL" | jq -r '.id')/assets")"
test "$(printf '%s' "$TASSETS" | jq 'length')" = 1
test "$(printf '%s' "$TASSETS" | jq -r '.[0].name')" = "$TEST_ASSET"
test "$(printf '%s' "$TASSETS" | jq -r '.[0].digest')" = "sha256:$TEST_SHA"
gh release download "$TEST_TAG" --repo "$REPO" -p "$TEST_ASSET"
echo "$TEST_SHA  $TEST_ASSET" | sha256sum -c -
unzip -t "$TEST_ASSET" >/dev/null

python3 release-staging/2.0.0/build_client_200.py | tee client-build.txt

python3 - <<'PY'
import hashlib,json,zipfile

accepted=[
 "1.0.0","1.0.1","1.0.2","1.0.3","1.1.0","1.2.0","1.2.1",
 "1.3.0","1.3.1","1.3.2","1.3.3","1.4.0","1.5.0","1.5.1","1.5.2","1.5.3",
 "1.6.0","1.6.1","1.6.2","1.7.0","1.7.1","1.8.0","1.8.1","1.8.2","1.9.1"
]
tests=["1.10.0-test.1","1.10.0-test.2","1.10.0-test.3","1.10.0-test.4"]
expected=accepted+tests
old='mods/PuzzlesLib-v21.1.60-mc1.21.1-NeoForge.jar'
new='mods/puzzleslib-v21.1.62-mc1.21.1+neoforge.jar'

with zipfile.ZipFile('SGP_ClientPatch_2.0.0.zip') as z:
    assert z.testzip() is None
    p=json.loads(z.read('patch.json'))
    assert p['patchId']=='sgp-client-2.0.0'
    assert p['toVersion']=='2.0.0'
    assert p['fromVersions']==expected, (p['fromVersions'], expected)
    assert '1.5.4' not in p['fromVersions']

    ds=[a for a in p['actions'] if a.get('actionId')=='remove-old-puzzleslib-21-1-60']
    assert len(ds)==1
    d=ds[0]
    assert d['type']=='delete'
    assert d['target']==old
    assert d['optional'] is True

    di=p['actions'].index(d)
    ni=next(i for i,a in enumerate(p['actions']) if a.get('type')=='copy' and a.get('target')==new)
    assert di < ni
    na=p['actions'][ni]
    b=z.read(na['source'])
    assert hashlib.sha256(b).hexdigest()==na['sha256']
    assert len(b)==na['size']

    assert not any(a.get('target')=='mods/unbreakablecatalyst-1.0.2.jar' for a in p['actions'])
    assert any(a.get('target')=='mods/PermanentSponges-v21.1.0-1.21.1-NeoForge.jar' for a in p['actions'])
    assert [e['value'] for e in next(a for a in p['actions'] if a.get('actionId')=='shift-right-armorhud-8px')['edits']]==[-111,-111,-111,-111]

print('CLIENT_200_CORRECTED_CUMULATIVE_PACKAGE_AUDIT_PASS')
PY

SHA="$(cat client200_sha.txt)"
SIZE="$(cat client200_size.txt)"

{
  echo '## SGP Client 2.0.0 — corrected cumulative stable'
  echo
  echo 'Owner-authorized replacement of the defective earlier 2.0.0 publication.'
  echo
  echo '- Fully cumulative: direct update from every accepted stable client 1.0.0 through 1.9.1.'
  echo '- Forward repair supported from 1.10.0-test.1 through 1.10.0-test.4.'
  echo '- Deletes exact old client JAR PuzzlesLib-v21.1.60-mc1.21.1-NeoForge.jar if present.'
  echo '- Installs Puzzles Lib 21.1.62 under its correct filename.'
  echo '- Permanent Sponges 21.1.0, ArmorHUD change, SGP Fixes rev 1.15 and RU Localization 1.10 are unchanged.'
  echo '- Existing Unbreakable Catalyst remains untouched.'
  echo
  printf 'Client SHA-256: %s (%s bytes)\n' "$SHA" "$SIZE"
} > notes.md

gh release create "$TAG" "$ASSET" --repo "$REPO" --target "$GITHUB_SHA" \
  --title 'SGP Client 2.0.0' --notes-file notes.md

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
accepted=[
 "1.0.0","1.0.1","1.0.2","1.0.3","1.1.0","1.2.0","1.2.1",
 "1.3.0","1.3.1","1.3.2","1.3.3","1.4.0","1.5.0","1.5.1","1.5.2","1.5.3",
 "1.6.0","1.6.1","1.6.2","1.7.0","1.7.1","1.8.0","1.8.1","1.8.2","1.9.1"
]
tests=["1.10.0-test.1","1.10.0-test.2","1.10.0-test.3","1.10.0-test.4"]
with zipfile.ZipFile('verify.zip') as z:
    assert z.testzip() is None
    p=json.loads(z.read('patch.json'))
    assert p['patchId']=='sgp-client-2.0.0' and p['toVersion']=='2.0.0'
    assert p['fromVersions']==accepted+tests
    d=next(a for a in p['actions'] if a.get('actionId')=='remove-old-puzzleslib-21-1-60')
    assert d['type']=='delete' and d['optional'] is True
    assert d['target']=='mods/PuzzlesLib-v21.1.60-mc1.21.1-NeoForge.jar'
    assert not any(a.get('target')=='mods/unbreakablecatalyst-1.0.2.jar' for a in p['actions'])
print('LIVE_CORRECTED_STABLE_200_VERIFY_PASS')
PY

echo "PUBLISHED_RELEASE_ID=$RID"
echo "PUBLISHED_ASSET_ID=$AID"
echo "PUBLISHED_SHA=$SHA"
echo "PUBLISHED_SIZE=$SIZE"
