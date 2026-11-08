#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
TAG="client-v2.0.11-test.1"
ZIP="SGP_ClientPatch_2.0.11-test.1.zip"
META="SGP_ClientPatch_2.0.11-test.1.meta.json"
ADDON="SGP-Wands-Paxel-Compat-1.0.1.jar"
SERVER_TEST="SGP_Server_TEST_2.1.0_WandsPaxelCompat_1.0.1.zip"

bash release-staging/2.0.11-test.1/ci_build_compat.sh
python3 release-staging/2.0.11-test.1/build_client_2011_test1.py | tee build-client-2011-test1.txt

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
TEST-кандидат для Minecraft 1.21.1 / NeoForge от stable 2.0.10.

Изменения:
- SGP Wands Paxel Compat 1.0.0 → 1.0.1.
- Исправлен Building Wands Replace по ванильному стеклу с Create: Ironworks paxel.
- Compat охватывает все восемь paxel: copper, bronze, brass, iron, gold, diamond, steel, netherite.
- Для paxel добавлена недостающая семантика axe/shovel в Building Wands Use-mode: strip, path, copper scrape/wax-off через реальный useOn самого paxel.
- Hoe/shears возможности намеренно не добавляются.
- Сохраняются реальный Tool tier/drop/Silk Touch и защита Building Wands от использования инструмента с остатком ≤5 durability.
- Sodium quad_splitting_mode точечно меняется SAFE → UNLIMITED для проверки прозрачной сортировки BetterNether Quartz Glass + water.
- BetterNether texture/RGB/alpha не меняются и не входят в патч.

Обязательный runtime TEST:
- paxel Replace: vanilla glass, stone/ore, wood, shovel-domain block;
- paxel Use: path, log strip, copper scrape/wax-off;
- negative: hoe/tilling и shear-only действия должны остаться недоступными;
- durability ≤5 должна блокировать использование;
- BetterNether Quartz Glass: обычное + чёрное + framed/pane с водой за стеклом, shaders OFF и Complementary ON;
- проверить FPS/стабильность перестроения чанков с Sodium UNLIMITED.

Для multiplayer paxel-fix нужен тот же compat 1.0.1 на dedicated server. Formal server release во время client TEST не публикуется.
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
cmp "$ZIP" "live-client/$ZIP"
cmp "$META" "live-client/$META"
python3 scripts/client-release-guard.py \
  --tag "$TAG" --channel test --zip "live-client/$ZIP" --metadata "live-client/$META"

python3 - <<'PY'
import hashlib, json, zipfile
zpath="live-client/SGP_ClientPatch_2.0.11-test.1.zip"
with zipfile.ZipFile(zpath) as z:
    assert z.testzip() is None
    assert sorted(z.namelist()) == sorted([
        "README.txt",
        "patch.json",
        "files/mods/SGP-Wands-Paxel-Compat-1.0.1.jar",
    ])
    p=json.loads(z.read("patch.json"))
    assert p["fromVersions"]==["2.0.10"]
    assert p["toVersion"]=="2.0.11-test.1"
    assert [a["type"] for a in p["actions"]]==["delete","copy","jsonEdit"]
    assert p["actions"][0]["target"]=="mods/SGP-Wands-Paxel-Compat-1.0.0.jar"
    assert p["actions"][1]["target"]=="mods/SGP-Wands-Paxel-Compat-1.0.1.jar"
    e=p["actions"][2]
    assert e["target"]=="config/sodium-options.json"
    assert e["edits"]==[{
        "op":"set",
        "path":"/performance/quad_splitting_mode",
        "value":"UNLIMITED",
        "createIfMissing":False,
    }]
    assert not any("betternether" in n.lower() for n in z.namelist())
    jar=z.read("files/mods/SGP-Wands-Paxel-Compat-1.0.1.jar")
    assert hashlib.sha256(jar).hexdigest()==p["actions"][1]["sha256"]
    assert len(jar)==p["actions"][1]["size"]
print("LIVE_CLIENT_2011_TEST1_EXACT_VERIFY_PASS")
PY

python3 - <<'PY'
from pathlib import Path
import zipfile
jar=Path("SGP-Wands-Paxel-Compat-1.0.1.jar").read_bytes()
readme="""SGP Server manual TEST handoff for client 2.0.11-test.1

This is NOT a server release and does NOT change .sgp/server version.

With the server STOPPED:
1. Remove mods/SGP-Wands-Paxel-Compat-1.0.0.jar
2. Copy mods/SGP-Wands-Paxel-Compat-1.0.1.jar from this archive
3. Start server and run the owner runtime matrix.
4. Do not treat this server state as accepted-good until explicit owner PASS.

No other server file is changed.
""".encode()
fixed=(2026,11,8,12,0,0)
with zipfile.ZipFile("SGP_Server_TEST_2.1.0_WandsPaxelCompat_1.0.1.zip","w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in [
        ("mods/SGP-Wands-Paxel-Compat-1.0.1.jar",jar),
        ("SERVER_TEST_README.txt",readme),
    ]:
        zi=zipfile.ZipInfo(name,fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=0o644<<16
        z.writestr(zi,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
with zipfile.ZipFile("SGP_Server_TEST_2.1.0_WandsPaxelCompat_1.0.1.zip") as z:
    assert z.testzip() is None
    assert sorted(z.namelist())==[
        "SERVER_TEST_README.txt",
        "mods/SGP-Wands-Paxel-Compat-1.0.1.jar",
    ]
print("SERVER_MANUAL_TEST_HANDOFF_PASS")
PY

AID="$(printf '%s' "$ASSETS" | jq -r --arg n "$ZIP" '.[]|select(.name==$n)|.id')"
MID="$(printf '%s' "$ASSETS" | jq -r --arg n "$META" '.[]|select(.name==$n)|.id')"
ZIP_SHA="$(sha256sum "$ZIP" | awk '{print $1}')"
META_SHA="$(sha256sum "$META" | awk '{print $1}')"
ADDON_SHA="$(sha256sum "$ADDON" | awk '{print $1}')"
SERVER_TEST_SHA="$(sha256sum "$SERVER_TEST" | awk '{print $1}')"

{
  echo "CLIENT_2011_TEST1_RELEASE_VERIFY_PASS"
  echo "PUBLISHED_RELEASE_ID=$RID"
  echo "PUBLISHED_ASSET_ID=$AID"
  echo "PUBLISHED_META_ASSET_ID=$MID"
  echo "PUBLISHED_SHA=$ZIP_SHA"
  echo "PUBLISHED_SIZE=$(stat -c '%s' "$ZIP")"
  echo "META_SHA=$META_SHA"
  echo "META_SIZE=$(stat -c '%s' "$META")"
  echo "PAXEL_COMPAT_SHA=$ADDON_SHA"
  echo "PAXEL_COMPAT_SIZE=$(stat -c '%s' "$ADDON")"
  echo "SERVER_TEST_SHA=$SERVER_TEST_SHA"
  echo "SERVER_TEST_SIZE=$(stat -c '%s' "$SERVER_TEST")"
  echo "SOURCE_COMMIT=$GITHUB_SHA"
} | tee release-client-2011-test1-result.txt
