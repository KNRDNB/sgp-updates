#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
TAG="client-v2.0.4-test.1"
ZIP="SGP_ClientPatch_2.0.4-test.1.zip"
META="SGP_ClientPatch_2.0.4-test.1.meta.json"
OLD_TEST="v1.10.0-test.4"

python3 release-staging/2.0.4-test.1/build_client_204_test1.py | tee build-client-204-test1.txt

python3 scripts/client-release-guard.py   --tag "$TAG" --channel test --zip "$ZIP" --metadata "$META"

if gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1; then
  echo "Unexpected existing release $TAG" >&2
  exit 1
fi
if gh api "repos/$REPO/git/ref/tags/$TAG" >/dev/null 2>&1; then
  echo "Unexpected existing tag $TAG" >&2
  exit 1
fi

cat > notes.md <<'EOF'
## SGP Client 2.0.4-test.1

TEST candidate from accepted stable 2.0.3.

Changes:
- add FTB Chunks Mobs Spawn Control 1.0.4;
- FTB Chunks claims: 1000 per member, party limit mode SUM, hard team cap 5000;
- player force-loading remains disabled (max_force_loaded_chunks = 0);
- FTB claim protection remains disabled;
- Mob Control blocks only NATURAL hostile spawning in explicitly protected claimed chunks;
- spawner, patrol, raid, structure, spawn egg, command, breeding, bucket and dispenser spawning remains allowed;
- named/persistent flags do not bypass the natural-spawn rule;
- strict join fallback remains disabled to avoid interfering with mod-controlled direct entity spawns.

protected_chunks.properties is intentionally not distributed: players choose protected chunks in-game.

This is a BOTH-side mod. Formal dedicated-server packaging is intentionally deferred until owner release authorization under the SGP server-preparation gate.
EOF

python3 scripts/client-release-guard.py   --tag "$TAG" --channel test --zip "$ZIP" --metadata "$META"   --publish --notes notes.md

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

python3 scripts/client-release-guard.py   --tag "$TAG" --channel test --zip "live-client/$ZIP" --metadata "live-client/$META"

python3 - <<'PY'
import hashlib, json, zipfile
def sha(b): return hashlib.sha256(b).hexdigest()
with zipfile.ZipFile("live-client/SGP_ClientPatch_2.0.4-test.1.zip") as z:
    assert z.testzip() is None
    assert sorted(z.namelist()) == sorted([
      "README.txt",
      "patch.json",
      "files/mods/ftb_chunks_mobs_spawn_control-1.0.4-neoforge-1.21.1.jar",
      "files/config/ftbchunks-world.snbt",
      "files/config/ftb_chunks_mobs_spawn_control-common.toml",
    ])
    p=json.loads(z.read("patch.json"))
    assert p["fromVersions"] == ["2.0.3"]
    assert p["toVersion"] == "2.0.4-test.1"
    assert [a["type"] for a in p["actions"]] == ["copy","copy","copy"]
    mod=z.read("files/mods/ftb_chunks_mobs_spawn_control-1.0.4-neoforge-1.21.1.jar")
    assert len(mod)==50538
    assert sha(mod)=="c7df7bdd469237418ce4ef892497793addba84f9c92125b0fde05f8b6e353960"
    ftb=z.read("files/config/ftbchunks-world.snbt").decode()
    assert "hard_team_claim_limit: 5000" in ftb
    assert "max_claimed_chunks: 1000" in ftb
    assert 'party_limit_mode: "sum"' in ftb
    assert "max_force_loaded_chunks: 0" in ftb
    assert "disable_protection: true" in ftb
    cfg=z.read("files/config/ftb_chunks_mobs_spawn_control-common.toml").decode()
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
        assert line in cfg,line
print("LIVE_CLIENT_204_TEST1_VERIFY_PASS")
PY

if gh api "repos/$REPO/releases/tags/$OLD_TEST" >/dev/null 2>&1; then
  gh release delete "$OLD_TEST" --repo "$REPO" --cleanup-tag -y
fi

AID="$(printf '%s' "$ASSETS" | jq -r --arg n "$ZIP" '.[]|select(.name==$n)|.id')"
MID="$(printf '%s' "$ASSETS" | jq -r --arg n "$META" '.[]|select(.name==$n)|.id')"
{
  echo "CLIENT_204_TEST1_RELEASE_VERIFY_PASS"
  echo "PUBLISHED_RELEASE_ID=$RID"
  echo "PUBLISHED_ASSET_ID=$AID"
  echo "PUBLISHED_META_ASSET_ID=$MID"
  echo "PUBLISHED_SHA=$(cat client204_test1_sha.txt)"
  echo "PUBLISHED_SIZE=$(cat client204_test1_size.txt)"
  echo "META_SHA=$(cat client204_test1_meta_sha.txt)"
  echo "META_SIZE=$(cat client204_test1_meta_size.txt)"
  echo "SOURCE_COMMIT=$GITHUB_SHA"
  echo "OLD_TEST_RETIRED=$OLD_TEST"
} | tee release-client-204-test1-result.txt
