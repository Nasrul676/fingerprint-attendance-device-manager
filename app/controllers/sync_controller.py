"""
Controller for handling FPLog synchronization operations
"""
from flask import jsonify, request, render_template
from datetime import datetime, timedelta
from app.services.sync_service import SyncService
from app.services.streaming_service import StreamingService
import sys
import os

# Add parent directory to path to import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from shared.notification_queue import notification_queue

class SyncController:
    """Controller for FPLog synchronization operations"""
    
    def __init__(self):
        self.sync_service = SyncService()
        self.streaming_service = StreamingService()
    
    def sync_dashboard(self):
        """Display sync dashboard page"""
        try:
            devices = self.sync_service.get_device_list()
            sync_summary = self.sync_service.get_device_sync_summary()
            
            return render_template('sync_dashboard.html', 
                                 devices=devices, 
                                 sync_summary=sync_summary)
        except Exception as e:
            return render_template('sync_dashboard.html', 
                                 error=f"Error loading dashboard: {str(e)}")
    
    def start_sync_all(self):
        """Start synchronization for all devices"""
        try:
            data = request.get_json() or {}
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            execute_procedures = data.get('execute_procedures', True)  # Default True untuk eksekusi prosedur
            
            # Convert date strings to date objects if provided
            start_date_obj = None
            end_date_obj = None
            
            if start_date:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            if end_date:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            success, message = self.sync_service.sync_all_devices(
                start_date_obj, end_date_obj, execute_procedures
            )
            
            response_data = {
                'success': success,
                'message': message,
                'sync_id': datetime.now().strftime('%Y%m%d_%H%M%S'),
                'execute_procedures': execute_procedures
            }
            
            if execute_procedures and start_date_obj and end_date_obj:
                response_data['procedures_info'] = f"Stored procedures (attrecord, spJamkerja) will be executed after sync completion for period {start_date} to {end_date}"
            elif execute_procedures:
                response_data['procedures_info'] = "Stored procedures will be skipped - no date range provided"
            
            return jsonify(response_data)
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error starting sync: {str(e)}'
            }), 500
    
    def start_sync_device(self, device_name):
        """Start synchronization for specific device"""
        try:
            data = request.get_json() or {}
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            
            # Find device config
            devices = self.sync_service.devices
            device_config = None
            for device in devices:
                if device['name'] == device_name:
                    device_config = device
                    break
            
            if not device_config:
                return jsonify({
                    'success': False,
                    'message': f'Device {device_name} not found'
                }), 404
            
            # Convert date strings to date objects if provided
            start_date_obj = None
            end_date_obj = None
            
            if start_date:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            if end_date:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            # Start sync in background thread
            import threading
            thread = threading.Thread(
                target=self.sync_service.sync_single_device,
                args=(device_config, start_date_obj, end_date_obj)
            )
            thread.daemon = True
            thread.start()
            
            return jsonify({
                'success': True,
                'message': f'Sync started for device {device_name}'
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error starting sync for device {device_name}: {str(e)}'
            }), 500
    
    def get_sync_status(self):
        """Get current synchronization status"""
        try:
            status = self.sync_service.get_sync_status()
            devices = self.sync_service.get_device_list()
            
            # Format datetime objects for JSON serialization
            formatted_status = {}
            for device_name, device_status in status.items():
                formatted_device_status = device_status.copy()
                
                # Format datetime fields
                for field in ['start_time', 'end_time']:
                    if field in formatted_device_status and formatted_device_status[field]:
                        formatted_device_status[field] = formatted_device_status[field].strftime('%Y-%m-%d %H:%M:%S')
                
                formatted_status[device_name] = formatted_device_status
            
            # Check if there are any active sync operations including procedure execution
            active_syncs = sum(1 for status_info in status.values() 
                             if status_info.get('status') in ['connecting', 'reading', 'syncing', 'processing', 'executing_procedures'])
            
            return jsonify({
                'success': True,
                'status': formatted_status,
                'devices': devices,
                'active_syncs': active_syncs,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error getting sync status: {str(e)}'
            }), 500
    
    def cancel_sync(self):
        """Cancel ongoing synchronization"""
        try:
            data = request.get_json() or {}
            device_name = data.get('device_name')
            
            success, message = self.sync_service.cancel_sync(device_name)
            
            return jsonify({
                'success': success,
                'message': message
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error cancelling sync: {str(e)}'
            }), 500
    
    def execute_stored_procedures(self):
        """Execute stored procedures manually"""
        try:
            data = request.get_json() or {}
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            
            if not start_date or not end_date:
                return jsonify({
                    'success': False,
                    'message': 'start_date and end_date are required'
                }), 400
            
            # Validate date format
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
                datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'Date format must be YYYY-MM-DD'
                }), 400
            
            # Execute procedures sequentially: attrecord FIRST, then spJamkerja
            results = {}
            
            # Step 1: Execute attrecord procedure FIRST
            print(f"🔄 Manual execution Step 1: Executing attrecord procedure for {start_date} to {end_date}")
            attrecord_success, attrecord_message = self.sync_service.attendance_model.execute_attrecord_procedure(
                start_date, end_date
            )
            results['attrecord'] = {
                'success': attrecord_success,
                'message': attrecord_message,
                'step': 1
            }
            
            # Step 2: Execute spJamkerja procedure ONLY if attrecord was successful
            if attrecord_success:
                print(f"✅ Step 1 completed: attrecord successful. Proceeding to Step 2: spJamkerja")
                spjamkerja_success, spjamkerja_message = self.sync_service.attendance_model.execute_spjamkerja_procedure(
                    start_date, end_date
                )
                results['spjamkerja'] = {
                    'success': spjamkerja_success,
                    'message': spjamkerja_message,
                    'step': 2
                }
                print(f"{'✅' if spjamkerja_success else '❌'} Step 2 completed: spJamkerja {'successful' if spjamkerja_success else 'failed'}")
            else:
                print(f"❌ Step 1 failed: attrecord failed. Skipping Step 2: spJamkerja")
                spjamkerja_success = False
                spjamkerja_message = "Skipped due to attrecord procedure failure"
                results['spjamkerja'] = {
                    'success': False,
                    'message': spjamkerja_message,
                    'step': 2,
                    'skipped': True
                }
            
            # Overall success - both procedures must succeed
            overall_success = attrecord_success and spjamkerja_success
            
            # Enhanced response message
            if overall_success:
                response_message = f'Both procedures executed successfully for period {start_date} to {end_date}'
            elif attrecord_success and not spjamkerja_success:
                response_message = f'attrecord completed but spJamkerja failed for period {start_date} to {end_date}'
            else:
                response_message = f'attrecord failed for period {start_date} to {end_date}. spJamkerja was skipped.'
            
            return jsonify({
                'success': overall_success,
                'message': response_message,
                'results': results,
                'execution_order': ['attrecord', 'spjamkerja'],
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error executing stored procedures: {str(e)}'
            }), 500
    
    def get_device_list(self):
        """Get list of configured devices with their status"""
        try:
            devices = self.sync_service.get_device_list()
            
            return jsonify({
                'success': True,
                'devices': devices
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error getting device list: {str(e)}'
            }), 500
    
    def get_sync_summary(self):
        """Get synchronization summary from database"""
        try:
            summary = self.sync_service.get_device_sync_summary()
            
            return jsonify({
                'success': True,
                'summary': summary
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error getting sync summary: {str(e)}'
            }), 500
    
    def sync_history(self):
        """Get synchronization history"""
        try:
            # Get query parameters
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 20))
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            
            # Get FPLog data from model
            from app.models.attendance import AttendanceModel
            model = AttendanceModel()
            logs, total, total_pages = model.get_fplog_data(start_date, end_date, page, per_page)
            
            if request.headers.get('Content-Type') == 'application/json':
                return jsonify({
                    'success': True,
                    'data': logs,
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': total,
                        'total_pages': total_pages
                    }
                })
            else:
                return render_template('sync_history.html',
                                     logs=logs,
                                     pagination={
                                         'page': page,
                                         'per_page': per_page,
                                         'total': total,
                                         'total_pages': total_pages
                                     })
            
        except Exception as e:
            if request.headers.get('Content-Type') == 'application/json':
                return jsonify({
                    'success': False,
                    'message': f'Error getting sync history: {str(e)}'
                }), 500
            else:
                return render_template('sync_history.html',
                                     error=f'Error getting sync history: {str(e)}')
    
    def test_device_connection(self, device_name):
        """Test connection to a specific device"""
        try:
            # Find device config
            devices = self.sync_service.devices
            device_config = None
            for device in devices:
                if device['name'] == device_name:
                    device_config = device
                    break
            
            if not device_config:
                return jsonify({
                    'success': False,
                    'message': f'Device {device_name} not found'
                }), 404
            
            # Check connection type and route accordingly
            connection_type = device_config.get('connection_type', 'zk')
            
            if connection_type == 'fingerspot_api':
                # Test Fingerspot API connection
                if not self.sync_service.fingerspot_service:
                    return jsonify({
                        'success': False,
                        'message': 'Fingerspot service not available'
                    })
                
                # Use fingerspot service to test connection
                success, message = self.sync_service.fingerspot_service.test_connection(device_config)
                
                if success:
                    # Get additional device info
                    device_info = self.sync_service.fingerspot_service.get_device_info(device_config)
                    
                    return jsonify({
                        'success': True,
                        'message': message,
                        'connection_type': 'fingerspot_api',
                        'device_info': device_info
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': message,
                        'connection_type': 'fingerspot_api'
                    })
            
            elif connection_type == 'online_attendance':
                # Test Online Attendance API connection
                if not self.sync_service.online_attendance_service:
                    return jsonify({
                        'success': False,
                        'message': 'Online Attendance service not available'
                    })
                
                # Use online attendance service to test connection
                success, message = self.sync_service.online_attendance_service.test_connection(device_config)
                
                return jsonify({
                    'success': success,
                    'message': message,
                    'connection_type': 'online_attendance',
                    'device_info': {
                        'api_url': device_config.get('api_config', {}).get('base_url', ''),
                        'endpoint': device_config.get('api_config', {}).get('endpoint', ''),
                        'test_result': 'Success' if success else 'Failed'
                    }
                })
            
            else:
                # Test ZK connection (existing logic)
                try:
                    from zk import ZK
                except ImportError:
                    return jsonify({
                        'success': False,
                        'message': 'zk module not available. Device connection not possible.'
                    })
                
                # Test ZK connection
                zk = ZK(device_config['ip'], port=device_config['port'], 
                       timeout=10, password=device_config['password'])
                
                try:
                    conn = zk.connect()
                    if conn:
                        # Get device info
                        device_info = {
                            'firmware': conn.get_firmware_version(),
                            'users_count': len(conn.get_users() or []),
                            'attendance_count': len(conn.get_attendance() or [])
                        }
                        conn.disconnect()
                        
                        return jsonify({
                            'success': True,
                            'message': 'Connection successful',
                            'connection_type': 'zk',
                            'device_info': device_info
                        })
                    else:
                        return jsonify({
                            'success': False,
                            'message': 'Failed to connect to device',
                            'connection_type': 'zk'
                        })
                        
                except Exception as e:
                    return jsonify({
                        'success': False,
                        'message': f'Connection failed: {str(e)}',
                        'connection_type': 'zk'
                    })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error testing connection: {str(e)}'
            }), 500
    
    def start_streaming(self):
        """Start real-time streaming from all devices"""
        try:
            success, message = self.streaming_service.start_streaming()
            return jsonify({
                'success': success,
                'message': message
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error starting streaming: {str(e)}'
            }), 500
    
    def stop_streaming(self):
        """Stop real-time streaming from all devices"""
        try:
            success, message = self.streaming_service.stop_streaming()
            return jsonify({
                'success': success,
                'message': message
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error stopping streaming: {str(e)}'
            }), 500
    
    def get_streaming_status(self):
        """Get current streaming status"""
        try:
            status = self.streaming_service.get_streaming_status()
            return jsonify({
                'success': True,
                'streaming': status
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error getting streaming status: {str(e)}'
            }), 500
    
    def get_streaming_notifications(self):
        """Get recent streaming notifications from streaming service"""
        try:
            limit = request.args.get('limit', 20, type=int)
            
            # Get notifications directly from streaming service
            notifications = list(self.streaming_service.notifications)
            
            # Sort by timestamp (newest first) and limit
            notifications.sort(key=lambda x: x['datetime'], reverse=True)
            notifications = notifications[:limit]
            
            return jsonify({
                'status': 'success',
                'notifications': notifications,
                'count': len(notifications)
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error getting streaming notifications: {str(e)}',
                'notifications': [],
                'count': 0
            })
    
    def clear_streaming_notifications(self):
        """Clear all streaming notifications from streaming service"""
        try:
            success, message = self.streaming_service.clear_notifications()
            return jsonify({
                'success': success,
                'message': message
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error clearing notifications: {str(e)}'
            }), 500
