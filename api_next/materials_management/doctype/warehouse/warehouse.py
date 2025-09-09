# Copyright (c) 2025, API Industrial Services Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Warehouse(Document):
    def validate(self):
        """Validate warehouse data"""
        if not self.warehouse_name:
            frappe.throw("Warehouse Name is required")
        
        # Ensure warehouse name is unique
        if frappe.db.exists("Warehouse", {"warehouse_name": self.warehouse_name, "name": ("!=", self.name)}):
            frappe.throw(f"Warehouse with name '{self.warehouse_name}' already exists")
    
    def before_save(self):
        """Execute before saving the document"""
        # Clean up warehouse name
        if self.warehouse_name:
            self.warehouse_name = self.warehouse_name.strip()