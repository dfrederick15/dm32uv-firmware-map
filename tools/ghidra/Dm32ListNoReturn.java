// Lists functions Ghidra marked as non-returning.
//@category DM32
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
public class Dm32ListNoReturn extends GhidraScript {
    @Override
    protected void run() throws Exception {
        for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
            if (f.hasNoReturn()) println("NORETURN " + f.getEntryPoint() + " " + f.getName() + " " + f.getBody().getNumAddresses());
        }
    }
}
