/**
 * Dashboard Utilities and Shared Components
 * Common functions and classes used across the Job Order Dashboard
 */

// Global dashboard utilities
window.DashboardUtils = {
    
    /**
     * Format currency values consistently
     */
    formatCurrency: function(value, currency = null) {
        if (!value) return '$0.00';
        
        // Use system currency if available
        const system_currency = frappe.defaults.get_default('currency') || 'USD';
        const format_currency = currency || system_currency;
        
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: format_currency,
            minimumFractionDigits: 2
        }).format(value);
    },
    
    /**
     * Format dates consistently
     */
    formatDate: function(date, format = 'MMM DD, YYYY') {
        if (!date) return '-';
        return frappe.datetime.str_to_user(date);
    },
    
    /**
     * Format relative dates (e.g., "3 days ago")
     */
    formatRelativeDate: function(date) {
        if (!date) return '-';
        return frappe.datetime.comment_when(date);
    },
    
    /**
     * Get priority color class
     */
    getPriorityClass: function(priority) {
        const priorityMap = {
            'Urgent': 'priority-urgent',
            'High': 'priority-high',
            'Medium': 'priority-medium',
            'Low': 'priority-low'
        };
        return priorityMap[priority] || 'priority-medium';
    },
    
    /**
     * Get phase color class
     */
    getPhaseClass: function(phase) {
        const phaseMap = {
            'Submission': 'phase-submission',
            'Estimation': 'phase-estimation',
            'Client Approval': 'phase-approval',
            'Planning': 'phase-planning',
            'Prework': 'phase-prework',
            'Execution': 'phase-execution',
            'Review': 'phase-review',
            'Invoicing': 'phase-invoicing',
            'Closeout': 'phase-closeout',
            'Archived': 'phase-archived'
        };
        return phaseMap[phase] || 'phase-default';
    },
    
    /**
     * Calculate progress percentage
     */
    calculateProgress: function(phase) {
        const phaseProgress = {
            'Submission': 10,
            'Estimation': 20,
            'Client Approval': 30,
            'Planning': 40,
            'Prework': 50,
            'Execution': 70,
            'Review': 80,
            'Invoicing': 90,
            'Closeout': 95,
            'Archived': 100
        };
        return phaseProgress[phase] || 0;
    },
    
    /**
     * Format duration in human readable form
     */
    formatDuration: function(hours) {
        if (hours < 24) {
            return `${hours.toFixed(1)} ${__('hours')}`;
        } else if (hours < 168) {
            const days = hours / 24;
            return `${days.toFixed(1)} ${__('days')}`;
        } else {
            const weeks = hours / 168;
            return `${weeks.toFixed(1)} ${__('weeks')}`;
        }
    },
    
    /**
     * Show loading state
     */
    showLoading: function($element, message = 'Loading...') {
        $element.html(`
            <div class="loading-state">
                <div class="spinner-border text-primary" role="status">
                    <span class="sr-only">${__(message)}</span>
                </div>
                <p class="mt-2">${__(message)}</p>
            </div>
        `);
    },
    
    /**
     * Show empty state
     */
    showEmptyState: function($element, message = 'No data available', icon = 'fa-inbox') {
        $element.html(`
            <div class="empty-state">
                <div class="empty-icon">
                    <i class="fa ${icon}"></i>
                </div>
                <p class="empty-message">${__(message)}</p>
            </div>
        `);
    },
    
    /**
     * Show error state
     */
    showErrorState: function($element, message = 'Failed to load data') {
        $element.html(`
            <div class="error-state">
                <div class="error-icon">
                    <i class="fa fa-exclamation-triangle"></i>
                </div>
                <p class="error-message">${__(message)}</p>
                <button class="btn btn-sm btn-outline-primary retry-btn">
                    ${__('Retry')}
                </button>
            </div>
        `);
    },
    
    /**
     * Debounce function calls
     */
    debounce: function(func, wait, immediate) {
        let timeout;
        return function executedFunction() {
            const context = this;
            const args = arguments;
            const later = function() {
                timeout = null;
                if (!immediate) func.apply(context, args);
            };
            const callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func.apply(context, args);
        };
    },
    
    /**
     * Create toast notifications
     */
    showToast: function(message, type = 'info', duration = 3000) {
        const toast = $(`
            <div class="toast toast-${type}" style="position: fixed; top: 20px; right: 20px; z-index: 9999;">
                <div class="toast-body">
                    ${message}
                </div>
            </div>
        `);
        
        $('body').append(toast);
        
        // Auto remove after duration
        setTimeout(() => {
            toast.fadeOut(() => toast.remove());
        }, duration);
    },
    
    /**
     * Export data to CSV
     */
    exportToCSV: function(data, filename = 'export.csv') {
        if (!data || !data.length) {
            frappe.msgprint(__('No data to export'));
            return;
        }
        
        const headers = Object.keys(data[0]);
        const csvContent = [
            headers.join(','),
            ...data.map(row => headers.map(header => `"${row[header] || ''}"`).join(','))
        ].join('\n');
        
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    },
    
    /**
     * Generate chart colors
     */
    getChartColors: function(count = 10, opacity = 0.8) {
        const baseColors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
            '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF',
            '#4BC0C0', '#FF6384'
        ];
        
        return baseColors.slice(0, count).map(color => {
            if (opacity < 1) {
                // Convert hex to rgba
                const r = parseInt(color.slice(1, 3), 16);
                const g = parseInt(color.slice(3, 5), 16);
                const b = parseInt(color.slice(5, 7), 16);
                return `rgba(${r}, ${g}, ${b}, ${opacity})`;
            }
            return color;
        });
    }
};

/**
 * Reusable Dashboard Components
 */

/**
 * Summary Card Component
 */
class SummaryCard {
    constructor(options) {
        this.title = options.title;
        this.value = options.value || 0;
        this.icon = options.icon || 'fa-info';
        this.color = options.color || 'primary';
        this.trend = options.trend || null;
        this.container = options.container;
    }
    
    render() {
        const trendHtml = this.trend ? `
            <div class="card-trend trend-${this.trend.direction}">
                <i class="fa fa-arrow-${this.trend.direction}"></i>
                ${this.trend.value}%
            </div>
        ` : '';
        
        const html = `
            <div class="summary-card card-${this.color}">
                <div class="card-icon">
                    <i class="fa ${this.icon}"></i>
                </div>
                <div class="card-content">
                    <h3 class="card-value">${this.value}</h3>
                    <p class="card-title">${this.title}</p>
                    ${trendHtml}
                </div>
            </div>
        `;
        
        if (this.container) {
            $(this.container).html(html);
        }
        
        return html;
    }
    
    update(value, trend = null) {
        this.value = value;
        if (trend) this.trend = trend;
        this.render();
    }
}

/**
 * Progress Bar Component
 */
class ProgressBar {
    constructor(options) {
        this.value = options.value || 0;
        this.max = options.max || 100;
        this.color = options.color || 'primary';
        this.showLabel = options.showLabel !== false;
        this.size = options.size || 'normal'; // 'small', 'normal', 'large'
        this.container = options.container;
    }
    
    render() {
        const percentage = Math.round((this.value / this.max) * 100);
        const label = this.showLabel ? `<span class="progress-label">${percentage}%</span>` : '';
        
        const html = `
            <div class="progress-wrapper progress-${this.size}">
                <div class="progress">
                    <div class="progress-bar bg-${this.color}" 
                         role="progressbar" 
                         style="width: ${percentage}%"
                         aria-valuenow="${this.value}" 
                         aria-valuemin="0" 
                         aria-valuemax="${this.max}">
                    </div>
                </div>
                ${label}
            </div>
        `;
        
        if (this.container) {
            $(this.container).html(html);
        }
        
        return html;
    }
    
    update(value) {
        this.value = value;
        this.render();
    }
}

/**
 * Status Badge Component
 */
class StatusBadge {
    constructor(options) {
        this.status = options.status;
        this.type = options.type || 'phase'; // 'phase', 'priority', 'status'
        this.size = options.size || 'normal'; // 'small', 'normal', 'large'
        this.container = options.container;
    }
    
    render() {
        const className = this.getStatusClass();
        const html = `
            <span class="status-badge badge-${this.type} badge-${this.size} ${className}">
                ${this.status}
            </span>
        `;
        
        if (this.container) {
            $(this.container).html(html);
        }
        
        return html;
    }
    
    getStatusClass() {
        switch (this.type) {
            case 'priority':
                return DashboardUtils.getPriorityClass(this.status);
            case 'phase':
                return DashboardUtils.getPhaseClass(this.status);
            default:
                return `status-${this.status.toLowerCase().replace(/\s+/g, '-')}`;
        }
    }
}

/**
 * Data Table Component with sorting and filtering
 */
class DataTable {
    constructor(options) {
        this.container = options.container;
        this.data = options.data || [];
        this.columns = options.columns || [];
        this.sortable = options.sortable !== false;
        this.filterable = options.filterable !== false;
        this.paginated = options.paginated !== false;
        this.pageSize = options.pageSize || 10;
        this.currentPage = 1;
        this.sortColumn = null;
        this.sortDirection = 'asc';
        this.filters = {};
        
        this.init();
    }
    
    init() {
        this.render();
        this.bindEvents();
    }
    
    render() {
        const $container = $(this.container);
        $container.empty();
        
        // Create table structure
        const $table = $('<table class="table table-hover data-table">');
        
        // Header
        const $thead = $('<thead>');
        const $headerRow = $('<tr>');
        
        this.columns.forEach(col => {
            const $th = $(`<th data-column="${col.field}">`);
            $th.text(col.title);
            
            if (this.sortable && col.sortable !== false) {
                $th.addClass('sortable');
                if (this.sortColumn === col.field) {
                    $th.addClass(`sorted-${this.sortDirection}`);
                }
            }
            
            $headerRow.append($th);
        });
        
        $thead.append($headerRow);
        $table.append($thead);
        
        // Body
        const $tbody = $('<tbody>');
        const displayData = this.getDisplayData();
        
        displayData.forEach(row => {
            const $tr = $('<tr>');
            
            this.columns.forEach(col => {
                const $td = $('<td>');
                const value = row[col.field];
                
                if (col.formatter) {
                    $td.html(col.formatter(value, row));
                } else {
                    $td.text(value || '');
                }
                
                $tr.append($td);
            });
            
            $tbody.append($tr);
        });
        
        $table.append($tbody);
        $container.append($table);
        
        // Pagination
        if (this.paginated) {
            this.renderPagination();
        }
    }
    
    getDisplayData() {
        let data = [...this.data];
        
        // Apply filters
        Object.keys(this.filters).forEach(column => {
            const filterValue = this.filters[column];
            if (filterValue) {
                data = data.filter(row => {
                    const cellValue = row[column];
                    return cellValue && cellValue.toString().toLowerCase().includes(filterValue.toLowerCase());
                });
            }
        });
        
        // Apply sorting
        if (this.sortColumn) {
            data.sort((a, b) => {
                const aVal = a[this.sortColumn];
                const bVal = b[this.sortColumn];
                
                let comparison = 0;
                if (aVal > bVal) comparison = 1;
                if (aVal < bVal) comparison = -1;
                
                return this.sortDirection === 'desc' ? -comparison : comparison;
            });
        }
        
        // Apply pagination
        if (this.paginated) {
            const start = (this.currentPage - 1) * this.pageSize;
            const end = start + this.pageSize;
            data = data.slice(start, end);
        }
        
        return data;
    }
    
    renderPagination() {
        const totalPages = Math.ceil(this.data.length / this.pageSize);
        if (totalPages <= 1) return;
        
        const $pagination = $('<nav class="table-pagination">');
        const $ul = $('<ul class="pagination justify-content-center">');
        
        // Previous button
        const $prevLi = $('<li class="page-item">');
        if (this.currentPage === 1) $prevLi.addClass('disabled');
        const $prevLink = $('<a class="page-link" href="#">').text('Previous');
        $prevLi.append($prevLink);
        $ul.append($prevLi);
        
        // Page numbers
        for (let i = 1; i <= totalPages; i++) {
            const $li = $('<li class="page-item">');
            if (i === this.currentPage) $li.addClass('active');
            const $link = $('<a class="page-link" href="#">').text(i).data('page', i);
            $li.append($link);
            $ul.append($li);
        }
        
        // Next button
        const $nextLi = $('<li class="page-item">');
        if (this.currentPage === totalPages) $nextLi.addClass('disabled');
        const $nextLink = $('<a class="page-link" href="#">').text('Next');
        $nextLi.append($nextLink);
        $ul.append($nextLi);
        
        $pagination.append($ul);
        $(this.container).append($pagination);
    }
    
    bindEvents() {
        const $container = $(this.container);
        
        // Sorting
        if (this.sortable) {
            $container.on('click', 'th.sortable', (e) => {
                const column = $(e.currentTarget).data('column');
                
                if (this.sortColumn === column) {
                    this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
                } else {
                    this.sortColumn = column;
                    this.sortDirection = 'asc';
                }
                
                this.render();
            });
        }
        
        // Pagination
        if (this.paginated) {
            $container.on('click', '.pagination a', (e) => {
                e.preventDefault();
                const $link = $(e.currentTarget);
                
                if ($link.text() === 'Previous' && this.currentPage > 1) {
                    this.currentPage--;
                } else if ($link.text() === 'Next') {
                    const totalPages = Math.ceil(this.data.length / this.pageSize);
                    if (this.currentPage < totalPages) {
                        this.currentPage++;
                    }
                } else if ($link.data('page')) {
                    this.currentPage = $link.data('page');
                }
                
                this.render();
            });
        }
    }
    
    updateData(newData) {
        this.data = newData;
        this.currentPage = 1;
        this.render();
    }
    
    addFilter(column, value) {
        this.filters[column] = value;
        this.currentPage = 1;
        this.render();
    }
    
    removeFilter(column) {
        delete this.filters[column];
        this.currentPage = 1;
        this.render();
    }
    
    clearFilters() {
        this.filters = {};
        this.currentPage = 1;
        this.render();
    }
}

/**
 * Chart Wrapper Component
 */
class ChartComponent {
    constructor(options) {
        this.container = options.container;
        this.type = options.type || 'bar';
        this.data = options.data || {};
        this.options = options.options || {};
        this.chart = null;
    }
    
    render() {
        const canvas = $(this.container).find('canvas')[0] || 
                      $('<canvas>').appendTo(this.container)[0];
        
        if (this.chart) {
            this.chart.destroy();
        }
        
        const ctx = canvas.getContext('2d');
        this.chart = new Chart(ctx, {
            type: this.type,
            data: this.data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                ...this.options
            }
        });
    }
    
    updateData(newData) {
        if (this.chart) {
            this.chart.data = newData;
            this.chart.update();
        } else {
            this.data = newData;
            this.render();
        }
    }
    
    destroy() {
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }
    }
}

// Expose components globally
window.DashboardComponents = {
    SummaryCard,
    ProgressBar,
    StatusBadge,
    DataTable,
    ChartComponent
};

// Add utility functions to window for global access
window.format_currency = DashboardUtils.formatCurrency;
window.format_date = DashboardUtils.formatDate;
window.format_relative_date = DashboardUtils.formatRelativeDate;