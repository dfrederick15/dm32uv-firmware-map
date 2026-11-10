# Ghidra project for the DM-32UV firmware

Builds a Ghidra project for `DM32.NRF.01.049` with the static-analysis map applied: every function created and named,
the evidence for each name as a function comment, RAM variables, modem registers, peripheral blocks, and the vector,
menu-state and key-handler tables typed.

```
TABLES=tables tools/ghidra/build_dm32_project.sh <split-dir> <project-dir>
ghidra    # File > Open Project > <project-dir>/DM32_NRF_01_049.gpr
```

`<split-dir>` holds your own program-flash dump split into segments, plus objdump listings of the two code segments:

| File | Program flash offset | Load address |
| --- | --- | --- |
| `boot-header.bin` | `0x000000-0x000FFF` | `0x03000000` |
| `bootloader.bin` | `0x001000-0x00BFFF` | `0x03001000` |
| `application.bin` | `0x00C000-0x0E14EB` | `0x0300C000` |
| `sahb-init.bin` | `0x0727D0-0x076BD3` | `0x18000800` |
| `iram-init.bin` | `0x0C0C38-0x0DFCEB` | `0x00010000` |
| `application.asm`, `iram-init.asm` | `objdump -D` of the two segments at their load addresses (C-SKY GNU binutils) | |

`TABLES` points at this repository's `tables/` folder (default: `<split-dir>`). The project contains firmware bytes,
so keep it out of version control.

## Bringing Ghidra edits back into the tables

Rename functions, edit function comments or name RAM variables in Ghidra, save, then:

```
analyzeHeadless <project-dir> DM32_NRF_01_049 -process application.bin -noanalysis -readOnly \
  -scriptPath tools/ghidra -postScript Dm32ExportNames.java <project-dir>/export
python3 -I tools/ghidra/sync_from_ghidra.py <project-dir>/export <tables-dir>            # dry run
python3 -I tools/ghidra/sync_from_ghidra.py <project-dir>/export <tables-dir> --apply
```

`Dm32ExportNames.java` can also be run from the Script Manager; it asks for the export prefix.

- A rename replaces the name in `labels.csv` and `functions.csv`, with source `ghidra review`.
- The evidence comes from the function comment, ignoring the `basis:`, `module:`, `tasks:` lines the import adds.
- A function set back to `FUN_`/`sub_` in Ghidra is only reported, unless `--allow-removals` is given.
- New or renamed user labels in RAM go to `ram-names.csv` with confidence `ghidra review`.
- Names that are already used at another address are skipped and reported.

## Processor module

Ghidra has no C-SKY support. The build fetches the SLEIGH files from
[leommxj/ghidra_csky](https://github.com/leommxj/ghidra_csky) (no licence file, so they are fetched rather than copied
here), applies `csky-patch/apply_patch.py`, compiles them with Ghidra's own `sleigh` tool and installs the result as a
user extension. The Java part of that project (ELF relocations) is not built or needed.

Local additions, with encodings inferred from the fixed bits of every occurrence in the GNU objdump listing:
`tst`, `tstnbz`, `ff0`, `ff1`, `xtrb0-3`, `mfcr`, `mtcr`, `rte`, `psrclr`, `psrset`, `muls`, `mulsa`, `mulsha`,
`srs.b/h/w`.

Semantic fixes, found by auditing every constructor body against the ISA (each one silently corrupted decompiled
output):

| Instruction | Upstream behaviour | Fixed |
| --- | --- | --- |
| `movih` | truncated the immediate to 16 bits before shifting, so every result was 0 (peripheral bases vanished) | `zext(imm) << 16` |
| `zext rz, rx, msb, lsb` | mask `(1 << msb) - 1` dropped bit `msb` (32-bit `zextb` became `& 0x7f`) | extract bits `msb..lsb` |
| `sext rz, rx, msb, lsb` | never sign-extended the field | arithmetic shift of the field |
| `andn` (16 and 32-bit) | NAND, and a negated NAND | `rz & ~rx`, `rx & ~ry` |
| `mvcv` (16-bit) | bitwise NOT of a one-bit flag gave 0xFE/0xFF | 0 or 1 |
| `mulsh` (16-bit) | unsigned | signed |
| `mulu`, `mulua`, `mulus` | 4-byte temporary | 64-bit product into hi:lo |

The import also turns off Ghidra's "Non-Returning Functions - Discovered" analyzer: it marked the uC/CPU
critical-section helpers as non-returning, cutting every function after its first critical section.

Still not decoded: DSP and coprocessor instructions (`bloop`, `cprgr`, `cpop`, `pkg`, vector ops), used mainly inside
the AMBE codec, so a few large codec functions are only partly disassembled.

## Scripts

| Script | Role |
| --- | --- |
| `build_dm32_project.sh` | End-to-end build: module, import, map, flow fix, check |
| `make_reference.py` | objdump listing to an `address mnemonic operands` reference, limited to known function bodies |
| `Dm32ImportMap.java` | Pre-analysis: memory blocks, functions, names, comments, RAM and register labels, tables, bookmarks |
| `Dm32FixFlow.java` | Post-analysis: clears wrong no-return and `bsr` flow overrides, disassembles unreached code inside known functions, marks literal pools constant, recomputes bodies |
| `Dm32CheckDisasm.java` | Compares Ghidra's disassembly with the reference |
| `Dm32Decompile.java` | Decompiles named functions to a file (uses the program's decompiler options); `--all` decompiles every function |
| `Dm32ExportNames.java`, `sync_from_ghidra.py` | Export names and comments from Ghidra and merge them into the tables |
| `review_names.py`, `show_c.py` | Flag names whose claimed area the decompiled code does not support; print decompiled functions |
| `Dm32BodySizes.java`, `Dm32GapStarts.java`, `Dm32ListNoReturn.java`, `Dm32Probe.java` | Diagnostics |

## Results on the analysed image

- 99.4% of instructions Ghidra decodes match objdump; the rest are alias spellings (`movt`/`inct`, `movf`/`incf`,
  `not`/`nor`).
- 96% of sampled reference instructions are disassembled; most of the remainder are literal pools that objdump decodes
  as code.
- 95% of the bytes in known function spans are inside Ghidra function bodies.
- Decompiled output uses the map's names for functions and RAM variables, for example `menu_state = param_1;`.
