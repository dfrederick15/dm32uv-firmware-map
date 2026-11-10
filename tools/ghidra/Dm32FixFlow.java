// Repairs code flow after auto-analysis of the DM32 firmware:
//  1. clears wrongly inferred "no return" flags (CPU_SR_Restore is called everywhere and does return),
//  2. disassembles at reference instruction addresses inside known function bodies that Ghidra did not reach
//     (code after calls to those functions, and switch cases behind unresolved jump tables), skipping padding,
//     coprocessor/DSP words and anything already defined as data,
//  3. recomputes every function body.
// Usage: -postScript Dm32FixFlow.java <reference.txt>   (lines: "address mnemonic operands", e.g. from objdump)
//@category DM32

import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.cmd.function.CreateFunctionCmd;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.*;

import java.nio.file.*;
import java.util.*;

public class Dm32FixFlow extends GhidraScript {
    private static final Set<String> SKIP = new HashSet<>(Arrays.asList(
        "bkpt", "cprgr", "cpwgr", "cprcr", "cpwcr", "cpop", "bloop", "ldcpr", "stcpr"));

    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        FunctionManager fm = currentProgram.getFunctionManager();
        int cleared = 0;
        for (Function f : fm.getFunctions(true)) {
            if (f.hasNoReturn()) {
                f.setNoReturn(false);
                cleared++;
            }
        }
        // Analysis marks some bsr call sites CALL_RETURN or CALL_TERMINATOR (after a function was once thought
        // non-returning). GCC for C-SKY never tail-calls with bsr, so every call gets normal flow back.
        int overrides = 0;
        for (Instruction ins : currentProgram.getListing().getInstructions(true)) {
            FlowOverride fo = ins.getFlowOverride();
            if (fo != FlowOverride.NONE && ins.getMnemonicString().toLowerCase().startsWith("bsr")) {
                ins.setFlowOverride(FlowOverride.NONE);
                overrides++;
            }
        }
        // Flash and initial-image blocks are read-only so the decompiler folds literal-pool constants.
        for (ghidra.program.model.mem.MemoryBlock b : currentProgram.getMemory().getBlocks()) {
            String n = b.getName();
            if (n.equals("app_flash") || n.equals("bootloader_flash") || n.equals("boot_header")) {
                b.setWrite(false);
            }
            println("block " + n + " " + b.getStart() + " r" + b.isRead() + " w" + b.isWrite() + " x" + b.isExecute() + " v" + b.isVolatile());
        }
        println("flow overrides cleared " + overrides);
        List<String[]> ref = new ArrayList<>();
        for (String l : Files.readAllLines(Paths.get(args[0]))) {
            String[] p = l.trim().split("\\s+", 3);
            if (p.length >= 2) ref.add(p);
        }
        Listing listing = currentProgram.getListing();
        long seeded = 0;
        for (int pass = 0; pass < 6; pass++) {
            AddressSet seeds = new AddressSet();
            for (String[] p : ref) {
                if (SKIP.contains(p[1])) continue;
                Address a = toAddr(Long.parseLong(p[0], 16));
                if (listing.getInstructionAt(a) != null) continue;
                if (listing.getDefinedDataContaining(a) != null) continue;
                if (listing.getInstructionContaining(a) != null) continue; // middle of a decoded instruction
                seeds.add(a);
            }
            if (seeds.isEmpty()) break;
            long before = currentProgram.getListing().getNumInstructions();
            for (Address a : seeds.getAddresses(true)) {
                if (listing.getInstructionAt(a) == null && listing.getDefinedDataContaining(a) == null
                        && listing.getInstructionContaining(a) == null) {
                    new DisassembleCommand(a, null, true).applyTo(currentProgram, monitor);
                }
            }
            long added = currentProgram.getListing().getNumInstructions() - before;
            seeded += added;
            println("pass " + pass + ": seeds " + seeds.getNumAddresses() + ", new instructions " + added);
            if (added == 0) break;
        }
        // Literal pools inside the application code range hold constants: mark them so the decompiler folds them.
        int constants = 0;
        ghidra.program.model.address.AddressSet code = new ghidra.program.model.address.AddressSet(toAddr(0x0300C000L), toAddr(0x030727C7L));
        code.add(toAddr(0x10000L), toAddr(0x2F0B3L));
        for (Data d : currentProgram.getListing().getDefinedData(code, true)) {
            if (d.getLength() == 4 && (d.isPointer() || d.getDataType().getName().toLowerCase().contains("word"))) {
                ghidra.program.model.data.MutabilitySettingsDefinition.DEF.setChoice(d, ghidra.program.model.data.MutabilitySettingsDefinition.CONSTANT);
                constants++;
            }
        }
        println("literal pool words marked constant: " + constants);
        int fixed = 0;
        for (Function f : fm.getFunctions(true)) {
            if (CreateFunctionCmd.fixupFunctionBody(currentProgram, f, monitor)) fixed++;
        }
        println("bsr flow overrides cleared: " + overrides);
        println(String.format("DM32 flow fix: no-return cleared %d, instructions added %d, bodies recomputed %d", cleared, seeded, fixed));
    }
}
