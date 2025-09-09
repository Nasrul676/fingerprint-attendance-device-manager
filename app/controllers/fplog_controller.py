"""
Controller for handling FPLog data operations
"""
from flask import jsonify, request, render_template, send_file
from datetime import datetime, timedelta
from io import BytesIO
from app.services.fplog_service import FPLogService

class FPLogController:
    """Controller for FPLog data operations"""
    
    def __init__(self):
        self.fplog_service = FPLogService()
    
    def fplog_dashboard(self):
        """Display FPLog dashboard page"""
        try:
            # Get statistics
            stats = self.fplog_service.get_fplog_statistics()
            
            # Get filter options
            machines = self.fplog_service.get_machine_list()
            statuses = self.fplog_service.get_status_list()
            
            return render_template('fplog_dashboard.html', 
                                 stats=stats,
                                 machines=machines,
                                 statuses=statuses)
        except Exception as e:
            return render_template('fplog_dashboard.html', 
                                 error=f"Error loading dashboard: {str(e)}")
    
    def search_fplog(self):
        """Search FPLog data with filters"""
        try:
            data = request.get_json() or {}
            
            filters = {
                'pin': data.get('pin', '').strip(),
                'machine': data.get('machine', '').strip(),
                'start_date': data.get('start_date', '').strip(),
                'end_date': data.get('end_date', '').strip(),
                'status': data.get('status', '').strip(),
                'limit': data.get('limit', 1000)
            }
            
            # Remove empty filters
            filters = {k: v for k, v in filters.items() if v != ''}
            
            success, message, fplog_data = self.fplog_service.search_fplog_data(filters)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': message,
                    'data': fplog_data,
                    'total': len(fplog_data)
                })
            else:
                return jsonify({
                    'success': False,
                    'message': message
                }), 400
                
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error searching data: {str(e)}'
            }), 500
    
    def export_fplog_excel(self):
        """Export FPLog data to Excel"""
        try:
            data = request.get_json() or {}
            
            filters = {
                'pin': data.get('pin', '').strip(),
                'machine': data.get('machine', '').strip(),
                'start_date': data.get('start_date', '').strip(),
                'end_date': data.get('end_date', '').strip(),
                'status': data.get('status', '').strip(),
                'limit': data.get('limit', 10000)  # Higher limit for export
            }
            
            # Remove empty filters
            filters = {k: v for k, v in filters.items() if v != ''}
            
            # Get data
            success, message, fplog_data = self.fplog_service.search_fplog_data(filters)
            
            if not success:
                return jsonify({
                    'success': False,
                    'message': message
                }), 400
            
            if not fplog_data:
                return jsonify({
                    'success': False,
                    'message': 'Tidak ada data untuk diekspor'
                }), 400
            
            # Export to Excel
            excel_data, filename = self.fplog_service.export_to_excel(fplog_data, filters)
            
            if excel_data is None:
                return jsonify({
                    'success': False,
                    'message': filename  # filename contains error message in this case
                }), 500
            
            # Send file
            return send_file(
                BytesIO(excel_data),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=filename
            )
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error exporting data: {str(e)}'
            }), 500
    
    def get_fplog_stats(self):
        """Get FPLog statistics"""
        try:
            stats = self.fplog_service.get_fplog_statistics()
            return jsonify({
                'success': True,
                'stats': stats
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error getting statistics: {str(e)}'
            }), 500
    
    def get_filter_options(self):
        """Get filter options for dropdowns"""
        try:
            machines = self.fplog_service.get_machine_list()
            statuses = self.fplog_service.get_status_list()
            
            return jsonify({
                'success': True,
                'machines': machines,
                'statuses': statuses
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error getting filter options: {str(e)}'
            }), 500
