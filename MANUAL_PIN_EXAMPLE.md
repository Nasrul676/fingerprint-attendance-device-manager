# Manual PIN Attendance - Example Usage

## 🚀 Quick Start Guide

### 1. Jalankan Tool
```bash
python test_fingerprint_devices.py
# atau
run_fingerprint_test.bat
```

### 2. Pilih Device
```
🔧 FINGERPRINT DEVICE TESTER
============================================================
Available options:
1. List all devices
2. Select device for testing
3. Start attendance capture test
4. Stop test
5. Test device connection
6. Show test results
7. Manual PIN attendance (Full Process)  ← NEW FEATURE!
0. Exit
============================================================

Select option: 2

📱 Available Devices:
------------------------------------------------------------
 1. 104              | P2-IN                | zk              | 10.163.3.21     ⚡ ZK
 2. 201              | P1 Masuk             | fingerspot_api  | 10.163.3.48     🌐 API
 3. Absensi Online   | Absensi Online via API| online_attendance| online          ☁️ Online
------------------------------------------------------------

Enter device number to select: 1
✅ Selected device: 104 (zk)
```

### 3. Manual PIN Attendance
```
Select option: 7

🖐️  MANUAL PIN ATTENDANCE
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
   AttRecord: ✅ Procedure executed successfully for PIN 12345
   Queue: ✅ Added to attendance queue

✅ ATTENDANCE PROCESSED SUCCESSFULLY!
============================================================
Final Status: Masuk
Database Status: Record saved successfully
Queue Status: ✅ Added to attendance queue
AttRecord Status: ✅ Procedure executed successfully for PIN 12345
============================================================
```

## 🔄 Full Process Flow

### ZK Device (Option 7 + ZK)
```
Manual PIN Input → Status Determination → FPID Lookup → FPLog Save → AttRecord Procedure → Attendance Queue
```

### Fingerspot API (Option 7 + Fingerspot)
```
Manual PIN Input → Status Determination → FPID Lookup → FPLog Save → AttRecord Procedure → Attendance Queue
```

### Online Attendance (Option 7 + Online)
```
Manual PIN Input → Status Determination → Gagalabsens Save → AttRecord Procedure (No Queue)
```

## 📊 Sample Results

### ZK Device Result
```json
{
  "timestamp": "2025-10-03 14:30:15",
  "device_name": "104",
  "device_type": "manual_zk",
  "user_id": "12345",
  "punch_code": 0,
  "status": "I",
  "status_display": "Masuk",
  "processing_result": {
    "status": "I",
    "status_display": "Masuk",
    "db_status": "Record saved successfully",
    "queue_status": "✅ Added to attendance queue",
    "attrecord_status": "✅ Procedure executed successfully",
    "fpid": "123456789"
  }
}
```

### Online Attendance Result
```json
{
  "timestamp": "2025-10-03 14:30:15",
  "device_name": "Absensi Online",
  "device_type": "manual_online_attendance",
  "user_id": "12345",
  "punch_code": 0,
  "status": "I",
  "status_display": "Masuk",
  "processing_result": {
    "status": "I",
    "status_display": "Masuk",
    "db_status": "✅ Gagalabsens: Record saved successfully",
    "queue_status": "Not applicable (direct processing)",
    "attrecord_status": "✅ Procedure executed successfully",
    "fpid": null
  }
}
```

## 🎯 Use Cases

### 1. Testing Attendance Logic
- Validate status determination rules
- Check database integration
- Verify procedure execution

### 2. Employee Data Validation
- Test FPID lookup from employee table
- Verify PIN to employee mapping
- Check attendance record creation

### 3. System Integration Testing
- End-to-end attendance flow
- Database transaction testing
- Queue system validation

### 4. Development & Debugging
- Simulate attendance without physical devices
- Test specific PIN/user scenarios
- Validate business logic implementation

## 🔧 Advanced Features

### Multiple Device Testing
```bash
# Test ZK device
Select device: 104 (zk) → Manual PIN → Full ZK flow

# Test Fingerspot API
Select device: 201 (fingerspot_api) → Manual PIN → Full API flow

# Test Online Attendance
Select device: Absensi Online → Manual PIN → Hybrid flow
```

### Batch Testing
```bash
# Multiple PIN tests
PIN: 12345, Punch: 0 → Masuk
PIN: 12345, Punch: 1 → Keluar
PIN: 67890, Punch: 0 → Masuk
```

### Status Code Testing
```bash
# Test all punch codes
Punch 0: Check In (Masuk)
Punch 1: Check Out (Keluar)
Punch 2: Break Out
Punch 3: Break In
Punch 4: Overtime In
Punch 5: Overtime Out
```

## ⚠️ Important Notes

1. **Real Database Operations**: Tool melakukan operasi database sesungguhnya
2. **AttRecord Procedure**: Menjalankan stored procedure untuk perhitungan attendance
3. **Queue Integration**: Data masuk ke attendance queue seperti sistem streaming
4. **FPID Validation**: Otomatis mencari FPID dari employee table berdasarkan PIN
5. **Device-Specific Logic**: Menggunakan logic yang sama dengan streaming service

## 💡 Tips

- **Always select device first** sebelum manual PIN attendance
- **Use realistic PINs** yang ada di employee table untuk hasil terbaik
- **Check test results** untuk melihat semua hasil testing
- **Different device types** memiliki flow processing yang berbeda
- **Save results to JSON** untuk analisis lebih lanjut