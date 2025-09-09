// Job Order Dashboard JavaScript
// Main dashboard functionality and interactions

frappe.pages['job-order-dashboard'].on_page_load = function(wrapper) {
    const dashboard = new JobOrderDashboard(wrapper);
    dashboard.init();
};

class JobOrderDashboard {
    constructor(wrapper) {
        this.wrapper = wrapper;
        this.page = frappe.ui.make_app_page({
            parent: wrapper,
            title: __('Job Order Dashboard'),
            single_column: false
        });
        
        // Initialize properties
        this.charts = {};
        this.current_view = 'overview';
        this.refresh_interval = null;
        this.kanban_data = {};
        this.calendar_instance = null;
        
        // Bind context
        this.init = this.init.bind(this);
        this.refresh_dashboard = this.refresh_dashboard.bind(this);
    }
    
    init() {
        this.setup_page();
        this.setup_event_listeners();
        this.load_overview_data();
        this.setup_auto_refresh();
    }
    
    setup_page() {
        // Add custom CSS classes
        this.wrapper.addClass('job-dashboard-wrapper');
        
        // Setup page actions
        this.page.set_primary_action(__('New Job Order'), () => {
            frappe.new_doc('Job Order');
        }, 'add');
        
        this.page.add_action_item(__('Refresh'), () => {
            this.refresh_dashboard();
        }, 'refresh');
        
        this.page.add_action_item(__('Settings'), () => {
            this.show_dashboard_settings();
        }, 'settings');
        
        // Setup page body
        this.page.main.html(this.get_dashboard_html());
    }
    
    get_dashboard_html() {
        return `
        <div class="dashboard-container">
            <div class="dashboard-tabs">
                <ul class="nav nav-tabs" role="tablist">
                    <li class="nav-item">
                        <a class="nav-link active" data-tab="overview" href="#overview">
                            <i class="fa fa-dashboard"></i> ${__('Overview')}
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" data-tab="kanban" href="#kanban">
                            <i class="fa fa-columns"></i> ${__('Kanban')}
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" data-tab="calendar" href="#calendar">
                            <i class="fa fa-calendar"></i> ${__('Calendar')}
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" data-tab="analytics" href="#analytics">
                            <i class="fa fa-bar-chart"></i> ${__('Analytics')}
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" data-tab="list" href="#list">
                            <i class="fa fa-list"></i> ${__('List View')}
                        </a>
                    </li>
                </ul>
            </div>
            
            <div class="tab-content">
                <div class="tab-pane active" id="overview">
                    ${this.get_overview_html()}
                </div>
                <div class="tab-pane" id="kanban">
                    ${this.get_kanban_html()}
                </div>
                <div class="tab-pane" id="calendar">
                    ${this.get_calendar_html()}
                </div>
                <div class="tab-pane" id="analytics">
                    ${this.get_analytics_html()}
                </div>
                <div class="tab-pane" id="list">
                    ${this.get_list_html()}
                </div>
            </div>
            
            <div class="dashboard-loading" style="display: none;">
                <div class="loading-content">
                    <div class="spinner"></div>
                    <p>${__('Loading dashboard data...')}</p>
                </div>
            </div>
        </div>`;
    }
    
    get_overview_html() {
        return `
        <div class="overview-container">
            <!-- Summary Cards -->
            <div class="row summary-cards">
                <div class="col-md-3">
                    <div class="summary-card total-jobs">
                        <div class="card-icon"><i class="fa fa-briefcase"></i></div>
                        <div class="card-content">
                            <h3 class="card-value" data-field="total_jobs">-</h3>
                            <p class="card-label">${__('Total Jobs')}</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="summary-card active-jobs">
                        <div class="card-icon"><i class="fa fa-play-circle"></i></div>
                        <div class="card-content">
                            <h3 class="card-value" data-field="active_jobs">-</h3>
                            <p class="card-label">${__('Active Jobs')}</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="summary-card completed-jobs">
                        <div class="card-icon"><i class="fa fa-check-circle"></i></div>
                        <div class="card-content">
                            <h3 class="card-value" data-field="completed_jobs">-</h3>
                            <p class="card-label">${__('Completed Jobs')}</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="summary-card completion-rate">
                        <div class="card-icon"><i class="fa fa-percentage"></i></div>
                        <div class="card-content">
                            <h3 class="card-value" data-field="completion_rate">-%</h3>
                            <p class="card-label">${__('Completion Rate')}</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Charts Row -->
            <div class="row charts-row">
                <div class="col-md-6">
                    <div class="chart-container">
                        <h5>${__('Phase Distribution')}</h5>
                        <canvas id="phase-chart"></canvas>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="chart-container">
                        <h5>${__('Priority Distribution')}</h5>
                        <canvas id="priority-chart"></canvas>
                    </div>
                </div>
            </div>
            
            <!-- Recent Activity and Alerts -->
            <div class="row activity-row">
                <div class="col-md-8">
                    <div class="recent-activity">
                        <h5>${__('Recent Jobs')}</h5>
                        <div class="activity-list" id="recent-jobs-list">
                            <!-- Jobs will be loaded here -->
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="alerts-panel">
                        <h5>${__('Alerts & Overdue')}</h5>
                        <div class="alerts-list" id="alerts-list">
                            <!-- Alerts will be loaded here -->
                        </div>
                    </div>
                </div>
            </div>
        </div>`;
    }
    
    get_kanban_html() {
        return `
        <div class="kanban-container">
            <div class="kanban-toolbar">
                <div class="row">
                    <div class="col-md-3">
                        <select class="form-control" id="kanban-customer-filter">
                            <option value="">${__('All Customers')}</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <select class="form-control" id="kanban-priority-filter">
                            <option value="">${__('All Priorities')}</option>
                            <option value="Urgent">${__('Urgent')}</option>
                            <option value="High">${__('High')}</option>
                            <option value="Medium">${__('Medium')}</option>
                            <option value="Low">${__('Low')}</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <select class="form-control" id="kanban-date-filter">
                            <option value="">${__('All Time')}</option>
                            <option value="this_week">${__('This Week')}</option>
                            <option value="this_month">${__('This Month')}</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <button class="btn btn-primary" id="apply-kanban-filters">
                            ${__('Apply Filters')}
                        </button>
                    </div>
                </div>
            </div>
            <div id="kanban-board" class="kanban-board">
                <!-- Kanban columns will be generated here -->
            </div>
        </div>`;
    }
    
    get_calendar_html() {
        return `
        <div class="calendar-container">
            <div class="calendar-toolbar">
                <div class="btn-group view-buttons">
                    <button class="btn btn-outline-primary" data-view="month">${__('Month')}</button>
                    <button class="btn btn-outline-primary" data-view="week">${__('Week')}</button>
                    <button class="btn btn-outline-primary active" data-view="agenda">${__('Agenda')}</button>
                </div>
                <div class="calendar-navigation">
                    <button class="btn btn-outline-secondary" id="calendar-prev">
                        <i class="fa fa-chevron-left"></i>
                    </button>
                    <span class="calendar-title" id="calendar-title">${__('Loading...')}</span>
                    <button class="btn btn-outline-secondary" id="calendar-next">
                        <i class="fa fa-chevron-right"></i>
                    </button>
                </div>
            </div>
            <div id="job-calendar" class="calendar-view">
                <!-- Calendar will be rendered here -->
            </div>
        </div>`;
    }
    
    get_analytics_html() {
        return `
        <div class="analytics-container">
            <div class="analytics-toolbar">
                <div class="row">
                    <div class="col-md-4">
                        <select class="form-control" id="analytics-period">
                            <option value="30">${__('Last 30 Days')}</option>
                            <option value="60">${__('Last 60 Days')}</option>
                            <option value="90">${__('Last 90 Days')}</option>
                            <option value="180">${__('Last 6 Months')}</option>
                            <option value="365">${__('Last Year')}</option>
                        </select>
                    </div>
                    <div class="col-md-4">
                        <button class="btn btn-primary" id="refresh-analytics">
                            ${__('Refresh Analytics')}
                        </button>
                    </div>
                </div>
            </div>
            
            <div class="row analytics-charts">
                <div class="col-md-6">
                    <div class="chart-container">
                        <h5>${__('Phase Duration Trends')}</h5>
                        <canvas id="phase-duration-chart"></canvas>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="chart-container">
                        <h5>${__('Revenue Trends')}</h5>
                        <canvas id="revenue-trend-chart"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="row analytics-charts">
                <div class="col-md-6">
                    <div class="chart-container">
                        <h5>${__('Bottleneck Analysis')}</h5>
                        <div id="bottleneck-analysis" class="bottleneck-list">
                            <!-- Bottleneck data will be loaded here -->
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="chart-container">
                        <h5>${__('Customer Performance')}</h5>
                        <canvas id="customer-performance-chart"></canvas>
                    </div>
                </div>
            </div>
        </div>`;
    }
    
    get_list_html() {
        return `
        <div class="list-container">
            <div class="list-toolbar">
                <div class="row">
                    <div class="col-md-3">
                        <input type="text" class="form-control" id="job-search" 
                               placeholder="${__('Search jobs...')}">
                    </div>
                    <div class="col-md-2">
                        <select class="form-control" id="list-phase-filter">
                            <option value="">${__('All Phases')}</option>
                            <option value="Submission">${__('Submission')}</option>
                            <option value="Estimation">${__('Estimation')}</option>
                            <option value="Client Approval">${__('Client Approval')}</option>
                            <option value="Planning">${__('Planning')}</option>
                            <option value="Prework">${__('Prework')}</option>
                            <option value="Execution">${__('Execution')}</option>
                            <option value="Review">${__('Review')}</option>
                            <option value="Invoicing">${__('Invoicing')}</option>
                            <option value="Closeout">${__('Closeout')}</option>
                            <option value="Archived">${__('Archived')}</option>
                        </select>
                    </div>
                    <div class="col-md-2">
                        <select class="form-control" id="list-priority-filter">
                            <option value="">${__('All Priorities')}</option>
                            <option value="Urgent">${__('Urgent')}</option>
                            <option value="High">${__('High')}</option>
                            <option value="Medium">${__('Medium')}</option>
                            <option value="Low">${__('Low')}</option>
                        </select>
                    </div>
                    <div class="col-md-2">
                        <button class="btn btn-primary" id="apply-list-filters">
                            ${__('Filter')}
                        </button>
                    </div>
                    <div class="col-md-3 text-right">
                        <button class="btn btn-success" id="create-new-job">
                            <i class="fa fa-plus"></i> ${__('New Job Order')}
                        </button>
                    </div>
                </div>
            </div>
            
            <div class="job-list-container">
                <table class="table table-hover" id="job-list-table">
                    <thead>
                        <tr>
                            <th>${__('Job Number')}</th>
                            <th>${__('Customer')}</th>
                            <th>${__('Project')}</th>
                            <th>${__('Phase')}</th>
                            <th>${__('Priority')}</th>
                            <th>${__('Start Date')}</th>
                            <th>${__('Value')}</th>
                            <th>${__('Status')}</th>
                            <th>${__('Actions')}</th>
                        </tr>
                    </thead>
                    <tbody id="job-list-body">
                        <!-- Job list will be loaded here -->
                    </tbody>
                </table>
                
                <!-- Pagination -->
                <div class="row">
                    <div class="col-md-6">
                        <div id="list-pagination-info" class="pagination-info">
                            <!-- Pagination info -->
                        </div>
                    </div>
                    <div class="col-md-6">
                        <nav>
                            <ul class="pagination justify-content-end" id="list-pagination">
                                <!-- Pagination controls -->
                            </ul>
                        </nav>
                    </div>
                </div>
            </div>
        </div>`;
    }
    
    setup_event_listeners() {
        const $wrapper = $(this.wrapper);
        
        // Tab switching
        $wrapper.on('click', '.nav-link', (e) => {
            e.preventDefault();
            const tab = $(e.currentTarget).data('tab');
            this.switch_tab(tab);
        });
        
        // Overview tab events
        $wrapper.on('click', '#refresh-dashboard', () => this.refresh_dashboard());
        $wrapper.on('click', '#view-all-jobs', () => this.switch_tab('list'));
        
        // Kanban events
        $wrapper.on('click', '#apply-kanban-filters', () => this.load_kanban_data());
        
        // Calendar events
        $wrapper.on('click', '.view-buttons .btn', (e) => {
            const view = $(e.currentTarget).data('view');
            this.switch_calendar_view(view);
        });
        $wrapper.on('click', '#calendar-prev', () => this.navigate_calendar('prev'));
        $wrapper.on('click', '#calendar-next', () => this.navigate_calendar('next'));
        
        // Analytics events
        $wrapper.on('click', '#refresh-analytics', () => this.load_analytics_data());
        $wrapper.on('change', '#analytics-period', () => this.load_analytics_data());
        
        // List view events
        $wrapper.on('click', '#apply-list-filters', () => this.load_list_data());
        $wrapper.on('click', '#create-new-job', () => frappe.new_doc('Job Order'));
        $wrapper.on('input', '#job-search', frappe.utils.debounce(() => this.load_list_data(), 300));
        
        // Job actions
        $wrapper.on('click', '.view-job-btn', (e) => {
            const jobName = $(e.currentTarget).data('job');
            this.show_job_detail(jobName);
        });
        
        $wrapper.on('click', '.edit-job-btn', (e) => {
            const jobName = $(e.currentTarget).data('job');
            frappe.set_route('Form', 'Job Order', jobName);
        });
    }
    
    switch_tab(tab) {
        if (this.current_view === tab) return;
        
        const $wrapper = $(this.wrapper);
        
        // Update nav
        $wrapper.find('.nav-link').removeClass('active');
        $wrapper.find(`[data-tab="${tab}"]`).addClass('active');
        
        // Update content
        $wrapper.find('.tab-pane').removeClass('active');
        $wrapper.find(`#${tab}`).addClass('active');
        
        this.current_view = tab;
        
        // Load tab-specific data
        switch (tab) {
            case 'overview':
                this.load_overview_data();
                break;
            case 'kanban':
                this.load_kanban_data();
                break;
            case 'calendar':
                this.load_calendar_data();
                break;
            case 'analytics':
                this.load_analytics_data();
                break;
            case 'list':
                this.load_list_data();
                break;
        }
    }
    
    show_loading(show = true) {
        const $loading = $(this.wrapper).find('.dashboard-loading');
        if (show) {
            $loading.show();
        } else {
            $loading.hide();
        }
    }
    
    load_overview_data() {
        this.show_loading(true);
        
        frappe.call({
            method: 'api_next.page.job_order_dashboard.job_order_dashboard.get_dashboard_overview',
            callback: (r) => {
                this.show_loading(false);
                if (r.message && r.message.success) {
                    this.render_overview(r.message.data);
                } else {
                    frappe.msgprint(__('Failed to load dashboard data'));
                }
            }
        });
    }
    
    render_overview(data) {
        const $wrapper = $(this.wrapper);
        
        // Update summary cards
        if (data.summary) {
            $wrapper.find('[data-field="total_jobs"]').text(data.summary.total_jobs || 0);
            $wrapper.find('[data-field="active_jobs"]').text(data.summary.active_jobs || 0);
            $wrapper.find('[data-field="completed_jobs"]').text(data.summary.completed_jobs || 0);
            $wrapper.find('[data-field="completion_rate"]').text(`${data.summary.completion_rate || 0}%`);
        }
        
        // Render phase distribution chart
        if (data.phase_distribution) {
            this.render_phase_chart(data.phase_distribution);
        }
        
        // Render priority distribution chart
        if (data.priority_distribution) {
            this.render_priority_chart(data.priority_distribution);
        }
        
        // Render recent jobs
        if (data.recent_jobs) {
            this.render_recent_jobs(data.recent_jobs);
        }
        
        // Render alerts
        if (data.overdue_jobs) {
            this.render_alerts(data.overdue_jobs);
        }
    }
    
    render_phase_chart(data) {
        const ctx = $(this.wrapper).find('#phase-chart')[0].getContext('2d');
        
        if (this.charts.phase) {
            this.charts.phase.destroy();
        }
        
        this.charts.phase = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.map(d => d.workflow_state),
                datasets: [{
                    data: data.map(d => d.count),
                    backgroundColor: [
                        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
                        '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF',
                        '#4BC0C0', '#FF6384'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                legend: {
                    position: 'bottom'
                }
            }
        });
    }
    
    render_priority_chart(data) {
        const ctx = $(this.wrapper).find('#priority-chart')[0].getContext('2d');
        
        if (this.charts.priority) {
            this.charts.priority.destroy();
        }
        
        this.charts.priority = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(d => d.priority),
                datasets: [{
                    data: data.map(d => d.count),
                    backgroundColor: ['#FF4444', '#FF8800', '#FFCC00', '#44AA44']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                },
                legend: {
                    display: false
                }
            }
        });
    }
    
    render_recent_jobs(jobs) {
        const $list = $(this.wrapper).find('#recent-jobs-list');
        $list.empty();
        
        jobs.forEach(job => {
            const priorityClass = `priority-${(job.priority || 'medium').toLowerCase()}`;
            const totalValue = (job.total_material_cost || 0) + (job.total_labor_cost || 0);
            
            $list.append(`
                <div class="job-item ${priorityClass}" data-job="${job.name}">
                    <div class="job-header">
                        <span class="job-number">${job.job_number}</span>
                        <span class="job-priority ${priorityClass}">${job.priority || 'Medium'}</span>
                    </div>
                    <div class="job-details">
                        <div class="job-customer">${job.customer_name}</div>
                        <div class="job-project">${job.project_name}</div>
                        <div class="job-phase">${job.workflow_state}</div>
                        <div class="job-value">${format_currency(totalValue)}</div>
                    </div>
                    <div class="job-actions">
                        <button class="btn btn-sm btn-outline-primary view-job-btn" data-job="${job.name}">
                            ${__('View')}
                        </button>
                        <button class="btn btn-sm btn-outline-secondary edit-job-btn" data-job="${job.name}">
                            ${__('Edit')}
                        </button>
                    </div>
                </div>
            `);
        });
    }
    
    render_alerts(overdue_data) {
        const $alerts = $(this.wrapper).find('#alerts-list');
        $alerts.empty();
        
        // Render overdue jobs
        if (overdue_data.overdue && overdue_data.overdue.length > 0) {
            overdue_data.overdue.forEach(job => {
                $alerts.append(`
                    <div class="alert alert-danger">
                        <strong>${__('Overdue')}:</strong> ${job.job_number}<br>
                        <small>${job.customer_name} - ${job.days_overdue} ${__('days overdue')}</small>
                    </div>
                `);
            });
        }
        
        // Render at-risk jobs
        if (overdue_data.at_risk && overdue_data.at_risk.length > 0) {
            overdue_data.at_risk.forEach(job => {
                $alerts.append(`
                    <div class="alert alert-warning">
                        <strong>${__('Due Soon')}:</strong> ${job.job_number}<br>
                        <small>${job.customer_name} - ${job.days_remaining} ${__('days remaining')}</small>
                    </div>
                `);
            });
        }
        
        if ($alerts.children().length === 0) {
            $alerts.append(`<div class="no-alerts">${__('No alerts at this time')}</div>`);
        }
    }
    
    load_kanban_data() {
        this.show_loading(true);
        
        const filters = {
            customer: $(this.wrapper).find('#kanban-customer-filter').val(),
            priority: $(this.wrapper).find('#kanban-priority-filter').val(),
            date_range: $(this.wrapper).find('#kanban-date-filter').val()
        };
        
        frappe.call({
            method: 'api_next.page.job_order_dashboard.job_order_dashboard.get_jobs_for_kanban',
            args: { filters: filters },
            callback: (r) => {
                this.show_loading(false);
                if (r.message && r.message.success) {
                    this.render_kanban_board(r.message.data);
                }
            }
        });
    }
    
    render_kanban_board(kanban_data) {
        const $board = $(this.wrapper).find('#kanban-board');
        $board.empty();
        
        const phases = Object.keys(kanban_data);
        phases.forEach(phase => {
            const column_data = kanban_data[phase];
            const $column = $(`
                <div class="kanban-column" data-phase="${phase}">
                    <div class="column-header">
                        <h5>${column_data.title}</h5>
                        <span class="job-count">${column_data.count}</span>
                        <span class="column-value">${format_currency(column_data.total_value)}</span>
                    </div>
                    <div class="column-body" data-phase="${phase}">
                        <!-- Jobs will be added here -->
                    </div>
                </div>
            `);
            
            // Add jobs to column
            column_data.jobs.forEach(job => {
                const $job_card = this.create_kanban_job_card(job);
                $column.find('.column-body').append($job_card);
            });
            
            $board.append($column);
        });
        
        // Make columns sortable
        this.setup_kanban_drag_drop();
    }
    
    create_kanban_job_card(job) {
        const priorityClass = `priority-${(job.priority || 'medium').toLowerCase()}`;
        const overdueClass = job.is_overdue ? 'overdue' : '';
        
        return $(`
            <div class="kanban-job-card ${priorityClass} ${overdueClass}" data-job="${job.name}">
                <div class="job-card-header">
                    <span class="job-number">${job.job_number}</span>
                    <span class="priority-badge ${priorityClass}">${job.priority || 'Medium'}</span>
                </div>
                <div class="job-card-body">
                    <div class="customer-name">${job.customer_name}</div>
                    <div class="project-name">${job.project_name}</div>
                    <div class="job-value">${format_currency(job.total_value || 0)}</div>
                    ${job.phase_target_date ? `<div class="target-date">${__('Due')}: ${frappe.datetime.str_to_user(job.phase_target_date)}</div>` : ''}
                </div>
                <div class="job-card-footer">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${job.progress || 0}%"></div>
                    </div>
                    <div class="job-actions">
                        <button class="btn btn-sm btn-outline-primary view-job-btn" data-job="${job.name}">
                            ${__('View')}
                        </button>
                    </div>
                </div>
            </div>
        `);
    }
    
    setup_kanban_drag_drop() {
        // This would setup drag and drop functionality for the kanban board
        // Implementation would use a library like SortableJS or implement custom drag/drop
    }
    
    load_list_data(page = 1) {
        this.show_loading(true);
        
        const filters = {
            phase: $(this.wrapper).find('#list-phase-filter').val(),
            priority: $(this.wrapper).find('#list-priority-filter').val()
        };
        
        const search = $(this.wrapper).find('#job-search').val();
        
        frappe.call({
            method: 'api_next.api.dashboard.get_advanced_job_list',
            args: {
                filters: filters,
                search: search,
                page: page,
                limit: 20
            },
            callback: (r) => {
                this.show_loading(false);
                if (r.message && r.message.success) {
                    this.render_job_list(r.message.data);
                }
            }
        });
    }
    
    render_job_list(data) {
        const $tbody = $(this.wrapper).find('#job-list-body');
        $tbody.empty();
        
        data.jobs.forEach(job => {
            const priorityClass = `priority-${(job.priority || 'medium').toLowerCase()}`;
            const overdueClass = job.is_overdue ? 'overdue' : '';
            
            $tbody.append(`
                <tr class="${priorityClass} ${overdueClass}" data-job="${job.name}">
                    <td><a href="/app/job-order/${job.name}">${job.job_number}</a></td>
                    <td>${job.customer_name}</td>
                    <td>${job.project_name}</td>
                    <td><span class="phase-badge">${job.workflow_state}</span></td>
                    <td><span class="priority-badge ${priorityClass}">${job.priority || 'Medium'}</span></td>
                    <td>${job.start_date ? frappe.datetime.str_to_user(job.start_date) : '-'}</td>
                    <td>${format_currency(job.total_value || 0)}</td>
                    <td><span class="status-badge">${job.status}</span></td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary view-job-btn" data-job="${job.name}">
                            ${__('View')}
                        </button>
                        <button class="btn btn-sm btn-outline-secondary edit-job-btn" data-job="${job.name}">
                            ${__('Edit')}
                        </button>
                    </td>
                </tr>
            `);
        });
        
        // Update pagination
        this.render_pagination(data.pagination);
    }
    
    render_pagination(pagination) {
        const $info = $(this.wrapper).find('#list-pagination-info');
        const $controls = $(this.wrapper).find('#list-pagination');
        
        // Update info
        $info.text(`${__('Showing')} ${(pagination.current_page - 1) * pagination.limit + 1} ${__('to')} ${Math.min(pagination.current_page * pagination.limit, pagination.total_count)} ${__('of')} ${pagination.total_count} ${__('jobs')}`);
        
        // Update controls
        $controls.empty();
        
        // Previous button
        if (pagination.has_prev) {
            $controls.append(`
                <li class="page-item">
                    <a class="page-link" href="#" data-page="${pagination.current_page - 1}">
                        ${__('Previous')}
                    </a>
                </li>
            `);
        }
        
        // Page numbers (simplified - show current and adjacent pages)
        for (let i = Math.max(1, pagination.current_page - 2); 
             i <= Math.min(pagination.total_pages, pagination.current_page + 2); i++) {
            const activeClass = i === pagination.current_page ? 'active' : '';
            $controls.append(`
                <li class="page-item ${activeClass}">
                    <a class="page-link" href="#" data-page="${i}">${i}</a>
                </li>
            `);
        }
        
        // Next button
        if (pagination.has_next) {
            $controls.append(`
                <li class="page-item">
                    <a class="page-link" href="#" data-page="${pagination.current_page + 1}">
                        ${__('Next')}
                    </a>
                </li>
            `);
        }
        
        // Bind pagination events
        $controls.find('a').on('click', (e) => {
            e.preventDefault();
            const page = $(e.currentTarget).data('page');
            if (page) {
                this.load_list_data(page);
            }
        });
    }
    
    load_analytics_data() {
        this.show_loading(true);
        
        const period = $(this.wrapper).find('#analytics-period').val() || '30';
        
        frappe.call({
            method: 'api_next.api.dashboard.get_analytics_data',
            args: { period: period },
            callback: (r) => {
                this.show_loading(false);
                if (r.message && r.message.success) {
                    this.render_analytics(r.message.data);
                }
            }
        });
    }
    
    render_analytics(data) {
        // Render phase duration chart
        if (data.phase_duration) {
            this.render_phase_duration_chart(data.phase_duration);
        }
        
        // Render revenue trend chart
        if (data.revenue_trend) {
            this.render_revenue_trend_chart(data.revenue_trend);
        }
        
        // Render bottleneck analysis
        if (data.bottleneck) {
            this.render_bottleneck_analysis(data.bottleneck);
        }
        
        // Render customer performance chart
        if (data.customer_performance) {
            this.render_customer_performance_chart(data.customer_performance);
        }
    }
    
    render_phase_duration_chart(data) {
        const ctx = $(this.wrapper).find('#phase-duration-chart')[0];
        if (!ctx) return;
        
        if (this.charts.phase_duration) {
            this.charts.phase_duration.destroy();
        }
        
        this.charts.phase_duration = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: __('Average Days'),
                    data: data.data,
                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
    
    render_revenue_trend_chart(data) {
        const ctx = $(this.wrapper).find('#revenue-trend-chart')[0];
        if (!ctx) return;
        
        if (this.charts.revenue_trend) {
            this.charts.revenue_trend.destroy();
        }
        
        this.charts.revenue_trend = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: __('Revenue'),
                    data: data.revenue,
                    fill: false,
                    borderColor: 'rgba(75, 192, 192, 1)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
    
    render_bottleneck_analysis(bottlenecks) {
        const $container = $(this.wrapper).find('#bottleneck-analysis');
        $container.empty();
        
        if (bottlenecks.length === 0) {
            $container.append(`<div class="no-bottlenecks">${__('No bottlenecks identified')}</div>`);
            return;
        }
        
        bottlenecks.forEach(bottleneck => {
            const severityClass = `severity-${bottleneck.severity.toLowerCase()}`;
            $container.append(`
                <div class="bottleneck-item ${severityClass}">
                    <div class="bottleneck-header">
                        <span class="phase-name">${bottleneck.phase}</span>
                        <span class="severity-badge ${severityClass}">${bottleneck.severity}</span>
                    </div>
                    <div class="bottleneck-details">
                        <div>${__('Jobs in Phase')}: ${bottleneck.jobs_in_phase}</div>
                        <div>${__('Avg. Days')}: ${bottleneck.avg_days_in_phase.toFixed(1)}</div>
                        <div>${__('Overdue')}: ${bottleneck.overdue_jobs}</div>
                    </div>
                </div>
            `);
        });
    }
    
    render_customer_performance_chart(data) {
        const ctx = $(this.wrapper).find('#customer-performance-chart')[0];
        if (!ctx) return;
        
        if (this.charts.customer_performance) {
            this.charts.customer_performance.destroy();
        }
        
        this.charts.customer_performance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: __('Completion Rate (%)'),
                    data: data.completion_rates,
                    backgroundColor: 'rgba(255, 159, 64, 0.5)',
                    borderColor: 'rgba(255, 159, 64, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
    }
    
    show_job_detail(job_name) {
        frappe.call({
            method: 'api_next.api.dashboard.get_job_detail',
            args: { job_name: job_name },
            callback: (r) => {
                if (r.message && r.message.success) {
                    this.render_job_detail_modal(r.message.data);
                }
            }
        });
    }
    
    render_job_detail_modal(job_data) {
        const modal_html = this.get_job_detail_modal_html(job_data);
        
        const dialog = new frappe.ui.Dialog({
            title: __('Job Details: {0}', [job_data.basic_info.job_number]),
            size: 'large',
            fields: [{
                fieldtype: 'HTML',
                options: modal_html
            }]
        });
        
        dialog.show();
    }
    
    get_job_detail_modal_html(job) {
        return `
        <div class="job-detail-modal">
            <div class="row">
                <div class="col-md-6">
                    <h6>${__('Basic Information')}</h6>
                    <table class="table table-bordered">
                        <tr><td>${__('Job Number')}</td><td>${job.basic_info.job_number}</td></tr>
                        <tr><td>${__('Customer')}</td><td>${job.basic_info.customer_name}</td></tr>
                        <tr><td>${__('Project')}</td><td>${job.basic_info.project_name}</td></tr>
                        <tr><td>${__('Status')}</td><td><span class="status-badge">${job.basic_info.status}</span></td></tr>
                        <tr><td>${__('Priority')}</td><td><span class="priority-badge">${job.basic_info.priority}</span></td></tr>
                        <tr><td>${__('Current Phase')}</td><td><span class="phase-badge">${job.basic_info.workflow_state}</span></td></tr>
                        <tr><td>${__('Progress')}</td><td>${job.basic_info.progress}%</td></tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6>${__('Financial Information')}</h6>
                    <table class="table table-bordered">
                        <tr><td>${__('Material Cost')}</td><td>${format_currency(job.financial.total_material_cost)}</td></tr>
                        <tr><td>${__('Labor Cost')}</td><td>${format_currency(job.financial.total_labor_cost)}</td></tr>
                        <tr><td>${__('Labor Hours')}</td><td>${job.financial.total_labor_hours}</td></tr>
                        <tr><td><strong>${__('Total Value')}</strong></td><td><strong>${format_currency(job.financial.total_value)}</strong></td></tr>
                    </table>
                    
                    <h6>${__('Important Dates')}</h6>
                    <table class="table table-bordered">
                        <tr><td>${__('Start Date')}</td><td>${job.dates.start_date ? frappe.datetime.str_to_user(job.dates.start_date) : '-'}</td></tr>
                        <tr><td>${__('End Date')}</td><td>${job.dates.end_date ? frappe.datetime.str_to_user(job.dates.end_date) : '-'}</td></tr>
                        <tr><td>${__('Phase Start')}</td><td>${job.dates.phase_start_date ? frappe.datetime.str_to_user(job.dates.phase_start_date) : '-'}</td></tr>
                        <tr><td>${__('Phase Target')}</td><td>${job.dates.phase_target_date ? frappe.datetime.str_to_user(job.dates.phase_target_date) : '-'}</td></tr>
                    </table>
                </div>
            </div>
        </div>`;
    }
    
    setup_auto_refresh() {
        // Auto-refresh overview every 5 minutes
        this.refresh_interval = setInterval(() => {
            if (this.current_view === 'overview') {
                this.load_overview_data();
            }
        }, 5 * 60 * 1000);
    }
    
    refresh_dashboard() {
        // Clear charts
        Object.values(this.charts).forEach(chart => {
            if (chart && chart.destroy) {
                chart.destroy();
            }
        });
        this.charts = {};
        
        // Reload current view data
        switch (this.current_view) {
            case 'overview':
                this.load_overview_data();
                break;
            case 'kanban':
                this.load_kanban_data();
                break;
            case 'calendar':
                this.load_calendar_data();
                break;
            case 'analytics':
                this.load_analytics_data();
                break;
            case 'list':
                this.load_list_data();
                break;
        }
    }
    
    show_dashboard_settings() {
        // Implementation for dashboard settings
        frappe.msgprint(__('Dashboard settings coming soon'));
    }
}