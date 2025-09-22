/**
 * Job Dashboard JavaScript
 * Enhanced job management dashboard with real-time updates
 */

class JobDashboard {
    constructor() {
        this.currentJobId = null;
        this.refreshInterval = null;
        this.notificationInterval = null;
        this.isLoading = false;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadInitialData();
        this.startAutoRefresh();
        this.setupRealTimeUpdates();
    }

    bindEvents() {
        // Form submission
        document.getElementById('createJobForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.createJob();
        });

        // Button events
        document.getElementById('refreshDashboard').addEventListener('click', () => {
            this.refreshAllData();
        });

        document.getElementById('showNotifications').addEventListener('click', () => {
            this.showNotificationsModal();
        });

        document.getElementById('createProcedureJob').addEventListener('click', (e) => {
            e.preventDefault();
            this.showCreateJobModal();
        });

        document.getElementById('cancelJobBtn').addEventListener('click', () => {
            this.cancelCurrentJob();
        });

        // Auto-set today's date
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('targetDate').value = today;
    }

    async loadInitialData() {
        this.showLoadingState();
        
        try {
            await Promise.all([
                this.loadStatistics(),
                this.loadRecentJobs(),
                this.loadSystemStatus(),
                this.loadNotificationCount()
            ]);
        } catch (error) {
            console.error('Error loading initial data:', error);
            toastr.error('Failed to load dashboard data');
        } finally {
            this.hideLoadingState();
        }
    }

    showLoadingState() {
        this.isLoading = true;
        // Loading states are handled by CSS skeletons
    }

    hideLoadingState() {
        this.isLoading = false;
    }

    async loadStatistics() {
        try {
            const response = await fetch('/job/statistics/api');
            const data = await response.json();

            if (data.success) {
                const stats = data.statistics;
                
                // Update stat cards with animation
                this.animateCounter('pendingCount', stats.status_counts?.pending || 0);
                this.animateCounter('runningCount', stats.status_counts?.running || 0);
                this.animateCounter('completedCount', stats.status_counts?.completed || 0);
                this.animateCounter('failedCount', stats.status_counts?.failed || 0);
                this.animateCounter('recentJobsCount', stats.recent_jobs_24h || 0);
                
                // Update system status
                this.updateSystemStatus(stats);
            }
        } catch (error) {
            console.error('Error loading statistics:', error);
            this.showStatError();
        }
    }

    animateCounter(elementId, targetValue) {
        const element = document.getElementById(elementId);
        const currentValue = parseInt(element.textContent) || 0;
        const increment = Math.ceil((targetValue - currentValue) / 20);
        
        if (currentValue !== targetValue) {
            const timer = setInterval(() => {
                const current = parseInt(element.textContent) || 0;
                if (current < targetValue) {
                    element.textContent = Math.min(current + increment, targetValue);
                } else {
                    element.textContent = targetValue;
                    clearInterval(timer);
                }
            }, 50);
        } else {
            element.textContent = targetValue;
        }
    }

    showStatError() {
        ['pendingCount', 'runningCount', 'completedCount', 'failedCount', 'recentJobsCount'].forEach(id => {
            document.getElementById(id).textContent = 'Error';
        });
    }

    updateSystemStatus(stats) {
        const workerStatus = document.getElementById('workerStatus');
        const databaseStatus = document.getElementById('databaseStatus');
        
        // Update worker status
        if (stats.is_worker_running) {
            workerStatus.textContent = 'Online';
            workerStatus.parentElement.className = 'status-indicator status-online';
        } else {
            workerStatus.textContent = 'Offline';
            workerStatus.parentElement.className = 'status-indicator status-offline';
        }
        
        // Database is considered online if we got stats
        databaseStatus.textContent = 'Connected';
        databaseStatus.parentElement.className = 'status-indicator status-online';
    }

    async loadRecentJobs() {
        try {
            const response = await fetch('/job/user?limit=5');
            const data = await response.json();

            if (data.success) {
                this.renderRecentJobs(data.jobs);
            } else {
                document.getElementById('recentJobsList').innerHTML = 
                    '<div class="alert alert-warning">No recent jobs found</div>';
            }
        } catch (error) {
            console.error('Error loading recent jobs:', error);
            document.getElementById('recentJobsList').innerHTML = 
                '<div class="alert alert-danger">Error loading recent jobs</div>';
        }
    }

    renderRecentJobs(jobs) {
        const container = document.getElementById('recentJobsList');
        
        if (jobs.length === 0) {
            container.innerHTML = `
                <div class="text-center py-4 text-muted">
                    <i class="fas fa-inbox fa-3x mb-3"></i>
                    <p>No recent jobs found</p>
                    <button class="btn btn-primary btn-sm" onclick="jobDashboard.showCreateJobModal()">
                        <i class="fas fa-plus me-1"></i>Create Your First Job
                    </button>
                </div>
            `;
            return;
        }

        let html = '';
        jobs.forEach(job => {
            const statusClass = `status-${job.status}`;
            const createdAt = this.formatDateTime(job.created_at);
            const duration = this.calculateDuration(job.created_at, job.completed_at);
            
            html += `
                <div class="job-item" onclick="jobDashboard.showJobDetails('${job.job_id}')">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <div class="d-flex align-items-center mb-2">
                                <span class="job-status ${statusClass} me-2">${job.status}</span>
                                <strong>${job.job_type}</strong>
                                ${job.priority <= 3 ? '<i class="fas fa-exclamation-circle text-warning ms-1" title="High Priority"></i>' : ''}
                            </div>
                            <div class="row">
                                <div class="col-md-6">
                                    <small class="text-muted">
                                        <i class="fas fa-calendar me-1"></i>Target: ${job.job_data.target_date || 'N/A'}
                                    </small><br>
                                    <small class="text-muted">
                                        <i class="fas fa-cogs me-1"></i>Procedures: ${(job.job_data.procedures || []).join(', ')}
                                    </small>
                                </div>
                                <div class="col-md-6">
                                    <small class="text-muted">
                                        <i class="fas fa-clock me-1"></i>Created: ${createdAt}
                                    </small><br>
                                    <small class="text-muted">
                                        <i class="fas fa-stopwatch me-1"></i>Duration: ${duration}
                                    </small>
                                </div>
                            </div>
                        </div>
                        <div class="ms-3">
                            <button class="btn btn-outline-primary btn-sm" onclick="event.stopPropagation(); jobDashboard.showJobDetails('${job.job_id}')">
                                <i class="fas fa-eye"></i>
                            </button>
                            ${job.status === 'pending' ? 
                                `<button class="btn btn-outline-danger btn-sm ms-1" onclick="event.stopPropagation(); jobDashboard.cancelJob('${job.job_id}')">
                                    <i class="fas fa-ban"></i>
                                </button>` : ''
                            }
                        </div>
                    </div>
                    
                    ${job.error_message ? 
                        `<div class="alert alert-danger mt-2 mb-0">
                            <small><i class="fas fa-exclamation-triangle me-1"></i><strong>Error:</strong> ${job.error_message}</small>
                        </div>` : ''
                    }
                    
                    ${job.result_summary ? 
                        `<div class="mt-2 p-2 bg-light rounded">
                            <small><i class="fas fa-check-circle text-success me-1"></i><strong>Result:</strong> ${job.result_summary.successful_procedures}/${job.result_summary.total_procedures} procedures completed</small>
                        </div>` : ''
                    }
                </div>
            `;
        });

        container.innerHTML = html;
    }

    async loadSystemStatus() {
        try {
            // This would be a separate endpoint for system health
            // For now, we'll use the statistics endpoint
            const response = await fetch('/job/statistics/api');
            const data = await response.json();
            
            if (data.success) {
                this.updateSystemStatus(data.statistics);
            }
        } catch (error) {
            console.error('Error loading system status:', error);
            document.getElementById('workerStatus').textContent = 'Unknown';
            document.getElementById('databaseStatus').textContent = 'Unknown';
        }
    }

    async loadNotificationCount() {
        try {
            const response = await fetch('/job/notifications?unread_only=true');
            const data = await response.json();

            if (data.success) {
                const unreadCount = data.notifications.length;
                const countElement = document.getElementById('notificationCount');
                
                if (unreadCount > 0) {
                    countElement.textContent = unreadCount;
                    countElement.style.display = 'flex';
                    
                    // Update navbar badge if exists
                    const navBadge = document.getElementById('notificationBadge');
                    if (navBadge) {
                        navBadge.textContent = unreadCount;
                        navBadge.style.display = 'inline';
                    }
                } else {
                    countElement.style.display = 'none';
                    const navBadge = document.getElementById('notificationBadge');
                    if (navBadge) {
                        navBadge.style.display = 'none';
                    }
                }
            }
        } catch (error) {
            console.error('Error loading notification count:', error);
        }
    }

    showCreateJobModal() {
        const modal = new bootstrap.Modal(document.getElementById('createJobModal'));
        modal.show();
    }

    async createJob() {
        if (this.isLoading) return;
        
        try {
            this.isLoading = true;
            
            const targetDate = document.getElementById('targetDate').value;
            const priority = parseInt(document.getElementById('priority').value);
            
            const procedures = [];
            if (document.getElementById('procAttrecord').checked) {
                procedures.push('attrecord');
            }
            if (document.getElementById('procSpjamkerja').checked) {
                procedures.push('spjamkerja');
            }

            if (procedures.length === 0) {
                toastr.warning('Please select at least one procedure');
                return;
            }

            const response = await fetch('/job/procedure', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    target_date: targetDate,
                    procedures: procedures,
                    priority: priority
                })
            });

            const data = await response.json();

            if (data.success) {
                toastr.success(`🚀 Job created successfully!<br>Job ID: <strong>${data.job_id}</strong>`, '', {
                    timeOut: 6000,
                    escapeHtml: false
                });
                
                document.getElementById('createJobForm').reset();
                
                // Reset to today's date
                const today = new Date().toISOString().split('T')[0];
                document.getElementById('targetDate').value = today;
                
                // Close modal
                bootstrap.Modal.getInstance(document.getElementById('createJobModal')).hide();
                
                // Refresh data
                this.refreshAllData();
            } else {
                toastr.error(data.message || 'Failed to create job');
            }
        } catch (error) {
            console.error('Error creating job:', error);
            toastr.error('Error creating job');
        } finally {
            this.isLoading = false;
        }
    }

    async showJobDetails(jobId) {
        try {
            const response = await fetch(`/job/${jobId}/status`);
            const data = await response.json();

            if (data.success) {
                this.currentJobId = jobId;
                const job = data.job;
                
                let html = this.generateJobDetailsHTML(job);
                
                document.getElementById('jobDetailsContent').innerHTML = html;
                
                // Show cancel button for pending jobs
                const cancelBtn = document.getElementById('cancelJobBtn');
                if (job.status === 'pending') {
                    cancelBtn.style.display = 'block';
                } else {
                    cancelBtn.style.display = 'none';
                }

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
                                <tr>
                                    <td><strong>Job ID:</strong></td>
                                    <td><code>${job.job_id}</code></td>
                                </tr>
                                <tr>
                                    <td><strong>Type:</strong></td>
                                    <td><span class="badge bg-primary">${job.job_type}</span></td>
                                </tr>
                                <tr>
                                    <td><strong>Status:</strong></td>
                                    <td><span class="job-status status-${job.status}">${job.status}</span></td>
                                </tr>
                                <tr>
                                    <td><strong>Priority:</strong></td>
                                    <td>
                                        ${this.getPriorityBadge(job.priority)}
                                        <small class="text-muted">(${job.priority})</small>
                                    </td>
                                </tr>
                                <tr>
                                    <td><strong>Attempts:</strong></td>
                                    <td>${job.attempts}/${job.max_attempts}</td>
                                </tr>
                                <tr>
                                    <td><strong>User:</strong></td>
                                    <td>${job.user_id}</td>
                                </tr>
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
                                <tr>
                                    <td><strong>Created:</strong></td>
                                    <td>${createdAt}</td>
                                </tr>
                                <tr>
                                    <td><strong>Started:</strong></td>
                                    <td>${startedAt}</td>
                                </tr>
                                <tr>
                                    <td><strong>Completed:</strong></td>
                                    <td>${completedAt}</td>
                                </tr>
                                <tr>
                                    <td><strong>Duration:</strong></td>
                                    <td><span class="badge bg-info">${duration}</span></td>
                                </tr>
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

    getPriorityBadge(priority) {
        if (priority <= 1) return '<span class="badge bg-danger">Critical</span>';
        if (priority <= 3) return '<span class="badge bg-warning">High</span>';
        if (priority <= 5) return '<span class="badge bg-primary">Normal</span>';
        if (priority <= 7) return '<span class="badge bg-info">Low</span>';
        return '<span class="badge bg-secondary">Very Low</span>';
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
                this.refreshAllData();
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

    async showNotificationsModal() {
        try {
            const response = await fetch('/job/notifications?limit=50');
            const data = await response.json();

            if (data.success) {
                this.renderNotifications(data.notifications);
                new bootstrap.Modal(document.getElementById('notificationsModal')).show();
            } else {
                toastr.error('Failed to load notifications');
            }
        } catch (error) {
            console.error('Error loading notifications:', error);
            toastr.error('Error loading notifications');
        }
    }

    renderNotifications(notifications) {
        const container = document.getElementById('notificationsList');
        
        if (notifications.length === 0) {
            container.innerHTML = `
                <div class="text-center py-4 text-muted">
                    <i class="fas fa-bell-slash fa-3x mb-3"></i>
                    <p>No notifications found</p>
                </div>
            `;
            return;
        }

        let html = '';
        notifications.forEach(notification => {
            const readClass = notification.is_read ? '' : 'border-primary bg-light';
            const createdAt = this.formatDateTime(notification.created_at);
            const typeIcon = this.getNotificationIcon(notification.type);

            html += `
                <div class="card mb-2 ${readClass}" onclick="jobDashboard.markNotificationRead('${notification.notification_id}', this)">
                    <div class="card-body py-2">
                        <div class="d-flex justify-content-between align-items-start">
                            <div class="flex-grow-1">
                                <h6 class="mb-1">
                                    ${typeIcon} ${notification.title}
                                    ${!notification.is_read ? '<span class="badge bg-primary ms-1">New</span>' : ''}
                                </h6>
                                <p class="mb-1 text-muted">${notification.message}</p>
                                <small class="text-muted">
                                    <i class="fas fa-clock me-1"></i>${createdAt} • 
                                    <i class="fas fa-cogs me-1"></i>Job: ${notification.job_id.substring(0, 8)}...
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    getNotificationIcon(type) {
        switch(type) {
            case 'job_completed': return '<i class="fas fa-check-circle text-success"></i>';
            case 'job_failed': return '<i class="fas fa-exclamation-circle text-danger"></i>';
            default: return '<i class="fas fa-info-circle text-info"></i>';
        }
    }

    async markNotificationRead(notificationId, element) {
        try {
            const response = await fetch(`/job/notifications/${notificationId}/read`, {
                method: 'POST'
            });

            if (response.ok) {
                element.classList.remove('border-primary', 'bg-light');
                const badge = element.querySelector('.badge');
                if (badge) badge.remove();
                
                // Update notification count
                this.loadNotificationCount();
            }
        } catch (error) {
            console.error('Error marking notification as read:', error);
        }
    }

    refreshAllData() {
        if (this.isLoading) return;
        
        toastr.info('🔄 Refreshing dashboard data...', '', {timeOut: 2000});
        this.loadInitialData();
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
        
        if (diff < 1000) return '< 1 second';
        if (diff < 60000) return `${Math.round(diff / 1000)} seconds`;
        if (diff < 3600000) return `${Math.round(diff / 60000)} minutes`;
        
        const hours = Math.floor(diff / 3600000);
        const minutes = Math.round((diff % 3600000) / 60000);
        return `${hours}h ${minutes}m`;
    }

    startAutoRefresh() {
        // Refresh statistics and recent jobs every 30 seconds
        this.refreshInterval = setInterval(() => {
            if (!this.isLoading) {
                this.loadStatistics();
                this.loadRecentJobs();
                this.loadSystemStatus();
            }
        }, 30000);

        // Check notifications every 60 seconds
        this.notificationInterval = setInterval(() => {
            if (!this.isLoading) {
                this.loadNotificationCount();
            }
        }, 60000);
    }

    setupRealTimeUpdates() {
        // This could be enhanced with WebSocket connections for real-time updates
        // For now, we'll rely on polling
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        if (this.notificationInterval) {
            clearInterval(this.notificationInterval);
        }
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.jobDashboard = new JobDashboard();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.jobDashboard) {
        window.jobDashboard.stopAutoRefresh();
    }
});