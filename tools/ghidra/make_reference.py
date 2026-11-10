"""Write an "address mnemonic operands" reference list from the objdump listings, limited to known function bodies.

Usage: python3 -I make_reference.py <split-dir> <out.txt> [<tables-dir>]
"""
import bisect
import csv
import re
import sys
from pathlib import Path

split, out = Path(sys.argv[1]), Path(sys.argv[2])
tables = Path(sys.argv[3]) if len(sys.argv) > 3 else split
line = re.compile(r"^\s*([0-9a-f]+):\t([0-9a-f ]+?)\s*\t(\S+)\s*(.*)$")
funcs = [r for r in csv.DictReader((tables / "functions.csv").open()) if r["segment"] != "bootloader"]
spans = sorted((int(r["address"], 16), int(r["span_end"], 16)) for r in funcs)
starts = [s for s, _ in spans]
copy_start = 0x030C0C38  # flash copy of the RAM image: covered at its RAM address instead
rows = []
for name in ("iram-init", "application"):
    for raw in (split / f"{name}.asm").open():
        m = line.match(raw)
        if not m or m[3].startswith("."):
            continue
        a = int(m[1], 16)
        if name == "application" and a >= copy_start:
            continue
        i = bisect.bisect_right(starts, a) - 1
        if i >= 0 and a < spans[i][1]:
            rows.append(f"{a:x} {m[3]} {m[4].split('//')[0].strip()}")
out.write_text("\n".join(rows) + "\n")
print("reference instructions:", len(rows))
