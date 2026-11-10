"""Apply the DM32 local additions to a checkout of leommxj/ghidra_csky's CSKY/data/languages folder.

Usage: python3 apply_patch.py <languages-dir>
Idempotent. Adds missing instructions (dm32_extra*.sinc), raw control-register fields, makes 16-bit mulsh signed,
and fixes movih (upstream truncated the immediate before shifting, so every movih produced 0).
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
edit("32b_data.sinc", "i32_imm16_rx = zext( i32_imm16_imm:2 << 16 );",
     "i32_imm16_rx = zext(i32_imm16_imm:2) << 16;  # DM32 local fix: shift after widening", "shift after widening")
# Semantic fixes found by auditing every constructor body against the C-SKY v2 ISA:
edit("16b_data.sinc", """        local tmp:4 = i16_r4_rz & i16_r4_rx;
        i16_r4_rz = ~tmp;""", """        i16_r4_rz = i16_r4_rz & ~i16_r4_rx;  # DM32 local fix: andn is rz & ~rx""", "andn is rz & ~rx")
edit("16b_data.sinc", "i16_r4_rz = zext(~psr_cf );", "i16_r4_rz = zext(psr_cf == 0);  # DM32 local fix: mvcv gives 0/1", "mvcv gives 0/1")
edit("32b_data.sinc", """            local tmp:4 = i32_r_rx & i32_r_ry;
            i32_r_rz =- zext( ~tmp );""", """            i32_r_rz = i32_r_rx & ~i32_r_ry;  # DM32 local fix: andn is rx & ~ry""", "andn is rx & ~ry")
# zext/sext rz, rx, msb, lsb: extract bits msb..lsb (upstream dropped bit msb and never sign-extended)
FIELD_Z = "i32_r_rz = (i32_r_rx << (31 - i32_r_pcode)) >> (31 - i32_r_pcode + i32_r_imm5);  # DM32 local fix"
FIELD_S = "i32_r_rz = (i32_r_rx << (31 - i32_r_pcode)) s>> (31 - i32_r_pcode + i32_r_imm5);  # DM32 local fix"
edit("32b_data.sinc", "    i32_r_rz = zext( ( i32_r_rx >> i32_r_pcode ) & 1 );", "    " + FIELD_Z + " (1 bit)", FIELD_Z + " (1 bit)")
edit("32b_data.sinc", """	local upper_mask:4 = ( 1 << i32_r_pcode ) - 1;
    i32_r_rz = zext( ( i32_r_rx & upper_mask ) >> i32_r_imm5 );""", "    " + FIELD_Z, FIELD_Z + "\n")
edit("32b_data.sinc", "    i32_r_rz = sext( ( i32_r_rx >> i32_r_pcode ) & 1 );", "    " + FIELD_S + " (1 bit)", FIELD_S + " (1 bit)")
edit("32b_data.sinc", """	local upper_mask:4 = ( 1 << i32_r_pcode ) - 1;
    i32_r_rz = sext( ( i32_r_rx & upper_mask ) >> i32_r_imm5 );""", "    " + FIELD_S, FIELD_S + "\n")
# mulu/mulua/mulus: 64-bit product into hi:lo (upstream used a 4-byte temporary)
edit("32b_data.sinc", """            local tmp = i32_r_rx * i32_r_ry;
            lo = tmp:32;
            hi = tmp>>32;""", """            local tmp:8 = zext(i32_r_rx) * zext(i32_r_ry);  # DM32 local fix
            lo = tmp:4;
            hi = tmp(4);""", "zext(i32_r_rx) * zext(i32_r_ry);  # DM32 local fix")
edit("32b_data.sinc", """            local tmp = hi<<32 + lo + i32_r_rx * i32_r_ry;
            lo = tmp:32;
            hi = tmp>>32;""", """            local tmp:8 = ((zext(hi) << 32) | zext(lo)) + zext(i32_r_rx) * zext(i32_r_ry);  # DM32 local fix
            lo = tmp:4;
            hi = tmp(4);""", "| zext(lo)) + zext(i32_r_rx)")
edit("32b_data.sinc", """            local tmp = (hi<<32 + lo) - i32_r_rx * i32_r_ry;
            lo = tmp:32;
            hi = tmp>>32;""", """            local tmp:8 = ((zext(hi) << 32) | zext(lo)) - zext(i32_r_rx) * zext(i32_r_ry);  # DM32 local fix
            lo = tmp:4;
            hi = tmp(4);""", "| zext(lo)) - zext(i32_r_rx)")
print("patched", lang)
