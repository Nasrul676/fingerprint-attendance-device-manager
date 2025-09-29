"""
Controller untuk Attendance Worker Dashboard
Mengelola monitoring dan kontrol worker untuk pemrosesan antrian absensi
"""

from flask import render_template, request, jsonify, session
from datetime import datetime, timedelta
import threading
import time
from app.workers.attendance_worker import AttendanceWorker
from app.models.attendance import AttendanceModel
from config.logging_config import get_worker_logger

logger = get_worker_logger()

class AttendanceWorkerController:
    def __init__(self):
        self.attendance_model = AttendanceModel()
        self.worker_instance = None
        self.worker_thread = None
        self.activity_log = []
        self.max_log_entries = 100
        
    def dashboard(self):
        """Render halaman dashboard worker"""
        try:
            return render_template('attendance_worker/dashboard.html')
        except Exception as e:
            logger.error(f"Error rendering worker dashboard: {str(e)}")
            return "Error loading dashboard", 500
    
    def get_worker_status(self):
        """API endpoint untuk mendapatkan status worker"""
        try:
            status_info = {
                'status': 'Berhenti',
                'thread_status': 'Tidak Aktif',
                'is_running': False,
                'thread_alive': False,
                'schedule_info': 'Belum ada jadwal',
                'next_run': 'Belum ada jadwal',
                'uptime': None
            }
            
            if self.worker_instance and self.worker_instance.is_running:
                status_info['status'] = 'Berjalan'
                status_info['is_running'] = True
                
                if self.worker_thread and self.worker_thread.is_alive():
                    status_info['thread_status'] = 'Aktif'
                    status_info['thread_alive'] = True
                
                # Mendapatkan informasi jadwal
                worker_status = self.worker_instance.get_status()
                if worker_status:
                    status_info['schedule_info'] = worker_status.get('schedule_info', 'Setiap 1 jam (0 jobs scheduled)')
                    next_run = worker_status.get('next_run')
                    if next_run:
                        status_info['next_run'] = next_run.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        status_info['next_run'] = 'Belum ada jadwal'
            
            return jsonify({
                'success': True,
                'worker_status': status_info
            })
            
        except Exception as e:
            logger.error(f"Error getting worker status: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error getting worker status: {str(e)}'
            }), 500
    
    def get_queue_statistics(self):
        """API endpoint untuk mendapatkan statistik antrian"""
        try:
            # Ambil semua data dari antrian (tanpa limit untuk data akurat)
            queue_records = self.attendance_model.get_attendance_queue()
            
            stats = {
                'total_records': len(queue_records),
                'status_counts': {
                    'baru': 0,
                    'diproses': 0,
                    'selesai': 0,
                    'error': 0
                },
                'today_records': 0,
                'pending_dates': []
            }
            
            today = datetime.now().date()
            pending_dates_set = set()
            
            for record in queue_records:
                # Use uppercase key as returned by model
                status = record.get('Status', 'unknown').lower()
                if status in stats['status_counts']:
                    stats['status_counts'][status] += 1
                
                # Hitung record hari ini - use uppercase Date key
                record_date = record.get('Date')
                if record_date and record_date.date() == today:
                    stats['today_records'] += 1
                
                # Kumpulkan tanggal yang masih pending (status 'baru')
                if status == 'baru' and record_date:
                    pending_dates_set.add(record_date.strftime('%Y-%m-%d'))
            
            stats['pending_dates'] = sorted(list(pending_dates_set))
            
            return jsonify({
                'success': True,
                'statistics': stats
            })
            
        except Exception as e:
            logger.error(f"Error getting queue statistics: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error getting queue statistics: {str(e)}'
            }), 500
    
    def start_worker(self):
        """API endpoint untuk memulai worker"""
        try:
            if self.worker_instance and self.worker_instance.is_running:
                return jsonify({
                    'success': False,
                    'message': 'Worker sudah berjalan'
                })
            
            # Buat instance worker baru
            self.worker_instance = AttendanceWorker()
            
            # Jalankan worker dalam thread terpisah
            self.worker_thread = threading.Thread(
                target=self.worker_instance.start_scheduler,
                name="AttendanceWorkerThread",
                daemon=True
            )
            self.worker_thread.start()
            
            # Tambahkan ke activity log
            self._add_to_activity_log("🚀 Worker dimulai melalui dashboard", 'SUCCESS')
            self._add_to_activity_log("⏰ Jadwal: Setiap 1 jam, memproses data 2 hari yang lalu", 'INFO')
            self._add_to_activity_log("📊 Status: Worker aktif dan siap memproses", 'INFO')
            
            logger.info("Attendance worker started via dashboard")
            
            return jsonify({
                'success': True,
                'message': 'Worker berhasil dijalankan'
            })
            
        except Exception as e:
            logger.error(f"Error starting worker: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error starting worker: {str(e)}'
            }), 500
    
    def stop_worker(self):
        """API endpoint untuk menghentikan worker"""
        try:
            if not self.worker_instance or not self.worker_instance.is_running:
                return jsonify({
                    'success': False,
                    'message': 'Worker tidak sedang berjalan'
                })
            
            # Hentikan worker
            self.worker_instance.stop_scheduler()
            
            # Tambahkan ke activity log
            self._add_to_activity_log("🛑 Worker dihentikan melalui dashboard", 'INFO')
            self._add_to_activity_log("⏸️ Jadwal otomatis dibatalkan", 'INFO')
            self._add_to_activity_log("📊 Status: Worker tidak aktif", 'INFO')
            
            logger.info("Attendance worker stopped via dashboard")
            
            return jsonify({
                'success': True,
                'message': 'Worker berhasil dihentikan'
            })
            
        except Exception as e:
            logger.error(f"Error stopping worker: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error stopping worker: {str(e)}'
            }), 500
    
    def run_now(self):
        """API endpoint untuk menjalankan worker sekali sekarang"""
        try:
            # Get JSON data from request if available
            data = request.get_json() if request.is_json else {}
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            pins_input = data.get('pins', '')
            pins = []
            if isinstance(pins_input, list):
                # If it's already a list, just use it (and ensure elements are strings)
                pins = [str(p).strip() for p in pins_input if str(p).strip()]
            elif isinstance(pins_input, str) and pins_input:
                # If it's a string, parse it
                pins = [pin.strip() for pin in pins_input.replace(',', '\n').split('\n') if pin.strip()]

            # Validate PINs if provided
            if pins and not all(isinstance(p, str) for p in pins):
                return jsonify({
                    'success': False,
                    'message': 'PINs harus berupa string dalam array/list'
                }), 400
            
            if not self.worker_instance:
                self.worker_instance = AttendanceWorker()
            
            # Jalankan pemrosesan dalam thread terpisah dengan parameter tanggal dan PINs
            process_thread = threading.Thread(
                target=self._run_process_now,
                args=(start_date, end_date, pins),
                name="ProcessNowThread",
                daemon=True
            )
            process_thread.start()
            
            # Tambahkan ke activity log
            filter_parts = []
            if start_date or end_date:
                filter_parts.append(f"Tanggal: {start_date or 'semua'} - {end_date or 'semua'}")
            if pins:
                pins_preview = pins[:3] + (['...'] if len(pins) > 3 else [])
                filter_parts.append(f"PINs: {', '.join(map(str, pins_preview))} ({len(pins)} total)")
            
            filter_info = f" (Filter: {'; '.join(filter_parts)})" if filter_parts else " (Semua data)"
            
            self._add_to_activity_log(f"🔄 Menjalankan pemrosesan manual{filter_info}", 'INFO')
            self._add_to_activity_log("🛠️ Thread pemrosesan dimulai dalam background", 'INFO')
            
            return jsonify({
                'success': True,
                'message': f'Pemrosesan manual dimulai{filter_info}'
            })
            
        except Exception as e:
            logger.error(f"Error running worker now: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error running worker now: {str(e)}'
            }), 500
    
    def get_activity_log(self):
        """API endpoint untuk mendapatkan activity log"""
        try:
            return jsonify({
                'success': True,
                'activity_log': self.activity_log
            })
            
        except Exception as e:
            logger.error(f"Error getting activity log: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error getting activity log: {str(e)}'
            }), 500
    
    def clear_activity_log(self):
        """API endpoint untuk membersihkan activity log"""
        try:
            self.activity_log = []
            self._add_to_activity_log("Activity log dibersihkan")
            
            return jsonify({
                'success': True,
                'message': 'Activity log berhasil dibersihkan'
            })
            
        except Exception as e:
            logger.error(f"Error clearing activity log: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error clearing activity log: {str(e)}'
            }), 500
    
    def download_log(self):
        """API endpoint untuk download log file"""
        try:
            # Implementasi download log file
            # Untuk saat ini, kembalikan URL ke log file
            return jsonify({
                'success': True,
                'message': 'Download log tidak tersedia saat ini',
                'log_path': '/logs/attendance_worker.log'
            })
            
        except Exception as e:
            logger.error(f"Error downloading log: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error downloading log: {str(e)}'
            }), 500
    
    def _run_process_now(self, start_date=None, end_date=None, pins=None):
        """Menjalankan pemrosesan worker sekarang dalam thread terpisah"""
        try:
            # Build filter info message
            filter_parts = []
            if start_date or end_date:
                filter_parts.append(f"tanggal: {start_date or 'semua'} - {end_date or 'semua'}")
            if pins:
                pins_preview = pins[:3] + (['...'] if len(pins) > 3 else [])
                filter_parts.append(f"PINs: {', '.join(map(str, pins_preview))} ({len(pins)} total)")
            
            filter_info = f" dengan filter {'; '.join(filter_parts)}" if filter_parts else ""
            
            self._add_to_activity_log(f"🚀 Memulai pemrosesan manual{filter_info}...", 'INFO')
            
            # Ensure worker instance exists
            if not self.worker_instance:
                self.worker_instance = AttendanceWorker()
                self._add_to_activity_log("🏭 Worker instance dibuat untuk pemrosesan manual", 'INFO')
            
            # Set callback untuk mendapatkan hasil processing
            self.worker_instance.set_activity_callback(self._add_to_activity_log)
            self._add_to_activity_log("🔗 Activity callback terhubung untuk real-time logging", 'INFO')
            
            # Call processing method with date and PINs parameters
            if start_date or end_date or pins:
                result = self.worker_instance.process_attendance_queue_with_filters(start_date, end_date, pins)
            else:
                result = self.worker_instance.process_attendance_queue()
            
            # Log hasil pemrosesan dengan detail
            if result:
                self._log_processing_result(result, start_date, end_date, pins)
            else:
                self._add_to_activity_log("💭 Pemrosesan manual selesai - tidak ada data untuk diproses", 'INFO')
                
        except Exception as e:
            self._add_to_activity_log(f"❌ Error dalam pemrosesan manual: {str(e)}", 'ERROR')
            logger.error(f"Error in manual processing: {str(e)}")
    
    def _add_to_activity_log(self, message, level='INFO'):
        """Menambahkan pesan ke activity log dengan level support"""
        try:
            timestamp = datetime.now().strftime('%d/%m/%Y, %H.%M.%S')
            
            # Add level indicator if not INFO
            if level != 'INFO':
                level_indicator = f"[{level}] "
            else:
                level_indicator = ""
            
            log_entry = f"[{timestamp}] {level_indicator}{message}"
            
            self.activity_log.append(log_entry)  # Append di akhir (log terbaru di bawah)
            
            # Batasi jumlah log entries - hapus yang paling lama (dari awal list)
            if len(self.activity_log) > self.max_log_entries:
                self.activity_log = self.activity_log[-self.max_log_entries:]
                
        except Exception as e:
            logger.error(f"Error adding to activity log: {str(e)}")
    
    def _log_processing_result(self, result, start_date=None, end_date=None, pins=None):
        """Log hasil pemrosesan worker dengan detail lengkap dan statistik"""
        try:
            if not result:
                return
            
            # Build filter info
            filter_parts = []
            if start_date or end_date:
                filter_parts.append(f"Tanggal: {start_date or 'semua'} - {end_date or 'semua'}")
            if pins:
                pins_preview = pins[:3] + (['...'] if len(pins) > 3 else [])
                filter_parts.append(f"PINs: {', '.join(map(str, pins_preview))} ({len(pins)} total)")
            
            filter_info = f" (Filter: {'; '.join(filter_parts)})" if filter_parts else ""
            
            # Determine success status
            is_success = result.get('success', False)
            emoji = "✅" if is_success else "❌"
            
            # Main completion message
            processing_time = result.get('processing_time', 0)
            self._add_to_activity_log(f"{emoji} Pemrosesan manual selesai{filter_info} dalam {processing_time:.2f} detik", 'SUCCESS' if is_success else 'ERROR')
            
            # Statistical summary
            total_records = result.get('total_records', 0)
            total_processed = result.get('total_processed', 0)
            successful = result.get('successful', 0)
            failed = result.get('failed', 0)
            successful_dates = result.get('successful_dates', 0)
            failed_dates = result.get('failed_dates', 0)
            
            self._add_to_activity_log(f"📊 Statistik Pemrosesan:", 'INFO')
            self._add_to_activity_log(f"   • Total Records Ditemukan: {total_records}", 'INFO')
            self._add_to_activity_log(f"   • Total Records Diproses: {total_processed}", 'INFO')
            self._add_to_activity_log(f"   • Berhasil: {successful} records", 'SUCCESS' if successful > 0 else 'INFO')
            if failed > 0:
                self._add_to_activity_log(f"   • Gagal: {failed} records", 'ERROR')
            
            self._add_to_activity_log(f"📅 Ringkasan Tanggal:", 'INFO')
            self._add_to_activity_log(f"   • Tanggal Berhasil: {successful_dates}", 'SUCCESS' if successful_dates > 0 else 'INFO')
            if failed_dates > 0:
                self._add_to_activity_log(f"   • Tanggal Gagal: {failed_dates}", 'ERROR')
            
            # Detail breakdown per tanggal
            date_details = result.get('date_details', [])
            if date_details:
                self._add_to_activity_log(f"📅 Detail Per Tanggal:", 'INFO')
                for detail in date_details[:5]:  # Tampilkan max 5 detail
                    date_str = detail.get('date')
                    success = detail.get('success', False)
                    record_count = detail.get('record_count', 0)
                    pin_count = detail.get('pin_count', 0)
                    processed = detail.get('processed', 0)
                    
                    status_icon = "✓" if success else "❌"
                    status_level = 'SUCCESS' if success else 'ERROR'
                    self._add_to_activity_log(f"   {status_icon} {date_str}: {processed}/{record_count} records, {pin_count} PINs", status_level)
                
                if len(date_details) > 5:
                    self._add_to_activity_log(f"   ... dan {len(date_details) - 5} tanggal lainnya", 'INFO')
            
            # Summary message
            summary = result.get('summary', '')
            if summary:
                self._add_to_activity_log(f"📝 {summary}", 'INFO')
                
        except Exception as e:
            self._add_to_activity_log(f"Error logging processing result: {str(e)}", 'ERROR')
            logger.error(f"Error logging processing result: {str(e)}")

# Global controller instance
attendance_worker_controller = AttendanceWorkerController()