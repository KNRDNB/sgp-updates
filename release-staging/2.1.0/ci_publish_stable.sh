#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
TEST_TAG="client-v2.1.0-test.1"
STABLE_TAG="client-v2.1.0"
TEST_ZIP="SGP_ClientPatch_2.1.0-test.1.zip"
TEST_META="SGP_ClientPatch_2.1.0-test.1.meta.json"
ZIP="SGP_ClientPatch_2.1.0.zip"
META="SGP_ClientPatch_2.1.0.meta.json"
TEST_SHA="08215fd8d3716e0c744a36f9fe4467d0f50bda87b7d49a8f8b93283359491a98"
TEST_META_SHA="0727019f32c15e1ab924c9649bd7ab6a948c2e654a85562fd6f3d6cb0681be77"
PAXEL_SHA="52a8993070fd3bab43660d3f26df87d9cdcdda2e2711a01504a4d981ff034692"
GLASS_SHA="60ce0f3a584b22f63c1b956629c49eac4b7d2514f6bd0ac1ba639f426661d5a7"

# Fail closed if stable version already exists: never overwrite any public asset.
if gh api "repos/$REPO/releases/tags/$STABLE_TAG" >/dev/null 2>&1; then
  echo "Stable release already exists, immutable: $STABLE_TAG" >&2; exit 1
fi
if gh api "repos/$REPO/git/ref/tags/$STABLE_TAG" >/dev/null 2>&1; then
  echo "Stable tag already exists, immutable: $STABLE_TAG" >&2; exit 1
fi

# The exact TEST bundle, not a source rebuild, is the mandatory basis.
TEST_RELEASE="$(gh api "repos/$REPO/releases/tags/$TEST_TAG")"
test "$(printf '%s' "$TEST_RELEASE" | jq -r '.draft')" = false
test "$(printf '%s' "$TEST_RELEASE" | jq -r '.prerelease')" = true
test "$(printf '%s' "$TEST_RELEASE" | jq '.assets|length')" -eq 2
test "$(printf '%s' "$TEST_RELEASE" | jq -r '.assets[].name' | sort)" = \
  "$(printf '%s\n%s\n' "$TEST_ZIP" "$TEST_META" | sort)"

mkdir -p test-proof
gh release download "$TEST_TAG" --repo "$REPO" --dir test-proof
test "$(sha256sum "test-proof/$TEST_ZIP" | awk '{print $1}')" = "$TEST_SHA"
test "$(sha256sum "test-proof/$TEST_META" | awk '{print $1}')" = "$TEST_META_SHA"
python3 scripts/client-release-guard.py \
    --tag "$TEST_TAG" --channel test \
    --zip "test-proof/$TEST_ZIP" --metadata "test-proof/$TEST_META"

python3 release-staging/2.1.0/build_stable_from_test1.py | tee client210-stable-build.log

# Verify version metadata, package integrity and unchanged TEST action set.
python3 scripts/client-release-guard.py \
    --tag "$STABLE_TAG" --channel stable --zip "$ZIP" --metadata "$META"
python3 - <<'PY'
import hashlib,json,zipfile
from pathlib import Path
def digest(b):return hashlib.sha256(b).hexdigest()
with zipfile.ZipFile("test-proof/SGP_ClientPatch_2.1.0-test.1.zip") as a,zipfile.ZipFile("SGP_ClientPatch_2.1.0.zip") as b:
    assert a.testzip() is None and b.testzip() is None
    assert sorted(a.namelist())==sorted(b.namelist())
    test=json.loads(a.read("patch.json"))
    stable=json.loads(b.read("patch.json"))
    assert stable["actions"]==test["actions"],"Invalid action drift"
    assert stable["summary"]==test["summary"],"Unexpected behavior drift"
    for k in ("schemaVersion","targetPackId","minecraft","neoforge","restartRequired"):
        assert stable[k]==test[k]
    assert stable["fromVersions"]==test["fromVersions"]+["2.1.0-test.1"]
    assert stable["toVersion"]=="2.1.0"
    for f,expected in (
        ("SGP-Wands-Paxel-Compat-1.0.3.jar","52a8993070fd3bab43660d3f26df87d9cdcdda2e2711a01504a4d981ff034692"),
        ("SGP-BetterNether-Quartz-Glass-Compat-1.0.0.jar","60ce0f3a584b22f63c1b956629c49eac4b7d2514f6bd0ac1ba639f426661d5a7")
    ):
        name="files/mods/"+f
        assert a.read(name)==b.read(name)
        assert digest(b.read(name))==expected
print("SGP_CLIENT_210_RUNTIME_TEST_PAYLOAD_ACTION_PRECONDITION_INVARIANCE_PASS")
PY

cat > notes-210-stable.md <<'EOF'
SGP Client 2.1.0 — stable. Finalized from exact owner-runtime-PASS 2.1.0-test.1.

Owner runtime PASS on 2026-11-08 across all 9 reported check groups:
- Building Wands Destroy and Replace;
- Ironworks paxel Use: log stripping, path flattening, copper actions;
- durability safety;
- tool-slot selection;
- correct mining and restrictions;
- other paxels and ordinary tools;
- BetterNether Quartz Glass visual behavior.

Exact payload, installer actions and preconditions are byte-for-byte/action-for-action unchanged relative to the tested 2.1.0-test.1. Only stable version/patch identity, authorized predecessor list (adds successful TEST) and README/release documentation differ.

Scope:
- SGP-Wands-Paxel-Compat 1.0.3, exact SHA-256 52a8993070fd3bab43660d3f26df87d9cdcdda2e2711a01504a4d981ff034692.
- SGP-BetterNether-Quartz-Glass-Compat 1.0.0, exact SHA-256 60ce0f3a584b22f63c1b956629c49eac4b7d2514f6bd0ac1ba639f426661d5a7.
- Remove earlier paxel compat 1.0.0/1.0.1/1.0.2, restore Sodium SAFE, preserve BetterNether textures/alpha.
- Sources: accepted 2.0.10, failed test lineage 2.0.11-test.1/.2/.3, accepted runtime-PASS 2.1.0-test.1 for promotion.
- No dedicated server artifact; dedicated server changes require separate owner instruction.

Owner runtime evidence is the explicitly reported 9-group matrix; additional per-case logs/shader screenshots were not provided and are not claimed.
EOF

# The guard publishes a NEW Draft, verifies the exact uploaded assets,
# checks Installer activation, then makes the public stable release.
python3 scripts/client-release-guard.py \
    --tag "$STABLE_TAG" --channel stable --zip "$ZIP" --metadata "$META" \
    --publish --notes notes-210-stable.md

PUB="$(gh api "repos/$REPO/releases/tags/$STABLE_TAG")"
RID="$(printf '%s' "$PUB" | jq -r '.id')"
test "$(printf '%s' "$PUB" | jq -r '.draft')" = false
test "$(printf '%s' "$PUB" | jq -r '.prerelease')" = false
ASSETS="$(gh api "repos/$REPO/releases/$RID/assets")"
test "$(printf '%s' "$ASSETS" | jq 'length')" -eq 2
test "$(printf '%s' "$ASSETS" | jq -r '.[].name' | sort)" = \
    "$(printf '%s\n%s\n' "$ZIP" "$META" | sort)"
test "$(printf '%s' "$ASSETS" | jq -r --arg n "$ZIP" '.[]|select(.name==$n)|.digest')" = \
    "sha256:$(sha256sum "$ZIP"|awk '{print $1}')"
test "$(printf '%s' "$ASSETS" | jq -r --arg n "$META" '.[]|select(.name==$n)|.digest')" = \
    "sha256:$(sha256sum "$META"|awk '{print $1}')"

rm -rf live-client210-stable && mkdir live-client210-stable
gh release download "$STABLE_TAG" --repo "$REPO" --dir live-client210-stable
cmp "$ZIP" "live-client210-stable/$ZIP"
cmp "$META" "live-client210-stable/$META"
python3 scripts/client-release-guard.py \
    --tag "$STABLE_TAG" --channel stable \
    --zip "live-client210-stable/$ZIP" \
    --metadata "live-client210-stable/$META"

# Retain the successful TEST release/tag as immutable runtime evidence until
# the next successfully published TEST replaces it, per standing workflow.
gh api "repos/$REPO/releases/tags/$TEST_TAG" >/dev/null

# Re-run the byte/action invariance test against downloaded PUBLIC stable.
python3 - <<'PY'
import hashlib, json, zipfile
def digest(b):return hashlib.sha256(b).hexdigest()
a="test-proof/SGP_ClientPatch_2.1.0-test.1.zip"
b="live-client210-stable/SGP_ClientPatch_2.1.0.zip"
with zipfile.ZipFile(a) as za,zipfile.ZipFile(b) as zb:
    assert za.testzip() is None and zb.testzip() is None
    at=json.loads(za.read("patch.json"));bt=json.loads(zb.read("patch.json"))
    assert at["actions"]==bt["actions"]
    assert at["summary"]==bt["summary"]
    assert bt["fromVersions"]==at["fromVersions"]+["2.1.0-test.1"]
    for n in za.namelist():
        if n.startswith("files/"): assert za.read(n)==zb.read(n),n
    print("SGP_CLIENT_210_LIVE_PUBLIC_BYTE_AND_TEST_INVARIANCE_PASS")
PY

AID="$(printf '%s' "$ASSETS" | jq -r --arg n "$ZIP" '.[]|select(.name==$n)|.id')"
MID="$(printf '%s' "$ASSETS" | jq -r --arg n "$META" '.[]|select(.name==$n)|.id')"
{
 echo "SGP_CLIENT_210_STABLE_PUBLIC_PASS"
 echo "PUBLIC_RELEASE_ID=$RID"
 echo "PUBLIC_ZIP_ASSET_ID=$AID"
 echo "PUBLIC_META_ASSET_ID=$MID"
 echo "ZIP_SHA=$(sha256sum "$ZIP" | awk '{print $1}')"
 echo "ZIP_SIZE=$(stat -c %s "$ZIP")"
 echo "META_SHA=$(sha256sum "$META" | awk '{print $1}')"
 echo "META_SIZE=$(stat -c %s "$META")"
 echo "PAXEL_SHA=$PAXEL_SHA"
 echo "GLASS_SHA=$GLASS_SHA"
 echo "OWNER_RUNTIME=PASS_9_GROUPS"
 echo "SUCCESSFUL_TEST_RETAINED=true"
 echo "DEDICATED_SERVER_ARTIFACT=NOT_CREATED"
 echo "SOURCE_COMMIT=$GITHUB_SHA"
} | tee client210-stable-public-evidence.txt
