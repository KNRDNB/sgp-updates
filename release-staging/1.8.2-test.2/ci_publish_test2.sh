#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
BASE_TAG="v1.8.1"
BASE_ASSET="SGP_ClientPatch_1.8.1.zip"
BASE_SHA="9f367afb0f4a50d389f671a35767099c5793c2b255e5f385b73b541cf87c2ce8"
TAG="v1.8.2-test.2"
ASSET="SGP_ClientPatch_1.8.2-test.2.zip"
APOTH_VERSION_ID="nEWTeHFF"
APOTH_JAR="Apotheosis-1.21.1-8.8.0.jar"
MOD_JAR="SGP-Apotheosis-Soulbound-Compat-1.0.0.jar"

! gh api "repos/$REPO/releases/tags/v1.8.2-test.1" >/dev/null 2>&1
! gh api "repos/$REPO/git/ref/tags/v1.8.2-test.1" >/dev/null 2>&1
if gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1; then
  echo "Release already exists" >&2
  exit 1
fi

gh release download "$BASE_TAG" --repo "$REPO" -p "$BASE_ASSET"
echo "$BASE_SHA  $BASE_ASSET" | sha256sum -c -
unzip -t "$BASE_ASSET" >/dev/null

curl -fsSL --retry 3 -A "SGP-PatchBuilder/1.0"   "https://api.modrinth.com/v2/version/$APOTH_VERSION_ID" -o apotheosis-version.json
test "$(jq -r '.version_number' apotheosis-version.json)" = "1.21.1-8.8.0"
test "$(jq -r '.loaders | index("neoforge") != null' apotheosis-version.json)" = "true"
test "$(jq -r '.game_versions | index("1.21.1") != null' apotheosis-version.json)" = "true"
URL="$(jq -r --arg f "$APOTH_JAR" '.files[] | select(.filename==$f) | .url' apotheosis-version.json)"
SHA512="$(jq -r --arg f "$APOTH_JAR" '.files[] | select(.filename==$f) | .hashes.sha512' apotheosis-version.json)"
test -n "$URL" && test "$URL" != "null"
test -n "$SHA512" && test "$SHA512" != "null"
curl -fL --retry 3 -A "SGP-PatchBuilder/1.0" -o "$APOTH_JAR" "$URL"
echo "$SHA512  $APOTH_JAR" | sha512sum -c -
unzip -t "$APOTH_JAR" >/dev/null

gradle -p release-staging/1.8.2-test.2/compatmod build --no-daemon --stacktrace
cp release-staging/1.8.2-test.2/compatmod/build/libs/SGP-Apotheosis-Soulbound-Compat-1.0.0.jar "$MOD_JAR"
unzip -t "$MOD_JAR" >/dev/null

unzip -l "$MOD_JAR" > compat-files.txt
grep -Fq 'META-INF/neoforge.mods.toml' compat-files.txt
grep -Fq 'sgp_apotheosis_soulbound_compat.mixins.json' compat-files.txt
grep -Fq 'sgp/apotheosissoulbound/mixin/PotionCharmItemMixin.class' compat-files.txt
grep -Fq 'assets/curios/lang/ru_ru.json' compat-files.txt
unzip -p "$MOD_JAR" assets/curios/lang/ru_ru.json | grep -Fq '"curios.identifier.amulet_pocket": "Кармашек для амулетов"'

unzip -p "$MOD_JAR" META-INF/neoforge.mods.toml > compat-mod.toml
grep -Fq 'modId="sgp_apotheosis_soulbound_compat"' compat-mod.toml
grep -Fq 'modId="apotheosis"' compat-mod.toml
grep -Fq 'versionRange="[8.8.0,8.9.0)"' compat-mod.toml
grep -Fq 'modId="soulbound"' compat-mod.toml
grep -Fq 'versionRange="[1.0.1,1.0.2)"' compat-mod.toml

javap -classpath "$APOTH_JAR" -p -s -c dev.shadowsoffire.apotheosis.item.PotionCharmItem > apoth-potioncharm.txt
grep -Fq 'public boolean supportsEnchantment(net.minecraft.world.item.ItemStack, net.minecraft.core.Holder<net.minecraft.world.item.enchantment.Enchantment>);' apoth-potioncharm.txt
grep -A8 -F 'supportsEnchantment(net.minecraft.world.item.ItemStack' apoth-potioncharm.txt | grep -Fq 'descriptor: (Lnet/minecraft/world/item/ItemStack;Lnet/minecraft/core/Holder;)Z'
grep -A12 -F 'supportsEnchantment(net.minecraft.world.item.ItemStack' apoth-potioncharm.txt | grep -Fq 'iconst_0'
grep -A12 -F 'supportsEnchantment(net.minecraft.world.item.ItemStack' apoth-potioncharm.txt | grep -Fq 'ireturn'
grep -Fq 'public boolean isEnchantable(net.minecraft.world.item.ItemStack);' apoth-potioncharm.txt

javap -classpath "$MOD_JAR" -p -v sgp.apotheosissoulbound.mixin.PotionCharmItemMixin > compat-mixin.txt
grep -Fq 'major version: 65' compat-mixin.txt
grep -Fq 'dev.shadowsoffire.apotheosis.item.PotionCharmItem' compat-mixin.txt
grep -Fq 'supportsEnchantment' compat-mixin.txt
grep -Fq 'org.spongepowered.asm.mixin.injection.Inject' compat-mixin.txt
grep -Fq 'org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable' compat-mixin.txt
grep -Fq 'soulbound' compat-mixin.txt

python3 release-staging/1.8.2-test.2/build_test2.py | tee client-build.txt
python3 release-staging/1.8.2-test.2/build_server_122.py | tee server-build.txt

python3 - <<'PY'
import hashlib,io,json,zipfile
accepted=[
 '1.0.0','1.0.1','1.0.2','1.0.3','1.1.0','1.2.0','1.2.1',
 '1.3.0','1.3.1','1.3.2','1.3.3','1.4.0','1.5.0','1.5.1','1.5.2','1.5.3',
 '1.6.0','1.6.1','1.6.2','1.7.0','1.7.1','1.8.0','1.8.1'
]
with zipfile.ZipFile('SGP_ClientPatch_1.8.2-test.2.zip') as z:
    assert z.testzip() is None
    p=json.loads(z.read('patch.json'))
    assert p['patchId']=='sgp-client-1.8.2-test.2'
    assert p['toVersion']=='1.8.2-test.2'
    for v in accepted: assert v in p['fromVersions'],v
    assert p['fromVersions'][-1]=='1.8.2-test.1'
    assert '1.5.4' not in p['fromVersions']
    a=[x for x in p['actions'] if x.get('target')=='config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip']
    assert len(a)==1
    dp=z.read(a[0]['source'])
    with zipfile.ZipFile(io.BytesIO(dp)) as dz:
        assert dz.testzip() is None
        assert json.loads(dz.read('pack.mcmeta'))['pack']['description'].endswith('internal rev 1.12')
        soul=json.loads(dz.read('data/soulbound/tags/item/enchantable.json'))
        assert soul['values'][-1]=='apotheosis:potion_charm'
        slot=json.loads(dz.read('data/sgp_fixes/curios/slots/amulet_pocket.json'))
        assert slot=={'order':210,'size':6,'icon':'curios:slot/empty_charm_slot','validators':['curios:tag']}
        tag=json.loads(dz.read('data/curios/tags/item/amulet_pocket.json'))
        assert tag=={'replace':False,'values':['apotheosis:potion_charm']}
    m=[x for x in p['actions'] if x.get('target')=='mods/SGP-Apotheosis-Soulbound-Compat-1.0.0.jar']
    assert len(m)==1
    jar=z.read(m[0]['source'])
    assert hashlib.sha256(jar).hexdigest()==m[0]['sha256']
    with zipfile.ZipFile(io.BytesIO(jar)) as jz:
        assert jz.testzip() is None
        assert 'sgp/apotheosissoulbound/mixin/PotionCharmItemMixin.class' in jz.namelist()
with zipfile.ZipFile('SGP_ServerPatch_1.2.2.zip') as z:
    assert z.testzip() is None
    assert sorted(z.namelist())==sorted([
      '.sgp/pack.json','.sgp/history.json',
      'config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip',
      'mods/SGP-Apotheosis-Soulbound-Compat-1.0.0.jar'])
    assert json.loads(z.read('.sgp/pack.json'))['version']=='1.2.2'
    assert json.loads(z.read('.sgp/history.json'))['currentVersion']=='1.2.2'
print('TEST2_EXACT_PACKAGE_AUDIT_PASS')
PY

SHA="$(sha256sum "$ASSET" | awk '{print $1}')"
FIXES_SHA="$(cat fixes_rev112_sha.txt)"
MOD_SHA="$(cat compat_mod_sha.txt)"
SERVER_SHA="$(cat server122_sha.txt)"

{
  echo '## SGP Client 1.8.2-test.2'
  echo
  echo 'Potion Charm Soulbound fix + dedicated 6-slot Curios pocket.'
  echo
  echo '- Exact Apotheosis 8.8.0 PotionCharmItem blocks normal enchantments in supportsEnchantment().'
  echo '- Adds SGP-Apotheosis-Soulbound-Compat-1.0.0.jar: allows only soulbound:soulbound on Potion Charms.'
  echo '- SGP Fixes rev 1.12 keeps apotheosis:potion_charm in soulbound:enchantable.'
  echo '- Adds Curios slot **amulet_pocket**, size **6**, accepting only apotheosis:potion_charm.'
  echo '- Russian slot name: **Кармашек для амулетов**.'
  echo '- Curios 9.5.1 functional slots invoke ItemStack.inventoryTick, preserving Potion Charm effects in the slot.'
  echo '- Cumulative from all accepted stable clients through 1.8.1, plus forward repair from failed 1.8.2-test.1.'
  echo '- No unrelated enchantments/configs/gameplay changes.'
  echo
  printf 'SGP Fixes rev 1.12 SHA-256: %s\n' "$FIXES_SHA"
  printf 'Compat mod SHA-256: %s\n' "$MOD_SHA"
  printf 'Client TEST SHA-256: %s\n' "$SHA"
  printf 'Withheld matching server 1.2.2 SHA-256: %s\n' "$SERVER_SHA"
} > notes.md

gh release create "$TAG" "$ASSET" --repo "$REPO" --target "$GITHUB_SHA"   --title 'SGP Client 1.8.2-test.2' --notes-file notes.md --prerelease

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
with zipfile.ZipFile('verify.zip') as z:
    p=json.loads(z.read('patch.json'))
    assert p['patchId']=='sgp-client-1.8.2-test.2'
    assert p['toVersion']=='1.8.2-test.2'
    assert p['fromVersions'][-1]=='1.8.2-test.1'
    dp_action=next(a for a in p['actions'] if a.get('target')=='config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip')
    with zipfile.ZipFile(io.BytesIO(z.read(dp_action['source']))) as dz:
        assert json.loads(dz.read('data/sgp_fixes/curios/slots/amulet_pocket.json'))['size']==6
        assert json.loads(dz.read('data/curios/tags/item/amulet_pocket.json'))['values']==['apotheosis:potion_charm']
    mod_action=next(a for a in p['actions'] if a.get('target')=='mods/SGP-Apotheosis-Soulbound-Compat-1.0.0.jar')
    with zipfile.ZipFile(io.BytesIO(z.read(mod_action['source']))) as mz:
        assert mz.testzip() is None
        ru=mz.read('assets/curios/lang/ru_ru.json').decode()
        assert 'Кармашек для амулетов' in ru
print('LIVE_CLIENT_182_TEST2_VERIFY_PASS')
PY

echo "PUBLISHED_RELEASE_ID=$RID"
echo "PUBLISHED_ASSET_ID=$AID"
echo "PUBLISHED_SHA=$SHA"
echo "FIXES_SHA=$FIXES_SHA"
echo "MOD_SHA=$MOD_SHA"
echo "SERVER_SHA=$SERVER_SHA"
