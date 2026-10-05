#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
BASE_TAG="v1.8.1"
BASE_ASSET="SGP_ClientPatch_1.8.1.zip"
BASE_SHA="9f367afb0f4a50d389f671a35767099c5793c2b255e5f385b73b541cf87c2ce8"
TAG="v1.8.2-test.4"
ASSET="SGP_ClientPatch_1.8.2-test.4.zip"
OLD_ARTIFACT_ID="11360648920"
MOD_JAR="SGP-Apotheosis-Soulbound-Compat-1.0.0.jar"
MOD_SHA="2e4857df16f2df04ef7b86674bd26cf737d671931646ccb4b707c4a7a6cf46d9"

! gh api "repos/$REPO/releases/tags/v1.8.2-test.3" >/dev/null 2>&1
! gh api "repos/$REPO/git/ref/tags/v1.8.2-test.3" >/dev/null 2>&1

if gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1; then
  echo "Release already exists" >&2
  exit 1
fi

gh release download "$BASE_TAG" --repo "$REPO" -p "$BASE_ASSET"
echo "$BASE_SHA  $BASE_ASSET" | sha256sum -c -
unzip -t "$BASE_ASSET" >/dev/null

gh api "repos/$REPO/actions/artifacts/$OLD_ARTIFACT_ID/zip" > old-server-artifact.zip
unzip -t old-server-artifact.zip >/dev/null
unzip -o old-server-artifact.zip -d old-server-artifact >/dev/null
test -f old-server-artifact/SGP_ServerPatch_1.2.2.zip
unzip -p old-server-artifact/SGP_ServerPatch_1.2.2.zip "mods/$MOD_JAR" > "$MOD_JAR"
echo "$MOD_SHA  $MOD_JAR" | sha256sum -c -
unzip -t "$MOD_JAR" >/dev/null

python3 release-staging/1.8.2-test.4/build_test4.py | tee client-build.txt
python3 release-staging/1.8.2-test.4/build_server_122.py | tee server-build.txt

python3 - <<'PY'
import hashlib,io,json,zipfile
accepted=[
 '1.0.0','1.0.1','1.0.2','1.0.3','1.1.0','1.2.0','1.2.1',
 '1.3.0','1.3.1','1.3.2','1.3.3','1.4.0','1.5.0','1.5.1','1.5.2','1.5.3',
 '1.6.0','1.6.1','1.6.2','1.7.0','1.7.1','1.8.0','1.8.1'
]
with zipfile.ZipFile('SGP_ClientPatch_1.8.2-test.4.zip') as z:
    assert z.testzip() is None
    p=json.loads(z.read('patch.json'))
    assert p['patchId']=='sgp-client-1.8.2-test.4'
    assert p['toVersion']=='1.8.2-test.4'
    for v in accepted: assert v in p['fromVersions'],v
    assert p['fromVersions'][-3:]==['1.8.2-test.1','1.8.2-test.2','1.8.2-test.3']
    assert '1.5.4' not in p['fromVersions']

    curios_actions=[
        a for a in p['actions']
        if a.get('type')=='tomlEdit' and a.get('target')=='config/curios-common.toml'
    ]
    values=[
        e.get('value')
        for a in curios_actions
        for e in a.get('edits',[])
        if e.get('op')=='arrayAddUnique' and e.get('path')=='slots'
    ]
    assert 'id=wings;size=1;order=-100;add_cosmetic=true' in values
    assert 'id=quiver;size=1;order=-90;add_cosmetic=true' in values
    assert 'id=glasses;size=1;order=-80;add_cosmetic=true' in values
    assert values.count('id=amulet_pocket;size=6;order=-70')==1

    fix=next(a for a in p['actions'] if a.get('target')=='config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip')
    dp=z.read(fix['source'])
    assert hashlib.sha256(dp).hexdigest()==fix['sha256']
    with zipfile.ZipFile(io.BytesIO(dp)) as dz:
        assert dz.testzip() is None
        assert json.loads(dz.read('pack.mcmeta'))['pack']['description'].endswith('internal rev 1.14')
        assert 'data/sgp_fixes/curios/slots/amulet_pocket.json' not in dz.namelist()
        assert json.loads(dz.read('data/curios/tags/item/amulet_pocket.json'))=={
            'replace':False,'values':['apotheosis:potion_charm']
        }
        assert json.loads(dz.read('data/soulbound/tags/item/enchantable.json'))['values'][-1]=='apotheosis:potion_charm'

    ru=next(a for a in p['actions'] if a.get('target')=='config/paxi/resourcepacks/SGP_RU_Localization_MC1.21.1.zip')
    rp=z.read(ru['source'])
    assert hashlib.sha256(rp).hexdigest()=='69cb222e2983abddb2a5dbd56c0e2d1a749529a2f332d3ae03376b3a7e3a7418'
    with zipfile.ZipFile(io.BytesIO(rp)) as rz:
        lang=json.loads(rz.read('assets/curios/lang/ru_ru.json'))
        assert lang['curios.identifier.glasses']=='Очки'
        assert lang['curios.identifier.amulet_pocket']=='Кармашек для амулетов'

    mod=next(a for a in p['actions'] if a.get('target')=='mods/SGP-Apotheosis-Soulbound-Compat-1.0.0.jar')
    assert hashlib.sha256(z.read(mod['source'])).hexdigest()=='2e4857df16f2df04ef7b86674bd26cf737d671931646ccb4b707c4a7a6cf46d9'

with zipfile.ZipFile('SGP_ServerPatch_1.2.2.zip') as z:
    assert z.testzip() is None
    assert sorted(z.namelist())==sorted([
      '.sgp/pack.json','.sgp/history.json',
      'config/curios-common.toml',
      'config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip',
      'mods/SGP-Apotheosis-Soulbound-Compat-1.0.0.jar'
    ])
    assert json.loads(z.read('.sgp/pack.json'))['version']=='1.2.2'
    assert 'id=amulet_pocket;size=6;order=-70' in z.read('config/curios-common.toml').decode('utf-8')
print('TEST4_EXACT_PACKAGE_AUDIT_PASS')
PY

SHA="$(sha256sum "$ASSET" | awk '{print $1}')"
FIXES_SHA="$(cat fixes_rev114_sha.txt)"
RU_SHA="$(cat ru_19_sha.txt)"
CFG_SHA="$(cat server122_curios_config_sha.txt)"
SERVER_SHA="$(cat server122_sha.txt)"

{
  echo '## SGP Client 1.8.2-test.4'
  echo
  echo 'Potion Charm Soulbound + Amulet Pocket registered through the proven Curios common-config path.'
  echo
  echo '- Keeps the owner-PASS Soulbound compat JAR byte-identical.'
  echo '- Keeps owner-PASS SGP RU Localization 1.9 byte-identical: Glasses → Очки.'
  echo '- Adds **amulet_pocket;size=6** via Installer **tomlEdit/arrayAddUnique** on **config/curios-common.toml**, exactly like the existing SGP wings/quiver/glasses actions.'
  echo '- SGP Fixes rev 1.14 keeps only the Potion Charm item tag for curios:amulet_pocket; failed datapack slot definition is removed.'
  echo '- Tooltip should therefore resolve «Слот: Кармашек для амулетов» once Curios loads the config-created slot type.'
  echo '- Cumulative from all accepted stable clients through 1.8.1, plus forward repair from test.1/test.2/test.3.'
  echo
  printf 'SGP Fixes rev 1.14 SHA-256: %s\n' "$FIXES_SHA"
  printf 'SGP RU Localization 1.9 SHA-256 (unchanged): %s\n' "$RU_SHA"
  printf 'curios-common.toml SHA-256: %s\n' "$CFG_SHA"
  printf 'Soulbound compat SHA-256 (unchanged): %s\n' "$MOD_SHA"
  printf 'Client TEST SHA-256: %s\n' "$SHA"
  printf 'Withheld matching server 1.2.2 SHA-256: %s\n' "$SERVER_SHA"
} > notes.md

gh release create "$TAG" "$ASSET" --repo "$REPO" --target "$GITHUB_SHA" \
  --title 'SGP Client 1.8.2-test.4' --notes-file notes.md --prerelease

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
    assert p['patchId']=='sgp-client-1.8.2-test.4'
    assert p['toVersion']=='1.8.2-test.4'
    assert p['fromVersions'][-3:]==['1.8.2-test.1','1.8.2-test.2','1.8.2-test.3']
    curios_actions=[
        a for a in p['actions']
        if a.get('type')=='tomlEdit' and a.get('target')=='config/curios-common.toml'
    ]
    matching=[
        e for a in curios_actions for e in a.get('edits',[])
        if e.get('op')=='arrayAddUnique'
        and e.get('path')=='slots'
        and e.get('value')=='id=amulet_pocket;size=6;order=-70'
        and e.get('createIfMissing') is False
    ]
    assert len(matching)==1
    f=next(a for a in p['actions'] if a.get('target')=='config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip')
    with zipfile.ZipFile(io.BytesIO(z.read(f['source']))) as dz:
        assert 'data/sgp_fixes/curios/slots/amulet_pocket.json' not in dz.namelist()
        assert json.loads(dz.read('data/curios/tags/item/amulet_pocket.json'))['values']==['apotheosis:potion_charm']
    r=next(a for a in p['actions'] if a.get('target')=='config/paxi/resourcepacks/SGP_RU_Localization_MC1.21.1.zip')
    assert hashlib.sha256(z.read(r['source'])).hexdigest()=='69cb222e2983abddb2a5dbd56c0e2d1a749529a2f332d3ae03376b3a7e3a7418'
    m=next(a for a in p['actions'] if a.get('target')=='mods/SGP-Apotheosis-Soulbound-Compat-1.0.0.jar')
    assert hashlib.sha256(z.read(m['source'])).hexdigest()=='2e4857df16f2df04ef7b86674bd26cf737d671931646ccb4b707c4a7a6cf46d9'
print('LIVE_CLIENT_182_TEST4_VERIFY_PASS')
PY

echo "PUBLISHED_RELEASE_ID=$RID"
echo "PUBLISHED_ASSET_ID=$AID"
echo "PUBLISHED_SHA=$SHA"
echo "FIXES_SHA=$FIXES_SHA"
echo "RU_SHA=$RU_SHA"
echo "CONFIG_SHA=$CFG_SHA"
echo "SERVER_SHA=$SERVER_SHA"
