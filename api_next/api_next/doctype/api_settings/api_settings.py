# Copyright (c) 2025, API Industrial Services and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, today, get_datetime
from datetime import datetime


class APISettings(Document):
    """Singleton DocType for API_Next system-wide configuration."""
    
    def validate(self):
        """Validate configuration changes."""
        self.validate_job_number_settings()
        self.validate_default_values()
        self.validate_notification_settings()
        self.validate_archive_settings()
        self.validate_integration_settings()
    
    def validate_job_number_settings(self):
        """Validate job number configuration."""
        if self.reset_job_numbers_annually:
            current_year = datetime.now().strftime("%y")
            if not self.last_job_number_reset:
                # First time setup
                self.last_job_number_reset = today()
                self.current_job_counter = 0
            else:
                # Check if we need to reset for new year
                reset_year = get_datetime(self.last_job_number_reset).strftime("%y")
                if current_year != reset_year:
                    self.reset_job_counter_for_new_year()
    
    def validate_default_values(self):
        """Validate default values are reasonable."""
        if self.default_labor_rate and self.default_labor_rate < 0:
            frappe.throw(_("Default Labor Rate cannot be negative"))
        
        if self.default_markup_percentage and self.default_markup_percentage < 0:
            frappe.throw(_("Default Markup Percentage cannot be negative"))
        
        if self.default_tax_rate and (self.default_tax_rate < 0 or self.default_tax_rate > 100):
            frappe.throw(_("Default Tax Rate must be between 0 and 100"))
    
    def validate_notification_settings(self):
        """Validate notification configuration."""
        if self.escalation_hours and self.escalation_hours < 1:
            frappe.throw(_("Escalation Hours must be at least 1"))
    
    def validate_archive_settings(self):
        """Validate auto-archive configuration."""
        if self.auto_archive_completed_jobs:
            if not self.archive_after_days:
                frappe.throw(_("Archive After Days is required when Auto Archive is enabled"))
            if self.archive_after_days < 1:
                frappe.throw(_("Archive After Days must be at least 1"))
    
    def validate_integration_settings(self):
        """Validate integration configuration."""
        if (self.sync_customers_with_erpnext or self.sync_items_with_erpnext) and not self.erpnext_integration_enabled:
            frappe.throw(_("ERPNext Integration must be enabled to sync customers or items"))
    
    def reset_job_counter_for_new_year(self):
        """Reset job counter for new year."""
        self.current_job_counter = 0
        self.last_job_number_reset = today()
        frappe.msgprint(_("Job counter has been reset for the new year"))
    
    def get_next_job_number(self):
        """Generate the next job number based on current settings."""
        if self.reset_job_numbers_annually:
            current_year = datetime.now().strftime("%y")
            reset_year = get_datetime(self.last_job_number_reset).strftime("%y") if self.last_job_number_reset else None
            
            if current_year != reset_year:
                self.reset_job_counter_for_new_year()
        
        # Increment counter
        next_counter = (self.current_job_counter or 0) + 1
        
        # Generate job number based on format
        if self.job_number_format == "YY-XXX":
            year = datetime.now().strftime("%y")
            job_number = f"{year}-{next_counter:03d}"
        else:  # JOB-YY-XXXXX
            year = datetime.now().strftime("%y")
            job_number = f"JOB-{year}-{next_counter:05d}"
        
        # Update counter
        self.current_job_counter = next_counter
        self.save()
        
        return job_number
    
    @staticmethod
    def get_settings():
        """Get API Settings singleton instance."""
        if not frappe.db.exists("API Settings", "API Settings"):
            # Create default settings
            settings = frappe.new_doc("API Settings")
            settings.save()
        else:
            settings = frappe.get_doc("API Settings", "API Settings")
        
        return settings
    
    def get_default_job_priority(self):
        """Get default job priority."""
        return self.default_job_priority or "Normal"
    
    def get_default_labor_rate(self):
        """Get default labor rate."""
        return self.default_labor_rate or 0
    
    def get_default_markup_percentage(self):
        """Get default markup percentage."""
        return self.default_markup_percentage or 0
    
    def get_default_tax_rate(self):
        """Get default tax rate."""
        return self.default_tax_rate or 0
    
    def should_notify_via_email(self):
        """Check if email notifications are enabled."""
        return self.enable_email_notifications
    
    def should_notify_via_sms(self):
        """Check if SMS notifications are enabled."""
        return self.enable_sms_notifications
    
    def get_digest_time(self):
        """Get notification digest time."""
        return self.notification_digest_time
    
    def get_escalation_hours(self):
        """Get escalation hours."""
        return self.escalation_hours or 24
    
    def should_auto_archive_jobs(self):
        """Check if jobs should be auto-archived."""
        return self.auto_archive_completed_jobs
    
    def get_archive_after_days(self):
        """Get number of days after which to archive jobs."""
        return self.archive_after_days or 30
    
    def is_audit_trail_enabled(self):
        """Check if audit trail is enabled."""
        return self.enable_audit_trail
    
    def get_approval_threshold(self):
        """Get threshold above which estimates require approval."""
        return self.require_approval_for_estimates_above or 0
    
    def is_erpnext_integration_enabled(self):
        """Check if ERPNext integration is enabled."""
        return self.erpnext_integration_enabled
    
    def should_sync_customers(self):
        """Check if customers should be synced with ERPNext."""
        return self.sync_customers_with_erpnext and self.erpnext_integration_enabled
    
    def should_sync_items(self):
        """Check if items should be synced with ERPNext."""
        return self.sync_items_with_erpnext and self.erpnext_integration_enabled
    
    def get_accounting_dimension(self):
        """Get accounting dimension for financial tracking."""
        return self.accounting_dimension


@frappe.whitelist()
def get_next_job_number():
    """API method to get the next job number."""
    settings = APISettings.get_settings()
    return settings.get_next_job_number()


@frappe.whitelist()
def get_api_settings():
    """API method to get API settings."""
    return APISettings.get_settings()


@frappe.whitelist()
def reset_job_counter():
    """API method to manually reset job counter (System Manager only)."""
    if not frappe.has_permission("API Settings", "write"):
        frappe.throw(_("Insufficient permissions"))
    
    settings = APISettings.get_settings()
    settings.reset_job_counter_for_new_year()
    settings.save()
    
    return {"message": _("Job counter has been reset")}