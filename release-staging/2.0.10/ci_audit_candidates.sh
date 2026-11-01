#!/usr/bin/env bash
set -euo pipefail

LITHO="lithostitched-1.8.1-neoforge-21.1.jar"
EVERY="everycomp-1.21-2.11.55-neoforge.jar"

curl -fL --retry 3 --retry-delay 2 "https://mediafilez.forgecdn.net/files/9170/709/$LITHO" -o "$LITHO"
curl -fL --retry 3 --retry-delay 2 "https://mediafilez.forgecdn.net/files/9263/267/$EVERY" -o "$EVERY"

for f in "$LITHO" "$EVERY"; do
  test -s "$f"
  unzip -t "$f" >/dev/null
done

unzip -p "$LITHO" META-INF/neoforge.mods.toml > litho.mods.toml
unzip -p "$EVERY" META-INF/neoforge.mods.toml > every.mods.toml

grep -Eq 'modId[[:space:]]*=[[:space:]]*"lithostitched"' litho.mods.toml
grep -Eq 'version[[:space:]]*=[[:space:]]*"1\.8\.1"' litho.mods.toml
grep -Eq 'modId[[:space:]]*=[[:space:]]*"everycomp"' every.mods.toml
grep -Eq 'version[[:space:]]*=[[:space:]]*"1\.21-2\.11\.55"|version[[:space:]]*=[[:space:]]*"2\.11\.55"' every.mods.toml

# Prove the Lithostitched candidate contains holder-set/alternate-targeting implementation,
# not merely a version number that satisfies RU's loose dependency range.
jar tf "$LITHO" > litho-files.txt
unzip -p "$LITHO" META-INF/neoforge.mods.toml > /dev/null
python3 - <<'PY'
import zipfile, re, sys
p="lithostitched-1.8.1-neoforge-21.1.jar"
with zipfile.ZipFile(p) as z:
    hits=[]
    for n in z.namelist():
        if not n.endswith('.class'): continue
        b=z.read(n)
        if b'holder_set' in b or b'HolderSet' in b or b'alternate' in b.lower():
            hits.append(n)
    print("LITHO_IMPLEMENTATION_HITS="+str(len(hits)))
    for n in hits[:80]: print(n)
    assert hits, "No holder-set/alternate targeting implementation evidence in Lithostitched 1.8.1"
PY

# Inspect declared dependencies for exact-current-pack compatibility review.
echo "===== LITHOSTITCHED MODS TOML ====="
cat litho.mods.toml
echo "===== EVERYCOMP MODS TOML ====="
cat every.mods.toml

sha256sum "$LITHO" | tee litho_sha.txt
stat -c '%s' "$LITHO" | tee litho_size.txt
sha256sum "$EVERY" | tee every_sha.txt
stat -c '%s' "$EVERY" | tee every_size.txt

echo "CORRECTIVE_210_CANDIDATES_AUDIT_PASS"
