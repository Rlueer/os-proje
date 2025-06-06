GTU OS Simülatörü - Kullanım Kılavuzu

1. Dizin Yapısı
----------------
Tüm dosyalar cpu_simulator klasöründedir. Üst klasör yapısı yoktur.

cpu_simulator/
├── bios.py
├── cpu.py
├── main.py
├── simulate.py
└── os_plus_threads.gtu

2. Çalıştırma
--------------
Ana simülasyonu çalıştırmak için:

  python main.py os_plus_threads.gtu
  → Varsayılan olarak 1000 cycle çalıştırır.

Belirli sayıda cycle çalıştırmak için:

  python main.py os_plus_threads.gtu 3000
  → 3000 cycle çalıştırır.

Bu komut çalıştırıldığında 2 adet dosya oluşur:
- instructions_output.txt → Tüm çalıştırılan talimatlar ve PC değerleri
- output.txt → Sadece SYSCALL_PRN komutları sonucu yazdırılan değerler

3. Debug Modları (simulate.py ile)
-----------------------------------
cpu_simulator dizinindeyken aşağıdaki komutları kullanabilirsin:

- Debug Mode 0:
    python simulate.py os_plus_threads.gtu -D 0
    → Program sonunda tüm bellek içeriği debug0_output.txt dosyasına yazılır.

- Debug Mode 1:
    python simulate.py os_plus_threads.gtu -D 1
    → Her instruction sonrası sadece değişen bellek adresleri debug1_output.txt’ye yazılır.

- Debug Mode 2:
    python simulate.py os_plus_threads.gtu -D 2
    → Her adım sonrası kullanıcıdan ENTER bekler. Bellek içeriği debug2_output.txt’ye yazılır.

- Debug Mode 3:
    python simulate.py os_plus_threads.gtu -D 3
    → Her SYSCALL veya context switch sonrası TCB durumu debug3_output.txt’ye yazılır.

4. Bellek Bölgeleri
--------------------
- 0–149           : OS ve TCB alanı
- 1000–1999       : Thread 1 kod ve verileri
- 2000–2999       : Thread 2
- 3000–3999       : Thread 3

dump_memory_regions: yalnızca dolu bellek adreslerini yazdırır.  
dump_memory        : kullanılan tüm bellek içeriğini gösterir.

5. Alternatif Test
-------------------
Farklı testler için:

  python cpu.py os_plus_threads.gtu

Çıktılar cpu_output.txt dosyasına yazılır.

6. Yardım Formatı
------------------
Kullanım: python main.py <gtu_dosya_yolu> [opsiyonel:max_cycle]
→ max_cycle verilmezse varsayılan 1000 olarak alınır.

7. Kullanılan AI Chat Linkleri
-------------------------------
(Gemini Paylaşımları)
- https://g.co/gemini/share/7f180ad74c65
- https://g.co/gemini/share/8f4dd7cf5e22
- https://g.co/gemini/share/ae61890d6b4a

(GPT-4 destekli içerikler dosya eki içerdiğinden paylaşılamıyor.)
