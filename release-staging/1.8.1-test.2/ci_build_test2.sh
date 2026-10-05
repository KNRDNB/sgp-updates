#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
BASE_TAG="v1.8.1-test.1"
BASE_ASSET="SGP_ClientPatch_1.8.1-test.1.zip"
BASE_SHA="10cdfdcec2c34815cce6f6dc7293d5b52a2b6609a5c16b3ae0973f759d560952"
STABLE_TAG="v1.8.0"
STABLE_ASSET="SGP_ClientPatch_1.8.0.zip"
STABLE_SHA="34c6f2b223892b92a1c6f1da0074802de474cfe4116fcd5c90e3d869081ef9bb"
CHIPPED_VERSION_ID="eqVowbGc"
CHIPPED_FILE="chipped-neoforge-1.21.1-4.0.2.jar"
CHIPPED_SHA="18ac6fd6b30db4922ccc6ee8bea5b113f69587505b7529834f37ace506427291"
MOD_JAR="SGP-Create-Chipped-Cutting-1.0.1.jar"
ASSET="SGP_ClientPatch_1.8.1-test.2.zip"

gh release download "$BASE_TAG" --repo "$REPO" -p "$BASE_ASSET"
echo "$BASE_SHA  $BASE_ASSET" | sha256sum -c -
unzip -t "$BASE_ASSET" >/dev/null
gh release download "$STABLE_TAG" --repo "$REPO" -p "$STABLE_ASSET"
echo "$STABLE_SHA  $STABLE_ASSET" | sha256sum -c -
unzip -t "$STABLE_ASSET" >/dev/null

curl -fsSL --retry 3 -A "SGP-PatchBuilder/1.0"   "https://api.modrinth.com/v2/version/$CHIPPED_VERSION_ID" -o chipped-version.json
test "$(jq -r '.version_number' chipped-version.json)" = "4.0.2"
test "$(jq -r '.loaders | index("neoforge") != null' chipped-version.json)" = "true"
test "$(jq -r '.game_versions | index("1.21.1") != null' chipped-version.json)" = "true"
URL="$(jq -r --arg f "$CHIPPED_FILE" '.files[] | select(.filename==$f) | .url' chipped-version.json)"
test -n "$URL" && test "$URL" != "null"
curl -fL --retry 3 -A "SGP-PatchBuilder/1.0" -o "$CHIPPED_FILE" "$URL"
echo "$CHIPPED_SHA  $CHIPPED_FILE" | sha256sum -c -
unzip -t "$CHIPPED_FILE" >/dev/null

python3 release-staging/1.8.1-test.2/generate_families.py
test "$(cat hotfix_family_count.txt)" = "277"
test "$(cat hotfix_route_count.txt)" = "6968"

gradle -p release-staging/1.8.1-test.2/compatmod build --no-daemon --stacktrace
cp release-staging/1.8.1-test.2/compatmod/build/libs/SGP-Create-Chipped-Cutting-1.0.1.jar "$MOD_JAR"
unzip -t "$MOD_JAR" >/dev/null

unzip -l "$MOD_JAR" > mod-files.txt
grep -Fq 'META-INF/neoforge.mods.toml' mod-files.txt
grep -Fq 'sgp_create_chipped_cutting.mixins.json' mod-files.txt
grep -Fq 'sgp/createchippedcutting/mixin/SawBlockEntityMixin.class' mod-files.txt
grep -Fq 'sgp/createchippedcutting/jei/SgpCreateChippedJeiPlugin.class' mod-files.txt
! grep -Eq 'data/.*/recipes?/' mod-files.txt

unzip -p "$MOD_JAR" META-INF/neoforge.mods.toml > mod.toml
grep -Fq 'modId="sgp_create_chipped_cutting"' mod.toml
grep -Fq 'version="1.0.1"' mod.toml
grep -Fq 'modId="create"' mod.toml
grep -Fq 'modId="chipped"' mod.toml

CREATE_JAR="$(find ~/.gradle/caches -type f -name 'create-1.21.1-6.0.10-280-slim.jar' | head -n1)"
test -n "$CREATE_JAR"

javap -classpath "$MOD_JAR" -p -v sgp.createchippedcutting.mixin.SawBlockEntityMixin > hotfix-mixin.txt
grep -Fq 'major version: 65' hotfix-mixin.txt
grep -Fq 'org.spongepowered.asm.mixin.Mixin' hotfix-mixin.txt
grep -Fq 'org.spongepowered.asm.mixin.injection.Redirect' hotfix-mixin.txt
grep -Fq 'RecipeFinder;get' hotfix-mixin.txt
javap -classpath "$CREATE_JAR" -p -s com.simibubi.create.content.kinetics.saw.SawBlockEntity > create-saw.txt
grep -Fq 'private java.util.List<net.minecraft.world.item.crafting.RecipeHolder<? extends net.minecraft.world.item.crafting.Recipe<?>>> getRecipes();' create-saw.txt
grep -A1 -F 'getRecipes();' create-saw.txt | grep -Fq 'descriptor: ()Ljava/util/List;'
javap -classpath "$CREATE_JAR" -p -s com.simibubi.create.foundation.recipe.RecipeFinder > create-recipefinder.txt
grep -Fq 'descriptor: (Ljava/lang/Object;Lnet/minecraft/world/level/Level;Ljava/util/function/Predicate;)Ljava/util/List;' create-recipefinder.txt

JEI_API="$(find ~/.gradle/caches -type f \( -name 'jei-1.21.1-common-api-19.21.0.247.jar' -o -name 'jei-1.21.1-neoforge-api-19.21.0.247.jar' \) | paste -sd: -)"
test -n "$JEI_API"
javap -classpath "$MOD_JAR:$JEI_API:$CREATE_JAR" -p -v sgp.createchippedcutting.jei.SgpCreateChippedJeiPlugin > hotfix-jei.txt
grep -Fq 'major version: 65' hotfix-jei.txt
grep -Fq 'mezz.jei.api.JeiPlugin' hotfix-jei.txt
grep -Fq 'createJeiRecipes' hotfix-jei.txt
grep -Fq 'createRecipeHolderType' hotfix-jei.txt
grep -Fq 'sawing' hotfix-jei.txt

javap -classpath "$MOD_JAR:$CREATE_JAR" -p -v sgp.createchippedcutting.DynamicCuttingBridge > hotfix-bridge.txt
grep -Fq 'createJeiRecipes' hotfix-bridge.txt
! grep -Fq 'mezz/jei' hotfix-bridge.txt
echo CREATE_CHIPPED_TEST2_MIXIN_JEI_PREFLIGHT_PASS

python3 release-staging/1.8.1-test.2/build_client_181_test2.py | tee client-build.txt
python3 release-staging/1.8.1-test.2/build_server_121.py | tee server-build.txt

python3 - <<'PY'
import io,json,zipfile
accepted=['1.0.0','1.0.1','1.0.2','1.0.3','1.1.0','1.2.0','1.2.1','1.3.0','1.3.1','1.3.2','1.3.3','1.4.0','1.5.0','1.5.1','1.5.2','1.5.3','1.6.0','1.6.1','1.6.2','1.7.0','1.7.1','1.8.0']
with zipfile.ZipFile('SGP_ClientPatch_1.8.1-test.2.zip') as z:
    assert z.testzip() is None
    p=json.loads(z.read('patch.json'))
    assert p['patchId']=='sgp-client-1.8.1-test.2'
    assert p['toVersion']=='1.8.1-test.2'
    for v in accepted: assert v in p['fromVersions'],v
    assert p['fromVersions'][-1]=='1.8.1-test.1'
    assert '1.5.4' not in p['fromVersions']
    assert 'files/config/paxi/datapacks/SGP_Create_Chipped_Cutting_MC1.21.1.zip' not in z.namelist()
    assert 'files/mods/SGP-Create-Chipped-Cutting-1.0.0.jar' not in z.namelist()
    assert any(a.get('actionId')=='remove-sgp-create-chipped-cutting-datapack' for a in p['actions'])
    assert any(a.get('actionId')=='remove-sgp-create-chipped-cutting-runtime-1-0-0' for a in p['actions'])
    assert any(a.get('actionId')=='install-sgp-create-chipped-cutting-runtime-1-0-1' for a in p['actions'])
    mod=z.read('files/mods/SGP-Create-Chipped-Cutting-1.0.1.jar')
    with zipfile.ZipFile(io.BytesIO(mod)) as mz:
        assert mz.testzip() is None
        names=mz.namelist()
        assert not any('/recipe/' in n or '/recipes/' in n for n in names)
        assert 'sgp/createchippedcutting/jei/SgpCreateChippedJeiPlugin.class' in names
with zipfile.ZipFile('SGP_ServerPatch_1.2.1.zip') as z:
    assert z.testzip() is None
    assert sorted(z.namelist())==sorted(['.sgp/pack.json','.sgp/history.json','mods/SGP-Create-Chipped-Cutting-1.0.1.jar'])
    assert json.loads(z.read('.sgp/pack.json'))['version']=='1.2.1'
    assert json.loads(z.read('.sgp/history.json'))['currentVersion']=='1.2.1'
print('HOTFIX_TEST2_CUMULATIVE_PACKAGE_AUDIT_PASS')
PY

sha256sum "$ASSET"
sha256sum SGP_ServerPatch_1.2.1.zip
