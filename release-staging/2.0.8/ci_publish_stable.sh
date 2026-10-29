#!/usr/bin/env bash
set -euo pipefail
REPO="KNRDNB/sgp-updates"
TAG="client-v2.0.8"
ZIP="SGP_ClientPatch_2.0.8.zip"
META="SGP_ClientPatch_2.0.8.meta.json"

python3 release-staging/2.0.8/build_client_208.py | tee build-client-208.txt
python3 scripts/client-release-guard.py --tag "$TAG" --channel stable --zip "$ZIP" --metadata "$META"

if gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1; then echo "Existing release" >&2; exit 1; fi
if gh api "repos/$REPO/git/ref/tags/$TAG" >/dev/null 2>&1; then echo "Existing tag" >&2; exit 1; fi

cat > notes.md <<'EOF'
Точечный compatibility hotfix для FTB Ultimine 2101.1.15.

Исправления:
- SGP Fixes обновлён с rev 1.15 до rev 1.16;
- minecraft:shears добавлены в ftbultimine:included_tools;
- FTB Ultimine теперь может считать ножницы подходящим инструментом даже при наличии компонента minecraft:unbreakable;
- глобальные require_tool / require_valid_tool_for_block не ослаблялись;
- другие предметы в allow-list не добавлялись;
- все остальные файлы SGP Fixes rev 1.15 остались содержательно идентичны.

Обновление рассчитано на stable 2.0.7.

Отдельный TEST не выпускался по явному разрешению владельца из-за узкого декларативного изменения. Runtime PASS остаётся PENDING до проверки на рабочем клиенте/сервере.
EOF

python3 scripts/client-release-guard.py --tag "$TAG" --channel stable --zip "$ZIP" --metadata "$META" --publish --notes notes.md

REL="$(gh api "repos/$REPO/releases/tags/$TAG")"
test "$(printf '%s' "$REL"|jq -r '.draft')" = false
test "$(printf '%s' "$REL"|jq -r '.prerelease')" = false
RID="$(printf '%s' "$REL"|jq -r '.id')"
ASSETS="$(gh api "repos/$REPO/releases/$RID/assets")"
test "$(printf '%s' "$ASSETS"|jq 'length')" = 2
rm -rf live208 && mkdir live208
gh release download "$TAG" --repo "$REPO" --dir live208
cmp "$ZIP" "live208/$ZIP"; cmp "$META" "live208/$META"
python3 scripts/client-release-guard.py --tag "$TAG" --channel stable --zip "live208/$ZIP" --metadata "live208/$META"
python3 - <<'PY'
import io,json,zipfile
p="live208/SGP_ClientPatch_2.0.8.zip"
with zipfile.ZipFile(p) as z:
    x=json.loads(z.read("patch.json"))
    assert x["fromVersions"]==["2.0.7"] and x["toVersion"]=="2.0.8"
    a=x["actions"][0]
    fb=z.read(a["source"])
    with zipfile.ZipFile(io.BytesIO(fb)) as fz:
        assert json.loads(fz.read("data/ftbultimine/tags/item/included_tools.json"))=={"replace":False,"values":["minecraft:shears"]}
        assert json.loads(fz.read("pack.mcmeta"))["pack"]["description"].endswith("internal rev 1.16")
print("LIVE_CLIENT_208_VERIFY_PASS")
PY

AID="$(printf '%s' "$ASSETS"|jq -r --arg n "$ZIP" '.[]|select(.name==$n)|.id')"
MID="$(printf '%s' "$ASSETS"|jq -r --arg n "$META" '.[]|select(.name==$n)|.id')"
{
 echo CLIENT_208_RELEASE_VERIFY_PASS
 echo PUBLISHED_RELEASE_ID=$RID
 echo PUBLISHED_ASSET_ID=$AID
 echo PUBLISHED_META_ASSET_ID=$MID
 echo PUBLISHED_SHA=$(cat client208_sha.txt)
 echo PUBLISHED_SIZE=$(cat client208_size.txt)
 echo META_SHA=$(cat client208_meta_sha.txt)
 echo META_SIZE=$(cat client208_meta_size.txt)
 echo FIX_SHA=$(cat fixes116_sha.txt)
 echo FIX_SIZE=$(cat fixes116_size.txt)
 echo SOURCE_COMMIT=$GITHUB_SHA
} | tee release-client-208-result.txt
