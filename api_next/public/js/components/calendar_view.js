/**
 * Calendar View Component for Job Order Dashboard
 * Interactive calendar with job scheduling and deadline management
 */

class CalendarView {
    constructor(options) {
        this.container = options.container;
        this.currentDate = new Date();
        this.currentView = options.view || 'month'; // 'month', 'week', 'agenda'
        this.events = options.events || [];
        this.onEventClick = options.onEventClick || function() {};
        this.onDateClick = options.onDateClick || function() {};
        this.onEventDrop = options.onEventDrop || function() {};
        this.editable = options.editable !== false;
        
        this.init();
    }
    
    init() {
        this.render();
        this.bindEvents();
        this.loadEvents();
    }
    
    render() {
        const $container = $(this.container);
        $container.empty();
        
        const html = `
            <div class="calendar-view-wrapper">
                <div class="calendar-toolbar">
                    <div class="calendar-nav">
                        <button class="btn btn-outline-secondary calendar-prev">
                            <i class="fa fa-chevron-left"></i>
                        </button>
                        <h4 class="calendar-title">${this.getCalendarTitle()}</h4>
                        <button class="btn btn-outline-secondary calendar-next">
                            <i class="fa fa-chevron-right"></i>
                        </button>
                    </div>
                    
                    <div class="calendar-actions">
                        <button class="btn btn-primary calendar-today">${__('Today')}</button>
                        
                        <div class="btn-group view-switcher" role="group">
                            <button type="button" class="btn btn-outline-primary ${this.currentView === 'month' ? 'active' : ''}" 
                                    data-view="month">${__('Month')}</button>
                            <button type="button" class="btn btn-outline-primary ${this.currentView === 'week' ? 'active' : ''}" 
                                    data-view="week">${__('Week')}</button>
                            <button type="button" class="btn btn-outline-primary ${this.currentView === 'agenda' ? 'active' : ''}" 
                                    data-view="agenda">${__('Agenda')}</button>
                        </div>
                        
                        <div class="dropdown">
                            <button class="btn btn-outline-secondary dropdown-toggle" data-toggle="dropdown">
                                <i class="fa fa-filter"></i> ${__('Filter')}
                            </button>
                            <div class="dropdown-menu">
                                <a class="dropdown-item filter-option" href="#" data-filter="all">
                                    <i class="fa fa-check"></i> ${__('All Jobs')}
                                </a>
                                <div class="dropdown-divider"></div>
                                <a class="dropdown-item filter-option" href="#" data-filter="overdue">
                                    ${__('Overdue')}
                                </a>
                                <a class="dropdown-item filter-option" href="#" data-filter="due_soon">
                                    ${__('Due Soon')}
                                </a>
                                <a class="dropdown-item filter-option" href="#" data-filter="high_priority">
                                    ${__('High Priority')}
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="calendar-content">
                    ${this.renderCalendarContent()}
                </div>
                
                <div class="calendar-legend">
                    <div class="legend-item">
                        <span class="legend-color event-start"></span>
                        <span class="legend-label">${__('Job Start')}</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-color event-end"></span>
                        <span class="legend-label">${__('Job End')}</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-color event-phase"></span>
                        <span class="legend-label">${__('Phase Due')}</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-color overdue"></span>
                        <span class="legend-label">${__('Overdue')}</span>
                    </div>
                </div>
            </div>
        `;
        
        $container.html(html);
    }
    
    renderCalendarContent() {
        switch (this.currentView) {
            case 'month':
                return this.renderMonthView();
            case 'week':
                return this.renderWeekView();
            case 'agenda':
                return this.renderAgendaView();
            default:
                return this.renderMonthView();
        }
    }
    
    renderMonthView() {
        const year = this.currentDate.getFullYear();
        const month = this.currentDate.getMonth();
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const startDate = new Date(firstDay);
        startDate.setDate(startDate.getDate() - firstDay.getDay()); // Start from Sunday
        
        const html = `
            <div class="calendar-month">
                <div class="calendar-header">
                    <div class="calendar-day-header">${__('Sun')}</div>
                    <div class="calendar-day-header">${__('Mon')}</div>
                    <div class="calendar-day-header">${__('Tue')}</div>
                    <div class="calendar-day-header">${__('Wed')}</div>
                    <div class="calendar-day-header">${__('Thu')}</div>
                    <div class="calendar-day-header">${__('Fri')}</div>
                    <div class="calendar-day-header">${__('Sat')}</div>
                </div>
                <div class="calendar-body">
                    ${this.renderMonthDays(startDate, year, month)}
                </div>
            </div>
        `;
        
        return html;
    }
    
    renderMonthDays(startDate, year, month) {
        let html = '';
        const current = new Date(startDate);
        const today = new Date();
        
        for (let week = 0; week < 6; week++) {
            html += '<div class="calendar-week">';
            
            for (let day = 0; day < 7; day++) {
                const isCurrentMonth = current.getMonth() === month;
                const isToday = this.isSameDay(current, today);
                const dayEvents = this.getEventsForDate(current);
                
                const dayClasses = [
                    'calendar-day',
                    isCurrentMonth ? 'current-month' : 'other-month',
                    isToday ? 'today' : '',
                    dayEvents.length > 0 ? 'has-events' : ''
                ].filter(Boolean).join(' ');
                
                html += `
                    <div class="${dayClasses}" data-date="${this.formatDate(current)}">
                        <div class="day-number">${current.getDate()}</div>
                        <div class="day-events">
                            ${this.renderDayEvents(dayEvents, true)}
                        </div>
                    </div>
                `;
                
                current.setDate(current.getDate() + 1);
            }
            
            html += '</div>';
            
            // Stop if we've gone past the current month and completed a full week
            if (current.getMonth() !== month && day === 6) {
                break;
            }
        }
        
        return html;
    }
    
    renderWeekView() {
        const startOfWeek = this.getStartOfWeek(this.currentDate);
        const days = [];
        
        for (let i = 0; i < 7; i++) {
            const date = new Date(startOfWeek);
            date.setDate(date.getDate() + i);
            days.push(date);
        }
        
        const html = `
            <div class="calendar-week-view">
                <div class="week-header">
                    ${days.map(date => `
                        <div class="week-day-header ${this.isSameDay(date, new Date()) ? 'today' : ''}">
                            <div class="day-name">${date.toLocaleDateString('en-US', { weekday: 'short' })}</div>
                            <div class="day-number">${date.getDate()}</div>
                        </div>
                    `).join('')}
                </div>
                <div class="week-body">
                    ${days.map(date => `
                        <div class="week-day-column" data-date="${this.formatDate(date)}">
                            ${this.renderDayEvents(this.getEventsForDate(date), false)}
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        
        return html;
    }
    
    renderAgendaView() {
        const startDate = new Date(this.currentDate);
        startDate.setDate(1); // Start of month
        const endDate = new Date(this.currentDate);
        endDate.setMonth(endDate.getMonth() + 1, 0); // End of month
        
        const upcomingEvents = this.events.filter(event => {
            const eventDate = new Date(event.start);
            return eventDate >= startDate && eventDate <= endDate;
        }).sort((a, b) => new Date(a.start) - new Date(b.start));
        
        if (upcomingEvents.length === 0) {
            return `
                <div class="agenda-view">
                    <div class="no-events">
                        <i class="fa fa-calendar-o"></i>
                        <p>${__('No events scheduled for this period')}</p>
                    </div>
                </div>
            `;
        }
        
        let html = '<div class="agenda-view">';
        let currentDateGroup = null;
        
        upcomingEvents.forEach(event => {
            const eventDate = new Date(event.start);
            const dateStr = eventDate.toLocaleDateString();
            
            if (dateStr !== currentDateGroup) {
                if (currentDateGroup !== null) {
                    html += '</div>'; // Close previous date group
                }
                html += `
                    <div class="agenda-date-group">
                        <div class="agenda-date-header">
                            <h5>${this.formatDateHeader(eventDate)}</h5>
                            <span class="day-name">${eventDate.toLocaleDateString('en-US', { weekday: 'long' })}</span>
                        </div>
                        <div class="agenda-events">
                `;
                currentDateGroup = dateStr;
            }
            
            html += this.renderAgendaEvent(event);
        });
        
        html += '</div></div></div>'; // Close last date group and agenda view
        
        return html;
    }
    
    renderDayEvents(events, compact = true) {
        if (!events || events.length === 0) return '';
        
        const maxVisible = compact ? 3 : 10;
        const visibleEvents = events.slice(0, maxVisible);
        const hiddenCount = events.length - maxVisible;
        
        let html = visibleEvents.map(event => {
            const eventClass = `calendar-event ${event.className || ''} ${this.getEventTypeClass(event)}`;
            const title = compact ? this.truncateText(event.title, 20) : event.title;
            
            return `
                <div class="${eventClass}" data-event-id="${event.id}" title="${event.title}">
                    <span class="event-time">${this.formatEventTime(event)}</span>
                    <span class="event-title">${title}</span>
                    ${event.extendedProps && event.extendedProps.overdue ? 
                        '<i class="fa fa-exclamation-triangle overdue-icon"></i>' : ''}
                </div>
            `;
        }).join('');
        
        if (hiddenCount > 0) {
            html += `
                <div class="calendar-event more-events" title="${hiddenCount} ${__('more events')}">
                    +${hiddenCount} ${__('more')}
                </div>
            `;
        }
        
        return html;
    }
    
    renderAgendaEvent(event) {
        const eventClass = `agenda-event ${this.getEventTypeClass(event)}`;
        const props = event.extendedProps || {};
        
        return `
            <div class="${eventClass}" data-event-id="${event.id}">
                <div class="event-time">
                    ${this.formatEventTime(event)}
                </div>
                <div class="event-content">
                    <div class="event-title">${event.title}</div>
                    <div class="event-details">
                        ${props.customer ? `<span class="event-customer">${props.customer}</span>` : ''}
                        ${props.phase ? `<span class="event-phase">${props.phase}</span>` : ''}
                        ${props.priority ? `<span class="event-priority priority-${props.priority.toLowerCase()}">${props.priority}</span>` : ''}
                        ${props.overdue ? '<span class="event-overdue"><i class="fa fa-exclamation-triangle"></i> Overdue</span>' : ''}
                    </div>
                </div>
                <div class="event-actions">
                    <button class="btn btn-sm btn-outline-primary view-job-btn" data-job="${props.job}">
                        <i class="fa fa-eye"></i>
                    </button>
                </div>
            </div>
        `;
    }
    
    bindEvents() {
        const $container = $(this.container);
        
        // Navigation
        $container.on('click', '.calendar-prev', () => {
            this.navigateCalendar(-1);
        });
        
        $container.on('click', '.calendar-next', () => {
            this.navigateCalendar(1);
        });
        
        $container.on('click', '.calendar-today', () => {
            this.goToToday();
        });
        
        // View switching
        $container.on('click', '.view-switcher .btn', (e) => {
            const newView = $(e.currentTarget).data('view');
            if (newView !== this.currentView) {
                this.changeView(newView);
            }
        });
        
        // Date clicks
        $container.on('click', '.calendar-day', (e) => {
            if ($(e.target).closest('.calendar-event').length) return;
            
            const dateStr = $(e.currentTarget).data('date');
            const date = new Date(dateStr);
            this.onDateClick(date);
        });
        
        // Event clicks
        $container.on('click', '.calendar-event', (e) => {
            e.stopPropagation();
            const eventId = $(e.currentTarget).data('event-id');
            const event = this.events.find(e => e.id === eventId);
            if (event) {
                this.onEventClick(event);
            }
        });
        
        // Job view buttons
        $container.on('click', '.view-job-btn', (e) => {
            e.stopPropagation();
            const jobName = $(e.currentTarget).data('job');
            this.onEventClick({ extendedProps: { job: jobName } });
        });
        
        // Filter options
        $container.on('click', '.filter-option', (e) => {
            e.preventDefault();
            const filter = $(e.currentTarget).data('filter');
            this.applyFilter(filter);
            
            // Update active state
            $('.filter-option').removeClass('active');
            $(e.currentTarget).addClass('active');
        });
        
        // More events click
        $container.on('click', '.more-events', (e) => {
            e.stopPropagation();
            const $day = $(e.currentTarget).closest('.calendar-day');
            const dateStr = $day.data('date');
            this.showDayEventsModal(new Date(dateStr));
        });
    }
    
    navigateCalendar(direction) {
        const newDate = new Date(this.currentDate);
        
        switch (this.currentView) {
            case 'month':
                newDate.setMonth(newDate.getMonth() + direction);
                break;
            case 'week':
                newDate.setDate(newDate.getDate() + (direction * 7));
                break;
            case 'agenda':
                newDate.setMonth(newDate.getMonth() + direction);
                break;
        }
        
        this.currentDate = newDate;
        this.render();
        this.loadEvents();
    }
    
    goToToday() {
        this.currentDate = new Date();
        this.render();
        this.loadEvents();
    }
    
    changeView(newView) {
        this.currentView = newView;
        this.render();
    }
    
    loadEvents() {
        // Calculate date range based on current view
        let startDate, endDate;
        
        switch (this.currentView) {
            case 'month':
                const year = this.currentDate.getFullYear();
                const month = this.currentDate.getMonth();
                startDate = new Date(year, month, 1);
                startDate.setDate(startDate.getDate() - startDate.getDay());
                endDate = new Date(year, month + 1, 0);
                endDate.setDate(endDate.getDate() + (6 - endDate.getDay()));
                break;
            case 'week':
                startDate = this.getStartOfWeek(this.currentDate);
                endDate = new Date(startDate);
                endDate.setDate(endDate.getDate() + 6);
                break;
            case 'agenda':
                startDate = new Date(this.currentDate);
                startDate.setDate(1);
                endDate = new Date(this.currentDate);
                endDate.setMonth(endDate.getMonth() + 1, 0);
                break;
        }
        
        // Load events from API
        frappe.call({
            method: 'api_next.api.dashboard.get_calendar_events',
            args: {
                start_date: this.formatDate(startDate),
                end_date: this.formatDate(endDate),
                view_type: this.currentView
            },
            callback: (r) => {
                if (r.message && r.message.success) {
                    this.events = r.message.data;
                    this.refreshCalendarContent();
                }
            }
        });
    }
    
    refreshCalendarContent() {
        const $content = $(this.container).find('.calendar-content');
        $content.html(this.renderCalendarContent());
    }
    
    getCalendarTitle() {
        switch (this.currentView) {
            case 'month':
                return this.currentDate.toLocaleDateString('en-US', { 
                    month: 'long', 
                    year: 'numeric' 
                });
            case 'week':
                const startOfWeek = this.getStartOfWeek(this.currentDate);
                const endOfWeek = new Date(startOfWeek);
                endOfWeek.setDate(endOfWeek.getDate() + 6);
                
                if (startOfWeek.getMonth() === endOfWeek.getMonth()) {
                    return `${startOfWeek.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })} ${startOfWeek.getDate()} - ${endOfWeek.getDate()}`;
                } else {
                    return `${startOfWeek.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${endOfWeek.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`;
                }
            case 'agenda':
                return this.currentDate.toLocaleDateString('en-US', { 
                    month: 'long', 
                    year: 'numeric' 
                });
            default:
                return '';
        }
    }
    
    getEventsForDate(date) {
        const dateStr = this.formatDate(date);
        return this.events.filter(event => {
            const eventDate = this.formatDate(new Date(event.start));
            return eventDate === dateStr;
        });
    }
    
    getEventTypeClass(event) {
        const type = event.extendedProps?.type || 'default';
        const priority = event.extendedProps?.priority?.toLowerCase() || 'medium';
        
        return `event-${type} priority-${priority}`;
    }
    
    formatEventTime(event) {
        if (event.allDay) return '';
        
        const startTime = new Date(event.start);
        const endTime = event.end ? new Date(event.end) : null;
        
        let timeStr = startTime.toLocaleTimeString('en-US', { 
            hour: 'numeric', 
            minute: '2-digit',
            hour12: true 
        });
        
        if (endTime && !this.isSameTime(startTime, endTime)) {
            timeStr += ' - ' + endTime.toLocaleTimeString('en-US', { 
                hour: 'numeric', 
                minute: '2-digit',
                hour12: true 
            });
        }
        
        return timeStr;
    }
    
    formatDateHeader(date) {
        const today = new Date();
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        
        if (this.isSameDay(date, today)) {
            return __('Today');
        } else if (this.isSameDay(date, tomorrow)) {
            return __('Tomorrow');
        } else if (this.isSameDay(date, yesterday)) {
            return __('Yesterday');
        } else {
            return date.toLocaleDateString('en-US', { 
                month: 'long', 
                day: 'numeric',
                year: date.getFullYear() !== today.getFullYear() ? 'numeric' : undefined
            });
        }
    }
    
    applyFilter(filterType) {
        // This would filter events based on the selected criteria
        switch (filterType) {
            case 'all':
                // Show all events
                break;
            case 'overdue':
                // Show only overdue events
                break;
            case 'due_soon':
                // Show events due within next 3 days
                break;
            case 'high_priority':
                // Show only high priority events
                break;
        }
        
        this.loadEvents(); // Reload with filter
    }
    
    showDayEventsModal(date) {
        const events = this.getEventsForDate(date);
        const dateStr = date.toLocaleDateString('en-US', { 
            weekday: 'long', 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        });
        
        const modal = new frappe.ui.Dialog({
            title: __('Events for {0}', [dateStr]),
            fields: [{
                fieldtype: 'HTML',
                options: events.map(event => this.renderAgendaEvent(event)).join('')
            }]
        });
        
        modal.show();
    }
    
    // Utility methods
    formatDate(date) {
        return date.toISOString().split('T')[0];
    }
    
    isSameDay(date1, date2) {
        return date1.getDate() === date2.getDate() &&
               date1.getMonth() === date2.getMonth() &&
               date1.getFullYear() === date2.getFullYear();
    }
    
    isSameTime(date1, date2) {
        return date1.getTime() === date2.getTime();
    }
    
    getStartOfWeek(date) {
        const start = new Date(date);
        const day = start.getDay();
        const diff = start.getDate() - day;
        return new Date(start.setDate(diff));
    }
    
    truncateText(text, maxLength) {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength - 3) + '...';
    }
    
    // Public methods
    updateEvents(newEvents) {
        this.events = newEvents;
        this.refreshCalendarContent();
    }
    
    addEvent(event) {
        this.events.push(event);
        this.refreshCalendarContent();
    }
    
    removeEvent(eventId) {
        this.events = this.events.filter(e => e.id !== eventId);
        this.refreshCalendarContent();
    }
    
    goToDate(date) {
        this.currentDate = new Date(date);
        this.render();
        this.loadEvents();
    }
    
    destroy() {
        $(this.container).empty();
    }
}

// Export for use in other modules
window.CalendarView = CalendarView;