"""
VPS Push Controller
Controller untuk menangani API requests terkait VPS push operations
"""

import json
from flask import Blueprint, request, jsonify, session, render_template
from datetime import datetime, timedelta
from app.services.vps_push_service import vps_push_service
from config.logging_config import get_background_logger

# Setup logging
logger = get_background_logger('VPSPushController', 'logs/vps_push_controller.log')

class VPSPushController:
    """Controller untuk VPS push operations"""
    
    def __init__(self):
        self.vps_push_service = vps_push_service
    
    def dashboard(self):
        """VPS Push Dashboard"""
        try:
            return render_template('vps_push_dashboard.html')
        except Exception as e:
            logger.error(f"Error loading VPS push dashboard: {e}")
            return jsonify({
                'success': False,
                'message': f'Dashboard error: {str(e)}'
            }), 500
    
    def push_attrecord_by_date(self):
        """Push AttRecord data by date range"""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({
                    'success': False,
                    'message': 'No data provided'
                }), 400
            
            # Get parameters
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            pins = data.get('pins', [])
            
            # Validate required parameters
            if not start_date:
                return jsonify({
                    'success': False,
                    'message': 'start_date is required'
                }), 400
            
            if not end_date:
                end_date = start_date
            
            # Validate date format
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
                datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }), 400
            
            # Validate pins if provided
            if pins and not isinstance(pins, list):
                return jsonify({
                    'success': False,
                    'message': 'pins must be an array'
                }), 400
            
            # Convert pins to strings
            pins = [str(pin) for pin in pins] if pins else None
            
            logger.info(f"Pushing AttRecord data - Start: {start_date}, End: {end_date}, PINs: {pins}")
            
            # Push data to VPS
            success, message = self.vps_push_service.push_attrecord_by_date_range(
                start_date, end_date, pins
            )
            
            if success:
                logger.info(f"AttRecord push successful: {message}")
                return jsonify({
                    'success': True,
                    'message': message,
                    'start_date': start_date,
                    'end_date': end_date,
                    'pins': pins,
                    'timestamp': datetime.now().isoformat()
                })
            else:
                logger.error(f"AttRecord push failed: {message}")
                return jsonify({
                    'success': False,
                    'message': message,
                    'start_date': start_date,
                    'end_date': end_date,
                    'pins': pins
                }), 500
        
        except Exception as e:
            logger.error(f"Error in push_attrecord_by_date: {e}")
            return jsonify({
                'success': False,
                'message': f'Internal error: {str(e)}'
            }), 500
    
    def push_attrecord_today(self):
        """Push today's AttRecord data"""
        try:
            data = request.get_json() or {}
            pins = data.get('pins', [])
            
            # Validate pins if provided
            if pins and not isinstance(pins, list):
                return jsonify({
                    'success': False,
                    'message': 'pins must be an array'
                }), 400
            
            # Convert pins to strings
            pins = [str(pin) for pin in pins] if pins else None
            
            logger.info(f"Pushing today's AttRecord data - PINs: {pins}")
            
            # Push today's data
            success, message = self.vps_push_service.push_attrecord_today(pins)
            
            today = datetime.now().strftime('%Y-%m-%d')
            
            if success:
                logger.info(f"Today's AttRecord push successful: {message}")
                return jsonify({
                    'success': True,
                    'message': message,
                    'date': today,
                    'pins': pins,
                    'timestamp': datetime.now().isoformat()
                })
            else:
                logger.error(f"Today's AttRecord push failed: {message}")
                return jsonify({
                    'success': False,
                    'message': message,
                    'date': today,
                    'pins': pins
                }), 500
        
        except Exception as e:
            logger.error(f"Error in push_attrecord_today: {e}")
            return jsonify({
                'success': False,
                'message': f'Internal error: {str(e)}'
            }), 500
    
    def push_attrecord_for_pins(self):
        """Push AttRecord data for specific PINs"""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({
                    'success': False,
                    'message': 'No data provided'
                }), 400
            
            # Get parameters
            pins = data.get('pins', [])
            days_back = data.get('days_back', 7)
            
            # Validate required parameters
            if not pins:
                return jsonify({
                    'success': False,
                    'message': 'pins array is required'
                }), 400
            
            if not isinstance(pins, list):
                return jsonify({
                    'success': False,
                    'message': 'pins must be an array'
                }), 400
            
            # Validate days_back
            try:
                days_back = int(days_back)
                if days_back < 1 or days_back > 365:
                    days_back = 7
            except (ValueError, TypeError):
                days_back = 7
            
            # Convert pins to strings
            pins = [str(pin) for pin in pins]
            
            logger.info(f"Pushing AttRecord data for PINs: {pins}, Days back: {days_back}")
            
            # Push data for specific PINs
            success, message = self.vps_push_service.push_attrecord_for_pins(pins, days_back)
            
            if success:
                logger.info(f"AttRecord push for PINs successful: {message}")
                return jsonify({
                    'success': True,
                    'message': message,
                    'pins': pins,
                    'days_back': days_back,
                    'timestamp': datetime.now().isoformat()
                })
            else:
                logger.error(f"AttRecord push for PINs failed: {message}")
                return jsonify({
                    'success': False,
                    'message': message,
                    'pins': pins,
                    'days_back': days_back
                }), 500
        
        except Exception as e:
            logger.error(f"Error in push_attrecord_for_pins: {e}")
            return jsonify({
                'success': False,
                'message': f'Internal error: {str(e)}'
            }), 500
    
    def test_vps_connection(self):
        """Test VPS connection"""
        try:
            logger.info("Testing VPS connection")
            
            success, message = self.vps_push_service.test_vps_connection()
            
            if success:
                logger.info(f"VPS connection test successful: {message}")
                return jsonify({
                    'success': True,
                    'message': message,
                    'timestamp': datetime.now().isoformat()
                })
            else:
                logger.warning(f"VPS connection test failed: {message}")
                return jsonify({
                    'success': False,
                    'message': message,
                    'timestamp': datetime.now().isoformat()
                }), 503
        
        except Exception as e:
            logger.error(f"Error in test_vps_connection: {e}")
            return jsonify({
                'success': False,
                'message': f'Internal error: {str(e)}'
            }), 500
    
    def get_vps_statistics(self):
        """Get VPS push statistics"""
        try:
            stats = self.vps_push_service.get_push_statistics()
            
            return jsonify({
                'success': True,
                'statistics': stats,
                'timestamp': datetime.now().isoformat()
            })
        
        except Exception as e:
            logger.error(f"Error in get_vps_statistics: {e}")
            return jsonify({
                'success': False,
                'message': f'Internal error: {str(e)}'
            }), 500
    
    def get_attrecord_preview(self):
        """Get preview of AttRecord data (without pushing)"""
        try:
            data = request.get_json() or {}
            
            # Get parameters
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            pins = data.get('pins', [])
            limit = data.get('limit', 100)
            
            # Set default dates if not provided
            if not start_date:
                start_date = datetime.now().strftime('%Y-%m-%d')
            if not end_date:
                end_date = start_date
            
            # Validate date format
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
                datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }), 400
            
            # Validate limit
            try:
                limit = int(limit)
                if limit < 1 or limit > 1000:
                    limit = 100
            except (ValueError, TypeError):
                limit = 100
            
            # Convert pins to strings
            pins = [str(pin) for pin in pins] if pins else None
            
            logger.info(f"Getting AttRecord preview - Start: {start_date}, End: {end_date}, PINs: {pins}, Limit: {limit}")
            
            # Get data from database
            data = self.vps_push_service.get_attrecord_data(start_date, end_date, pins, limit)
            
            return jsonify({
                'success': True,
                'data': data,
                'record_count': len(data),
                'start_date': start_date,
                'end_date': end_date,
                'pins': pins,
                'limit': limit,
                'timestamp': datetime.now().isoformat()
            })
        
        except Exception as e:
            logger.error(f"Error in get_attrecord_preview: {e}")
            return jsonify({
                'success': False,
                'message': f'Internal error: {str(e)}'
            }), 500

# Global controller instance
vps_push_controller = VPSPushController()