# DM-32UV firmware map

A static map of the Baofeng DM-32UV stock firmware `DM32.NRF.01.049`: memory layout, functions, RAM variables,
hardware use, menus, keys, settings and codeplug structure. Nothing here was tested on a running radio.

This repository holds addresses, names and descriptions only. It contains no firmware binaries and no disassembly.

## Contents

| Path | Contents |
| --- | --- |
| `docs/memory-map.md` | CPU address space, peripherals, interrupts, program flash, RAM and data flash layout, codeplug blocks |
| `docs/firmware-notes.md` | Voice path, transmit control, modem configuration, interrupt dispatch, hardware notes, open questions |
| `tables/functions.csv` | 2,881 functions: address, size, callers, callees, module, hardware, tasks, reachability |
| `tables/labels.csv` | Every function name with how it was derived and the evidence |
| `tables/callgraph.csv` | Direct calls between functions |
| `tables/tasks.csv`, `tables/task-map.csv` | uC/OS-III tasks and what each reaches |
| `tables/vectors.csv`, `tables/irq-handlers.csv` | Vector table and run-time interrupt handler installation |
| `tables/indirect-calls.csv`, `tables/callback-tables.csv` | Register-indirect calls and the resolved function tables |
| `tables/hardware-map.csv`, `tables/gpio-map.csv` | Peripheral blocks and GPIO pins with the functions that use them |
| `tables/modem-registers.csv`, `tables/rfic-writes.csv` | Modem register use and RF chip register writes |
| `tables/keypad-map.csv`, `tables/key-events.csv` | Keypad scan codes and key event handlers |
| `tables/menu-states.csv`, `tables/menu-pages.csv` | Menu dispatch states and the 276 menu pages |
| `tables/settings-*.csv` | Setting IDs, RAM fields, flash locations and call sites |
| `tables/codeplug-access.csv` | Every codeplug read and write site with block, offset and length |
| `tables/ram-names.csv`, `tables/ram-variables.csv`, `tables/ram-xrefs.csv` | Named RAM variables and where RAM addresses are used |
| `tables/sound-ids.csv` | Sound and voice prompt request IDs |
| `tables/data-map-program.csv`, `tables/data-map-dataflash.csv`, `tables/images.csv` | Data regions in program flash and data flash, icons |
| `tables/code-gaps.csv`, `tables/bootloader-ram-functions.csv` | Bytes between functions, and functions in the bootloader's RAM image |
| `tools/ghidra/` | Scripts that build a Ghidra project from your own firmware dump with all of the above applied (see its README) |

## Ghidra

`tools/ghidra/build_dm32_project.sh` builds a Ghidra 12 project from a program-flash dump: C-SKY processor module,
every function named with its evidence as a comment, RAM variables, registers and tables. Ghidra's disassembly matches
GNU objdump on 95.6% of the 203,882 instructions in known functions, plus 0.6% that differ only in alias spelling.

## Naming conventions

- Plain names (`lcd_init`, `OSSemPend`) have direct code evidence.
- `candidate_` names are inferences from behaviour, strings or context.
- Names such as `get_u8_3e172`, `set_<var>`, `test_<var>_<mask>` and `<callee>_thunk_<addr>` come from code-shape rules.
- `sub_<addr>` functions are not yet named.
- `labels.csv` records the source of each name, so any group can be filtered out.

Addresses are runtime addresses: application code at `0x0300C000` (executed in place from program flash offset
`0xC000`), RAM code from `0x10000`.

## Coverage

1,915 of 2,881 functions are named, and 92.3% of direct call sites reach a named function. 1,241 names are `candidate_`;
the rest have direct code evidence or come from code-shape rules checked against decompiled code.

## Credits

Some names and register descriptions were matched against the RadioFoundry project's DM-32 map and vector table
(MIT licence, see `THIRD_PARTY/RadioFoundry-LICENSE`).
