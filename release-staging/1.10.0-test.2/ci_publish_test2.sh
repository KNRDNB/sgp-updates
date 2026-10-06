#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
BASE_TAG="v1.10.0-test.1"
BASE_ASSET="SGP_ClientPatch_1.10.0-test.1.zip"
BASE_SHA="586473090d69f29b65bfdcb787a4b52f6a8349b086b9d10266e7dbcd90aa69c6"
TAG="v1.10.0-test.2"
ASSET="SGP_ClientPatch_1.10.0-test.2.zip"
CAT="unbreakablecatalyst-1.0.2.jar"
CAT_SHA1="3a381f81669ee967737fc1037825ee20ea153ab3"
CAT_CF_PROJECT="1427017"
CAT_CF_FILE="7453109"

T1="$(gh api "repos/$REPO/releases/tags/$BASE_TAG")"
test "$(printf '%s' "$T1" | jq -r '.draft')" = false
test "$(printf '%s' "$T1" | jq -r '.prerelease')" = true
if gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1; then
  echo "TEST2 release already exists" >&2
  exit 1
fi

gh release download "$BASE_TAG" --repo "$REPO" -p "$BASE_ASSET"
echo "$BASE_SHA  $BASE_ASSET" | sha256sum -c -
unzip -t "$BASE_ASSET" >/dev/null

# Exact CurseForge 1.21.1 NeoForge file. API URL first, deterministic CDN fallback.
curl -fL -A 'SGP-release-builder/1.0'   "https://www.curseforge.com/api/v1/mods/$CAT_CF_PROJECT/files/$CAT_CF_FILE/download"   -o "$CAT"   || curl -fL -A 'SGP-release-builder/1.0'   "https://edge.forgecdn.net/files/7453/109/$CAT"   -o "$CAT"
echo "$CAT_SHA1  $CAT" | sha1sum -c -
unzip -t "$CAT" >/dev/null

# Unbreakable Catalyst exact contract / implementation preflight.
unzip -p "$CAT" META-INF/neoforge.mods.toml > catalyst.mods.toml
grep -Eq 'modId *= *"unbreakablecatalyst"' catalyst.mods.toml
grep -Eq 'version *= *"1\.0\.2"' catalyst.mods.toml || true
jar tf "$CAT" | grep '\.class$' > catalyst-classes.txt
: > catalyst-javap.txt
while IFS= read -r cf; do
  cls="${cf%.class}"; cls="${cls//\//.}"
  javap -classpath "$CAT" -p -c "$cls" >> catalyst-javap.txt 2>/dev/null || true
done < catalyst-classes.txt
# The mod must gate its anvil operation on durability/damageability and write UNBREAKABLE.
grep -Eqi 'isDamageableItem|MAX_DAMAGE|getMaxDamage' catalyst-javap.txt
grep -Eqi 'UNBREAKABLE|Unbreakable' catalyst-javap.txt
grep -Eqi 'Anvil|onAnvil|AnvilUpdate' catalyst-javap.txt

# Permanent Sponges source contract is pinned by TEST1 exact JAR.
python3 release-staging/1.10.0-test.2/build_client_1100_test2.py | tee client-build.txt

python3 - <<'PY'
import hashlib,io,json,zipfile
asset='SGP_ClientPatch_1.10.0-test.2.zip'
sponges=[
 'permanentsponges:aqueous_sponge_on_a_stick',
 'permanentsponges:magmatic_sponge_on_a_stick'
]
with zipfile.ZipFile(asset) as z:
    assert z.testzip() is None
    p=json.loads(z.read('patch.json'))
    assert p['patchId']=='sgp-client-1.10.0-test.2'
    assert p['toVersion']=='1.10.0-test.2'
    assert p['fromVersions'][-2:]==['1.9.1','1.10.0-test.1']

    # TEST1 UI + Permanent Sponges payload remains.
    h=next(a for a in p['actions'] if a.get('actionId')=='shift-right-armorhud-8px')
    assert [e['value'] for e in h['edits']]==[-111,-111,-111,-111]
    assert any(a.get('target')=='mods/PermanentSponges-v21.1.0-1.21.1-NeoForge.jar' for a in p['actions'])
    assert any(a.get('target')=='mods/puzzleslib-v21.1.62-mc1.21.1+neoforge.jar' for a in p['actions'])

    cat=next(a for a in p['actions'] if a.get('target')=='mods/unbreakablecatalyst-1.0.2.jar')
    cb=z.read(cat['source'])
    assert len(cb)==cat['size']
    assert hashlib.sha256(cb).hexdigest()==cat['sha256']

    fix=next(a for a in p['actions'] if a.get('type')=='copy' and a.get('target')=='config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip')
    fb=z.read(fix['source'])
    assert hashlib.sha256(fb).hexdigest()==fix['sha256']
    with zipfile.ZipFile(io.BytesIO(fb)) as fz:
      assert fz.testzip() is None
      assert json.loads(fz.read('pack.mcmeta'))['pack']['description'].endswith('internal rev 1.15')
      tag=json.loads(fz.read('data/soulbound/tags/item/enchantable.json'))
      assert tag['replace'] is False
      assert tag['values'][-2:]==sponges
print('TEST1100_TEST2_EXACT_PACKAGE_AUDIT_PASS')
PY

SHA="$(cat client1100test2_sha.txt)"
SIZE="$(cat client1100test2_size.txt)"
CAT_SHA="$(cat catalyst_sha.txt)"
CAT_SIZE="$(cat catalyst_size.txt)"
FIX_SHA="$(cat fixes115_sha.txt)"
FIX_SIZE="$(cat fixes115_size.txt)"

{
  echo '## SGP Client 1.10.0-test.2'
  echo
  echo 'Runtime TEST: ArmorHUD + Permanent Sponges + sponge-stick persistence.'
  echo
  echo '- Keeps TEST1 ArmorHUD right-side X -111 and Permanent Sponges/Puzzles Lib exact payload.'
  echo '- Adds Unbreakable Catalyst 1.0.2, a NeoForge 1.21.1 analogue of Things Hardening Catalyst.'
  echo '- SGP Fixes rev 1.15 adds both Permanent Sponges stick items to soulbound:enchantable.'
  echo '- Runtime check BOTH sponge sticks: Unbreakable Catalyst via anvil, Soulbound via normal book/anvil path, then actual water/lava absorption.'
  echo '- No dedicated-server patch is built during client TEST.'
  echo
  printf 'Unbreakable Catalyst SHA-256: %s (%s bytes)\n' "$CAT_SHA" "$CAT_SIZE"
  printf 'SGP Fixes rev 1.15 SHA-256: %s (%s bytes)\n' "$FIX_SHA" "$FIX_SIZE"
  printf 'Client TEST SHA-256: %s (%s bytes)\n' "$SHA" "$SIZE"
} > notes.md

gh release create "$TAG" "$ASSET" --repo "$REPO" --target "$GITHUB_SHA"   --title 'SGP Client 1.10.0-test.2' --notes-file notes.md --prerelease

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
import hashlib,io,json,zipfile
with zipfile.ZipFile('verify.zip') as z:
  assert z.testzip() is None
  p=json.loads(z.read('patch.json'))
  assert p['patchId']=='sgp-client-1.10.0-test.2'
  cat=next(a for a in p['actions'] if a.get('target')=='mods/unbreakablecatalyst-1.0.2.jar')
  assert hashlib.sha256(z.read(cat['source'])).hexdigest()==cat['sha256']
  fix=next(a for a in p['actions'] if a.get('type')=='copy' and a.get('target')=='config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip')
  with zipfile.ZipFile(io.BytesIO(z.read(fix['source']))) as fz:
    tag=json.loads(fz.read('data/soulbound/tags/item/enchantable.json'))
    assert tag['values'][-2:]==[
      'permanentsponges:aqueous_sponge_on_a_stick',
      'permanentsponges:magmatic_sponge_on_a_stick'
    ]
print('LIVE_CLIENT_1100_TEST2_VERIFY_PASS')
PY

# Single-current-TEST rule: remove TEST1 only after TEST2 live verification.
T1ID="$(printf '%s' "$T1" | jq -r '.id')"
gh api -X DELETE "repos/$REPO/releases/$T1ID"
if gh api "repos/$REPO/git/ref/tags/$BASE_TAG" >/dev/null 2>&1; then
  gh api -X DELETE "repos/$REPO/git/refs/tags/$BASE_TAG"
fi
! gh api "repos/$REPO/releases/tags/$BASE_TAG" >/dev/null 2>&1
! gh api "repos/$REPO/git/ref/tags/$BASE_TAG" >/dev/null 2>&1
echo SUPERSEDED_TEST1_REMOVED_PASS

echo "PUBLISHED_RELEASE_ID=$RID"
echo "PUBLISHED_ASSET_ID=$AID"
echo "PUBLISHED_SHA=$SHA"
echo "PUBLISHED_SIZE=$SIZE"
echo "CATALYST_SHA=$CAT_SHA"
echo "CATALYST_SIZE=$CAT_SIZE"
echo "FIXES115_SHA=$FIX_SHA"
echo "FIXES115_SIZE=$FIX_SIZE"
