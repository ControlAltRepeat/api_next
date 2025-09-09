/**
 * Kanban Board Component for Job Order Dashboard
 * Drag-and-drop workflow management
 */

class KanbanBoard {
    constructor(options) {
        this.container = options.container;
        this.columns = options.columns || [];
        this.data = options.data || {};
        this.onJobMove = options.onJobMove || function() {};
        this.onJobClick = options.onJobClick || function() {};
        this.allowDrag = options.allowDrag !== false;
        this.template = options.template || this.getDefaultTemplate();
        
        this.init();
    }
    
    init() {
        this.render();
        if (this.allowDrag) {
            this.setupDragDrop();
        }
        this.bindEvents();
    }
    
    getDefaultTemplate() {
        return {
            job: (job) => `
                <div class="kanban-job-card ${this.getJobClasses(job)}" 
                     data-job="${job.name}" draggable="${this.allowDrag}">
                    <div class="job-card-header">
                        <span class="job-number">${job.job_number}</span>
                        <span class="priority-badge ${DashboardUtils.getPriorityClass(job.priority)}">
                            ${job.priority || 'Medium'}
                        </span>
                    </div>
                    <div class="job-card-body">
                        <div class="customer-name">${job.customer_name}</div>
                        <div class="project-name" title="${job.project_name}">
                            ${this.truncateText(job.project_name, 40)}
                        </div>
                        <div class="job-value">${DashboardUtils.formatCurrency(job.total_value || 0)}</div>
                        ${job.phase_target_date ? 
                            `<div class="target-date ${job.is_overdue ? 'overdue' : ''}">
                                <i class="fa fa-clock-o"></i>
                                ${DashboardUtils.formatDate(job.phase_target_date)}
                            </div>` : ''
                        }
                    </div>
                    <div class="job-card-footer">
                        <div class="progress-wrapper">
                            <div class="progress progress-sm">
                                <div class="progress-bar" style="width: ${job.progress || 0}%"></div>
                            </div>
                            <span class="progress-label">${job.progress || 0}%</span>
                        </div>
                        <div class="job-actions">
                            <button class="btn btn-sm btn-outline-primary view-job-btn" 
                                    data-job="${job.name}" title="${__('View Job')}">
                                <i class="fa fa-eye"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `,
            column: (column, jobs) => `
                <div class="kanban-column" data-phase="${column.id}">
                    <div class="column-header">
                        <div class="column-title">
                            <h5>${column.title}</h5>
                            <div class="column-meta">
                                <span class="job-count">${jobs.length}</span>
                                <span class="column-value">${this.getColumnValue(jobs)}</span>
                            </div>
                        </div>
                        <div class="column-actions">
                            <button class="btn btn-sm btn-outline-secondary add-job-btn" 
                                    data-phase="${column.id}" title="${__('Add Job')}">
                                <i class="fa fa-plus"></i>
                            </button>
                            <div class="dropdown">
                                <button class="btn btn-sm btn-outline-secondary dropdown-toggle" 
                                        data-toggle="dropdown" title="${__('Column Options')}">
                                    <i class="fa fa-ellipsis-v"></i>
                                </button>
                                <div class="dropdown-menu">
                                    <a class="dropdown-item collapse-column" href="#" data-phase="${column.id}">
                                        <i class="fa fa-compress"></i> ${__('Collapse')}
                                    </a>
                                    <a class="dropdown-item filter-column" href="#" data-phase="${column.id}">
                                        <i class="fa fa-filter"></i> ${__('Filter')}
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="column-body" data-phase="${column.id}">
                        ${jobs.map(job => this.template.job(job)).join('')}
                    </div>
                    <div class="column-footer">
                        <div class="add-job-area" data-phase="${column.id}">
                            <button class="btn btn-sm btn-outline-primary add-job-btn" data-phase="${column.id}">
                                <i class="fa fa-plus"></i> ${__('Add Job')}
                            </button>
                        </div>
                    </div>
                </div>
            `
        };
    }
    
    render() {
        const $container = $(this.container);
        $container.empty();
        
        const $board = $('<div class="kanban-board-wrapper">');
        const $scrollContainer = $('<div class="kanban-scroll-container">');
        
        this.columns.forEach(column => {
            const jobs = this.data[column.id] ? this.data[column.id].jobs || [] : [];
            const $column = $(this.template.column(column, jobs));
            $scrollContainer.append($column);
        });
        
        $board.append($scrollContainer);
        $container.append($board);
        
        // Add scroll controls if needed
        this.addScrollControls($container);
    }
    
    addScrollControls($container) {
        const $scrollContainer = $container.find('.kanban-scroll-container');
        const scrollWidth = $scrollContainer[0].scrollWidth;
        const containerWidth = $scrollContainer.width();
        
        if (scrollWidth > containerWidth) {
            const $controls = $(`
                <div class="kanban-scroll-controls">
                    <button class="btn btn-sm btn-outline-secondary scroll-left">
                        <i class="fa fa-chevron-left"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-secondary scroll-right">
                        <i class="fa fa-chevron-right"></i>
                    </button>
                </div>
            `);
            
            $container.prepend($controls);
            
            // Bind scroll events
            $controls.find('.scroll-left').on('click', () => {
                $scrollContainer.animate({ scrollLeft: '-=200' }, 300);
            });
            
            $controls.find('.scroll-right').on('click', () => {
                $scrollContainer.animate({ scrollLeft: '+=200' }, 300);
            });
        }
    }
    
    setupDragDrop() {
        const $container = $(this.container);
        
        // Make job cards draggable
        $container.on('dragstart', '.kanban-job-card', (e) => {
            const jobName = $(e.currentTarget).data('job');
            const sourceColumn = $(e.currentTarget).closest('.kanban-column').data('phase');
            
            e.originalEvent.dataTransfer.setData('text/plain', JSON.stringify({
                job: jobName,
                sourceColumn: sourceColumn
            }));
            
            $(e.currentTarget).addClass('dragging');
        });
        
        $container.on('dragend', '.kanban-job-card', (e) => {
            $(e.currentTarget).removeClass('dragging');
        });
        
        // Setup drop zones
        $container.on('dragover', '.column-body', (e) => {
            e.preventDefault();
            $(e.currentTarget).addClass('drag-over');
        });
        
        $container.on('dragleave', '.column-body', (e) => {
            $(e.currentTarget).removeClass('drag-over');
        });
        
        $container.on('drop', '.column-body', (e) => {
            e.preventDefault();
            $(e.currentTarget).removeClass('drag-over');
            
            const dropData = JSON.parse(e.originalEvent.dataTransfer.getData('text/plain'));
            const targetColumn = $(e.currentTarget).data('phase');
            
            if (dropData.sourceColumn !== targetColumn) {
                this.moveJob(dropData.job, dropData.sourceColumn, targetColumn);
            }
        });
    }
    
    bindEvents() {
        const $container = $(this.container);
        
        // Job click events
        $container.on('click', '.kanban-job-card', (e) => {
            if ($(e.target).closest('.job-actions').length) return;
            
            const jobName = $(e.currentTarget).data('job');
            this.onJobClick(jobName);
        });
        
        // View job button
        $container.on('click', '.view-job-btn', (e) => {
            e.stopPropagation();
            const jobName = $(e.currentTarget).data('job');
            this.onJobClick(jobName);
        });
        
        // Add job button
        $container.on('click', '.add-job-btn', (e) => {
            e.preventDefault();
            const phase = $(e.currentTarget).data('phase');
            this.showAddJobModal(phase);
        });
        
        // Column actions
        $container.on('click', '.collapse-column', (e) => {
            e.preventDefault();
            const phase = $(e.currentTarget).data('phase');
            this.toggleColumn(phase);
        });
        
        $container.on('click', '.filter-column', (e) => {
            e.preventDefault();
            const phase = $(e.currentTarget).data('phase');
            this.showColumnFilter(phase);
        });
    }
    
    moveJob(jobName, fromColumn, toColumn) {
        // Find and remove job from source column
        let job = null;
        if (this.data[fromColumn] && this.data[fromColumn].jobs) {
            const jobIndex = this.data[fromColumn].jobs.findIndex(j => j.name === jobName);
            if (jobIndex >= 0) {
                job = this.data[fromColumn].jobs.splice(jobIndex, 1)[0];
                this.data[fromColumn].count--;
                this.data[fromColumn].total_value -= (job.total_value || 0);
            }
        }
        
        // Add job to target column
        if (job && this.data[toColumn]) {
            if (!this.data[toColumn].jobs) {
                this.data[toColumn].jobs = [];
            }
            this.data[toColumn].jobs.push(job);
            this.data[toColumn].count++;
            this.data[toColumn].total_value += (job.total_value || 0);
        }
        
        // Update UI
        this.render();
        
        // Notify parent component
        this.onJobMove(jobName, fromColumn, toColumn);
    }
    
    getJobClasses(job) {
        const classes = [];
        
        if (job.priority) {
            classes.push(DashboardUtils.getPriorityClass(job.priority));
        }
        
        if (job.is_overdue) {
            classes.push('overdue');
        }
        
        if (job.status === 'Completed') {
            classes.push('completed');
        }
        
        return classes.join(' ');
    }
    
    getColumnValue(jobs) {
        const totalValue = jobs.reduce((sum, job) => sum + (job.total_value || 0), 0);
        return DashboardUtils.formatCurrency(totalValue);
    }
    
    truncateText(text, maxLength) {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength - 3) + '...';
    }
    
    showAddJobModal(phase) {
        // This would show a modal to create a new job in the specified phase
        frappe.msgprint(`${__('Add new job to')} ${phase} ${__('phase')}`);
    }
    
    toggleColumn(phase) {
        const $column = $(this.container).find(`[data-phase="${phase}"]`);
        $column.toggleClass('collapsed');
        
        const $body = $column.find('.column-body');
        if ($column.hasClass('collapsed')) {
            $body.slideUp();
        } else {
            $body.slideDown();
        }
    }
    
    showColumnFilter(phase) {
        // This would show filtering options for the column
        frappe.msgprint(`${__('Filter')} ${phase} ${__('column')}`);
    }
    
    updateData(newData) {
        this.data = newData;
        this.render();
    }
    
    addJob(job, column) {
        if (!this.data[column]) {
            this.data[column] = { jobs: [], count: 0, total_value: 0 };
        }
        
        this.data[column].jobs.push(job);
        this.data[column].count++;
        this.data[column].total_value += (job.total_value || 0);
        
        this.render();
    }
    
    removeJob(jobName) {
        for (const columnId in this.data) {
            const column = this.data[columnId];
            if (column.jobs) {
                const jobIndex = column.jobs.findIndex(j => j.name === jobName);
                if (jobIndex >= 0) {
                    const job = column.jobs.splice(jobIndex, 1)[0];
                    column.count--;
                    column.total_value -= (job.total_value || 0);
                    this.render();
                    break;
                }
            }
        }
    }
    
    updateJob(jobName, updatedJob) {
        for (const columnId in this.data) {
            const column = this.data[columnId];
            if (column.jobs) {
                const jobIndex = column.jobs.findIndex(j => j.name === jobName);
                if (jobIndex >= 0) {
                    column.jobs[jobIndex] = { ...column.jobs[jobIndex], ...updatedJob };
                    this.render();
                    break;
                }
            }
        }
    }
    
    getJob(jobName) {
        for (const columnId in this.data) {
            const column = this.data[columnId];
            if (column.jobs) {
                const job = column.jobs.find(j => j.name === jobName);
                if (job) return job;
            }
        }
        return null;
    }
    
    getColumnStats(columnId) {
        const column = this.data[columnId];
        if (!column) return null;
        
        return {
            jobCount: column.jobs ? column.jobs.length : 0,
            totalValue: column.jobs ? column.jobs.reduce((sum, job) => sum + (job.total_value || 0), 0) : 0,
            overdueCount: column.jobs ? column.jobs.filter(job => job.is_overdue).length : 0,
            highPriorityCount: column.jobs ? column.jobs.filter(job => job.priority === 'High' || job.priority === 'Urgent').length : 0
        };
    }
    
    filterJobs(filterFn) {
        const filteredData = {};
        
        for (const columnId in this.data) {
            const column = this.data[columnId];
            filteredData[columnId] = {
                ...column,
                jobs: column.jobs ? column.jobs.filter(filterFn) : []
            };
            filteredData[columnId].count = filteredData[columnId].jobs.length;
            filteredData[columnId].total_value = filteredData[columnId].jobs.reduce(
                (sum, job) => sum + (job.total_value || 0), 0
            );
        }
        
        const currentData = this.data;
        this.data = filteredData;
        this.render();
        
        return currentData; // Return original data for restoring
    }
    
    restoreData(originalData) {
        this.data = originalData;
        this.render();
    }
    
    destroy() {
        $(this.container).empty();
    }
}

// Export for use in other modules
window.KanbanBoard = KanbanBoard;