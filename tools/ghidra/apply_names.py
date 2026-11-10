"""Apply reviewed function names to the DM32 tables.

Usage: python3 -I apply_names.py <tables-dir> <names.tsv> [source]
names.tsv lines: address<TAB>name<TAB>evidence   (lines starting with # are ignored)
Renames existing labels at that address or adds new ones; refuses duplicate names.
"""
import csv
import sys
from pathlib import Path

tables, tsv = Path(sys.argv[1]), Path(sys.argv[2])
source = sys.argv[3] if len(sys.argv) > 3 else "ghidra review"
want = []
for line in tsv.read_text().splitlines():
    if not line.strip() or line.startswith("#"):
        continue
    a, n, why = line.split("\t", 2)
    want.append((int(a, 16), n.strip(), why.strip()))

labels = list(csv.DictReader((tables / "labels.csv").open()))
lf = list(labels[0])
functions = list(csv.DictReader((tables / "functions.csv").open()))
ff = list(functions[0])
fa = {int(r["address"], 16) for r in functions}
by = {int(r["nrf_address"], 16): r for r in labels if r["nrf_address"]}
used = {r["name"]: r for r in labels}
done = 0
for a, n, why in want:
    if a not in fa:
        print(f"skip {a:#x} {n}: not a function start")
        continue
    if n in used and used[n] is not by.get(a):
        print(f"skip {a:#x} {n}: name already used")
        continue
    row = by.get(a)
    if row is None:
        row = {k: "" for k in lf}
        row["nrf_address"] = hex(a)
        labels.append(row)
        by[a] = row
    if row.get("name"):
        used.pop(row["name"], None)
    row.update(name=n, evidence=why, match_method="reviewed decompiled code", source=source)
    used[n] = row
    done += 1
labels.sort(key=lambda t: int(t["nrf_address"], 16) if t["nrf_address"] else 1 << 40)
assert len({r["name"] for r in labels}) == len(labels)
names = {int(r["nrf_address"], 16): r["name"] for r in labels if r["nrf_address"]}
for r in functions:
    a = int(r["address"], 16)
    if a in names:
        r["name"], r["labeled"] = names[a], "yes"
for path, rows, fields in ((tables / "labels.csv", labels, lf), (tables / "functions.csv", functions, ff)):
    with path.open("w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
print(f"applied {done} of {len(want)}")
