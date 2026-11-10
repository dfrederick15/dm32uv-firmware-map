#!/usr/bin/env bash
# Build a Ghidra project for the DM-32UV DM32.NRF.01.049 firmware with the static-analysis map applied.
#
# Usage: tools/ghidra/build_dm32_project.sh <split-dir> <project-dir> [ghidra-dir]
#   <split-dir>   folder with application.bin, iram-init.bin, sahb-init.bin, bootloader.bin, boot-header.bin,
#                 and application.asm / iram-init.asm (objdump listings of those segments)
#   TABLES        environment variable: folder with the CSV tables (default: <split-dir>)
#   <project-dir> where the Ghidra project DM32_NRF_01_049 is created (must not already contain it)
# Needs: Ghidra 12.x, gh or curl, python3. The C-SKY SLEIGH files come from github.com/leommxj/ghidra_csky
# (fetched at build time, not redistributed here) plus the local additions in csky-patch/.
set -euo pipefail
SPLIT=$(realpath "$1"); OUT=$(realpath -m "$2"); GHIDRA=${3:-$HOME/.local/opt/ghidra_12.2_PUBLIC}
HERE=$(dirname "$(realpath "$0")")
VER=$(sed -n 's/^application.version=//p' "$GHIDRA/Ghidra/application.properties")
EXT="$HOME/.config/ghidra/ghidra_${VER}_PUBLIC/Extensions/CSKY"
CSKY_REF=${CSKY_REF:-HEAD}
TABLES=$(realpath "${TABLES:-$SPLIT}")

if [ ! -f "$EXT/data/languages/csky_v2.sla" ]; then
  tmp=$(mktemp -d)
  curl -fsSL "https://codeload.github.com/leommxj/ghidra_csky/tar.gz/$CSKY_REF" | tar xz -C "$tmp" --strip-components=1
  rm -rf "$EXT"; mkdir -p "$EXT/data"
  cp -r "$tmp/CSKY/data/languages" "$EXT/data/"
  cp "$tmp/CSKY/Module.manifest" "$EXT/"
  printf 'name=CSKY\ndescription=C-SKY v2 SLEIGH (leommxj/ghidra_csky) with DM32 local additions\nauthor=leommxj; local additions\nversion=%s\n' "$VER" > "$EXT/extension.properties"
  rm -rf "$tmp"
  python3 "$HERE/csky-patch/apply_patch.py" "$EXT/data/languages"
  (cd "$EXT/data/languages" && "$GHIDRA/support/sleigh" csky_v2.slaspec)
fi

mkdir -p "$OUT"
REF="$OUT/objdump-reference.txt"
python3 -I "$HERE/make_reference.py" "$SPLIT" "$REF" "$TABLES"

"$GHIDRA/support/analyzeHeadless" "$OUT" DM32_NRF_01_049 \
  -import "$SPLIT/application.bin" -loader BinaryLoader -loader-baseAddr 0x0300C000 \
  -processor CSKY_V2:LE:32:default -scriptPath "$HERE" \
  -preScript Dm32ImportMap.java "$TABLES" "$SPLIT" \
  -postScript Dm32FixFlow.java "$REF" \
  -postScript Dm32CheckDisasm.java "$REF" "$OUT/disasm-check.txt" \
  -analysisTimeoutPerFile 3000 > "$OUT/build.log" 2>&1
grep -E "DM32 map|DM32 flow fix|literal pool|Import succeeded|ERROR" "$OUT/build.log" || true
head -1 "$OUT/disasm-check.txt"
