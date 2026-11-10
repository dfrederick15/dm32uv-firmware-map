# DM-32UV memory map, firmware `DM32.NRF.01.049`

Addresses, sizes and layouts from a static analysis of the program flash and data flash. Names starting with
`candidate_` are inferences; everything else has direct code evidence. Nothing here was tested on hardware.

SoC: HR_C7000 (C-SKY CK803S core, ABIv2). RF chip: FD6818. Program flash: 1 MiB. Data flash: 16 MiB SPI NOR.

## CPU address space

| Range | Contents | Basis |
| --- | --- | --- |
| `0x00010000-0x0004FFFF` | Main RAM, range used by the firmware (256 KiB): vectors, RAM code, data, BSS, stacks | startup copy and zero loops |
| `0x03000000-0x030FFFFF` | Program flash, executed in place | boot header entry, literal pools |
| `0x11000000-0x1100FFFF` | Modem / baseband registers (`WORK_MODE`, `AUDIO_CONTROL`, interrupt status, layer 2, RF mode) | 70 functions read or write it |
| `0x12000000` | LCD controller interface (ST7789-type commands) | `lcd_init` and draw routines |
| `0x13000000` | USB controller (no direct register references found) | peripheral map |
| `0x14000000-0x1415FFFF` | Peripherals, 64 KiB apart (table below) | driver code |
| `0x16000000-0x16000FFF` | Modem buffer RAM: TX/RX frame RAM, voice RAM at `0x16000960` | `txram_copy`, `rxram_copy`, `voice_ram_*` |
| `0x18000800-0x18004C03` | Second SRAM ("SAHB"): callback tables and codec tables copied from flash | startup copy loop |

### Peripherals

| Base | Block | Notes |
| --- | --- | --- |
| `0x14000000` | Timers | OS tick and five general timers (vectors 33-38) |
| `0x14010000` | Watchdog | |
| `0x14020000` | GPIO A | vector 47 |
| `0x14030000` | UART0 | programming cable, vector 44 |
| `0x14040000` | UART1 | GPS, vector 42 |
| `0x14050000` | UART2 | one reference |
| `0x14060000` | I2C0 | one reference |
| `0x14070000` | I2C1 | no references |
| `0x14080000` | I2C2 | real-time clock |
| `0x14090000` | UART3 | one reference |
| `0x140A0000` | SPI0 | data flash |
| `0x140B0000` | SPI1 | SD card driver present, apparently unused |
| `0x140C0000` | PWM | no direct references |
| `0x140D0000` | ADC | analog inputs |
| `0x140E0000` | SPI2 | no direct references |
| `0x140F0000` | DAC | TX level |
| `0x14100000` | GPIO B | vector 46; rotary encoder |
| `0x14110000` | GPIO C | vector 49 |
| `0x14150000` | SPI3 | candidate eFuse / OTP reads |

Bit-banged buses on GPIO: FD6818 three-wire control, RDA5807 FM receiver I2C (pins `0x19`/`0x1A`), and the ALPU-MP
licence chip (pins `0x05`/`0x06`), which only the AMBE codec calls.

### Interrupts

Vector base is `0x10000`. 18 handlers are installed at run time; every other vector goes to a common entry or a stub.

| Vector | Handler |
| --- | --- |
| 33 | OS tick |
| 34-38 | Timers 2-6 |
| 42 | GPS UART |
| 44 | Programming-cable UART |
| 46, 47, 49 | GPIO banks B, A, C |
| 59 | PCM playback (speaker) |
| 60 | PCM capture (microphone) |
| 61 | Modem system interrupt (status snapshot, deferred handling) |
| 62, 63 | TX slot, RX slot (30 ms DMR slot timing) |
| 64, 65 | RF switch to TX, RF switch to RX |

## Program flash (1 MiB)

Runtime address = `0x03000000` + flash offset.

| Flash offset | Runtime | Size | Contents |
| --- | --- | --- | --- |
| `0x000000-0x000FFF` | `0x03000000` | 4 KiB | Boot header: ROM boot flag and entry address, then padding |
| `0x001000-0x00AFFF` | `0x03001000` | 40 KiB | Bootloader (update mode). Most of it is copied to RAM `0x10000-0x12A5F` from flash `0x1F48` and runs there |
| `0x00B000-0x00BFFF` | `0x0300B000` | 4 KiB | Information page: factory option bits at `+0x80..+0x82` (GPS, recording, ...), model byte at `+0xA0`. The only program-flash page the application writes, and only from the cable task |
| `0x00C000-0x0727C7` | `0x0300C000` | 410 KiB | Application code, executed in place (modules below) |
| `0x0727D0-0x076BD3` | `0x030727D0` | 17 KiB | Initial image of the second SRAM (copied to `0x18000800`) |
| `0x076BD4-0x0C0C37` | `0x03076BD4` | 296 KiB | Read-only data: UI strings (English and GB2312), icons, fonts, menu tables, lookup tables |
| `0x0C0C38-0x0DFCEB` | `0x030C0C38` | 124 KiB | Initial image of main RAM (copied to `0x10000`) |
| `0x0DFCEC-0x0E14EB` | | 6 KiB | End of the application image, not classified |
| `0x0E14EC-0x0FFFFF` | | | Not part of the image |

### Application code modules

Ranges are approximate: module boundaries were assigned from callers, strings and hardware use.

| Runtime range | Functions | Module |
| --- | ---: | --- |
| `0x0300C000-0x0300C0E3` | | Reset entry and exception stubs |
| `0x0300C0E4-0x0300C903` | 71 | OS wrappers and signal helpers |
| `0x0300C904-0x0300F03B` | 88 | Modem and RF control |
| `0x0300F03C-0x0301104B` | 63 | Codeplug storage layer (tagged pages in data flash) |
| `0x0301104C-0x03012D2B` | 27 | GPS |
| `0x03012D2C-0x03017883` | 162 | Keys and programmable key functions |
| `0x03017884-0x0301B00F` | 97 | Display drawing |
| `0x0301B010-0x0301E47F` | 91 | Board support: power, GPIO, timers, UART, ADC, DAC |
| `0x0301E480-0x0302A447` | 263 | DMR call control and layer 2 |
| `0x0302A448-0x0302B823` | 8 | Programming cable protocol |
| `0x0302B824-0x03035E17` | 186 | Call display, channel and codeplug logic |
| `0x03035E18-0x03059447` | 518 | Menu system |
| `0x03059448-0x0305C1DF` | 55 | Text input |
| `0x0305C1E0-0x030643C3` | 174 | Radio state, LEDs, records, sound |
| `0x030643C4-0x03066EFF` | 76 | Broadcast FM receiver and miscellaneous |
| `0x03066F00-0x030678EF` | 22 | SD card over SPI1 (apparently unused) |
| `0x030678F0-0x03068E53` | 37 | RF chip (FD6818) setup |
| `0x03068E54-0x0306E0BB` | 142 | uC/OS-III kernel (flash part) |
| `0x0306E0BC-0x030727C7` | 89 | C library and soft-float |

### Notable read-only tables

| Runtime address | Contents |
| --- | --- |
| `0x030728DC` | Programmable key function table, 43 entries (copied to `0x1800090C`) |
| `0x03079400-0x0307EAFF` | Largest GB2312 string block |
| `0x030B1184` | Menu state table: 126 handlers, 18 screens of 7 slots |
| `0x030B8B60-0x030BCC10` | Menu page descriptors (276), with English and Chinese string arrays |
| various | 40 RGB565 icons, 16x16 to 48x41 pixels |

## Main RAM (`0x10000-0x4FFFF`)

| Range | Contents |
| --- | --- |
| `0x10000-0x1018B` | Vector table (VBR) |
| `0x1018C-0x14157` | uC/OS-III kernel and CPU port |
| `0x14164-0x16CDB` | Audio and codec glue: PCM interrupts, encoder and decoder tasks |
| `0x16CDC-0x2B2D1` | AMBE+2 codec (vocoder, FEC, ALPU-MP calls) |
| `0x2B2DC-0x2F0B3` | Real-time drivers and handlers: data flash, RF chip bus, interrupt handlers, voice rings |
| `0x2F0B4-0x4A7DF` | Zeroed data (BSS), about 110 KiB |
| `0x4A7E0-0x4FFFF` | Free space below the initial stack pointer `0x50000` |

The bootloader uses `0x10000-0x12A5F` for its own RAM code before the application is started.

### Named RAM variables (selection)

| Address | Name | Notes |
| --- | --- | --- |
| `0x320C8` | menu stack and state | state byte at `+3`, refresh flag at `+4` |
| `0x35F1C`, `0x35F6C`, `0x36468` | slot timer, TX slot, RX slot semaphores | posted from interrupts |
| `0x3658C` | call event flags | |
| `0x3783C` | system interrupt semaphore | |
| `0x385AC` | RF switch semaphore | |
| `0x38D8C` | key message queue | |
| `0x39360`, `0x39468` | LCD/keypad bus lock, data flash lock | LCD DB0-DB4 double as keypad rows |
| `0x3C69C`, `0x3C7D8` | RX and TX burst rings (27-byte DMR voice bursts) | |
| `0x3C834` | TX queue entries | |
| `0x3E1F8` | Current channel record (copy of the flash record from `+0x10`) | RX frequency `+0`, TX `+4`, flags `+8` |
| `0x3E238`, `0x3E374` | VFO records, selected by settings `+0x2D` bit 7 | |
| `0x3E5E4` | Current menu handler | |
| `0x3E9D4` | Settings block in RAM | the most referenced variable (1,426 references) |
| `0x3FDB0` | System event flags | |
| `0x3FDD8` | Status flags | |
| `0x42531`, `0x426FC` | OS scheduler-lock and interrupt nesting counters | |
| `0x456E4`, `0x48184` | Codec decoder and encoder state | |
| `0x46A38`, `0x49A1C` | Decoder and encoder PCM buffers | |
| `0x46B80`, `0x4814C` | TX and RX voice rings | |

### Second SRAM (`0x18000800-0x18004C03`)

| Address | Contents |
| --- | --- |
| `0x18000804` | Key hook function pointer |
| `0x18000834` | Key press handler table |
| `0x180008A0` | Key release handler table |
| `0x1800090C` | Programmable key function table |
| `0x18000A8C`, `0x18000A90` | Cable receive and send function pointers |
| `0x18000B0A` | Text input method (candidate) |
| rest | Codec tables and other initialised data |

## Data flash (16 MiB)

| Range | Contents |
| --- | --- |
| `0x000000-0x000FFF` | Header page |
| `0x001000-0x0C8FFF` | Codeplug: 200 pages of 4 KiB, each tagged with a logical block number at `+0xFFF`. Physical placement varies; some pages hold leftover firmware fragments |
| `0x0C9000-0x148FFF` | 16-pixel fonts and Unicode / GB2312 character tables |
| `0x150000-0x1757FF` | Boot screen, 240x320 RGB565 little-endian |
| `0x180000-0x1F9FFF` | 24x24 Chinese font, 72 bytes per glyph |
| `0x201000-0x201FFF` | Voice prompt index, 16-byte records |
| `0x202000-0x264FFF` | 59 voice prompts, WAV 8 kHz 16-bit mono |
| `0x265000-0x277FFF` | 24x24 GB2312 symbol glyphs from row A1 (about 1,080), 72 bytes per glyph; the firmware reads rows A1-A5 from here |
| `0x278000-0x5AAFFF` | Contact (user ID) database: 16-byte header with the record count, then 92-byte records (name 16, a 4-byte value of unconfirmed meaning, callsign 8, city 16, state 16, country 32) |
| `0x5AB000-0x6DBFFF` | Zero or blank |
| `0x6DC000-0x6DEFFF` | Recording index area A (active sector tagged `0xA5` at `+0xFFF`) |
| `0x6DF000-0x6E4FFF` | Recording index area B |
| `0x6E5000-0xFFFFFF` | Recording audio area |

### Codeplug logical blocks

| Block | Contents |
| --- | --- |
| `0x02` | Calibration (unit-specific; can be written by stock adjust/test code) |
| `0x04` | Settings (loaded into RAM `0x3E9D4`) |
| `0x06` | Analog-side contact lists |
| `0x0B` | Read by menu and call display code; layout not worked out |
| `0x0F` | RX group lists |
| `0x10` | Encryption key table at `+0x300`: 44-byte entries (number, 10-byte name, type, 32-byte key), stored unencrypted |
| `0x11` | Scan lists |
| `0x12` onward | Channels: 48-byte records, 84 in the first block from `+0x20`, then 85 per block, up to 4,000 |
| `0x42` | TX contact per channel |
| `0x44` onward | Contacts |
| `0x5C` onward | Zones: 145-byte records (16-byte name, member count, up to 64 two-byte channel numbers), 28 per block |
| `0x67` | Radio IDs |

Channel record: 16-byte name, then RX frequency (`+0x10`), TX frequency (`+0x14`), flags (`+0x18`, bit 4 digital),
likely encryption key number (`+0x1E`, `0xFF` none), RX tone (`+0x21/0x22`). Squelch, timeout and admit criteria are
not yet located. The VFOs appear to use the reserved channel numbers 4015 and 4063 (inferred).

## Coverage

2,881 functions found: 2,172 in the application, 590 in RAM code and 119 in the bootloader (68 of them are small
leaf routines found in code gaps with no known caller). 1,653 have names, and 86.5% of direct call sites reach a named function. 1,045 names are inferred
(`candidate_`); code-shape rule names were checked against decompiled code.
