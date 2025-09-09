#!/usr/bin/env python3
"""
Standalone script untuk menjalankan Attendance Worker
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.workers.attendance_worker import run_worker

if __name__ == '__main__':
    print("🚀 Starting Attendance Worker...")
    print("Worker akan berjalan setiap 2 jam untuk memproses antrian absensi")
    print("Tekan Ctrl+C untuk menghentikan worker\n")
    
    try:
        run_worker()
    except KeyboardInterrupt:
        print("\n🛑 Worker dihentikan oleh user")
    except Exception as e:
        print(f"\nWorker error: {str(e)}")
        sys.exit(1)
