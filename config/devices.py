"""
Device Configuration for Fingerprint Attendance System
Centralized configuration for all fingerprint devices
"""

# === Konfigurasi Mesin Absensi (Fingerprint Devices) ===
# Tambahkan atau hapus mesin sesuai kebutuhan di dalam list ini
FINGERPRINT_DEVICES = [
    {
        'name': '104',
        'ip': '10.163.3.21',
        'port': 4370,
        'password': 1234567,
        'description': 'P2-IN',
        'location': 'P2'
    },
    {
        'name': '111',
        'ip': '10.163.3.176',
        'port': 4370,
        'password': 0,
        'description': 'Pelet',
        'location': 'Pelet'
    },
    {
        'name': '110',
        'ip': '10.163.2.159',
        'port': 4370,
        'password': 123456,
        'description': 'Blowing',
        'location': 'Blowing'
    },
    {
        'name': '108',
        'ip': '10.163.3.84',
        'port': 4370,
        'password': 0,
        'description': 'Karung',
        'location': 'Karung'
    },
    {
        'name': '102',
        'ip': '10.163.1.65',
        'port': 4370,
        'password': 0,
        'description': 'P2-OUT',
        'location': 'P2'
    },
    {
        'name': '103',
        'ip': '10.163.3.175',
        'port': 4370,
        'password': 12345,
        'description': 'Makan',
        'location': 'Makan'
    },
    {
        'name': '201',
        'ip': '10.163.3.205',
        'port': 4370,
        'password': 12345,
        'description': 'P1 Masuk',
        'location': 'P1'
    },
    {
        'name': '203',
        'ip': '10.163.3.228',
        'port': 4370,
        'password': 12345,
        'description': 'P1 Pulang',
        'location': 'P1'
    }
]

# === Device Status Mapping Rules ===
# Rules for determining attendance status based on device and punch code
DEVICE_STATUS_RULES = {
    '104': {
        'punch_0': 'I',     # fpid 0 → status 'I' (100% konsisten)
        'punch_4': 'i',     # fpid 4 → status 'i' (89% dominan)
        'punch_255': 'I',   # fpid 255 → status 'I' (100% konsisten)
        'punch_other': 'I'  # Default to 'I'
    },
    '108': {
        'punch_0': 'I',     # fpid 0 → status 'I' (huruf besar)
        'punch_1': 'O',     # fpid 1 → status 'O' (huruf besar)
        'punch_4': 'i',     # fpid 4 → status 'i' (huruf kecil)
        'punch_5': 'o',     # fpid 5 → status 'o' (huruf kecil)
        'punch_i': 'i',     # untuk punch 'i' → status 'i'
        'punch_other': 'I'  # Default to 'I'
    },
    '111': {
        'punch_0': 'I',     # fpid 0 → status 'I' (huruf besar)
        'punch_1': 'O',     # fpid 1 → status 'O' (huruf besar)
        'punch_4': 'i',     # fpid 4 → status 'i' (huruf kecil)
        'punch_5': 'o',     # fpid 5 → status 'o' (huruf kecil)
        'punch_i': 'i',     # untuk punch 'i' → status 'i'
        'punch_other': 'I'  # Default to 'I'
    },
    '110': {
        'punch_0': 'I',     # fpid 0 → status 'I' (huruf besar)
        'punch_1': 'O',     # fpid 1 → status 'O' (huruf besar)
        'punch_4': 'i',     # fpid 4 → status 'i' (huruf kecil)
        'punch_5': 'o',     # fpid 5 → status 'o' (huruf kecil)
        'punch_i': 'i',     # untuk punch 'i' → status 'i'
        'punch_other': 'I'  # Default to 'I'
    },
    '102': {
        'punch_2': 0,  # fpid 2 → status 0 (In)
        'punch_3': 1,  # fpid 3 → status 1 (Out)
        'punch_other': 0  # Default to In
    },
    'default': {
        'punch_0': 'I',  # In
        'punch_1': 'O'   # Out
    }
}

# === Device Display Names ===
# Mapping device names to human-readable display names
DEVICE_DISPLAY_NAMES = {
    '104': 'P2-IN',
    '111': 'Pelet', 
    '110': 'Blowing',
    '108': 'Karung',
    '102': 'P2-OUT',
    '103': 'Makan'
}

# === Helper Functions ===

def get_device_by_name(device_name):
    """Get device configuration by name"""
    for device in FINGERPRINT_DEVICES:
        if device['name'] == device_name:
            return device
    return None

def get_device_ip(device_name):
    """Get device IP address by name"""
    device = get_device_by_name(device_name)
    return device['ip'] if device else None

def get_device_display_name(device_name):
    """Get human-readable device display name"""
    return DEVICE_DISPLAY_NAMES.get(device_name, f'Device {device_name}')

def get_all_device_names():
    """Get list of all device names"""
    return [device['name'] for device in FINGERPRINT_DEVICES]

def get_all_device_ips():
    """Get list of all device IP addresses"""
    return [device['ip'] for device in FINGERPRINT_DEVICES]

def determine_status(device_name, punch_code):
    """
    Determine attendance status based on device name and punch code
    Returns status value (I/O for string devices, 0/1 for binary devices)
    """
    # Check if device has specific rules
    if device_name in DEVICE_STATUS_RULES:
        rules = DEVICE_STATUS_RULES[device_name]
        
        # Handle special case for device 102
        if device_name == '102':
            if punch_code == 2:
                return rules['punch_2']
            elif punch_code == 3:
                return rules['punch_3']
            else:
                return rules['punch_other']
        
        # Handle device 104 (P2-IN) with specific punch code mapping
        elif device_name == '104':
            if punch_code == 0:
                return rules['punch_0']
            elif punch_code == 4:
                return rules['punch_4']
            elif punch_code == 255:
                return rules['punch_255']
            else:
                return rules['punch_other']
        
        # Handle device 108 (Karung) with specific punch code mapping
        elif device_name == '108':
            if punch_code == 0:
                return rules['punch_0']
            elif punch_code == 1:
                return rules['punch_1']
            elif punch_code == 4:
                return rules['punch_4']
            elif punch_code == 5:
                return rules['punch_5']
            elif punch_code == 'i':
                return rules['punch_i']
            else:
                return rules['punch_other']
        
        # Handle device 111 (Pelet) with specific punch code mapping
        elif device_name == '111':
            if punch_code == 0:
                return rules['punch_0']
            elif punch_code == 1:
                return rules['punch_1']
            elif punch_code == 4:
                return rules['punch_4']
            elif punch_code == 5:
                return rules['punch_5']
            elif punch_code == 'i':
                return rules['punch_i']
            else:
                return rules['punch_other']
        
        # Handle device 110 (Blowing) with specific punch code mapping
        elif device_name == '110':
            if punch_code == 0:
                return rules['punch_0']
            elif punch_code == 1:
                return rules['punch_1']
            elif punch_code == 4:
                return rules['punch_4']
            elif punch_code == 5:
                return rules['punch_5']
            elif punch_code == 'i':
                return rules['punch_i']
            else:
                return rules['punch_other']
    
    # Use default rules
    default_rules = DEVICE_STATUS_RULES['default']
    if punch_code == 0:
        return default_rules['punch_0']
    elif punch_code == 1:
        return default_rules['punch_1']
    else:
        return punch_code
    # Return None if punch code is not recognized
    return None

def get_status_display(device_name, punch_code):
    """
    Get human-readable status display text
    """
    status = determine_status(device_name, punch_code)
    
    # Handle device 104 special status values
    if device_name == '104':
        if status in ['I', 'i']:
            return 'Masuk'
        elif status in ['O', 'o']:
            return 'Keluar'
        else:
            return 'Unknown'
    
    # Handle device 108 special status values
    elif device_name == '108':
        if status in ['I', 'i']:
            return 'Masuk'
        elif status in ['O', 'o']:
            return 'Keluar'
        else:
            return 'Unknown'
    
    # Handle device 111 special status values
    elif device_name == '111':
        if status in ['I', 'i']:
            return 'Masuk'
        elif status in ['O', 'o']:
            return 'Keluar'
        else:
            return 'Unknown'
    
    # Handle device 110 special status values
    elif device_name == '110':
        if status in ['I', 'i']:
            return 'Masuk'
        elif status in ['O', 'o']:
            return 'Keluar'
        else:
            return 'Unknown'
    
    # Default logic for other devices
    if status == 'I' or status == 0:
        return 'Masuk'
    elif status == 'O' or status == 1:
        return 'Keluar'
    elif status == 'B':
        return 'Istirahat'
    else:
        return 'Unknown'

def validate_device_config():
    """
    Validate device configuration for consistency
    Returns list of validation errors if any
    """
    errors = []
    device_names = []
    device_ips = []
    
    for device in FINGERPRINT_DEVICES:
        # Check required fields
        required_fields = ['name', 'ip', 'port', 'password']
        for field in required_fields:
            if field not in device:
                errors.append(f"Missing required field '{field}' in device config")
        
        # Check for duplicate names
        if device['name'] in device_names:
            errors.append(f"Duplicate device name: {device['name']}")
        device_names.append(device['name'])
        
        # Check for duplicate IPs
        if device['ip'] in device_ips:
            errors.append(f"Duplicate device IP: {device['ip']}")
        device_ips.append(device['ip'])
        
        # Validate IP format (basic check)
        ip_parts = device['ip'].split('.')
        if len(ip_parts) != 4:
            errors.append(f"Invalid IP format for device {device['name']}: {device['ip']}")
        
        # Validate port range
        if not (1 <= device['port'] <= 65535):
            errors.append(f"Invalid port for device {device['name']}: {device['port']}")
    
    return errors

# Run validation on import
_validation_errors = validate_device_config()
if _validation_errors:
    print("Device configuration validation errors:")
    for error in _validation_errors:
        print(f"  - {error}")
