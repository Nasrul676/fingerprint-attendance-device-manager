/**
 * Job History Management JavaScript
 * Handles job history viewing, filtering, pagination, and export functionality
 */

class JobHistory {
    constructor() {
        this.currentPage = 1;
        this.currentFilters = {};
        this.flatpickrStart = null;
        this.flatpickrEnd = null;
        
        // Configure toastr
        toastr.options = {
            closeButton: true,
            debug: false,
            newestOnTop: true,
            progressBar: true,
            positionClass: "toast-top-right",
            preventDuplicates: false,
            onclick: null,
            showDuration: "300",
            hideDuration: "1000",
            timeOut: "5000",
            extendedTimeOut: "1000",
            showEasing: "swing",
            hideEasing: "linear",
            showMethod: "fadeIn",
            hideMethod: "fadeOut"
        };
    }

    init() {
        this.initDatePickers();
        this.bindEvents();
        this.loadHistory();
        this.loadStatistics();
    }

    initDatePickers() {
        // Initialize Flatpickr for date inputs
        this.flatpickrStart = flatpickr("#startDate", {
            dateFormat: "Y-m-d",
            maxDate: "today",
            onChange: (selectedDates, dateStr, instance) => {
                if (this.flatpickrEnd) {
                    this.flatpickrEnd.set('minDate', dateStr);
                }
            }
        });

        this.flatpickrEnd = flatpickr("#endDate", {
            dateFormat: "Y-m-d",
            maxDate: "today"
        });
    }

    bindEvents() {
        // Filter form submission
        document.getElementById('filterForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.currentPage = 1;
            this.applyFilters();
        });

        // Reset filters
        document.getElementById('resetFilters').addEventListener('click', () => {
            this.resetFilters();
        });

        // Export functionality
        document.getElementById('exportHistory').addEventListener('click', () => {
            this.exportHistory();
        });

        // Real-time search
        document.getElementById('searchJob').addEventListener('input', this.debounce(() => {
            this.currentPage = 1;
            this.applyFilters();
        }, 500));

        // Status and priority filter changes
        document.getElementById('statusFilter').addEventListener('change', () => {
            this.currentPage = 1;
            this.applyFilters();
        });

        document.getElementById('priorityFilter').addEventListener('change', () => {
            this.currentPage = 1;
            this.applyFilters();
        });

        document.getElementById('limitFilter').addEventListener('change', () => {
            this.currentPage = 1;
            this.applyFilters();
        });
    }

    async loadHistory(page = 1) {
        try {
            this.showLoading(true);
            
            const params = new URLSearchParams({
                page: page,
                ...this.currentFilters
            });

            const response = await fetch(`/job/api/job-history?${params.toString()}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.renderHistoryTable(data.data.jobs);
                this.renderPagination(data.data.pagination);
                this.showNoData(data.data.jobs.length === 0);
            } else {
                throw new Error(data.message || 'Failed to load job history');
            }
        } catch (error) {
            console.error('Error loading job history:', error);
            toastr.error('Failed to load job history: ' + error.message);
            this.showNoData(true);
        } finally {
            this.showLoading(false);
        }
    }

    async loadStatistics() {
        try {
            const params = new URLSearchParams(this.currentFilters);
            const response = await fetch(`/job/api/job-history-stats?${params.toString()}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.updateStatistics(data.data);
            }
        } catch (error) {
            console.error('Error loading statistics:', error);
        }
    }

    renderHistoryTable(jobs) {
        const tbody = document.getElementById('historyTableBody');
        
        if (!jobs || jobs.length === 0) {
            tbody.innerHTML = '';
            return;
        }

        tbody.innerHTML = jobs.map(job => {
            const startTime = new Date(job.created_at);
            const endTime = job.completed_at ? new Date(job.completed_at) : null;
            const duration = this.calculateDuration(job.created_at, job.completed_at);
            
            return `
                <tr>
                    <td>
                        <div class="fw-bold">${this.escapeHtml(job.job_name)}</div>
                        <div class="job-details">${this.escapeHtml(job.job_data || 'No description')}</div>
                    </td>
                    <td>
                        <span class="status-badge status-${job.status}">${this.capitalizeFirst(job.status)}</span>
                    </td>
                    <td>
                        <span class="priority-badge priority-${job.priority}">${this.capitalizeFirst(job.priority)}</span>
                    </td>
                    <td>
                        <div>${this.formatDateTime(startTime)}</div>
                        <small class="text-muted">${this.formatRelativeTime(startTime)}</small>
                    </td>
                    <td>
                        <div>${endTime ? this.formatDateTime(endTime) : '<span class="text-muted">-</span>'}</div>
                        ${endTime ? `<small class="text-muted">${this.formatRelativeTime(endTime)}</small>` : ''}
                    </td>
                    <td>
                        ${duration ? `<span class="duration-badge">${duration}</span>` : '<span class="text-muted">-</span>'}
                    </td>
                    <td>
                        <div class="text-truncate" style="max-width: 200px;" title="${this.escapeHtml(job.result || 'No result')}">
                            ${this.escapeHtml(job.result || 'No result')}
                        </div>
                    </td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="jobHistory.showJobDetails(${job.id})">
                            <i class="fas fa-eye"></i>
                        </button>
                        ${job.status === 'failed' ? `
                            <button class="btn btn-sm btn-outline-warning ms-1" onclick="jobHistory.retryJob(${job.id})" title="Retry Job">
                                <i class="fas fa-redo"></i>
                            </button>
                        ` : ''}
                    </td>
                </tr>
            `;
        }).join('');
    }

    renderPagination(pagination) {
        const paginationEl = document.getElementById('historyPagination');
        
        if (!pagination || pagination.total_pages <= 1) {
            paginationEl.innerHTML = '';
            return;
        }

        let paginationHTML = '';
        
        // Previous button
        if (pagination.current_page > 1) {
            paginationHTML += `
                <li class="page-item">
                    <a class="page-link" href="#" data-page="${pagination.current_page - 1}">
                        <i class="fas fa-chevron-left"></i>
                    </a>
                </li>
            `;
        }

        // Page numbers
        const startPage = Math.max(1, pagination.current_page - 2);
        const endPage = Math.min(pagination.total_pages, pagination.current_page + 2);

        if (startPage > 1) {
            paginationHTML += `<li class="page-item"><a class="page-link" href="#" data-page="1">1</a></li>`;
            if (startPage > 2) {
                paginationHTML += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
        }

        for (let i = startPage; i <= endPage; i++) {
            paginationHTML += `
                <li class="page-item ${i === pagination.current_page ? 'active' : ''}">
                    <a class="page-link" href="#" data-page="${i}">${i}</a>
                </li>
            `;
        }

        if (endPage < pagination.total_pages) {
            if (endPage < pagination.total_pages - 1) {
                paginationHTML += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
            paginationHTML += `<li class="page-item"><a class="page-link" href="#" data-page="${pagination.total_pages}">${pagination.total_pages}</a></li>`;
        }

        // Next button
        if (pagination.current_page < pagination.total_pages) {
            paginationHTML += `
                <li class="page-item">
                    <a class="page-link" href="#" data-page="${pagination.current_page + 1}">
                        <i class="fas fa-chevron-right"></i>
                    </a>
                </li>
            `;
        }

        paginationEl.innerHTML = paginationHTML;

        // Bind pagination events
        paginationEl.querySelectorAll('a[data-page]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = parseInt(link.getAttribute('data-page'));
                this.currentPage = page;
                this.loadHistory(page);
            });
        });
    }

    updateStatistics(stats) {
        document.getElementById('totalCompleted').textContent = stats.completed || 0;
        document.getElementById('totalFailed').textContent = stats.failed || 0;
        document.getElementById('totalCancelled').textContent = stats.cancelled || 0;
        
        const avgDuration = stats.avg_duration || 0;
        document.getElementById('avgDuration').textContent = avgDuration > 0 ? `${avgDuration}s` : '0s';
    }

    applyFilters() {
        // Collect filter values
        this.currentFilters = {
            status: document.getElementById('statusFilter').value,
            priority: document.getElementById('priorityFilter').value,
            start_date: document.getElementById('startDate').value,
            end_date: document.getElementById('endDate').value,
            search: document.getElementById('searchJob').value,
            limit: document.getElementById('limitFilter').value
        };

        // Remove empty filters
        Object.keys(this.currentFilters).forEach(key => {
            if (!this.currentFilters[key]) {
                delete this.currentFilters[key];
            }
        });

        this.loadHistory(this.currentPage);
        this.loadStatistics();
    }

    resetFilters() {
        // Reset form
        document.getElementById('filterForm').reset();
        
        // Reset date pickers
        if (this.flatpickrStart) this.flatpickrStart.clear();
        if (this.flatpickrEnd) this.flatpickrEnd.clear();
        
        // Reset filters and reload
        this.currentFilters = {};
        this.currentPage = 1;
        this.loadHistory();
        this.loadStatistics();
        
        toastr.info('Filters have been reset');
    }

    async showJobDetails(jobId) {
        try {
            const response = await fetch(`/job/api/job-details/${jobId}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.renderJobDetailsModal(data.data);
                const modal = new bootstrap.Modal(document.getElementById('jobDetailsModal'));
                modal.show();
            } else {
                throw new Error(data.message || 'Failed to load job details');
            }
        } catch (error) {
            console.error('Error loading job details:', error);
            toastr.error('Failed to load job details: ' + error.message);
        }
    }

    renderJobDetailsModal(job) {
        const content = document.getElementById('jobDetailsContent');
        const startTime = new Date(job.created_at);
        const endTime = job.completed_at ? new Date(job.completed_at) : null;
        const duration = this.calculateDuration(job.created_at, job.completed_at);

        content.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h6 class="fw-bold mb-3">Job Information</h6>
                    <table class="table table-sm">
                        <tr>
                            <td class="fw-bold" style="width: 40%;">Job Name:</td>
                            <td>${this.escapeHtml(job.job_name)}</td>
                        </tr>
                        <tr>
                            <td class="fw-bold">Status:</td>
                            <td><span class="status-badge status-${job.status}">${this.capitalizeFirst(job.status)}</span></td>
                        </tr>
                        <tr>
                            <td class="fw-bold">Priority:</td>
                            <td><span class="priority-badge priority-${job.priority}">${this.capitalizeFirst(job.priority)}</span></td>
                        </tr>
                        <tr>
                            <td class="fw-bold">Created:</td>
                            <td>${this.formatDateTime(startTime)}</td>
                        </tr>
                        <tr>
                            <td class="fw-bold">Completed:</td>
                            <td>${endTime ? this.formatDateTime(endTime) : '<span class="text-muted">Not completed</span>'}</td>
                        </tr>
                        <tr>
                            <td class="fw-bold">Duration:</td>
                            <td>${duration ? `<span class="duration-badge">${duration}</span>` : '<span class="text-muted">-</span>'}</td>
                        </tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6 class="fw-bold mb-3">Job Data</h6>
                    <div class="border rounded p-3" style="max-height: 200px; overflow-y: auto; background-color: #f8f9fa;">
                        <pre class="mb-0" style="font-size: 0.85rem;">${this.escapeHtml(job.job_data || 'No job data available')}</pre>
                    </div>
                </div>
            </div>
            <div class="row mt-3">
                <div class="col-12">
                    <h6 class="fw-bold mb-3">Result</h6>
                    <div class="border rounded p-3" style="max-height: 150px; overflow-y: auto; background-color: #f8f9fa;">
                        <pre class="mb-0" style="font-size: 0.85rem;">${this.escapeHtml(job.result || 'No result available')}</pre>
                    </div>
                </div>
            </div>
        `;
    }

    async retryJob(jobId) {
        if (!confirm('Are you sure you want to retry this job?')) {
            return;
        }

        try {
            const response = await fetch(`/job/api/retry-job/${jobId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                toastr.success('Job has been queued for retry');
                this.loadHistory(this.currentPage);
            } else {
                throw new Error(data.message || 'Failed to retry job');
            }
        } catch (error) {
            console.error('Error retrying job:', error);
            toastr.error('Failed to retry job: ' + error.message);
        }
    }

    async exportHistory() {
        try {
            const params = new URLSearchParams({
                ...this.currentFilters,
                export: 'csv'
            });

            const response = await fetch(`/job/api/job-history-export?${params.toString()}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `job_history_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            toastr.success('Job history exported successfully');
        } catch (error) {
            console.error('Error exporting history:', error);
            toastr.error('Failed to export job history: ' + error.message);
        }
    }

    showLoading(show) {
        const spinner = document.getElementById('loadingSpinner');
        const table = document.getElementById('historyTable');
        
        if (show) {
            spinner.style.display = 'block';
            table.style.display = 'none';
        } else {
            spinner.style.display = 'none';
            table.style.display = 'block';
        }
    }

    showNoData(show) {
        const noDataEl = document.getElementById('noDataMessage');
        const tableEl = document.getElementById('historyTable');
        
        if (show) {
            noDataEl.classList.remove('d-none');
            tableEl.style.display = 'none';
        } else {
            noDataEl.classList.add('d-none');
            tableEl.style.display = 'block';
        }
    }

    // Utility functions
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    capitalizeFirst(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    formatDateTime(date) {
        return date.toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }

    formatRelativeTime(date) {
        const now = new Date();
        const diff = now - date;
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`;
        if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        if (minutes > 0) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
        return `${seconds} second${seconds !== 1 ? 's' : ''} ago`;
    }

    calculateDuration(startTime, endTime) {
        if (!startTime || !endTime) return null;
        
        const start = new Date(startTime);
        const end = new Date(endTime);
        const diffMs = end - start;
        
        if (diffMs < 0) return null;
        
        const seconds = Math.floor(diffMs / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        
        if (hours > 0) {
            return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
        } else if (minutes > 0) {
            return `${minutes}m ${seconds % 60}s`;
        } else {
            return `${seconds}s`;
        }
    }
}

// Make JobHistory available globally
window.JobHistory = JobHistory;
window.jobHistory = null;