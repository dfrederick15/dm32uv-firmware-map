"""Print decompiled C for named functions from an all.c file, without the plate comments.
Usage: python3 -I show_c.py <all.c> name [name ...]"""
import re, sys
text = open(sys.argv[1], errors="replace").read()
parts = re.split(r"^//@@ (\S+) (\S+) body=(\d+)\n", text, flags=re.M)
want = set(sys.argv[2:])
for i in range(1, len(parts), 4):
    if parts[i + 1] in want:
        c = re.sub(r"/\*.*?\*/\n?", "", parts[i + 3], flags=re.S)
        c = "\n".join(l for l in c.splitlines() if l.strip())
        print(f"// {parts[i+1]} @ {parts[i]} ({parts[i+2]} bytes)\n{c}\n")
