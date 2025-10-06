# Fingerprint Device Tester

Tool untuk testing koneksi dan capture data dari mesin fingerprint. Mendukung semua tipe device yang ada dalam sistem absensi.

## 🚀 Cara Menjalankan

### Opsi 1: Menggunakan Batch File (Recommended)
```bash
run_fingerprint_test.bat
```

### Opsi 2: Menggunakan Python Langsung
```bash
python test_fingerprint_devices.py
```

## 📱 Supported Devices

Tool ini mendukung semua tipe device yang terkonfigurasi:

| Device Type | Connection | Description |
|-------------|------------|-------------|
| **ZK Devices** | ⚡ Direct TCP | Real-time streaming |
| **Fingerspot API** | 🌐 HTTP API | Polling-based |
| **Online Attendance** | ☁️ Cloud API | Sync-based |

## 🔧 Fitur Utama

### 1. List All Devices
- Menampilkan semua device yang terkonfigurasi
- Menunjukkan tipe koneksi dan status

### 2. Select Device
- Pilih device mana yang akan di-test
- Validasi konfigurasi device

### 3. Test Connection
- Test koneksi ke device yang dipilih
- Validasi akses dan konfigurasi
- Menampilkan informasi device

### 4. Start Attendance Capture
- **ZK Devices**: Real-time capture saat finger di-scan
- **Fingerspot API**: Polling setiap 30 detik
- **Online Attendance**: Sync setiap 60 detik

### 5. Show Results
- Menampilkan hasil capture
- Export ke file JSON
- Timestamp dan detail lengkap

### 6. Manual PIN Attendance (FULL PROCESS) ⭐
- **Input PIN manual** untuk simulasi absensi
- **Proses lengkap** seperti streaming service:
  - Save ke database (FPLog/Gagalabsens)
  - Execute attrecord procedure
  - Add to attendance queue
  - Validasi FPID dari employee table
- **Support semua device types** dengan logic yang sesuai
- **Real-time feedback** dari setiap tahap proses

## 🎯 Cara Penggunaan

1. **Jalankan Tool**
   ```bash
   run_fingerprint_test.bat
   ```

2. **Pilih Menu 1** - List semua device
   ```
   Available Devices:
   1. 104              | P2-IN                | zk              | 10.163.3.21     ⚡ ZK
   2. 201              | P1 Masuk             | fingerspot_api  | 10.163.3.48     🌐 API
   3. Absensi Online   | Absensi Online via API| online_attendance| online          ☁️ Online
   ```

3. **Pilih Menu 2** - Select device untuk testing
   ```
   Enter device number to select: 1
   ✅ Selected device: 104 (zk)
   ```

4. **Pilih Menu 5** - Test koneksi (opsional)
   ```
   🔗 Testing connection to 104 (zk)...
   ✅ Connection to 104 successful!
   ```

5. **Pilih Menu 3** - Start capture test
   ```
   🚀 Starting attendance capture test for 104 (zk)
   📋 Press fingerprint on the device to capture attendance data
   ⏹️ Type 'stop' or press Ctrl+C to stop the test
   ```

6. **Scan Fingerprint** pada device yang dipilih
   ```
   👆 FINGERPRINT DETECTED!
      Time: 2025-10-03 14:30:15
      Device: 104 (zk)
      User ID: 12345
      Punch Code: 0
      Status: I (Masuk)
   ```

7. **Stop Test** dengan mengetik `stop` atau Ctrl+C

8. **Pilih Menu 7** - Manual PIN Attendance (NEW!)
   ```
   �️  MANUAL PIN ATTENDANCE
   Device: 104 (zk)
   ============================================================
   Enter PIN/User ID: 12345
   
   Punch codes:
   0 = Check In (Masuk)
   1 = Check Out (Keluar)
   2 = Break Out
   3 = Break In
   4 = Overtime In
   5 = Overtime Out
   Enter punch code (0-5, default=0): 0
   
   🚀 Processing attendance...
      PIN: 12345
      Punch Code: 0
      Device: 104
      Time: 2025-10-03 14:30:15
   --------------------------------------------------
   📝 Processing as ZK device attendance...
      Status determined: I (Masuk)
      FPID found: 123456789
      FPLog save: ✅ Record saved successfully
      AttRecord: ✅ Procedure executed successfully
      Queue: ✅ Added to attendance queue
   
   ✅ ATTENDANCE PROCESSED SUCCESSFULLY!
   ============================================================
   Final Status: Masuk
   Database Status: Record saved successfully
   Queue Status: ✅ Added to attendance queue
   AttRecord Status: ✅ Procedure executed successfully
   ============================================================
   ```

## 📊 Output Format

### Real-time Display
```
👆 FINGERPRINT DETECTED!
   Time: 2025-10-03 14:30:15
   Device: 104 (zk)
   User ID: 12345
   Punch Code: 0
   Status: I (Masuk)
   --------------------------------------------------
```

### JSON Export
```json
[
  {
    "timestamp": "2025-10-03 14:30:15",
    "device_name": "104",
    "device_type": "zk",
    "user_id": "12345",
    "punch_code": 0,
    "status": "I",
    "status_display": "Masuk"
  }
]
```

## 🔧 Device-Specific Testing

### ZK Devices
- **Real-time streaming**: Data langsung muncul saat finger di-scan
- **Live capture**: Menggunakan `live_capture()` method
- **Instant feedback**: Response time < 1 detik
- **Manual PIN**: Proses ke FPLog → AttRecord → Queue

### Fingerspot API
- **Polling mode**: Check data setiap 30 detik
- **API endpoint**: Menggunakan `/get_attlog` endpoint
- **Batch processing**: Bisa capture multiple records sekaligus
- **Manual PIN**: Proses ke FPLog → AttRecord → Queue

### Online Attendance
- **Sync mode**: Full sync setiap 60 detik
- **Cloud-based**: Data dari cloud API
- **Batch summary**: Menampilkan jumlah records yang di-sync
- **Manual PIN**: Hybrid approach → Gagalabsens → AttRecord (no queue)

## 🛠️ Troubleshooting

### Connection Issues
1. **ZK Device tidak connect**:
   - Check IP dan port
   - Pastikan password benar
   - Check network connectivity

2. **Fingerspot API error**:
   - Verify API key
   - Check base URL
   - Validate device_id

3. **Online Attendance gagal**:
   - Check internet connection
   - Verify API endpoint
   - Check authentication

### No Data Captured
1. **ZK**: Pastikan finger benar-benar di-scan pada device
2. **Fingerspot**: Tunggu minimal 30 detik untuk polling
3. **Online**: Data bisa delay, tunggu 1-2 menit

## 📝 Menu Options

| Menu | Description | Function |
|------|-------------|----------|
| **1** | List all devices | Tampilkan semua device |
| **2** | Select device | Pilih device untuk test |
| **3** | Start test | Mulai capture attendance |
| **4** | Stop test | Stop capture test |
| **5** | Test connection | Test koneksi device |
| **6** | Show results | Tampilkan hasil test |
| **7** | Manual PIN attendance | Input PIN manual + proses lengkap |
| **0** | Exit | Keluar dari program |

## 🎯 Tips Penggunaan

1. **Test koneksi** terlebih dahulu sebelum mulai capture
2. **ZK devices** memberikan response paling cepat
3. **Fingerspot API** butuh waktu polling, tunggu 30 detik
4. **Online Attendance** untuk test bulk sync
5. **Save results** selalu tersimpan dalam format JSON
6. **Multiple tests** bisa dilakukan berulang-ulang
7. **Manual PIN testing** untuk simulasi absensi tanpa device fisik
8. **Validasi FPID** otomatis dari employee table
9. **Full process testing** mencakup semua tahap streaming service

## ⚠️ Catatan Penting

- Tool ini hanya untuk **testing dan debugging**
- **Tidak menyimpan** data ke database
- **Real-time display** saja untuk monitoring
- Gunakan **Ctrl+C** untuk stop darurat
- Results tersimpan di file JSON untuk analisis

## 🔒 Keamanan

- Tool menggunakan konfigurasi yang sama dengan sistem utama
- Credentials tersimpan aman di `config/devices.py`
- Tidak ada penyimpanan password di file test results
- Log level dapat disesuaikan untuk debugging