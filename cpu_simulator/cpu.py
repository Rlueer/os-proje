# cpu_simulator/cpu.py

class CPU:
    # ÖZEL BELLEK KONUMLARI (Sabitler olarak tanımlayabiliriz)
    REG_PC = 0
    REG_SP = 1
    REG_SYSCALL_RESULT = 2
    REG_INSTR_EXECUTED = 3
    # Adres 3-9 arası OS'ye veya diğer amaçlara ayrılmış olabilir.
    MEM_OS_SYSCALL_TYPE = 10      # Hangi syscall yapıldığını OS'ye bildirmek için
    MEM_OS_SYSCALL_HLT_HANDLER = 11 # OS'nin SYSCALL_HLT işleyicisinin adresi
    MEM_OS_SYSCALL_YIELD_HANDLER = 12 # OS'nin SYSCALL_YIELD işleyicisinin adresi
    MEM_OS_SYSCALL_PRN_HANDLER = 13 # Eğer PRN de OS'de işlenecekse (ama doküman C/C++ diyor)

    # Yığın için varsayılan sınırlar (OS bunları iplik bazlı değiştirebilir)
    # Bu sınırlar, yığının hangi bellek aralığında çalıştığını belirtir.
    # Örn: KERNEL yığını 999'dan aşağı doğru, USER iplik yığını 1999'dan aşağı doğru.
    # Şimdilik basit bir alt sınır (0) ve üst sınır (bellek sonu) kullanalım.
    # Daha iyi bir yaklaşım, SP'nin başlangıç değerini bilmek ve onun altına inmemesini sağlamaktır.
    # Veya her iplik için ayrılan bellek segmentinin sonundan başlatıp segmentin başına kadar izin vermek.
    # Şimdilik _is_valid_address SP'nin genel bellek sınırlarını zaten kontrol ediyor.
    # Spesifik stack overflow/underflow için SP'nin belirli bir aralıkta kalmasını sağlamalıyız.
    # Bu proje için SP'nin başlangıç değeri program tarafından data segmentinde memory[1] e yazılır.
    # PUSH yaptıkça azalır, POP yaptıkça artar.
    # Stack Overflow: SP, ipliğe ayrılan yığın alanının altına inerse.
    # Stack Underflow: SP, ipliğe ayrılan yığın alanının ilk ayarlanan SP değerinin üzerine çıkarsa.
    # Bu kontrolleri PUSH ve POP içine ekleyeceğiz. OS yüklendiğinde her thread için
    # stack_base ve stack_limit değerlerini ayarlayabilir. Şimdilik genel bir kontrol yapalım.


    def __init__(self, memory_size=11000): # Proje dokümanındaki adres aralığını kapsasın
        # Bellek: Basit bir byte listesi (veya int listesi, sayılarımız long integer olacağı için)
        # Proje dokümanı sayıların "signed long integers" olduğunu belirtiyor.
        # Python'ın tamsayıları zaten keyfi hassasiyete sahip olduğu için bu konuda endişelenmemize gerek yok.
        self.memory = [0] * memory_size
        
        # Bellek Eşlemeli Yazmaçlar (Memory-Mapped Registers)
        # Bu yazmaçlar aslında belleğin ilk birkaç hücresidir.
        # PC (Program Counter) -> Bellek Adresi 0
        # SP (Stack Pointer) -> Bellek Adresi 1
        # SR (System Call Result) -> Bellek Adresi 2
        # NUM_INSTRUCTIONS (Number of Instructions Executed) -> Bellek Adresi 3
        
        # CPU Durumları
        self.is_halted = False
        self.mode = "KERNEL"  # Başlangıçta KERNEL modunda

        # Proje dokümanında belirtilen diğer olası yazmaçlar/bellek alanları (3-20)
        # Şimdilik bunları doğrudan kullanmayabiliriz ama yerleri belli.
        
        # OS'nin syscall handler adreslerini ve yığın sınırlarını başlangıçta
        # data segmentinde ayarlaması beklenir. Testler için varsayılanlar:
        self.memory[CPU.MEM_OS_SYSCALL_HLT_HANDLER] = 0 # OS bu adresi kendi HLT handler'ı ile güncellemeli
        self.memory[CPU.MEM_OS_SYSCALL_YIELD_HANDLER] = 0 # OS bu adresi kendi YIELD handler'ı ile güncellemeli
        
        # Her iplik için yığın sınırları OS tarafından yönetilmeli.
        # Testler için varsayılan SP'yi (memory[1]) kullanacağız.
        # self.current_thread_stack_base = 0 # İpliğin yığın başlangıcı (en yüksek adres)
        # self.current_thread_stack_limit = 0 # İpliğin yığın sonu (en düşük adres)

        print("GTU-C312 CPU initialized.")

    @property
    def pc(self):
        return self.memory[CPU.REG_PC]

    @pc.setter
    def pc(self, value):
        self.memory[CPU.REG_PC] = value

    @property
    def sp(self):
        return self.memory[CPU.REG_SP]

    @sp.setter
    def sp(self, value):
        self.memory[CPU.REG_SP] = value

    @property
    def syscall_result(self):
        return self.memory[CPU.REG_SYSCALL_RESULT]

    @syscall_result.setter
    def syscall_result(self, value):
        self.memory[CPU.REG_SYSCALL_RESULT] = value

    @property
    def instructions_executed(self):
        return self.memory[CPU.REG_INSTR_EXECUTED]

    @instructions_executed.setter
    def instructions_executed(self, value):
        self.memory[CPU.REG_INSTR_EXECUTED] = value
    
    def _is_valid_address(self, address, operation_type="access"):
        """Bellek adresinin geçerli olup olmadığını ve erişim haklarını kontrol eder."""
        #print(f"DEBUG: Checking address {address} for {operation_type}, Mode: {self.mode}")  # EKLE
    
        if not (0 <= address < len(self.memory)):
            print(f"Error: {operation_type.capitalize()} to invalid memory address {address}. Halting.")
            self.is_halted = True
            return False
        
        if self.mode == "USER" and address < 1000:
            print(f"Error: USER mode attempted to {operation_type} protected memory address {address}. Thread will be shut down. Halting.")
            self.is_halted = True # OS bunu daha sofistike yönetecek
            return False
        return True
    
    # DEĞİŞTİRİLDİ
    def _fetch(self):
        """
        Program Sayacının (PC) gösterdiği adresten bir sonraki komutu alır.
        Şimdilik komutların string olarak bellekte saklandığını varsayalım.
        BIOS yüklerken komutları bu şekilde yerleştirecek.
        """
        instruction_address = self.pc
        # Artık _is_valid_address ile hem sınırları hem de USER mod erişimini kontrol ediyoruz.
        if not self._is_valid_address(instruction_address, "fetch from"): 
             return None
        
        # Komutlarımızın program dosyasında "KOMUT PARAM1 PARAM2" formatında olacağını varsayıyoruz.
        # BIOS bunları belleğe string olarak veya ayrıştırılmış bir formatta yükleyebilir.
        # Şimdilik string olarak tutalım.
        instruction_str = self.memory[instruction_address]
        # print(f"Fetched from addr {instruction_address}: {instruction_str}") # Debug
        return instruction_str

# DEĞİŞTİRİLDİ 6 (CPYI2 eklendi, syscall'lar güncellendi, PUSH/POP'a yığın kontrolü eklendi)
    def _decode_execute(self, instruction_str):
        """
        Alınan komut string'ini çözer ve yürütür.
        CPYI2 eklendi.
        SYSCALL'lar OS'ye tipini ve sonucunu/parametrelerini bildirecek şekilde güncellendi.
        PUSH/POP komutlarına temel yığın sınırı kontrolleri eklendi.
        SYSCALL_HLT ve SYSCALL_YIELD OS handler'larına PC'yi yönlendiriyor.
        """
        print(f"[DECODE_EXECUTE] PC={self.pc} -> '{instruction_str}' Mode={self.mode} | SysRes={self.syscall_result} | IE={self.instructions_executed}")

        if not instruction_str or not isinstance(instruction_str, str):
            print(f"Warning: Invalid instruction format or empty instruction at PC {self.pc}. Halting.")
            self.is_halted = True
            return

        parts = instruction_str.strip().upper().split()
        command = parts[0]
        args = [arg.rstrip(',') for arg in parts[1:]] 

        executed_successfully = False
        pc_incremented_by_command = False
        
        original_mode_before_syscall = self.mode # Sadece bilgilendirme amaçlı, dönüşü OS yönetir.

        if command.startswith("SYSCALL"):
            self.mode = "KERNEL"

        if command == "HLT":
            self.is_halted = True
            return 
        elif command == "SET":
            # ... (SET kodu aynı) ...
            if len(args) == 2:
                try:
                    value_to_set = int(args[0]) 
                    memory_address = int(args[1])
                    if self._is_valid_address(memory_address, "write to"):
                        print(f"[SET] memory[{memory_address}] = {value_to_set}")

                        self.memory[memory_address] = value_to_set
                        executed_successfully = True
                        if memory_address == CPU.REG_PC: # Eğer PC'ye yazılıyorsa
                            pc_incremented_by_command = True # PC zaten komutla değişti
                except ValueError: # ...
                    print(f"Error: Invalid arguments for SET: {args}. Halting.")
                    self.is_halted = True
            else: # ...
                print(f"Error: SET requires 2 arguments, got {len(args)}. Halting.")
                self.is_halted = True
        elif command == "CPY":
            # ... (CPY kodu aynı) ...
            if len(args) == 2:
                try:
                    source_address = int(args[0])
                    dest_address = int(args[1])
                    if self._is_valid_address(source_address, "read from") and \
                       self._is_valid_address(dest_address, "write to"):
                        print(f"[CPY] memory[{dest_address}] = memory[{source_address}] ({self.memory[dest_address]})")

                        self.memory[dest_address] = self.memory[source_address]
                        executed_successfully = True
                            # DÜZELTME: Eğer hedef adres PC ise, PC manuel olarak değiştirilmiş demektir
                        if dest_address == CPU.REG_PC:  # PC = memory[0]
                            pc_incremented_by_command = True
                except ValueError: # ...
                    print(f"Error: Invalid arguments for CPY: {args}. Halting.")
                    self.is_halted = True
                except Exception as e: # Genel hata yakalama (opsiyonel debug için)
                     print(f"Unexpected error in CPY: {e}. Halting.")
                     self.is_halted = True
            else: # ...
                print(f"Error: CPY requires 2 arguments, got {len(args)}. Halting.")
                self.is_halted = True
        elif command == "CPYI":
            # ... (CPYI kodu aynı) ...
            if len(args) == 2:
                try:
                    pointer_address = int(args[0]) 
                    dest_address = int(args[1])   
                    if self._is_valid_address(pointer_address, "read from (pointer for CPYI)") and \
                       self._is_valid_address(dest_address, "write to (CPYI)"):
                        source_address_via_pointer = self.memory[pointer_address] 
                        if self._is_valid_address(source_address_via_pointer, "read from (indirect for CPYI)"):
                            self.memory[dest_address] = self.memory[source_address_via_pointer]
                            executed_successfully = True
                except ValueError: # ...
                    print(f"Error: Invalid arguments for CPYI: {args}. Halting.")
                    self.is_halted = True
            else: # ...
                print(f"Error: CPYI requires 2 arguments, got {len(args)}. Halting.")
                self.is_halted = True
        # YENİ EKLENEN KOMUT
        elif command == "CPYI2": # Format: CPYI2 A1 A2 (memory[memory[A2]] = memory[memory[A1]])
            if len(args) == 2:
                try:
                    pointer_addr1 = int(args[0]) # A1: Kaynak işaretçisini tutan adres
                    pointer_addr2 = int(args[1]) # A2: Hedef işaretçisini tutan adres

                    # Tüm seviyeler için adres ve erişim kontrolü
                    if self._is_valid_address(pointer_addr1, "read pointer1 for CPYI2") and \
                       self._is_valid_address(pointer_addr2, "read pointer2 for CPYI2"):
                        
                        source_addr_via_ptr1 = self.memory[pointer_addr1] # İşaretçi1'in gösterdiği asıl kaynak adresi
                        dest_addr_via_ptr2 = self.memory[pointer_addr2]   # İşaretçi2'nin gösterdiği asıl hedef adresi

                        if self._is_valid_address(source_addr_via_ptr1, "read indirect source for CPYI2") and \
                           self._is_valid_address(dest_addr_via_ptr2, "write indirect dest for CPYI2"):
                            
                            self.memory[dest_addr_via_ptr2] = self.memory[source_addr_via_ptr1]
                            executed_successfully = True
                except ValueError:
                    print(f"Error: Invalid arguments for CPYI2: {args}. Halting.")
                    self.is_halted = True
            else:
                print(f"Error: CPYI2 requires 2 arguments, got {len(args)}. Halting.")
                self.is_halted = True
        
        elif command == "ADD":
            # ... (ADD kodu aynı) ...
            if len(args) == 2:
                try:
                    memory_address = int(args[0]) 
                    value_to_add = int(args[1])   
                    if self._is_valid_address(memory_address, "read/write for ADD"):
                        self.memory[memory_address] += value_to_add
                        executed_successfully = True
                except ValueError: # ...
                    print(f"Error: Invalid arguments for ADD: {args}. Halting.")
                    self.is_halted = True
            else: # ...
                print(f"Error: ADD requires 2 arguments, got {len(args)}. Halting.")
                self.is_halted = True
        elif command == "ADDI":
            # ... (ADDI kodu aynı) ...
            if len(args) == 2:
                try:
                    dest_address = int(args[0])         
                    source_val_address = int(args[1])   
                    if self._is_valid_address(dest_address, "read/write for ADDI") and \
                       self._is_valid_address(source_val_address, "read from for ADDI"):
                        self.memory[dest_address] += self.memory[source_val_address]
                        executed_successfully = True
                except ValueError: # ...
                    print(f"Error: Invalid arguments for ADDI: {args}. Halting.")
                    self.is_halted = True
            else: # ...
                print(f"Error: ADDI requires 2 arguments, got {len(args)}. Halting.")
                self.is_halted = True
        elif command == "SUBI":
            # ... (SUBI kodu aynı) ...
            if len(args) == 2:
                try:
                    address1 = int(args[0]) 
                    address2 = int(args[1]) 
                    if self._is_valid_address(address1, "read from for SUBI (A1)") and \
                       self._is_valid_address(address2, "read/write for SUBI (A2)"):
                        self.memory[address2] = self.memory[address1] - self.memory[address2]
                        executed_successfully = True
                except ValueError: # ...
                    print(f"Error: Invalid arguments for SUBI: {args}. Halting.")
                    self.is_halted = True
            else: # ...
                print(f"Error: SUBI requires 2 arguments, got {len(args)}. Halting.")
                self.is_halted = True
        elif command == "JIF":
            # ... (JIF kodu aynı) ...
            if len(args) == 2:
                try:
                    condition_address = int(args[0]) 
                    jump_target_address = int(args[1]) 
                    if self._is_valid_address(condition_address, "read from for JIF condition"):
                        condition_value = self.memory[condition_address]
                        if condition_value <= 0:
                            self.pc = jump_target_address
                            pc_incremented_by_command = True 
                        executed_successfully = True 
                except ValueError: # ...
                    print(f"Error: Invalid arguments for JIF: {args}. Halting.")
                    self.is_halted = True
            else: # ...
                print(f"Error: JIF requires 2 arguments, got {len(args)}. Halting.")
                self.is_halted = True
        # YENİ EKLENEN KOMUTLAR
        elif command == "PUSH": 
            if len(args) == 1:
                try:
                    source_address = int(args[0])
                    # Yığın sınırı kontrolü (basit): SP, 0'ın altına inmemeli (veya iplik yığın alanı alt sınırı)
                    # Daha gelişmiş kontrol için ipliğe özel yığın sınırları (limit ve base) gerekir.
                    # Şimdilik, _is_valid_address(self.sp - 1) zaten SP'nin 0'ın altına inmesini engeller.
                    # Ek olarak, SP'nin belirli bir alt sınırı (örn: iplik için ayrılan segment başı) geçmemesini sağlamalıyız.
                    # Bu proje kapsamında OS, ipliklerin SP'lerini ve yığınlarını yönetecek.
                    # CPU sadece SP'nin geçerli bir bellek adresi olup olmadığını kontrol eder.
                    # "Stack Overflow" mantığı daha çok OS seviyesinde anlam kazanır.
                    # CPU için, SP'nin yazacağı adres geçerli mi ona bakarız.
                    
                    if self._is_valid_address(source_address, "read from for PUSH"):
                        value_to_push = self.memory[source_address]
                        potential_sp = self.sp - 1
                        if self._is_valid_address(potential_sp, "write to stack for PUSH"): # Yazılacak yığın adresi geçerli mi?
                            self.sp = potential_sp # SP'yi sadece adres geçerliyse güncelle
                            self.memory[self.sp] = value_to_push
                            executed_successfully = True
                        # else: Hata _is_valid_address içinde zaten verildi.
                except ValueError:
                    print(f"Error: Invalid argument for PUSH: {args}. Halting.")
                    self.is_halted = True
            else:
                print(f"Error: PUSH requires 1 argument, got {len(args)}. Halting.")
                self.is_halted = True

        elif command == "POP": 
            if len(args) == 1:
                try:
                    dest_address = int(args[0])
                    # Yığın sınırı kontrolü (basit): SP, yığının başlangıçta ayarlandığı "base" değerini geçmemeli.
                    # Bu, programın mantığına ve SP'nin başlangıç değerine bağlıdır.
                    # Eğer self.sp, ipliğin yığın için ayrılan alanının başlangıç (en yüksek) adresindeyse, POP yapılamaz (underflow).
                    # CPU için, SP'nin okuyacağı adres geçerli mi ona bakarız.
                    if self._is_valid_address(self.sp, "read from stack for POP"): # Okunacak yığın adresi geçerli mi?
                        value_popped = self.memory[self.sp]
                        # self.sp += 1 # SP'yi artırmadan önce hedef adresin geçerliliğini kontrol et
                        if self._is_valid_address(dest_address, "write to for POP"):
                            self.memory[dest_address] = value_popped
                            self.sp += 1 # Sadece başarılı yazma sonrası SP'yi artır
                            executed_successfully = True
                        # else: Hedef adres hatası _is_valid_address içinde verildi.
                    # else: SP okuma hatası _is_valid_address içinde verildi.
                except ValueError:
                    print(f"Error: Invalid argument for POP: {args}. Halting.")
                    self.is_halted = True
            else:
                print(f"Error: POP requires 1 argument, got {len(args)}. Halting.")
                self.is_halted = True

        elif command == "CALL": # Format: CALL C (Dönüş adresini yığına it, PC = C yap)
            if len(args) == 1:
                try:
                    jump_target_address = int(args[0])
                    return_address = self.pc + 1 # Bir sonraki komutun adresi

                    self.sp -= 1 # Yığın aşağı doğru büyür
                    if self._is_valid_address(self.sp, "write return address to stack for CALL"):
                        print(f"[CALL] SP={self.sp+1} -> SP={self.sp}, Return Addr={return_address}, Jump To={jump_target_address}")

                        self.memory[self.sp] = return_address
                        self.pc = jump_target_address
                        pc_incremented_by_command = True
                        executed_successfully = True
                    else:
                        self.sp += 1 # Başarısız olursa SP'yi geri al
                        print(f"Error: Stack Pointer ({self.sp+1} -> {self.sp}) points to invalid/protected memory for CALL. Halting.")
                        self.is_halted = True
                except ValueError:
                    print(f"Error: Invalid argument for CALL: {args}. Halting.")
                    self.is_halted = True
            else:
                print(f"Error: CALL requires 1 argument, got {len(args)}. Halting.")
                self.is_halted = True

        elif command == "RET": # Format: RET (Yığından dönüş adresini çek, PC'yi ona ayarla)
            if not args: # Argüman almaz
                print(f"[RET] Trying to pop return address from SP={self.sp}")
                if self._is_valid_address(self.sp, "read return address from stack for RET"):
                    return_address = self.memory[self.sp]
                    self.sp += 1 # SP artar
                    print(f"[RET] Returning to address {return_address}, SP={self.sp}")
                    self.pc = return_address
                    pc_incremented_by_command = True
                    executed_successfully = True
                else:
                    print("[RET] Invalid SP address!")
            else:
                print(f"Error: RET does not take arguments, got {len(args)}. Halting.")
                self.is_halted = True

        elif command == "USER": # Format: USER A (CPU'yu USER moduna geçir, PC = memory[A])
            if len(args) == 1:
                try:
                    address_containing_new_pc = int(args[0])
                    if self._is_valid_address(address_containing_new_pc, "read new PC address for USER"):
                        print(f"--------------------- USER MODE'a geciliyor (Thread ID: {self.memory[15]})")
                        new_pc_value = self.memory[address_containing_new_pc]
                        self.mode = "USER"
                        self.pc = new_pc_value
                        pc_incremented_by_command = True
                        executed_successfully = True
                        print(f"Switched to USER mode. New PC = {self.pc} (hedef adres: {address_containing_new_pc} iceriginden)")
                    # else: Adres gecersizse _is_valid_address icinde durdurulur.
                except ValueError:
                    print(f"Error: Invalid argument for USER: {args}. Halting.")
                    self.is_halted = True
            else:
                print(f"Error: USER requires 1 argument, got {len(args)}. Halting.")
                self.is_halted = True
        
        elif command == "SYSCALL_PRN": 
            if len(args) == 1:
                try:
                    address_to_print = int(args[0])
                    if self._is_valid_address(address_to_print, "read for SYSCALL_PRN"):
                            # 1. Değeri oku ve Python'da konsola yazdır (Proje gereksinimi)
                        value_to_print = self.memory[address_to_print]
                        print("--------------------------------- KERNEL MODE'a geçildi (System Call)")
                        print(f"[SYSCALL_PRN Output]: {value_to_print}")

                        # 2. İşletim sistemine gerekli bilgileri aktar
                        self.memory[CPU.MEM_OS_SYSCALL_TYPE] = 0  # PRN syscall tip kodu
                        self.syscall_result = self.pc + 1        # Thread'in dönüş adresini memory[2]'ye yaz

                        # 3. Kontrolü OS'deki PRN Handler'ına devret
                        os_prn_handler_address = self.memory[CPU.MEM_OS_SYSCALL_PRN_HANDLER]
                        if self._is_valid_address(os_prn_handler_address, "jump to OS PRN handler"):
                            self.pc = os_prn_handler_address
                            pc_incremented_by_command = True
                            executed_successfully = True
                        else:
                            print(f"Error: Invalid OS PRN handler address configured at memory[{CPU.MEM_OS_SYSCALL_PRN_HANDLER}]. Halting.")
                            self.is_halted = True
                except ValueError:
                    print(f"Error: Invalid argument for SYSCALL_PRN: {args}. Halting.")
                    self.is_halted = True
            else:
                print(f"Error: SYSCALL_PRN requires 1 argument, got {len(args)}. Halting.")
                self.is_halted = True

        elif command == "SYSCALL_HLT": 
            if not args:
                # print(f"[SYSCALL_HLT]: Thread halt. PC will jump to OS HLT handler.") # Debug
                self.memory[CPU.MEM_OS_SYSCALL_TYPE] = 1 # HLT syscall kodu
                self.syscall_result = 0 # Genel sonuç (başarılı)
                
                os_handler_address = self.memory[CPU.MEM_OS_SYSCALL_HLT_HANDLER]
                if self._is_valid_address(os_handler_address, "jump to OS HLT handler"):
                    print("--------------------------------- KERNEL MODE'a geçildi (System Call)")
                    
                    self.pc = os_handler_address
                    pc_incremented_by_command = True
                    executed_successfully = True
                else:
                    print(f"Error: Invalid OS HLT handler address configured at memory[{CPU.MEM_OS_SYSCALL_HLT_HANDLER}]. Halting.")
                    self.is_halted = True
            else:
                print(f"Error: SYSCALL_HLT does not take arguments, got {len(args)}. Halting.")
                self.is_halted = True

        elif command == "SYSCALL_YIELD": 
            print("--------------------------------- KERNEL MODE'a geçildi (System Call)")

            print(f"[CPU_DEBUG] Entering SYSCALL_YIELD; memory[15]={self.memory[15]}")
            if not args:
                self.memory[CPU.MEM_OS_SYSCALL_TYPE] = 2 # YIELD syscall kodu

                # YIELD yapan ipliğin dönüş PC'sini (bir sonraki komutun adresi)
                # syscall_result'a (memory[2]) kaydet.
                self.syscall_result = self.pc + 1 

                # print(f"[SYSCALL_YIELD]: CPU yield. Return PC={self.syscall_result}. PC will jump to OS YIELD handler.") # Debug

                os_handler_address = self.memory[CPU.MEM_OS_SYSCALL_YIELD_HANDLER]
                if self._is_valid_address(os_handler_address, "jump to OS YIELD handler"):
                    # self.mode = "KERNEL" # Zaten syscall başında KERNEL moda geçildi
                    self.pc = os_handler_address
                    pc_incremented_by_command = True
                    executed_successfully = True
                else:
                    print(f"Error: Invalid OS YIELD handler address configured at memory[{CPU.MEM_OS_SYSCALL_YIELD_HANDLER}]. Halting.")
                    self.is_halted = True
            else:
                print(f"Error: SYSCALL_YIELD does not take arguments, got {len(args)}. Halting.")
                self.is_halted = True

        else: # Bu else bloğu en sonda kalmalı
            print(f"Error: Unknown command '{command}'. Halting.")
            self.is_halted = True
            return 

        if executed_successfully:
            #print(f"DEBUG: Before IE increment: IE={self.instructions_executed}, Current Command: {command}") # DEBUG SATIRI
            if not pc_incremented_by_command:
                self.pc += 1
            self.instructions_executed += 1 # Bu self.memory[3] oluyor
            thread_id = self.memory[15]
            if thread_id == 0:
                tcb_range = range(21, 27)
            elif thread_id == 1:
                tcb_range = range(31, 37)
            elif thread_id == 2:
                tcb_range = range(41, 47)
            else:
                tcb_range = []
            

            for base in [20, 30, 40]:  # TCB0, TCB1, TCB2
                tcb_id = self.memory[base]
                values = [self.memory[base + offset] for offset in range(7)]
                #print(f"mem[{base}-{base+6}] (ID={tcb_id}):", " | ".join(f"{v}" for v in values))

            #print(f"------ [TCB Snapshot for Thread ID {thread_id}] ------")
            #for addr in tcb_range:
               #print(f"mem[{addr}]={self.memory[addr]}", end=" | ")
            #print("")
            #value_at_sp = "N/A" # Eger SP gecersiz bir adres ise veya yigin bos ise
            #if 0 <= self.sp < len(self.memory): # SP gecerli bir adres mi diye kontrol et
                #value_at_sp = self.memory[self.sp]
            #print(f"IE: {self.instructions_executed} | Next PC: {self.pc} | Mode: {self.mode} | SP: {self.sp} (ValAtSP: {value_at_sp}) | Syscall Result: {self.syscall_result}")
        
        elif not self.is_halted: 
            print(f"Error: Command '{command}' with args {args} could not be executed successfully. Halting.")
            self.is_halted = True
    
    # ... (run_cycle ve load_program_to_memory fonksiyonları aynı) ...
    def run_cycle(self):
        """
        Tek bir CPU döngüsünü çalıştırır: Fetch, Decode, Execute.
        """
        if not self.is_halted:
            print()
            #print(f"[RUN_CYCLE] PC: {self.pc}, SP: {self.sp}, Mode: {self.mode}, Thread: {self.memory[15]}")
            instruction_str = self._fetch()
            if instruction_str and not self.is_halted: # Fetch sırasında hata olup durdurulmadıysa
                self._decode_execute(instruction_str)
        # else:
            # print("CPU is halted. Cannot run cycle.") # Debug

    def load_program_to_memory(self, program_data_segment, program_instruction_segment, os_offset=21, thread_offsets=None):
        """
        BIOS'un yapacağı gibi, programın veri ve komut segmentlerini belleğe yükler.
        Bu metod daha sonra bios.py'a taşınabilir veya oradan çağrılabilir.
        
        program_data_segment: [(adres, değer), ...] formatında bir liste
        program_instruction_segment: [(adres, "KOMUT ARG1 ARG2"), ...] formatında bir liste
        os_offset: OS komutlarının ve verilerinin başlayacağı adres
        thread_offsets: {thread_id: başlangıç_adresi} şeklinde bir sözlük
        """
        print("Loading program to memory...")
        # Veri Segmenti Yükleme
        for address, value in program_data_segment:
            if 0 <= address < len(self.memory):
                self.memory[address] = value
                # print(f"Loaded data: memory[{address}] = {value}") # Debug
            else:
                print(f"Warning: Data address {address} is out of bounds.")

        # Komut Segmenti Yükleme
        # Bu kısım daha sofistike olacak. Şimdilik sadece OS komutlarını yükleyelim.
        # Gerçekte, BIOS bir ".gtu" dosyasını okuyup hem OS'u hem de iplikleri yükleyecek.
        for address, instruction_string in program_instruction_segment:
            actual_address = address # Şimdilik doğrudan adresi kullanalım.
                                    # OS için bu adres os_offset'ten başlayabilir.
            if 0 <= actual_address < len(self.memory):
                self.memory[actual_address] = instruction_string
                # print(f"Loaded instruction: memory[{actual_address}] = \"{instruction_string}\"") # Debug
            else:
                print(f"Warning: Instruction address {actual_address} is out of bounds.")
        
        # Başlangıç PC'si genellikle veri segmentinde adres 0'da ayarlanır.
        # self.pc = self.memory[0] # Eğer BIOS yüklerken PC'yi (adres 0) ayarladıysa
        print(f"Program loaded. Initial PC: {self.pc}, SP: {self.sp}")

    # YENİ METOT (Debug amaçlı, main.py'dan çağrılabilir)
    def dump_memory(self, start_addr=0, end_addr=None):
        """Belirtilen aralıktaki bellek içeriğini yazdırır."""
        if end_addr is None:
            end_addr = len(self.memory)
        
        print(f"\n--- Memory Dump (Addresses {start_addr}-{end_addr-1}) ---")
        for i in range(start_addr, end_addr):
            if self.memory[i] != 0: # Sadece sıfır olmayanları veya belirli bir aralığı yazdırabiliriz
                print(f"Mem[{i:04d}]: {self.memory[i]}")
        print("--- End of Memory Dump ---")

    def get_cpu_state_for_debug(self):
        """Debug modları için CPU'nun temel durumunu döndürür."""
        return {
            "PC": self.pc,
            "SP": self.sp,
            "SysCall_Result": self.syscall_result,
            "Instructions_Executed": self.instructions_executed,
            "Mode": self.mode,
            "Halted": self.is_halted,
            "OS_Syscall_Type": self.memory[CPU.MEM_OS_SYSCALL_TYPE]
        }

# DEĞİŞTİRİLDİ 7 (Testler güncellenen syscall mantığına ve CPYI2'ye göre ayarlanacak)
def run_all_cpu_tests():
    """CPU sınıfının tüm komutlarını test eden ana fonksiyon."""
    max_cycles_default = 300 # Çoğu test için yeterli
    max_cycles_long = 300    # CALL/RET veya döngü içeren testler için

    # --- Test 1: SET ve HLT ---
    print("\n--- Test 1: SET ve HLT ---")
    cpu1 = CPU() # Her test için yeni bir CPU örneği
    data_segment1 = [(0, 100), (1, 1023)]
    instruction_segment1 = [(100, "SET 50, 200"), (101, "HLT")]
    cpu1.load_program_to_memory(data_segment1, instruction_segment1)
    cycle_count = 0
    while not cpu1.is_halted and cycle_count < max_cycles_default: cpu1.run_cycle(); cycle_count += 1
    print(f"Test 1 Sonucu: Halted={cpu1.is_halted}, Mem[200]={cpu1.memory[200] if 200 < len(cpu1.memory) else 'OOB'}, Expected Mem[200]=50, Instructions Executed={cpu1.instructions_executed}")

     # --- Test CPYI2 ---
    print("\n--- Test CPYI2 ---")
    cpu_cpyi2 = CPU()
    # memory[memory[ptr_A2]] = memory[memory[ptr_A1]]
    # Mem[200]=10 (değer1), Mem[201]=20 (değer2)
    # Mem[300]=200 (ptr_A1), Mem[301]=201 (ptr_A2)
    # İstenen: Mem[Mem[301]] = Mem[Mem[300]]  => Mem[201] = Mem[200] => Mem[201] = 10
    data_cpyi2 = [
        (CPU.REG_PC, 100), (CPU.REG_SP, 1023),
        (200, 10), (201, 20), # Başlangıçta Mem[201]=20
        (300, 200), (301, 201)
    ]
    instr_cpyi2 = [
        (100, "CPYI2 300, 301"),
        (101, "HLT")
    ]
    cpu_cpyi2.load_program_to_memory(data_cpyi2, instr_cpyi2)
    cycle_count = 0
    while not cpu_cpyi2.is_halted and cycle_count < max_cycles_default: cpu_cpyi2.run_cycle(); cycle_count += 1
    print(f"Test CPYI2 Sonucu: Halted={cpu_cpyi2.is_halted}, Mem[201]={cpu_cpyi2.memory[201]} (Expected=10), IE={cpu_cpyi2.instructions_executed}")


    # --- Test 2: CPY ---
    print("\n--- Test 2: CPY ---")
    cpu2 = CPU()
    data_segment2 = [(0, 100), (1, 1023), (200, 77)]
    instruction_segment2 = [(100, "CPY 200, 201"), (101, "HLT")]
    cpu2.load_program_to_memory(data_segment2, instruction_segment2)
    cycle_count = 0
    while not cpu2.is_halted and cycle_count < max_cycles_default: cpu2.run_cycle(); cycle_count += 1
    print(f"Test 2 Sonucu: Halted={cpu2.is_halted}, Mem[201]={cpu2.memory[201] if 201 < len(cpu2.memory) else 'OOB'}, Expected Mem[201]=77, Instructions Executed={cpu2.instructions_executed}")

    # --- Test 3: CPYI ---
    print("\n--- Test 3: CPYI ---")
    cpu3 = CPU()
    data_segment3 = [(0, 100), (1, 1023), (250, 88), (300, 250)]
    instruction_segment3 = [(100, "CPYI 300, 350"), (101, "HLT")]
    cpu3.load_program_to_memory(data_segment3, instruction_segment3)
    cycle_count = 0
    while not cpu3.is_halted and cycle_count < max_cycles_default: cpu3.run_cycle(); cycle_count += 1
    print(f"Test 3 Sonucu: Halted={cpu3.is_halted}, Mem[350]={cpu3.memory[350] if 350 < len(cpu3.memory) else 'OOB'}, Expected Mem[350]=88, Instructions Executed={cpu3.instructions_executed}")

    # --- Test 4: ADD ---
    print("\n--- Test 4: ADD ---")
    cpu4 = CPU()
    data_segment4 = [(0, 100), (1, 1023), (200, 60)]
    instruction_segment4 = [(100, "ADD 200, 25"), (101, "HLT")]
    cpu4.load_program_to_memory(data_segment4, instruction_segment4)
    cycle_count = 0
    while not cpu4.is_halted and cycle_count < max_cycles_default: cpu4.run_cycle(); cycle_count += 1
    print(f"Test 4 Sonucu: Halted={cpu4.is_halted}, Mem[200]={cpu4.memory[200] if 200 < len(cpu4.memory) else 'OOB'}, Expected Mem[200]=85, Instructions Executed={cpu4.instructions_executed}")

    # --- Test 5: ADDI ---
    print("\n--- Test 5: ADDI ---")
    cpu5 = CPU()
    data_segment5 = [(0, 100), (1, 1023), (200, 55), (201, 33)]
    instruction_segment5 = [(100, "ADDI 200, 201"), (101, "HLT")]
    cpu5.load_program_to_memory(data_segment5, instruction_segment5)
    cycle_count = 0
    while not cpu5.is_halted and cycle_count < max_cycles_default: cpu5.run_cycle(); cycle_count += 1
    print(f"Test 5 Sonucu: Halted={cpu5.is_halted}, Mem[200]={cpu5.memory[200] if 200 < len(cpu5.memory) else 'OOB'}, Expected Mem[200]=88, Instructions Executed={cpu5.instructions_executed}")

    # --- Test 6: USER Modu Bellek İhlali (SET to low address) ---
    print("\n--- Test 6: USER Mode Memory Violation (SET to low address) ---")
    cpu6 = CPU()
    cpu6.mode = "USER"
    data_segment6 = [(0, 1000), (1, 1999)] # PC ve SP USER alanında
    instruction_segment6 = [(1000, "SET 50, 20"), (1001, "HLT")] # Korumalı alana yazma
    cpu6.load_program_to_memory(data_segment6, instruction_segment6)
    cycle_count = 0
    while not cpu6.is_halted and cycle_count < max_cycles_default: cpu6.run_cycle(); cycle_count += 1
    print(f"Test 6 Sonucu: Halted={cpu6.is_halted} (Expected=True), Instructions Executed={cpu6.instructions_executed} (Expected=0)")

    # --- Test 7: USER Modu Bellek İhlali (CPYI indirect read from low address) ---
    print("\n--- Test 7: USER Mode Memory Violation (CPYI indirect read from low address) ---")
    cpu7 = CPU()
    cpu7.mode = "USER"
    data_segment7 = [(0, 1000), (1, 1999), (30, 999), (1500, 30)] # Mem[1500]=30 (işaretçi)
    instruction_segment7 = [(1000, "CPYI 1500, 1600"), (1001, "HLT")] # Korumalı alandan (30) okuma
    cpu7.load_program_to_memory(data_segment7, instruction_segment7)
    cycle_count = 0
    while not cpu7.is_halted and cycle_count < max_cycles_default: cpu7.run_cycle(); cycle_count += 1
    print(f"Test 7 Sonucu: Halted={cpu7.is_halted} (Expected=True), Instructions Executed={cpu7.instructions_executed} (Expected=0)")

    # --- Test 8: SUBI ---
    print("\n--- Test 8: SUBI ---")
    cpu8 = CPU()
    data_segment8 = [(0, 100), (1, 1023), (200, 50), (201, 20)]
    instruction_segment8 = [(100, "SUBI 200, 201"), (101, "HLT")]
    cpu8.load_program_to_memory(data_segment8, instruction_segment8)
    cycle_count = 0
    while not cpu8.is_halted and cycle_count < max_cycles_default: cpu8.run_cycle(); cycle_count += 1
    print(f"Test 8 Sonucu: Halted={cpu8.is_halted}, Mem[201]={cpu8.memory[201] if 201 < len(cpu8.memory) else 'OOB'}, Expected Mem[201]=30, Instructions Executed={cpu8.instructions_executed}")

    # --- Test 9: JIF (Jump taken) ---
    print("\n--- Test 9: JIF (Jump taken) ---")
    cpu9 = CPU()
    data_segment9 = [(0, 100), (1, 1023), (201, 0)] # Mem[201] başlangıçta 0
    instruction_segment9 = [
        (100, "SET -5, 200"),    # Mem[200] = -5
        (101, "JIF 200, 103"),  # Koşul doğru, PC=103
        (102, "SET 99, 201"),   # Bu atlanacak
        (103, "HLT")
    ]
    cpu9.load_program_to_memory(data_segment9, instruction_segment9)
    cycle_count = 0
    final_pc_at_hlt9 = -1
    while not cpu9.is_halted and cycle_count < max_cycles_default:
        # HLT komutuna gelindiğinde PC'yi yakala
        current_instruction_str = cpu9.memory[cpu9.pc]
        if isinstance(current_instruction_str, str) and current_instruction_str.upper().startswith("HLT"):
            final_pc_at_hlt9 = cpu9.pc
        cpu9.run_cycle()
        cycle_count += 1
    print(f"Test 9 Sonucu: Halted={cpu9.is_halted}, Final PC (at HLT)={final_pc_at_hlt9}, Mem[201]={cpu9.memory[201] if 201 < len(cpu9.memory) else 'OOB'} (Expected=0), Instructions Executed={cpu9.instructions_executed} (Expected=2)")

    # --- Test 10: JIF (Jump not taken) ---
    print("\n--- Test 10: JIF (Jump not taken) ---")
    cpu10 = CPU()
    data_segment10 = [(0, 100), (1, 1023), (201, 0)] # Mem[201] başlangıçta 0
    instruction_segment10 = [
        (100, "SET 5, 200"),     # Mem[200] = 5
        (101, "JIF 200, 103"),  # Koşul yanlış, PC=102
        (102, "SET 88, 201"),   # Bu çalışacak, Mem[201]=88
        (103, "HLT")
    ]
    cpu10.load_program_to_memory(data_segment10, instruction_segment10)
    cycle_count = 0
    final_pc_at_hlt10 = -1
    while not cpu10.is_halted and cycle_count < max_cycles_default:
        current_instruction_str = cpu10.memory[cpu10.pc]
        if isinstance(current_instruction_str, str) and current_instruction_str.upper().startswith("HLT"):
            final_pc_at_hlt10 = cpu10.pc
        cpu10.run_cycle()
        cycle_count += 1
    print(f"Test 10 Sonucu: Halted={cpu10.is_halted}, Final PC (at HLT)={final_pc_at_hlt10}, Mem[201]={cpu10.memory[201] if 201 < len(cpu10.memory) else 'OOB'} (Expected=88), Instructions Executed={cpu10.instructions_executed} (Expected=3)")

    # --- Test 11: PUSH and POP ---
    print("\n--- Test 11: PUSH and POP ---")
    cpu11 = CPU()
    data_segment11 = [(0, 100), (1, 1023), (200, 777), (201, 0)] # SP=1023
    instruction_segment11 = [
        (100, "PUSH 200"),      # SP=1022, Mem[1022]=777
        (101, "POP 201"),       # Mem[201]=777, SP=1023
        (102, "HLT")
    ]
    cpu11.load_program_to_memory(data_segment11, instruction_segment11)
    initial_sp11 = cpu11.sp # load_program_to_memory sonrası SP'yi al
    cycle_count = 0
    while not cpu11.is_halted and cycle_count < max_cycles_default: cpu11.run_cycle(); cycle_count += 1
    print(f"Test 11 Sonucu: Halted={cpu11.is_halted}, Mem[201]={cpu11.memory[201] if 201 < len(cpu11.memory) else 'OOB'} (Expected=777), Final SP={cpu11.sp} (Expected={initial_sp11}), Instructions Executed={cpu11.instructions_executed}")

    # --- Test 12: CALL ve RET ---
    print("\n--- Test 12: CALL and RET ---")
    cpu12 = CPU()
    data_segment12 = [(0, 100), (1, 1023), (300, 0), (301, 0)] # SP=1023
    instruction_segment12 = [
        (100, "CALL 200"),      # SP=1022 (Mem[1022]=101), PC=200
        (101, "SET 55, 300"),   # PC=101 (dönüş sonrası), Mem[300]=55
        (102, "HLT"),
        (200, "SET 22, 301"),   # PC=200, Mem[301]=22
        (201, "RET")            # PC=Mem[1022]=101, SP=1023
    ]
    cpu12.load_program_to_memory(data_segment12, instruction_segment12)
    initial_sp12 = cpu12.sp
    cycle_count = 0
    while not cpu12.is_halted and cycle_count < max_cycles_long: cpu12.run_cycle(); cycle_count += 1
    print(f"Test 12 Sonucu: Halted={cpu12.is_halted}, Mem[300]={cpu12.memory[300]} (Expected=55), Mem[301]={cpu12.memory[301]} (Expected=22), Final SP={cpu12.sp} (Expected={initial_sp12}), Instructions Executed={cpu12.instructions_executed} (Expected=4)")

    # --- Test 13: USER komutu ---
    print("\n--- Test 13: USER command ---")
    cpu13 = CPU()
    data_segment13 = [(0, 100), (1, 1023), (250, 1000)] # Mem[250]=1000 (yeni PC)
    instruction_segment13 = [
        (100, "USER 250"),         # PC=1000, Mode=USER
        # (101, "HLT"),           # Bu komut çalışmaz
        (1000, "SET 10, 1001"),   # Mem[1001]=10 (USER modunda)
        (1001, "HLT")             # USER modunda HLT
    ]
    cpu13.load_program_to_memory(data_segment13, instruction_segment13)
    final_mode13 = ""
    cycle_count = 0
    while not cpu13.is_halted and cycle_count < max_cycles_default:
        cpu13.run_cycle()
        if cpu13.is_halted: final_mode13 = cpu13.mode
        cycle_count += 1
    print(f"Test 13 Sonucu: Halted={cpu13.is_halted}, Final Mode='{final_mode13}' (Expected=USER), Mem[1001]={cpu13.memory[1001] if 1001 < len(cpu13.memory) else 'OOB'} (Expected=10), Instructions Executed={cpu13.instructions_executed} (Expected=2)")

     # --- GÜNCELLENMİŞ SYSCALL TESTLERİ ---
    # --- Test 14: SYSCALL_PRN (Güncellenmiş) ---
    print("\n--- Test 14: SYSCALL_PRN (Updated) ---")
    cpu14 = CPU()
    data_segment14 = [(CPU.REG_PC, 100), (CPU.REG_SP, 1023), (500, 12345)]
    instruction_segment14 = [(100, "SYSCALL_PRN 500"), (101, "HLT")]
    cpu14.load_program_to_memory(data_segment14, instruction_segment14)
    print("Beklenen SYSCALL_PRN çıktısı aşağıda olmalı:")
    cycle_count = 0
    while not cpu14.is_halted and cycle_count < max_cycles_default: cpu14.run_cycle(); cycle_count += 1
    print(f"Test 14 Sonucu: Halted={cpu14.is_halted}, OS_Syscall_Type={cpu14.memory[CPU.MEM_OS_SYSCALL_TYPE]} (Expected=0), SyscallRes={cpu14.syscall_result} (Expected=100), IE={cpu14.instructions_executed}")

    # --- Test 15: SYSCALL_HLT (OS Handler'a Zıplama) ---
    print("\n--- Test 15: SYSCALL_HLT (Jump to OS Handler) ---")
    cpu15 = CPU()
    os_hlt_handler_addr = 500 # OS'nin HLT işleyicisinin adresi
    data_segment15 = [
        (CPU.REG_PC, 100), (CPU.REG_SP, 1023),
        (CPU.MEM_OS_SYSCALL_HLT_HANDLER, os_hlt_handler_addr) # OS handler adresini ayarla
    ]
    instruction_segment15 = [
        (100, "SYSCALL_HLT"),
        (101, "SET 1, 600"), # Bu komut çalışmamalı, PC handler'a zıplamalı
        # OS HLT Handler (basitçe CPU'yu durdursun bu test için)
        (os_hlt_handler_addr, "SET 99, 700"), # Handler'ın bir iş yaptığını göster
        (os_hlt_handler_addr + 1, "HLT")
    ]
    cpu15.load_program_to_memory(data_segment15, instruction_segment15)
    cycle_count = 0
    final_pc15 = -1
    while not cpu15.is_halted and cycle_count < max_cycles_default:
        final_pc15 = cpu15.pc # Her döngüde PC'yi kaydet
        cpu15.run_cycle()
        cycle_count += 1
    # Beklenen: SYSCALL_HLT (PC=500 olur), SET (handler), HLT. IE=2 (SYSCALL_HLT + SET)
    print(f"Test 15 Sonucu: Halted={cpu15.is_halted}, OS_Syscall_Type={cpu15.memory[CPU.MEM_OS_SYSCALL_TYPE]} (Expected=1), PC (before HLT in handler) approx {os_hlt_handler_addr+1}, Mem[700]={cpu15.memory[700]} (Expected=99), IE={cpu15.instructions_executed}")
    
    # Testler için PUSH/POP yığın sınırı senaryoları da eklenebilir.
    # Örneğin, SP'yi bilerek çok düşürüp PUSH yapmaya çalışmak (overflow).
    # Veya SP'yi bilerek çok yükseltip POP yapmaya çalışmak (underflow).
    # Bu, self.current_thread_stack_base ve self.current_thread_stack_limit gibi
    # değişkenlerin OS tarafından ayarlanmasını gerektirir. Şimdilik _is_valid_address genel koruma sağlar.


    # --- Test 16: SYSCALL_YIELD (OS Handler'a Zıplama) ---
    print("\n--- Test 16: SYSCALL_YIELD (Jump to OS Handler) ---") # Başlığı güncelledim
    cpu16 = CPU()
    os_yield_handler_addr = 550 # OS'nin YIELD işleyicisinin adresi (farklı bir adres)
    data_segment16 = [
        (CPU.REG_PC, 100), (CPU.REG_SP, 1023),
        (CPU.MEM_OS_SYSCALL_YIELD_HANDLER, os_yield_handler_addr), # OS handler adresini ayarla
        (501, 0) # SET komutunun yazacağı yeri sıfırla
    ]
    instruction_segment16 = [
        (100, "SYSCALL_YIELD"),
        (101, "SET 2, 601"), # Bu komut çalışmamalı, PC handler'a zıplamalı
        # OS YIELD Handler (basitçe bir değer set etsin ve CPU'yu durdursun bu test için)
        (os_yield_handler_addr, "SET 77, 501"), # Handler'ın bir iş yaptığını göster
        (os_yield_handler_addr + 1, "HLT")
    ]
    cpu16.load_program_to_memory(data_segment16, instruction_segment16)
    cycle_count = 0
    final_pc16 = -1
    while not cpu16.is_halted and cycle_count < max_cycles_default:
        final_pc16 = cpu16.pc 
        cpu16.run_cycle()
        cycle_count += 1
    # Beklenen: SYSCALL_YIELD (PC=550 olur), SET (handler), HLT. IE=2 (SYSCALL_YIELD + SET)
    print(f"Test 16 Sonucu: Halted={cpu16.is_halted}, OS_Syscall_Type={cpu16.memory[CPU.MEM_OS_SYSCALL_TYPE]} (Expected=2), PC (before HLT in handler) approx {os_yield_handler_addr+1}, Mem[501]={cpu16.memory[501]} (Expected=77), IE={cpu16.instructions_executed}")

if __name__ == "__main__":
    run_all_cpu_tests()


