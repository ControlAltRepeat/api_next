// Copyright (c) 2025, API Industrial Services and contributors
// For license information, please see license.txt

frappe.ui.form.on('API Settings', {
    refresh(frm) {
        // Add custom buttons for system administrators
        if (frappe.user.has_role('System Manager')) {
            frm.add_custom_button(__('Reset Job Counter'), function() {
                frappe.confirm(__('Are you sure you want to reset the job counter? This action cannot be undone.'), 
                    function() {
                        frappe.call({
                            method: 'api_next.api_next.doctype.api_settings.api_settings.reset_job_counter',
                            callback: function(r) {
                                if (r.message) {
                                    frappe.msgprint(r.message.message);
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                );
            }, __('Actions'));
            
            frm.add_custom_button(__('Test Job Number Generation'), function() {
                frappe.call({
                    method: 'api_next.api_next.doctype.api_settings.api_settings.get_next_job_number',
                    callback: function(r) {
                        if (r.message) {
                            frappe.msgprint(__('Next job number will be: {0}', [r.message]));
                        }
                    }
                });
            }, __('Actions'));
        }
        
        // Show current job counter status
        if (frm.doc.current_job_counter) {
            frm.dashboard.add_indicator(__('Current Job Counter: {0}', [frm.doc.current_job_counter]), 'blue');
        }
        
        // Show last reset date
        if (frm.doc.last_job_number_reset) {
            frm.dashboard.add_indicator(__('Last Reset: {0}', [frappe.datetime.str_to_user(frm.doc.last_job_number_reset)]), 'green');
        }
        
        // Set field descriptions
        frm.set_df_property('job_number_format', 'description', 
            __('YY-XXX format: 25-001, 25-002, etc.<br>JOB-YY-XXXXX format: JOB-25-00001, JOB-25-00002, etc.'));
    },
    
    job_number_format(frm) {
        // Show example when format changes
        let example = '';
        let year = new Date().getFullYear().toString().substr(-2);
        
        if (frm.doc.job_number_format === 'YY-XXX') {
            example = year + '-001, ' + year + '-002, etc.';
        } else if (frm.doc.job_number_format === 'JOB-YY-XXXXX') {
            example = 'JOB-' + year + '-00001, JOB-' + year + '-00002, etc.';
        }
        
        if (example) {
            frappe.msgprint(__('Example job numbers: {0}', [example]));
        }
    },
    
    reset_job_numbers_annually(frm) {
        if (frm.doc.reset_job_numbers_annually) {
            frm.set_df_property('last_job_number_reset', 'hidden', 0);
            frm.set_df_property('current_job_counter', 'hidden', 0);
        } else {
            frm.set_df_property('last_job_number_reset', 'hidden', 1);
            frm.set_df_property('current_job_counter', 'hidden', 1);
        }
    },
    
    auto_archive_completed_jobs(frm) {
        frm.toggle_reqd('archive_after_days', frm.doc.auto_archive_completed_jobs);
    },
    
    erpnext_integration_enabled(frm) {
        // Show/hide integration fields based on ERPNext integration setting
        frm.toggle_display('sync_customers_with_erpnext', frm.doc.erpnext_integration_enabled);
        frm.toggle_display('sync_items_with_erpnext', frm.doc.erpnext_integration_enabled);
        
        if (!frm.doc.erpnext_integration_enabled) {
            frm.set_value('sync_customers_with_erpnext', 0);
            frm.set_value('sync_items_with_erpnext', 0);
        }
    },
    
    validate(frm) {
        // Additional client-side validation
        if (frm.doc.default_labor_rate && frm.doc.default_labor_rate < 0) {
            frappe.msgprint(__('Default Labor Rate cannot be negative'));
            frappe.validated = false;
        }
        
        if (frm.doc.default_tax_rate && (frm.doc.default_tax_rate < 0 || frm.doc.default_tax_rate > 100)) {
            frappe.msgprint(__('Default Tax Rate must be between 0 and 100'));
            frappe.validated = false;
        }
        
        if (frm.doc.auto_archive_completed_jobs && (!frm.doc.archive_after_days || frm.doc.archive_after_days < 1)) {
            frappe.msgprint(__('Archive After Days must be at least 1 when Auto Archive is enabled'));
            frappe.validated = false;
        }
        
        if ((frm.doc.sync_customers_with_erpnext || frm.doc.sync_items_with_erpnext) && !frm.doc.erpnext_integration_enabled) {
            frappe.msgprint(__('ERPNext Integration must be enabled to sync customers or items'));
            frappe.validated = false;
        }
    }
});