# Copyright (c) 2025, API Industrial Services Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime


class JobOrderLabor(Document):
    def validate(self):
        """Validate the labor entry and calculate amount."""
        self.calculate_amount()
        self.validate_dates()
        self.validate_hours()
    
    def calculate_amount(self):
        """Calculate amount based on actual hours and rate."""
        if self.hours_actual and self.rate:
            self.amount = self.hours_actual * self.rate
        elif self.hours_estimated and self.rate and not self.hours_actual:
            # Use estimated hours if actual hours not recorded yet
            self.amount = self.hours_estimated * self.rate
        else:
            self.amount = 0
    
    def validate_dates(self):
        """Validate start and end dates."""
        if self.start_date and self.end_date:
            if get_datetime(self.start_date) > get_datetime(self.end_date):
                frappe.throw("End Date cannot be before Start Date")
    
    def validate_hours(self):
        """Validate hours are not negative."""
        if self.hours_estimated and self.hours_estimated < 0:
            frappe.throw("Estimated hours cannot be negative")
        
        if self.hours_actual and self.hours_actual < 0:
            frappe.throw("Actual hours cannot be negative")
        
        # Warning if actual hours significantly exceed estimated hours
        if (self.hours_estimated and self.hours_actual and 
            self.hours_actual > (self.hours_estimated * 1.5)):
            frappe.msgprint(
                f"Actual hours ({self.hours_actual}) significantly exceed estimated hours ({self.hours_estimated}). Please verify.",
                title="Hours Variance",
                indicator="orange"
            )
    
    def before_save(self):
        """Pre-save operations."""
        # Fetch employee details if not already fetched
        if self.employee and not self.employee_name:
            employee = frappe.get_doc("Employee", self.employee)
            self.employee_name = employee.employee_name
        
        # Auto-update status based on dates and hours
        self.update_status_auto()
    
    def update_status_auto(self):
        """Auto-update status based on dates and completion."""
        if self.status == "Scheduled":
            # If work has started (actual hours logged), change to In Progress
            if self.hours_actual and self.hours_actual > 0:
                self.status = "In Progress"
            # If start date has passed, also change to In Progress
            elif self.start_date and get_datetime(self.start_date) <= now_datetime():
                self.status = "In Progress"
        
        elif self.status == "In Progress":
            # If end date has passed and actual hours equal or exceed estimated, mark completed
            if (self.end_date and get_datetime(self.end_date) <= now_datetime() and
                self.hours_actual and self.hours_estimated and
                self.hours_actual >= self.hours_estimated):
                self.status = "Completed"