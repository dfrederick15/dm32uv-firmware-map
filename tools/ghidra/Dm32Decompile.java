// Decompiles functions and writes C to a file, using the program's decompiler options.
// Usage: -postScript Dm32Decompile.java <out.c> name1 name2 ...
//        -postScript Dm32Decompile.java <out.c> --all
// Each function starts with a line "//@@ <address> <name> body=<bytes>" so the output can be split by tools.
//@category DM32
import ghidra.app.decompiler.*;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import java.io.*;
import java.nio.file.*;
import java.util.*;

public class Dm32Decompile extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        DecompileOptions opts = new DecompileOptions();
        opts.grabFromProgram(currentProgram);
        DecompInterface d = new DecompInterface();
        d.setOptions(opts);
        d.openProgram(currentProgram);
        boolean all = args.length > 1 && args[1].equals("--all");
        Set<String> want = new HashSet<>(Arrays.asList(args).subList(1, args.length));
        int done = 0, failed = 0;
        try (BufferedWriter out = Files.newBufferedWriter(Paths.get(args[0]))) {
            for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
                if (!all && !want.contains(f.getName())) continue;
                if (monitor.isCancelled()) break;
                DecompileResults r = d.decompileFunction(f, 60, monitor);
                out.write("//@@ " + f.getEntryPoint() + " " + f.getName() + " body=" + f.getBody().getNumAddresses() + "\n");
                if (r.decompileCompleted()) {
                    out.write(r.getDecompiledFunction().getC());
                    done++;
                } else {
                    out.write("// failed: " + r.getErrorMessage() + "\n");
                    failed++;
                }
                out.write("\n");
            }
        }
        d.dispose();
        println("decompiled " + done + ", failed " + failed);
    }
}
