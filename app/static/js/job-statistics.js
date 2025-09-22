/**
 * Job Statistics Management JavaScript
 * Handles statistics visualization, charts, and performance metrics
 */

class JobStatistics {
    constructor() {
        this.charts = {};
        this.currentFilters = {
            timeRange: 'week',
            jobType: ''
        };
        this.refreshInterval = null;
        
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
        
        // Chart colors
        this.colors = {
            primary: '#3498db',
            success: '#27ae60',
            danger: '#e74c3c',
            warning: '#f39c12',
            info: '#17a2b8',
            secondary: '#6c757d'
        };
    }

    init() {
        this.bindEvents();
        this.initializeCharts();
        this.loadStatistics();
        this.startAutoRefresh();
    }

    bindEvents() {
        // Filter controls
        document.getElementById('applyFilters').addEventListener('click', () => {
            this.applyFilters();
        });

        document.getElementById('refreshStats').addEventListener('click', () => {
            this.loadStatistics();
        });

        // Time range change
        document.getElementById('timeRange').addEventListener('change', () => {
            this.applyFilters();
        });

        // Job type filter change
        document.getElementById('jobTypeFilter').addEventListener('change', () => {
            this.applyFilters();
        });

        // Period selector for trend chart
        document.querySelectorAll('.period-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.updateTrendChart(e.target.getAttribute('data-period'));
            });
        });
    }

    initializeCharts() {
        // Initialize trend chart
        const trendCtx = document.getElementById('trendChart').getContext('2d');
        this.charts.trend = new Chart(trendCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Completed',
                        data: [],
                        borderColor: this.colors.success,
                        backgroundColor: this.hexToRgba(this.colors.success, 0.1),
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Failed',
                        data: [],
                        borderColor: this.colors.danger,
                        backgroundColor: this.hexToRgba(this.colors.danger, 0.1),
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Jobs Count'
                        },
                        beginAtZero: true
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });

        // Initialize status pie chart
        const statusCtx = document.getElementById('statusChart').getContext('2d');
        this.charts.status = new Chart(statusCtx, {
            type: 'doughnut',
            data: {
                labels: ['Completed', 'Failed', 'Cancelled'],
                datasets: [{
                    data: [0, 0, 0],
                    backgroundColor: [
                        this.colors.success,
                        this.colors.danger,
                        this.colors.warning
                    ],
                    borderWidth: 3,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((context.parsed / total) * 100).toFixed(1);
                                return `${context.label}: ${context.parsed} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });

        // Initialize duration chart
        const durationCtx = document.getElementById('durationChart').getContext('2d');
        this.charts.duration = new Chart(durationCtx, {
            type: 'bar',
            data: {
                labels: ['0-30s', '30s-1m', '1-5m', '5-15m', '15m+'],
                datasets: [{
                    label: 'Job Count',
                    data: [0, 0, 0, 0, 0],
                    backgroundColor: this.colors.primary,
                    borderColor: this.colors.primary,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Duration Range'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Number of Jobs'
                        },
                        beginAtZero: true
                    }
                }
            }
        });
    }

    async loadStatistics() {
        try {
            this.showLoading(true);
            
            const params = new URLSearchParams(this.currentFilters);
            const response = await fetch(`/job/api/job-statistics?${params.toString()}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.updateStatistics(data.data);
            } else {
                throw new Error(data.message || 'Failed to load statistics');
            }
        } catch (error) {
            console.error('Error loading statistics:', error);
            toastr.error('Failed to load statistics: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }

    async updateTrendChart(period) {
        try {
            const params = new URLSearchParams({
                ...this.currentFilters,
                period: period
            });
            
            const response = await fetch(`/job/api/job-trends?${params.toString()}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.charts.trend.data.labels = data.data.labels;
                this.charts.trend.data.datasets[0].data = data.data.completed;
                this.charts.trend.data.datasets[1].data = data.data.failed;
                this.charts.trend.update();
            }
        } catch (error) {
            console.error('Error updating trend chart:', error);
            toastr.error('Failed to update trend chart');
        }
    }

    updateStatistics(stats) {
        // Update main statistics cards
        document.getElementById('totalCompleted').textContent = stats.overview.completed || 0;
        document.getElementById('totalFailed').textContent = stats.overview.failed || 0;
        document.getElementById('avgDuration').textContent = `${stats.overview.avg_duration || 0}s`;
        document.getElementById('successRate').textContent = `${stats.overview.success_rate || 0}%`;

        // Update trends
        this.updateTrend('completedTrend', stats.trends.completed_trend || 0);
        this.updateTrend('failedTrend', stats.trends.failed_trend || 0, true); // Inverted for failed (down is good)
        this.updateTrend('durationTrend', stats.trends.duration_trend || 0, true); // Inverted for duration
        this.updateTrend('successRateTrend', stats.trends.success_rate_trend || 0);

        // Update status pie chart
        this.charts.status.data.datasets[0].data = [
            stats.overview.completed || 0,
            stats.overview.failed || 0,
            stats.overview.cancelled || 0
        ];
        this.charts.status.update();

        // Update duration distribution chart
        if (stats.duration_distribution) {
            this.charts.duration.data.datasets[0].data = [
                stats.duration_distribution['0-30s'] || 0,
                stats.duration_distribution['30s-1m'] || 0,
                stats.duration_distribution['1-5m'] || 0,
                stats.duration_distribution['5-15m'] || 0,
                stats.duration_distribution['15m+'] || 0
            ];
            this.charts.duration.update();
        }

        // Update performance metrics
        document.getElementById('avgWaitTime').textContent = `${stats.performance.avg_wait_time || 0}s`;
        document.getElementById('avgRetries').textContent = stats.performance.avg_retries || 0;
        document.getElementById('throughput').textContent = stats.performance.throughput || 0;
        document.getElementById('peakHour').textContent = stats.performance.peak_hour || '--:--';

        // Update metric badges
        this.updateMetricBadge('waitTimeMetric', stats.performance.avg_wait_time || 0, 30, 60);
        this.updateMetricBadge('retriesMetric', stats.performance.avg_retries || 0, 1, 2);
        this.updateMetricBadge('throughputMetric', stats.performance.throughput || 0, 10, 5);

        // Update top job types
        this.updateTopJobTypes(stats.top_job_types || []);

        // Update common errors
        this.updateCommonErrors(stats.common_errors || []);

        // Update trend chart if trend data is available
        if (stats.trend_data) {
            this.charts.trend.data.labels = stats.trend_data.labels;
            this.charts.trend.data.datasets[0].data = stats.trend_data.completed;
            this.charts.trend.data.datasets[1].data = stats.trend_data.failed;
            this.charts.trend.update();
        }
    }

    updateTrend(elementId, value, inverted = false) {
        const element = document.getElementById(elementId);
        const span = element.querySelector('span');
        const icon = element.querySelector('i');
        
        const absValue = Math.abs(value);
        span.textContent = `${value > 0 ? '+' : ''}${value.toFixed(1)}%`;
        
        element.className = 'stat-trend';
        
        if (value > 0) {
            element.classList.add(inverted ? 'trend-down' : 'trend-up');
            icon.className = `fas fa-arrow-${inverted ? 'down' : 'up'}`;
        } else if (value < 0) {
            element.classList.add(inverted ? 'trend-up' : 'trend-down');
            icon.className = `fas fa-arrow-${inverted ? 'up' : 'down'}`;
        } else {
            element.classList.add('trend-neutral');
            icon.className = 'fas fa-minus';
        }
    }

    updateMetricBadge(elementId, value, goodThreshold, warningThreshold) {
        const element = document.getElementById(elementId);
        
        element.className = 'metric-badge';
        
        if (value <= goodThreshold) {
            element.classList.add('metric-good');
            element.textContent = 'Good';
        } else if (value <= warningThreshold) {
            element.classList.add('metric-warning');
            element.textContent = 'Warning';
        } else {
            element.classList.add('metric-danger');
            element.textContent = 'Poor';
        }
    }

    updateTopJobTypes(topJobTypes) {
        const container = document.getElementById('topJobTypes');
        
        if (!topJobTypes || topJobTypes.length === 0) {
            container.innerHTML = '<div class="text-center text-muted py-4">No data available</div>';
            return;
        }
        
        container.innerHTML = topJobTypes.map((item, index) => `
            <div class="top-list-item">
                <div class="top-list-rank">#${index + 1}</div>
                <div class="top-list-content">
                    <div class="top-list-title">${this.escapeHtml(item.job_type)}</div>
                    <div class="top-list-subtitle">${item.percentage}% of total jobs</div>
                </div>
                <div class="top-list-value">${item.count}</div>
            </div>
        `).join('');
    }

    updateCommonErrors(commonErrors) {
        const container = document.getElementById('commonErrors');
        
        if (!commonErrors || commonErrors.length === 0) {
            container.innerHTML = '<div class="text-center text-muted py-4">No errors found</div>';
            return;
        }
        
        container.innerHTML = commonErrors.map((item, index) => `
            <div class="top-list-item">
                <div class="top-list-rank">#${index + 1}</div>
                <div class="top-list-content">
                    <div class="top-list-title">${this.escapeHtml(item.error_type)}</div>
                    <div class="top-list-subtitle">${item.percentage}% of failed jobs</div>
                </div>
                <div class="top-list-value">${item.count}</div>
            </div>
        `).join('');
    }

    applyFilters() {
        this.currentFilters = {
            timeRange: document.getElementById('timeRange').value,
            jobType: document.getElementById('jobTypeFilter').value
        };
        
        // Remove empty filters
        Object.keys(this.currentFilters).forEach(key => {
            if (!this.currentFilters[key]) {
                delete this.currentFilters[key];
            }
        });
        
        this.loadStatistics();
        toastr.info('Filters applied successfully');
    }

    startAutoRefresh() {
        // Refresh every 5 minutes
        this.refreshInterval = setInterval(() => {
            this.loadStatistics();
        }, 300000);
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    showLoading(show) {
        const spinner = document.getElementById('loadingSpinner');
        
        if (show) {
            spinner.classList.remove('d-none');
        } else {
            spinner.classList.add('d-none');
        }
    }

    // Utility functions
    hexToRgba(hex, alpha) {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }

    escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }

    formatDuration(seconds) {
        if (seconds < 60) {
            return `${seconds}s`;
        } else if (seconds < 3600) {
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = seconds % 60;
            return `${minutes}m ${remainingSeconds}s`;
        } else {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return `${hours}h ${minutes}m`;
        }
    }

    destroy() {
        this.stopAutoRefresh();
        
        // Destroy charts
        Object.values(this.charts).forEach(chart => {
            if (chart) {
                chart.destroy();
            }
        });
    }
}

// Make JobStatistics available globally
window.JobStatistics = JobStatistics;