/**
 * Job Queue Monitor JavaScript
 * Real-time monitoring of job queue with filtering and management
 */

class JobQueueMonitor {
    constructor() {
        this.currentFilters = {
            status: 'all',
            priority: '',
            jobType: '',
            dateRange: '',
            limit: 50
        };
        this.selectedJobs = new Set();
        this.isAutoRefreshEnabled = true;
        this.refreshInterval = null;
        this.currentJobId = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadQueueData();
        this.startAutoRefresh();
        this.updateRealTimeStatus('connecting');
    }

    bindEvents() {
        // Refresh controls
        document.getElementById('refreshQueue').addEventListener('click', () => {
            this.loadQueueData();
        });

        document.getElementById('toggleAutoRefresh').addEventListener('click', () => {
            this.toggleAutoRefresh();
        });

        // Status filter buttons
        document.querySelectorAll('[data-status]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.setStatusFilter(e.target.dataset.status);
            });
        });

        // Filter controls
        document.getElementById('priorityFilter').addEventListener('change', (e) => {
            this.currentFilters.priority = e.target.value;
            this.loadQueueData();
        });

        document.getElementById('jobTypeFilter').addEventListener('change', (e) => {
            this.currentFilters.jobType = e.target.value;
            this.loadQueueData();
        });

        document.getElementById('dateFilter').addEventListener('change', (e) => {
            this.currentFilters.dateRange = e.target.value;
            this.loadQueueData();
        });

        document.getElementById('limitFilter').addEventListener('change', (e) => {
            this.currentFilters.limit = parseInt(e.target.value);
            this.loadQueueData();
        });

        // Bulk actions
        document.getElementById('selectAll').addEventListener('click', () => {
            this.toggleSelectAll();
        });

        document.getElementById('selectAllCheckbox').addEventListener('change', (e) => {
            this.toggleSelectAll(e.target.checked);
        });

        document.getElementById('bulkCancel').addEventListener('click', () => {
            this.bulkCancelJobs();
        });

        // Job details modal
        document.getElementById('cancelJobBtn').addEventListener('click', () => {
            this.cancelCurrentJob();
        });
    }

    setStatusFilter(status) {
        // Update button states
        document.querySelectorAll('[data-status]').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-status="${status}"]`).classList.add('active');

        this.currentFilters.status = status;
        this.loadQueueData();
    }

    async loadQueueData() {
        try {
            this.updateRealTimeStatus('connecting');
            
            // Build query parameters
            const params = new URLSearchParams();
            if (this.currentFilters.status !== 'all') {
                params.append('status', this.currentFilters.status);
            }
            if (this.currentFilters.priority) {
                params.append('priority', this.currentFilters.priority);
            }
            if (this.currentFilters.jobType) {
                params.append('job_type', this.currentFilters.jobType);
            }
            if (this.currentFilters.dateRange) {
                params.append('date_range', this.currentFilters.dateRange);
            }
            params.append('limit', this.currentFilters.limit);

            // Load queue data and statistics
            const [queueResponse, statsResponse] = await Promise.all([
                fetch(`/job/queue/api?${params.toString()}`),
                fetch('/job/statistics/api')
            ]);

            const queueData = await queueResponse.json();
            const statsData = await statsResponse.json();

            if (queueData.success) {
                this.renderQueueTable(queueData.jobs || []);
                this.updateJobCount(queueData.total || 0);
            } else {
                this.showError('Failed to load queue data');
            }

            if (statsData.success) {
                this.updateQueueStatistics(statsData.statistics);
            }

            this.updateRealTimeStatus('connected');
            
        } catch (error) {
            console.error('Error loading queue data:', error);
            this.showError('Error loading queue data');
            this.updateRealTimeStatus('disconnected');
        }
    }

    async loadQueueStatistics() {
        try {
            const response = await fetch('/job/statistics/api');
            const data = await response.json();

            if (data.success) {
                this.updateQueueStatistics(data.statistics);
            }
        } catch (error) {
            console.error('Error loading queue statistics:', error);
        }
    }

    updateQueueStatistics(stats) {
        const statusCounts = stats.status_counts || {};
        
        document.getElementById('totalJobs').textContent = 
            Object.values(statusCounts).reduce((a, b) => a + b, 0);
        document.getElementById('pendingJobs').textContent = statusCounts.pending || 0;
        document.getElementById('runningJobs').textContent = statusCounts.running || 0;
        document.getElementById('completedJobs').textContent = statusCounts.completed || 0;
        document.getElementById('failedJobs').textContent = statusCounts.failed || 0;
        
        // Calculate average processing time (placeholder)
        document.getElementById('avgProcessTime').textContent = '2.3m';
    }

    renderQueueTable(jobs) {
        const tbody = document.getElementById('queueTableBody');
        
        if (jobs.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="empty-state">
                        <i class="fas fa-inbox"></i>
                        <h5>No jobs found</h5>
                        <p>No jobs match your current filters.</p>
                    </td>
                </tr>
            `;
            return;
        }

        let html = '';
        jobs.forEach(job => {
            html += this.generateJobRow(job);
        });

        tbody.innerHTML = html;
        this.clearSelection();
    }

    generateJobRow(job) {
        const priorityClass = `priority-${job.priority}`;
        const statusClass = `status-${job.status}`;
        const runningPulse = job.status === 'running' ? 'running-pulse' : '';
        
        const createdAt = this.formatDateTime(job.created_at);
        const duration = this.calculateDuration(job.created_at, job.completed_at);
        const progress = this.getJobProgress(job);
        
        return `
            <tr class="job-row ${runningPulse}" onclick="jobQueueMonitor.showJobDetails('${job.job_id}')">
                <td onclick="event.stopPropagation()">
                    <input type="checkbox" class="form-check-input job-checkbox" 
                           value="${job.job_id}" onchange="jobQueueMonitor.toggleJobSelection(this)">
                </td>
                <td>
                    <div class="priority-indicator ${priorityClass}" title="Priority ${job.priority}"></div>
                </td>
                <td>
                    <div>
                        <strong>${job.job_type}</strong>
                        <br>
                        <small class="text-muted">ID: ${job.job_id.substring(0, 8)}...</small>
                        <br>
                        <small class="text-muted">
                            <i class="fas fa-calendar me-1"></i>${job.job_data.target_date || 'N/A'}
                        </small>
                    </div>
                </td>
                <td>
                    <span class="job-status-badge ${statusClass}">
                        ${job.status === 'running' ? '<i class="fas fa-spinner fa-spin me-1"></i>' : ''}
                        ${job.status}
                    </span>
                </td>
                <td>
                    ${this.getPriorityBadge(job.priority)}
                </td>
                <td>
                    <div class="progress mb-1" style="height: 8px;">
                        <div class="progress-bar ${this.getProgressBarClass(job.status)}" 
                             style="width: ${progress}%" 
                             title="${progress}% complete"></div>
                    </div>
                    <small class="text-muted">${job.attempts}/${job.max_attempts} attempts</small>
                </td>
                <td>
                    <small>
                        <strong>Created:</strong><br>${createdAt}<br>
                        <strong>Duration:</strong><br>${duration}
                    </small>
                </td>
                <td onclick="event.stopPropagation()">
                    <div class="action-buttons">
                        <button class="btn btn-outline-primary btn-action" 
                                onclick="jobQueueMonitor.showJobDetails('${job.job_id}')"
                                title="View Details">
                            <i class="fas fa-eye"></i>
                        </button>
                        ${job.status === 'pending' ? `
                            <button class="btn btn-outline-danger btn-action" 
                                    onclick="jobQueueMonitor.cancelJob('${job.job_id}')"
                                    title="Cancel Job">
                                <i class="fas fa-ban"></i>
                            </button>
                        ` : ''}
                        ${job.status === 'failed' && job.attempts < job.max_attempts ? `
                            <button class="btn btn-outline-warning btn-action" 
                                    onclick="jobQueueMonitor.retryJob('${job.job_id}')"
                                    title="Retry Job">
                                <i class="fas fa-redo"></i>
                            </button>
                        ` : ''}
                    </div>
                </td>
            </tr>
        `;
    }

    getPriorityBadge(priority) {
        if (priority <= 2) return '<span class="badge bg-danger">Critical</span>';
        if (priority <= 4) return '<span class="badge bg-warning">High</span>';
        if (priority <= 6) return '<span class="badge bg-primary">Normal</span>';
        if (priority <= 8) return '<span class="badge bg-info">Low</span>';
        return '<span class="badge bg-secondary">Very Low</span>';
    }

    getJobProgress(job) {
        switch (job.status) {
            case 'pending': return 0;
            case 'running': return 50;
            case 'completed': return 100;
            case 'failed': return job.attempts > 0 ? (job.attempts / job.max_attempts) * 100 : 0;
            case 'cancelled': return 0;
            default: return 0;
        }
    }

    getProgressBarClass(status) {
        switch (status) {
            case 'running': return 'bg-info progress-bar-animated progress-bar-striped';
            case 'completed': return 'bg-success';
            case 'failed': return 'bg-danger';
            case 'cancelled': return 'bg-secondary';
            default: return 'bg-warning';
        }
    }

    async showJobDetails(jobId) {
        try {
            const response = await fetch(`/job/${jobId}/status`);
            const data = await response.json();

            if (data.success) {
                this.currentJobId = jobId;
                const job = data.job;
                
                document.getElementById('jobDetailsContent').innerHTML = 
                    this.generateJobDetailsHTML(job);
                
                // Show cancel button for pending jobs
                const cancelBtn = document.getElementById('cancelJobBtn');
                cancelBtn.style.display = job.status === 'pending' ? 'block' : 'none';

                new bootstrap.Modal(document.getElementById('jobDetailsModal')).show();
            } else {
                toastr.error(data.message || 'Failed to load job details');
            }
        } catch (error) {
            console.error('Error loading job details:', error);
            toastr.error('Error loading job details');
        }
    }

    generateJobDetailsHTML(job) {
        const createdAt = this.formatDateTime(job.created_at);
        const startedAt = job.started_at ? this.formatDateTime(job.started_at) : 'Not started';
        const completedAt = job.completed_at ? this.formatDateTime(job.completed_at) : 'Not completed';
        const duration = this.calculateDuration(job.created_at, job.completed_at);
        
        return `
            <div class="row">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h6 class="mb-0"><i class="fas fa-info-circle me-2"></i>Job Information</h6>
                        </div>
                        <div class="card-body">
                            <table class="table table-sm">
                                <tr><td><strong>Job ID:</strong></td><td><code>${job.job_id}</code></td></tr>
                                <tr><td><strong>Type:</strong></td><td><span class="badge bg-primary">${job.job_type}</span></td></tr>
                                <tr><td><strong>Status:</strong></td><td><span class="job-status-badge status-${job.status}">${job.status}</span></td></tr>
                                <tr><td><strong>Priority:</strong></td><td>${this.getPriorityBadge(job.priority)} (${job.priority})</td></tr>
                                <tr><td><strong>Attempts:</strong></td><td>${job.attempts}/${job.max_attempts}</td></tr>
                                <tr><td><strong>User:</strong></td><td>${job.user_id}</td></tr>
                            </table>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h6 class="mb-0"><i class="fas fa-clock me-2"></i>Timing Information</h6>
                        </div>
                        <div class="card-body">
                            <table class="table table-sm">
                                <tr><td><strong>Created:</strong></td><td>${createdAt}</td></tr>
                                <tr><td><strong>Started:</strong></td><td>${startedAt}</td></tr>
                                <tr><td><strong>Completed:</strong></td><td>${completedAt}</td></tr>
                                <tr><td><strong>Duration:</strong></td><td><span class="badge bg-info">${duration}</span></td></tr>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row mt-3">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">
                            <h6 class="mb-0"><i class="fas fa-code me-2"></i>Job Data</h6>
                        </div>
                        <div class="card-body">
                            <pre class="bg-light p-3 rounded"><code>${JSON.stringify(job.job_data, null, 2)}</code></pre>
                        </div>
                    </div>
                </div>
            </div>
            
            ${job.error_message ? `
                <div class="row mt-3">
                    <div class="col-12">
                        <div class="card border-danger">
                            <div class="card-header bg-danger text-white">
                                <h6 class="mb-0"><i class="fas fa-exclamation-triangle me-2"></i>Error Details</h6>
                            </div>
                            <div class="card-body">
                                <div class="alert alert-danger mb-0">${job.error_message}</div>
                            </div>
                        </div>
                    </div>
                </div>
            ` : ''}
            
            ${job.result_data ? `
                <div class="row mt-3">
                    <div class="col-12">
                        <div class="card border-success">
                            <div class="card-header bg-success text-white">
                                <h6 class="mb-0"><i class="fas fa-check-circle me-2"></i>Result Data</h6>
                            </div>
                            <div class="card-body">
                                <pre class="bg-light p-3 rounded"><code>${JSON.stringify(job.result_data, null, 2)}</code></pre>
                            </div>
                        </div>
                    </div>
                </div>
            ` : ''}
        `;
    }

    async cancelJob(jobId) {
        if (!confirm('Are you sure you want to cancel this job?')) {
            return;
        }

        try {
            const response = await fetch(`/job/${jobId}/cancel`, {
                method: 'POST'
            });

            const data = await response.json();

            if (data.success) {
                toastr.success('Job cancelled successfully');
                this.loadQueueData();
            } else {
                toastr.error(data.message || 'Failed to cancel job');
            }
        } catch (error) {
            console.error('Error cancelling job:', error);
            toastr.error('Error cancelling job');
        }
    }

    async cancelCurrentJob() {
        if (this.currentJobId) {
            await this.cancelJob(this.currentJobId);
            bootstrap.Modal.getInstance(document.getElementById('jobDetailsModal')).hide();
        }
    }

    async retryJob(jobId) {
        if (!confirm('Are you sure you want to retry this failed job?')) {
            return;
        }

        try {
            const response = await fetch(`/job/${jobId}/retry`, {
                method: 'POST'
            });

            const data = await response.json();

            if (data.success) {
                toastr.success('Job retry initiated');
                this.loadQueueData();
            } else {
                toastr.error(data.message || 'Failed to retry job');
            }
        } catch (error) {
            console.error('Error retrying job:', error);
            toastr.error('Error retrying job');
        }
    }

    toggleJobSelection(checkbox) {
        if (checkbox.checked) {
            this.selectedJobs.add(checkbox.value);
        } else {
            this.selectedJobs.delete(checkbox.value);
        }
        
        this.updateBulkActions();
        this.updateSelectAllState();
    }

    toggleSelectAll(forceState = null) {
        const checkboxes = document.querySelectorAll('.job-checkbox');
        const selectAllCheckbox = document.getElementById('selectAllCheckbox');
        
        const shouldSelect = forceState !== null ? forceState : this.selectedJobs.size === 0;
        
        this.selectedJobs.clear();
        
        checkboxes.forEach(checkbox => {
            checkbox.checked = shouldSelect;
            if (shouldSelect) {
                this.selectedJobs.add(checkbox.value);
            }
        });
        
        selectAllCheckbox.checked = shouldSelect;
        this.updateBulkActions();
    }

    updateSelectAllState() {
        const checkboxes = document.querySelectorAll('.job-checkbox');
        const selectAllCheckbox = document.getElementById('selectAllCheckbox');
        
        if (checkboxes.length === 0) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
        } else if (this.selectedJobs.size === checkboxes.length) {
            selectAllCheckbox.checked = true;
            selectAllCheckbox.indeterminate = false;
        } else if (this.selectedJobs.size > 0) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = true;
        } else {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
        }
    }

    updateBulkActions() {
        const bulkCancelBtn = document.getElementById('bulkCancel');
        bulkCancelBtn.disabled = this.selectedJobs.size === 0;
        
        if (this.selectedJobs.size > 0) {
            bulkCancelBtn.innerHTML = `<i class="fas fa-ban"></i> Cancel ${this.selectedJobs.size} Selected`;
        } else {
            bulkCancelBtn.innerHTML = '<i class="fas fa-ban"></i> Cancel Selected';
        }
    }

    async bulkCancelJobs() {
        if (this.selectedJobs.size === 0) return;
        
        if (!confirm(`Are you sure you want to cancel ${this.selectedJobs.size} selected jobs?`)) {
            return;
        }

        try {
            const promises = Array.from(this.selectedJobs).map(jobId => 
                fetch(`/job/${jobId}/cancel`, { method: 'POST' })
            );

            const responses = await Promise.all(promises);
            const results = await Promise.all(responses.map(r => r.json()));
            
            const successful = results.filter(r => r.success).length;
            const failed = results.length - successful;
            
            if (successful > 0) {
                toastr.success(`Successfully cancelled ${successful} jobs`);
            }
            if (failed > 0) {
                toastr.error(`Failed to cancel ${failed} jobs`);
            }
            
            this.clearSelection();
            this.loadQueueData();
            
        } catch (error) {
            console.error('Error bulk cancelling jobs:', error);
            toastr.error('Error bulk cancelling jobs');
        }
    }

    clearSelection() {
        this.selectedJobs.clear();
        document.querySelectorAll('.job-checkbox').forEach(cb => cb.checked = false);
        document.getElementById('selectAllCheckbox').checked = false;
        this.updateBulkActions();
    }

    updateJobCount(count) {
        document.getElementById('jobCount').textContent = count;
    }

    updateRealTimeStatus(status) {
        const indicator = document.getElementById('realTimeStatus');
        indicator.className = `real-time-indicator ${status}`;
        
        switch (status) {
            case 'connected':
                indicator.innerHTML = '<i class="fas fa-circle me-1"></i><span>Live Monitoring</span>';
                break;
            case 'connecting':
                indicator.innerHTML = '<i class="fas fa-circle me-1"></i><span>Connecting...</span>';
                break;
            case 'disconnected':
                indicator.innerHTML = '<i class="fas fa-circle me-1"></i><span>Disconnected</span>';
                break;
        }
    }

    toggleAutoRefresh() {
        const btn = document.getElementById('toggleAutoRefresh');
        
        if (this.isAutoRefreshEnabled) {
            this.stopAutoRefresh();
            btn.innerHTML = '<i class="fas fa-play"></i> Auto Refresh';
            btn.classList.remove('btn-light');
            btn.classList.add('btn-warning');
        } else {
            this.startAutoRefresh();
            btn.innerHTML = '<i class="fas fa-pause"></i> Auto Refresh';
            btn.classList.remove('btn-warning');
            btn.classList.add('btn-light');
        }
    }

    startAutoRefresh() {
        this.isAutoRefreshEnabled = true;
        this.refreshInterval = setInterval(() => {
            this.loadQueueData();
        }, 10000); // Refresh every 10 seconds
    }

    stopAutoRefresh() {
        this.isAutoRefreshEnabled = false;
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    showError(message) {
        const tbody = document.getElementById('queueTableBody');
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-5 text-danger">
                    <i class="fas fa-exclamation-triangle fa-3x mb-3"></i>
                    <h5>Error Loading Data</h5>
                    <p>${message}</p>
                    <button class="btn btn-primary" onclick="jobQueueMonitor.loadQueueData()">
                        <i class="fas fa-redo me-1"></i>Retry
                    </button>
                </td>
            </tr>
        `;
    }

    formatDateTime(dateTimeString) {
        if (!dateTimeString) return 'N/A';
        
        const date = new Date(dateTimeString);
        return date.toLocaleString('id-ID', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    calculateDuration(startTime, endTime) {
        if (!startTime) return 'N/A';
        if (!endTime) return 'Running...';
        
        const start = new Date(startTime);
        const end = new Date(endTime);
        const diff = end - start;
        
        if (diff < 1000) return '< 1s';
        if (diff < 60000) return `${Math.round(diff / 1000)}s`;
        if (diff < 3600000) return `${Math.round(diff / 60000)}m`;
        
        const hours = Math.floor(diff / 3600000);
        const minutes = Math.round((diff % 3600000) / 60000);
        return `${hours}h ${minutes}m`;
    }

    cleanup() {
        this.stopAutoRefresh();
    }

    // Worker Control Functions
    async startWorker() {
        try {
            this.showWorkerLoading('Starting worker...');
            
            const response = await fetch('/worker/start', {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                toastr.success(data.message);
                this.updateWorkerStatus(data.status);
                this.loadQueueData(); // Refresh queue after starting worker
            } else {
                toastr.error(data.message || 'Failed to start worker');
            }
            
        } catch (error) {
            console.error('Error starting worker:', error);
            toastr.error('Error starting worker');
        } finally {
            this.hideWorkerLoading();
        }
    }

    async stopWorker() {
        if (!confirm('Are you sure you want to stop the job worker? This will pause all job processing.')) {
            return;
        }

        try {
            this.showWorkerLoading('Stopping worker...');
            
            const response = await fetch('/worker/stop', {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                toastr.success(data.message);
                this.updateWorkerStatus(data.status);
            } else {
                toastr.error(data.message || 'Failed to stop worker');
            }
            
        } catch (error) {
            console.error('Error stopping worker:', error);
            toastr.error('Error stopping worker');
        } finally {
            this.hideWorkerLoading();
        }
    }

    async restartWorker() {
        if (!confirm('Are you sure you want to restart the job worker? This will briefly interrupt job processing.')) {
            return;
        }

        try {
            this.showWorkerLoading('Restarting worker...');
            
            const response = await fetch('/worker/restart', {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                toastr.success(data.message);
                this.updateWorkerStatus(data.status);
                this.loadQueueData(); // Refresh queue after restart
            } else {
                toastr.error(data.message || 'Failed to restart worker');
            }
            
        } catch (error) {
            console.error('Error restarting worker:', error);
            toastr.error('Error restarting worker');
        } finally {
            this.hideWorkerLoading();
        }
    }

    async checkWorkerStatus() {
        try {
            const response = await fetch('/worker/status');
            const data = await response.json();
            
            if (data.success) {
                this.showWorkerStatusModal(data.worker_status);
            } else {
                toastr.error(data.message || 'Failed to get worker status');
            }
            
        } catch (error) {
            console.error('Error getting worker status:', error);
            toastr.error('Error getting worker status');
        }
    }

    async createTestJob() {
        if (!confirm('Create a test job to verify the worker is functioning properly?')) {
            return;
        }

        try {
            const response = await fetch('/test-job', {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                toastr.success(`Test job created: ${data.job_id.substring(0, 8)}...`);
                this.loadQueueData(); // Refresh to show new test job
            } else {
                toastr.error(data.message || 'Failed to create test job');
            }
            
        } catch (error) {
            console.error('Error creating test job:', error);
            toastr.error('Error creating test job');
        }
    }

    updateWorkerStatus(status) {
        const alertElement = document.getElementById('workerStatusAlert');
        const statusText = document.getElementById('workerStatusText');
        
        if (alertElement && statusText) {
            alertElement.className = 'alert mb-3 ' + (status === 'running' ? 'alert-success' : 'alert-warning');
            statusText.innerHTML = status === 'running' 
                ? '<i class="fas fa-check-circle me-2"></i>Job Worker is running'
                : '<i class="fas fa-pause-circle me-2"></i>Job Worker is stopped';
        }
    }

    showWorkerStatusModal(workerStatus) {
        const modalContent = `
            <div class="row">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h6 class="mb-0"><i class="fas fa-info-circle me-2"></i>Worker Status</h6>
                        </div>
                        <div class="card-body">
                            <table class="table table-sm">
                                <tr>
                                    <td><strong>Status:</strong></td>
                                    <td>
                                        <span class="badge ${workerStatus.is_running ? 'bg-success' : 'bg-warning'}">
                                            ${workerStatus.status}
                                        </span>
                                    </td>
                                </tr>
                                <tr>
                                    <td><strong>Thread Alive:</strong></td>
                                    <td>
                                        <span class="badge ${workerStatus.thread_alive ? 'bg-success' : 'bg-danger'}">
                                            ${workerStatus.thread_alive ? 'Yes' : 'No'}
                                        </span>
                                    </td>
                                </tr>
                                <tr>
                                    <td><strong>Registered Handlers:</strong></td>
                                    <td>${workerStatus.registered_handlers.length}</td>
                                </tr>
                            </table>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h6 class="mb-0"><i class="fas fa-chart-bar me-2"></i>Statistics</h6>
                        </div>
                        <div class="card-body">
                            <table class="table table-sm">
                                <tr><td><strong>Total Jobs:</strong></td><td>${workerStatus.statistics.total_jobs || 0}</td></tr>
                                <tr><td><strong>Pending:</strong></td><td>${workerStatus.statistics.status_counts?.pending || 0}</td></tr>
                                <tr><td><strong>Running:</strong></td><td>${workerStatus.statistics.status_counts?.running || 0}</td></tr>
                                <tr><td><strong>Completed:</strong></td><td>${workerStatus.statistics.status_counts?.completed || 0}</td></tr>
                                <tr><td><strong>Failed:</strong></td><td>${workerStatus.statistics.status_counts?.failed || 0}</td></tr>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            
            ${workerStatus.registered_handlers.length > 0 ? `
                <div class="row mt-3">
                    <div class="col-12">
                        <div class="card">
                            <div class="card-header">
                                <h6 class="mb-0"><i class="fas fa-cogs me-2"></i>Registered Job Handlers</h6>
                            </div>
                            <div class="card-body">
                                <div class="d-flex flex-wrap gap-2">
                                    ${workerStatus.registered_handlers.map(handler => 
                                        `<span class="badge bg-primary">${handler}</span>`
                                    ).join('')}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            ` : ''}
        `;

        // Create and show modal
        const modalHtml = `
            <div class="modal fade" id="workerStatusModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-server me-2"></i>Job Worker Status
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            ${modalContent}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal if any
        const existingModal = document.getElementById('workerStatusModal');
        if (existingModal) {
            existingModal.remove();
        }

        // Add new modal to body
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Show modal
        new bootstrap.Modal(document.getElementById('workerStatusModal')).show();
    }

    showWorkerLoading(message) {
        const dropdown = document.querySelector('.dropdown-menu');
        if (dropdown) {
            dropdown.style.pointerEvents = 'none';
            dropdown.style.opacity = '0.7';
        }
        
        // Show loading toast
        this.workerLoadingToast = toastr.info(message, '', {
            timeOut: 0,
            extendedTimeOut: 0,
            closeButton: false,
            tapToDismiss: false
        });
    }

    hideWorkerLoading() {
        const dropdown = document.querySelector('.dropdown-menu');
        if (dropdown) {
            dropdown.style.pointerEvents = 'auto';
            dropdown.style.opacity = '1';
        }
        
        // Hide loading toast
        if (this.workerLoadingToast) {
            toastr.clear(this.workerLoadingToast);
            this.workerLoadingToast = null;
        }
    }
}

// Initialize monitor when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.jobQueueMonitor = new JobQueueMonitor();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.jobQueueMonitor) {
        window.jobQueueMonitor.cleanup();
    }
});