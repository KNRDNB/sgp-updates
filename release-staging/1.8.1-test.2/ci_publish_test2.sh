#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
TAG="v1.8.1-test.2"
ASSET="SGP_ClientPatch_1.8.1-test.2.zip"
OLD_TEST_TAG="v1.8.1-test.1"

if gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1; then
  echo "Release already exists" >&2
  exit 1
fi

SHA="$(sha256sum "$ASSET" | awk '{print $1}')"
MOD_SHA="$(cat hotfix_mod_sha.txt)"
SERVER_SHA="$(cat server121_sha.txt)"

{
  echo '## SGP Client 1.8.1-test.2'
  echo
  echo 'Create × Chipped performance hotfix TEST with restored JEI visibility.'
  echo
  echo '- Old datapack with **6,968 registered create:cutting recipes** remains explicitly removed.'
  echo '- Runtime bridge **SGP-Create-Chipped-Cutting-1.0.1.jar** registers **zero recipe JSONs**.'
  echo '- JEI receives **6,968 client-only synthetic Saw recipes** for the same **277 Chipped 4.0.2 families**.'
  echo '- Synthetic JEI entries use the existing Create create:sawing category and do not enter the server RecipeManager.'
  echo '- Mechanical Saw output-filter behavior and 50-tick processing remain unchanged.'
  echo '- Patch is cumulative from every accepted stable **1.0.0–1.8.0** and supports forward repair from **1.8.1-test.1**.'
  echo '- No MineColonies, simulation-distance, JVM/GC or unrelated config changes.'
  echo
  echo 'Runtime validation: check JEI R/U visibility and representative Saw conversions. Server spark comes after matching server handoff.'
  echo
  printf 'Mod SHA-256: %s\n' "$MOD_SHA"
  printf 'Client TEST SHA-256: %s\n' "$SHA"
  printf 'Withheld matching server 1.2.1 SHA-256: %s\n' "$SERVER_SHA"
  echo
  echo 'Minecraft 1.21.1 · NeoForge 21.1.249 · Create 6.0.10 · Chipped 4.0.2 · JEI 19.21.0.247'
} > notes.md

gh release create "$TAG" "$ASSET" --repo "$REPO" --target "$GITHUB_SHA"   --title 'SGP Client 1.8.1-test.2' --notes-file notes.md --prerelease

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
import io,json,zipfile
accepted=['1.0.0','1.0.1','1.0.2','1.0.3','1.1.0','1.2.0','1.2.1','1.3.0','1.3.1','1.3.2','1.3.3','1.4.0','1.5.0','1.5.1','1.5.2','1.5.3','1.6.0','1.6.1','1.6.2','1.7.0','1.7.1','1.8.0']
with zipfile.ZipFile('verify.zip') as z:
    p=json.loads(z.read('patch.json'))
    assert p['patchId']=='sgp-client-1.8.1-test.2'
    assert p['toVersion']=='1.8.1-test.2'
    for v in accepted: assert v in p['fromVersions'],v
    assert p['fromVersions'][-1]=='1.8.1-test.1'
    assert 'files/config/paxi/datapacks/SGP_Create_Chipped_Cutting_MC1.21.1.zip' not in z.namelist()
    assert 'files/mods/SGP-Create-Chipped-Cutting-1.0.0.jar' not in z.namelist()
    mod=z.read('files/mods/SGP-Create-Chipped-Cutting-1.0.1.jar')
    with zipfile.ZipFile(io.BytesIO(mod)) as mz:
        assert mz.testzip() is None
        assert not any('/recipe/' in n or '/recipes/' in n for n in mz.namelist())
        assert 'sgp/createchippedcutting/jei/SgpCreateChippedJeiPlugin.class' in mz.namelist()
print('LIVE_CLIENT_181_TEST2_VERIFY_PASS')
PY

if gh api "repos/$REPO/releases/tags/$OLD_TEST_TAG" >/dev/null 2>&1; then
  gh release delete "$OLD_TEST_TAG" --repo "$REPO" --cleanup-tag -y
fi
! gh api "repos/$REPO/releases/tags/$OLD_TEST_TAG" >/dev/null 2>&1
! gh api "repos/$REPO/git/ref/tags/$OLD_TEST_TAG" >/dev/null 2>&1

echo TEST1_RETIRED_PASS
echo "PUBLISHED_RELEASE_ID=$RID"
echo "PUBLISHED_ASSET_ID=$AID"
echo "PUBLISHED_SHA=$SHA"
