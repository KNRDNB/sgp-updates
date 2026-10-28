#!/usr/bin/env bash
set -euo pipefail
REPO="KNRDNB/sgp-updates"
TAG="client-v2.0.6"
ZIP="SGP_ClientPatch_2.0.6.zip"
META="SGP_ClientPatch_2.0.6.meta.json"
RUN="40723100648"
ART="sgp-ftb-auto-protect-1.0.2-candidate"
JAR="SGP-FTB-Spawn-Guard-Auto-Protect-1.0.2.jar"

rm -rf .addon206 && mkdir .addon206
gh run download "$RUN" --repo "$REPO" --name "$ART" --dir .addon206
cp ".addon206/$JAR" "$JAR"
test "$(sha256sum "$JAR"|awk '{print $1}')" = "537f31e8a3c3904681fa6e089087514117e372d63a3361a30ee1675cc594eaea"
test "$(stat -c '%s' "$JAR")" = "13475"

python3 release-staging/2.0.6/build_client_206.py | tee build-client-206.txt
python3 scripts/client-release-guard.py --tag "$TAG" --channel stable --zip "$ZIP" --metadata "$META"

if gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1; then echo "Existing release" >&2; exit 1; fi
if gh api "repos/$REPO/git/ref/tags/$TAG" >/dev/null 2>&1; then echo "Existing tag" >&2; exit 1; fi

cat > notes.md <<'EOF'
Production hotfix после аварийного 2.0.5.

Исправления:
- устранён IllegalAccessException, из-за которого SGP Auto Protect 1.0.1 валил загрузку клиента и dedicated server;
- регистрация FTB AFTER_CLAIM теперь выполняется через публичный интерфейс Architectury Event, а не через package-private EventFactory$EventImpl;
- сохранён direct AFTER_CLAIM auto-protect без повторного lookup claim;
- сохранён SGP serverbound transport для одиночных Mob Control toggle, чтобы не использовать vanilla command-spam path;
- сторонний FTB Chunks Mobs Spawn Control 1.0.4 не модифицируется;
- protected_chunks.properties не распространяется и не перезаписывается.

Патч поддерживает прямое обновление как с 2.0.4, так и с аварийного 2.0.5.

Отдельного тестового сервера нет. Релиз выполнен по явному разрешению владельца; runtime PASS остаётся PENDING до проверки на рабочем сервере.
EOF

python3 scripts/client-release-guard.py --tag "$TAG" --channel stable --zip "$ZIP" --metadata "$META" --publish --notes notes.md

REL="$(gh api "repos/$REPO/releases/tags/$TAG")"
test "$(printf '%s' "$REL"|jq -r '.draft')" = false
test "$(printf '%s' "$REL"|jq -r '.prerelease')" = false
RID="$(printf '%s' "$REL"|jq -r '.id')"
ASSETS="$(gh api "repos/$REPO/releases/$RID/assets")"
test "$(printf '%s' "$ASSETS"|jq 'length')" = 2
rm -rf live206 && mkdir live206
gh release download "$TAG" --repo "$REPO" --dir live206
cmp "$ZIP" "live206/$ZIP"; cmp "$META" "live206/$META"
python3 scripts/client-release-guard.py --tag "$TAG" --channel stable --zip "live206/$ZIP" --metadata "live206/$META"

python3 - <<'PY'
import hashlib,json,zipfile
p="live206/SGP_ClientPatch_2.0.6.zip"
with zipfile.ZipFile(p) as z:
    x=json.loads(z.read("patch.json"))
    assert x["fromVersions"]==["2.0.4","2.0.5"] and x["toVersion"]=="2.0.6"
    assert [a["type"] for a in x["actions"]]==["delete","delete","copy"]
    a=x["actions"][2]; data=z.read(a["source"])
    assert hashlib.sha256(data).hexdigest()=="537f31e8a3c3904681fa6e089087514117e372d63a3361a30ee1675cc594eaea"
    assert len(data)==13475
print("LIVE_CLIENT_206_VERIFY_PASS")
PY

AID="$(printf '%s' "$ASSETS"|jq -r --arg n "$ZIP" '.[]|select(.name==$n)|.id')"
MID="$(printf '%s' "$ASSETS"|jq -r --arg n "$META" '.[]|select(.name==$n)|.id')"
{
 echo CLIENT_206_RELEASE_VERIFY_PASS
 echo PUBLISHED_RELEASE_ID=$RID
 echo PUBLISHED_ASSET_ID=$AID
 echo PUBLISHED_META_ASSET_ID=$MID
 echo PUBLISHED_SHA=$(cat client206_sha.txt)
 echo PUBLISHED_SIZE=$(cat client206_size.txt)
 echo META_SHA=$(cat client206_meta_sha.txt)
 echo META_SIZE=$(cat client206_meta_size.txt)
 echo ADDON_RUN=$RUN
 echo ADDON_ARTIFACT_ID=12831891949
 echo ADDON_SHA=537f31e8a3c3904681fa6e089087514117e372d63a3361a30ee1675cc594eaea
 echo ADDON_SIZE=13475
 echo SOURCE_COMMIT=$GITHUB_SHA
} | tee release-client-206-result.txt
