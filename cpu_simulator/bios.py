# cpu_simulator/bios.py

def load_and_parse_gtu_program(filepath):
    """
    Verilen .gtu dosyasını okur, veri ve komut segmentlerini ayrıştırır.
    Dönüş: (data_segment, instruction_segment) tuple'ı
           data_segment = [(adres, değer), ...]
           instruction_segment = [(adres, "KOMUT STRING"), ...]
    """
    data_segment = []
    instruction_segment = []
    
    in_data_section = False
    in_instruction_section = False

    try:
        with open(filepath, 'r') as f:
            for line_number, raw_line in enumerate(f, 1):
                line = raw_line.strip()

                # Yorumları ve boş satırları atla
                if not line or line.startswith('#'):
                    continue

                # Yorumları satır sonundan temizle
                if '#' in line:
                    line = line.split('#', 1)[0].strip()
                    if not line: # Eğer yorumdan sonra bir şey kalmadıysa
                        continue

                # Bölüm belirteçlerini kontrol et
                if line.upper() == "BEGIN DATA SECTION":
                    in_data_section = True
                    in_instruction_section = False
                    continue
                elif line.upper() == "END DATA SECTION":
                    in_data_section = False
                    continue
                elif line.upper() == "BEGIN INSTRUCTION SECTION":
                    in_instruction_section = True
                    in_data_section = False
                    continue
                elif line.upper() == "END INSTRUCTION SECTION":
                    in_instruction_section = False
                    continue

                # Bölümlere göre ayrıştırma
                if in_data_section:
                    try:
                        # Format: adres=değer veya adres değer (boşlukla ayrılmış)
                        if '=' in line:
                            addr_str, val_str = line.split('=', 1)
                        else:
                            parts = line.split(None, 1) # İlk boşluğa göre ayır
                            if len(parts) != 2:
                                print(f"BIOS Warning: Invalid data format in {filepath} at line {line_number}: '{raw_line.strip()}'")
                                continue
                            addr_str, val_str = parts
                        
                        address = int(addr_str.strip())
                        value = int(val_str.strip())
                        data_segment.append((address, value))
                    except ValueError:
                        print(f"BIOS Warning: Could not parse data line in {filepath} at line {line_number}: '{raw_line.strip()}'")
                
                elif in_instruction_section:
                    try:
                        # Format: adres: KOMUT ARG1 ARG2
                        if ':' not in line:
                            print(f"BIOS Warning: Invalid instruction format (missing ':') in {filepath} at line {line_number}: '{raw_line.strip()}'")
                            continue
                        
                        addr_str, instr_str = line.split(':', 1)
                        address = int(addr_str.strip())
                        instruction = instr_str.strip().upper() # Komutları büyük harf yapalım
                        instruction_segment.append((address, instruction))
                    except ValueError:
                        print(f"BIOS Warning: Could not parse instruction line in {filepath} at line {line_number}: '{raw_line.strip()}'")
                        
    except FileNotFoundError:
        print(f"BIOS Error: File not found at '{filepath}'")
        return None, None # Veya hata yükselt
        
    return data_segment, instruction_segment

# bios.py dosyasını test etmek için basit bir ana blok (opsiyonel)
if __name__ == '__main__':
    # Test için gtu_c312_programs altına test_bios.gtu adında bir dosya oluşturun
    # Örnek test_bios.gtu içeriği:
    # Begin Data Section
    # 0=100
    # 1=1023
    # End Data Section
    # Begin Instruction Section
    # 100: SET 50, 200
    # 101: HLT
    # End Instruction Section

    # Bu yolu kendi projenizdeki dosya yoluna göre güncelleyin
    test_file_path = "gtu_c312_programs/test_programs/test_bios_simple.gtu"
    
    # Önce test_bios_simple.gtu dosyasını oluşturun:
    # gtu_c312_programs/test_bios_simple.gtu
    # Begin Data Section
    # 0=100
    # 1=1023
    # 250=77
    # End Data Section
    # Begin Instruction Section
    # 100: SET 50, 200
    # 101: CPY 250, 202
    # 102: HLT
    # End Instruction Section
    
    print(f"Attempting to parse: {test_file_path}")
    data, instructions = load_and_parse_gtu_program(test_file_path)

    if data is not None and instructions is not None:
        print("\n--- Parsed Data Segment ---")
        for addr, val in data:
            print(f"Address: {addr}, Value: {val}")
        
        print("\n--- Parsed Instruction Segment ---")
        for addr, instr in instructions:
            print(f"Address: {addr}, Instruction: '{instr}'")
    else:
        print("Failed to parse the .gtu file.")