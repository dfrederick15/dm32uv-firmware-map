# Firmware notes, `DM32.NRF.01.049`

Static analysis only. Function names starting with `candidate_` are inferred; see `tables/labels.csv` for the basis of
each name. Memory layout is in `memory-map.md`.

## Overview

- Application version string `DM32.NRF.01.049`, dated 2022-06-27. The bootloader's update ID is `BFUV32-V2`.
- uC/OS-III with 38 distinct tasks (`tables/tasks.csv`).
- The AMBE+2 codec runs from RAM and calls an ALPU-MP licence chip over a bit-banged bus on GPIO pins `0x05`/`0x06`.
  All 12 calls to that bus come from inside the codec.
- The FD6818 RF chip's register numbers for RSSI, noise, deviation, tones and FSK match the BK4819 register map
  (an inference from register use).
- The display controller takes ST7789-type commands. The RDA5807 broadcast FM receiver is driven over bit-banged I2C on
  pins `0x19`/`0x1A`.

## Voice path

Transmit:

1. `capture_pcm_irq` collects microphone audio.
2. `task_encoder` waits on its task semaphore and calls `codec_encode` on 80-sample blocks.
3. `candidate_ambe_fec_encode` and `candidate_bits_pack` build 72-bit frames, three per 27-byte burst.
4. Clear voice goes to modem voice RAM (`0x16000960`) through `voice_ram_write`.
5. Encrypted voice goes through the ring at `0x46B80`. `task_encrypt` moves it to the ring at `0x3C7D8` every 60 ms.
6. `candidate_tx_slot_irq` posts semaphore `0x35F6C`, which wakes `task_txslot`.
7. `candidate_tx_burst_build` writes the burst through `txram_copy`.

Receive:

1. `system_irq_collect` saves the modem interrupt status to `0x3BEA0` and posts semaphore `0x3783C`.
2. `task_sysint` runs `candidate_sysint_dispatch`, and the deframers read modem RX RAM through `rxram_copy`.
3. `task_decoder` reads 27 bytes with `voice_ram_read`. Encrypted bursts first pass through `task_decrypt` and the
   rings at `0x3C69C` and `0x4A760`.
4. `candidate_bits_unpack` and `candidate_ambe_fec_decode` recover the frames, then `codec_decode` produces audio.
5. `play_pcm_irq` plays it.

## Transmit start and stop

- PTT press: `candidate_ptt_press_callback`, then `candidate_ptt_admission`, which checks whether transmit is allowed.
- Analog FM start: `candidate_analog_tx_start` calls `rf_tx_setup`, `fm_ptt_set` and the audio path functions.
- Stop: `candidate_tx_stop` sends command 1 to `candidate_call_control_event`.
- DMR timing: `candidate_call_control_event` and `modem_state_event_set` signal the modem state worker. Slot activity
  then runs from interrupts through `task_txslot`.
- RF switching: `rf_tx_irq` and `rf_rx_irq` post semaphore `0x385AC`, which wakes `rf_switch_worker`. It runs
  `rf_tx_switch` or `rf_rx_restore`, including the band select and `tx_level_ramp`.
- User-visible start and end of a transmission run as deferred events in `task_psint`, posted by the modem state
  machine.

## Modem configuration

| Situation | Function | Writes |
| --- | --- | --- |
| FM mode | `candidate_modem_fm_mode_setup` | `RF_MODE = 0x10E0`, `WORK_MODE = 0x80` |
| DMR mode | `candidate_modem_dmr_mode_setup` | `LAYER2_SLOTON = 0x11`, `RF_MODE` bit changes, `WORK_MODE = 0x6E` |
| Microphone capture | `capture_pcm_enable` / `capture_pcm_disable` | `AUDIO_CONTROL` bit 4 |
| Speaker playback | `play_pcm_enable` / `play_pcm_disable` | `AUDIO_CONTROL` bit 5 |
| FM playback | `fm_play_enable` | `AUDIO_CONTROL` bit 6 |
| DMR burst | `candidate_tx_burst_build` | `LAYER2_SEND_TYPE`, then `LAYER2_TXRX_CTRL` bit 7 (transmit next slot) |
| Layer 2 stop | `candidate_modem_layer2_stop` | `LAYER2_CONTROL = 0`, `LAYER2_TXRX_CTRL = 0` |

`tables/modem-registers.csv` lists 77 used registers with their readers and writers.

## Receive interrupt dispatch

`candidate_sysint_dispatch` reads the saved `SYS_INTERP_LIST` value at `0x3BEA0`.

| Bit | Event | Handler |
| --- | --- | --- |
| 1 | Layer 2 RX processing point | `candidate_rx_slot_ready_handler` |
| 2 | Voice late entry | `candidate_late_entry_rx_handler` |
| 3 | Burst deframed | `candidate_burst_rx_handler` |
| 4 | Short LC received | `candidate_short_lc_rx_handler` |
| 6 | RX slot boundary abnormal | `candidate_rx_slot_abnormal_handler` |

The dispatcher skips all handlers when the mode byte at `0x3EC11` is 2 or 4.

## Keys and menus

- `candidate_key_event_dispatch` calls per-key handlers from a press table (`0x18000834`) and a release table
  (`0x180008A0`), 27 keys each. PTT is key 1.
- The 43 programmable key functions sit in a table at `0x1800090C`. They are named by position against the
  programmable-key list; spot checks fit, but the pairing is not verified.
- The menu state table at `0x030B1184` has 126 states: 18 screens of 7 slots. The slots are show, list move (two),
  two small transitions, confirm and back.
- `candidate_menu_key_handler` switches on 25 key event codes (0-24) through a jump table at `0x030B0F64`.

## Codeplug

- Pages in data flash carry their logical block number in the last byte of each 4 KiB page.
- Channels: 48-byte records (16-byte name first), 84 in block `0x12` from `+0x20`, then 85 per block, up to 4,000.
  The RAM copy of the current channel at `0x3E1F8` starts at record `+0x10`: RX frequency, TX frequency, flags
  (bit 4 digital).
- Zones: 145-byte records from block `0x5C`, 28 per block: 16-byte name, member count, up to 64 channel numbers.
- The encryption key table in block `0x10` at `+0x300` is stored unencrypted: 44-byte entries with number, 10-byte name,
  type (`01` custom, `02` ARC4, `03` AES128, `04` AES256) and 32-byte key.
- The recording area starts at data flash `0x6DC000`, with two small index areas tagged `0xA5`/`0xA6` in the last byte
  of a sector.
- Some codeplug-area pages hold leftover fragments of a firmware image rather than codeplug data.

## Hardware notes

- `tables/gpio-map.csv` lists 50 pins. Pin `0x0A` (PTA10) is driven low by the GPS UART setup, probably the unused GPS
  transmit line (inference).
- Pin `0x17` (PTA23) is the chip select of an SD-over-SPI driver on SPI1. Its init has no known caller and no SD or file
  system text exists, so it is probably leftover code.
- Pin `0x3B` (FD6818 GPIO0): its interrupt is turned off during tuning.
- `task usb` does not touch the USB controller. It serves the programming cable and its commands such as `IDCHECK`.
- The bootloader is a uC/OS build linked to run from RAM (`0x10000-0x12A5F`); calling through its flash addresses breaks
  a flash-based call graph.

## Crypto, DTMF, CRCs

- ARC4 voice privacy runs in RAM code: an RC4 key schedule, keystream generators, and an XOR of 7 keystream bytes into
  each AMBE frame of a burst.
- DTMF: a key maps to row/column tone frequencies through tables at `0x030B8450`/`0x030B8458`.
- DMR data CRCs: CRC-32 (polynomial `0x04C11DB7`) and CRC-9. DCS codewords use the Golay (23,12) generator `0xC75`.

## Codec structure

- `codec_encode`: frame analysis (input filter, real-FFT spectrum, parameter estimation, refinement, tracking), a
  post step, then a four-part quantiser and bit packing.
- `codec_decode`: frame classification, unpacking and dequantisation, then two 80-sample synthesis calls (state update,
  enhancement, unvoiced synthesis with the MBE noise generator `x = 173x + 13849`, voiced synthesis).
- Shared fixed-point toolkit: radix-2 complex FFT with block floating point and real-FFT wrappers, log2/pow2 and root
  polynomials, an interpolated cosine table.

## Voice cipher

Internal cipher types: 1 ARC4, 2 a 64-bit block cipher compiled out (empty stubs), 4 AES-128, 5 AES-256. The AES code
(S-box `0x180011A4`, inverse S-box `0x180012A4`, Rcon `0x180013A0`) runs in OFB mode over an IV expanded by a 32-step
LFSR; the keystream is XORed into the AMBE frames.

## Bootloader flash driver

The bootloader carries the same program-flash erase (`0x20`) and page-program (`0x02`) routines as the application
(`boot_progflash_erase` at `0x03003E9C`, `boot_progflash_program` at `0x03003F60`), without the application's guard
flag.

## Program flash writes

The application has its own program-flash SPI driver in RAM (`candidate_progflash_erase`, `_program`, `_read`; commands
0x06, 0x20, 0x02, 0x05). Every write targets only the 4 KiB information page at `0x0300B000`, and only the cable task
(`task_usb`) reaches them. A guard byte at `0x18000A64` blocks all three. `candidate_feature_flags_load` copies option
bits from that page into the feature flags at `0x3FDE0`/`0x3FDE3`.

## Codeplug index blocks

- Block `0x0B` is the contact index: count at offset 0 (at most 800), then an ID-sorted index
  (`candidate_contact_name_by_id`).
- Contacts are 24-byte records, 170 per block from block `0x44`, with the 16-byte name at `+2`.

## Open questions

- 966 functions are still unnamed, mainly menu handlers, DMR call control, codec internals and the bootloader.
- Most settings have only weak hints for their meaning. Squelch, timeout and admit criteria in the channel record are not
  located.
- Which physical key drives menu slots 3 and 4, and the exact keypad-to-menu-event translation.
- Which control burst type each of the six DMR receive handlers serves.
