#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
TAG="client-v2.0.5"
ZIP="SGP_ClientPatch_2.0.5.zip"
META="SGP_ClientPatch_2.0.5.meta.json"
ADDON_RUN="40718384725"
ADDON_ARTIFACT="sgp-ftb-auto-protect-1.0.1"
ADDON_JAR="SGP-FTB-Spawn-Guard-Auto-Protect-1.0.1.jar"

rm -rf .addon205
mkdir .addon205
gh run download "$ADDON_RUN" --repo "$REPO" --name "$ADDON_ARTIFACT" --dir .addon205
cp ".addon205/$ADDON_JAR" "$ADDON_JAR"
cp ".addon205/sgp205_addon_sha.txt" sgp205_addon_sha.txt
cp ".addon205/sgp205_addon_size.txt" sgp205_addon_size.txt

test "$(sha256sum "$ADDON_JAR" | awk '{print $1}')" = "206c05efb483a1ac88e76e7406fbb22a7fe7bb142699bb9fc17934fc2e646bef"
test "$(stat -c '%s' "$ADDON_JAR")" = "12587"
test "$(awk '{print $1}' sgp205_addon_sha.txt)" = "206c05efb483a1ac88e76e7406fbb22a7fe7bb142699bb9fc17934fc2e646bef"
test "$(cat sgp205_addon_size.txt)" = "12587"

python3 release-staging/2.0.5/build_client_205.py | tee build-client-205.txt

python3 scripts/client-release-guard.py \
  --tag "$TAG" --channel stable --zip "$ZIP" --metadata "$META"

if gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1; then
  echo "Unexpected existing release $TAG" >&2
  exit 1
fi
if gh api "repos/$REPO/git/ref/tags/$TAG" >/dev/null 2>&1; then
  echo "Unexpected existing tag $TAG" >&2
  exit 1
fi

cat > notes.md <<'EOF'
Production hotfix для FTB Chunks / Mob Control.

Исправления:
- auto-protect на dedicated server больше не делает повторный lookup claim через FTB manager внутри AFTER_CLAIM; context строится прямо из уже успешно созданного claim;
- одиночный middle-click Mob Control больше не отправляет ftbmsc chunk ... gui_toggle как vanilla command packet;
- вместо command-spam path используется собственный SGP serverbound payload;
- на сервере переключение передаётся в штатный Spawn Guard executeClaim(..., gui_toggle), поэтому сохраняются его permission checks и toggle semantics;
- сторонний FTB Chunks Mobs Spawn Control 1.0.4 остаётся без модификации JAR;
- protected_chunks.properties не распространяется и не перезаписывается.

Обновление заменяет SGP-FTB-Spawn-Guard-Auto-Protect-1.0.0.jar на 1.0.1 и поддерживается с stable 2.0.4.

Владелец явно разрешил этот production hotfix без отдельного тестового сервера. Dedicated runtime verification выполняется на рабочем сервере после установки server 2.0.5; это не считается предварительным runtime PASS.
EOF

python3 scripts/client-release-guard.py \
  --tag "$TAG" --channel stable --zip "$ZIP" --metadata "$META" \
  --publish --notes notes.md

REL="$(gh api "repos/$REPO/releases/tags/$TAG")"
test "$(printf '%s' "$REL" | jq -r '.draft')" = false
test "$(printf '%s' "$REL" | jq -r '.prerelease')" = false
RID="$(printf '%s' "$REL" | jq -r '.id')"
ASSETS="$(gh api "repos/$REPO/releases/$RID/assets")"
test "$(printf '%s' "$ASSETS" | jq 'length')" = 2

rm -rf live-client-205 && mkdir live-client-205
gh release download "$TAG" --repo "$REPO" --dir live-client-205
cmp "$ZIP" "live-client-205/$ZIP"
cmp "$META" "live-client-205/$META"

python3 scripts/client-release-guard.py \
  --tag "$TAG" --channel stable --zip "live-client-205/$ZIP" --metadata "live-client-205/$META"

python3 - <<'PY'
import hashlib, json, zipfile
path="live-client-205/SGP_ClientPatch_2.0.5.zip"
with zipfile.ZipFile(path) as z:
    assert z.testzip() is None
    p=json.loads(z.read("patch.json"))
    assert p["fromVersions"] == ["2.0.4"]
    assert p["toVersion"] == "2.0.5"
    assert [a["type"] for a in p["actions"]] == ["delete","copy"]
    assert p["actions"][0]["target"] == "mods/SGP-FTB-Spawn-Guard-Auto-Protect-1.0.0.jar"
    assert p["actions"][0]["optional"] is False
    a=p["actions"][1]
    assert a["target"] == "mods/SGP-FTB-Spawn-Guard-Auto-Protect-1.0.1.jar"
    data=z.read(a["source"])
    assert len(data)==12587
    assert hashlib.sha256(data).hexdigest()=="206c05efb483a1ac88e76e7406fbb22a7fe7bb142699bb9fc17934fc2e646bef"
    assert a["sha256"]==hashlib.sha256(data).hexdigest() and a["size"]==len(data)
    assert not any("protected_chunks.properties" in n for n in z.namelist())
print("LIVE_CLIENT_205_VERIFY_PASS")
PY

AID="$(printf '%s' "$ASSETS" | jq -r --arg n "$ZIP" '.[]|select(.name==$n)|.id')"
MID="$(printf '%s' "$ASSETS" | jq -r --arg n "$META" '.[]|select(.name==$n)|.id')"

{
  echo "CLIENT_205_RELEASE_VERIFY_PASS"
  echo "PUBLISHED_RELEASE_ID=$RID"
  echo "PUBLISHED_ASSET_ID=$AID"
  echo "PUBLISHED_META_ASSET_ID=$MID"
  echo "PUBLISHED_SHA=$(cat client205_sha.txt)"
  echo "PUBLISHED_SIZE=$(cat client205_size.txt)"
  echo "META_SHA=$(cat client205_meta_sha.txt)"
  echo "META_SIZE=$(cat client205_meta_size.txt)"
  echo "ADDON_BUILD_RUN=$ADDON_RUN"
  echo "ADDON_ARTIFACT_ID=12829052640"
  echo "ADDON_SHA=206c05efb483a1ac88e76e7406fbb22a7fe7bb142699bb9fc17934fc2e646bef"
  echo "ADDON_SIZE=12587"
  echo "SOURCE_COMMIT=$GITHUB_SHA"
} | tee release-client-205-result.txt
