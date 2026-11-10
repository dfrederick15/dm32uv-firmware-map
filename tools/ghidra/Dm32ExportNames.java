// Exports names and comments from the DM32 Ghidra project so edits made in Ghidra can be merged back into the tables.
// Writes two CSV files:
//   <out>-functions.csv : address, name, source, comment          (every function)
//   <out>-labels.csv    : address, name, source, block            (user-defined labels outside functions' entry points)
// Usage: -postScript Dm32ExportNames.java <out-prefix>
//@category DM32

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.*;

import java.nio.file.*;

public class Dm32ExportNames extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String prefix = getScriptArgs().length > 0 ? getScriptArgs()[0]
            : askFile("Export prefix (two CSV files are written)", "Export").getAbsolutePath();
        StringBuilder f = new StringBuilder("address,name,source,comment\n");
        for (Function fn : currentProgram.getFunctionManager().getFunctions(true)) {
            f.append(hex(fn.getEntryPoint().getOffset())).append(',')
             .append(q(fn.getName())).append(',')
             .append(fn.getSymbol().getSource()).append(',')
             .append(q(fn.getComment() == null ? "" : fn.getComment())).append('\n');
        }
        Files.writeString(Paths.get(prefix + "-functions.csv"), f.toString());

        StringBuilder l = new StringBuilder("address,name,source,block\n");
        SymbolTable st = currentProgram.getSymbolTable();
        for (Symbol s : st.getAllSymbols(true)) {
            if (s.getSymbolType() != SymbolType.LABEL || s.getSource() != SourceType.USER_DEFINED) continue;
            if (s.isExternal()) continue;
            if (getFunctionAt(s.getAddress()) != null) continue;
            MemoryBlock b = currentProgram.getMemory().getBlock(s.getAddress());
            l.append(hex(s.getAddress().getOffset())).append(',').append(q(s.getName())).append(',')
             .append(s.getSource()).append(',').append(b == null ? "" : b.getName()).append('\n');
        }
        Files.writeString(Paths.get(prefix + "-labels.csv"), l.toString());
        println("exported to " + prefix + "-functions.csv and -labels.csv");
    }

    private static String hex(long v) {
        return "0x" + Long.toHexString(v);
    }

    private static String q(String s) {
        if (s.contains(",") || s.contains("\"") || s.contains("\n")) return "\"" + s.replace("\"", "\"\"") + "\"";
        return s;
    }
}
