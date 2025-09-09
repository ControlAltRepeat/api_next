# Copyright (c) 2024, API Industrial Services Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Item(Document):
    """Item DocType for materials management."""
    
    def validate(self):
        """Validate item data before saving."""
        self.validate_item_code()
        self.validate_standard_rate()
        
    def validate_item_code(self):
        """Ensure item code is properly formatted."""
        if not self.item_code:
            frappe.throw("Item Code is mandatory")
        
        # Remove leading/trailing spaces
        self.item_code = self.item_code.strip()
        
        if not self.item_code:
            frappe.throw("Item Code cannot be empty")
            
    def validate_standard_rate(self):
        """Validate standard rate is positive if provided."""
        if self.standard_rate and self.standard_rate < 0:
            frappe.throw("Standard Rate cannot be negative")
    
    def before_save(self):
        """Process data before saving."""
        # Auto-generate item name from code if not provided
        if not self.item_name and self.item_code:
            self.item_name = self.item_code
            
        # Set default unit of measure if not provided
        if not self.unit_of_measure:
            self.unit_of_measure = "Each"
    
    def after_insert(self):
        """Actions to perform after inserting new item."""
        frappe.msgprint(f"Item {self.item_code} has been created successfully.")