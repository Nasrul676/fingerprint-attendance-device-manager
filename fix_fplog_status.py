"""
Script untuk memperbaiki status di FPLog yang masih menggunakan punch code
Mengkonversi punch code ke status yang benar sesuai device rules
"""

from config.devices import determine_status, get_device_display_name
from config.database import db_manager
from datetime import datetime, timedelta

def fix_fplog_status_data():
    """Memperbaiki status di FPLog yang masih berupa punch code"""
    print("=" * 70)
    print("FIXING FPLOG STATUS DATA")
    print("=" * 70)
    
    try:
        # Connect to SQL Server
        conn = db_manager.get_sqlserver_connection()
        if not conn:
            print("❌ Cannot connect to SQL Server")
            return False
        
        cursor = conn.cursor()
        
        # Get FPLog data that might have punch codes as status
        # Focusing on recent data (last 30 days)
        query = """
            SELECT PIN, Date, Machine, Status, fpid
            FROM FPLog
            WHERE Date >= DATEADD(day, -30, GETDATE())
            AND (
                -- Likely punch codes (numeric values > 1)
                (ISNUMERIC(Status) = 1 AND CAST(Status AS INT) > 1)
                OR 
                -- Or specific known punch codes that shouldn't be status
                Status IN ('2', '3', '4', '5', '255')
            )
            ORDER BY Date DESC
        """
        
        cursor.execute(query)
        records = cursor.fetchall()
        
        if not records:
            print("✅ No records found with punch code status values")
            return True
        
        print(f"🔍 Found {len(records)} records that may need fixing...")
        
        # Analyze and fix records
        fixed_count = 0
        error_count = 0
        
        # Group by device for reporting
        device_fixes = {}
        
        for record in records:
            pin, date, machine, status, fpid = record
            
            try:
                # Convert current status (which is likely a punch code) back to punch code
                # and then determine the correct status
                punch_code = int(status) if str(status).isdigit() else status
                
                # Determine correct status using device rules
                correct_status = determine_status(machine, punch_code)
                
                if str(correct_status) != str(status):
                    # Update the record
                    update_query = """
                        UPDATE FPLog 
                        SET Status = ?
                        WHERE PIN = ? AND Date = ? AND Machine = ? AND Status = ?
                    """
                    
                    cursor.execute(update_query, (correct_status, pin, date, machine, status))
                    
                    if machine not in device_fixes:
                        device_fixes[machine] = []
                    
                    device_fixes[machine].append({
                        'pin': pin,
                        'date': date,
                        'old_status': status,
                        'new_status': correct_status,
                        'punch_code': punch_code
                    })
                    
                    fixed_count += 1
                    
            except Exception as e:
                print(f"❌ Error fixing record PIN {pin}, Status {status}: {e}")
                error_count += 1
        
        # Commit changes
        if fixed_count > 0:
            conn.commit()
            print(f"✅ Fixed {fixed_count} records")
            
            # Show details by device
            for device_name, fixes in device_fixes.items():
                device_desc = get_device_display_name(device_name)
                print(f"\n📱 Device {device_name} ({device_desc}): {len(fixes)} fixes")
                
                # Show sample fixes
                for i, fix in enumerate(fixes[:5]):  # Show first 5
                    print(f"   {i+1}. PIN {fix['pin']}: Punch {fix['punch_code']} -> Status {fix['old_status']} ➜ {fix['new_status']}")
                
                if len(fixes) > 5:
                    print(f"   ... and {len(fixes) - 5} more")
        
        if error_count > 0:
            print(f"⚠️  {error_count} records had errors during fixing")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error during fixing: {e}")
        import traceback
        traceback.print_exc()
        return False

def preview_fplog_fixes():
    """Preview apa yang akan diperbaiki tanpa mengubah data"""
    print("=" * 70)
    print("PREVIEW FPLOG STATUS FIXES")
    print("=" * 70)
    
    try:
        # Connect to SQL Server
        conn = db_manager.get_sqlserver_connection()
        if not conn:
            print("❌ Cannot connect to SQL Server")
            return False
        
        cursor = conn.cursor()
        
        # Get sample data for preview
        query = """
            SELECT TOP 20 PIN, Date, Machine, Status, fpid
            FROM FPLog
            WHERE Date >= DATEADD(day, -7, GETDATE())
            AND (
                -- Likely punch codes
                (ISNUMERIC(Status) = 1 AND CAST(Status AS INT) > 1)
                OR 
                Status IN ('2', '3', '4', '5', '255')
            )
            ORDER BY Date DESC
        """
        
        cursor.execute(query)
        records = cursor.fetchall()
        
        if not records:
            print("✅ No records found with potential punch code status values")
            return True
        
        print(f"🔍 Preview of {len(records)} records that would be fixed:")
        print()
        
        for i, record in enumerate(records, 1):
            pin, date, machine, status, fpid = record
            
            try:
                punch_code = int(status) if str(status).isdigit() else status
                correct_status = determine_status(machine, punch_code)
                
                device_desc = get_device_display_name(machine)
                
                if str(correct_status) != str(status):
                    print(f"{i:2d}. {machine} ({device_desc}) - PIN {pin}")
                    print(f"    Current Status: {status} → Correct Status: {correct_status}")
                    print(f"    Date: {date}")
                else:
                    print(f"{i:2d}. {machine} ({device_desc}) - PIN {pin} (already correct)")
                
                print()
                
            except Exception as e:
                print(f"{i:2d}. Error analyzing record: {e}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error during preview: {e}")
        return False

def main():
    """Main function"""
    print("FPLOG STATUS CORRECTION UTILITY")
    print("=" * 70)
    print()
    print("This script will fix FPLog records where Status contains")
    print("punch codes instead of proper status values (I, O, i, o, 0, 1)")
    print()
    
    try:
        # Show preview first
        preview_fplog_fixes()
        
        # Ask for confirmation (in production, you might want to add input())
        print("\n" + "=" * 70)
        print("APPLYING FIXES...")
        print("=" * 70)
        
        # Apply fixes
        success = fix_fplog_status_data()
        
        if success:
            print("\n🎉 FPLog status correction completed successfully!")
        else:
            print("\n❌ FPLog status correction failed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
