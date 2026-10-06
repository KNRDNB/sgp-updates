#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
BASE_TAG="v1.10.0-test.3"
BASE_ASSET="SGP_ClientPatch_1.10.0-test.3.zip"
BASE_SHA="19bc0769966fd8903b75b1d87e648fba97f719c55cfef9d014c2893a27983328"
TAG="v1.10.0-test.4"
ASSET="SGP_ClientPatch_1.10.0-test.4.zip"

T3="$(gh api "repos/$REPO/releases/tags/$BASE_TAG")"
test "$(printf '%s' "$T3" | jq -r '.draft')" = false
test "$(printf '%s' "$T3" | jq -r '.prerelease')" = true
! gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1

gh release download "$BASE_TAG" --repo "$REPO" -p "$BASE_ASSET"
echo "$BASE_SHA  $BASE_ASSET" | sha256sum -c -
unzip -t "$BASE_ASSET" >/dev/null

python3 release-staging/1.10.0-test.4/build_client_1100_test4.py | tee client-build.txt

python3 - <<'PY'
import hashlib,io,json,zipfile
asset='SGP_ClientPatch_1.10.0-test.4.zip'
expected={
  'block.permanentsponges.aqueous_sponge':'Водная губка',
  'block.permanentsponges.magmatic_sponge':'Магматическая губка',
  'item.permanentsponges.aqueous_sponge_on_a_stick':'Водная губка на палочке',
  'item.permanentsponges.magmatic_sponge_on_a_stick':'Магматическая губка на палочке',
  'itemGroup.permanentsponges.main':'Вечные губки',
}
with zipfile.ZipFile(asset) as z:
    assert z.testzip() is None
    p=json.loads(z.read('patch.json'))
    assert p['patchId']=='sgp-client-1.10.0-test.4'
    assert p['toVersion']=='1.10.0-test.4'
    assert p['fromVersions'][-4:]==['1.9.1','1.10.0-test.1','1.10.0-test.2','1.10.0-test.3']
    assert [e['value'] for e in next(a for a in p['actions'] if a.get('actionId')=='shift-right-armorhud-8px')['edits']]==[-111,-111,-111,-111]
    assert any(a.get('target')=='mods/PermanentSponges-v21.1.0-1.21.1-NeoForge.jar' for a in p['actions'])
    assert any(a.get('target')=='mods/puzzleslib-v21.1.62-mc1.21.1+neoforge.jar' for a in p['actions'])
    assert not any(a.get('target')=='mods/unbreakablecatalyst-1.0.2.jar' for a in p['actions'])
    ru=next(a for a in p['actions'] if a.get('type')=='copy' and a.get('target')=='config/paxi/resourcepacks/SGP_RU_Localization_MC1.21.1.zip')
    b=z.read(ru['source'])
    assert hashlib.sha256(b).hexdigest()==ru['sha256'] and len(b)==ru['size']
    with zipfile.ZipFile(io.BytesIO(b)) as rz:
        assert rz.testzip() is None
        assert json.loads(rz.read('assets/permanentsponges/lang/ru_ru.json'))==expected
        assert json.loads(rz.read('pack.mcmeta'))['pack']['description'].startswith('SGP RU Localization 1.10')
print('TEST1100_TEST4_EXACT_LOCALIZATION_PACKAGE_AUDIT_PASS')
PY

SHA="$(cat client1100test4_sha.txt)"
SIZE="$(cat client1100test4_size.txt)"
RU_SHA="$(cat ru110_sha.txt)"
RU_SIZE="$(cat ru110_size.txt)"

{
  echo '## SGP Client 1.10.0-test.4'
  echo
  echo 'Localization-only follow-up after owner runtime PASS of TEST3.'
  echo
  echo '- SGP RU Localization 1.10 adds all five Permanent Sponges Russian language keys.'
  echo '- Водная губка / Магматическая губка.'
  echo '- Водная губка на палочке / Магматическая губка на палочке.'
  echo '- Creative tab: Вечные губки.'
  echo '- Gameplay/config payload from TEST3 is otherwise unchanged.'
  echo '- No dedicated-server patch during TEST.'
  echo
  printf 'SGP RU Localization 1.10 SHA-256: %s (%s bytes)\n' "$RU_SHA" "$RU_SIZE"
  printf 'Client TEST SHA-256: %s (%s bytes)\n' "$SHA" "$SIZE"
} > notes.md

gh release create "$TAG" "$ASSET" --repo "$REPO" --target "$GITHUB_SHA"   --title 'SGP Client 1.10.0-test.4' --notes-file notes.md --prerelease

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
import io,json,zipfile
with zipfile.ZipFile('verify.zip') as z:
  assert z.testzip() is None
  p=json.loads(z.read('patch.json'))
  assert p['patchId']=='sgp-client-1.10.0-test.4'
  ru=next(a for a in p['actions'] if a.get('target')=='config/paxi/resourcepacks/SGP_RU_Localization_MC1.21.1.zip')
  with zipfile.ZipFile(io.BytesIO(z.read(ru['source']))) as rz:
    lang=json.loads(rz.read('assets/permanentsponges/lang/ru_ru.json'))
    assert lang['item.permanentsponges.aqueous_sponge_on_a_stick']=='Водная губка на палочке'
    assert lang['item.permanentsponges.magmatic_sponge_on_a_stick']=='Магматическая губка на палочке'
print('LIVE_CLIENT_1100_TEST4_VERIFY_PASS')
PY

# test.3 had owner runtime PASS, but single-current-TEST keeps only the newly published current TEST.
T3ID="$(printf '%s' "$T3" | jq -r '.id')"
gh api -X DELETE "repos/$REPO/releases/$T3ID"
if gh api "repos/$REPO/git/ref/tags/$BASE_TAG" >/dev/null 2>&1; then
  gh api -X DELETE "repos/$REPO/git/refs/tags/$BASE_TAG"
fi
! gh api "repos/$REPO/releases/tags/$BASE_TAG" >/dev/null 2>&1
! gh api "repos/$REPO/git/ref/tags/$BASE_TAG" >/dev/null 2>&1
echo SUCCESSFUL_TEST3_RETIRED_AFTER_TEST4_PASS

echo "PUBLISHED_RELEASE_ID=$RID"
echo "PUBLISHED_ASSET_ID=$AID"
echo "PUBLISHED_SHA=$SHA"
echo "PUBLISHED_SIZE=$SIZE"
echo "RU_SHA=$RU_SHA"
echo "RU_SIZE=$RU_SIZE"
