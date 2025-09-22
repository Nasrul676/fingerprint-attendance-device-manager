# Job Queue Worker Control System

## Overview

The job queue system now includes comprehensive worker control functionality that allows administrators to manage the job processing worker through the web interface.

## Features Implemented

### 1. Worker Control UI (Job Queue Monitor)

**Location**: `/job/queue` page

**New Controls Added**:
- **Worker Control Dropdown**: Added to the top toolbar with the following options:
  - Start Worker
  - Stop Worker  
  - Restart Worker
  - Check Status
  - Create Test Job

**Worker Status Indicator**: 
- Green alert: "Job Worker is running" 
- Yellow alert: "Job Worker is stopped"
- Real-time status updates after control actions

### 2. Backend API Endpoints

**New Routes Added** (`app/routes.py`):
```
POST /worker/start    - Start the job worker
POST /worker/stop     - Stop the job worker  
POST /worker/restart  - Restart the job worker
GET  /worker/status   - Get detailed worker status
POST /test-job        - Create a test job
```

### 3. Controller Methods

**New Methods Added** (`app/controllers/job_controller.py`):

- `start_job_worker()` - Starts the worker if not running
- `stop_job_worker()` - Stops the worker if running  
- `restart_job_worker()` - Stops and restarts the worker
- `get_worker_status()` - Returns detailed worker status including:
  - Running state
  - Thread alive status
  - Registered job handlers
  - Job statistics
- `create_test_job()` - Creates a test procedure processing job

### 4. Frontend JavaScript Functions

**New Functions Added** (`app/static/js/job-queue-monitor.js`):

- `startWorker()` - Calls start worker API
- `stopWorker()` - Calls stop worker API with confirmation
- `restartWorker()` - Calls restart worker API with confirmation
- `checkWorkerStatus()` - Shows detailed status modal
- `createTestJob()` - Creates test job with confirmation
- `updateWorkerStatus()` - Updates UI worker status indicator
- `showWorkerStatusModal()` - Displays comprehensive status information

## Usage Instructions

### Starting the Worker
1. Navigate to `/job/queue`
2. Click the "Worker Controls" dropdown
3. Select "Start Worker"
4. Status indicator will update to green when successful

### Stopping the Worker
1. Click "Worker Controls" dropdown
2. Select "Stop Worker"
3. Confirm the action in the dialog
4. Status indicator will update to yellow when stopped

### Restarting the Worker
1. Click "Worker Controls" dropdown
2. Select "Restart Worker"  
3. Confirm the action in the dialog
4. Worker will be stopped and restarted automatically

### Checking Worker Status
1. Click "Worker Controls" dropdown
2. Select "Check Status"
3. A detailed modal will show:
   - Worker running state
   - Thread status
   - Registered job handlers
   - Current job statistics

### Creating Test Jobs
1. Click "Worker Controls" dropdown
2. Select "Create Test Job"
3. Confirm to create a test procedure processing job
4. Job will appear in the queue for processing

## Technical Details

### Error Handling
- All API calls include comprehensive error handling
- User-friendly error messages via toastr notifications
- Failed operations show specific error details

### User Feedback
- Loading states during worker operations
- Success/error notifications for all actions
- Real-time status updates in the UI
- Confirmation dialogs for destructive actions

### Security Considerations
- All worker control actions require user authentication
- Confirmation dialogs prevent accidental worker shutdown
- Audit logging for all worker control actions

## Integration with Existing System

The worker control system integrates seamlessly with:
- Existing job service worker (`JobService`)
- Manual procedure processing system
- Job queue monitoring and statistics
- User session management
- Logging and error reporting

## Testing

To test the worker control functionality:

1. **Start Application**: `python app.py`
2. **Access Queue Page**: Navigate to `http://localhost:5000/job/queue`
3. **Test Worker Controls**: Use dropdown to start/stop/restart worker
4. **Verify Status**: Check status modal for worker information
5. **Create Test Job**: Use test job creation to verify processing
6. **Monitor Queue**: Watch jobs process in real-time

## Files Modified

- `app/templates/job_queue_monitor.html` - Added worker control UI
- `app/routes.py` - Added worker control routes
- `app/controllers/job_controller.py` - Added worker control methods
- `app/static/js/job-queue-monitor.js` - Added worker control JavaScript

This implementation provides complete administrative control over the job processing worker through an intuitive web interface.