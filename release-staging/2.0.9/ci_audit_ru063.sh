#!/usr/bin/env bash
set -euo pipefail

JAR="regions-unexplored-0.6.3-neoforge-21.1.jar"
URL="https://mediafilez.forgecdn.net/files/9252/522/$JAR"

curl -fL --retry 3 --retry-delay 2 "$URL" -o "$JAR"
test -s "$JAR"
unzip -t "$JAR" >/dev/null

# Exact identity/version/loader audit.
unzip -p "$JAR" META-INF/neoforge.mods.toml > ru063-neoforge.mods.toml
grep -Eq 'modId[[:space:]]*=[[:space:]]*"regions_unexplored"' ru063-neoforge.mods.toml
grep -Eq 'version[[:space:]]*=[[:space:]]*"0\.6\.3"' ru063-neoforge.mods.toml
grep -Eq 'modId[[:space:]]*=[[:space:]]*"minecraft"' ru063-neoforge.mods.toml
grep -Eq '1\.21\.1|1\.21' ru063-neoforge.mods.toml

# Sanity: this must be the NeoForge jar and retain its embedded/runtime metadata.
jar tf "$JAR" > ru063-files.txt
grep -Fq 'META-INF/neoforge.mods.toml' ru063-files.txt
grep -Fq 'net/regions_unexplored/' ru063-files.txt

sha256sum "$JAR" | tee ru063_sha.txt
stat -c '%s' "$JAR" | tee ru063_size.txt
echo "RU_063_CANDIDATE_AUDIT_PASS"
