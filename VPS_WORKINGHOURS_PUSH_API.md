# VPS WorkingHours Push API Documentation

## 📋 Overview

Fitur untuk push data **WorkingHours** (hasil kalkulasi jam kerja dan lembur dari stored procedure `spJamkerja`) ke VPS server. Data yang dikirim berasal dari tabel `workinghourrecs`.

## 🔧 Configuration

Tambahkan konfigurasi berikut di file `.env`:

```env
# VPS API Configuration
VPS_API_URL=https://your-vps-domain.com/api
VPS_API_KEY=your_secret_api_key_here
VPS_API_TIMEOUT=30
VPS_API_RETRY_COUNT=3
VPS_PUSH_ENABLED=True
```

### Parameter Konfigurasi:

| Parameter | Deskripsi | Default |
|-----------|-----------|---------|
| `VPS_API_URL` | Base URL VPS API endpoint | None (required) |
| `VPS_API_KEY` | API Key untuk authentikasi | None (required) |
| `VPS_API_TIMEOUT` | Timeout request dalam detik | 30 |
| `VPS_API_RETRY_COUNT` | Jumlah retry jika gagal | 3 |
| `VPS_PUSH_ENABLED` | Enable/disable push service | False |

## 📡 API Endpoints

### 1. Preview WorkingHours Data
**GET** `/vps-push/workinghours/preview`

Preview data sebelum push ke VPS (tidak mengirim data).

**Request Body:**
```json
{
  "start_date": "2025-10-25",
  "end_date": "2025-10-28",
  "pins": ["1001", "1002"],
  "limit": 100
}
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 12345,
      "pin": "1001",
      "name": "John Doe",
      "shift": "Shift A",
      "deptname": "IT Department",
      "lokasi": "Jakarta",
      "tgl": "2025-10-28",
      "hari": "Monday",
      "masuk": "08:00:00",
      "keluar": "17:00:00",
      "break_out": "12:00:00",
      "break_in": "13:00:00",
      "jamkerja": 8.0,
      "lembur": 0.0,
      "kehadiran": 1.0,
      "status": "Hadir",
      "keterangan": null,
      "created_at": "2025-10-28 18:00:00",
      "updated_at": "2025-10-28 18:00:00"
    }
  ],
  "record_count": 1,
  "payload_preview": { ... },
  "start_date": "2025-10-25",
  "end_date": "2025-10-28",
  "pins": ["1001", "1002"],
  "limit": 100,
  "timestamp": "2025-10-28T18:30:00"
}
```

---

### 2. Push WorkingHours Hari Ini
**POST** `/vps-push/workinghours/push/today`

Push data workinghours dari **kemarin sampai hari ini** (2 hari) ke VPS.

**Response:**
```json
{
  "success": true,
  "message": "Successfully pushed 90 WorkingHours records",
  "start_date": "2025-10-27",
  "end_date": "2025-10-28",
  "timestamp": "2025-10-28T18:30:00"
}
```

---

### 3. Push WorkingHours by Date Range
**POST** `/vps-push/workinghours/push/date-range`

Push data workinghours berdasarkan range tanggal.

**Request Body:**
```json
{
  "start_date": "2025-10-25",
  "end_date": "2025-10-28",
  "pins": ["1001", "1002"]
}
```

**Parameter:**
- `start_date` (required): Tanggal mulai (YYYY-MM-DD)
- `end_date` (optional): Tanggal akhir, default = start_date
- `pins` (optional): Array PIN karyawan untuk filter

**Response:**
```json
{
  "success": true,
  "message": "Successfully pushed 120 WorkingHours records",
  "start_date": "2025-10-25",
  "end_date": "2025-10-28",
  "pins": ["1001", "1002"],
  "timestamp": "2025-10-28T18:30:00"
}
```

---

### 4. Push WorkingHours for Specific PINs
**POST** `/vps-push/workinghours/push/pins`

Push data workinghours untuk PIN karyawan tertentu.

**Request Body:**
```json
{
  "pins": ["1001", "1002", "1003"],
  "days_back": 7
}
```

**Parameter:**
- `pins` (required): Array PIN karyawan
- `days_back` (optional): Jumlah hari ke belakang, default = 7

**Response:**
```json
{
  "success": true,
  "message": "Successfully pushed 84 WorkingHours records",
  "pins": ["1001", "1002", "1003"],
  "days_back": 7,
  "timestamp": "2025-10-28T18:30:00"
}
```

---

## 📊 Data Structure

### WorkingHours Record Format

Data yang dikirim ke VPS memiliki format:

```json
{
  "records": [
    {
      "id": 12345,
      "pin": "1001",
      "name": "John Doe",
      "shift": "Shift A",
      "deptname": "IT Department",
      "lokasi": "Jakarta",
      "tgl": "2025-10-28",
      "hari": "Monday",
      "masuk": "08:00:00",
      "keluar": "17:00:00",
      "break_out": "12:00:00",
      "break_in": "13:00:00",
      "jamkerja": 8.0,
      "lembur": 0.0,
      "kehadiran": 1.0,
      "status": "Hadir",
      "keterangan": null,
      "created_at": "2025-10-28 18:00:00",
      "updated_at": "2025-10-28 18:00:00"
    }
  ]
}
```

### Field Descriptions:

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key record |
| `pin` | String | Employee PIN |
| `name` | String | Employee name |
| `shift` | String | Work shift |
| `deptname` | String | Department name |
| `lokasi` | String | Location |
| `tgl` | String | Date (YYYY-MM-DD) |
| `hari` | String | Day name (Monday, Tuesday, etc) |
| `masuk` | String | Clock in time (HH:MM:SS) |
| `keluar` | String | Clock out time (HH:MM:SS) |
| `break_out` | String | Break start time (HH:MM:SS) |
| `break_in` | String | Break end time (HH:MM:SS) |
| `jamkerja` | Float | Total working hours (decimal) |
| `lembur` | Float | Overtime hours (decimal) |
| `kehadiran` | Float | Attendance ratio (0-1) |
| `status` | String | Attendance status |
| `keterangan` | String | Additional notes |
| `created_at` | String | Record creation timestamp |
| `updated_at` | String | Record update timestamp |

---

## 🔐 Authentication

Semua request harus menyertakan authentication headers:

```
Authorization: Bearer YOUR_API_KEY
X-API-Key: YOUR_API_KEY
Content-Type: application/json
User-Agent: AttendanceSystem/1.0
```

---

## 🚀 Usage Examples

### Python Example

```python
import requests

# Configuration
VPS_API_URL = "https://your-vps.com/api"
API_KEY = "your_secret_key"

# Push workinghours data by date range
def push_workinghours(start_date, end_date):
    url = f"{VPS_API_URL}/vps-push/workinghours/push/date-range"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "start_date": start_date,
        "end_date": end_date
    }
    
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

# Example usage
result = push_workinghours("2025-10-25", "2025-10-28")
print(result)
```

### cURL Example

```bash
# Push today's workinghours data
curl -X POST http://127.0.0.1:5000/vps-push/workinghours/push/today \
  -H "Content-Type: application/json"

# Push by date range
curl -X POST http://127.0.0.1:5000/vps-push/workinghours/push/date-range \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-10-25",
    "end_date": "2025-10-28",
    "pins": ["1001", "1002"]
  }'

# Push for specific PINs
curl -X POST http://127.0.0.1:5000/vps-push/workinghours/push/pins \
  -H "Content-Type: application/json" \
  -d '{
    "pins": ["1001", "1002"],
    "days_back": 7
  }'

# Preview data (no push)
curl -X POST http://127.0.0.1:5000/vps-push/workinghours/preview \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-10-25",
    "end_date": "2025-10-28",
    "limit": 10
  }'
```

### PowerShell Example

```powershell
# Push workinghours data by date range
$body = @{
    start_date = "2025-10-25"
    end_date = "2025-10-28"
    pins = @("1001", "1002")
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
    -Uri "http://127.0.0.1:5000/vps-push/workinghours/push/date-range" `
    -ContentType "application/json" `
    -Body $body
```

---

## 🔄 Retry Logic

Service memiliki automatic retry mechanism:

1. **Retry Count**: Sesuai `VPS_API_RETRY_COUNT` (default: 3)
2. **Retry Scenarios**:
   - Connection timeout
   - Connection error
   - Rate limit exceeded (429)
   - Server errors (5xx)
3. **Backoff Strategy**: Exponential backoff untuk rate limit

---

## 📝 Logging

Semua operasi push akan di-log ke:
- **Console/Terminal**: Real-time output dengan emoji indicators
- **Log File**: `logs/vps_push_service.log`

### Log Format:

```
VPS PUSH WORKINGHOURS PAYLOAD LOG
================================================================================
Timestamp: 2025-10-28 18:30:00
Total Records: 120
Start Date: 2025-10-25
End Date: 2025-10-28

Payload JSON (first 2 records):
{
  "records": [ ... ]
}
================================================================================

📤 Attempt 1/3: Pushing 120 WorkingHours records to VPS...
📨 Response received: Status 200
✅ SUCCESS: WorkingHours data pushed successfully!
```

---

## ⚠️ Error Handling

### Common Error Responses:

**Authentication Failed (401):**
```json
{
  "success": false,
  "message": "Authentication failed"
}
```

**Rate Limit Exceeded (429):**
```json
{
  "success": false,
  "message": "Rate limit exceeded"
}
```

**Connection Error:**
```json
{
  "success": false,
  "message": "Connection error"
}
```

**No Data Found:**
```json
{
  "success": false,
  "message": "No WorkingHours data found for the specified criteria"
}
```

**Invalid Date Format:**
```json
{
  "success": false,
  "message": "Invalid date format. Use YYYY-MM-DD"
}
```

---

## 🔍 Testing

### Test VPS Connection

```bash
curl -X GET http://127.0.0.1:5000/vps-push/test
```

### Get Statistics

```bash
curl -X GET http://127.0.0.1:5000/vps-push/statistics
```

---

## 📌 Best Practices

1. **Preview First**: Gunakan `/preview` endpoint untuk validate data sebelum push
2. **Date Range**: Gunakan range tanggal yang reasonable (tidak terlalu besar)
3. **PIN Filter**: Filter berdasarkan PIN untuk mengurangi data yang dikirim
4. **Monitoring**: Monitor log file untuk troubleshooting
5. **Error Handling**: Implementasikan proper error handling di aplikasi client

---

## 🔗 Related Endpoints

- **AttRecord Push**: `/vps-push/push/date-range`
- **Test Connection**: `/vps-push/test`
- **Statistics**: `/vps-push/statistics`

---

## 📞 Support

Untuk issue atau pertanyaan, silakan hubungi tim development atau buka issue di repository project.
