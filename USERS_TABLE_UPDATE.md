# 🔄 USERS TABLE UPDATE - QUICK REFERENCE

## ✅ Perubahan Selesai!

### 📊 Database Schema Changes

```
OLD STRUCTURE               NEW STRUCTURE
────────────────────────────────────────────────────
id INT                  →   id BIGINT
full_name NVARCHAR      →   name NVARCHAR
password_hash NVARCHAR  →   password NVARCHAR
is_active BIT           →   status NVARCHAR
created_at DATETIME         created_at DATETIME
updated_at DATETIME         updated_at DATETIME
                        +   email_verified_at DATETIME
                        +   remember_token NVARCHAR(100)
                        +   role NVARCHAR
                        +   pin NVARCHAR
```

### 🆕 Fitur Baru

| Fitur | Deskripsi |
|-------|-----------|
| **Role Management** | Field `role` untuk admin/user |
| **PIN Integration** | Field `pin` untuk mapping karyawan |
| **Status String** | 'aktif' / 'nonaktif' (lebih fleksibel) |
| **New Methods** | `is_active()`, `is_admin()` |

### 👤 Default User

```
Email    : admin@absensi.com
Password : admin123
Name     : Administrator
Role     : admin
Status   : aktif
PIN      : NULL
```

---

## 🚀 Deployment Steps

### Option A: Fresh Install (No existing users table)

```bash
1. start_production.bat
2. Table akan dibuat otomatis
3. Default admin user akan dibuat otomatis
```

### Option B: Update Existing Table (Has existing users table)

```sql
-- Step 1: Jalankan di SQL Server Management Studio
USE HRAPP;
DROP TABLE users;

-- Step 2: Restart Flask
start_production.bat

-- Step 3: Table baru akan dibuat otomatis dengan struktur baru
```

---

## 📝 Code Changes Summary

### User Model
```python
# Constructor
User(id, email, password, name, status='aktif', role=None, pin=None)

# Methods
user.is_active()      # Returns True/False
user.is_admin()       # Returns True/False
user.check_password(pwd)  # Verify password
user.to_dict()       # Convert to dict (exclude password)

# Static Methods
User.create_user(email, password, name, role='user', pin=None)
User.find_by_email(email)
User.find_by_id(user_id)
```

### Session Variables
```python
session['user_id']     # User ID (BIGINT)
session['user_email']  # Email
session['user_name']   # Name (was full_name)
session['user_role']   # Role (NEW!)
session['user_pin']    # PIN (NEW!)
```

---

## 🔍 Verification

### Check Table Structure
```sql
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'users';
```

### Check Default User
```sql
SELECT id, name, email, status, role 
FROM users 
WHERE email = 'admin@absensi.com';
```

### Test Login
```
URL: http://localhost:5000/auth/login
Email: admin@absensi.com
Password: admin123
Expected: Login berhasil, redirect ke dashboard
```

---

## 📚 Documentation

- **Full Guide:** `docs/users_table_update.md`
- **SQL Script:** `sql/create_users_table.sql`
- **Setup Auth:** `docs/SETUP_AUTH.md`

---

## ⚠️ Breaking Changes

| Area | Change | Impact |
|------|--------|--------|
| Field Names | `full_name` → `name` | Update all references |
| Field Names | `password_hash` → `password` | Update all references |
| Data Type | `is_active` BIT → `status` NVARCHAR | Change from boolean to string |
| Method | `user.is_active` → `user.is_active()` | Property to method |
| ID Type | INT → BIGINT | Larger ID range |

---

## 🎯 Next Steps

1. ✅ **Drop existing table** (if exists):
   ```sql
   DROP TABLE users;
   ```

2. ✅ **Restart aplikasi**:
   ```bash
   start_production.bat
   ```

3. ✅ **Verify logs**:
   ```
   [OK] Users table checked/created successfully
   [OK] Default user created: admin@absensi.com / admin123
   ```

4. ✅ **Test login**:
   - Open: http://localhost:5000
   - Login with default credentials
   - Check menu "Scheduler" muncul
   - Check user dropdown di navbar

---

**Status:** ✅ Ready to Deploy  
**Version:** 1.2.0 (New Users Table Structure)  
**Date:** October 28, 2025
