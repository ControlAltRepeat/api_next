// Copyright (c) 2024, API Next and contributors
// For license information, please see license.txt

frappe.listview_settings['Job Material Requisition'] = {
    add_fields: ['status', 'approval_status', 'priority', 'required_by', 'total_estimated_cost'],
    
    get_indicator: function(doc) {
        const status_colors = {
            'Draft': 'orange',
            'Pending Approval': 'blue', 
            'Approved': 'green',
            'Ordered': 'purple',
            'Partially Received': 'yellow',
            'Received': 'green',
            'Cancelled': 'red'
        };
        
        // Check for urgency
        if (doc.required_by) {
            const today = frappe.datetime.get_today();
            const days_diff = frappe.datetime.get_diff(doc.required_by, today);
            
            if (days_diff < 0) {
                return [__('Overdue'), 'red', 'status,=,Overdue'];
            } else if (days_diff <= 2 && doc.status !== 'Received' && doc.status !== 'Cancelled') {
                return [__('Due Soon'), 'orange', 'status,=,Due Soon'];
            }
        }
        
        return [__(doc.status), status_colors[doc.status] || 'gray', 'status,=,' + doc.status];
    },
    
    formatters: {
        priority: function(value) {
            const priority_colors = {
                'Low': 'text-muted',
                'Normal': '',
                'High': 'text-warning',
                'Urgent': 'text-danger font-weight-bold'
            };
            
            const css_class = priority_colors[value] || '';
            return `<span class="${css_class}">${__(value)}</span>`;
        },
        
        approval_status: function(value) {
            const approval_colors = {
                'Pending': 'indicator orange',
                'Approved': 'indicator green',
                'Rejected': 'indicator red'
            };
            
            return `<span class="${approval_colors[value] || ''}">${__(value)}</span>`;
        },
        
        required_by: function(value) {
            if (!value) return '';
            
            const today = frappe.datetime.get_today();
            const days_diff = frappe.datetime.get_diff(value, today);
            
            let css_class = '';
            if (days_diff < 0) {
                css_class = 'text-danger font-weight-bold';
            } else if (days_diff <= 2) {
                css_class = 'text-warning';
            }
            
            return `<span class="${css_class}">${frappe.datetime.str_to_user(value)}</span>`;
        },
        
        total_estimated_cost: function(value) {
            if (!value) return '';
            return format_currency(value, 'CAD');
        }
    },
    
    onload: function(listview) {
        // Add custom buttons
        add_custom_list_buttons(listview);
        
        // Set up bulk actions
        setup_bulk_actions(listview);
        
        // Add custom filters
        add_custom_filters(listview);
    },
    
    refresh: function(listview) {
        // Refresh indicators and formatting
        update_urgency_indicators(listview);
    }
};

function add_custom_list_buttons(listview) {
    // Bulk Approve button
    if (frappe.user_roles.includes('Materials Coordinator') || 
        frappe.user_roles.includes('Job Manager') ||
        frappe.user_roles.includes('System Manager')) {
        
        listview.page.add_action_item(__('Bulk Approve'), function() {
            bulk_approve_requisitions(listview);
        });
    }
    
    // Analytics button
    listview.page.add_action_item(__('Analytics'), function() {
        show_requisition_analytics();
    });
    
    // Export button
    listview.page.add_action_item(__('Export'), function() {
        export_requisitions(listview);
    });
}

function setup_bulk_actions(listview) {
    // Override default bulk actions
    listview.page.add_actions_menu_item(__('Bulk Approve Selected'), function() {
        const selected = listview.get_checked_items();
        if (selected.length === 0) {
            frappe.msgprint(__('Please select items to approve'));
            return;
        }
        
        bulk_approve_selected(selected);
    }, true);
    
    listview.page.add_actions_menu_item(__('Check Stock for Selected'), function() {
        const selected = listview.get_checked_items();
        if (selected.length === 0) {
            frappe.msgprint(__('Please select items to check'));
            return;
        }
        
        check_stock_for_selected(selected);
    }, true);
}

function add_custom_filters(listview) {
    // Add quick filters
    listview.page.add_field({
        fieldtype: 'Select',
        fieldname: 'priority_filter',
        label: __('Priority'),
        options: '\nLow\nNormal\nHigh\nUrgent',
        change: function() {
            const value = this.get_value();
            if (value) {
                listview.filter_area.add('Job Material Requisition', 'priority', '=', value);
            } else {
                listview.filter_area.remove('priority');
            }
        }
    });
    
    listview.page.add_field({
        fieldtype: 'Select', 
        fieldname: 'status_filter',
        label: __('Status'),
        options: '\nDraft\nPending Approval\nApproved\nOrdered\nPartially Received\nReceived\nCancelled',
        change: function() {
            const value = this.get_value();
            if (value) {
                listview.filter_area.add('Job Material Requisition', 'status', '=', value);
            } else {
                listview.filter_area.remove('status');
            }
        }
    });
    
    // Date range filter
    listview.page.add_field({
        fieldtype: 'Check',
        fieldname: 'overdue_filter',
        label: __('Overdue Only'),
        change: function() {
            const checked = this.get_value();
            if (checked) {
                listview.filter_area.add('Job Material Requisition', 'required_by', '<', frappe.datetime.get_today());
            } else {
                listview.filter_area.remove('required_by');
            }
        }
    });
}

function bulk_approve_requisitions(listview) {
    const dialog = new frappe.ui.Dialog({
        title: __('Bulk Approve Requisitions'),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'approval_info',
                options: '<p>This will approve all pending requisitions that you have permission to approve.</p>'
            },
            {
                fieldtype: 'Small Text',
                fieldname: 'approver_notes',
                label: __('Approver Notes'),
                description: __('Optional notes that will be added to all approved requisitions')
            }
        ],
        primary_action_label: __('Approve All Pending'),
        primary_action: (values) => {
            frappe.call({
                method: 'api_next.api.material_requisition.bulk_approve_requisitions',
                args: {
                    requisition_names: [], // Empty array means all pending
                    approver_notes: values.approver_notes
                },
                callback: (r) => {
                    if (r.message && r.message.results) {
                        show_bulk_approval_results(r.message.results);
                        listview.refresh();
                    }
                }
            });
            dialog.hide();
        }
    });
    
    dialog.show();
}

function bulk_approve_selected(selected_items) {
    const requisition_names = selected_items.map(item => item.name);
    
    const dialog = new frappe.ui.Dialog({
        title: __('Bulk Approve Selected'),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'selection_info',
                options: `<p>Approving ${selected_items.length} selected requisitions:</p>
                         <ul>${selected_items.map(item => `<li>${item.name}</li>`).join('')}</ul>`
            },
            {
                fieldtype: 'Small Text',
                fieldname: 'approver_notes',
                label: __('Approver Notes'),
                description: __('Optional notes for all approvals')
            }
        ],
        primary_action_label: __('Approve Selected'),
        primary_action: (values) => {
            frappe.call({
                method: 'api_next.api.material_requisition.bulk_approve_requisitions',
                args: {
                    requisition_names: requisition_names,
                    approver_notes: values.approver_notes
                },
                callback: (r) => {
                    if (r.message && r.message.results) {
                        show_bulk_approval_results(r.message.results);
                        cur_list.refresh();
                    }
                }
            });
            dialog.hide();
        }
    });
    
    dialog.show();
}

function show_bulk_approval_results(results) {
    const success_count = results.filter(r => r.status === 'success').length;
    const error_count = results.filter(r => r.status === 'error').length;
    const skipped_count = results.filter(r => r.status === 'skipped').length;
    
    let message = `<div class="row">
        <div class="col-md-4">
            <div class="alert alert-success">
                <strong>Approved:</strong> ${success_count}
            </div>
        </div>`;
    
    if (error_count > 0) {
        message += `<div class="col-md-4">
            <div class="alert alert-danger">
                <strong>Errors:</strong> ${error_count}
            </div>
        </div>`;
    }
    
    if (skipped_count > 0) {
        message += `<div class="col-md-4">
            <div class="alert alert-warning">
                <strong>Skipped:</strong> ${skipped_count}
            </div>
        </div>`;
    }
    
    message += '</div>';
    
    // Show detailed results
    if (error_count > 0 || skipped_count > 0) {
        message += '<h5>Details:</h5><ul>';
        results.forEach(result => {
            if (result.status !== 'success') {
                message += `<li><strong>${result.name}:</strong> ${result.message}</li>`;
            }
        });
        message += '</ul>';
    }
    
    frappe.msgprint({
        title: __('Bulk Approval Results'),
        message: message,
        wide: true
    });
}

function check_stock_for_selected(selected_items) {
    const requisition_names = selected_items.map(item => item.name);
    
    frappe.call({
        method: 'api_next.materials_management.utils.stock_check.check_stock_for_requisitions',
        args: {
            requisition_names: requisition_names
        },
        callback: (r) => {
            if (r.message) {
                show_stock_check_results(r.message);
            }
        }
    });
}

function show_stock_check_results(stock_data) {
    const html = `
        <table class="table table-bordered">
            <thead>
                <tr>
                    <th>Requisition</th>
                    <th>Item Code</th>
                    <th>Requested</th>
                    <th>Available</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                ${stock_data.map(item => `
                    <tr class="${item.sufficient ? 'text-success' : 'text-danger'}">
                        <td>${item.requisition}</td>
                        <td>${item.item_code}</td>
                        <td>${item.requested}</td>
                        <td>${item.available}</td>
                        <td>${item.sufficient ? 'Sufficient' : 'Insufficient'}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    frappe.msgprint({
        title: __('Stock Availability Check'),
        message: html,
        wide: true
    });
}

function show_requisition_analytics() {
    frappe.set_route('query-report', 'Material Requisition Analytics');
}

function export_requisitions(listview) {
    const filters = listview.filter_area.get();
    
    frappe.call({
        method: 'api_next.materials_management.utils.export.export_requisitions',
        args: {
            filters: filters,
            format: 'xlsx'
        },
        callback: (r) => {
            if (r.message && r.message.file_url) {
                window.open(r.message.file_url);
            }
        }
    });
}

function update_urgency_indicators(listview) {
    // Add visual indicators for urgent items
    setTimeout(() => {
        const rows = listview.$result.find('.list-row');
        rows.each(function() {
            const row = $(this);
            const required_by = row.find('[data-fieldname="required_by"]').text();
            const status = row.find('[data-fieldname="status"]').text();
            
            if (required_by && (status !== 'Received' && status !== 'Cancelled')) {
                const today = frappe.datetime.get_today();
                const days_diff = frappe.datetime.get_diff(required_by, today);
                
                if (days_diff < 0) {
                    row.addClass('list-row-danger');
                    row.find('.list-row-col:first').prepend('<i class="fa fa-exclamation-triangle text-danger" title="Overdue"></i> ');
                } else if (days_diff <= 2) {
                    row.addClass('list-row-warning');
                    row.find('.list-row-col:first').prepend('<i class="fa fa-clock-o text-warning" title="Due Soon"></i> ');
                }
            }
        });
    }, 100);
}