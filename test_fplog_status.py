"""
Test script untuk memverifikasi status yang tersimpan di FPLog sudah sesuai device rules
"""

import pyodbc
from datetime import datetime, timedelta
from config.devices import (
    FINGERPRINT_DEVICES,
    determine_status,
    get_status_display,
    get_device_display_name
)
from config.database import db_manager

def test_fplog_status_correctness():
    """Test apakah status di FPLog sudah sesuai dengan device rules"""
    print("=" * 70)
    print("TESTING FPLOG STATUS CORRECTNESS")
    print("=" * 70)
    
    try:
        # Connect to SQL Server
        conn = db_manager.get_sqlserver_connection()
        if not conn:
            print("❌ Cannot connect to SQL Server")
            return
        
        cursor = conn.cursor()
        
        # Get recent FPLog data for analysis
        query = """
            SELECT TOP 100
                PIN, Date, Machine, Status, fpid
            FROM FPLog
            WHERE Date >= DATEADD(day, -7, GETDATE())
            ORDER BY Date DESC
        """
        
        cursor.execute(query)
        records = cursor.fetchall()
        
        if not records:
            print("⚠️  No recent FPLog records found")
            return
        
        print(f"📊 Analyzing {len(records)} recent FPLog records...")
        print()
        
        # Group by device
        device_analysis = {}
        
        for record in records:
            pin, date, machine, status, fpid = record
            
            if machine not in device_analysis:
                device_analysis[machine] = {
                    'total_records': 0,
                    'status_counts': {},
                    'sample_records': []
                }
            
            device_analysis[machine]['total_records'] += 1
            device_analysis[machine]['status_counts'][status] = device_analysis[machine]['status_counts'].get(status, 0) + 1
            
            # Keep sample records for detailed analysis
            if len(device_analysis[machine]['sample_records']) < 5:
                device_analysis[machine]['sample_records'].append({
                    'pin': pin,
                    'date': date,
                    'status': status,
                    'fpid': fpid
                })
        
        # Analyze each device
        for device_name, analysis in device_analysis.items():
            device_desc = get_device_display_name(device_name)
            
            print(f"🔍 Device: {device_name} ({device_desc})")
            print(f"   📈 Total records: {analysis['total_records']}")
            print(f"   📊 Status distribution: {analysis['status_counts']}")
            
            # Analyze if status values look correct
            status_issues = []
            for status, count in analysis['status_counts'].items():
                # Check if status looks like punch code instead of converted status
                if isinstance(status, (int, str)):
                    if str(status).isdigit() and int(status) > 5:
                        status_issues.append(f"Suspicious numeric status: {status} (might be punch code)")
                    elif status not in ['I', 'O', 'i', 'o', '0', '1', 0, 1]:
                        status_issues.append(f"Unknown status format: {status}")
            
            if status_issues:
                print(f"   ⚠️  Potential issues:")
                for issue in status_issues:
                    print(f"      - {issue}")
            else:
                print(f"   ✅ Status values look correct")
            
            # Show sample records
            print(f"   📝 Sample records:")
            for sample in analysis['sample_records'][:3]:
                expected_status = "Unknown"
                try:
                    # We can't reverse-engineer the punch code, but we can show what we have
                    status_display = get_status_display(device_name, sample['status']) if isinstance(sample['status'], int) else sample['status']
                    print(f"      PIN {sample['pin']}: Status={sample['status']} -> {status_display}")
                except:
                    print(f"      PIN {sample['pin']}: Status={sample['status']} (cannot interpret)")
            
            print()
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()

def test_sync_status_conversion():
    """Test status conversion in sync process"""
    print("=" * 70)
    print("TESTING SYNC STATUS CONVERSION")
    print("=" * 70)
    
    # Test cases: (device, punch_code, expected_status)
    test_cases = [
        ('104', 0, 'I'),
        ('104', 4, 'i'),
        ('104', 255, 'I'),
        ('108', 0, 'I'),
        ('108', 1, 'O'),
        ('108', 4, 'i'),
        ('108', 5, 'o'),
        ('102', 2, 0),
        ('102', 3, 1),
        ('111', 0, 'I'),
        ('111', 1, 'O'),
        ('111', 4, 'i'),
        ('111', 5, 'o'),
        ('103', 0, 'I'),
        ('103', 1, 'O'),
        ('201', 0, 'I'),
        ('201', 1, 'O'),
        ('203', 0, 'I'),
        ('203', 1, 'O'),
    ]
    
    print("🧪 Testing status conversion logic...")
    
    all_passed = True
    for device_name, punch_code, expected_status in test_cases:
        actual_status = determine_status(device_name, punch_code)
        status_display = get_status_display(device_name, punch_code)
        
        if actual_status == expected_status:
            print(f"✅ {device_name} punch {punch_code}: {actual_status} ({status_display})")
        else:
            print(f"❌ {device_name} punch {punch_code}: Expected {expected_status}, got {actual_status}")
            all_passed = False
    
    if all_passed:
        print("\n🎉 All status conversion tests passed!")
    else:
        print("\n⚠️  Some status conversion tests failed!")

def main():
    """Run all tests"""
    try:
        test_sync_status_conversion()
        print()
        test_fplog_status_correctness()
        
        print("=" * 70)
        print("RECOMMENDATION")
        print("=" * 70)
        print("✅ After fixing the attendance model, new sync operations should store")
        print("   the correct status values (I, O, i, o, 0, 1) instead of punch codes.")
        print()
        print("🔄 To fix existing data, you may need to:")
        print("   1. Re-sync recent data from devices")
        print("   2. Or run a data correction script")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
