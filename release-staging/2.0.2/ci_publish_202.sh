#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
TAG="client-v2.0.2"
ZIP="SGP_ClientPatch_2.0.2.zip"
META="SGP_ClientPatch_2.0.2.meta.json"
SERVER="SGP_ServerPatch_2.0.2.zip"

python3 release-staging/2.0.2/build_202.py | tee build-202.txt

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
## SGP Client 2.0.2

Owner-authorized direct stable config-only maintenance release.

Exact sequential edge: 2.0.1 -> 2.0.2.

Changes:
- ArmorHUD left-side group aligned symmetrically with the accepted right-side spacing:
  - helmPosX, chestPosX, mainPosX, arrPosX: 136 -> 111;
  - existing right-side -111 values are unchanged.
- Create schematic maximum upload file size: 2048 -> 20480 KiB (2 MiB -> 20 MiB).
- Create schematic upload chunk size: 1024 -> 32767 bytes.

The Create packet-size value is the maximum declared by Create's own config range. No mods, datapacks, resource packs, options, or unrelated config values are changed.
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

rm -rf live-client && mkdir live-client
gh release download "$TAG" --repo "$REPO" --dir live-client
test -f "live-client/$ZIP"
test -f "live-client/$META"
cmp "$ZIP" "live-client/$ZIP"
cmp "$META" "live-client/$META"

python3 scripts/client-release-guard.py \
  --tag "$TAG" --channel stable --zip "live-client/$ZIP" --metadata "live-client/$META"

python3 - <<'PY'
import json, tomllib, zipfile

with zipfile.ZipFile("live-client/SGP_ClientPatch_2.0.2.zip") as z:
    assert z.testzip() is None
    assert sorted(z.namelist()) == ["README.txt", "patch.json"]
    p=json.loads(z.read("patch.json"))
    assert p["fromVersions"] == ["2.0.1"]
    assert p["toVersion"] == "2.0.2"
    assert len(p["actions"]) == 2
    hud,create=p["actions"]
    assert hud["target"] == "config/inventoryhud-client.toml"
    assert [(e["path"],e["value"]) for e in hud["edits"]] == [
      ("positions.helmPosX",111),
      ("positions.chestPosX",111),
      ("positions.mainPosX",111),
      ("positions.arrPosX",111),
    ]
    assert create["target"] == "config/create-server.toml"
    assert [(e["path"],e["value"]) for e in create["edits"]] == [
      ("schematics.maxTotalSchematicSize",20480),
      ("schematics.maxSchematicPacketSize",32767),
    ]

with zipfile.ZipFile("SGP_ServerPatch_2.0.2.zip") as z:
    assert z.testzip() is None
    assert sorted(z.namelist()) == [
      ".sgp/history.json",
      ".sgp/pack.json",
      "config/create-server.toml",
      "world/serverconfig/create-server.toml",
    ]
    a=z.read("config/create-server.toml")
    b=z.read("world/serverconfig/create-server.toml")
    assert a == b
    c=tomllib.loads(a.decode("utf-8"))
    assert c["schematics"]["maxTotalSchematicSize"] == 20480
    assert c["schematics"]["maxSchematicPacketSize"] == 32767
    assert json.loads(z.read(".sgp/pack.json"))["version"] == "2.0.2"
    h=json.loads(z.read(".sgp/history.json"))
    assert h["currentVersion"] == "2.0.2"
    assert h["entries"][-1]["version"] == "2.0.2"

print("LIVE_CLIENT_202_VERIFY_PASS")
print("SERVER_202_HANDOFF_AUDIT_PASS")
PY

AID="$(printf '%s' "$ASSETS" | jq -r --arg n "$ZIP" '.[]|select(.name==$n)|.id')"
MID="$(printf '%s' "$ASSETS" | jq -r --arg n "$META" '.[]|select(.name==$n)|.id')"

{
  echo "SGP_202_RELEASE_VERIFY_PASS"
  echo "PUBLISHED_RELEASE_ID=$RID"
  echo "PUBLISHED_ASSET_ID=$AID"
  echo "PUBLISHED_META_ASSET_ID=$MID"
  echo "PUBLISHED_SHA=$(cat client_sha.txt)"
  echo "PUBLISHED_SIZE=$(cat client_size.txt)"
  echo "META_SHA=$(cat meta_sha.txt)"
  echo "META_SIZE=$(cat meta_size.txt)"
  echo "TARGET_CREATE_SHA=$(cat target_create_sha.txt)"
  echo "TARGET_CREATE_SIZE=$(cat target_create_size.txt)"
  echo "TARGET_HUD_SHA=$(cat target_hud_sha.txt)"
  echo "TARGET_HUD_SIZE=$(cat target_hud_size.txt)"
  echo "SERVER_SHA=$(cat server_sha.txt)"
  echo "SERVER_SIZE=$(cat server_size.txt)"
  echo "SERVER_PACK_SHA=$(cat server_pack_sha.txt)"
  echo "SERVER_PACK_SIZE=$(cat server_pack_size.txt)"
  echo "SERVER_HISTORY_SHA=$(cat server_history_sha.txt)"
  echo "SERVER_HISTORY_SIZE=$(cat server_history_size.txt)"
  echo "SOURCE_COMMIT=$GITHUB_SHA"
} | tee release-202-result.txt
