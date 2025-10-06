# VPS Push Feature Documentation

## Overview
VPS Push adalah fitur untuk menyinkronkan data AttRecord dari database lokal ke server VPS eksternal melalui REST API. Feature ini memungkinkan push data absensi secara manual atau otomatis ke sistem VPS untuk integrasi dengan sistem lain.

## Configuration

### Environment Variables
Tambahkan variabel berikut di file `.env`:

```bash
# VPS API Configuration
VPS_API_URL=https://your-vps-domain.com/api/attendance
VPS_API_KEY=your-secret-api-key-here
VPS_API_TIMEOUT=30
VPS_API_RETRY_COUNT=3
VPS_PUSH_ENABLED=true
```

### Konfigurasi Detail:
- `VPS_API_URL`: URL endpoint API VPS untuk menerima data AttRecord
- `VPS_API_KEY`: API key untuk autentikasi ke VPS (Bearer token)
- `VPS_API_TIMEOUT`: Timeout dalam detik untuk HTTP request (default: 30)
- `VPS_API_RETRY_COUNT`: Jumlah retry jika request gagal (default: 3)
- `VPS_PUSH_ENABLED`: Enable/disable VPS push functionality (default: false)

## API Endpoints

### 1. Dashboard
```
GET /vps-push/
```
Dashboard web untuk monitoring dan kontrol VPS push operations.

### 2. Test Connection
```
GET /vps-push/test
```
Test koneksi ke VPS API.

**Response:**
```json
{
    "success": true/false,
    "message": "Connection status message",
    "timestamp": "2024-01-01T10:00:00"
}
```

### 3. Get Statistics
```
GET /vps-push/statistics
```
Mendapatkan statistik push operations.

**Response:**
```json
{
    "success": true,
    "statistics": {
        "total_records_pushed": 1000,
        "failed_pushes": 5,
        "last_push_time": "2024-01-01 10:00:00"
    },
    "timestamp": "2024-01-01T10:00:00"
}
```

### 4. Preview Data
```
POST /vps-push/preview
```
Preview data AttRecord tanpa push ke VPS.

**Request Body:**
```json
{
    "start_date": "2024-01-01",
    "end_date": "2024-01-01",
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
            "PIN": "1001",
            "Date": "2024-01-01",
            "Time": "08:00:00",
            "Status": "1",
            "WorkCode": "1",
            "DeviceName": "Device1"
        }
    ],
    "record_count": 1,
    "start_date": "2024-01-01",
    "end_date": "2024-01-01",
    "pins": ["1001", "1002"],
    "limit": 100,
    "timestamp": "2024-01-01T10:00:00"
}
```

### 5. Push Today's Data
```
POST /vps-push/push/today
```
Push data absensi hari ini ke VPS.

**Request Body:**
```json
{
    "pins": ["1001", "1002"]  // Optional, jika kosong push semua PIN
}
```

**Response:**
```json
{
    "success": true,
    "message": "Successfully pushed 50 records for date 2024-01-01",
    "date": "2024-01-01",
    "pins": ["1001", "1002"],
    "timestamp": "2024-01-01T10:00:00"
}
```

### 6. Push by Date Range
```
POST /vps-push/push/date-range
```
Push data berdasarkan rentang tanggal.

**Request Body:**
```json
{
    "start_date": "2024-01-01",
    "end_date": "2024-01-03",
    "pins": ["1001", "1002"]  // Optional
}
```

**Response:**
```json
{
    "success": true,
    "message": "Successfully pushed 150 records for date range 2024-01-01 to 2024-01-03",
    "start_date": "2024-01-01",
    "end_date": "2024-01-03",
    "pins": ["1001", "1002"],
    "timestamp": "2024-01-01T10:00:00"
}
```

### 7. Push by PINs
```
POST /vps-push/push/pins
```
Push data untuk PIN tertentu dengan rentang hari ke belakang.

**Request Body:**
```json
{
    "pins": ["1001", "1002", "1003"],
    "days_back": 7
}
```

**Response:**
```json
{
    "success": true,
    "message": "Successfully pushed 200 records for 3 PINs (7 days back)",
    "pins": ["1001", "1002", "1003"],
    "days_back": 7,
    "timestamp": "2024-01-01T10:00:00"
}
```

## VPS API Format

### Expected Request Format to VPS
VPS harus menerima POST request dengan format:

**Headers:**
```
Content-Type: application/json
Authorization: Bearer {VPS_API_KEY}
```

**Body:**
```json
{
    "source": "attendance_system",
    "data": [
        {
            "PIN": "1001",
            "Date": "2024-01-01",
            "Time": "08:00:00",
            "Status": "1",
            "WorkCode": "1",
            "DeviceName": "Device1"
        }
    ],
    "metadata": {
        "record_count": 1,
        "date_range": {
            "start": "2024-01-01",
            "end": "2024-01-01"
        },
        "push_timestamp": "2024-01-01T10:00:00"
    }
}
```

### Expected Response from VPS
```json
{
    "success": true,
    "message": "Data received successfully",
    "received_count": 1,
    "processed_count": 1,
    "timestamp": "2024-01-01T10:00:05"
}
```

## Database Schema

VPS Push mengambil data dari tabel `attrecord` dengan kolom:
- `PIN`: Employee ID
- `Date`: Tanggal absensi  
- `Time`: Waktu absensi
- `Status`: Status absensi (1=Masuk, 2=Pulang, dll)
- `WorkCode`: Kode kerja
- `DeviceName`: Nama device yang merekam

## Error Handling

### Common Errors:
1. **Connection Error**: VPS tidak dapat dijangkau
2. **Authentication Error**: API Key tidak valid
3. **Rate Limit**: Terlalu banyak request
4. **Timeout Error**: Request timeout
5. **Invalid Data**: Format data tidak sesuai

### Retry Logic:
- Automatic retry untuk connection errors
- Exponential backoff untuk rate limits
- Maximum retry count configurable

## Security

1. **API Key Authentication**: Menggunakan Bearer token
2. **HTTPS Required**: Komunikasi harus melalui HTTPS
3. **Rate Limiting**: Built-in protection terhadap spam requests
4. **Input Validation**: Validasi semua input parameters

## Monitoring

### Dashboard Features:
- Connection status monitoring
- Push statistics (total, failed, last push)
- Data preview sebelum push
- Activity log untuk troubleshooting
- Manual push operations

### Logging:
- Semua operations dicatat di `logs/vps_push_controller.log`
- Include timestamp, status, error messages
- Rotation log untuk mencegah file besar

## Usage Examples

### 1. Push Today's Data via Dashboard
1. Buka `/vps-push/` di browser
2. Klik "Push Today's Data"
3. Monitor di Activity Log

### 2. Push Specific Date Range via API
```bash
curl -X POST http://localhost:5000/vps-push/push/date-range \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-01-01",
    "end_date": "2024-01-03",
    "pins": ["1001", "1002"]
  }'
```

### 3. Test Connection
```bash
curl -X GET http://localhost:5000/vps-push/test
```

## Integration with Attendance Processing

VPS push dapat diintegrasikan dengan proses absensi existing:

1. **Manual Push**: Melalui dashboard atau API calls
2. **Scheduled Push**: Integrate dengan attendance worker untuk push otomatis
3. **Real-time Push**: Trigger setelah streaming service menerima data baru

## Troubleshooting

### Common Issues:

1. **VPS_PUSH_ENABLED=false**
   - Pastikan environment variable diset ke `true`

2. **Connection Failed**
   - Check VPS_API_URL accessibility
   - Verify network connectivity
   - Check firewall settings

3. **Authentication Failed**
   - Verify VPS_API_KEY correctness
   - Check VPS-side authentication logic

4. **No Data Found**
   - Check date range
   - Verify PIN exists in database
   - Check database connection

5. **Request Timeout**
   - Increase VPS_API_TIMEOUT value
   - Check VPS server performance
   - Reduce batch size

### Debug Steps:
1. Check dashboard connection status
2. Review activity logs
3. Test with preview function first
4. Verify VPS API independently
5. Check database connectivity

## Future Enhancements

1. **Automatic Scheduling**: Cron-like scheduling untuk push otomatis
2. **Batch Processing**: Optimize untuk volume data besar
3. **Compression**: Compress data untuk transfer yang lebih efisien
4. **Webhook Support**: VPS dapat trigger push via webhook
5. **Data Filtering**: Advanced filtering berdasarkan device, shift, dll