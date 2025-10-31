"""
Test script untuk VPS WorkingHours Push functionality
"""

import sys
import os
sys.path.append(os.getcwd())

from datetime import datetime, timedelta
from app.services.vps_push_service import vps_push_service

def print_section(title):
    """Print formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def test_get_workinghours_data():
    """Test getting workinghours data from database"""
    print_section("TEST 1: Get WorkingHours Data from Database")
    
    # Test dengan date range
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"📅 Date Range: {yesterday} to {today}")
    print(f"🔢 Limit: 5 records")
    
    data = vps_push_service.get_workinghours_data(
        start_date=yesterday,
        end_date=today,
        limit=5
    )
    
    print(f"\n✅ Retrieved {len(data)} records")
    
    if data:
        print("\n📋 Sample Record Fields:")
        for key in data[0].keys():
            print(f"   - {key}: {data[0][key]}")
    else:
        print("⚠️  No data found")
    
    return len(data) > 0

def test_workinghours_preview():
    """Test preview workinghours payload"""
    print_section("TEST 2: Preview WorkingHours Payload")
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    print(f"📅 Date: {today}")
    print(f"🔢 Limit: 2 records")
    
    preview = vps_push_service.get_workinghours_preview(
        start_date=today,
        end_date=today,
        limit=2
    )
    
    if 'error' in preview:
        print(f"❌ Error: {preview['error']}")
        return False
    
    records = preview.get('records', [])
    print(f"\n✅ Preview generated: {len(records)} records")
    
    if records:
        print("\n📝 Payload Structure:")
        import json
        print(json.dumps(preview, indent=2, ensure_ascii=False, default=str))
    
    return len(records) > 0

def test_push_workinghours_dry_run():
    """Test push workinghours (dry run - shows what would be sent)"""
    print_section("TEST 3: Push WorkingHours (Dry Run)")
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    print(f"📅 Date: {today}")
    print("⚠️  This is a DRY RUN - will show payload but not actually push")
    print("   (VPS API might not be configured or reachable)")
    
    # Get data yang akan di-push
    data = vps_push_service.get_workinghours_data(
        start_date=today,
        end_date=today,
        limit=2
    )
    
    if not data:
        print("\n⚠️  No WorkingHours data found for today")
        print("   This is expected if spJamkerja hasn't been run today")
        return False
    
    print(f"\n✅ Found {len(data)} records that would be pushed")
    print("\n📊 Sample Record that would be sent:")
    
    import json
    sample = {
        "id": data[0].get('id'),
        "pin": data[0].get('pin'),
        "name": data[0].get('name'),
        "working_date": data[0].get('working_date'),
        "shift": data[0].get('shift'),
        "check_in": data[0].get('check_in'),
        "check_out": data[0].get('check_out'),
        "workinghours": data[0].get('workinghours'),
        "overtime": data[0].get('overtime'),
        "workingdays": data[0].get('workingdays')
    }
    print(json.dumps(sample, indent=2, ensure_ascii=False, default=str))
    
    print("\n💡 To actually push to VPS, call:")
    print("   success, msg = vps_push_service.push_workinghours_today()")
    
    return True

def test_api_configuration():
    """Test VPS API configuration"""
    print_section("TEST 4: VPS API Configuration")
    
    stats = vps_push_service.get_push_statistics()
    
    print("📊 Configuration Status:")
    print(f"   Push Enabled: {'✅ YES' if stats['push_enabled'] else '❌ NO'}")
    print(f"   API URL: {stats['api_url']}")
    print(f"   Timeout: {stats['timeout']} seconds")
    print(f"   Retry Count: {stats['retry_count']}")
    
    if not stats['push_enabled']:
        print("\n⚠️  VPS Push is DISABLED")
        print("   To enable, set in .env:")
        print("   VPS_PUSH_ENABLED=True")
        print("   VPS_API_URL=https://your-vps.com/api")
        print("   VPS_API_KEY=your_secret_key")
    
    return stats['push_enabled']

def main():
    """Run all tests"""
    print("\n" + "🧪 " + "="*78)
    print("  VPS WORKINGHOURS PUSH - FUNCTIONALITY TEST")
    print("="*80)
    
    results = {}
    
    # Test 1: Get data from database
    try:
        results['get_data'] = test_get_workinghours_data()
    except Exception as e:
        print(f"\n❌ Test 1 Failed: {e}")
        results['get_data'] = False
    
    # Test 2: Preview payload
    try:
        results['preview'] = test_workinghours_preview()
    except Exception as e:
        print(f"\n❌ Test 2 Failed: {e}")
        results['preview'] = False
    
    # Test 3: Dry run push
    try:
        results['dry_run'] = test_push_workinghours_dry_run()
    except Exception as e:
        print(f"\n❌ Test 3 Failed: {e}")
        results['dry_run'] = False
    
    # Test 4: Configuration
    try:
        results['config'] = test_api_configuration()
    except Exception as e:
        print(f"\n❌ Test 4 Failed: {e}")
        results['config'] = False
    
    # Summary
    print_section("TEST SUMMARY")
    
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {test_name.upper()}: {status}")
    
    print(f"\n📊 Overall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\n🎉 All tests passed! WorkingHours push functionality is working!")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    print("\n" + "="*80)
    print("💡 NEXT STEPS:")
    print("="*80)
    print("1. Configure VPS API in .env file:")
    print("   VPS_API_URL=https://your-vps.com/api")
    print("   VPS_API_KEY=your_secret_key")
    print("   VPS_PUSH_ENABLED=True")
    print("")
    print("2. Test API endpoints using curl or Postman:")
    print("   POST http://127.0.0.1:5000/vps-push/workinghours/preview")
    print("   POST http://127.0.0.1:5000/vps-push/workinghours/push/today")
    print("")
    print("3. See full documentation: VPS_WORKINGHOURS_PUSH_API.md")
    print("="*80 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
