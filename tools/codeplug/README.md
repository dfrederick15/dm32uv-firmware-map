# Codeplug tools

Work on DM-32UV CPS codeplug files (`.data`). Nothing here talks to a radio.

| Script | Use |
| --- | --- |
| `codeplug_diff.py` | Compare two `.data` files page by page; changed bytes are labelled by block, record and known field |
| `codeplug_edit.py` | Make a modified copy of a `.data` file (channel or block byte edits, optional bit mask) for checking in the official CPS |

```
python3 -I codeplug_diff.py before.data after.data
python3 -I codeplug_edit.py in.data out.data ch:7:0x1A:0x70=0x10 blk:0x04:0xA2=0x02
```

Field layouts are in `docs/codeplug-format.md`. Before writing any CPS-edited codeplug to a radio, diff it against a
fresh read: the official CPS's channel dialog can change tones, TX admit, scan lists and step sizes on channels that
were only browsed.
