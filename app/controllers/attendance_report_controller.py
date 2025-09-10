from flask import Blueprint, render_template, request, jsonify, send_file
from app.models.attendance_report import AttendanceReportModel
from datetime import datetime, date, timedelta
import json

# Create blueprint
attendance_report_bp = Blueprint('attendance_report', __name__, url_prefix='/attendance-report')

@attendance_report_bp.route('/')
def index():
    """Display the attendance report dashboard"""
    try:
        # Initialize model
        model = AttendanceReportModel()
        
        # Get filter options for dropdowns
        filter_options = model.get_filter_options()
        
        # Set default date range (last 30 days)
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        return render_template('attendance_report/index.html', 
                             filter_options=filter_options,
                             default_start_date=start_date.strftime('%Y-%m-%d'),
                             default_end_date=end_date.strftime('%Y-%m-%d'))
    
    except Exception as e:
        print(f"Error in attendance report index: {e}")
        return render_template('attendance_report/index.html', 
                             filter_options={},
                             default_start_date='',
                             default_end_date='',
                             error="Error loading page")

@attendance_report_bp.route('/api/data')
def api_data():
    """API endpoint to get attendance data with filtering and pagination"""
    try:
        # Initialize model
        model = AttendanceReportModel()
        
        # Get request parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        sort_by = request.args.get('sort_by', 'tgl')
        sort_order = request.args.get('sort_order', 'DESC')
        
        # Build filters from request parameters
        filters = {}
        
        if request.args.get('start_date'):
            filters['start_date'] = request.args.get('start_date')
        
        if request.args.get('end_date'):
            filters['end_date'] = request.args.get('end_date')
        
        if request.args.get('pin'):
            filters['pin'] = request.args.get('pin').strip()
        
        if request.args.get('name'):
            filters['name'] = request.args.get('name').strip()
        
        if request.args.get('jabatan'):
            filters['jabatan'] = request.args.get('jabatan')
        
        if request.args.get('lokasi'):
            filters['lokasi'] = request.args.get('lokasi')
        
        if request.args.get('deptname'):
            filters['deptname'] = request.args.get('deptname')
        
        if request.args.get('shift'):
            filters['shift'] = request.args.get('shift')
        
        if request.args.get('keterangan'):
            filters['keterangan'] = request.args.get('keterangan')
        
        # Limit per_page to prevent excessive loads
        per_page = min(per_page, 500)
        
        # Get data
        data, total_count, total_pages = model.get_attendance_data(
            filters=filters, 
            page=page, 
            per_page=per_page,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # Get summary statistics
        summary = model.get_summary_stats(filters=filters)
        
        return jsonify({
            'success': True,
            'data': data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_prev': page > 1,
                'has_next': page < total_pages
            },
            'summary': summary,
            'filters_applied': filters
        })
    
    except Exception as e:
        print(f"Error in attendance report API: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': [],
            'pagination': {
                'page': 1,
                'per_page': 50,
                'total_count': 0,
                'total_pages': 0,
                'has_prev': False,
                'has_next': False
            },
            'summary': {},
            'filters_applied': {}
        })

@attendance_report_bp.route('/api/export')
def api_export():
    """API endpoint to export attendance data to Excel"""
    try:
        # Initialize model
        model = AttendanceReportModel()
        
        # Build filters from request parameters
        filters = {}
        
        if request.args.get('start_date'):
            filters['start_date'] = request.args.get('start_date')
        
        if request.args.get('end_date'):
            filters['end_date'] = request.args.get('end_date')
        
        if request.args.get('pin'):
            filters['pin'] = request.args.get('pin').strip()
        
        if request.args.get('name'):
            filters['name'] = request.args.get('name').strip()
        
        if request.args.get('jabatan'):
            filters['jabatan'] = request.args.get('jabatan')
        
        if request.args.get('lokasi'):
            filters['lokasi'] = request.args.get('lokasi')
        
        if request.args.get('deptname'):
            filters['deptname'] = request.args.get('deptname')
        
        if request.args.get('shift'):
            filters['shift'] = request.args.get('shift')
        
        if request.args.get('keterangan'):
            filters['keterangan'] = request.args.get('keterangan')
        
        # Export to Excel
        excel_file = model.export_to_excel(filters=filters)
        
        if excel_file is None:
            return jsonify({
                'success': False,
                'error': 'Failed to generate Excel file'
            }), 500
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'attendance_report_{timestamp}.xlsx'
        
        return send_file(
            excel_file,
            download_name=filename,
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    except Exception as e:
        print(f"Error in attendance report export: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@attendance_report_bp.route('/api/filter-options')
def api_filter_options():
    """API endpoint to get filter options"""
    try:
        model = AttendanceReportModel()
        filter_options = model.get_filter_options()
        
        return jsonify({
            'success': True,
            'filter_options': filter_options
        })
    
    except Exception as e:
        print(f"Error getting filter options: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'filter_options': {}
        })

@attendance_report_bp.route('/api/summary')
def api_summary():
    """API endpoint to get summary statistics"""
    try:
        model = AttendanceReportModel()
        
        # Build filters from request parameters
        filters = {}
        
        if request.args.get('start_date'):
            filters['start_date'] = request.args.get('start_date')
        
        if request.args.get('end_date'):
            filters['end_date'] = request.args.get('end_date')
        
        if request.args.get('pin'):
            filters['pin'] = request.args.get('pin').strip()
        
        if request.args.get('name'):
            filters['name'] = request.args.get('name').strip()
        
        if request.args.get('jabatan'):
            filters['jabatan'] = request.args.get('jabatan')
        
        if request.args.get('lokasi'):
            filters['lokasi'] = request.args.get('lokasi')
        
        if request.args.get('deptname'):
            filters['deptname'] = request.args.get('deptname')
        
        if request.args.get('shift'):
            filters['shift'] = request.args.get('shift')
        
        if request.args.get('keterangan'):
            filters['keterangan'] = request.args.get('keterangan')
        
        summary = model.get_summary_stats(filters=filters)
        
        return jsonify({
            'success': True,
            'summary': summary
        })
    
    except Exception as e:
        print(f"Error getting summary: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'summary': {}
        })
