# spJamkerja Scheduler - Dokumentasi

## 📋 Overview

Scheduler otomatis untuk menjalankan stored procedure `spJamkerja` secara periodik dengan parameter rentang tanggal kemarin sampai hari ini.

## 🎯 Fitur Utama

### 1. **Auto-Start**
- ✅ Scheduler otomatis mulai saat aplikasi Flask dijalankan
- ✅ Tidak perlu manual start setiap kali server restart
- ✅ Eksekusi pertama setelah 5 menit (biar aplikasi settle dulu)

### 2. **Scheduled Execution**
- ⏰ Default interval: **3 jam** (10800 detik)
- 📅 Parameter otomatis: **kemarin s/d hari ini**
- 🔄 Runs in background thread (tidak block aplikasi)

### 3. **Safety Features**
- 🛡️ **Overlap Prevention**: Tidak akan mulai eksekusi baru jika yang lama masih jalan
- ⏱️ **Timeout Protection**: Max 90 menit per eksekusi
- 🔁 **Retry Mechanism**: Auto-retry jika gagal
- 📊 **Statistics Tracking**: Success/failure counts, duration, dll

### 4. **Manual Controls**
- ▶️  Start/Stop scheduler via API atau UI
- ⚡ Force execute (trigger manual)
- ⚙️  Set interval dynamically (minimal 30 menit)
- 📊 Real-time status monitoring

## 🚀 Cara Kerja

### **Otomatis (Recommended)**

Scheduler akan **auto-start** saat aplikasi Flask dijalankan:

```bash
# Development
python app.py

# Production
gunicorn --config config/gunicorn_config.py wsgi:app
```

Scheduler akan:
1. Start otomatis 5 menit setelah aplikasi running
2. Execute spJamkerja pertama kali (kemarin s/d hari ini)
3. Tunggu 3 jam
4. Execute lagi (loop terus selama aplikasi running)

### **Manual Control via Dashboard**

Akses dashboard: `http://localhost:5000/scheduler/dashboard`

Features:
- ✅ Real-time status monitoring
- ✅ Start/Stop controls
- ✅ Force execute button
- ✅ Set interval configuration
- ✅ Execution statistics

### **Manual Control via API**

```bash
# Get status
curl http://localhost:5000/scheduler/status

# Start scheduler
curl -X POST http://localhost:5000/scheduler/start

# Stop scheduler
curl -X POST http://localhost:5000/scheduler/stop

# Force execute now
curl -X POST http://localhost:5000/scheduler/force-execute

# Set interval (6 hours)
curl -X POST http://localhost:5000/scheduler/set-interval \
  -H "Content-Type: application/json" \
  -d '{"hours": 6}'
```

## 📊 Status Response

```json
{
  "success": true,
  "data": {
    "running": true,
    "is_processing": false,
    "interval_hours": 3.0,
    "last_execution_time": "2025-10-28T10:30:00",
    "last_execution_duration": 2700.5,
    "last_execution_status": "success",
    "execution_count": 5,
    "success_count": 4,
    "failure_count": 1,
    "next_execution_in_seconds": 8640
  }
}
```

## ⚙️ Configuration

### **Interval (Default: 3 jam)**

Mengapa 3 jam?
- spJamkerja execution: 30-45 menit
- Safety buffer: 2x execution time
- Balance antara up-to-date data vs resource usage

Rekomendasi interval berdasarkan execution time:
- 30 menit execution → **2 jam** interval
- 45 menit execution → **3 jam** interval ✅ (Default)
- 60 menit execution → **4 jam** interval

### **Mengubah Interval**

Via code (`app/services/spjamkerja_scheduler_service.py`):
```python
scheduler = get_spjamkerja_scheduler()
scheduler.interval_seconds = 21600  # 6 jam
```

Via API:
```bash
curl -X POST http://localhost:5000/scheduler/set-interval \
  -H "Content-Type: application/json" \
  -d '{"hours": 6}'
```

Via Dashboard:
- Klik "Set Interval" button
- Input desired hours (min: 0.5)
- Save

### **Parameter Tanggal**

Default: **Kemarin s/d Hari Ini**

Contoh:
- Hari ini: 2025-10-28
- Parameter: `@awal = '2025-10-27'`, `@akhir = '2025-10-28'`

Jika ingin custom range, modifikasi `_execute_spjamkerja()` di `spjamkerja_scheduler_service.py`:
```python
# Current (kemarin s/d hari ini)
today = datetime.now().date()
yesterday = today - timedelta(days=1)

# Custom: 7 hari terakhir
end_date = datetime.now().date()
start_date = end_date - timedelta(days=7)
```

## 🔧 Troubleshooting

### **Scheduler tidak auto-start**

Check logs:
```bash
tail -f logs/attendance_app.log | grep -i "spjamkerja"
```

Expected output:
```
2025-10-28 10:00:00 INFO: ✅ SpJamkerjaScheduler initialized
2025-10-28 10:00:00 INFO: ✅ spJamkerja Scheduler auto-started: Scheduler started (runs every 3.0 hours)
2025-10-28 10:05:00 INFO: 🔄 Scheduler loop started
2025-10-28 10:05:00 INFO: ⏳ First execution will run after 300 seconds...
```

### **Execution timeout**

Jika spJamkerja butuh > 90 menit, increase timeout di `spjamkerja_scheduler_service.py`:
```python
self.timeout_seconds = 7200  # 2 jam = 7200 detik
```

### **Scheduler running tapi tidak execute**

Check via dashboard atau API:
```bash
curl http://localhost:5000/scheduler/status
```

Perhatikan field:
- `is_processing`: Apakah sedang proses?
- `last_execution_time`: Kapan terakhir jalan?
- `next_execution_in_seconds`: Berapa detik lagi eksekusi berikutnya?

### **Force execute stuck**

Jika force execute hang/stuck > 2 jam:
1. Restart aplikasi Flask
2. Check database connection
3. Check stored procedure di SQL Server (mungkin deadlock)

## 📈 Monitoring

### **Logs**

Main log file: `logs/attendance_app.log`

Filter scheduler logs:
```bash
# Linux/Mac
tail -f logs/attendance_app.log | grep "spJamkerja"

# Windows PowerShell
Get-Content logs/attendance_app.log -Wait | Select-String "spJamkerja"
```

Expected log patterns:
```
🚀 Executing spJamkerja (execution #5)
📅 Date range: 2025-10-27 to 2025-10-28
✅ spJamkerja completed successfully in 2700.5 seconds (45.0 minutes)
⏳ Next execution in 10800 seconds (3.0 hours)...
```

### **Statistics Dashboard**

Akses: `http://localhost:5000/scheduler/dashboard`

Metrics yang ditampilkan:
- **Total Executions**: Total berapa kali jalan
- **Success**: Berapa kali sukses
- **Failures**: Berapa kali gagal
- **Last Duration**: Durasi terakhir (dalam menit)
- **Last Execution**: Timestamp terakhir jalan
- **Last Status**: Status terakhir (success/failed/error)

### **Health Check**

Quick check via API:
```bash
curl http://localhost:5000/scheduler/status | jq '.data.running'
# Output: true (running) atau false (stopped)
```

## 🔐 Security Notes

1. **API Endpoints**: Tidak ada authentication (tambahkan jika production)
2. **Force Execute**: Bisa dipanggil siapa saja (tambahkan auth/rate limiting)
3. **Dashboard**: Public access (tambahkan login jika perlu)

## 📝 Best Practices

### **Development Environment**
- Use shorter interval (1-2 jam) untuk testing
- Monitor logs closely
- Test force execute dulu sebelum auto-scheduler

### **Production Environment**
- Use 3-6 jam interval (optimal)
- Setup monitoring alerts (Grafana, Prometheus, dll)
- Regular check statistics (success rate harus > 95%)
- Database backup before major changes

### **Resource Management**
- 12GB RAM: 3 jam interval OK ✅
- 8GB RAM: Consider 4-6 jam interval
- 4GB RAM: Mungkin perlu optimasi stored procedure

## 🎓 Architecture Overview

```
Flask App Startup
    ↓
Auto-start Scheduler (5 min delay)
    ↓
Background Thread Loop
    ↓
Execute spJamkerja (kemarin s/d hari ini)
    ↓ (30-45 min)
Success/Failure logged
    ↓
Sleep 3 hours
    ↓
Loop back to Execute
```

## 📞 Support

Jika ada masalah:
1. Check logs: `logs/attendance_app.log`
2. Check dashboard: `/scheduler/dashboard`
3. Try force execute manual
4. Check database connectivity
5. Restart aplikasi

## 🔄 Future Improvements

Potential enhancements:
- [ ] Email notification on failure
- [ ] Slack/Teams integration
- [ ] Grafana dashboard integration
- [ ] Multiple schedule profiles (weekend vs weekday)
- [ ] Dynamic interval based on data volume
- [ ] Prometheus metrics export
