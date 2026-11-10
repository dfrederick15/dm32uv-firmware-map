// Decompiles the named functions and writes C to a file, with body sizes. Usage: -postScript Dm32Decompile.java <out.c> name1 name2 ...
//@category DM32
import ghidra.app.decompiler.*;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import java.nio.file.*;
public class Dm32Decompile extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        DecompInterface d = new DecompInterface();
        DecompileOptions opts = new DecompileOptions();
        opts.grabFromProgram(currentProgram);
        d.setOptions(opts);
        d.openProgram(currentProgram);
        StringBuilder out = new StringBuilder();
        for (int i = 1; i < args.length; i++) {
            for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
                if (!f.getName().equals(args[i])) continue;
                DecompileResults r = d.decompileFunction(f, 60, monitor);
                out.append("// ").append(f.getName()).append(" @ ").append(f.getEntryPoint()).append(", body ").append(f.getBody().getNumAddresses()).append(" bytes\n");
                out.append(r.decompileCompleted() ? r.getDecompiledFunction().getC() : "// failed: " + r.getErrorMessage()).append("\n");
            }
        }
        Files.writeString(Paths.get(args[0]), out.toString());
    }
}
