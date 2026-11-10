"""Make a modified copy of a DM-32UV CPS codeplug file (.data) for checking in the official CPS.

Usage:
  python3 -I tools/codeplug_edit.py <in.data> <out.data> EDIT [EDIT ...]
EDIT forms:
  ch:<n>:<offset>=<byte>            set channel n record byte (offset from record start, hex), e.g. ch:7:0x1A=0x10
  ch:<n>:<offset>:<mask>=<value>    set only the masked bits (value already shifted), e.g. ch:7:0x1A:0x70=0x20
  blk:<tag>:<offset>=<byte>         set a byte in logical block <tag>, e.g. blk:0x04:0xA2=0x03
  blk:<tag>:<offset>:<mask>=<value> masked form for blocks

Channel records: block 0x12 holds a 16-byte header then 84 records of 48 bytes from +0x10; later blocks hold 85.
The input file is never modified. Prints every byte changed. Writes nothing to any radio.
"""
import sys


def num(s):
    return int(s, 0)


def page_index(data):
    idx = {}
    for i in range(len(data) // 4096):
        tag = data[i * 4096 + 4095]
        if tag not in (0x00, 0xFF):
            idx[tag] = i * 4096
    return idx


def channel_addr(idx, n, off):
    if n < 1 or off >= 48:
        raise SystemExit(f"bad channel {n} offset {off:#x}")
    if n <= 84:
        tag, base = 0x12, 0x10 + (n - 1) * 48
    else:
        k = n - 85
        tag, base = 0x13 + k // 85, (k % 85) * 48
    if tag not in idx:
        raise SystemExit(f"block {tag:#x} for channel {n} is not in the file")
    return idx[tag] + base + off


def main():
    src, dst, edits = sys.argv[1], sys.argv[2], sys.argv[3:]
    data = bytearray(open(src, "rb").read())
    idx = page_index(data)
    for e in edits:
        lhs, rhs = e.split("=")
        parts = lhs.split(":")
        mask = 0xFF
        if parts[0] == "ch":
            addr = channel_addr(idx, int(parts[1]), num(parts[2]))
            if len(parts) > 3:
                mask = num(parts[3])
        elif parts[0] == "blk":
            tag, off = num(parts[1]), num(parts[2])
            if tag not in idx or off >= 4095:
                raise SystemExit(f"bad block edit {e}")
            addr = idx[tag] + off
            if len(parts) > 3:
                mask = num(parts[3])
        else:
            raise SystemExit(f"unknown edit {e}")
        old = data[addr]
        new = (old & ~mask & 0xFF) | (num(rhs) & mask)
        data[addr] = new
        print(f"{e}: file +0x{addr:05X} {old:02X} -> {new:02X}")
    if dst == src:
        raise SystemExit("refusing to overwrite the input file")
    open(dst, "wb").write(data)
    print("wrote", dst)


if __name__ == "__main__":
    main()
