#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
TAG="client-v2.0.11-test.1"
ZIP="SGP_ClientPatch_2.0.11-test.1.zip"
META="SGP_ClientPatch_2.0.11-test.1.meta.json"
ADDON="SGP-Wands-Paxel-Compat-1.0.1.jar"

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

Runtime TEST выполняется на клиенте в одиночке/integrated server. Dedicated-server patch во время client TEST не строится и не передаётся.
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

AID="$(printf '%s' "$ASSETS" | jq -r --arg n "$ZIP" '.[]|select(.name==$n)|.id')"
MID="$(printf '%s' "$ASSETS" | jq -r --arg n "$META" '.[]|select(.name==$n)|.id')"
ZIP_SHA="$(sha256sum "$ZIP" | awk '{print $1}')"
META_SHA="$(sha256sum "$META" | awk '{print $1}')"
ADDON_SHA="$(sha256sum "$ADDON" | awk '{print $1}')"

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
  echo "SOURCE_COMMIT=$GITHUB_SHA"
} | tee release-client-2011-test1-result.txt
