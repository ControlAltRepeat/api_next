# Copyright (c) 2025, API Industrial Services Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Employee(Document):
    def validate(self):
        """Validate employee data"""
        if not self.employee_number:
            frappe.throw("Employee Number is required")
        
        # Auto-generate full name from first and last name BEFORE validation
        if self.first_name and self.last_name:
            self.employee_name = f"{self.first_name} {self.last_name}"
        
        if not self.employee_name:
            frappe.throw("Employee Name is required")
        
        # Ensure employee number is unique
        if frappe.db.exists("Employee", {"employee_number": self.employee_number, "name": ("!=", self.name)}):
            frappe.throw(f"Employee with number '{self.employee_number}' already exists")
    
    def before_save(self):
        """Execute before saving the document"""
        # Clean up employee data
        if self.employee_number:
            self.employee_number = self.employee_number.strip()
        if self.employee_name:
            self.employee_name = self.employee_name.strip()
        
        # Set is_active based on status
        if self.status == "Active":
            self.is_active = 1
        else:
            self.is_active = 0