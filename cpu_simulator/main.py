# main.py
import sys
from cpu import CPU
from bios import load_and_parse_gtu_program

def main():
    if len(sys.argv) < 2:
        print("Kullanım: python main.py <gtu_dosya_yolu>")
        sys.exit(1)

    open("instructions_output.txt", "w", encoding="utf-8").close()
    open("output.txt", "w", encoding="utf-8").close()
    
    program_filepath = sys.argv[1]

    # Eğer kullanıcı 2. argüman olarak cycle sayısı girdiyse onu al
    max_execution_cycles = 1000  # Varsayılan değer
    if len(sys.argv) >= 3:
        try:
            max_execution_cycles = int(sys.argv[2])
        except ValueError:
            print(f"Geçersiz döngü sayısı: {sys.argv[2]}. Varsayılan 1000 kullanılacak.")

    print(f"GTU-C312 Simülatörü Başlatılıyor...")
    print(f"Program Dosyası: {program_filepath}")

    # 1. CPU örneğini oluştur
    my_cpu = CPU()

    # 2. BIOS ile programı ayrıştır
    data_segment, instruction_segment = load_and_parse_gtu_program(program_filepath)

    if data_segment is None or instruction_segment is None:
        print(f"Program yüklenemedi: {program_filepath}")
        sys.exit(1)
    
    # 3. Programı CPU belleğine yükle
    my_cpu.load_program_to_memory(data_segment, instruction_segment)
    
    print("\nCPU Çalıştırılıyor...")
    # 4. CPU'yu çalıştır
    current_cycles = 0
    try:
        while not my_cpu.is_halted and current_cycles < max_execution_cycles:
            my_cpu.run_cycle()
            current_cycles += 1
            # Debug modları burada devreye girecek (ileride)
            # if debug_mode == 1: my_cpu.dump_memory(...)
            # if debug_mode == 2: my_cpu.dump_memory(...); input("Devam etmek için Enter'a basın...")

        if current_cycles >= max_execution_cycles and not my_cpu.is_halted:
            print("\nMaksimum döngü sayısına ulaşıldı, CPU durdurulmadı. Programda sonsuz döngü olabilir.")
    except Exception as e:
        print(f"\nSimülasyon sırasında bir hata oluştu: {e}")
    finally:
        print("\nSimülasyon Durumu:")
        print(f"  CPU Durumu: {'DURDU (Halted)' if my_cpu.is_halted else 'ÇALIŞIYOR (Not Halted)'}")
        print(f"  Toplam Yürütülen Komut Sayısı: {my_cpu.instructions_executed}")
        print(f"  Program Sayacı (PC): {my_cpu.pc}")
        print(f"  Yığın İşaretçisi (SP): {my_cpu.sp}")
        print(f"  Sistem Çağrısı Sonucu: {my_cpu.syscall_result}")
        print(f"\nDEBUG - Kritik Memory Adresleri:")
        print(f"  memory[17] (saved_pc): {my_cpu.memory[17]}")
        print(f"  memory[30] (TCB2_PC): {my_cpu.memory[30]}")
        print(f"  memory[2] (syscall_result): {my_cpu.memory[2]}")
        print(f"  memory[15] (current_thread_id): {my_cpu.memory[15]}")
        print(f"  memory[16] (next_thread_id): {my_cpu.memory[16]}")
        print(f"  OS Sistem Çağrısı Tipi: {my_cpu.memory[CPU.MEM_OS_SYSCALL_TYPE]}") # OS syscall tipini de yazdıralım

        # İsteğe bağlı: Belleğin belirli bir kısmını dök
        # print("\nSon Bellek Durumu (Örnek Adresler):")
        # print(f"  Mem[0-3]: PC={my_cpu.memory[CPU.REG_PC]}, SP={my_cpu.memory[CPU.REG_SP]}, SR={my_cpu.memory[CPU.REG_SYSCALL_RESULT]}, IE={my_cpu.memory[CPU.REG_INSTR_EXECUTED]}")
        # if 200 < len(my_cpu.memory) : print(f"  Mem[200]: {my_cpu.memory[200]}")
        # if 202 < len(my_cpu.memory) : print(f"  Mem[202]: {my_cpu.memory[202]}")


if __name__ == "__main__":
    main()