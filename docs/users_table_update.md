# Update: Tabel Users - Struktur Baru

## Perubahan Database Schema

### Struktur Lama vs Baru

| Field Lama | Field Baru | Tipe | Keterangan |
|------------|------------|------|------------|
| `id` INT | `id` BIGINT | ID auto-increment | Ukuran lebih besar |
| `full_name` | `name` | NVARCHAR(255) | Nama user |
| `email` | `email` | NVARCHAR(255) | Email (unique) |
| - | `email_verified_at` | DATETIME | Verifikasi email |
| `password_hash` | `password` | NVARCHAR(255) | Password hash |
| - | `remember_token` | NVARCHAR(100) | Token remember me |
| `created_at` | `created_at` | DATETIME | Tanggal dibuat |
| `updated_at` | `updated_at` | DATETIME | Tanggal update |
| `is_active` BIT | `status` NVARCHAR | Status aktif/nonaktif |
| - | `role` | NVARCHAR(255) | Role user (admin/user) |
| - | `pin` | NVARCHAR(255) | PIN karyawan |

### Fitur Baru

1. **Role Management**
   - Field `role` untuk membedakan admin dan user biasa
   - Default role: `user`
   - Admin role: `admin`

2. **PIN Integration**
   - Field `pin` untuk mapping dengan data karyawan
   - Nullable (optional)

3. **Status String**
   - `status = 'aktif'` untuk user aktif
   - `status = 'nonaktif'` untuk user tidak aktif
   - Lebih fleksibel dari BIT (boolean)

4. **Remember Token**
   - Support untuk "Remember Me" functionality
   - Field `remember_token` (belum diimplementasi)

## Perubahan Code

### 1. User Model (`app/models/user.py`)

**Constructor:**
```python
# Before
def __init__(self, id=None, email=None, password_hash=None, full_name=None, is_active=True)

# After
def __init__(self, id=None, email=None, password=None, name=None, status='aktif', role=None, pin=None)
```

**New Methods:**
```python
def is_active(self):
    """Check if user is active"""
    return self.status == 'aktif'

def is_admin(self):
    """Check if user has admin role"""
    return self.role == 'admin'
```

**Create User:**
```python
# Before
User.create_user(email, password, full_name)

# After
User.create_user(email, password, name, role='user', pin=None)
```

### 2. Auth Controller (`app/controllers/auth_controller.py`)

**Session Storage:**
```python
# Before
session['user_name'] = user.full_name

# After
session['user_name'] = user.name
session['user_role'] = user.role
session['user_pin'] = user.pin
```

**Status Check:**
```python
# Before
if not user.is_active:

# After
if not user.is_active():
```

## Default User

Default admin user yang dibuat:

```python
Email: admin@absensi.com
Password: admin123
Name: Administrator
Role: admin
Status: aktif
PIN: NULL
```

## SQL Scripts

### Drop & Create Table
File: `sql/create_users_table.sql`

Untuk membuat ulang tabel (jika sudah ada tabel lama):
```sql
USE HRAPP;
GO

-- Drop old table
DROP TABLE users;

-- Create new table
CREATE TABLE dbo.users (
    id BIGINT IDENTITY(1,1) NOT NULL,
    name NVARCHAR(255) NOT NULL,
    email NVARCHAR(255) NOT NULL,
    email_verified_at DATETIME NULL,
    password NVARCHAR(255) NOT NULL,
    remember_token NVARCHAR(100) NULL,
    created_at DATETIME NULL,
    updated_at DATETIME NULL,
    status NVARCHAR(255) DEFAULT 'aktif' NOT NULL,
    [role] NVARCHAR(255) NULL,
    pin NVARCHAR(255) NULL,
    CONSTRAINT PK__users__3213E83F99303A5E PRIMARY KEY (id)
);

-- Create unique index
CREATE UNIQUE NONCLUSTERED INDEX users_email_unique 
ON dbo.users (email ASC);
```

## Migration Guide

### Jika Tabel Users Sudah Ada

**Option 1: Drop & Recreate (Data akan hilang!)**
```sql
-- Jalankan di SQL Server Management Studio
USE HRAPP;
DROP TABLE users;
-- Restart aplikasi Flask, table akan dibuat otomatis
```

**Option 2: Manual Migration (Preserve data)**
```sql
-- 1. Backup data lama
SELECT * INTO users_backup FROM users;

-- 2. Drop & create new table
DROP TABLE users;
-- Restart Flask app

-- 3. Migrate data (sesuaikan mapping)
INSERT INTO users (name, email, password, status, [role], created_at, updated_at)
SELECT 
    full_name as name,
    email,
    password_hash as password,
    CASE WHEN is_active = 1 THEN 'aktif' ELSE 'nonaktif' END as status,
    'user' as [role],
    created_at,
    updated_at
FROM users_backup;
```

### Jika Tabel Users Belum Ada

Tidak perlu action khusus! Tabel akan dibuat otomatis saat aplikasi start.

## Testing

### 1. Cek Struktur Table
```sql
SELECT 
    COLUMN_NAME,
    DATA_TYPE,
    CHARACTER_MAXIMUM_LENGTH,
    IS_NULLABLE,
    COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'users'
ORDER BY ORDINAL_POSITION;
```

### 2. Test Login
```
URL: http://localhost:5000/auth/login
Email: admin@absensi.com
Password: admin123
```

### 3. Cek Session
```python
# Di route yang sudah login, cek session:
print(session.get('user_name'))  # Administrator
print(session.get('user_role'))  # admin
print(session.get('user_pin'))   # None
```

### 4. Test Role Check
```python
from app.models.user import User

user = User.find_by_email('admin@absensi.com')
print(user.is_active())  # True
print(user.is_admin())   # True
print(user.status)       # 'aktif'
print(user.role)         # 'admin'
```

## API Changes

### User Dictionary
```python
# Before
user.to_dict()
{
    'id': 1,
    'email': 'admin@absensi.com',
    'full_name': 'Administrator',
    'is_active': True
}

# After
user.to_dict()
{
    'id': 1,
    'email': 'admin@absensi.com',
    'name': 'Administrator',
    'status': 'aktif',
    'role': 'admin',
    'pin': None
}
```

## Breaking Changes

⚠️ **Field name changes:**
- `full_name` → `name`
- `password_hash` → `password`
- `is_active` (BIT) → `status` (NVARCHAR)

⚠️ **Type changes:**
- `id`: INT → BIGINT
- `is_active`: BIT → `status` NVARCHAR

⚠️ **Method changes:**
- `user.is_active` (property) → `user.is_active()` (method)

## Rollback Plan

Jika perlu rollback ke struktur lama:

1. Restore dari backup:
```sql
DROP TABLE users;
SELECT * INTO users FROM users_backup;
```

2. Revert code changes di git:
```bash
git checkout HEAD~1 app/models/user.py
git checkout HEAD~1 app/controllers/auth_controller.py
```

3. Restart aplikasi

---

**Updated:** October 28, 2025  
**Status:** ✅ Ready for deployment  
**Compatibility:** Breaking changes - requires migration
