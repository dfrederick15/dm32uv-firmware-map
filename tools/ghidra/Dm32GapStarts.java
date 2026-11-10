// For a reference list of "address mnemonic operands" lines in address order, reports where Ghidra's
// disassembly stops: each reference instruction that is not disassembled although the previous one is.
// Usage: -postScript Dm32GapStarts.java <reference.txt> <report.txt>
//@category DM32

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Instruction;
import java.nio.file.*;
import java.util.*;

public class Dm32GapStarts extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        StringBuilder out = new StringBuilder();
        boolean prevHad = false;
        String prevText = "";
        long prevAddr = -10;
        for (String l : Files.readAllLines(Paths.get(args[0]))) {
            String[] p = l.trim().split("\\s+", 3);
            if (p.length < 2) continue;
            long a = Long.parseLong(p[0], 16);
            Instruction ins = getInstructionAt(toAddr(a));
            boolean contiguous = a - prevAddr <= 4;
            if (ins == null && prevHad && contiguous) {
                Instruction pi = getInstructionAt(toAddr(prevAddr));
                out.append(String.format("%x\t%s\t|after\t%s%n", a, l.trim().substring(p[0].length()).trim(), pi == null ? prevText : pi.toString()));
            }
            prevHad = ins != null;
            prevText = l;
            prevAddr = a;
        }
        Files.writeString(Paths.get(args[1]), out.toString());
    }
}
