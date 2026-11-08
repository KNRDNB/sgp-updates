#!/usr/bin/env bash
set -euo pipefail

mkdir -p .sgp-paxel-audit
cd .sgp-paxel-audit

download_exact() {
  local version="$1" target="$2"
  curl --fail --location --silent --show-error --retry 2 \
    "https://api.modrinth.com/v2/version/$version" -o "$target.json"
  local url expected
  url="$(jq -er '.files | (map(select(.primary == true)) + .)[0].url' "$target.json")"
  expected="$(jq -er '.files | (map(select(.primary == true)) + .)[0].hashes.sha512' "$target.json")"
  curl --fail --location --silent --show-error --retry 2 "$url" -o "$target.jar"
  printf '%s  %s\n' "$expected" "$target.jar" | sha512sum --check --status
  echo "EXACT_DOWNLOAD_PASS $target version=$version size=$(stat -c '%s' "$target.jar") sha256=$(sha256sum "$target.jar" | cut -c1-64)"
}

download_exact nvMyIx0w wands-305
download_exact 91r9PehB ironworks-403

echo "=== WANDS JAR MOD METADATA ==="
unzip -p wands-305.jar META-INF/neoforge.mods.toml | head -90 || true
echo "=== WANDS CLASSES ==="
unzip -Z1 wands-305.jar | grep -E 'WandTool|wand/Wand.class|WandToolsMenu|WandUtils|WandsConfig' | head -80 || true

javap -classpath wands-305.jar -p -s net.nicguzzo.wands.wand.Wand > wands-method-descriptors.txt
javap -classpath wands-305.jar -c -p net.nicguzzo.wands.wand.Wand > wands-bytecode.txt
echo "=== EXACT WANDS MENU CLASSES ==="
unzip -Z1 wands-305.jar | grep -Ei '(Menu|Screen).class$' | grep -Ei 'Wand|Tool' | head -100 || true
menu_class="$(unzip -Z1 wands-305.jar | grep -E '/Wand(Menu|ToolsMenu).class$' | head -1 | sed -e 's@/@.@g' -e 's@\.class$@@' || true)"
if [ -n "$menu_class" ]; then
  javap -classpath wands-305.jar -c -p "$menu_class" > wands-menu-bytecode.txt
else
  echo "MENU CLASS NOT FOUND" > wands-menu-bytecode.txt
fi
javap -classpath wands-305.jar -c -p net.nicguzzo.wands.utils.WandUtils > wands-utils-bytecode.txt
javap -classpath wands-305.jar -c -p net.nicguzzo.wands.client.screens.WandToolScreen > wands-screen-bytecode.txt

python3 - <<'PY'
from pathlib import Path
s=Path('wands-method-descriptors.txt').read_text()
print('=== EXACT WANDS TARGET FIELDS/SIGNATURES ===')
for line in s.splitlines():
    if any(k in line for k in ('tools;', 'player_data;', 'digger_item;', 'digger_item_slot;', 'has_axe;', 'has_shovel;', 'use;', 'update_tools(', 'can_dig(', 'can_destroy_or_use(', 'place_block(', 'tool_would_break(', 'hurt_tool(')):
        print(line)
print('=== EXACT TARGET METHOD BYTECODE EXCERPTS ===')
lines=Path('wands-bytecode.txt').read_text().splitlines()
for name,limit in [('update_tools',300),('can_destroy_or_use',340),('can_dig',340),('tool_would_break',180),('place_block',240)]:
    matches=[i for i,l in enumerate(lines) if l.startswith('  ') and l.endswith(');') and (name+'(') in l]
    if not matches:
        print(name,'NOT FOUND'); continue
    i=matches[0]; j=next((k for k in range(i+1,len(lines)) if lines[k].startswith('  ') and lines[k].endswith(');') and not lines[k].startswith('    ')),len(lines))
    sel=lines[i:min(j,i+limit)]
    print(f'\n### {name} bytecode total_lines={j-i}, showing={len(sel)}')
    for line in sel: print(line)
print('=== MENU CLICK METHOD ===')
ml=Path('wands-menu-bytecode.txt').read_text().splitlines()
for i,l in enumerate(ml):
    if l.startswith('  ') and 'clicked(' in l:
        print('\n'.join(ml[i:i+160])); break
PY

echo "=== IRONWORKS PAXEL FILES ==="
unzip -Z1 ironworks-403.jar | grep -Ei 'paxel|tags/item/(axes|pickaxes|shovels|hoes)|tags/block/mineable' | head -160 || true

echo "=== IRONWORKS PAXEL CLASS CANDIDATES ==="
unzip -Z1 ironworks-403.jar | grep -Ei '(Paxel|Tool|ModItems).*class$' | head -100 || true

echo "=== EXACT IRONWORKS PAXEL CLASS METHODS ==="
for p in Copper Bronze Brass Iron Gold Diamond Steel Netherite; do
  javap -classpath ironworks-403.jar -p -c "create_ironworks.item.$p"PaxelItem > "ironworks-$p-paxel-bytecode.txt"
  grep -E '^public class|^  (public|protected)' "ironworks-$p-paxel-bytecode.txt" | head -35 || true
done

echo "=== EXACT IRONWORKS PAXEL TAGS ==="
for name in data/create_ironworks/tags/item/tools/paxels.json data/minecraft/tags/item/axes.json data/minecraft/tags/item/pickaxes.json data/minecraft/tags/item/shovels.json data/minecraft/tags/item/hoes.json data/c/tags/item/pickaxes.json; do
  echo "$name"
  unzip -p ironworks-403.jar "$name" 2>/dev/null || true
  echo
done

echo "=== EXACT SCREEN / MENU BYTECODE INDICATORS ==="
grep -n -E 'Tools|clicked|ContainerInput|putIntArray|SendPlayerData|sendToServer|getIntArray' wands-menu-bytecode.txt wands-screen-bytecode.txt | head -140 || true

echo "=== IRONWORKS CONSTRUCTORS + ABILITIES + USE-ON ==="
python3 - <<'PY'
from pathlib import Path
import re
for tier in ('Copper','Bronze','Brass','Iron','Gold','Diamond','Steel','Netherite'):
    p=Path('ironworks-'+tier+'-paxel-bytecode.txt')
    raw=p.read_text()
    sections=re.split(r'(?=^  (?:public|protected|private) .+\([^;]*\);$)',raw,flags=re.M)
    wanted=('PaxelItem();','canPerformAction(', 'isCorrectToolForDrops(', 'getDestroySpeed(', 'useOn(')
    print('\n=========',tier,'=========')
    for section in sections:
        first=section.splitlines()[0] if section.strip() else ''
        if any(x in first for x in wanted):
            print('\n'.join(section.splitlines()[:125]))
    print("EXPLICIT_USEON=",any('useOn(' in x.splitlines()[0] for x in sections if x.strip()))
PY
echo "=== MOD ITEM REGISTRATION ==="
javap -classpath ironworks-403.jar -p -c create_ironworks.init.CreateIronworksModItems > ironworks-items-bytecode.txt
grep -n -Ei 'paxel|tool|tiereditem' ironworks-items-bytecode.txt | head -140 || true
echo "=== EXACT WANDS MENU CLICK ==="
python3 - <<'PY'
from pathlib import Path
s=Path('wands-menu-bytecode.txt').read_text()
i=s.find('  public void clicked(')
j=s.find('\n  ',i+3)
print(s[i:i+12500] if j<=i else s[i:min(j,i+12500)])
PY
echo "EXACT_WANDS_PAXEL_AUDIT_COMPLETE"
