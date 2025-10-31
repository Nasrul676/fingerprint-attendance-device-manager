# Setup dan Menjalankan Aplikasi dengan Autentikasi

## Quick Start

### 1. Restart Aplikasi
```bash
# Stop Flask jika sedang berjalan (Ctrl+C)
# Kemudian jalankan:
start_production.bat
```

### 2. Login ke Aplikasi
Buka browser dan akses: `http://localhost:5000`

Anda akan diarahkan ke halaman login secara otomatis.

**Login Credentials:**
```
Email: admin@absensi.com
Password: admin123
```

### 3. Akses Scheduler Dashboard
Setelah login, Anda dapat mengakses:
- **Scheduler Menu** di navbar (icon 🕐)
- **URL Direct:** `http://localhost:5000/scheduler/dashboard`

## Apa yang Berubah?

### ✅ Fitur Baru:
1. **Sistem Autentikasi**
   - Login page dengan email & password
   - Session management
   - Password hashing untuk keamanan
   - Auto-redirect ke login jika belum login

2. **Menu Scheduler**
   - Menu baru di navbar: "Scheduler"
   - Akses dashboard spJamkerja Scheduler
   - Protected dengan login requirement

3. **User Menu**
   - Nama user ditampilkan di navbar (kanan atas)
   - Dropdown menu dengan opsi Logout

### 🔒 Protected Routes:
Semua halaman sekarang memerlukan login:
- `/` (Dashboard utama)
- `/fplog/dashboard` (Data Absensi)
- `/failed-logs/dashboard` (Gagal Absen)
- `/attendance-report/` (Laporan)
- `/sync/dashboard` (Device Sync)
- `/vps-push/dashboard` (VPS Push)
- `/scheduler/dashboard` (Scheduler - BARU!)
- `/export` (Export CSV)

### 📁 File Baru:
```
app/
├── models/
│   └── user.py                      # User model
├── controllers/
│   └── auth_controller.py           # Login/logout
├── templates/
│   └── auth/
│       └── login.html               # Login page
├── utils/
│   └── auth_middleware.py           # Security decorator
docs/
└── authentication_guide.md          # Dokumentasi lengkap
```

## Database Changes

### Table Baru: `users`
Akan dibuat otomatis saat aplikasi pertama kali dijalankan:

```sql
CREATE TABLE users (
    id INT IDENTITY(1,1) PRIMARY KEY,
    email NVARCHAR(255) UNIQUE NOT NULL,
    password_hash NVARCHAR(255) NOT NULL,
    full_name NVARCHAR(255) NOT NULL,
    is_active BIT DEFAULT 1,
    created_at DATETIME DEFAULT GETDATE(),
    updated_at DATETIME DEFAULT GETDATE()
)
```

### Default User
User admin akan dibuat otomatis dengan credentials:
- Email: `admin@absensi.com`
- Password: `admin123`

## Testing Checklist

### ✅ Test 1: Auto-create Table & User
```bash
# 1. Jalankan aplikasi
start_production.bat

# 2. Cek log untuk konfirmasi:
# [OK] Users table checked/created successfully
# [OK] Default user created: admin@absensi.com / admin123
# [OK] User authentication system initialized
```

### ✅ Test 2: Login Flow
```bash
# 1. Buka browser: http://localhost:5000
# 2. Akan redirect ke: http://localhost:5000/auth/login
# 3. Login dengan: admin@absensi.com / admin123
# 4. Akan redirect ke dashboard utama
# 5. Lihat nama user di navbar kanan atas
```

### ✅ Test 3: Scheduler Menu
```bash
# 1. Setelah login, lihat navbar
# 2. Ada menu "Scheduler" dengan icon jam
# 3. Klik menu Scheduler
# 4. Akan buka: http://localhost:5000/scheduler/dashboard
# 5. Dashboard scheduler tampil dengan:
#    - Status scheduler
#    - Next execution time
#    - Statistics
#    - Control buttons
```

### ✅ Test 4: Protected Routes
```bash
# 1. Logout (klik user menu → Logout)
# 2. Coba akses: http://localhost:5000/scheduler/dashboard
# 3. Akan redirect ke login dengan pesan warning
# 4. Setelah login, akan redirect ke URL yang dituju
```

### ✅ Test 5: User Menu
```bash
# 1. Login ke aplikasi
# 2. Lihat navbar kanan atas
# 3. Ada dropdown dengan nama/email user
# 4. Klik dropdown
# 5. Ada menu Logout
# 6. Klik Logout
# 7. Akan logout dan redirect ke login page
```

## Troubleshooting

### Issue: Table 'users' tidak ada
**Solution:**
Table akan dibuat otomatis. Jika tidak:
```sql
-- Jalankan di SQL Server Management Studio
CREATE TABLE users (
    id INT IDENTITY(1,1) PRIMARY KEY,
    email NVARCHAR(255) UNIQUE NOT NULL,
    password_hash NVARCHAR(255) NOT NULL,
    full_name NVARCHAR(255) NOT NULL,
    is_active BIT DEFAULT 1,
    created_at DATETIME DEFAULT GETDATE(),
    updated_at DATETIME DEFAULT GETDATE()
)
```

### Issue: Tidak bisa login dengan admin123
**Solution:**
```python
# Jalankan di Python console:
from app.models.user import User
User.create_default_user()
```

### Issue: Menu Scheduler tidak muncul
**Solution:**
- Clear browser cache (Ctrl+Shift+Del)
- Restart Flask application
- Cek bahwa base.html sudah terupdate

### Issue: Session hilang terus
**Solution:**
1. Cek SECRET_KEY di .env:
```env
SECRET_KEY=your-secret-key-here
```
2. Restart aplikasi

### Issue: Error "login_required not found"
**Solution:**
- Restart Flask application
- Pastikan semua file baru sudah di-create

## Verifikasi Database

### Cek Table Users:
```sql
-- Cek apakah table ada
SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'users'

-- Lihat semua users
SELECT id, email, full_name, is_active, created_at FROM users

-- Cek default admin
SELECT * FROM users WHERE email = 'admin@absensi.com'
```

### Cek Logs:
```powershell
# Lihat log aplikasi
Get-Content logs\attendance_app.log -Tail 50

# Cari log authentication
Get-Content logs\attendance_app.log | Select-String "User|auth|login|[OK]"
```

## Next Steps

### 1. Ganti Password Default
**⚠️ PENTING untuk Production:**
```sql
-- Update password admin (hash akan digenerate via aplikasi)
-- Gunakan Python console:
from app.models.user import User
from werkzeug.security import generate_password_hash
from config.database import get_db_connection

connection = get_db_connection()
cursor = connection.cursor()

new_password_hash = generate_password_hash('YourNewStrongPassword123!')

cursor.execute("""
    UPDATE users 
    SET password_hash = ?, updated_at = GETDATE()
    WHERE email = ?
""", (new_password_hash, 'admin@absensi.com'))

connection.commit()
connection.close()
```

### 2. Buat User Baru (Optional)
```python
from app.models.user import User

User.create_user(
    email="user2@absensi.com",
    password="password123",
    full_name="User Kedua"
)
```

### 3. Monitor Authentication
```powershell
# Real-time log monitoring
Get-Content logs\attendance_app.log -Wait | Select-String "User|login|logout"
```

## Security Notes

### ✅ Implemented:
- Password hashing dengan Werkzeug
- Session-based authentication
- Protected routes dengan @login_required
- Auto-redirect to login
- Security headers
- SQL injection prevention
- HTTP-only cookies
- Secure cookies (production)

### 📋 Recommended for Production:
1. **Ganti SECRET_KEY**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
   Simpan hasil ke `.env`

2. **Enable HTTPS**
   ```python
   # config.py
   SESSION_COOKIE_SECURE = True
   ```

3. **Strong Password Policy**
   - Minimal 12 karakter
   - Kombinasi huruf, angka, simbol
   - Tidak sama dengan username

4. **Regular Password Rotation**
   - Ganti password setiap 90 hari
   - Jangan reuse password lama

## Support

Untuk pertanyaan atau masalah:
1. Cek dokumentasi lengkap: `docs/authentication_guide.md`
2. Cek log: `logs/attendance_app.log`
3. Cek database: Pastikan table `users` ada dan berisi data

---

**Status:** ✅ Ready to Use
**Version:** 1.1.0 (Authentication Enabled)
**Updated:** October 28, 2025
