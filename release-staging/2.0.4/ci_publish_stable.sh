#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
TAG="client-v2.0.4"
ZIP="SGP_ClientPatch_2.0.4.zip"
META="SGP_ClientPatch_2.0.4.meta.json"
TEST_TAG="client-v2.0.4-test.2"
TEST_ZIP="SGP_ClientPatch_2.0.4-test.2.zip"

python3 release-staging/2.0.4/build_client_204.py | tee build-client-204.txt

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
Стабильное обновление механики Mob Control для FTB Chunks.

Изменения:
- новый FTB Chunks claim автоматически включает Mob Control для этого чанка;
- дополнительный middle-click после создания claim больше не требуется;
- средняя кнопка мыши по-прежнему вручную включает/выключает Mob Control на уже claimed чанках;
- ручное отключение сохраняется: автоматическое включение снова происходит только при новом claim/re-claim;
- FTB Chunks Mobs Spawn Control 1.0.4 используется без модификации стороннего JAR;
- добавлен SGP compatibility addon 1.0.0, который реагирует только на успешный AFTER_CLAIM и использует штатное хранилище Spawn Guard;
- Mob Control настроен на блокировку только natural hostile spawn;
- spawner, patrol, raid, structure, spawn egg, command, breeding, bucket и dispenser пути остаются разрешены настройками;
- лимиты claims: 1000 на игрока, SUM для команды, hard cap 5000;
- force-load для обычных игроков остаётся отключён (0);
- protected_chunks.properties в патч не входит и остаётся живым состоянием выбранных чанков.

Обновление поддерживается с stable 2.0.3, а также как forward repair с 2.0.4-test.1 и 2.0.4-test.2.
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

rm -rf live-client-204 && mkdir live-client-204
gh release download "$TAG" --repo "$REPO" --dir live-client-204
cmp "$ZIP" "live-client-204/$ZIP"
cmp "$META" "live-client-204/$META"

python3 scripts/client-release-guard.py \
  --tag "$TAG" --channel stable --zip "live-client-204/$ZIP" --metadata "live-client-204/$META"

python3 - <<'PY'
import hashlib, json, pathlib, zipfile

def sha(data):
    return hashlib.sha256(data).hexdigest()

expected = {
    "files/mods/ftb_chunks_mobs_spawn_control-1.0.4-neoforge-1.21.1.jar":
        ("c7df7bdd469237418ce4ef892497793addba84f9c92125b0fde05f8b6e353960", 50538),
    "files/mods/SGP-FTB-Spawn-Guard-Auto-Protect-1.0.0.jar":
        ("abf4a0418a8d991d460d389264792d1c92c65baf01c009da4a46ef5f95fc5674", 5622),
    "files/config/ftbchunks-world.snbt":
        ("7464ff26796dd1144135513789b32e2bf778baeea39f7019d77fda3a05cd7d75", 9106),
    "files/config/ftb_chunks_mobs_spawn_control-common.toml":
        ("4d82c90d99c8c14883c441c28ea36483a48d53fe1e42ab999bf02cb6052b10c3", 598),
}
with zipfile.ZipFile("live-client-204/SGP_ClientPatch_2.0.4.zip") as z:
    assert z.testzip() is None
    p = json.loads(z.read("patch.json"))
    assert p["fromVersions"] == ["2.0.3", "2.0.4-test.1", "2.0.4-test.2"]
    assert p["toVersion"] == "2.0.4"
    assert [a["type"] for a in p["actions"]] == ["copy", "copy", "copy", "copy"]
    assert not any("protected_chunks.properties" in n for n in z.namelist())
    for name, (digest, size) in expected.items():
        data = z.read(name)
        assert len(data) == size
        assert sha(data) == digest

test_path = pathlib.Path(".stable-204-source/SGP_ClientPatch_2.0.4-test.2.zip")
with zipfile.ZipFile(test_path) as tz, zipfile.ZipFile("live-client-204/SGP_ClientPatch_2.0.4.zip") as sz:
    for name in expected:
        assert tz.read(name) == sz.read(name), name

print("LIVE_CLIENT_204_VERIFY_PASS")
print("STABLE_PAYLOAD_BYTE_IDENTICAL_TO_TEST2_PASS")
PY

AID="$(printf '%s' "$ASSETS" | jq -r --arg n "$ZIP" '.[]|select(.name==$n)|.id')"
MID="$(printf '%s' "$ASSETS" | jq -r --arg n "$META" '.[]|select(.name==$n)|.id')"

{
  echo "CLIENT_204_RELEASE_VERIFY_PASS"
  echo "PUBLISHED_RELEASE_ID=$RID"
  echo "PUBLISHED_ASSET_ID=$AID"
  echo "PUBLISHED_META_ASSET_ID=$MID"
  echo "PUBLISHED_SHA=$(cat client204_sha.txt)"
  echo "PUBLISHED_SIZE=$(cat client204_size.txt)"
  echo "META_SHA=$(cat client204_meta_sha.txt)"
  echo "META_SIZE=$(cat client204_meta_size.txt)"
  echo "SOURCE_TEST=$TEST_TAG"
  echo "SOURCE_COMMIT=$GITHUB_SHA"
} | tee release-client-204-result.txt
