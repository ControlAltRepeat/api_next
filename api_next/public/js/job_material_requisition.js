// Copyright (c) 2024, API Next and contributors
// For license information, please see license.txt

frappe.ui.form.on('Job Material Requisition', {
    refresh(frm) {
        // Set up custom buttons and actions
        setup_custom_buttons(frm);
        
        // Apply conditional formatting
        apply_conditional_formatting(frm);
        
        // Set up real-time updates
        setup_realtime_updates(frm);
        
        // Auto-fetch job order details
        if (frm.doc.job_order && !frm.doc.warehouse) {
            fetch_job_order_details(frm);
        }
    },
    
    job_order(frm) {
        if (frm.doc.job_order) {
            fetch_job_order_details(frm);
            
            // Option to populate items from job order
            if (!frm.doc.items || frm.doc.items.length === 0) {
                show_populate_items_dialog(frm);
            }
        }
    },
    
    priority(frm) {
        apply_priority_formatting(frm);
    },
    
    required_by(frm) {
        check_urgency(frm);
    },
    
    approval_status(frm) {
        apply_conditional_formatting(frm);
    },
    
    before_save(frm) {
        // Validate before save
        validate_items(frm);
        calculate_totals(frm);
    }
});

frappe.ui.form.on('Job Material Requisition Item', {
    item_code(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.item_code) {
            fetch_item_details(frm, row);
        }
    },
    
    quantity_requested(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        calculate_item_cost(frm, row);
        calculate_totals(frm);
    },
    
    quantity_approved(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        validate_approved_quantity(frm, row);
    },
    
    warehouse(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.item_code && row.warehouse) {
            check_stock_availability(frm, row);
        }
    },
    
    items_remove(frm) {
        calculate_totals(frm);
    }
});

function setup_custom_buttons(frm) {
    // Clear existing custom buttons
    frm.clear_custom_buttons();
    
    if (frm.doc.docstatus === 0) {
        // Draft state buttons
        if (frm.doc.approval_status === 'Pending' && can_approve(frm)) {
            frm.add_custom_button(__('Approve'), () => {
                approve_requisition(frm);
            }, __('Actions')).addClass('btn-success');
            
            frm.add_custom_button(__('Reject'), () => {
                reject_requisition(frm);
            }, __('Actions')).addClass('btn-danger');
        }
        
        if (frm.doc.job_order) {
            frm.add_custom_button(__('Fetch Job Materials'), () => {
                populate_from_job_order(frm);
            }, __('Get Items From'));
        }
        
        frm.add_custom_button(__('Check Stock Availability'), () => {
            check_all_stock_availability(frm);
        }, __('Tools'));
    }
    
    if (frm.doc.docstatus === 1) {
        // Submitted state buttons
        if (frm.doc.approval_status === 'Approved' && !frm.doc.material_request) {
            frm.add_custom_button(__('Create Material Request'), () => {
                create_material_request(frm);
            }).addClass('btn-primary');
        }
        
        if (frm.doc.material_request) {
            frm.add_custom_button(__('View Material Request'), () => {
                frappe.set_route('Form', 'Material Request', frm.doc.material_request);
            });
            
            frm.add_custom_button(__('Update Fulfillment'), () => {
                update_fulfillment_status(frm);
            }, __('Actions'));
        }
        
        frm.add_custom_button(__('Print Requisition'), () => {
            print_requisition(frm);
        }, __('Print'));
    }
}

function apply_conditional_formatting(frm) {
    // Status-based formatting
    if (frm.doc.status) {
        const status_colors = {
            'Draft': 'orange',
            'Pending Approval': 'blue',
            'Approved': 'green',
            'Ordered': 'purple',
            'Partially Received': 'yellow',
            'Received': 'green',
            'Cancelled': 'red'
        };
        
        frm.dashboard.set_headline_alert(
            `Status: ${frm.doc.status}`,
            status_colors[frm.doc.status] || 'gray'
        );
    }
    
    // Approval status formatting
    if (frm.doc.approval_status === 'Rejected') {
        frm.dashboard.set_headline_alert(
            `Rejected: ${frm.doc.rejection_reason || 'No reason provided'}`,
            'red'
        );
    }
    
    // Priority-based formatting
    apply_priority_formatting(frm);
    
    // Urgency check
    check_urgency(frm);
}

function apply_priority_formatting(frm) {
    if (frm.doc.priority === 'Urgent') {
        frm.dashboard.add_indicator(__('URGENT PRIORITY'), 'red');
    } else if (frm.doc.priority === 'High') {
        frm.dashboard.add_indicator(__('High Priority'), 'orange');
    }
}

function check_urgency(frm) {
    if (frm.doc.required_by) {
        const today = frappe.datetime.get_today();
        const required_date = frm.doc.required_by;
        const days_diff = frappe.datetime.get_diff(required_date, today);
        
        if (days_diff < 0) {
            frm.dashboard.add_indicator(__(`Overdue by ${Math.abs(days_diff)} days`), 'red');
        } else if (days_diff <= 2) {
            frm.dashboard.add_indicator(__(`Due in ${days_diff} days`), 'orange');
        }
    }
}

function setup_realtime_updates(frm) {
    if (frm.doc.name && frm.doc.material_request) {
        // Listen for Material Request updates
        frappe.realtime.on('material_request_update', (data) => {
            if (data.requisition_name === frm.doc.name) {
                frm.reload_doc();
            }
        });
    }
}

function fetch_job_order_details(frm) {
    if (!frm.doc.job_order) return;
    
    frappe.call({
        method: 'frappe.client.get',
        args: {
            doctype: 'Job Order',
            name: frm.doc.job_order
        },
        callback: (r) => {
            if (r.message) {
                const job_order = r.message;
                
                // Set defaults from job order
                if (!frm.doc.warehouse && job_order.warehouse) {
                    frm.set_value('warehouse', job_order.warehouse);
                }
                
                if (!frm.doc.project && job_order.project) {
                    frm.set_value('project', job_order.project);
                }
                
                if (!frm.doc.required_by && job_order.scheduled_end_date) {
                    frm.set_value('required_by', job_order.scheduled_end_date);
                }
                
                // Show job order info
                frm.dashboard.add_comment(
                    `Job Order: ${job_order.title} | Customer: ${job_order.customer || 'Not set'}`,
                    'blue'
                );
            }
        }
    });
}

function show_populate_items_dialog(frm) {
    frappe.confirm(
        __('Would you like to populate items from the Job Order materials?'),
        () => {
            populate_from_job_order(frm);
        }
    );
}

function populate_from_job_order(frm) {
    if (!frm.doc.job_order) {
        frappe.msgprint(__('Please select a Job Order first'));
        return;
    }
    
    frappe.call({
        method: 'frappe.client.get',
        args: {
            doctype: 'Job Order',
            name: frm.doc.job_order
        },
        callback: (r) => {
            if (r.message && r.message.materials) {
                // Clear existing items
                frm.clear_table('items');
                
                // Add items from job order
                r.message.materials.forEach(material => {
                    const item = frm.add_child('items');
                    item.item_code = material.item_code;
                    item.quantity_requested = material.quantity;
                    item.warehouse = material.warehouse || frm.doc.warehouse;
                    item.notes = material.notes || '';
                });
                
                frm.refresh_field('items');
                
                // Calculate totals
                calculate_totals(frm);
                
                frappe.msgprint(__('Items populated from Job Order'));
            } else {
                frappe.msgprint(__('No materials found in the Job Order'));
            }
        }
    });
}

function fetch_item_details(frm, row) {
    if (!row.item_code) return;
    
    frappe.call({
        method: 'api_next.materials_management.doctype.job_material_requisition_item.job_material_requisition_item.get_item_details',
        args: {
            item_code: row.item_code,
            warehouse: row.warehouse || frm.doc.warehouse
        },
        callback: (r) => {
            if (r.message) {
                const item_details = r.message;
                
                // Update row with item details
                frappe.model.set_value(row.doctype, row.name, 'item_name', item_details.item_name);
                frappe.model.set_value(row.doctype, row.name, 'description', item_details.description);
                frappe.model.set_value(row.doctype, row.name, 'unit', item_details.stock_uom);
                
                if (item_details.available_stock !== undefined) {
                    show_stock_info(row, item_details.available_stock);
                }
                
                // Calculate estimated cost
                calculate_item_cost(frm, row, item_details.last_purchase_rate);
            }
        }
    });
}

function calculate_item_cost(frm, row, rate) {
    if (row.quantity_requested && rate) {
        const estimated_cost = flt(row.quantity_requested) * flt(rate);
        frappe.model.set_value(row.doctype, row.name, 'estimated_cost', estimated_cost);
    }
}

function calculate_totals(frm) {
    let total_cost = 0;
    
    (frm.doc.items || []).forEach(item => {
        if (item.estimated_cost) {
            total_cost += flt(item.estimated_cost);
        }
    });
    
    frm.set_value('total_estimated_cost', total_cost);
}

function validate_items(frm) {
    if (!frm.doc.items || frm.doc.items.length === 0) {
        frappe.throw(__('Please add at least one item to the requisition'));
    }
    
    frm.doc.items.forEach((item, idx) => {
        if (!item.item_code) {
            frappe.throw(__(`Row ${idx + 1}: Item Code is required`));
        }
        
        if (!item.quantity_requested || item.quantity_requested <= 0) {
            frappe.throw(__(`Row ${idx + 1}: Quantity must be greater than 0`));
        }
    });
}

function validate_approved_quantity(frm, row) {
    if (row.quantity_approved && row.quantity_requested) {
        if (flt(row.quantity_approved) > flt(row.quantity_requested)) {
            frappe.msgprint(__('Approved quantity cannot be greater than requested quantity'));
            frappe.model.set_value(row.doctype, row.name, 'quantity_approved', row.quantity_requested);
        }
    }
}

function check_stock_availability(frm, row) {
    if (!row.item_code || !row.warehouse) return;
    
    frappe.call({
        method: 'api_next.materials_management.doctype.job_material_requisition_item.job_material_requisition_item.validate_item_availability',
        args: {
            item_code: row.item_code,
            quantity: row.quantity_requested,
            warehouse: row.warehouse
        },
        callback: (r) => {
            if (r.message) {
                show_stock_info(row, r.message.available_qty, r.message.available);
            }
        }
    });
}

function check_all_stock_availability(frm) {
    if (!frm.doc.items || frm.doc.items.length === 0) {
        frappe.msgprint(__('No items to check'));
        return;
    }
    
    let stock_report = [];
    let pending_checks = 0;
    
    frm.doc.items.forEach(item => {
        if (item.item_code && item.warehouse) {
            pending_checks++;
            
            frappe.call({
                method: 'api_next.materials_management.doctype.job_material_requisition_item.job_material_requisition_item.validate_item_availability',
                args: {
                    item_code: item.item_code,
                    quantity: item.quantity_requested,
                    warehouse: item.warehouse
                },
                callback: (r) => {
                    pending_checks--;
                    
                    if (r.message) {
                        stock_report.push({
                            item: item.item_code,
                            requested: item.quantity_requested,
                            available: r.message.available_qty,
                            sufficient: r.message.available
                        });
                    }
                    
                    if (pending_checks === 0) {
                        show_stock_availability_dialog(stock_report);
                    }
                }
            });
        }
    });
    
    if (pending_checks === 0) {
        frappe.msgprint(__('No items with warehouse specified'));
    }
}

function show_stock_info(row, available_qty, is_sufficient) {
    const color = is_sufficient ? 'green' : 'red';
    const message = `Available: ${available_qty}`;
    
    // You could add a visual indicator here
    console.log(`${row.item_code}: ${message} (${is_sufficient ? 'Sufficient' : 'Insufficient'})`);
}

function show_stock_availability_dialog(stock_report) {
    const html = `
        <table class="table table-bordered">
            <thead>
                <tr>
                    <th>Item Code</th>
                    <th>Requested</th>
                    <th>Available</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                ${stock_report.map(item => `
                    <tr class="${item.sufficient ? 'text-success' : 'text-danger'}">
                        <td>${item.item}</td>
                        <td>${item.requested}</td>
                        <td>${item.available}</td>
                        <td>${item.sufficient ? 'Sufficient' : 'Insufficient'}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    frappe.msgprint({
        title: __('Stock Availability Report'),
        message: html,
        wide: true
    });
}

function approve_requisition(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __('Approve Requisition'),
        fields: [
            {
                fieldtype: 'Small Text',
                fieldname: 'approver_notes',
                label: __('Approver Notes'),
                description: __('Optional notes for the approval')
            }
        ],
        primary_action_label: __('Approve'),
        primary_action: (values) => {
            frappe.call({
                method: 'approve_requisition',
                doc: frm.doc,
                args: {
                    approver_notes: values.approver_notes
                },
                callback: (r) => {
                    if (r.message && r.message.status === 'success') {
                        frappe.msgprint(r.message.message);
                        frm.reload_doc();
                    }
                }
            });
            dialog.hide();
        }
    });
    
    dialog.show();
}

function reject_requisition(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __('Reject Requisition'),
        fields: [
            {
                fieldtype: 'Small Text',
                fieldname: 'rejection_reason',
                label: __('Rejection Reason'),
                reqd: 1,
                description: __('Please provide a reason for rejection')
            }
        ],
        primary_action_label: __('Reject'),
        primary_action: (values) => {
            frappe.call({
                method: 'reject_requisition',
                doc: frm.doc,
                args: {
                    rejection_reason: values.rejection_reason
                },
                callback: (r) => {
                    if (r.message && r.message.status === 'success') {
                        frappe.msgprint(r.message.message);
                        frm.reload_doc();
                    }
                }
            });
            dialog.hide();
        }
    });
    
    dialog.show();
}

function create_material_request(frm) {
    frappe.call({
        method: 'api_next.api.material_requisition.sync_with_erpnext',
        args: {
            requisition_name: frm.doc.name
        },
        callback: (r) => {
            if (r.message && r.message.status === 'success') {
                frappe.msgprint(r.message.message);
                frm.reload_doc();
            }
        }
    });
}

function update_fulfillment_status(frm) {
    frappe.call({
        method: 'update_fulfillment_status',
        doc: frm.doc,
        callback: (r) => {
            frappe.msgprint(__('Fulfillment status updated'));
            frm.reload_doc();
        }
    });
}

function print_requisition(frm) {
    // Custom print functionality
    frappe.utils.print(
        frm.doc.doctype,
        frm.doc.name,
        __('Material Requisition')
    );
}

function can_approve(frm) {
    // Check if current user can approve this requisition
    return frappe.user_roles.includes('Materials Coordinator') ||
           frappe.user_roles.includes('Job Manager') ||
           frappe.user_roles.includes('System Manager');
}