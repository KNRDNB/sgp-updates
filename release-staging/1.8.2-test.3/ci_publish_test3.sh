#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
BASE_TAG="v1.8.1"
BASE_ASSET="SGP_ClientPatch_1.8.1.zip"
BASE_SHA="9f367afb0f4a50d389f671a35767099c5793c2b255e5f385b73b541cf87c2ce8"
TAG="v1.8.2-test.3"
ASSET="SGP_ClientPatch_1.8.2-test.3.zip"
OLD_ARTIFACT_ID="11359569157"
MOD_JAR="SGP-Apotheosis-Soulbound-Compat-1.0.0.jar"
MOD_SHA="2e4857df16f2df04ef7b86674bd26cf737d671931646ccb4b707c4a7a6cf46d9"

! gh api "repos/$REPO/releases/tags/v1.8.2-test.2" >/dev/null 2>&1
! gh api "repos/$REPO/git/ref/tags/v1.8.2-test.2" >/dev/null 2>&1

if gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1; then
  echo "Release already exists" >&2
  exit 1
fi

gh release download "$BASE_TAG" --repo "$REPO" -p "$BASE_ASSET"
echo "$BASE_SHA  $BASE_ASSET" | sha256sum -c -
unzip -t "$BASE_ASSET" >/dev/null

# Preserve the already-working Soulbound compat bytes exactly from successful test.2 evidence.
gh api "repos/$REPO/actions/artifacts/$OLD_ARTIFACT_ID/zip" > old-server-artifact.zip
unzip -t old-server-artifact.zip >/dev/null
unzip -o old-server-artifact.zip -d old-server-artifact >/dev/null
test -f old-server-artifact/SGP_ServerPatch_1.2.2.zip
unzip -p old-server-artifact/SGP_ServerPatch_1.2.2.zip "mods/$MOD_JAR" > "$MOD_JAR"
echo "$MOD_SHA  $MOD_JAR" | sha256sum -c -
unzip -t "$MOD_JAR" >/dev/null

python3 release-staging/1.8.2-test.3/build_test3.py | tee client-build.txt
python3 release-staging/1.8.2-test.3/build_server_122.py | tee server-build.txt

python3 - <<'PY'
import hashlib,io,json,zipfile
accepted=[
 '1.0.0','1.0.1','1.0.2','1.0.3','1.1.0','1.2.0','1.2.1',
 '1.3.0','1.3.1','1.3.2','1.3.3','1.4.0','1.5.0','1.5.1','1.5.2','1.5.3',
 '1.6.0','1.6.1','1.6.2','1.7.0','1.7.1','1.8.0','1.8.1'
]
with zipfile.ZipFile('SGP_ClientPatch_1.8.2-test.3.zip') as z:
    assert z.testzip() is None
    p=json.loads(z.read('patch.json'))
    assert p['patchId']=='sgp-client-1.8.2-test.3'
    assert p['toVersion']=='1.8.2-test.3'
    for v in accepted: assert v in p['fromVersions'],v
    assert p['fromVersions'][-2:]==['1.8.2-test.1','1.8.2-test.2']
    assert '1.5.4' not in p['fromVersions']

    fix=next(a for a in p['actions'] if a.get('target')=='config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip')
    dp=z.read(fix['source'])
    assert hashlib.sha256(dp).hexdigest()==fix['sha256']
    assert len(dp)==fix['size']
    with zipfile.ZipFile(io.BytesIO(dp)) as dz:
        assert dz.testzip() is None
        meta=json.loads(dz.read('pack.mcmeta'))
        assert meta['pack']['description'].endswith('internal rev 1.13')
        soul=json.loads(dz.read('data/soulbound/tags/item/enchantable.json'))
        assert soul['values'][-1]=='apotheosis:potion_charm'
        slot=json.loads(dz.read('data/sgp_fixes/curios/slots/amulet_pocket.json'))
        assert slot=={
          'order':210,'size':6,'icon':'curios:slot/empty_charm_slot',
          'validators':['curios:tag'],'entities':['minecraft:player']
        }
        tag=json.loads(dz.read('data/curios/tags/item/amulet_pocket.json'))
        assert tag=={'replace':False,'values':['apotheosis:potion_charm']}

    ru=next(a for a in p['actions'] if a.get('target')=='config/paxi/resourcepacks/SGP_RU_Localization_MC1.21.1.zip')
    rp=z.read(ru['source'])
    assert hashlib.sha256(rp).hexdigest()==ru['sha256']
    assert len(rp)==ru['size']
    with zipfile.ZipFile(io.BytesIO(rp)) as rz:
        assert rz.testzip() is None
        meta=json.loads(rz.read('pack.mcmeta'))
        assert 'SGP RU Localization 1.9' in meta['pack']['description']
        lang=json.loads(rz.read('assets/curios/lang/ru_ru.json'))
        assert lang['curios.identifier.glasses']=='Очки'
        assert lang['curios.identifier.amulet_pocket']=='Кармашек для амулетов'
        assert lang['curios.identifier.wings']=='Крылья'
        assert lang['curios.identifier.quiver']=='Колчан'

    mod=next(a for a in p['actions'] if a.get('target')=='mods/SGP-Apotheosis-Soulbound-Compat-1.0.0.jar')
    jar=z.read(mod['source'])
    assert hashlib.sha256(jar).hexdigest()=='2e4857df16f2df04ef7b86674bd26cf737d671931646ccb4b707c4a7a6cf46d9'

with zipfile.ZipFile('SGP_ServerPatch_1.2.2.zip') as z:
    assert z.testzip() is None
    assert sorted(z.namelist())==sorted([
      '.sgp/pack.json','.sgp/history.json',
      'config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip',
      'mods/SGP-Apotheosis-Soulbound-Compat-1.0.0.jar'
    ])
    assert json.loads(z.read('.sgp/pack.json'))['version']=='1.2.2'
    with zipfile.ZipFile(io.BytesIO(z.read('config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip'))) as dz:
        slot=json.loads(dz.read('data/sgp_fixes/curios/slots/amulet_pocket.json'))
        assert slot['entities']==['minecraft:player']
print('TEST3_EXACT_PACKAGE_AUDIT_PASS')
PY

SHA="$(sha256sum "$ASSET" | awk '{print $1}')"
FIXES_SHA="$(cat fixes_rev113_sha.txt)"
RU_SHA="$(cat ru_19_sha.txt)"
SERVER_SHA="$(cat server122_sha.txt)"

{
  echo '## SGP Client 1.8.2-test.3'
  echo
  echo 'Potion Charm Soulbound + corrected 6-slot Amulet Pocket + Curios Russian names.'
  echo
  echo '- Keeps the already-working Soulbound compat JAR byte-identical to test.2.'
  echo '- Fixes the missing Amulet Pocket by attaching the slot type to **minecraft:player**.'
  echo '- Amulet Pocket remains **size 6** and accepts only **apotheosis:potion_charm**.'
  echo '- Updates SGP RU Localization to **1.9**: **Glasses → Очки** and **amulet_pocket → Кармашек для амулетов**.'
  echo '- Cumulative from all accepted stable clients through 1.8.1, plus forward repair from test.1/test.2.'
  echo
  printf 'SGP Fixes rev 1.13 SHA-256: %s\n' "$FIXES_SHA"
  printf 'SGP RU Localization 1.9 SHA-256: %s\n' "$RU_SHA"
  printf 'Soulbound compat SHA-256 (unchanged): %s\n' "$MOD_SHA"
  printf 'Client TEST SHA-256: %s\n' "$SHA"
  printf 'Withheld matching server 1.2.2 SHA-256: %s\n' "$SERVER_SHA"
} > notes.md

gh release create "$TAG" "$ASSET" --repo "$REPO" --target "$GITHUB_SHA"   --title 'SGP Client 1.8.2-test.3' --notes-file notes.md --prerelease

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
with zipfile.ZipFile('verify.zip') as z:
    p=json.loads(z.read('patch.json'))
    assert p['patchId']=='sgp-client-1.8.2-test.3'
    assert p['toVersion']=='1.8.2-test.3'
    assert p['fromVersions'][-2:]==['1.8.2-test.1','1.8.2-test.2']
    f=next(a for a in p['actions'] if a.get('target')=='config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip')
    with zipfile.ZipFile(io.BytesIO(z.read(f['source']))) as dz:
        slot=json.loads(dz.read('data/sgp_fixes/curios/slots/amulet_pocket.json'))
        assert slot['size']==6
        assert slot['entities']==['minecraft:player']
    r=next(a for a in p['actions'] if a.get('target')=='config/paxi/resourcepacks/SGP_RU_Localization_MC1.21.1.zip')
    with zipfile.ZipFile(io.BytesIO(z.read(r['source']))) as rz:
        lang=json.loads(rz.read('assets/curios/lang/ru_ru.json'))
        assert lang['curios.identifier.glasses']=='Очки'
        assert lang['curios.identifier.amulet_pocket']=='Кармашек для амулетов'
    m=next(a for a in p['actions'] if a.get('target')=='mods/SGP-Apotheosis-Soulbound-Compat-1.0.0.jar')
    assert hashlib.sha256(z.read(m['source'])).hexdigest()=='2e4857df16f2df04ef7b86674bd26cf737d671931646ccb4b707c4a7a6cf46d9'
print('LIVE_CLIENT_182_TEST3_VERIFY_PASS')
PY

echo "PUBLISHED_RELEASE_ID=$RID"
echo "PUBLISHED_ASSET_ID=$AID"
echo "PUBLISHED_SHA=$SHA"
echo "FIXES_SHA=$FIXES_SHA"
echo "RU_SHA=$RU_SHA"
echo "SERVER_SHA=$SERVER_SHA"
