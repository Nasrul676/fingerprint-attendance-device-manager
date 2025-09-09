"""
Controller for Attendance Queue Management
Handle web requests for attendance queue operations
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from app.services.sync_service import SyncService
from app.models.attendance import AttendanceModel

# Create blueprint for attendance queue routes
attendance_queue_bp = Blueprint('attendance_queue', __name__)

@attendance_queue_bp.route('/attendance-queue')
def attendance_queue_dashboard():
    """Display attendance queue dashboard"""
    try:
        attendance_model = AttendanceModel()
        
        # Get queue records with pagination
        page = request.args.get('page', 1, type=int)
        status_filter = request.args.get('status', None)
        per_page = 20
        
        # Get queue records
        all_records = attendance_model.get_attendance_queue(status=status_filter, limit=per_page * page)
        
        # Calculate pagination
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        records = all_records[start_index:end_index]
        
        # Get status counts
        all_queue_records = attendance_model.get_attendance_queue()
        status_counts = {}
        for record in all_queue_records:
            status = record['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return render_template('attendance_queue/dashboard.html', 
                             records=records,
                             status_counts=status_counts,
                             current_page=page,
                             status_filter=status_filter,
                             total_records=len(all_records))
                             
    except Exception as e:
        flash(f"Error loading attendance queue: {str(e)}", 'error')
        return render_template('attendance_queue/dashboard.html', 
                             records=[], status_counts={}, current_page=1)

@attendance_queue_bp.route('/attendance-queue/process', methods=['POST'])
def process_queue():
    """Process attendance queue records"""
    try:
        sync_service = SyncService()
        batch_size = request.form.get('batch_size', 50, type=int)
        
        success, message = sync_service.process_attendance_queue(batch_size)
        
        if success:
            flash(f"Queue processing completed: {message}", 'success')
        else:
            flash(f"Queue processing failed: {message}", 'error')
            
    except Exception as e:
        flash(f"Error processing queue: {str(e)}", 'error')
    
    return redirect(url_for('attendance_queue.attendance_queue_dashboard'))

@attendance_queue_bp.route('/attendance-queue/update-status', methods=['POST'])
def update_queue_status():
    """Update status of queue record"""
    try:
        queue_id = request.form.get('queue_id', type=int)
        new_status = request.form.get('new_status')
        
        if not queue_id or not new_status:
            return jsonify({'success': False, 'message': 'Missing required parameters'})
        
        attendance_model = AttendanceModel()
        success, message = attendance_model.update_queue_status(queue_id, new_status)
        
        return jsonify({'success': success, 'message': message})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@attendance_queue_bp.route('/attendance-queue/delete', methods=['POST'])
def delete_from_queue():
    """Delete record from attendance queue"""
    try:
        queue_id = request.form.get('queue_id', type=int)
        
        if not queue_id:
            return jsonify({'success': False, 'message': 'Missing queue ID'})
        
        attendance_model = AttendanceModel()
        success, message = attendance_model.delete_from_queue(queue_id)
        
        return jsonify({'success': success, 'message': message})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@attendance_queue_bp.route('/attendance-queue/api/stats')
def get_queue_stats():
    """Get attendance queue statistics via API"""
    try:
        attendance_model = AttendanceModel()
        all_records = attendance_model.get_attendance_queue()
        
        stats = {
            'total': len(all_records),
            'by_status': {},
            'recent_records': []
        }
        
        # Count by status
        for record in all_records:
            status = record['status']
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
        
        # Get recent records (last 10)
        recent = sorted(all_records, key=lambda x: x['created_at'], reverse=True)[:10]
        stats['recent_records'] = [
            {
                'id': r['id'],
                'pin': r['pin'],
                'date': r['date'].strftime('%Y-%m-%d %H:%M:%S') if r['date'] else '',
                'status': r['status'],
                'machine': r['machine']
            }
            for r in recent
        ]
        
        return jsonify({'success': True, 'data': stats})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Helper function to register blueprint
def register_attendance_queue_routes(app):
    """Register attendance queue routes with Flask app"""
    app.register_blueprint(attendance_queue_bp)
