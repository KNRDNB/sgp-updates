#!/usr/bin/env bash
set -euo pipefail
REPO="KNRDNB/sgp-updates"
TAG="client-v2.0.7"
ZIP="SGP_ClientPatch_2.0.7.zip"
META="SGP_ClientPatch_2.0.7.meta.json"
RUN="40728093121"
HEAD="2a592bbd05b222db82662ffab8c20a8093f34df6"
ART="sgp-ftb-auto-protect-1.0.3-candidate"
JAR="SGP-FTB-Spawn-Guard-Auto-Protect-1.0.3.jar"

gh run watch "$RUN" --repo "$REPO" --exit-status
RUN_JSON="$(gh run view "$RUN" --repo "$REPO" --json conclusion,headSha)"
test "$(printf '%s' "$RUN_JSON"|jq -r '.conclusion')" = success
test "$(printf '%s' "$RUN_JSON"|jq -r '.headSha')" = "$HEAD"

rm -rf .addon207 && mkdir .addon207
gh run download "$RUN" --repo "$REPO" --name "$ART" --dir .addon207
cp ".addon207/$JAR" "$JAR"
cp ".addon207/sgp207_addon_sha.txt" sgp207_addon_sha.txt
cp ".addon207/sgp207_addon_size.txt" sgp207_addon_size.txt
test "$(sha256sum "$JAR"|awk '{print $1}')" = "$(awk '{print $1}' sgp207_addon_sha.txt)"
test "$(stat -c '%s' "$JAR")" = "$(cat sgp207_addon_size.txt)"

python3 release-staging/2.0.7/build_client_207.py | tee build-client-207.txt
python3 scripts/client-release-guard.py --tag "$TAG" --channel stable --zip "$ZIP" --metadata "$META"

if gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1; then echo "Existing release" >&2; exit 1; fi
if gh api "repos/$REPO/git/ref/tags/$TAG" >/dev/null 2>&1; then echo "Existing tag" >&2; exit 1; fi

cat > notes.md <<'EOF'
Production hotfix для оставшегося Mob Control command-spam path.

Исправления:
- ручной gui_toggle по-прежнему использует SGP serverbound payload;
- отложенный gui_sync после отпускания мыши/ресинка больше не отправляется через vanilla sendCommand;
- gui_sync теперь запрашивается отдельным SGP serverbound payload;
- на сервере вызывается штатный CommandBridge.guiSync(player, level, x, z), поэтому сохраняются permission checks, 16x16 sync semantics и существующий клиентский parser ответа;
- auto-protect после FTB claim сохранён;
- глобальные vanilla anti-spam лимиты не меняются;
- protected_chunks.properties не распространяется и не перезаписывается.

Обновление рассчитано на stable 2.0.6.

Отдельного тестового сервера нет. Релиз выполнен по явному разрешению владельца; финальный runtime PASS остаётся PENDING до проверки на рабочем сервере.
EOF

python3 scripts/client-release-guard.py --tag "$TAG" --channel stable --zip "$ZIP" --metadata "$META" --publish --notes notes.md

REL="$(gh api "repos/$REPO/releases/tags/$TAG")"
test "$(printf '%s' "$REL"|jq -r '.draft')" = false
test "$(printf '%s' "$REL"|jq -r '.prerelease')" = false
RID="$(printf '%s' "$REL"|jq -r '.id')"
ASSETS="$(gh api "repos/$REPO/releases/$RID/assets")"
test "$(printf '%s' "$ASSETS"|jq 'length')" = 2
rm -rf live207 && mkdir live207
gh release download "$TAG" --repo "$REPO" --dir live207
cmp "$ZIP" "live207/$ZIP"; cmp "$META" "live207/$META"
python3 scripts/client-release-guard.py --tag "$TAG" --channel stable --zip "live207/$ZIP" --metadata "live207/$META"

python3 - <<'PY'
import hashlib,json,zipfile,pathlib
p="live207/SGP_ClientPatch_2.0.7.zip"
sha=pathlib.Path("sgp207_addon_sha.txt").read_text().split()[0]
size=int(pathlib.Path("sgp207_addon_size.txt").read_text().strip())
with zipfile.ZipFile(p) as z:
    x=json.loads(z.read("patch.json"))
    assert x["fromVersions"]==["2.0.6"] and x["toVersion"]=="2.0.7"
    assert [a["type"] for a in x["actions"]]==["delete","copy"]
    a=x["actions"][1]; data=z.read(a["source"])
    assert hashlib.sha256(data).hexdigest()==sha and len(data)==size
print("LIVE_CLIENT_207_VERIFY_PASS")
PY

AID="$(printf '%s' "$ASSETS"|jq -r --arg n "$ZIP" '.[]|select(.name==$n)|.id')"
MID="$(printf '%s' "$ASSETS"|jq -r --arg n "$META" '.[]|select(.name==$n)|.id')"
{
 echo CLIENT_207_RELEASE_VERIFY_PASS
 echo PUBLISHED_RELEASE_ID=$RID
 echo PUBLISHED_ASSET_ID=$AID
 echo PUBLISHED_META_ASSET_ID=$MID
 echo PUBLISHED_SHA=$(cat client207_sha.txt)
 echo PUBLISHED_SIZE=$(cat client207_size.txt)
 echo META_SHA=$(cat client207_meta_sha.txt)
 echo META_SIZE=$(cat client207_meta_size.txt)
 echo ADDON_RUN=$RUN
 echo ADDON_SHA=$(awk '{print $1}' sgp207_addon_sha.txt)
 echo ADDON_SIZE=$(cat sgp207_addon_size.txt)
 echo SOURCE_COMMIT=$GITHUB_SHA
} | tee release-client-207-result.txt
