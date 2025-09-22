"""
Helper functions untuk menentukan status absensi berdasarkan device dan punch code
"""
from config.devices import DEVICE_STATUS_RULES

def determine_status_for_gagalabsens(device_name, status_raw):
    """
    Menentukan status dan machine untuk data gagalabsens berdasarkan device dan status raw
    
    Args:
        device_name (str): Nama device (misal: 'Absensi Online')
        status_raw (str): Status mentah dari API (misal: 'I', 'O', 'Masuk', 'Keluar')
        
    Returns:
        tuple: (machine, status) - machine identifier dan status yang sudah diformat
    """
    try:
        # Ambil aturan untuk device
        device_rules = DEVICE_STATUS_RULES.get(device_name, {})
        
        # Untuk device 'Absensi Online'
        if device_name == 'Absensi Online':
            # Mapping status dari API ke machine number
            if status_raw in ['I', 'IN', 'Masuk', 'masuk']:
                machine = device_rules.get('I', '114')  # Default machine untuk masuk
                status = 'Masuk'
            elif status_raw in ['O', 'OUT', 'Keluar', 'keluar']:
                machine = device_rules.get('O', '112')  # Default machine untuk keluar
                status = 'Keluar'
            else:
                machine = device_rules.get('punch_other', '112')  # Default machine
                status = f'Unknown ({status_raw})'
            
            return machine, status
        
        # Untuk device lain, gunakan aturan yang ada
        else:
            # Default behavior untuk device lain
            if status_raw in ['I', 'IN', 'Masuk', 'masuk']:
                return '114', 'Masuk'
            elif status_raw in ['O', 'OUT', 'Keluar', 'keluar']:
                return '112', 'Keluar'
            else:
                return '112', f'Unknown ({status_raw})'
    
    except Exception as e:
        # Return safe defaults jika ada error
        return '112', f'Error ({status_raw})'

def format_status_for_display(status):
    """
    Format status untuk ditampilkan dengan konsisten
    
    Args:
        status (str): Status mentah
        
    Returns:
        str: Status yang sudah diformat
    """
    status_mapping = {
        'I': 'Masuk',
        'O': 'Keluar',
        'IN': 'Masuk',
        'OUT': 'Keluar',
        'masuk': 'Masuk',
        'keluar': 'Keluar',
        'Masuk': 'Masuk',
        'Keluar': 'Keluar'
    }
    
    return status_mapping.get(status, status)

def validate_pin(pin):
    """
    Validasi format PIN karyawan
    
    Args:
        pin (str): PIN karyawan
        
    Returns:
        bool: True jika PIN valid
    """
    if not pin:
        return False
    
    # Convert to string dan strip whitespace
    pin_str = str(pin).strip()
    
    # PIN tidak boleh kosong
    if not pin_str:
        return False
    
    # PIN harus terdiri dari karakter yang valid (alphanumeric)
    if not pin_str.replace('-', '').replace('_', '').isalnum():
        return False
    
    return True

def parse_timestamp(timestamp_str):
    """
    Parse timestamp dari berbagai format
    
    Args:
        timestamp_str (str): String timestamp
        
    Returns:
        str: Timestamp dalam format YYYY-MM-DD HH:MM:SS atau None jika gagal
    """
    from datetime import datetime
    
    if not timestamp_str:
        return None
    
    # Daftar format yang didukung
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%d/%m/%Y %H:%M:%S',
        '%d-%m-%Y %H:%M:%S',
        '%Y/%m/%d %H:%M:%S'
    ]
    
    for fmt in formats:
        try:
            parsed_time = datetime.strptime(timestamp_str, fmt)
            return parsed_time.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            continue
    
    return None