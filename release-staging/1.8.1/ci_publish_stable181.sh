#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
TEST_TAG="v1.8.1-test.2"
TEST_ASSET="SGP_ClientPatch_1.8.1-test.2.zip"
TEST_SHA="810111faa329becbdd87b666af6fc9e955167095f25b3d3d69d0ba37d3a78af3"
TAG="v1.8.1"
ASSET="SGP_ClientPatch_1.8.1.zip"

if gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1; then
  echo "Stable already exists" >&2
  exit 1
fi

gh release download "$TEST_TAG" --repo "$REPO" -p "$TEST_ASSET"
echo "$TEST_SHA  $TEST_ASSET" | sha256sum -c -
unzip -t "$TEST_ASSET" >/dev/null

python3 release-staging/1.8.1/build_stable181.py | tee stable-build.txt
SHA="$(sha256sum "$ASSET" | awk '{print $1}')"

{
  echo '## SGP Client 1.8.1'
  echo
  echo 'Stable promotion from owner-runtime-PASS **1.8.1-test.2**.'
  echo
  echo '- Exact tested payload/action set preserved.'
  echo '- Removes the old 6,968-recipe Create × Chipped datapack.'
  echo '- Installs SGP-Create-Chipped-Cutting-1.0.1.jar.'
  echo '- Runtime path registers zero recipe JSONs; JEI keeps all 6,968 client-only synthetic Saw routes.'
  echo '- Cumulative from every accepted stable 1.0.0–1.8.0; forward repair includes 1.8.1-test.1 and tested 1.8.1-test.2.'
  echo '- No MineColonies, distance, JVM/GC or unrelated config changes.'
  echo
  printf 'SHA-256: %s\n' "$SHA"
} > notes.md

gh release create "$TAG" "$ASSET" --repo "$REPO" --target "$GITHUB_SHA"   --title 'SGP Client 1.8.1' --notes-file notes.md

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
    p=json.loads(z.read('patch.json'))
    assert p['patchId']=='sgp-client-1.8.1'
    assert p['toVersion']=='1.8.1'
    assert p['fromVersions'][-1]=='1.8.1-test.2'
    assert '1.8.0' in p['fromVersions']
    assert '1.5.4' not in p['fromVersions']
    assert 'files/config/paxi/datapacks/SGP_Create_Chipped_Cutting_MC1.21.1.zip' not in z.namelist()
    assert 'files/mods/SGP-Create-Chipped-Cutting-1.0.0.jar' not in z.namelist()
    mod=z.read('files/mods/SGP-Create-Chipped-Cutting-1.0.1.jar')
    assert hashlib.sha256(mod).hexdigest()=='433d99ad5172119a0f12613162dec28c9d50097dde397564d3a2c4b714c6dc31'
    with zipfile.ZipFile(io.BytesIO(mod)) as mz:
        assert mz.testzip() is None
        assert not any('/recipe/' in n or '/recipes/' in n for n in mz.namelist())
        assert 'sgp/createchippedcutting/jei/SgpCreateChippedJeiPlugin.class' in mz.namelist()
print('LIVE_STABLE_181_VERIFY_PASS')
PY

gh api "repos/$REPO/releases/tags/$TEST_TAG" >/dev/null
echo CURRENT_SUCCESSFUL_TEST_RETAINED
echo "PUBLISHED_RELEASE_ID=$RID"
echo "PUBLISHED_ASSET_ID=$AID"
echo "PUBLISHED_SHA=$SHA"
