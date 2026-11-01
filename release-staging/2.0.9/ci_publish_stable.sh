#!/usr/bin/env bash
set -euo pipefail
REPO="KNRDNB/sgp-updates"
TAG="client-v2.0.9"
ZIP="SGP_ClientPatch_2.0.9.zip"
META="SGP_ClientPatch_2.0.9.meta.json"
RUN="41297149806"
HEAD="5d3daef9e8ac23c75f89fa1b3e925a7d1e5b9e96"
ART="regions-unexplored-0.6.3-candidate"
JAR="regions-unexplored-0.6.3-neoforge-21.1.jar"

RUN_JSON="$(gh run view "$RUN" --repo "$REPO" --json conclusion,headSha)"
test "$(printf '%s' "$RUN_JSON"|jq -r '.conclusion')" = success
test "$(printf '%s' "$RUN_JSON"|jq -r '.headSha')" = "$HEAD"

rm -rf .ru063 && mkdir .ru063
gh run download "$RUN" --repo "$REPO" --name "$ART" --dir .ru063
cp ".ru063/$JAR" "$JAR"
test "$(sha256sum "$JAR"|awk '{print $1}')" = "e7f2edd7bab869c2e566b1b251ea54c6b95834205276bf3a302859d72d9d0c9b"
test "$(stat -c '%s' "$JAR")" = "6641783"

python3 release-staging/2.0.9/build_client_209.py | tee build-client-209.txt
python3 scripts/client-release-guard.py --tag "$TAG" --channel stable --zip "$ZIP" --metadata "$META"

if gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1; then echo "Existing release" >&2; exit 1; fi
if gh api "repos/$REPO/git/ref/tags/$TAG" >/dev/null 2>&1; then echo "Existing tag" >&2; exit 1; fi

cat > notes.md <<'EOF'
Точечное обновление Regions Unexplored для NeoForge 1.21.1.

Изменения:
- Regions Unexplored обновлён с 0.6.2 до 0.6.3;
- исправлен upstream-баг, из-за которого обычные еловые саженцы иногда выращивали настоящее RU Pine-дерево;
- старый regions-unexplored-0.6.2-neoforge-21.1.jar удаляется перед установкой regions-unexplored-0.6.3-neoforge-21.1.jar;
- дубликат JAR версий не допускается;
- другие файлы SGP не меняются.

RU 0.6.3 также содержит upstream-исправления лодок, текстур и генерации Prismachasm/Redstone Caves при некоторых сочетаниях biome-модов. Существующие чанки этот SGP patch не переписывает; различия worldgen могут проявиться только в будущих новых чанках.

Обновление рассчитано на stable 2.0.8. Отдельный TEST не выпускался по явному разрешению владельца; runtime PASS остаётся PENDING до проверки рабочего клиента/сервера.
EOF

python3 scripts/client-release-guard.py --tag "$TAG" --channel stable --zip "$ZIP" --metadata "$META" --publish --notes notes.md

REL="$(gh api "repos/$REPO/releases/tags/$TAG")"
test "$(printf '%s' "$REL"|jq -r '.draft')" = false
test "$(printf '%s' "$REL"|jq -r '.prerelease')" = false
RID="$(printf '%s' "$REL"|jq -r '.id')"
ASSETS="$(gh api "repos/$REPO/releases/$RID/assets")"
test "$(printf '%s' "$ASSETS"|jq 'length')" = 2

rm -rf live209 && mkdir live209
gh release download "$TAG" --repo "$REPO" --dir live209
cmp "$ZIP" "live209/$ZIP"
cmp "$META" "live209/$META"
python3 scripts/client-release-guard.py --tag "$TAG" --channel stable --zip "live209/$ZIP" --metadata "live209/$META"

python3 - <<'PY'
import hashlib,json,zipfile
p="live209/SGP_ClientPatch_2.0.9.zip"
with zipfile.ZipFile(p) as z:
    x=json.loads(z.read("patch.json"))
    assert x["fromVersions"]==["2.0.8"] and x["toVersion"]=="2.0.9"
    assert [a["type"] for a in x["actions"]]==["delete","copy"]
    assert x["actions"][0]["target"]=="mods/regions-unexplored-0.6.2-neoforge-21.1.jar"
    a=x["actions"][1]; data=z.read(a["source"])
    assert a["target"]=="mods/regions-unexplored-0.6.3-neoforge-21.1.jar"
    assert hashlib.sha256(data).hexdigest()=="e7f2edd7bab869c2e566b1b251ea54c6b95834205276bf3a302859d72d9d0c9b"
    assert len(data)==6641783
print("LIVE_CLIENT_209_VERIFY_PASS")
PY

AID="$(printf '%s' "$ASSETS"|jq -r --arg n "$ZIP" '.[]|select(.name==$n)|.id')"
MID="$(printf '%s' "$ASSETS"|jq -r --arg n "$META" '.[]|select(.name==$n)|.id')"
{
 echo CLIENT_209_RELEASE_VERIFY_PASS
 echo PUBLISHED_RELEASE_ID=$RID
 echo PUBLISHED_ASSET_ID=$AID
 echo PUBLISHED_META_ASSET_ID=$MID
 echo PUBLISHED_SHA=$(cat client209_sha.txt)
 echo PUBLISHED_SIZE=$(cat client209_size.txt)
 echo META_SHA=$(cat client209_meta_sha.txt)
 echo META_SIZE=$(cat client209_meta_size.txt)
 echo RU_SHA=$(cat ru063_sha.txt)
 echo RU_SIZE=$(cat ru063_size.txt)
 echo SOURCE_COMMIT=$GITHUB_SHA
} | tee release-client-209-result.txt
