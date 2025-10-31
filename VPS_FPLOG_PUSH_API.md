# VPS FPLog Push API Documentation

## Overview

API untuk push data **FPLog** (Fingerprint Log) dari database lokal ke server VPS endpoint `/bulk-upsert`.

**Base URL:** `http://localhost:5000/vps-push`

**Authentication:** API Key (via environment variable `VPS_API_KEY`)

**Target Endpoint:** VPS Server `/bulk-upsert`

---

## Table Structure

### FPLog Table

FPLog menyimpan raw fingerprint log dari device:

| Column | Type | Description |
|--------|------|-------------|
| fpid | int | Primary key, auto increment |
| PIN | varchar | Employee ID/PIN |
| Date | datetime | Timestamp of fingerprint scan |
| Machine | varchar | Device/machine identifier |
| Status | varchar/int | Check in/out status |

**Sample Data:**
```sql
fpid | PIN  | Date                | Machine | Status
-----|------|---------------------|---------|-------
1    | 101  | 2024-01-28 08:15:00 | 102     | 0
2    | 101  | 2024-01-28 17:30:00 | 102     | 1
3    | 102  | 2024-01-28 08:20:00 | 104     | I
```

---

## API Endpoints

### 1. Preview FPLog Data

Get preview of FPLog data without pushing to VPS.

**Endpoint:** `POST /vps-push/fplog/preview`

**Request Body:**
```json
{
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "pins": ["101", "102", "103"],
    "limit": 50
}
```

**Parameters:**
- `start_date` (required): Start date in YYYY-MM-DD format
- `end_date` (optional): End date, defaults to start_date
- `pins` (optional): Array of employee PINs to filter
- `limit` (optional): Max records to preview (default: 50, max: 1000)

**Success Response (200):**
```json
{
    "success": true,
    "data": [
        {
            "pin": "101",
            "date": "2024-01-28 08:15:00",
            "machine": "102",
            "status": "0",
            "fpid": 1
        }
    ],
    "record_count": 1,
    "payload_preview": {
        "records": [...]
    },
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "pins": ["101", "102", "103"],
    "limit": 50,
    "timestamp": "2024-01-28T10:30:00"
}
```

**Error Response (400/500):**
```json
{
    "success": false,
    "message": "Invalid date format. Use YYYY-MM-DD"
}
```

**Example:**
```bash
# PowerShell
$body = @{
    start_date = "2024-01-28"
    end_date = "2024-01-28"
    limit = 50
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:5000/vps-push/fplog/preview" `
    -Method POST -Body $body -ContentType "application/json"
```

---

### 2. Push FPLog Today

Push FPLog data for today (yesterday to today - 2 days).

**Endpoint:** `POST /vps-push/fplog/push/today`

**Request Body:** None (optional empty JSON `{}`)

**Success Response (200):**
```json
{
    "success": true,
    "message": "Successfully pushed 150 FPLog records to VPS",
    "record_count": 150,
    "start_date": "2024-01-27",
    "end_date": "2024-01-28"
}
```

**Error Response (500):**
```json
{
    "success": false,
    "message": "VPS returned status 500: Internal server error"
}
```

**Example:**
```bash
# PowerShell
Invoke-WebRequest -Uri "http://localhost:5000/vps-push/fplog/push/today" `
    -Method POST -ContentType "application/json"
```

**Behavior:**
- Automatically calculates date range: yesterday to today
- Pushes to VPS endpoint `/bulk-upsert`
- Retries 3 times on failure
- Default date range: Yesterday to Today (2 days)

---

### 3. Push FPLog by Date Range

Push FPLog data for custom date range.

**Endpoint:** `POST /vps-push/fplog/push/date-range`

**Request Body:**
```json
{
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
}
```

**Parameters:**
- `start_date` (required): Start date in YYYY-MM-DD format
- `end_date` (optional): End date, defaults to start_date

**Success Response (200):**
```json
{
    "success": true,
    "message": "Successfully pushed 500 FPLog records to VPS",
    "record_count": 500,
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
}
```

**Error Response (400):**
```json
{
    "success": false,
    "message": "start_date is required"
}
```

**Example:**
```bash
# PowerShell
$body = @{
    start_date = "2024-01-01"
    end_date = "2024-01-31"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:5000/vps-push/fplog/push/date-range" `
    -Method POST -Body $body -ContentType "application/json"
```

---

### 4. Push FPLog by Employee PINs

Push FPLog data for specific employee PINs.

**Endpoint:** `POST /vps-push/fplog/push/pins`

**Request Body:**
```json
{
    "pins": ["101", "102", "103"],
    "days_back": 7
}
```

**Parameters:**
- `pins` (required): Array of employee PINs
- `days_back` (optional): Number of days to look back (default: 7, max: 90)

**Success Response (200):**
```json
{
    "success": true,
    "message": "Successfully pushed 42 FPLog records to VPS",
    "record_count": 42,
    "pins": ["101", "102", "103"],
    "days_back": 7
}
```

**Error Response (400):**
```json
{
    "success": false,
    "message": "pins array is required and cannot be empty"
}
```

**Example:**
```bash
# PowerShell
$body = @{
    pins = @("101", "102", "103")
    days_back = 7
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:5000/vps-push/fplog/push/pins" `
    -Method POST -Body $body -ContentType "application/json"
```

---

## VPS Endpoint Integration

### Target VPS Endpoint

**URL:** `{VPS_API_URL}/bulk-upsert`

**Method:** POST

**Headers:**
```
Content-Type: application/json
Authorization: Bearer {VPS_API_KEY}
X-API-Key: {VPS_API_KEY}
```

**Payload Format:**
```json
{
    "records": [
        {
            "PIN": "101",
            "Date": "2024-01-28 08:15:00",
            "Machine": "102",
            "Status": "0",
            "fpid": 1
        }
    ],
    "source": "fingerprint_device",
    "timestamp": "2024-01-28T10:30:00"
}
```

**Expected VPS Response:**
```json
{
    "success": true,
    "message": "Records upserted successfully",
    "records_processed": 150
}
```

---

## Configuration

### Environment Variables (.env)

```bash
# VPS API Configuration
VPS_API_URL=http://your-vps-server.com/api
VPS_API_KEY=your-secret-api-key
VPS_PUSH_ENABLED=true
VPS_API_TIMEOUT=30
VPS_API_RETRY_COUNT=3
```

### Configuration Details

| Variable | Description | Default |
|----------|-------------|---------|
| VPS_API_URL | VPS server base URL | (required) |
| VPS_API_KEY | API authentication key | (required) |
| VPS_PUSH_ENABLED | Enable/disable push | true |
| VPS_API_TIMEOUT | Request timeout (seconds) | 30 |
| VPS_API_RETRY_COUNT | Number of retry attempts | 3 |

---

## Error Handling

### Retry Logic

The service implements automatic retry with exponential backoff:

1. **First attempt:** Immediate
2. **Second attempt:** Wait 2 seconds
3. **Third attempt:** Wait 4 seconds

### Common Errors

**1. No Data Found**
```json
{
    "success": false,
    "message": "No data found for the specified date range"
}
```
**Solution:** Check if FPLog table has data for the date range

**2. VPS Service Disabled**
```json
{
    "success": false,
    "message": "VPS push service is disabled"
}
```
**Solution:** Set `VPS_PUSH_ENABLED=true` in .env

**3. Connection Timeout**
```json
{
    "success": false,
    "message": "Request timeout after multiple attempts"
}
```
**Solution:** Check VPS server connectivity and increase `VPS_API_TIMEOUT`

**4. Invalid Date Format**
```json
{
    "success": false,
    "message": "Invalid date format. Use YYYY-MM-DD"
}
```
**Solution:** Use YYYY-MM-DD format for dates

**5. VPS Server Error**
```json
{
    "success": false,
    "message": "VPS returned status 500: Internal server error"
}
```
**Solution:** Check VPS server logs and endpoint configuration

---

## Usage Examples

### Example 1: Push Today's Data

```python
import requests

url = "http://localhost:5000/vps-push/fplog/push/today"
response = requests.post(url)
print(response.json())
```

**Output:**
```json
{
    "success": true,
    "message": "Successfully pushed 150 FPLog records to VPS",
    "record_count": 150,
    "start_date": "2024-01-27",
    "end_date": "2024-01-28"
}
```

### Example 2: Push Specific Date Range

```python
import requests

url = "http://localhost:5000/vps-push/fplog/push/date-range"
data = {
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
}
response = requests.post(url, json=data)
print(response.json())
```

### Example 3: Push for Specific Employees

```python
import requests

url = "http://localhost:5000/vps-push/fplog/push/pins"
data = {
    "pins": ["101", "102", "103"],
    "days_back": 7
}
response = requests.post(url, json=data)
print(response.json())
```

### Example 4: Preview Before Push

```python
import requests

# Step 1: Preview data
preview_url = "http://localhost:5000/vps-push/fplog/preview"
preview_data = {
    "start_date": "2024-01-28",
    "end_date": "2024-01-28",
    "limit": 50
}
preview_response = requests.post(preview_url, json=preview_data)
print(f"Found {preview_response.json()['record_count']} records")

# Step 2: If data looks good, push it
if preview_response.json()['record_count'] > 0:
    push_url = "http://localhost:5000/vps-push/fplog/push/date-range"
    push_data = {
        "start_date": "2024-01-28",
        "end_date": "2024-01-28"
    }
    push_response = requests.post(push_url, json=push_data)
    print(push_response.json())
```

---

## Testing

### Manual Testing Steps

1. **Test Preview:**
```bash
# PowerShell
$body = @{ start_date = "2024-01-28"; limit = 10 } | ConvertTo-Json
Invoke-WebRequest -Uri "http://localhost:5000/vps-push/fplog/preview" `
    -Method POST -Body $body -ContentType "application/json"
```

2. **Test Push Today:**
```bash
Invoke-WebRequest -Uri "http://localhost:5000/vps-push/fplog/push/today" `
    -Method POST -ContentType "application/json"
```

3. **Test Date Range:**
```bash
$body = @{ start_date = "2024-01-01"; end_date = "2024-01-31" } | ConvertTo-Json
Invoke-WebRequest -Uri "http://localhost:5000/vps-push/fplog/push/date-range" `
    -Method POST -Body $body -ContentType "application/json"
```

4. **Test PIN Filter:**
```bash
$body = @{ pins = @("101", "102"); days_back = 7 } | ConvertTo-Json
Invoke-WebRequest -Uri "http://localhost:5000/vps-push/fplog/push/pins" `
    -Method POST -Body $body -ContentType "application/json"
```

---

## Logging

All operations are logged to: `logs/vps_push_service.log` and `logs/vps_push_controller.log`

**Log Format:**
```
2024-01-28 10:30:00 - INFO - Fetching FPLog data for date range: 2024-01-01 to 2024-01-31
2024-01-28 10:30:01 - INFO - Retrieved 500 FPLog records from database
2024-01-28 10:30:02 - INFO - Pushing 500 FPLog records to VPS: http://vps/api/bulk-upsert
2024-01-28 10:30:05 - INFO - Successfully pushed 500 FPLog records to VPS
```

---

## Performance

### Benchmarks

| Operation | Records | Time |
|-----------|---------|------|
| Preview 50 records | 50 | ~500ms |
| Push 100 records | 100 | ~2s |
| Push 500 records | 500 | ~5s |
| Push 1000 records | 1000 | ~10s |

**Notes:**
- Time includes database query + network transfer
- VPS response time varies by network
- Retry logic may increase time on failure

### Optimization Tips

1. **Batch Size:** Keep under 1000 records per push
2. **Date Range:** Use smaller date ranges for faster response
3. **PIN Filter:** Filter by PINs to reduce data volume
4. **Preview First:** Always preview large datasets first

---

## Security

### Authentication

- API key required in VPS request headers
- Keys stored in environment variables (not in code)
- HTTPS recommended for production

### Data Validation

- Date format validation
- PIN format validation
- Record limit enforcement
- SQL injection protection (parameterized queries)

---

## Troubleshooting

### Issue: Push fails immediately

**Check:**
1. VPS_PUSH_ENABLED is true
2. VPS_API_URL is configured
3. VPS_API_KEY is configured
4. VPS server is online

### Issue: No data found

**Check:**
1. FPLog table has data: `SELECT COUNT(*) FROM FPLog`
2. Date range is correct
3. PINs exist in database

### Issue: Timeout errors

**Check:**
1. VPS server response time
2. Network connectivity
3. Increase VPS_API_TIMEOUT
4. Check firewall settings

### Issue: VPS returns error

**Check:**
1. VPS endpoint URL is correct (/bulk-upsert)
2. VPS API key is valid
3. VPS server logs
4. Payload format matches VPS expectations

---

## API Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/vps-push/fplog/preview` | POST | Preview data |
| `/vps-push/fplog/push/today` | POST | Push yesterday-today |
| `/vps-push/fplog/push/date-range` | POST | Push custom date range |
| `/vps-push/fplog/push/pins` | POST | Push by employee PINs |

**All endpoints:**
- Return JSON responses
- Support retry logic
- Log all operations
- Validate input parameters

---

## Change Log

### Version 1.0.0 (2024-01-28)
- Initial release
- 4 API endpoints
- Retry logic (3 attempts)
- Exponential backoff
- Comprehensive logging
- Preview feature
- PIN filtering
- Date range filtering

---

**Last Updated:** 2024-01-28  
**Version:** 1.0.0  
**Status:** Production Ready ✅
