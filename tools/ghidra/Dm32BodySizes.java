// Writes "entry name body_bytes" for every function. Usage: -postScript Dm32BodySizes.java <out.txt>
//@category DM32
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import java.nio.file.*;
public class Dm32BodySizes extends GhidraScript {
    @Override
    protected void run() throws Exception {
        StringBuilder sb = new StringBuilder();
        for (Function f : currentProgram.getFunctionManager().getFunctions(true))
            sb.append(Long.toHexString(f.getEntryPoint().getOffset())).append(' ').append(f.getName()).append(' ').append(f.getBody().getNumAddresses()).append('\n');
        Files.writeString(Paths.get(getScriptArgs()[0]), sb.toString());
    }
}
