# Dokumentasi Urutan Eksekusi Prosedur

## Urutan Eksekusi Stored Procedures

Sistem absensi telah diperbarui untuk memastikan urutan eksekusi prosedur yang benar:

### 🔄 **Automatic Execution (setelah Sync All Devices)**

1. **Step 1: attrecord procedure**
   - Dijalankan pertama kali
   - Memproses data attendance dari tabel FPLog
   - Mengubah data mentah menjadi data attendance yang terstruktur
   - **WAJIB berhasil** sebelum melanjutkan ke step berikutnya

2. **Step 2: spJamkerja procedure** 
   - Dijalankan **HANYA JIKA** attrecord berhasil
   - Menghitung jam kerja berdasarkan data attendance
   - Menghasilkan laporan jam kerja karyawan
   - **Dilewati** jika attrecord gagal

### 🎯 **Logic Flow**

```
Sync All Devices
    ↓
Wait for all devices to complete
    ↓
Execute attrecord procedure
    ↓
IF attrecord SUCCESS:
    ↓
    Execute spJamkerja procedure
ELSE:
    ↓
    Skip spJamkerja (show warning)
    ↓
End
```

### 📊 **Manual Execution**

Pengguna dapat menjalankan prosedur secara manual melalui:
- **Button "Execute Procedures"** di dashboard
- **API endpoint**: `POST /sync/procedures/execute`

Urutan yang sama diterapkan:
1. attrecord dulu
2. spJamkerja hanya jika attrecord berhasil

### ⚠️ **Mengapa Urutan Ini Penting?**

1. **Data Dependency**: spJamkerja membutuhkan data yang diproses oleh attrecord
2. **Data Integrity**: Mencegah jam kerja dihitung dari data attendance yang corrupt
3. **Error Prevention**: Menghindari error jika data dasar tidak tersedia
4. **Consistency**: Memastikan semua perhitungan berdasarkan data yang valid

### 🔧 **Implementation Details**

#### SyncService (_execute_procedures_after_sync):
```python
# Step 1: Execute attrecord FIRST
attrecord_success, attrecord_message = self.attendance_model.execute_attrecord_procedure(start_date, end_date)

if attrecord_success:
    # Step 2: Execute spJamkerja ONLY if attrecord succeeded
    spjamkerja_success, spjamkerja_message = self.attendance_model.execute_spjamkerja_procedure(start_date, end_date)
else:
    # Skip spJamkerja if attrecord failed
    spjamkerja_success = False
    spjamkerja_message = "Skipped due to attrecord procedure failure"
```

#### SyncController (execute_stored_procedures):
```python
# Step 1: Execute attrecord procedure FIRST
attrecord_success, attrecord_message = execute_attrecord_procedure(start_date, end_date)

# Step 2: Execute spJamkerja ONLY if attrecord was successful
if attrecord_success:
    spjamkerja_success, spjamkerja_message = execute_spjamkerja_procedure(start_date, end_date)
else:
    spjamkerja_success = False
    spjamkerja_message = "Skipped due to attrecord procedure failure"
```

### 📝 **Status Messages**

- **✅ Success**: "Both procedures executed successfully"
- **⚠️ Partial**: "attrecord completed but spJamkerja failed"
- **❌ Failed**: "attrecord failed. spJamkerja was skipped"

### 🔍 **Monitoring**

Dashboard menampilkan:
- Real-time execution status
- Step-by-step progress
- Detailed error messages
- Execution order confirmation

### 🚀 **Benefits**

1. **Reliable Data Flow**: Data selalu diproses dalam urutan yang benar
2. **Error Isolation**: Gagalnya satu step tidak merusak step lainnya
3. **Clear Feedback**: User mendapat informasi jelas tentang status setiap step
4. **Automatic Recovery**: Sistem bisa retry individual steps jika diperlukan
5. **Data Integrity**: Memastikan konsistensi data di seluruh sistem

---

**Update terakhir**: October 6, 2025
**Version**: 1.0.0