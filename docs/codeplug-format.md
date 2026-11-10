# DM-32UV codeplug format notes (CPS `.data` files, firmware DM32.NRF.01.049)

Working notes from diffing official-CPS files and probe files made with `tools/codeplug_edit.py`. Field names that
come only from NeonPlug (github.com/infamy/NeonPlug, `src/radios/dm3x/structures.ts`) are marked (NP).

## File

A CPS `.data` file is a sequence of 4 KiB pages. The last byte of each page is the logical block number, the same
tag the radio stores in data flash; codeplug blocks are byte-identical to the radio's. Page 0 is a header with the
firmware string; a few untagged pages (0x00/0xFF) are CPS bookkeeping. Block 0x0B (contact index) is not in the file.

## Channel record (block 0x12 +0x10, 48 bytes; 84 in block 0x12, 85 per later block)

| Offset | Field | Source |
| --- | --- | --- |
| +0x00 | name, 16 bytes | CPS diff |
| +0x10 | RX frequency, BCD little-endian (10 Hz units) | CPS diff |
| +0x14 | TX frequency | CPS diff |
| +0x18 | bits 7-4 mode, bit 3 forbid TX, bits 2-1 power, bit 0 lone worker | NP |
| +0x19 | bit 7 wide (CPS diff), bit 6 scan add, bits 5-0 scan list | CPS diff, NP |
| +0x1A | bits 6-4 TX Admit: 0 Always, 1 Channel idle, 2 CC idle; bit 7 forbid talkaround (NP) | CPS diff |
| +0x1B | low bits: digital emergency system (2 shows "DEmer 2") | CPS probe P2 |
| +0x1C | bits 7-4 squelch level (CPS: 3 -> 9 observed), bits 3-2 APRS report (NP) | CPS diff |
| +0x1D | bits 3-0 colour code (shown, greyed, on analog channels too); NP: digital bit 4 slot, bit 5 TDMA direct, bit 6 short data confirm, bit 7 encryption | CPS probe P2, NP |
| +0x1E | encryption key number, 0xFF none | firmware + codeplug |
| +0x1F | digital: RX group list; analog: PTT ID (NP) | NP |
| +0x21 | RX tone, 2 bytes: low = ones<<4 \| tenths, high = hundreds<<4 \| tens; DCS high 0x80 (N) / 0xC0 (I); CPS writes FF FF for None; radio also accepts 00 00 | CPS diff + probe, NP |
| +0x23 | TX tone, same encoding | CPS probe P1 |
| +0x26 | bits 3-1 signalling type (2 = Two Tone); NP places signalling type in +0x27 bits 3-0, which the CPS probe does not support | CPS probe P2 |
| +0x29 | bits 3-2 PTT ID type (1 = BOT); NP places it in bits 7-4 | CPS probe P2 |
| +0x1A bit 3, +0x1C bits 1-0, +0x25 bits 3-0, +0x28 | no visible effect in the Channel Information dialog | CPS probe P2 |
| +0x25..0x2B (rest) | compander/VOX flags, RX squelch mode, step, encryption ID, TX radio ID index | NP |

Caution (CPS bug): a tone stored as `00 00` (no tone, valid for the radio) has no entry in the Channel Information
dialog, which shows the first list item, 60.0, and writes `00 06` (60.0 Hz) on OK. This hit RX and TX tones on
analog and digital channels alike. Set the field to None (writes `FF FF`) or leave with Cancel (writes nothing).
The dialog also appears stateful when stepping with Next/Previous: dropdowns such as TX Admit kept the previous
channel's value although the stored values differed. Fields shown this way are written back on OK, and also by Next/Previous: browsing channels with Next in one session
rewrote TX Admit, tones, a scan list (+0x19 low bits) and the step (+0x27 high nibble, 25 kHz -> 2.5 kHz) on every
channel passed. Browse with Cancel only, and diff before writing.

## Settings block (logical block 0x04)

| Offset | Field | Values | Source |
| --- | --- | --- | --- |
| +0x85 | bit 0 key lock mode: 0 Manual, 1 Auto (NP agrees) | | CPS diff, firmware setting 15 |
| +0x32 | menu exit time: seconds = 5 x value (4 = 20 s); NP places this at +0x36 | | CPS probe S1 |
| +0xA3 | VOX delay: seconds = value / 10 (10 = 1.0 s) | | CPS probe S1 |
| +0xA6 | analog mic level: shown as value + 1, range 1-5 | | CPS probe S1, firmware setting 85 |
| +0xA7 | digital mic level: 0-4 = levels 1-5, 5 = Enhance MIC1 (more Enhance options likely above) | | CPS probe S2, firmware setting 84 |
| +0xA5 | bits 1-0 tail noise reduction: 0 None, 1 120 deg, 2 180 deg, 3 55 Hz; other bits unidentified (bit 5 set in a stock codeplug) | | CPS probes S2, S2a |
| +0xA9 | no visible CPS field (values 3, 4, 7 tried) | | CPS probes S2, S2b |
| +0x45 | bit 0 Record (checkbox) | | CPS probes S3, S3b |
| +0x82 bits 1-0, +0xA8 bit 0 | no visible CPS field | | CPS probes S3, S3a, S3c, S3d |
| +0xA0 | TOT (TX timeout): 0 Off, n = 10 + 5n seconds (4 = 30 s, 22 = 120 s) | | CPS diff, firmware setting 3 |
| +0x1E | auto power-off | 0 off, 1 30 min, 2 1 h, 3 2 h, 4 4 h (firmware 049 maps 5 to 30 min) | CPS diff + firmware |
| +0x31 | backlight time | CPS wrote 4 -> 11 (more options than 0-5) | CPS diff |
| +0xA1 | TOT predict | 5 -> 10 observed | CPS diff |
| +0xA2 | VOX level | 0 off?, 1-5 | CPS diff + probe P1 |
| +0xA4 | bits 5-4 power save (3 -> 0 observed); bit 2 Weather alarm (1 on) | | CPS diffs 09, 18 |

Firmware links: VOX level is setting ID 58, backlight time 45, auto power-off 95 (see the firmware map tables).

Reading values in the CPS: settings checkboxes can also show stale values after switching files in one session (the
weather alarm read false for a codeplug that had it on). Open one file per fresh CPS session when reading back.
