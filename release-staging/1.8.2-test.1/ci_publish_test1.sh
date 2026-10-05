#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
BASE_TAG="v1.8.1"
BASE_ASSET="SGP_ClientPatch_1.8.1.zip"
BASE_SHA="9f367afb0f4a50d389f671a35767099c5793c2b255e5f385b73b541cf87c2ce8"
TAG="v1.8.2-test.1"
ASSET="SGP_ClientPatch_1.8.2-test.1.zip"
OLD_TEST_TAG="v1.8.1-test.2"

if gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1; then
  echo "Release already exists" >&2
  exit 1
fi

gh release download "$BASE_TAG" --repo "$REPO" -p "$BASE_ASSET"
echo "$BASE_SHA  $BASE_ASSET" | sha256sum -c -
unzip -t "$BASE_ASSET" >/dev/null

python3 release-staging/1.8.2-test.1/build_test1.py | tee build.txt

SHA="$(sha256sum "$ASSET" | awk '{print $1}')"
FIXES_SHA="$(cat sgp_fixes_rev111_sha.txt)"
FIXES_SIZE="$(cat sgp_fixes_rev111_size.txt)"

{
  echo '## SGP Client 1.8.2-test.1'
  echo
  echo 'Maintenance TEST: Soulbound eligibility for all Apotheosis Potion Charms.'
  echo
  echo '- Updates **SGP_Fixes_NeoForge_1.21.1.zip** internal rev **1.10 → 1.11**.'
  echo '- Adds exact registry item **apotheosis:potion_charm** to **soulbound:enchantable**.'
  echo '- Every Potion Charm effect variant uses this same item, so Flight, Resistance II and all other variants are covered.'
  echo '- This makes Soulbound applicable to the charms; it does **not** automatically enchant already-existing charms.'
  echo '- All other SGP Fixes files are byte-identical to rev 1.10.'
  echo '- No Soulbound config, Apotheosis config, Create, MineColonies, distance, JVM/GC or unrelated changes.'
  echo '- Cumulative direct update from every accepted stable client through **1.8.1**.'
  echo
  printf 'SGP Fixes rev 1.11 SHA-256: %s (%s bytes)\n' "$FIXES_SHA" "$FIXES_SIZE"
  printf 'Client TEST SHA-256: %s\n' "$SHA"
} > notes.md

gh release create "$TAG" "$ASSET" --repo "$REPO" --target "$GITHUB_SHA"   --title 'SGP Client 1.8.2-test.1' --notes-file notes.md --prerelease

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
import hashlib,io,json,zipfile
accepted=[
    '1.0.0','1.0.1','1.0.2','1.0.3',
    '1.1.0','1.2.0','1.2.1',
    '1.3.0','1.3.1','1.3.2','1.3.3',
    '1.4.0','1.5.0','1.5.1','1.5.2','1.5.3',
    '1.6.0','1.6.1','1.6.2','1.7.0','1.7.1','1.8.0','1.8.1'
]
old_values=[
    '#artifacts:artifacts','#icarus:wings','supplementaries:quiver',
    'sophisticatedbackpacks:backpack','sophisticatedbackpacks:copper_backpack',
    'sophisticatedbackpacks:iron_backpack','sophisticatedbackpacks:gold_backpack',
    'sophisticatedbackpacks:diamond_backpack','sophisticatedbackpacks:netherite_backpack'
]
with zipfile.ZipFile('verify.zip') as z:
    assert z.testzip() is None
    p=json.loads(z.read('patch.json'))
    assert p['patchId']=='sgp-client-1.8.2-test.1'
    assert p['toVersion']=='1.8.2-test.1'
    assert p['fromVersions'][-1]=='1.8.1'
    for v in accepted:
        assert v in p['fromVersions'],v
    assert '1.5.4' not in p['fromVersions']
    a=[x for x in p['actions'] if x.get('type')=='copy' and x.get('target')=='config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip']
    assert len(a)==1
    nested=z.read(a[0]['source'])
    assert hashlib.sha256(nested).hexdigest()==a[0]['sha256']
    assert len(nested)==a[0]['size']
    with zipfile.ZipFile(io.BytesIO(nested)) as dz:
        assert dz.testzip() is None
        meta=json.loads(dz.read('pack.mcmeta'))
        tag=json.loads(dz.read('data/soulbound/tags/item/enchantable.json'))
        assert meta['pack']['pack_format']==48
        assert meta['pack']['description'].endswith('internal rev 1.11')
        assert tag=={'replace':False,'values':old_values+['apotheosis:potion_charm']}
print('LIVE_CLIENT_182_TEST1_VERIFY_PASS')
PY

if gh api "repos/$REPO/releases/tags/$OLD_TEST_TAG" >/dev/null 2>&1; then
  gh release delete "$OLD_TEST_TAG" --repo "$REPO" --cleanup-tag -y
fi
! gh api "repos/$REPO/releases/tags/$OLD_TEST_TAG" >/dev/null 2>&1
! gh api "repos/$REPO/git/ref/tags/$OLD_TEST_TAG" >/dev/null 2>&1

echo PREVIOUS_TEST_RETIRED_PASS
echo "PUBLISHED_RELEASE_ID=$RID"
echo "PUBLISHED_ASSET_ID=$AID"
echo "PUBLISHED_SHA=$SHA"
echo "FIXES_SHA=$FIXES_SHA"
echo "FIXES_SIZE=$FIXES_SIZE"
