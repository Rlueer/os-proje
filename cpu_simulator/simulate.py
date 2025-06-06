import sys
import time
from cpu import CPU
from bios import load_and_parse_gtu_program

def dump_tcb(cpu, out):
    print("\n---- THREAD TABLE SNAPSHOT ----", file=out)
    print("\n---- THREAD TABLE SNAPSHOT ----", file=sys.stderr)
    

    # CPU özel yazmaçları
    reg_pc = cpu.memory[0] if 0 < len(cpu.memory) else 0
    reg_sp = cpu.memory[1] if 1 < len(cpu.memory) else 0
    syscall_result = cpu.memory[2] if 2 < len(cpu.memory) else 0
    instr_executed = cpu.memory[3] if 3 < len(cpu.memory) else 0
    print(f"CPU_REGS -> PC={reg_pc}, SP={reg_sp}, SYSCALL_RET_PC={syscall_result}, IE={instr_executed}", file=out)
    print(f"CPU_REGS -> PC={reg_pc}, SP={reg_sp}, SYSCALL_RET_PC={syscall_result}, IE={instr_executed}", file=sys.stderr)


    # TCB yapısı: Her 10 hücrede bir TCB (ID, State, PC, SP, UnblockIE, StartIE, UsedIE + 3 boş)
    tcb_bases = [20, 30, 40, 50, 100, 107, 114, 121, 128, 135, 142]  # TCB başlangıç adresleri
    
    for i, base in enumerate(tcb_bases):
        if base < len(cpu.memory):
            tid = i  # Thread ID = index
            state = cpu.memory[base + 1] if (base + 1) < len(cpu.memory) else 0
            saved_pc = cpu.memory[base + 2] if (base + 2) < len(cpu.memory) else 0
            saved_sp = cpu.memory[base + 3] if (base + 3) < len(cpu.memory) else 0
            unblock_ie = cpu.memory[base + 4] if (base + 4) < len(cpu.memory) else 0
            starting_ie = cpu.memory[base + 5] if (base + 5) < len(cpu.memory) else 0
            used_ie = cpu.memory[base + 6] if (base + 6) < len(cpu.memory) else 0
            
            line = f"TCB[{tid}] -> State={state}, PC={saved_pc}, SP={saved_sp}, UnblockIE={unblock_ie}, StartIE={starting_ie}, UsedIE={used_ie}"
            print(line, file=out)
            print(line, file=sys.stderr)

    print("--------------------------------", file=out)
    print("--------------------------------", file=sys.stderr)

def dump_memory(cpu, out):
    print("\n--- MEMORY DUMP ---", file=out)
    print("\n--- MEMORY DUMP ---", file=sys.stderr)
    for addr, val in enumerate(cpu.memory):
        if val != 0:
            line = f"mem[{addr}] = {val}"
            print(line, file=out)
            print(line, file=sys.stderr)
    print("--- END OF DUMP ---", file=out)
    print("--- END OF DUMP ---", file=sys.stderr)

def dump_memory_regions(cpu, out):
    regions = [
        (0, 150),
        (1000, 2000),
        (2000, 3000),
        (3000, 4000),
    ]
    for start, end in regions:
        header = f"-- Memory {start}-{end-1} --"
        print(header, file=out)
        print(header, file=sys.stderr)
        for i in range(start, end):
            if i < len(cpu.memory):
                val = cpu.memory[i]
                if val != 0:
                    line = f"mem[{i}] = {val}"
                    print(line, file=out)
                    print(line, file=sys.stderr)

def main():
    if len(sys.argv) != 4 or sys.argv[2] != "-D":
        print("Usage: python simulate.py <filename.gtu> -D <debug_mode>")
        sys.exit(1)

    filename = sys.argv[1]
    debug_mode = int(sys.argv[3])
    if debug_mode not in (0, 1, 2, 3):
        print("Debug mode must be 0, 1, 2, or 3")
        sys.exit(1)

    data, instr = load_and_parse_gtu_program(filename)
    cpu = CPU()
    cpu.load_program_to_memory(data, instr)

    last_syscall = -1
    last_thread = -1

    debug_filenames = {
        0: "debug0_output.txt",
        1: "debug1_output.txt",
        2: "debug2_output.txt",
        3: "debug3_output.txt"
    }
    debug_file_path = debug_filenames[debug_mode]

    with open(debug_file_path, "w") as debug_file:
        while not cpu.is_halted:
            if debug_mode == 1:
                current_pc = cpu.pc
                current_instruction = cpu.memory[current_pc] if current_pc < len(cpu.memory) else "UNKNOWN"
                header = f"[INSTRUCTION] PC={current_pc}, Executing: {current_instruction}"
                print(header, file=debug_file)
                print(header, file=sys.stderr)
                print("[MEMORY_DUMP]", file=debug_file)
                print("[MEMORY_DUMP]", file=sys.stderr)
                dump_memory_regions(cpu, debug_file)
                print("", file=debug_file)
                print("", file=sys.stderr)

            elif debug_mode == 2:
                header = f"[IE {cpu.instructions_executed}] Press ENTER to step"
                print(header, file=debug_file)
                print(header, file=sys.stderr)
                input()
                print("[MEMORY_DUMP]", file=debug_file)
                print("[MEMORY_DUMP]", file=sys.stderr)
                dump_memory_regions(cpu, debug_file)

            elif debug_mode == 3:
                current_pc = cpu.pc
                next_instr = cpu.memory[current_pc] if current_pc < len(cpu.memory) else -1
                thread_id = cpu.memory[15] if 15 < len(cpu.memory) else -1

                is_syscall_instr = any(
                    str(next_instr).startswith(str(op)) for op in [97, 98, 99]  # SYSCALL ops
                )

                if thread_id != last_thread or (is_syscall_instr and thread_id != 0):
                    dump_tcb(cpu, debug_file)
                    last_thread = thread_id


            cpu.run_cycle()

        if debug_mode == 0:
            dump_memory_regions(cpu, debug_file)

if __name__ == "__main__":
    main()
