# Konfigurasi Device Fingerprint

File `devices.py` berisi konfigurasi terpusat untuk semua device fingerprint dalam sistem absensi. Semua file lain akan mengimpor konfigurasi dari file ini untuk memastikan konsistensi.

## Struktur Konfigurasi

### 1. FINGERPRINT_DEVICES
Array yang berisi semua device fingerprint beserta konfigurasinya:

```python
FINGERPRINT_DEVICES = [
    {
        'name': '104',
        'ip': '10.163.3.21',
        'port': 4370,
        'password': 1234567,
        'description': 'Device 104 - Main Entrance',
        'location': 'Main Building Entrance'
    },
    # ... device lainnya
]
```

**Field yang tersedia:**
- `name`: Nama/ID device (string)
- `ip`: IP Address device (string)
- `port`: Port komunikasi (integer, default: 4370)
- `password`: Password untuk koneksi ke device (integer)
- `description`: Deskripsi device (opsional)
- `location`: Lokasi fisik device (opsional)

### 2. DEVICE_STATUS_RULES
Aturan untuk mapping punch code ke status absensi:

```python
DEVICE_STATUS_RULES = {
    '104': {
        'punch_0': 'I',  # In
        'punch_other': 'O'  # Out
    },
    '102': {
        'punch_2': 0,  # In (binary)
        'punch_other': 1  # Out (binary)
    },
    'default': {
        'punch_0': 'I',  # In
        'punch_1': 'O'   # Out
    }
}
```

### 3. DEVICE_DISPLAY_NAMES
Mapping nama device ke nama yang ditampilkan di interface:

```python
DEVICE_DISPLAY_NAMES = {
    '104': 'Main Entrance Scanner',
    '111': 'Office Floor Scanner',
    # ... device lainnya
}
```

## Fungsi Helper

### get_device_by_name(device_name)
Mengambil konfigurasi device berdasarkan nama.

```python
device = get_device_by_name('104')
print(device['ip'])  # Output: 10.163.3.21
```

### determine_status(device_name, punch_code)
Menentukan status absensi berdasarkan device dan punch code.

```python
status = determine_status('104', 0)
print(status)  # Output: 'I' (Masuk)
```

### get_status_display(device_name, punch_code)
Mengambil teks display untuk status absensi.

```python
display = get_status_display('104', 0)
print(display)  # Output: 'Masuk'
```

### get_device_display_name(device_name)
Mengambil nama display device.

```python
display_name = get_device_display_name('104')
print(display_name)  # Output: 'Main Entrance Scanner'
```

## Cara Menggunakan

### 1. Import di File Python
```python
from config.devices import (
    FINGERPRINT_DEVICES,
    determine_status,
    get_status_display,
    get_device_display_name
)

# Gunakan device list
for device in FINGERPRINT_DEVICES:
    print(f"Connecting to {device['name']} at {device['ip']}")

# Tentukan status
status = determine_status('104', 0)
display = get_status_display('104', 0)
```

### 2. Menambah Device Baru
Untuk menambah device baru, edit array `FINGERPRINT_DEVICES` di `devices.py`:

```python
FINGERPRINT_DEVICES.append({
    'name': '115',
    'ip': '10.163.4.100',
    'port': 4370,
    'password': 123456,
    'description': 'Device 115 - Security Gate',
    'location': 'Security Checkpoint'
})
```

Lalu tambahkan display name di `DEVICE_DISPLAY_NAMES`:

```python
DEVICE_DISPLAY_NAMES['115'] = 'Security Gate Scanner'
```

### 3. Update Logika Status
Jika device baru memiliki logika status khusus, tambahkan di `DEVICE_STATUS_RULES`:

```python
DEVICE_STATUS_RULES['115'] = {
    'punch_0': 'I',
    'punch_1': 'O',
    'punch_2': 'B'  # Break
}
```

## Validasi Konfigurasi

File `devices.py` secara otomatis melakukan validasi saat diimpor:
- Memastikan semua field required ada
- Mengecek duplicate device name atau IP
- Validasi format IP dan range port
- Menampilkan error jika ada masalah konfigurasi

## File yang Menggunakan Konfigurasi Ini

1. `scripts/streaming_data.py` - Real-time streaming data
2. `scripts/automatic_update.py` - Automatic data update
3. `app/services/streaming_service.py` - Flask streaming service
4. `shared/notification_queue.py` - Notification system

## Tips Penggunaan

1. **Konsistensi**: Selalu gunakan helper functions daripada hardcode logika
2. **Validasi**: Jalankan script untuk memastikan tidak ada error validasi
3. **Backup**: Backup file `devices.py` sebelum melakukan perubahan besar
4. **Testing**: Test semua device setelah perubahan konfigurasi

## Troubleshooting

### Device Tidak Terhubung
1. Cek IP address dan port di konfigurasi
2. Pastikan password sesuai dengan setting device
3. Ping IP device untuk memastikan network connectivity

### Status Tidak Sesuai
1. Cek mapping di `DEVICE_STATUS_RULES`
2. Lihat punch code yang diterima di log
3. Update rules jika diperlukan

### Error Validasi
1. Periksa format IP address (contoh: 10.163.3.21)
2. Pastikan port dalam range 1-65535
3. Cek tidak ada duplicate name atau IP
