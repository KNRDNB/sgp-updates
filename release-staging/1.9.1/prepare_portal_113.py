from pathlib import Path
import json, shutil

ROOT=Path.cwd()
SRC=ROOT/"release-staging/1.9.0/portalmod"
TEST3=ROOT/"release-staging/1.9.1-test.3/portalmod"
OUT=ROOT/"release-staging/1.9.1/portalmod"

if OUT.exists():
    shutil.rmtree(OUT)
shutil.copytree(SRC, OUT)

# Start from the proven base-obsidian arbitrary-shape implementation (1.0.0)
# and add only the narrow portal-generated zombified-piglin suppression
# already present in 1.1.1/1.1.2.
shutil.copyfile(
    TEST3/"src/main/java/sgp/shapelessportals/mixin/NetherPortalBlockMixin.java",
    OUT/"src/main/java/sgp/shapelessportals/mixin/NetherPortalBlockMixin.java",
)

gp=OUT/"gradle.properties"
s=gp.read_text("utf-8")
assert "mod_version=1.0.0" in s
gp.write_text(s.replace("mod_version=1.0.0","mod_version=1.1.3"),"utf-8")

(OUT/"src/main/resources/sgp_shapeless_nether_portals.mixins.json").write_text(
json.dumps({
  "required": True,
  "minVersion": "0.8",
  "package": "sgp.shapelessportals.mixin",
  "compatibilityLevel": "JAVA_21",
  "mixins": [
    "NetherPortalBlockMixin",
    "PortalShapeAccessor",
    "PortalShapeMixin"
  ],
  "injectors": {"defaultRequire": 1}
}, indent=2)+"\n","utf-8")

(OUT/"src/main/resources/META-INF/neoforge.mods.toml").write_text(
'''modLoader="javafml"
loaderVersion="[4,)"
license="MIT"

[[mods]]
modId="sgp_shapeless_nether_portals"
version="1.1.3"
displayName="SGP Shapeless Nether Portals"
authors="SGP; portal-shape algorithm adapted from Nicer Portals by Roundaround"
description=\'\'\'Allows arbitrary enclosed vertical Nether portal shapes using the normal portal-frame predicate and disables portal-generated zombified piglins. SGP adds no crying-obsidian or BetterNether frame materials.\'\'\'

[[mixins]]
config="sgp_shapeless_nether_portals.mixins.json"

[[dependencies.sgp_shapeless_nether_portals]]
modId="neoforge"
type="required"
versionRange="[21.1.249,21.2)"
ordering="NONE"
side="BOTH"

[[dependencies.sgp_shapeless_nether_portals]]
modId="minecraft"
type="required"
versionRange="[1.21.1]"
ordering="NONE"
side="BOTH"
''',"utf-8")

# Stable 1.1.3 deliberately contains none of the TEST2/TEST3 alternate-frame additions.
for forbidden in [
    OUT/"src/main/java/sgp/shapelessportals/PortalFrameRules.java",
    OUT/"src/main/java/sgp/shapelessportals/mixin/BaseFireBlockMixin.java",
    OUT/"src/main/resources/data/c/tags/block/nether_pframe.json",
]:
    assert not forbidden.exists(), forbidden

print("PORTALMOD_113_SOURCE_PREP_PASS")
