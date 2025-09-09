"""
Test script to validate device status rules
This script tests the device status determination for all configured devices
"""

from config.devices import (
    FINGERPRINT_DEVICES,
    DEVICE_STATUS_RULES,
    determine_status,
    get_status_display,
    get_device_display_name,
    validate_device_config
)

def test_device_status_rules():
    """Test device status rules for all devices and common punch codes"""
    print("=" * 60)
    print("TESTING DEVICE STATUS RULES")
    print("=" * 60)
    
    # Test punch codes that are commonly used
    test_punch_codes = [0, 1, 2, 3, 4, 5, 'i', 'o', 255, 999]
    
    for device in FINGERPRINT_DEVICES:
        device_name = device['name']
        device_desc = device.get('description', 'Unknown')
        
        print(f"\n📱 Device: {device_name} ({device_desc})")
        print("-" * 40)
        
        # Check if device has specific rules
        if device_name in DEVICE_STATUS_RULES:
            print(f"✅ Has specific status rules")
            rules = DEVICE_STATUS_RULES[device_name]
            print(f"   Rules defined: {list(rules.keys())}")
        else:
            print(f"⚠️  Using default rules")
        
        # Test each punch code
        for punch_code in test_punch_codes:
            try:
                status = determine_status(device_name, punch_code)
                display = get_status_display(device_name, punch_code)
                print(f"   Punch {punch_code:>3} → Status: {status:>3} ({display})")
            except Exception as e:
                print(f"   Punch {punch_code:>3} → ERROR: {e}")

def test_device_config_validation():
    """Test device configuration validation"""
    print("\n" + "=" * 60)
    print("TESTING DEVICE CONFIGURATION VALIDATION")
    print("=" * 60)
    
    errors = validate_device_config()
    
    if errors:
        print("❌ Configuration errors found:")
        for error in errors:
            print(f"   - {error}")
    else:
        print("✅ Device configuration is valid")

def test_missing_devices():
    """Check for devices without status rules"""
    print("\n" + "=" * 60)
    print("CHECKING FOR MISSING DEVICE RULES")
    print("=" * 60)
    
    all_devices = [device['name'] for device in FINGERPRINT_DEVICES]
    devices_with_rules = list(DEVICE_STATUS_RULES.keys())
    devices_with_rules.remove('default')  # Remove default rule
    
    missing_devices = []
    for device_name in all_devices:
        if device_name not in devices_with_rules:
            missing_devices.append(device_name)
    
    if missing_devices:
        print("⚠️  Devices without specific rules (using default):")
        for device_name in missing_devices:
            device_info = next((d for d in FINGERPRINT_DEVICES if d['name'] == device_name), {})
            desc = device_info.get('description', 'Unknown')
            print(f"   - {device_name} ({desc})")
    else:
        print("✅ All devices have specific status rules")

def test_status_consistency():
    """Test status consistency across services"""
    print("\n" + "=" * 60)
    print("TESTING STATUS CONSISTENCY")
    print("=" * 60)
    
    # Test cases that should be consistent
    test_cases = [
        ('104', 0, 'I', 'Masuk'),
        ('104', 4, 'i', 'Masuk'),
        ('104', 255, 'I', 'Masuk'),
        ('108', 0, 'I', 'Masuk'),
        ('108', 1, 'O', 'Keluar'),
        ('108', 4, 'i', 'Masuk'),
        ('108', 5, 'o', 'Keluar'),
        ('102', 2, 0, 'Masuk'),
        ('102', 3, 1, 'Keluar'),
        ('111', 0, 'I', 'Masuk'),
        ('111', 1, 'O', 'Keluar'),
    ]
    
    all_passed = True
    
    for device_name, punch_code, expected_status, expected_display in test_cases:
        actual_status = determine_status(device_name, punch_code)
        actual_display = get_status_display(device_name, punch_code)
        
        status_ok = actual_status == expected_status
        display_ok = actual_display == expected_display
        
        if status_ok and display_ok:
            print(f"✅ {device_name} punch {punch_code}: {actual_status} ({actual_display})")
        else:
            print(f"❌ {device_name} punch {punch_code}: Expected {expected_status} ({expected_display}), got {actual_status} ({actual_display})")
            all_passed = False
    
    if all_passed:
        print("\n🎉 All consistency tests passed!")
    else:
        print("\n⚠️  Some consistency tests failed!")

def main():
    """Run all tests"""
    try:
        test_device_config_validation()
        test_missing_devices()
        test_device_status_rules()
        test_status_consistency()
        
        print("\n" + "=" * 60)
        print("DEVICE STATUS TESTING COMPLETED")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
