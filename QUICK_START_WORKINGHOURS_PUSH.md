# 🚀 Quick Start: Push WorkingHours ke VPS

## 1️⃣ Konfigurasi (5 menit)

Edit file `.env`:

```env
VPS_API_URL=https://your-vps-domain.com/api
VPS_API_KEY=your_secret_api_key_here
VPS_PUSH_ENABLED=True
```

## 2️⃣ Test Koneksi

```bash
curl http://127.0.0.1:5000/vps-push/test
```

## 3️⃣ Preview Data

```bash
curl -X POST http://127.0.0.1:5000/vps-push/workinghours/preview \
  -H "Content-Type: application/json" \
  -d '{"limit": 5}'
```

## 4️⃣ Push ke VPS

### Push Hari Ini (Kemarin - Hari Ini)

```bash
curl -X POST http://127.0.0.1:5000/vps-push/workinghours/push/today
```

**Note:** Endpoint ini akan push data 2 hari (kemarin sampai hari ini)

### Push by Date Range

```bash
curl -X POST http://127.0.0.1:5000/vps-push/workinghours/push/date-range \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-10-25",
    "end_date": "2025-10-28"
  }'
```

### Push for Specific Employees

```bash
curl -X POST http://127.0.0.1:5000/vps-push/workinghours/push/pins \
  -H "Content-Type: application/json" \
  -d '{
    "pins": ["1001", "1002", "1003"],
    "days_back": 7
  }'
```

## 📋 Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/vps-push/workinghours/preview` | POST | Preview data tanpa push |
| `/vps-push/workinghours/push/today` | POST | Push data hari ini |
| `/vps-push/workinghours/push/date-range` | POST | Push by range tanggal |
| `/vps-push/workinghours/push/pins` | POST | Push by PIN karyawan |

## 🔍 Troubleshooting

### Check Logs

```bash
tail -f logs/vps_push_service.log
```

### Test Script

```bash
python test_workinghours_push.py
```

### Check Data Availability

```sql
SELECT COUNT(*) FROM workinghourrecs;
SELECT TOP 5 * FROM workinghourrecs ORDER BY working_date DESC;
```

## 📚 Full Documentation

See: `VPS_WORKINGHOURS_PUSH_API.md` untuk dokumentasi lengkap.
