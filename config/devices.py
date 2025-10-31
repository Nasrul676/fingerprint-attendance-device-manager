"""
Device Configuration for Fingerprint Attendance System
Centralized configuration for all fingerprint devices
"""

# === Konfigurasi Mesin Absensi (Fingerprint Devices) ===
# Tambahkan atau hapus mesin sesuai kebutuhan di dalam list ini
FINGERPRINT_DEVICES = [
    
]

# === Fingerspot API Configuration ===
# Konfigurasi khusus untuk API Fingerspot Developer
FINGERSPOT_API_CONFIG = {
    'base_url': 'https://developer.fingerspot.io/api',  # Ganti dengan URL API yang benar
    'version': 'v1',
    'endpoints': {
        'attendance': '/get_attlog',  # Updated endpoint for attendance logs
        'devices': '/get_device',     # Endpoint for device info and connection test
        'employees': '/employees'
    },
    'headers': {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    },
    'timeout': 30,
    'retry_count': 3,
    'retry_delay': 5
}

# === Online Attendance API Configuration ===
ONLINE_ATTENDANCE_API_CONFIG = {
    'base_url': 'https://pkpapi.pradha.co.id/api',
    'version': 'v1',
    'endpoints': {
        'attendance': '/mobileatt', # Endpoint yang benar
    },
    'headers': {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    },
    'timeout': 30,
    'retry_count': 3,
    'retry_delay': 5
}


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
    '103': {
        'punch_0': 'I',     # fpid 0 → status 'I' (huruf besar)
        'punch_1': 'O',     # fpid 1 → status 'O' (huruf besar)
        'punch_4': 'i',     # fpid 4 → status 'i' (huruf kecil)
        'punch_5': 'o',     # fpid 5 → status 'o' (huruf kecil)
        'punch_i': 'i',     # untuk punch 'i' → status 'i'
        'punch_other': 'I'  # Default to 'I'
    },
    '201': {
        # Device 201 khusus untuk mesin pulang dengan format P1 MASUK-X
        # dimana X = status_scan + 1
        # status_scan 0 → P1 MASUK-1, status_scan 1 → P1 MASUK-2, dst.
        'device_type': 'fingerspot_masuk',
        'format_pattern': 'P1 MASUK-{increment}',  # {increment} = status_scan + 1
        'punch_0': 'P1 MASUK-1',     # status_scan 0 → P1 MASUK-1
        'punch_1': 'P1 MASUK-2',     # status_scan 1 → P1 MASUK-2
        'punch_2': 'P1 MASUK-3',     # status_scan 2 → P1 MASUK-3
        'punch_3': 'P1 MASUK-4',     # status_scan 3 → P1 MASUK-4
        'punch_4': 'P1 MASUK-5',     # status_scan 4 → P1 MASUK-5
        'punch_5': 'P1 MASUK-6',     # status_scan 5 → P1 MASUK-6
        'punch_6': 'P1 MASUK-7',     # status_scan 6 → P1 MASUK-7
        'punch_7': 'P1 MASUK-8',     # status_scan 7 → P1 MASUK-8
        'punch_8': 'P1 MASUK-9',     # status_scan 8 → P1 MASUK-9
        'punch_9': 'P1 MASUK-10',    # status_scan 9 → P1 MASUK-10
        'punch_other': 'P1 MASUK-1'  # Default ke P1 MASUK-1 jika status_scan tidak dikenal
    },
    '203': {
        'device_type': 'fingerspot_pulang',
        'format_pattern': 'P1 PULANG-{increment}',  # {increment} = status_scan + 1
        'punch_0': 'P1 PULANG-1',     # status_scan 0 → P1 PULANG-1
        'punch_1': 'P1 PULANG-2',     # status_scan 1 → P1 PULANG-2
        'punch_2': 'P1 PULANG-3',     # status_scan 2 → P1 PULANG-3
        'punch_3': 'P1 PULANG-4',     # status_scan 3 → P1 PULANG-4
        'punch_4': 'P1 PULANG-5',     # status_scan 4 → P1 PULANG-5
        'punch_5': 'P1 PULANG-6',     # status_scan 5 → P1 PULANG-6
        'punch_6': 'P1 PULANG-7',     # status_scan 6 → P1 PULANG-7
        'punch_7': 'P1 PULANG-8',     # status_scan 7 → P1 PULANG-8
        'punch_8': 'P1 PULANG-9',     # status_scan 8 → P1 PULANG-9
        'punch_9': 'P1 PULANG-10',    # status_scan 9 → P1 PULANG-10
        'punch_other': 'P1 PULANG-1'  # Default ke P1 PULANG-1 jika status_scan tidak dikenal
    },
    'Absensi Online': {
        'device_type': 'online_attendance',
        'I': '114',  # Status 'I' maps to machine '114'
        'O': '112',  # Status 'O' maps to machine '112'
        'punch_other': '112' # Default machine
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
    '103': 'Makan',
    '201': 'P1 Masuk',
    '203': 'P1 Pulang',
    'Absensi Online': 'Absensi Online'
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

def get_devices_by_connection_type(connection_type):
    """Get devices filtered by connection type"""
    return [device for device in FINGERPRINT_DEVICES if device.get('connection_type') == connection_type]

def get_zk_devices():
    """Get devices that use standard ZK connection"""
    return get_devices_by_connection_type('zk')

def get_fingerspot_api_devices():
    """Get devices that use Fingerspot API connection"""
    return get_devices_by_connection_type('fingerspot_api')

def is_fingerspot_device(device_name):
    """Check if device uses Fingerspot API"""
    device = get_device_by_name(device_name)
    return device and device.get('connection_type') == 'fingerspot_api'

def get_fingerspot_config(device_name):
    """Get Fingerspot API configuration for a specific device"""
    device = get_device_by_name(device_name)
    if device and device.get('connection_type') == 'fingerspot_api':
        return device.get('api_config', {})
    return None

def determine_status(device_name, punch_code):
    """
    Determine attendance status based on device name and punch code
    Returns status value (I/O for string devices, 0/1 for binary devices)
    
    Args:
        device_name (str): Name of the device (e.g., '104', '108', etc.)
        punch_code (int/str): Punch code from the device
    
    Returns:
        str/int: Status value based on device rules
    """
    try:
        # Convert punch_code to proper type if needed
        if isinstance(punch_code, str) and punch_code.isdigit():
            punch_code = int(punch_code)
        
        # Check if device has specific rules
        if device_name in DEVICE_STATUS_RULES:
            rules = DEVICE_STATUS_RULES[device_name]
            
            # Handle special case for device 102 (binary status)
            if device_name == '102':
                if punch_code == 2:
                    return rules['punch_2']
                elif punch_code == 3:
                    return rules['punch_3']
                else:
                    return rules['punch_other']
            
            # Handle special case for device 201 (Fingerspot API with P1 MASUK-X format)
            elif device_name == '201':
                # Device 201 menggunakan format P1 MASUK-X dimana X = status_scan + 1
                if isinstance(punch_code, (int, str)) and str(punch_code).isdigit():
                    status_scan = int(punch_code)
                    increment = status_scan + 1
                    return f'P1 MASUK-{increment}'
                else:
                    # Fallback ke punch key lookup jika tidak numerik
                    punch_key = f'punch_{punch_code}'
                    return rules.get(punch_key, rules.get('punch_other', 'P1 MASUK-1'))
            
            # Handle other devices with string status
            else:
                # Create punch key for lookup
                punch_key = f'punch_{punch_code}'
                
                # Direct lookup for numeric punch codes
                if punch_key in rules:
                    return rules[punch_key]
                
                # Handle special string punch codes
                elif punch_code == 'i' and 'punch_i' in rules:
                    return rules['punch_i']
                elif punch_code == 'o' and 'punch_o' in rules:
                    return rules['punch_o']
                
                # Use default for device
                else:
                    return rules.get('punch_other', 'I')
        
        # Use default rules for devices without specific configuration
        default_rules = DEVICE_STATUS_RULES['default']
        if punch_code == 0:
            return default_rules['punch_0']
        elif punch_code == 1:
            return default_rules['punch_1']
        else:
            # Return the punch code itself if no mapping found
            return 'I'  # Default to 'I' (In) for unknown punch codes
            
    except Exception as e:
        # Log error and return safe default
        print(f"Error determining status for device {device_name}, punch {punch_code}: {e}")
        return 'I'  # Safe default

def get_status_display(device_name, punch_code):
    """
    Get human-readable status display text based on device and punch code
    
    Args:
        device_name (str): Name of the device
        punch_code (int/str): Punch code from device
    
    Returns:
        str: Human-readable status ('Masuk', 'Keluar', 'Istirahat', 'Unknown')
    """
    try:
        # Get the status value using determine_status
        status = determine_status(device_name, punch_code)
        
        # Handle binary status devices (like 102)
        if isinstance(status, int):
            if status == 0:
                return 'Masuk'
            elif status == 1:
                return 'Keluar'
            else:
                return 'Unknown'
        
        # Handle string status devices
        elif isinstance(status, str):
            # Handle special case for device 201 (P1 MASUK-X format)
            if device_name == '201' and status.startswith('P1 MASUK-'):
                # Extract increment number for display
                try:
                    increment = status.split('-')[1]
                    return f'P1 Masuk Ke-{increment}'
                except (IndexError, ValueError):
                    return 'P1 Masuk'
            # Handle standard status codes
            elif status.upper() == 'I':
                return 'Masuk'
            elif status.upper() == 'O':
                return 'Keluar'
            elif status.upper() == 'B':
                return 'Istirahat'
            else:
                return status  # Return the status as-is for custom formats
        
        # Fallback for unknown status types
        else:
            return 'Unknown'
            
    except Exception as e:
        print(f"Error getting status display for device {device_name}, punch {punch_code}: {e}")
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
        required_fields = ['name', 'ip', 'port', 'password', 'connection_type']
        for field in required_fields:
            if field not in device:
                errors.append(f"Missing required field '{field}' in device config")
        
        # Check for duplicate names
        if device['name'] in device_names:
            errors.append(f"Duplicate device name: {device['name']}")
        device_names.append(device['name'])
        
        # Check for duplicate IPs (allow 'online' as a special case)
        if device['ip'] != 'online' and device['ip'] in device_ips:
            errors.append(f"Duplicate device IP: {device['ip']}")
        device_ips.append(device['ip'])
        
        # Validate IP format (basic check)
        if device['ip'] != 'online':
            ip_parts = device['ip'].split('.')
            if len(ip_parts) != 4:
                errors.append(f"Invalid IP format for device {device['name']}: {device['ip']}")
        
        # Validate port range
        if not (0 <= device['port'] <= 65535):
            errors.append(f"Invalid port for device {device['name']}: {device['port']}")
        
        # Validate connection type
        valid_connection_types = ['zk', 'fingerspot_api', 'online_attendance']
        if device.get('connection_type') not in valid_connection_types:
            errors.append(f"Invalid connection_type for device {device['name']}: {device.get('connection_type')}")
        
        # Validate API config for relevant types
        if device.get('connection_type') in ['fingerspot_api', 'online_attendance']:
            api_config = device.get('api_config', {})
            
            # Required fields berbeda untuk setiap connection type
            if device.get('connection_type') == 'fingerspot_api':
                required_api_fields = ['base_url', 'api_key', 'device_id']
            elif device.get('connection_type') == 'online_attendance':
                required_api_fields = ['base_url']  # api_key optional untuk online_attendance
            
            for field in required_api_fields:
                if field not in api_config or not api_config[field]:
                    errors.append(f"Missing or empty '{field}' in api_config for device {device['name']}")
    
    return errors

# Run validation on import
_validation_errors = validate_device_config()
if _validation_errors:
    print("Device configuration validation errors:")
    for error in _validation_errors:
        print(f"  - {error}")

# === Compatibility Mapping ===
# For backward compatibility with existing code that uses DEVICE_CONFIG
DEVICE_CONFIG = {}
for device in FINGERPRINT_DEVICES:
    device_name = device['name']
    device_rules = DEVICE_STATUS_RULES.get(device_name, DEVICE_STATUS_RULES.get('default', {}))
    
    DEVICE_CONFIG[device_name] = {
        'name': device['name'],
        'ip': device['ip'],
        'port': device['port'],
        'password': device['password'],
        'description': device.get('description', ''),
        'location': device.get('location', ''),
        'connection_type': device.get('connection_type', 'zk'),
        'api_config': device.get('api_config', {}),
        'status_rules': device_rules
    }


