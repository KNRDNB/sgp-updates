#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
TEST_TAG="v1.8.2-test.4"
TEST_ASSET="SGP_ClientPatch_1.8.2-test.4.zip"
TEST_SHA="170ba57c169b1466e918beafc32c5ac683368c78fed3183966c16ff0c1f5433f"
TAG="v1.8.2"
ASSET="SGP_ClientPatch_1.8.2.zip"

if gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1; then
  echo "Stable already exists" >&2
  exit 1
fi

gh release download "$TEST_TAG" --repo "$REPO" -p "$TEST_ASSET"
echo "$TEST_SHA  $TEST_ASSET" | sha256sum -c -
unzip -t "$TEST_ASSET" >/dev/null

python3 release-staging/1.8.2/build_stable182.py | tee stable-build.txt
SHA="$(sha256sum "$ASSET" | awk '{print $1}')"

{
  echo '## SGP Client 1.8.2'
  echo
  echo 'Stable promotion from owner-runtime-PASS **1.8.2-test.4**.'
  echo
  echo '- Exact tested payload/action set preserved.'
  echo '- Potion Charm Soulbound compatibility retained.'
  echo '- Six Amulet Pocket Curios cells retained through the exact tested targeted tomlEdit.'
  echo '- SGP RU Localization 1.9: Glasses → Очки; amulet_pocket → Кармашек для амулетов.'
  echo '- Cumulative from every accepted stable through 1.8.1; forward repair includes all 1.8.2 TEST states through test.4.'
  echo
  printf 'SHA-256: %s\n' "$SHA"
} > notes.md

gh release create "$TAG" "$ASSET" --repo "$REPO" --target "$GITHUB_SHA" \
  --title 'SGP Client 1.8.2' --notes-file notes.md

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
    assert p['patchId']=='sgp-client-1.8.2'
    assert p['toVersion']=='1.8.2'
    assert p['fromVersions'][-1]=='1.8.2-test.4'
    assert '1.8.1' in p['fromVersions']
    assert '1.5.4' not in p['fromVersions']

    curios=[
        a for a in p['actions']
        if a.get('type')=='tomlEdit' and a.get('target')=='config/curios-common.toml'
    ]
    matching=[
        e for a in curios for e in a.get('edits',[])
        if e.get('op')=='arrayAddUnique'
        and e.get('path')=='slots'
        and e.get('value')=='id=amulet_pocket;size=6;order=-70'
        and e.get('createIfMissing') is False
    ]
    assert len(matching)==1

    fix=next(a for a in p['actions'] if a.get('target')=='config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip')
    with zipfile.ZipFile(io.BytesIO(z.read(fix['source']))) as dz:
        assert dz.testzip() is None
        assert json.loads(dz.read('pack.mcmeta'))['pack']['description'].endswith('internal rev 1.14')
        assert json.loads(dz.read('data/curios/tags/item/amulet_pocket.json'))['values']==['apotheosis:potion_charm']

    ru=next(a for a in p['actions'] if a.get('target')=='config/paxi/resourcepacks/SGP_RU_Localization_MC1.21.1.zip')
    with zipfile.ZipFile(io.BytesIO(z.read(ru['source']))) as rz:
        lang=json.loads(rz.read('assets/curios/lang/ru_ru.json'))
        assert lang['curios.identifier.glasses']=='Очки'
        assert lang['curios.identifier.amulet_pocket']=='Кармашек для амулетов'

    mod=next(a for a in p['actions'] if a.get('target')=='mods/SGP-Apotheosis-Soulbound-Compat-1.0.0.jar')
    assert hashlib.sha256(z.read(mod['source'])).hexdigest()=='2e4857df16f2df04ef7b86674bd26cf737d671931646ccb4b707c4a7a6cf46d9'
print('LIVE_STABLE_182_VERIFY_PASS')
PY

gh api "repos/$REPO/releases/tags/$TEST_TAG" >/dev/null
echo CURRENT_SUCCESSFUL_TEST_RETAINED
echo "PUBLISHED_RELEASE_ID=$RID"
echo "PUBLISHED_ASSET_ID=$AID"
echo "PUBLISHED_SHA=$SHA"
