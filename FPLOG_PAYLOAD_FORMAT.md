# FPLog Push Payload Format Update

## Overview
Dokumentasi ini menjelaskan format payload untuk push data FPLog ke VPS endpoint `/api/fplog/bulk-upsert`.

## Updated Payload Format

### Request Endpoint
```
POST /api/fplog/bulk-upsert
Content-Type: application/json
```

### Payload Structure
```json
{
  "records": [
    {
      "FPID": "1001",
      "PIN": "5431",
      "date": "2025-10-27 21:00:00",
      "Machine": "102",
      "status": "Active"
    },
    {
      "FPID": "1002",
      "PIN": "5432",
      "date": "2025-10-27 00:00:00",
      "Machine": "104",
      "status": "Active"
    }
  ]
}
```

## Field Mappings

Transformasi dari database FPLog ke VPS API format:

| Database Column | VPS API Field | Type   | Description                    |
|----------------|---------------|--------|--------------------------------|
| `fpid`         | `FPID`        | String | Fingerprint ID                 |
| `PIN`          | `PIN`         | String | Employee PIN/ID                |
| `Date`         | `date`        | String | Timestamp (YYYY-MM-DD HH:MM:SS)|
| `Machine`      | `Machine`     | String | Device/Machine ID              |
| `Status`       | `status`      | String | Record status (e.g., "Active") |

## Implementation Details

### 1. Service Layer Changes
**File:** `app/services/vps_push_service.py`

#### Method: `_push_fplog_to_vps()`
```python
# Transform data to match VPS API format
formatted_records = []
for record in data:
    formatted_record = {
        "FPID": str(record.get('fpid', '')),
        "PIN": str(record.get('PIN', '')),
        "date": record.get('Date', ''),  # Already in 'YYYY-MM-DD HH:MM:SS' format
        "Machine": str(record.get('Machine', '')),
        "status": str(record.get('Status', 'Active'))
    }
    formatted_records.append(formatted_record)

# Format payload - send records array only
payload = {
    'records': formatted_records
}
```

#### Method: `get_fplog_preview()`
```python
# Format for preview - same format as will be sent to VPS
formatted_records = []
for record in data:
    formatted_record = {
        "FPID": str(record.get('fpid', '')),
        "PIN": str(record.get('PIN', '')),
        "date": record.get('Date', ''),
        "Machine": str(record.get('Machine', '')),
        "status": str(record.get('Status', 'Active'))
    }
    formatted_records.append(formatted_record)
```

### 2. Frontend Changes
**File:** `app/templates/vps_push_dashboard.html`

Updated preview modal table to display correct field names:
```javascript
records.forEach(record => {
    html += `<tr>
        <td>${record.FPID || 'N/A'}</td>
        <td>${record.PIN || 'N/A'}</td>
        <td>${record.date || 'N/A'}</td>
        <td>${record.Machine || 'N/A'}</td>
        <td>${record.status || 'N/A'}</td>
    </tr>`;
});
```

## Changes Summary

### What Changed:
1. ✅ **Removed metadata fields**: `source` and `timestamp` dari root payload
2. ✅ **Simplified payload**: Hanya berisi `records` array
3. ✅ **Updated field names**: Mengikuti konvensi yang diminta
   - `fpid` → `FPID` (uppercase)
   - `Date` → `date` (lowercase)
   - `Status` → `status` (lowercase)
4. ✅ **Type conversion**: Semua field dikonversi ke string kecuali `date`
5. ✅ **Preview consistency**: Preview menampilkan format yang sama dengan payload aktual

### What Stayed the Same:
- ✅ Database query logic (`get_fplog_data()`)
- ✅ Date filtering functionality
- ✅ PIN filtering functionality
- ✅ Retry mechanism dengan exponential backoff
- ✅ Error handling
- ✅ API endpoints (`/vps-push/fplog/*`)
- ✅ UI controls dan forms

## Example Payloads

### Single Record
```json
{
  "records": [
    {
      "FPID": "1001",
      "PIN": "5431",
      "date": "2025-10-27 21:00:00",
      "Machine": "102",
      "status": "Active"
    }
  ]
}
```

### Multiple Records
```json
{
  "records": [
    {
      "FPID": "1001",
      "PIN": "5431",
      "date": "2025-10-27 21:00:00",
      "Machine": "102",
      "status": "Active"
    },
    {
      "FPID": "1002",
      "PIN": "5432",
      "date": "2025-10-27 00:00:00",
      "Machine": "104",
      "status": "Active"
    },
    {
      "FPID": "1003",
      "PIN": "5433",
      "date": "2025-10-27 08:30:00",
      "Machine": "102",
      "status": "Active"
    }
  ]
}
```

## API Usage

### 1. Push Today's Data
```bash
curl -X POST http://localhost:5000/vps-push/fplog/push/today \
  -H "Content-Type: application/json"
```

### 2. Push Date Range
```bash
curl -X POST http://localhost:5000/vps-push/fplog/push/date-range \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-10-25",
    "end_date": "2025-10-27"
  }'
```

### 3. Push Filtered by PINs
```bash
curl -X POST http://localhost:5000/vps-push/fplog/push/pins \
  -H "Content-Type: application/json" \
  -d '{
    "pins": ["5431", "5432", "5433"]
  }'
```

### 4. Preview Data
```bash
curl -X POST http://localhost:5000/vps-push/fplog/preview \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-10-27",
    "end_date": "2025-10-27",
    "limit": 10
  }'
```

## Testing

### Test with PowerShell
```powershell
# Test push today
Invoke-WebRequest -Uri "http://127.0.0.1:5000/vps-push/fplog/push/today" `
  -Method POST `
  -ContentType "application/json" | Select-Object -ExpandProperty Content

# Test preview
$body = @{
    start_date = "2025-10-27"
    end_date = "2025-10-27"
    limit = 5
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://127.0.0.1:5000/vps-push/fplog/preview" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body | Select-Object -ExpandProperty Content
```

## Notes

1. **Date Format**: Tetap menggunakan format `YYYY-MM-DD HH:MM:SS` dari database
2. **Status Default**: Jika `Status` kosong di database, default ke `"Active"`
3. **String Conversion**: Semua field kecuali `date` dikonversi ke string untuk konsistensi
4. **Empty Values**: Field kosong dikonversi ke empty string `""` bukan `null`

## Backward Compatibility

⚠️ **Breaking Change**: Format payload ini **tidak kompatibel** dengan format sebelumnya yang menggunakan:
```json
{
  "records": [...],
  "source": "fingerprint_device",
  "timestamp": "2025-10-27T12:00:00"
}
```

Pastikan VPS endpoint `/api/fplog/bulk-upsert` sudah siap menerima format baru.

## Version History

- **v2.0** (2025-10-28): Updated payload format sesuai spesifikasi baru
- **v1.0** (2025-10-27): Initial implementation dengan format lama

---
*Last Updated: October 28, 2025*
