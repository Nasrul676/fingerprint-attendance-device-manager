# Changelog: WorkingHours Push Default Date Range

## 📅 Update Date: October 28, 2025

---

## 🔄 Perubahan

### SEBELUM:
- **Endpoint:** `POST /vps-push/workinghours/push/today`
- **Default Range:** Hanya hari ini (1 hari)
- **Contoh:** 2025-10-28 → 2025-10-28

### SESUDAH:
- **Endpoint:** `POST /vps-push/workinghours/push/today`
- **Default Range:** Kemarin sampai hari ini (2 hari)
- **Contoh:** 2025-10-27 → 2025-10-28

---

## 📝 File yang Diupdate

### 1. **app/services/vps_push_service.py**
```python
# BEFORE
def push_workinghours_today(self) -> Tuple[bool, str]:
    """Push today's WorkingHours data"""
    today = datetime.now().strftime('%Y-%m-%d')
    return self.push_workinghours_by_date_range(today, today)

# AFTER
def push_workinghours_today(self) -> Tuple[bool, str]:
    """Push WorkingHours data from yesterday to today"""
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    return self.push_workinghours_by_date_range(yesterday, today)
```

### 2. **app/controllers/vps_push_controller.py**
```python
# Updated method documentation
def push_workinghours_today(self):
    """Push WorkingHours data from yesterday to today"""
    
# Updated response format
return jsonify({
    'success': True,
    'message': message,
    'start_date': yesterday,  # NEW
    'end_date': today,        # NEW
    'timestamp': datetime.now().isoformat()
})
```

### 3. **app/routes.py**
```python
# Updated route documentation
@vps_push_bp.route('/workinghours/push/today', methods=['POST'])
def push_workinghours_today():
    """Push WorkingHours data from yesterday to today (2 days) to VPS"""
    return vps_push_controller.push_workinghours_today()
```

### 4. **VPS_WORKINGHOURS_PUSH_API.md**
- Updated endpoint documentation
- Changed example responses to show 2-day range

### 5. **WORKINGHOURS_PUSH_SUMMARY.md**
- Added note about default push range

### 6. **QUICK_START_WORKINGHOURS_PUSH.md**
- Updated quick start guide with new date range info

---

## 🎯 Testing

### Test Command:
```bash
curl -X POST http://127.0.0.1:5000/vps-push/workinghours/push/today
```

### Expected Response:
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

## 💡 Alasan Perubahan

**Mengapa 2 hari (kemarin - hari ini)?**

1. ✅ **Lebih Aman:** Memastikan tidak ada data yang terlewat
2. ✅ **Cover Late Data:** Menangkap data yang baru diproses dari kemarin
3. ✅ **Overlap Prevention:** Mencegah missing data karena timing issues
4. ✅ **Best Practice:** Standard dalam data synchronization

---

## ✅ Verification

Test dilakukan pada: **2025-10-28 09:21:29**

```
✅ Method push_workinghours_today exists
✅ Will push data from YESTERDAY to TODAY (2 days)
✅ Date calculation: 2025-10-27 to 2025-10-28
✅ All files updated successfully
✅ Documentation updated
```

---

## 🔗 Related

- Fitur ini konsisten dengan AttRecord push yang juga menggunakan range kemarin-hari ini
- Sesuai dengan sync_service.py yang menggunakan default 3 hari untuk sync

---

## 📞 Notes

- Jika ingin push single day, gunakan endpoint `/vps-push/workinghours/push/date-range`
- Untuk custom range, gunakan parameter `start_date` dan `end_date`
- Default 2 hari hanya berlaku untuk endpoint `/push/today`
