# main.py
import sys
from cpu_simulator.cpu import CPU
from cpu_simulator.bios import load_and_parse_gtu_program

def main():
    if len(sys.argv) < 2:
        print("Kullanım: python main.py <gtu_dosya_yolu>")
        sys.exit(1)

    program_filepath = sys.argv[1]
    # Proje dokümanında debug modu da belirtiliyor ama onu daha sonra ekleyeceğiz.
    # debug_mode = -1 # Varsayılan olarak debug kapalı
    # if len(sys.argv) > 2 and sys.argv[2].startswith("-D"):
    # try:
    # debug_mode = int(sys.argv[2][2:])
    # except ValueError:
    # print(f"Geçersiz debug modu: {sys.argv[2]}")

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
    max_execution_cycles = 1000 # Güvenlik için maksimum döngü sayısı
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
        print(f"  OS Sistem Çağrısı Tipi: {my_cpu.memory[CPU.MEM_OS_SYSCALL_TYPE]}") # OS syscall tipini de yazdıralım

        # İsteğe bağlı: Belleğin belirli bir kısmını dök
        # print("\nSon Bellek Durumu (Örnek Adresler):")
        # print(f"  Mem[0-3]: PC={my_cpu.memory[CPU.REG_PC]}, SP={my_cpu.memory[CPU.REG_SP]}, SR={my_cpu.memory[CPU.REG_SYSCALL_RESULT]}, IE={my_cpu.memory[CPU.REG_INSTR_EXECUTED]}")
        # if 200 < len(my_cpu.memory) : print(f"  Mem[200]: {my_cpu.memory[200]}")
        # if 202 < len(my_cpu.memory) : print(f"  Mem[202]: {my_cpu.memory[202]}")


if __name__ == "__main__":
    main()