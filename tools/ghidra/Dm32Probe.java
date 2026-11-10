// Prints instruction details, flow and p-code at the given addresses. Usage: -postScript Dm32Probe.java addr...
//@category DM32
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.pcode.PcodeOp;
public class Dm32Probe extends GhidraScript {
    @Override
    protected void run() throws Exception {
        for (String s : getScriptArgs()) {
            var a = toAddr(Long.decode(s));
            Instruction i = getInstructionAt(a);
            Function f = getFunctionContaining(a);
            println("@" + a + " fn=" + (f == null ? "-" : f.getName()) + " ins=" + i
                + (i == null ? " data=" + getDataAt(a) : " len=" + i.getLength() + " flow=" + i.getFlowType() + " fall=" + i.getFallThrough() + " override=" + i.getFlowOverride()));
            if (i != null) for (PcodeOp op : i.getPcode()) println("    " + op);
        }
    }
}
