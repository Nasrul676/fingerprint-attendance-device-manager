# Panduan Autentikasi Sistem Absensi

## Overview
Sistem autentikasi telah ditambahkan ke aplikasi untuk melindungi akses ke dashboard dan fitur-fitur sensitif. Semua pengguna harus login sebelum dapat mengakses aplikasi.

## Fitur Autentikasi

### 1. **Login System**
- Halaman login yang aman dengan validasi email dan password
- Session-based authentication menggunakan Flask session
- Password hashing menggunakan Werkzeug security
- Auto-create default user pada first run

### 2. **Default User**
Pada saat pertama kali aplikasi dijalankan, user default akan dibuat otomatis:

```
Email: admin@absensi.com
Password: admin123
```

**⚠️ PENTING:** Segera ganti password default setelah login pertama kali!

### 3. **Protected Routes**
Semua route/halaman dilindungi dengan decorator `@login_required`:
- Dashboard Absensi
- Data FPLog
- Failed Logs
- Sync Dashboard
- Attendance Report
- VPS Push
- **Scheduler Dashboard** (baru)
- Worker Dashboard
- Export CSV

### 4. **User Interface**
- **Login Page:** `/auth/login`
- **Logout:** Menu dropdown di navbar (klik nama user → Logout)
- **User Info:** Nama/email user ditampilkan di navbar

## Menu Baru

### Scheduler Dashboard
Menu baru telah ditambahkan ke navbar untuk mengakses spJamkerja Scheduler:

**Lokasi:** Navbar → "Scheduler"
**URL:** `http://localhost:5000/scheduler/dashboard`
**Icon:** 🕐 (Clock icon)

**Fitur:**
- Monitor status scheduler (Running/Stopped/Processing)
- Lihat jadwal eksekusi berikutnya
- Statistik eksekusi (total, sukses, gagal)
- Control buttons (Start/Stop/Force Execute)
- Set interval eksekusi

## Database Schema

### Table: users
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

## Cara Menambah User Baru

### Via SQL Server Management Studio:
```sql
-- Lihat semua users
SELECT * FROM users

-- Tambah user baru (password akan di-hash oleh aplikasi)
-- Gunakan aplikasi atau Python console untuk membuat user
```

### Via Python Console:
```python
from app.models.user import User

# Membuat user baru
User.create_user(
    email="user@example.com",
    password="password123",
    full_name="Nama Lengkap"
)
```

## API Endpoints Autentikasi

### 1. Login
```
POST /auth/login
Content-Type: application/x-www-form-urlencoded

email=admin@absensi.com&password=admin123
```

### 2. Logout
```
GET /auth/logout
```

### 3. Check Session
```
GET /auth/check-session

Response (logged in):
{
    "logged_in": true,
    "user": {
        "id": 1,
        "email": "admin@absensi.com",
        "full_name": "Administrator",
        "is_active": true
    }
}

Response (not logged in):
{
    "logged_in": false
}
```

## Security Features

### 1. **Password Security**
- Password di-hash menggunakan Werkzeug `generate_password_hash`
- Password tidak pernah disimpan dalam plain text
- Verifikasi password menggunakan `check_password_hash`

### 2. **Session Security**
- Session cookie dengan HTTP-only flag
- Session cookie dengan Secure flag (production)
- Session cookie dengan SameSite=Lax
- Auto-expire session saat logout

### 3. **Access Control**
- Middleware `@login_required` pada semua protected routes
- Redirect ke login page jika belum login
- Flash message untuk memberitahu user
- Simpan URL tujuan untuk redirect setelah login

### 4. **SQL Injection Prevention**
- Parameterized queries untuk semua database operations
- Prepared statements dengan pyodbc

## Troubleshooting

### Issue: "Table 'users' does not exist"
**Solution:**
```python
from app.models.user import User
User.create_table()
User.create_default_user()
```

### Issue: "Cannot login with default credentials"
**Solution:**
1. Cek apakah user table ada:
```sql
SELECT * FROM users
```

2. Reset default user:
```python
from app.models.user import User
from werkzeug.security import generate_password_hash
from config.database import get_db_connection

connection = get_db_connection()
cursor = connection.cursor()

# Delete old admin
cursor.execute("DELETE FROM users WHERE email = 'admin@absensi.com'")

# Create new admin
password_hash = generate_password_hash('admin123')
cursor.execute("""
    INSERT INTO users (email, password_hash, full_name, is_active)
    VALUES (?, ?, ?, 1)
""", ('admin@absensi.com', password_hash, 'Administrator'))

connection.commit()
connection.close()
```

### Issue: "Session not persisting"
**Solution:**
1. Pastikan SECRET_KEY sudah di-set di `.env`:
```env
SECRET_KEY=your-secret-key-here-change-this-in-production
```

2. Restart aplikasi Flask

### Issue: "Redirect loop ke login page"
**Solution:**
1. Clear browser cookies
2. Restart Flask application
3. Cek session configuration di `config.py`

## Best Practices

### 1. **Password Management**
- Gunakan password yang kuat (minimal 8 karakter)
- Kombinasi huruf besar, huruf kecil, angka, dan simbol
- Jangan gunakan password yang sama dengan sistem lain
- Ganti password secara berkala

### 2. **User Management**
- Buat user terpisah untuk setiap person
- Jangan share credentials
- Nonaktifkan user yang sudah tidak digunakan:
```sql
UPDATE users SET is_active = 0 WHERE email = 'old-user@example.com'
```

### 3. **Security Headers**
Sudah di-configure di `app/__init__.py`:
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Strict-Transport-Security (production only)

### 4. **Production Deployment**
Sebelum deploy ke production:

1. **Ganti SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```
Copy hasilnya ke `.env`:
```env
SECRET_KEY=hasil-generate-secret-key-di-atas
```

2. **Ganti Default Password:**
Login dengan admin@absensi.com, lalu update password di database

3. **Enable HTTPS:**
Set di `config.py`:
```python
SESSION_COOKIE_SECURE = True
PREFERRED_URL_SCHEME = 'https'
```

4. **Set Production Config:**
```bash
set FLASK_ENV=production
```

## Testing

### Test Login Flow:
```bash
# 1. Start aplikasi
python app.py

# 2. Buka browser
http://localhost:5000

# 3. Akan redirect ke login
http://localhost:5000/auth/login

# 4. Login dengan credentials:
Email: admin@absensi.com
Password: admin123

# 5. Akan redirect ke dashboard
http://localhost:5000/fplog/dashboard
```

### Test Protected Routes:
```bash
# Tanpa login - akan redirect ke /auth/login
curl http://localhost:5000/scheduler/dashboard

# Dengan login - akan tampil dashboard
# (gunakan browser dengan session)
```

## Logs

Authentication events dicatat di log:
```
[OK] User logged in: admin@absensi.com
[WARN] Failed login attempt: wrong@email.com
[OK] User logged out: admin@absensi.com
[OK] User authentication system initialized
[OK] Users table checked/created successfully
[OK] Default user created: admin@absensi.com / admin123
```

## File Structure

```
app/
├── models/
│   └── user.py                  # User model dengan authentication methods
├── controllers/
│   └── auth_controller.py       # Login/logout handlers
├── templates/
│   └── auth/
│       └── login.html           # Login page template
├── utils/
│   └── auth_middleware.py       # @login_required decorator
└── __init__.py                  # Register auth blueprint, initialize users table
```

## Changelog

### Version 1.1.0 - Authentication System
- ✅ Added user authentication system
- ✅ Created User model with password hashing
- ✅ Created login/logout controllers
- ✅ Created login page template
- ✅ Added @login_required middleware
- ✅ Protected all dashboard routes
- ✅ Added user menu dropdown in navbar
- ✅ Added Scheduler menu item in navbar
- ✅ Auto-create default admin user on first run
- ✅ Auto-create users table on app startup

## Support

Jika mengalami masalah dengan autentikasi:
1. Cek logs di `logs/attendance_app.log`
2. Cek koneksi database
3. Pastikan table `users` ada di database
4. Verify SECRET_KEY ada di .env
5. Clear browser cookies dan restart Flask

---

**Security Notice:** Sistem ini menggunakan session-based authentication yang cocok untuk internal application. Untuk production dengan high security requirements, pertimbangkan untuk menggunakan JWT tokens atau OAuth2.
