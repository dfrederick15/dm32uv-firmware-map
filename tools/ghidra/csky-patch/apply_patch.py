"""Apply the DM32 local additions to a checkout of leommxj/ghidra_csky's CSKY/data/languages folder.

Usage: python3 apply_patch.py <languages-dir>
Idempotent. Adds missing instructions (dm32_extra*.sinc), raw control-register fields, and makes 16-bit mulsh signed.
"""
import shutil
import sys
from pathlib import Path

lang = Path(sys.argv[1])
here = Path(__file__).parent
for f in ("dm32_extra16.sinc", "dm32_extra32.sinc", "dm32_extra32_defs.sinc"):
    shutil.copy(here / f, lang / f)


def edit(name, old, new, marker):
    p = lang / name
    s = p.read_text()
    if marker in s:
        return
    if old not in s:
        sys.exit(f"{name}: expected text not found; upstream changed, review the patch")
    p.write_text(s.replace(old, new, 1))


edit("32b.sinc", "    i32_bit_1011 = (26,27)\n;",
     "    i32_bit_1011 = (26,27)\n\n    # DM32 local: raw register-number fields for control register operands\n"
     "    cr_num_rx = (0,4)\n    cr_num_ry = (5,9)\n    cr_num_rz = (16,20)\n;", "cr_num_rx")
edit("32b.sinc", "with : i32_optype = 0b11 {",
     '@include "dm32_extra32_defs.sinc"\n\nwith : i32_optype = 0b11 {\n@include "dm32_extra32.sinc"', "dm32_extra32_defs")
edit("16b.sinc", '@include "16b_data.sinc"', '@include "16b_data.sinc"\n@include "dm32_extra16.sinc"', "dm32_extra16")
edit("16b_data.sinc", "i16_r4_rz = zext(i16_r4_rx[0,16]) * zext(i16_r4_rz[0,16]);",
     "i16_r4_rz = sext(i16_r4_rx:2) * sext(i16_r4_rz:2);  # DM32 local fix: signed", "DM32 local fix")
print("patched", lang)
