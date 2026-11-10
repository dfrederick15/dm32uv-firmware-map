"""Diff DM-32UV CPS codeplug files (.data) page by page and explain each change.

Usage: python3 -I tools/codeplug_diff.py <baseline.data> <changed.data> [--settings-fields <settings-fields.csv>]

The CPS file is a sequence of 4 KiB pages; the last byte of each page is its logical codeplug block number (the same
tags the radio stores in data flash). Pages are matched by tag, so reordering does not matter. Known record layouts
are decoded into a record number and offset:
  0x12+  channels   16-byte header (count), then 48-byte records: 84 in block 0x12 from +0x10, 85 per later block
  0x44+  contacts   24-byte records, 170 per block
  0x5C+  zones      145-byte records, 28 per block
  0x0F   RX group lists 109-byte records from +0x1C
  0x04   settings   offset within the settings block (RAM copy at 0x3E9D4 + offset - 0xA0 for the main part)
Untagged (0x00/0xFF) pages are compared by position and reported as CPS-only pages.
Static analysis aid; the files never leave this machine.
"""
import csv
import sys
from collections import defaultdict


def pages(data):
    tagged, untagged = {}, {}
    for i in range(len(data) // 4096):
        p = data[i * 4096:(i + 1) * 4096]
        tag = p[4095]
        if tag in (0x00, 0xFF):
            untagged[i] = p
        else:
            tagged[tag] = p
    return tagged, untagged


CHANNEL_FIELDS = {
    **{i: "name" for i in range(16)}, 0x10: "RX freq (BCD LE)", 0x11: "RX freq", 0x12: "RX freq", 0x13: "RX freq",
    0x14: "TX freq (BCD LE)", 0x15: "TX freq", 0x16: "TX freq", 0x17: "TX freq", 0x18: "flags (bit 4 digital)",
    0x19: "bit 7 wide, bit 6 scan add, bits 5-0 scan list", 0x1A: "bits 6-4 TX admit (0 Always, 1 Channel idle, 2 CC idle)", 0x1B: "low bits digital emergency system (2 = DEmer 2)", 0x1C: "high nibble squelch", 0x1D: "bits 3-0 colour code", 0x1E: "encryption key (0xFF none)",
    0x1F: "RX group list", 0x21: "RX tone low (BCD ones|tenths)", 0x22: "RX tone high (BCD hundreds|tens; FF FF = None, 00 06 = 60.0 Hz)",
    0x23: "TX tone low (BCD)", 0x24: "TX tone high", 0x26: "bits 3-1 signalling type (2 = Two Tone)", 0x27: "bits 7-4 step (NP: 5 = 25 kHz)", 0x29: "bits 3-2 PTT ID type (1 = BOT)",
}


def locate(tag, off):
    if 0x12 <= tag <= 0x41:
        if tag == 0x12:
            if off < 0x10:
                return "channel block header (byte 0 = channel count)"
            n, r = divmod(off - 0x10, 48)
            ch = n + 1
        else:
            n, r = divmod(off, 48)
            ch = 84 + (tag - 0x13) * 85 + n + 1
        field = CHANNEL_FIELDS.get(r, "")
        return f"channel {ch} +0x{r:02X}" + (f" {field}" if field else "") + (f" (RAM 0x3E1F8+0x{r - 16:02X})" if r >= 16 else "")
    if 0x44 <= tag <= 0x5B:
        n, r = divmod(off, 24)
        return f"contact {(tag - 0x44) * 170 + n + 1} +0x{r:02X}"
    if 0x5C <= tag <= 0x64:
        n, r = divmod(off, 145)
        return f"zone {(tag - 0x5C) * 28 + n + 1} +0x{r:02X}"
    if tag == 0x0F and off >= 0x1C:
        n, r = divmod(off - 0x1C, 109)
        return f"RX group list {n + 1} +0x{r:02X}"
    return ""


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sf = None
    if "--settings-fields" in sys.argv:
        sf = sys.argv[sys.argv.index("--settings-fields") + 1]
        args = [a for a in args if a != sf]
    a, b = open(args[0], "rb").read(), open(args[1], "rb").read()
    ta, ua = pages(a)
    tb, ub = pages(b)
    by_offset = defaultdict(list)
    if sf:
        for r in csv.DictReader(open(sf)):
            try:
                by_offset[int(r["byte_offset"], 0)].append(r["setting_id"])
            except (KeyError, ValueError):
                pass
    changes = 0
    for tag in sorted(set(ta) | set(tb)):
        pa, pb = ta.get(tag), tb.get(tag)
        if pa is None or pb is None:
            print(f"block 0x{tag:02X}: only in {'changed' if pa is None else 'baseline'}")
            continue
        for off in range(4095):
            if pa[off] != pb[off]:
                changes += 1
                extra = locate(tag, off)
                if tag == 0x04 and by_offset:
                    ids = by_offset.get(off - 0xA0) or by_offset.get(off)
                    if ids:
                        extra = f"setting id(s) {','.join(ids)}"
                print(f"block 0x{tag:02X} +0x{off:03X}: {pa[off]:02X} -> {pb[off]:02X}  "
                      f"bits {pa[off] ^ pb[off]:08b}  {extra}")
    for i in sorted(set(ua) | set(ub)):
        pa, pb = ua.get(i), ub.get(i)
        if pa is None or pb is None:
            print(f"untagged page {i}: only in one file")
            continue
        d = [k for k in range(4096) if pa[k] != pb[k]]
        if d:
            changes += len(d)
            print(f"untagged page {i}: {len(d)} bytes differ (first +0x{d[0]:03X}): "
                  + " ".join(f"+0x{k:03X}:{pa[k]:02X}->{pb[k]:02X}" for k in d[:12]))
    print(f"{changes} changed bytes")


if __name__ == "__main__":
    main()
