#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
TAG="client-v2.0.11-test.2"
OLD_TAG="client-v2.0.11-test.1"
ZIP="SGP_ClientPatch_2.0.11-test.2.zip"
META="SGP_ClientPatch_2.0.11-test.2.meta.json"
ADDON="SGP-Wands-Paxel-Compat-1.0.2.jar"

bash release-staging/2.0.11-test.2/ci_build_compat.sh
python3 release-staging/2.0.11-test.2/build_client_2011_test2.py | tee build-client-2011-test2.txt

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
Исправляющий TEST-кандидат для Minecraft 1.21.1 / NeoForge от stable 2.0.10 и failed 2.0.11-test.1.

Почему test.2:
- 2.0.11-test.1 не запускался: SGP Wands Paxel Compat 1.0.1 содержал mixin в package net.nicguzzo.wands.wand.
- Java module resolver получил split-package между модулем sgp_wands_paxel_compat и Building Wands и остановил запуск до Minecraft.

Исправление:
- SGP Wands Paxel Compat 1.0.1 → 1.0.2.
- Все классы SGP compat теперь находятся только в sgp.wandspaxel.*.
- Добавлен статический regression guard: JAR не может содержать net/nicguzzo/wands/**.
- Доступ к выбранным инструментам идёт через player/player_data и @Shadow, без упаковки классов в namespace Building Wands.

Функциональный scope прежний:
- все восемь Create: Ironworks paxel;
- Replace/Destroy, включая vanilla glass;
- axe/shovel Use: path, log strip, copper scrape/wax-off;
- без hoe/shears расширения;
- реальный tier/drop/Silk Touch;
- защита при остатке прочности ≤5.

Quartz Glass TEST также прежний:
- Sodium quad_splitting_mode = UNLIMITED;
- BetterNether texture/RGB/alpha не меняются.

Runtime TEST проводится только на клиенте в одиночке/integrated server. Никакого server TEST/candidate не создаётся.
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
zpath="live-client/SGP_ClientPatch_2.0.11-test.2.zip"
with zipfile.ZipFile(zpath) as z:
    assert z.testzip() is None
    assert sorted(z.namelist()) == sorted([
        "README.txt",
        "patch.json",
        "files/mods/SGP-Wands-Paxel-Compat-1.0.2.jar",
    ])
    p=json.loads(z.read("patch.json"))
    assert p["fromVersions"]==["2.0.10","2.0.11-test.1"]
    assert p["toVersion"]=="2.0.11-test.2"
    assert [a["type"] for a in p["actions"]]==["delete","delete","copy","jsonEdit"]
    assert p["actions"][0]["target"]=="mods/SGP-Wands-Paxel-Compat-1.0.0.jar"
    assert p["actions"][1]["target"]=="mods/SGP-Wands-Paxel-Compat-1.0.1.jar"
    assert p["actions"][2]["target"]=="mods/SGP-Wands-Paxel-Compat-1.0.2.jar"
    e=p["actions"][3]
    assert e["target"]=="config/sodium-options.json"
    assert e["edits"]==[{
        "op":"set",
        "path":"/performance/quad_splitting_mode",
        "value":"UNLIMITED",
        "createIfMissing":False,
    }]
    assert not any("betternether" in n.lower() for n in z.namelist())
    jar=z.read("files/mods/SGP-Wands-Paxel-Compat-1.0.2.jar")
    assert hashlib.sha256(jar).hexdigest()==p["actions"][2]["sha256"]
    assert len(jar)==p["actions"][2]["size"]
    with zipfile.ZipFile(__import__('io').BytesIO(jar)) as j:
        assert not any(n.startswith('net/nicguzzo/wands/') for n in j.namelist())
        assert 'sgp/wandspaxel/mixin/SgpWandsPaxelCompatMixin.class' in j.namelist()
print("LIVE_CLIENT_2011_TEST2_EXACT_VERIFY_PASS")
PY

# Retire failed test.1 only after test.2 is public and exact-byte verified.
if gh api "repos/$REPO/releases/tags/$OLD_TAG" >/dev/null 2>&1; then
  gh release delete "$OLD_TAG" --repo "$REPO" --cleanup-tag --yes
fi
if gh api "repos/$REPO/git/ref/tags/$OLD_TAG" >/dev/null 2>&1; then
  gh api -X DELETE "repos/$REPO/git/refs/tags/$OLD_TAG"
fi
! gh api "repos/$REPO/releases/tags/$OLD_TAG" >/dev/null 2>&1
! gh api "repos/$REPO/git/ref/tags/$OLD_TAG" >/dev/null 2>&1

AID="$(printf '%s' "$ASSETS" | jq -r --arg n "$ZIP" '.[]|select(.name==$n)|.id')"
MID="$(printf '%s' "$ASSETS" | jq -r --arg n "$META" '.[]|select(.name==$n)|.id')"
ZIP_SHA="$(sha256sum "$ZIP" | awk '{print $1}')"
META_SHA="$(sha256sum "$META" | awk '{print $1}')"
ADDON_SHA="$(sha256sum "$ADDON" | awk '{print $1}')"

{
  echo "CLIENT_2011_TEST2_RELEASE_VERIFY_PASS"
  echo "PUBLISHED_RELEASE_ID=$RID"
  echo "PUBLISHED_ASSET_ID=$AID"
  echo "PUBLISHED_META_ASSET_ID=$MID"
  echo "PUBLISHED_SHA=$ZIP_SHA"
  echo "PUBLISHED_SIZE=$(stat -c '%s' "$ZIP")"
  echo "META_SHA=$META_SHA"
  echo "META_SIZE=$(stat -c '%s' "$META")"
  echo "PAXEL_COMPAT_SHA=$ADDON_SHA"
  echo "PAXEL_COMPAT_SIZE=$(stat -c '%s' "$ADDON")"
  echo "FAILED_TEST1_RETIRED=PASS"
  echo "SOURCE_COMMIT=$GITHUB_SHA"
} | tee release-client-2011-test2-result.txt
