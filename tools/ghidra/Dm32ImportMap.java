// Sets up a DM-32UV DM32.NRF.01.049 program in Ghidra from the static-analysis tables.
// Adds memory blocks (RAM image, second SRAM, bootloader, peripherals), creates and names every function,
// adds plate comments with the evidence for each name, names RAM variables and modem registers, types the
// vector table, menu state table and key handler tables, and bookmarks the data regions.
//
// Usage (headless, as a pre-script so auto-analysis runs afterwards):
//   analyzeHeadless <projectDir> <projectName> -import <split>/application.bin \
//     -loader BinaryLoader -loader-baseAddr 0x0300C000 -processor CSKY_V2:LE:32:default \
//     -preScript Dm32ImportMap.java <split-or-tables-dir> [<split-dir-with-bins>]
// The first argument is the folder holding the CSV tables; the second (default: same folder) holds the
// binary segments iram-init.bin, sahb-init.bin, bootloader.bin and boot-header.bin.
// Static analysis aid only.
//@category DM32

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.data.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import ghidra.program.model.symbol.*;

import java.io.*;
import java.nio.file.*;
import java.util.*;

public class Dm32ImportMap extends GhidraScript {

    private File tables;
    private File bins;
    private int created, renamed, comments, labels;

    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 1) {
            tables = askDirectory("Folder with the DM32 CSV tables", "Use");
        } else {
            tables = new File(args[0]);
        }
        bins = args.length > 1 ? new File(args[1]) : tables;

        setupMemory();
        typeTables();
        applyFunctions();
        applyRamNames();
        applyModemRegisters();
        applyTasks();
        bookmarkData();
        println(String.format("DM32 map: %d functions created, %d named, %d comments, %d labels", created, renamed, comments, labels));
    }

    // ---------------------------------------------------------------- memory

    private void setupMemory() throws Exception {
        Memory mem = currentProgram.getMemory();
        MemoryBlock app = mem.getBlock(toAddr(0x0300C000L));
        if (app != null) {
            app.setName("app_flash");
            app.setExecute(true);
            app.setWrite(false);
        }
        fileBlock("boot_header", 0x03000000L, "boot-header.bin", false, false);
        fileBlock("bootloader_flash", 0x03001000L, "bootloader.bin", true, false);
        long iramEnd = fileBlock("ram_init", 0x10000L, "iram-init.bin", true, true);
        if (iramEnd > 0 && iramEnd < 0x50000L) {
            emptyBlock("ram_bss_stack", iramEnd, 0x50000L - iramEnd, false);
        }
        emptyBlock("modem_regs", 0x11000000L, 0x10000L, true);
        emptyBlock("lcd_if", 0x12000000L, 0x100L, true);
        emptyBlock("usb", 0x13000000L, 0x1000L, true);
        String[][] periph = {
            {"timers", "0x14000000"}, {"watchdog", "0x14010000"}, {"gpio_a", "0x14020000"}, {"uart0_cable", "0x14030000"},
            {"uart1_gps", "0x14040000"}, {"uart2", "0x14050000"}, {"i2c0", "0x14060000"}, {"i2c1", "0x14070000"},
            {"i2c2_rtc", "0x14080000"}, {"uart3", "0x14090000"}, {"spi0_dataflash", "0x140A0000"}, {"spi1", "0x140B0000"},
            {"pwm", "0x140C0000"}, {"adc", "0x140D0000"}, {"spi2", "0x140E0000"}, {"dac", "0x140F0000"},
            {"gpio_b", "0x14100000"}, {"gpio_c", "0x14110000"}, {"spi3_efuse", "0x14150000"}};
        for (String[] p : periph) {
            emptyBlock(p[0], Long.decode(p[1]), 0x1000L, true);
        }
        emptyBlock("modem_buffers", 0x16000000L, 0x1000L, true);
        long sahbEnd = fileBlock("sram2_init", 0x18000800L, "sahb-init.bin", false, true);
        if (sahbEnd > 0 && sahbEnd < 0x18004C04L) {
            emptyBlock("sram2_bss", sahbEnd, 0x18004C04L - sahbEnd, false);
        }
    }

    private long fileBlock(String name, long start, String file, boolean exec, boolean write) throws Exception {
        File f = new File(bins, file);
        Memory mem = currentProgram.getMemory();
        if (!f.isFile()) {
            println("missing " + f + ", block " + name + " not created");
            return -1;
        }
        if (mem.getBlock(toAddr(start)) != null) {
            return start + f.length();
        }
        try (InputStream in = new FileInputStream(f)) {
            MemoryBlock b = mem.createInitializedBlock(name, toAddr(start), in, f.length(), monitor, false);
            b.setRead(true);
            b.setExecute(exec);
            b.setWrite(write);
        }
        return start + f.length();
    }

    private void emptyBlock(String name, long start, long size, boolean isVolatile) throws Exception {
        Memory mem = currentProgram.getMemory();
        if (mem.getBlock(toAddr(start)) != null) {
            return;
        }
        MemoryBlock b = mem.createUninitializedBlock(name, toAddr(start), size, false);
        b.setRead(true);
        b.setWrite(true);
        b.setVolatile(isVolatile);
    }

    // ---------------------------------------------------------------- tables

    private void typeTables() throws Exception {
        pointerArray(0x10000L, 99, "vector_table", "Vector table (VBR = 0x10000)");
        pointerArray(0x030B1184L, 126, "menu_state_table", "Menu state handlers: 18 screens x 7 slots (show, list move A/B, two transitions, confirm, back)");
        pointerArray(0x18000834L, 27, "key_press_handlers", "Per-key press handlers, PTT is key 1");
        pointerArray(0x180008A0L, 27, "key_release_handlers", "Per-key release handlers");
        pointerArray(0x1800090CL, 43, "key_function_handlers", "Programmable key function handlers (order matches the CPS key function list)");
        pointerArray(0x030728DCL, 43, "key_function_handlers_flash_image", "Flash image of key_function_handlers, copied to 0x1800090C");
    }

    private void pointerArray(long a, int n, String name, String note) {
        try {
            Address addr = toAddr(a);
            if (currentProgram.getMemory().getBlock(addr) == null) {
                return;
            }
            clearListing(addr, addr.add(4L * n - 1));
            createData(addr, new ArrayDataType(PointerDataType.dataType, n, 4));
            label(addr, name);
            setPlateComment(addr, note);
            comments++;
        } catch (Exception e) {
            println("table " + name + ": " + e.getMessage());
        }
    }

    // ---------------------------------------------------------------- functions

    private void applyFunctions() throws Exception {
        Map<String, Map<String, String>> evidence = new HashMap<>();
        for (Map<String, String> r : readCsv("labels.csv")) {
            evidence.put(r.get("name"), r);
        }
        FunctionManager fm = currentProgram.getFunctionManager();
        for (Map<String, String> r : readCsv("functions.csv")) {
            Address a = toAddr(Long.decode(r.get("address")));
            if (currentProgram.getMemory().getBlock(a) == null) {
                continue;
            }
            String name = r.get("name");
            Function f = fm.getFunctionAt(a);
            if (f == null) {
                disassemble(a);
                f = createFunction(a, name);
                if (f != null) {
                    created++;
                }
            }
            if (f == null) {
                label(a, name);
                continue;
            }
            if (!name.startsWith("sub_")) {
                f.setName(name, SourceType.USER_DEFINED);
                renamed++;
            }
            StringBuilder c = new StringBuilder();
            Map<String, String> ev = evidence.get(name);
            if (ev != null) {
                c.append(ev.getOrDefault("evidence", "")).append("\n");
                c.append("basis: ").append(ev.getOrDefault("match_method", "")).append(" / ").append(ev.getOrDefault("source", ""));
                if (name.startsWith("candidate_")) {
                    c.append(" (inferred)");
                }
                c.append("\n");
            }
            append(c, "module", r.get("module"));
            append(c, "hardware", r.get("hardware"));
            append(c, "tasks", r.get("reached_by_tasks"));
            append(c, "direct callers", r.get("direct_callers"));
            if ("no".equals(r.get("reachable"))) {
                c.append("no known caller\n");
            }
            if (c.length() > 0) {
                f.setComment(c.toString().trim());
                comments++;
            }
        }
    }

    private void append(StringBuilder c, String k, String v) {
        if (v != null && !v.isEmpty()) {
            c.append(k).append(": ").append(v).append("\n");
        }
    }

    // ---------------------------------------------------------------- data names

    private void applyRamNames() throws Exception {
        for (Map<String, String> r : readCsv("ram-names.csv")) {
            Address a = toAddr(Long.decode(r.get("address")));
            if (label(a, r.get("name"))) {
                setPreComment(a, r.get("confidence") + ": " + r.get("basis"));
            }
        }
    }

    private void applyModemRegisters() throws Exception {
        for (Map<String, String> r : readCsv("modem-registers.csv")) {
            long off = Long.decode(r.get("offset_from_0x11000000"));
            String n = r.get("documented_name");
            if (n == null || n.isEmpty()) {
                n = String.format("MODEM_REG_%03X", off);
            }
            Address a = toAddr(0x11000000L + off);
            if (label(a, n)) {
                setEOLComment(a, "reads " + r.get("reads") + ", writes " + r.get("writes"));
            }
        }
    }

    private void applyTasks() throws Exception {
        for (Map<String, String> r : readCsv("tasks.csv")) {
            String ep = r.get("entry_point");
            if (ep == null || !ep.startsWith("0x")) {
                continue;
            }
            Address a = toAddr(Long.decode(ep));
            String note = "uC/OS-III task \"" + r.get("os_task_name") + "\", created by " + r.get("created_by");
            Function f = getFunctionAt(a);
            if (f != null) {
                String old = f.getComment();
                f.setComment(note + (old == null ? "" : "\n" + old));
            } else {
                setPlateComment(a, note);
            }
        }
    }

    private void bookmarkData() throws Exception {
        for (Map<String, String> r : readCsv("data-map-program.csv")) {
            Address a = toAddr(Long.decode(r.get("start")));
            if (currentProgram.getMemory().getBlock(a) != null) {
                createBookmark(a, "DM32 data", r.get("kind") + " (" + r.get("bytes") + " bytes)");
            }
        }
        for (Map<String, String> r : readCsv("images.csv")) {
            Address a = toAddr(Long.decode(r.get("address")));
            createBookmark(a, "DM32 image", r.get("width") + "x" + r.get("height") + " " + r.get("format"));
            label(a, String.format("icon_%sx%s_%x", r.get("width"), r.get("height"), a.getOffset()));
        }
    }

    private boolean label(Address a, String name) {
        try {
            if (currentProgram.getMemory().getBlock(a) == null || name == null || name.isEmpty()) {
                return false;
            }
            createLabel(a, name, true, SourceType.USER_DEFINED);
            labels++;
            return true;
        } catch (Exception e) {
            println("label " + name + " at " + a + ": " + e.getMessage());
            return false;
        }
    }

    // ---------------------------------------------------------------- csv

    private List<Map<String, String>> readCsv(String file) throws IOException {
        List<Map<String, String>> rows = new ArrayList<>();
        Path p = new File(tables, file).toPath();
        if (!Files.exists(p)) {
            println("missing table " + p);
            return rows;
        }
        List<String> lines = Files.readAllLines(p);
        if (lines.isEmpty()) {
            return rows;
        }
        List<String> head = split(lines.get(0));
        StringBuilder pending = new StringBuilder();
        for (int i = 1; i < lines.size(); i++) {
            pending.append(pending.length() > 0 ? "\n" : "").append(lines.get(i));
            if (quoteCount(pending) % 2 != 0) {
                continue; // quoted field spans lines
            }
            List<String> v = split(pending.toString());
            pending.setLength(0);
            Map<String, String> m = new HashMap<>();
            for (int k = 0; k < head.size(); k++) {
                m.put(head.get(k), k < v.size() ? v.get(k) : "");
            }
            rows.add(m);
        }
        return rows;
    }

    private int quoteCount(CharSequence s) {
        int n = 0;
        for (int i = 0; i < s.length(); i++) {
            if (s.charAt(i) == '"') {
                n++;
            }
        }
        return n;
    }

    private List<String> split(String line) {
        List<String> out = new ArrayList<>();
        StringBuilder cur = new StringBuilder();
        boolean q = false;
        for (int i = 0; i < line.length(); i++) {
            char ch = line.charAt(i);
            if (q) {
                if (ch == '"' && i + 1 < line.length() && line.charAt(i + 1) == '"') {
                    cur.append('"');
                    i++;
                } else if (ch == '"') {
                    q = false;
                } else {
                    cur.append(ch);
                }
            } else if (ch == '"') {
                q = true;
            } else if (ch == ',') {
                out.add(cur.toString());
                cur.setLength(0);
            } else {
                cur.append(ch);
            }
        }
        out.add(cur.toString());
        return out;
    }
}
