"""Flag function names that the decompiled code does not support. Static analysis aid.

Usage: python3 -I review_names.py <all.c from Dm32Decompile --all> <tables-dir> [out.tsv]

For each named function whose name claims an area (lcd, modem, rfic, codeplug, key, gps, sound, menu, ...), looks
for that area in the function's own decompiled text and in the names and text of its callees up to two levels down.
Prints functions where nothing matches. Also lists named functions whose body is empty, and rule-based names.
"""
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

src, tables = Path(sys.argv[1]), Path(sys.argv[2])
out = Path(sys.argv[3]) if len(sys.argv) > 3 else None
text = src.read_text(errors="replace")
parts = re.split(r"^//@@ (\S+) (\S+) body=(\d+)\n", text, flags=re.M)
funcs = {}
for i in range(1, len(parts), 4):
    addr, name, body, c = parts[i], parts[i + 1], int(parts[i + 2]), parts[i + 3]
    # drop the plate comment the import added, so the evidence text does not count as code
    code = re.sub(r"/\*.*?\*/", "", c, flags=re.S)
    funcs[name] = {"addr": addr, "body": body, "code": code}
names = set(funcs)
calls = {n: set(re.findall(r"\b([A-Za-z_]\w*)\s*\(", f["code"])) & names - {n} for n, f in funcs.items()}

REG = r"\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b"  # named hardware registers, e.g. AUDIO_CONTROL
AREAS = {
    "lcd": r"lcd|LCD|draw|fill_rect|12000[0-9a-f]{3}|glyph|bitmap|font",
    "draw": r"lcd|LCD|draw|fill|glyph|bitmap|font|pixel",
    "modem": r"(?:" + REG + r")|MODEM_REG|modem|110[0-9a-f]{5}|LAYER2|WORK_MODE|AUDIO_CONTROL|RF_MODE",
    "rfic": r"rfic|3wire|fd6818",
    "dataflash": r"dataflash|spi0|140a[0-9a-f]{4}",
    "codeplug": r"codeplug|dataflash",
    "key": r"key|KEY",
    "gps": r"gps|GPS|nmea|NMEA|uart1|1404[0-9a-f]{4}",
    "uart": r"uart|140[3459][0-9a-f]{4}",
    "sound": r"(?:" + REG + r")|sound|tone|prompt|beep|play|audio|dac|pcm",
    "tone": r"tone|ctcss|dcs|sound|beep|rfic",
    "prompt": r"(?:" + REG + r")|prompt|sound|voice|play",
    "menu": r"menu|lcd|draw|page",
    "fm": r"(?:" + REG + r")|fm_|rda|bitbang_i2c|FM|110[0-9a-f]{5}",
    "led": r"led|gpio",
    "gpio": r"gpio|14(02|10|11)[0-9a-f]{4}",
    "timer": r"timer|1400[0-9a-f]{4}",
    "adc": r"adc|140d[0-9a-f]{4}",
    "battery": r"batt|adc",
    "encrypt": r"crypt|key|aes|arc4|rc4",
    "crypto": r"crypt|key|aes|arc4|rc4",
    "tx": r"(?:" + REG + r")|tx|TX|ptt|rf_|modem|MODEM|110[0-9a-f]{5}|transmit|dac|140f[0-9a-f]{4}",
    "rx": r"(?:" + REG + r")|rx|RX|modem|MODEM|110[0-9a-f]{5}|rf_|receive|slot",
    "channel": r"channel|codeplug|current_channel|zone|vfo",
    "zone": r"zone|codeplug|channel",
    "contact": r"contact|codeplug|dataflash",
    "scan": r"scan",
    "vox": r"vox|audio|adc",
    "os": r"OS|os_|Os|CPU_",
}


def reach(n, depth=2):
    seen, frontier = {n}, {n}
    for _ in range(depth):
        frontier = {c for f in frontier for c in calls.get(f, ())} - seen
        seen |= frontier
    return seen


rows = []
for n, f in funcs.items():
    if re.match(r"^(sub_|FUN_|thunk_|get_|set_|test_|clear_|update_|return_|empty_stub|menu_state_\d)", n) or "_thunk_" in n:
        continue
    words = set(re.split(r"_", n.lower()))
    claimed = [a for a in AREAS if a in words]
    if not claimed:
        continue
    scope = reach(n)
    # search callee names and code, but not this function's own name (its signature line would match itself)
    own = funcs[n]["code"].replace(n, "")
    blob = " ".join(scope - {n}) + " " + own + " " + " ".join(funcs[s]["code"] for s in scope - {n})
    missing = [a for a in claimed if not re.search(AREAS[a], blob)]
    if missing:
        rows.append((n, f["addr"], f["body"], ",".join(missing), len(calls.get(n, ()))))
empty = [(n, f["addr"]) for n, f in funcs.items() if not n.startswith(("sub_", "FUN_", "empty_stub"))
         and re.search(r"\{\s*return;\s*\}", f["code"]) and f["body"] <= 4]
print(f"named functions checked; area claims not supported: {len(rows)}")
for r in sorted(rows, key=lambda x: x[0]):
    print("  {:55s} {} body={} missing={} callees={}".format(*r))
print(f"named functions with an empty body: {len(empty)}", empty[:10])
if out:
    with out.open("w") as h:
        h.write("name\taddress\tbody\tmissing\tcallees\n")
        for r in rows:
            h.write("\t".join(map(str, r)) + "\n")
