#!/usr/bin/env bash
set -euo pipefail
REPO="KNRDNB/sgp-updates"
VERSION="2.1.1"
TAG="server-v2.1.1"
BASE_TAG="server-v2.1.0"
BUILD_RUN="42504345413"
BUILD_COMMIT="91bd68f38cd27015816faebbb09f778d9e0e601a"
ARTIFACT="sgp-server-2.1.1-paxel-handoff"
ZIP="SGP_ServerPatch_2.1.1.zip"
ZIP_SHA="ada4f72e85adda0826e91e3da85c4bfe08ddc2b92b86c3a2f4b7ee102a5a9f3a"
ZIP_SIZE=7750
PAXEL_SHA="52a8993070fd3bab43660d3f26df87d9cdcdda2e2711a01504a4d981ff034692"

# Strict one-shot authorization: user explicitly approved stable release and
# clarified dedicated server must be published after client runtime PASS.
# The old server-v2.1.0 release belongs to JourneyMap and is immutable.
if gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1; then
  echo "Refusing existing stable release $TAG" >&2; exit 1
fi
if gh api "repos/$REPO/git/ref/tags/$TAG" >/dev/null 2>&1; then
  echo "Refusing existing tag $TAG" >&2; exit 1
fi
gh api "repos/$REPO/releases/tags/$BASE_TAG" >/dev/null
POINTER="$(gh api "repos/$REPO/contents/server/latest.json" -H 'Accept: application/vnd.github.raw+json')"
# GET /contents may be JSON metadata or raw according to proxy; verify on both.
python3 - <<'PY'
import base64, json, subprocess
raw=subprocess.check_output(["gh","api","repos/KNRDNB/sgp-updates/contents/server/latest.json"])
doc=json.loads(raw)
if "content" in doc:
    doc=json.loads(base64.b64decode(doc["content"]))
assert doc["version"]=="2.1.0" and doc["tag"]=="server-v2.1.0", doc
print("SERVER_211_EXACT_PREDECESSOR_CHANNEL_PASS")
PY
RUN="$(gh api "repos/$REPO/actions/runs/$BUILD_RUN")"
test "$(printf '%s' "$RUN" | jq -r '.conclusion')" = "success"
test "$(printf '%s' "$RUN" | jq -r '.head_sha')" = "$BUILD_COMMIT"
test "$(printf '%s' "$RUN" | jq -r '.head_repository.full_name')" = "$REPO"
test "$(printf '%s' "$RUN" | jq -r '.path')" = ".github/workflows/build-server-2.1.1.yml"

mkdir -p handoff
gh run download "$BUILD_RUN" --repo "$REPO" --name "$ARTIFACT" --dir handoff
test -f "handoff/$ZIP"
test "$(stat -c %s "handoff/$ZIP")" = "$ZIP_SIZE"
test "$(sha256sum "handoff/$ZIP" | awk '{print $1}')" = "$ZIP_SHA"
python3 - <<'PY'
from pathlib import Path
import hashlib, io, json, zipfile
report=json.loads(Path("handoff/server211_audit.json").read_bytes())
assert report["target_version"]=="2.1.1"
assert report["source_server"]=="2.1.0"
assert report["zip_size"]==7750
assert report["zip_sha256"]=="ada4f72e85adda0826e91e3da85c4bfe08ddc2b92b86c3a2f4b7ee102a5a9f3a"
assert report["deletions"]==["mods/SGP-Wands-Paxel-Compat-1.0.0.jar"]
assert report["client_only_glass_included"] is False
assert report["journeymap_live_config_changed"] is False
p=Path("handoff/SGP_ServerPatch_2.1.1.zip")
with zipfile.ZipFile(p) as z:
    assert z.testzip() is None
    assert set(z.namelist())=={
        ".sgp/pack.json",".sgp/history.json",
        "mods/SGP-Wands-Paxel-Compat-1.0.3.jar"
    }
    paxel=z.read("mods/SGP-Wands-Paxel-Compat-1.0.3.jar")
    assert len(paxel)==7673
    assert hashlib.sha256(paxel).hexdigest()=="52a8993070fd3bab43660d3f26df87d9cdcdda2e2711a01504a4d981ff034692"
    with zipfile.ZipFile(io.BytesIO(paxel)) as jar:
        assert jar.testzip() is None
        assert "sgp/wandspaxel/mixin/SgpWandsPaxelCompatMixin.class" in jar.namelist()
    pack=json.loads(z.read(".sgp/pack.json"))
    history=json.loads(z.read(".sgp/history.json"))
    assert pack["version"]==history["currentVersion"]=="2.1.1"
    assert [entry["version"] for entry in history["entries"]][-2:]==["2.1.0","2.1.1"]
    assert pack["lastUpdate"]=={
      "id":"sgp-server-2.1.1","type":"release",
      "version":"2.1.1","releaseDate":"2026-11-08"}
    assert not any(n.startswith(("world/","config/","journeymap/")) for n in z.namelist())
print("SERVER_211_EXACT_BUILD_ARTIFACT_REUSE_AND_CONTENT_PASS")
PY

printf '%s' '["2.1.0"]' > from-versions.json
printf '%s' '["mods/SGP-Wands-Paxel-Compat-1.0.0.jar"]' > deletions.json
cat > changelog.txt <<'EOF'
Серверное исправление совместимости Building Wands 3.0.5 с восемью пакселями Create: Ironworks 4.0.3. Удалить старый SGP-Wands-Paxel-Compat-1.0.0.jar и установить точно проверенный на клиенте 2.1.0 SGP-Wands-Paxel-Compat-1.0.3.jar. Исправлены распознавание добывающего инструмента и действия топора и лопаты через NeoForge. Сохранены уровень добычи, прочность, выбор инструмента и ограничения. JourneyMap 6.0.8, серверные конфиги, данные мира и клиентский Quartz Glass compat не изменяются. Патч требует резервной копии и остановки сервера перед установкой. Серверный runtime пока не подтверждён.
EOF

python3 scripts/server-release-guard.py \
 --zip "handoff/$ZIP" \
 --version "$VERSION" \
 --from-versions-file from-versions.json \
 --expected-sha "$ZIP_SHA" \
 --expected-size "$ZIP_SIZE" \
 --deletions deletions.json \
 --changelog changelog.txt \
 --backup-mode files \
 --min-installer 2.2.0 \
 --output channel

python3 - <<'PY'
import json, pathlib
meta=json.loads(pathlib.Path("channel/SGP_ServerPatch_2.1.1.meta.json").read_text())
assert meta["fromVersions"]==["2.1.0"]
assert meta["deletions"]==["mods/SGP-Wands-Paxel-Compat-1.0.0.jar"]
assert meta["backupMode"]=="files"
assert meta["minInstallerVersion"]=="2.2.0"
assert meta["tag"]=="server-v2.1.1"
p=json.loads(pathlib.Path("channel/latest.json").read_text())
assert p["tag"]==meta["tag"] and p["metadataName"]=="SGP_ServerPatch_2.1.1.meta.json"
print("SERVER_211_CANONICAL_GUARD_AND_METADATA_PASS")
PY

# Reuse standard guarded publication: Draft, downloaded Draft bytes,
# public exact bytes and pointer activation LAST. No archive rebuild.
export VERSION
python3 scripts/publish-server-channel.py | tee publication-server-211.log

PUBLIC="$(gh api "repos/$REPO/releases/tags/$TAG")"
test "$(printf '%s' "$PUBLIC" | jq -r '.draft')" = false
test "$(printf '%s' "$PUBLIC" | jq -r '.prerelease')" = false
RID="$(printf '%s' "$PUBLIC" | jq -r '.id')"
ASSETS="$(printf '%s' "$PUBLIC" | jq '.assets')"
test "$(printf '%s' "$ASSETS" | jq 'length')" -eq 2
test "$(printf '%s' "$ASSETS" | jq -r '.[].name' | sort)" = \
 "$(printf '%s\n%s\n' "$ZIP" "SGP_ServerPatch_2.1.1.meta.json" | sort)"
test "$(printf '%s' "$ASSETS" | jq -r --arg n "$ZIP" '.[]|select(.name==$n)|.digest')" = "sha256:$ZIP_SHA"
test "$(printf '%s' "$ASSETS" | jq -r --arg n "$ZIP" '.[]|select(.name==$n)|.size')" = "$ZIP_SIZE"
META_SHA="$(sha256sum channel/SGP_ServerPatch_2.1.1.meta.json | awk '{print $1}')"
test "$(printf '%s' "$ASSETS" | jq -r --arg n "SGP_ServerPatch_2.1.1.meta.json" '.[]|select(.name==$n)|.digest')" = "sha256:$META_SHA"

rm -rf live-211 && mkdir live-211
gh release download "$TAG" --repo "$REPO" --dir live-211
cmp "handoff/$ZIP" "live-211/$ZIP"
cmp channel/SGP_ServerPatch_2.1.1.meta.json live-211/SGP_ServerPatch_2.1.1.meta.json
test "$(sha256sum "live-211/$ZIP" | awk '{print $1}')" = "$ZIP_SHA"
test "$(sha256sum "live-211/SGP_ServerPatch_2.1.1.meta.json" | awk '{print $1}')" = "$META_SHA"

python3 - <<'PY'
import base64,json,subprocess
raw=json.loads(subprocess.check_output(["gh","api","repos/KNRDNB/sgp-updates/contents/server/latest.json"]))
pointer=json.loads(base64.b64decode(raw["content"]))
meta=json.load(open("channel/SGP_ServerPatch_2.1.1.meta.json"))
assert pointer==json.load(open("channel/latest.json"))
assert pointer["version"]=="2.1.1" and pointer["tag"]=="server-v2.1.1"
assert pointer["metadataSha256"]==__import__("hashlib").sha256(open("channel/SGP_ServerPatch_2.1.1.meta.json","rb").read()).hexdigest()
assert meta["sha256"]=="ada4f72e85adda0826e91e3da85c4bfe08ddc2b92b86c3a2f4b7ee102a5a9f3a"
print("SERVER_211_LIVE_PUBLIC_ASSETS_AND_STATIC_POINTER_PASS")
PY

ZIP_ID="$(printf '%s' "$ASSETS" | jq -r --arg n "$ZIP" '.[]|select(.name==$n)|.id')"
META_ID="$(printf '%s' "$ASSETS" | jq -r --arg n "SGP_ServerPatch_2.1.1.meta.json" '.[]|select(.name==$n)|.id')"
{
 echo "SGP_SERVER_211_PUBLIC_PASS"
 echo "RELEASE_ID=$RID"
 echo "ZIP_ASSET_ID=$ZIP_ID"
 echo "META_ASSET_ID=$META_ID"
 echo "ZIP_SHA256=$ZIP_SHA"
 echo "ZIP_SIZE=$ZIP_SIZE"
 echo "META_SHA256=$META_SHA"
 echo "META_SIZE=$(stat -c %s channel/SGP_ServerPatch_2.1.1.meta.json)"
 echo "PAXEL_SHA256=$PAXEL_SHA"
 echo "FROM_VERSIONS=[2.1.0]"
 echo "DELETION=mods/SGP-Wands-Paxel-Compat-1.0.0.jar"
 echo "OWNER_SERVER_RUNTIME=PENDING"
 echo "SERVER_HANDED_OFF_UNDER_STANDING_RULE=true"
 echo "SOURCE_COMMIT=$GITHUB_SHA"
} | tee server211-public-evidence.txt
