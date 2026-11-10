// Compares Ghidra's disassembly with a reference list of "address mnemonic" lines (for example from GNU objdump)
// and reports agreement, missing instructions and the most common mnemonic differences.
// Usage: -postScript Dm32CheckDisasm.java <reference.txt> [<report.txt>]
//@category DM32

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Instruction;

import java.io.*;
import java.nio.file.*;
import java.util.*;

public class Dm32CheckDisasm extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        List<String> lines = Files.readAllLines(Paths.get(args[0]));
        int same = 0, differ = 0, none = 0;
        Map<String, Integer> diffs = new HashMap<>();
        Map<String, Integer> missing = new HashMap<>();
        StringBuilder missList = new StringBuilder();
        for (String l : lines) {
            String[] p = l.trim().split("\\s+");
            if (p.length < 2) {
                continue;
            }
            Address a = toAddr(Long.parseLong(p[0], 16));
            Instruction ins = getInstructionAt(a);
            if (ins == null) {
                none++;
                missing.merge(p[1], 1, Integer::sum);
                missList.append(p[0]).append(' ').append(p[1]).append('\n');
                continue;
            }
            String g = ins.getMnemonicString().toLowerCase();
            if (g.equals(p[1]) || g.replace("16", "").replace("32", "").equals(p[1])) {
                same++;
            } else {
                differ++;
                diffs.merge(p[1] + " -> " + g, 1, Integer::sum);
            }
        }
        StringBuilder out = new StringBuilder();
        out.append(String.format("reference %d: same %d, different %d, not disassembled %d%n", same + differ + none, same, differ, none));
        out.append("top differences:\n");
        diffs.entrySet().stream().sorted((x, y) -> y.getValue() - x.getValue()).limit(30)
            .forEach(e -> out.append("  ").append(e.getValue()).append("  ").append(e.getKey()).append("\n"));
        out.append("not disassembled, by reference mnemonic:\n");
        missing.entrySet().stream().sorted((x, y) -> y.getValue() - x.getValue()).limit(30)
            .forEach(e -> out.append("  ").append(e.getValue()).append("  ").append(e.getKey()).append("\n"));
        println(out.toString());
        if (args.length > 1) {
            Files.writeString(Paths.get(args[1]), out.toString());
        }
        if (args.length > 2) {
            Files.writeString(Paths.get(args[2]), missList.toString());
        }
    }
}
