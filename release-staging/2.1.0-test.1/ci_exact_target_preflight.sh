#!/usr/bin/env bash
set -euo pipefail
mkdir -p .sgp-210-exact
cd .sgp-210-exact
fetch_version() {
  local version="$1" name="$2" expected="$3"
  curl -fL --retry 3 --silent --show-error \
    "https://api.modrinth.com/v2/version/$version" -o "$name.json"
  local url sha512
  url="$(jq -er '.files | (map(select(.primary == true)) + .)[0].url' "$name.json")"
  sha512="$(jq -er '.files | (map(select(.primary == true)) + .)[0].hashes.sha512' "$name.json")"
  curl -fL --retry 3 --silent --show-error "$url" -o "$name.jar"
  printf '%s  %s\n' "$sha512" "$name.jar" | sha512sum --check
  test "$(sha256sum "$name.jar" | cut -d' ' -f1)" = "$expected"
  echo "EXACT_UPSTREAM_PASS $name $(stat -c %s "$name.jar")"
}
fetch_version nvMyIx0w wands \
 "565c7c31926a7d4f5dd365bae79fc891d5d21f09d3beb0026e7743b9f8bcc57f"
fetch_version 91r9PehB ironworks \
 "d6efd546e0dce52d7a79fb98de5be4a2690e70505e9ce1ed920f0431597243fd"
javap -classpath wands.jar -p -s net.nicguzzo.wands.wand.Wand > wand-sig.txt
javap -classpath wands.jar -p -c net.nicguzzo.wands.wand.Wand > wand-bytecode.txt
javap -classpath wands.jar -p -c net.nicguzzo.wands.menues.WandMenu > wand-menu-bytecode.txt
for exact in \
 'can_dig(net.minecraft.world.level.block.state.BlockState, boolean, net.minecraft.world.item.ItemStack)' \
 'can_destroy_or_use(net.minecraft.world.level.block.state.BlockState, boolean)' \
 'place_block(net.minecraft.core.BlockPos, net.minecraft.world.level.block.state.BlockState)' \
 'net.minecraft.nbt.CompoundTag player_data' \
 'net.minecraft.world.item.ItemStack digger_item' \
 'public int digger_item_slot' \
 'public boolean has_axe' \
 'public boolean has_shovel'; do
   grep -Fq "$exact" wand-sig.txt || { echo "WANDS_SIGNATURE_MISSING: $exact"; exit 1; }
done
grep -Fq 'ItemStack.useOn:(Lnet/minecraft/world/item/context/UseOnContext;)Lnet/minecraft/world/InteractionResult;' wand-bytecode.txt
grep -Fq 'DataComponents.TOOL' wand-bytecode.txt
grep -Fq 'String Tools' wand-bytecode.txt
grep -Fq 'String Tools' wand-menu-bytecode.txt
grep -Fq 'SendPlayerData:' wand-menu-bytecode.txt

for tier in Copper Bronze Brass Iron Gold Diamond Steel Netherite; do
  name="create_ironworks.item.$tier"PaxelItem
  javap -classpath ironworks.jar -p -c "$name" > "$tier"-paxel-bytecode.txt
  grep -Fq 'extends net.minecraft.world.item.TieredItem' "$tier"-paxel-bytecode.txt
  grep -Fq 'canPerformAction(' "$tier"-paxel-bytecode.txt
  grep -Fq 'isCorrectToolForDrops(' "$tier"-paxel-bytecode.txt
  grep -Fq 'getDestroySpeed(' "$tier"-paxel-bytecode.txt
  grep -Fq 'ItemAbilities.DEFAULT_AXE_ACTIONS' "$tier"-paxel-bytecode.txt
  grep -Fq 'ItemAbilities.DEFAULT_SHOVEL_ACTIONS' "$tier"-paxel-bytecode.txt
  ! grep -Fq ' useOn(' "$tier"-paxel-bytecode.txt
  ! grep -Fq 'Item$Properties.tool:' "$tier"-paxel-bytecode.txt
done
echo "EXACT_WANDS_305_IRONWORKS_403_BYTECODE_GATE_PASS"
