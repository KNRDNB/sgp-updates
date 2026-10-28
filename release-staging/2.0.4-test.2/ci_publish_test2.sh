#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
TAG="client-v2.0.4-test.2"
ZIP="SGP_ClientPatch_2.0.4-test.2.zip"
META="SGP_ClientPatch_2.0.4-test.2.meta.json"
OLD_TEST="client-v2.0.4-test.1"
ADDON="SGP-FTB-Spawn-Guard-Auto-Protect-1.0.0.jar"

bash release-staging/2.0.4-test.2/ci_build_auto_protect.sh
python3 release-staging/2.0.4-test.2/build_client_204_test2.py | tee build-client-204-test2.txt

python3 scripts/client-release-guard.py \
  --tag "$TAG" --channel test --zip "$ZIP" --metadata "$META"

if gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1; then
  echo "Unexpected existing release $TAG" >&2
  exit 1
fi
if gh api "repos/$REPO/git/ref/tags/$TAG" >/dev/null 2>&1; then
  echo "Unexpected existing tag $TAG" >&2
  exit 1
fi

cat > notes.md <<'EOF'
## SGP Client 2.0.4-test.2

TEST-кандидат для Minecraft 1.21.1 / NeoForge.

Изменения:
- новый FTB Chunks claim автоматически включает Mob Control для этого чанка;
- дополнительный клик средней кнопкой после создания claim больше не требуется;
- средняя кнопка мыши по-прежнему вручную включает/выключает Mob Control на уже claimed чанках;
- ручное отключение не переопределяется автоматически: защита снова включится по умолчанию только при новом claim/re-claim;
- добавлен небольшой SGP compatibility addon, который слушает успешный AFTER_CLAIM и использует штатное хранилище FTB Chunks Mobs Spawn Control;
- сторонний JAR Spawn Guard 1.0.4 не модифицируется;
- миграции существующих claims нет: по подтверждению владельца на live-сервере FTB Chunks claims сейчас отсутствуют;
- Mob Control по-прежнему блокирует только естественный спаун враждебных мобов;
- спаунеры, рейды, патрули, структурный спаун, яйца призыва, команды, размножение, ведра и раздатчики остаются разрешены;
- лимиты claims остаются 1000 на игрока, SUM для команды, hard cap 5000;
- force-load для обычных игроков остаётся отключён (0).

Обновление поддерживается как с stable 2.0.3, так и с 2.0.4-test.1.

Файл protected_chunks.properties в патч не входит: это живое состояние выбранных чанков.

Формальный dedicated-server patch во время TEST не создаётся.
EOF

python3 scripts/client-release-guard.py \
  --tag "$TAG" --channel test --zip "$ZIP" --metadata "$META" \
  --publish --notes notes.md

REL="$(gh api "repos/$REPO/releases/tags/$TAG")"
test "$(printf '%s' "$REL" | jq -r '.draft')" = false
test "$(printf '%s' "$REL" | jq -r '.prerelease')" = true
RID="$(printf '%s' "$REL" | jq -r '.id')"
ASSETS="$(gh api "repos/$REPO/releases/$RID/assets")"
test "$(printf '%s' "$ASSETS" | jq 'length')" = 2

rm -rf live-client && mkdir live-client
gh release download "$TAG" --repo "$REPO" --dir live-client
test -f "live-client/$ZIP"
test -f "live-client/$META"
cmp "$ZIP" "live-client/$ZIP"
cmp "$META" "live-client/$META"

python3 scripts/client-release-guard.py \
  --tag "$TAG" --channel test --zip "live-client/$ZIP" --metadata "live-client/$META"

python3 - <<'PY'
import hashlib, io, json, zipfile

def sha(data):
    return hashlib.sha256(data).hexdigest()

with zipfile.ZipFile("live-client/SGP_ClientPatch_2.0.4-test.2.zip") as z:
    assert z.testzip() is None
    expected = sorted([
        "README.txt",
        "patch.json",
        "files/mods/ftb_chunks_mobs_spawn_control-1.0.4-neoforge-1.21.1.jar",
        "files/mods/SGP-FTB-Spawn-Guard-Auto-Protect-1.0.0.jar",
        "files/config/ftbchunks-world.snbt",
        "files/config/ftb_chunks_mobs_spawn_control-common.toml",
    ])
    assert sorted(z.namelist()) == expected
    assert not any("protected_chunks.properties" in n for n in z.namelist())

    p = json.loads(z.read("patch.json"))
    assert p["fromVersions"] == ["2.0.3", "2.0.4-test.1"]
    assert p["toVersion"] == "2.0.4-test.2"
    assert [a["type"] for a in p["actions"]] == ["copy", "copy", "copy", "copy"]

    spawn = z.read("files/mods/ftb_chunks_mobs_spawn_control-1.0.4-neoforge-1.21.1.jar")
    assert len(spawn) == 50538
    assert sha(spawn) == "c7df7bdd469237418ce4ef892497793addba84f9c92125b0fde05f8b6e353960"

    addon = z.read("files/mods/SGP-FTB-Spawn-Guard-Auto-Protect-1.0.0.jar")
    with zipfile.ZipFile(io.BytesIO(addon)) as az:
        assert az.testzip() is None
        names = set(az.namelist())
        assert "sgp/ftbspawnguard/AutoProtectHook.class" in names
        assert "sgp/ftbspawnguard/SgpFtbSpawnGuardAutoProtect.class" in names
        assert not any(n.startswith("dev/ftb/") for n in names)
        assert not any(n.startswith("org/ftb_chunks_mobs_spawn_control/") for n in names)
        toml = az.read("META-INF/neoforge.mods.toml").decode()
        assert 'modId="sgp_ftb_spawn_guard_auto_protect"' in toml
        assert 'version="1.0.0"' in toml

    ftb = z.read("files/config/ftbchunks-world.snbt").decode()
    assert "max_claimed_chunks: 1000" in ftb
    assert 'party_limit_mode: "sum"' in ftb
    assert "hard_team_claim_limit: 5000" in ftb
    assert "max_force_loaded_chunks: 0" in ftb
    assert "disable_protection: true" in ftb

    cfg = z.read("files/config/ftb_chunks_mobs_spawn_control-common.toml").decode()
    for line in [
        'filterMode = "HOSTILE_ONLY"',
        "blockNatural = true",
        "blockSpawner = false",
        "blockPatrol = false",
        "blockRaid = false",
        "blockStructure = false",
        "allowSpawnEgg = true",
        "allowCommand = true",
        "allowBreeding = true",
        "allowBucket = true",
        "allowDispenser = true",
        "allowNamedMobs = false",
        "allowPersistentMobs = false",
        "strictJoinFallback = false",
    ]:
        assert line in cfg, line

print("LIVE_CLIENT_204_TEST2_VERIFY_PASS")
PY

# Single-current-TEST lifecycle: retire test.1 only after test.2 is public
# and its exact asset pair has passed live-public verification.
if gh api "repos/$REPO/releases/tags/$OLD_TEST" >/dev/null 2>&1; then
  gh release delete "$OLD_TEST" --repo "$REPO" --cleanup-tag -y
fi

AID="$(printf '%s' "$ASSETS" | jq -r --arg n "$ZIP" '.[]|select(.name==$n)|.id')"
MID="$(printf '%s' "$ASSETS" | jq -r --arg n "$META" '.[]|select(.name==$n)|.id')"

{
  echo "CLIENT_204_TEST2_RELEASE_VERIFY_PASS"
  echo "PUBLISHED_RELEASE_ID=$RID"
  echo "PUBLISHED_ASSET_ID=$AID"
  echo "PUBLISHED_META_ASSET_ID=$MID"
  echo "PUBLISHED_SHA=$(cat client204_test2_sha.txt)"
  echo "PUBLISHED_SIZE=$(cat client204_test2_size.txt)"
  echo "META_SHA=$(cat client204_test2_meta_sha.txt)"
  echo "META_SIZE=$(cat client204_test2_meta_size.txt)"
  echo "AUTO_PROTECT_SHA=$(cat auto_protect_exact_sha.txt)"
  echo "AUTO_PROTECT_SIZE=$(cat auto_protect_exact_size.txt)"
  echo "SOURCE_COMMIT=$GITHUB_SHA"
  echo "OLD_TEST_RETIRED=$OLD_TEST"
} | tee release-client-204-test2-result.txt
