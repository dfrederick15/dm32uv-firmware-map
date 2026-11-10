"""Merge function and RAM names edited in Ghidra back into the DM32 tables.

Usage:
  python3 -I sync_from_ghidra.py <export-prefix> <tables-dir> [--apply] [--allow-removals]

Reads <export-prefix>-functions.csv and -labels.csv written by Dm32ExportNames.java.
Without --apply it only prints what would change.

Rules:
- A function whose Ghidra name differs from the table name and is not a placeholder (sub_*, FUN_*) is a rename.
  Its labels.csv row is replaced (or added) with source "ghidra review". The evidence is taken from the Ghidra
  function comment: the text before the "basis:" line that the import script adds, if it was edited.
- A comment edit without a rename updates the evidence of the existing row.
- A function that has a name in the tables but a placeholder in Ghidra is reported; it is only unnamed with
  --allow-removals.
- User-defined labels in RAM (0x2F000-0x57FFF, 0x18000800-0x18004C03) that are not in ram-names.csv are added
  with confidence "ghidra review"; renamed ones are updated.
functions.csv names are updated to match labels.csv.
"""
import csv
import re
import sys
from pathlib import Path

args = [a for a in sys.argv[1:] if not a.startswith("--")]
APPLY = "--apply" in sys.argv
REMOVE = "--allow-removals" in sys.argv
prefix, tables = args[0], Path(args[1])
SOURCE = "ghidra review"
PLACEHOLDER = re.compile(r"^(sub|FUN|thunk_FUN)_[0-9a-fA-F]+$")
META = ("basis:", "module:", "hardware:", "tasks:", "direct callers:", "no known caller", "uC/OS-III task")


def read(path):
    with open(path, newline="") as h:
        return list(csv.DictReader(h))


def write(path, rows, fields):
    with open(path, "w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def evidence_from(comment):
    keep = []
    for line in comment.splitlines():
        if line.strip().startswith(META):
            continue
        keep.append(line.strip())
    return " ".join(x for x in keep if x).strip()


gfun = {int(r["address"], 16): r for r in read(f"{prefix}-functions.csv")}
glab = read(f"{prefix}-labels.csv")
labels = read(tables / "labels.csv")
lfields = list(labels[0])
functions = read(tables / "functions.csv")
ffields = list(functions[0])
by_addr = {int(r["nrf_address"], 16): r for r in labels if r["nrf_address"]}
names_in_use = {r["name"] for r in labels}

renames, comment_edits, removals, adds = [], [], [], []
for f in functions:
    a = int(f["address"], 16)
    g = gfun.get(a)
    if not g:
        continue
    gname, tname = g["name"], f["name"]
    row = by_addr.get(a)
    ev = evidence_from(g["comment"])
    if PLACEHOLDER.match(gname):
        if row and not PLACEHOLDER.match(tname):
            removals.append((a, tname))
        continue
    if gname != tname:
        if gname in names_in_use and (not row or row["name"] != gname):
            print(f"skip {a:#x}: name {gname} already used elsewhere")
            continue
        renames.append((a, tname, gname, ev))
    elif row and ev and ev != row["evidence"].strip() and ev != " ".join(row["evidence"].split()):
        comment_edits.append((a, gname, row["evidence"], ev))

print(f"renames {len(renames)}, comment edits {len(comment_edits)}, names cleared in Ghidra {len(removals)}")
for a, old, new, ev in renames[:60]:
    print(f"  rename {a:#x}: {old} -> {new}")
for a, n, old, new in comment_edits[:30]:
    print(f"  evidence {a:#x} {n}: {new[:100]}")
for a, n in removals[:30]:
    print(f"  cleared in Ghidra {a:#x}: {n}" + ("" if REMOVE else " (kept; use --allow-removals)"))

# RAM labels
ram = read(tables / "ram-names.csv")
rfields = list(ram[0])
ram_by = {int(r["address"], 16): r for r in ram}
ram_changes = []
for r in glab:
    a = int(r["address"], 16)
    if not (0x2F000 <= a < 0x58000 or 0x18000800 <= a < 0x18004C04):
        continue
    n = r["name"]
    if n.startswith(("DAT_", "PTR_", "LAB_", "s_", "u_")) or n.endswith("_handlers") or n == "key_function_handlers_flash_image":
        continue
    cur = ram_by.get(a)
    if cur is None or cur["name"] != n:
        ram_changes.append((a, cur["name"] if cur else "", n))
print(f"RAM label changes {len(ram_changes)}")
for a, old, new in ram_changes[:40]:
    print(f"  ram {a:#x}: {old or '(new)'} -> {new}")

if not APPLY:
    print("dry run: add --apply to write")
    sys.exit(0)

for a, old, new, ev in renames:
    row = by_addr.get(a)
    if row:
        row["name"] = new
        row["source"] = SOURCE
        row["match_method"] = "reviewed in Ghidra"
        if ev:
            row["evidence"] = ev
    else:
        row = {k: "" for k in lfields}
        row.update(name=new, nrf_address=hex(a), match_method="reviewed in Ghidra", evidence=ev, source=SOURCE)
        labels.append(row)
        by_addr[a] = row
for a, n, old, new in comment_edits:
    by_addr[a]["evidence"] = new
    by_addr[a]["source"] = SOURCE if by_addr[a]["source"] != SOURCE else SOURCE
if REMOVE:
    gone = {a for a, _ in removals}
    labels = [r for r in labels if not (r["nrf_address"] and int(r["nrf_address"], 16) in gone)]
labels.sort(key=lambda t: int(t["nrf_address"], 16) if t["nrf_address"] else 1 << 40)
dupes = {r["name"] for r in labels if sum(1 for x in labels if x["name"] == r["name"]) > 1}
if dupes:
    sys.exit(f"duplicate names after merge, nothing written: {sorted(dupes)[:10]}")
write(tables / "labels.csv", labels, lfields)

final = {int(r["nrf_address"], 16): r["name"] for r in labels if r["nrf_address"]}
for f in functions:
    a = int(f["address"], 16)
    if a in final:
        f["name"], f["labeled"] = final[a], "yes"
    elif REMOVE and any(a == x for x, _ in removals):
        f["name"], f["labeled"] = f"sub_{a:x}", ""
write(tables / "functions.csv", functions, ffields)

for a, old, new in ram_changes:
    if a in ram_by:
        ram_by[a]["name"] = new
        ram_by[a]["confidence"] = SOURCE
    else:
        row = {k: "" for k in rfields}
        row.update(address=hex(a), name=new, confidence=SOURCE, basis="named in Ghidra")
        ram.append(row)
write(tables / "ram-names.csv", ram, rfields)
print("written:", tables / "labels.csv", tables / "functions.csv", tables / "ram-names.csv")
