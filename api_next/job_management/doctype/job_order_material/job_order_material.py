# Copyright (c) 2025, API Industrial Services Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class JobOrderMaterial(Document):
    def validate(self):
        """Validate the material entry and calculate amount."""
        self.calculate_amount()
        self.validate_delivery_date()
    
    def calculate_amount(self):
        """Calculate amount based on quantity and rate."""
        if self.quantity and self.rate:
            self.amount = self.quantity * self.rate
        else:
            self.amount = 0
    
    def validate_delivery_date(self):
        """Validate delivery date is not in the past for new records."""
        if self.delivery_date and not self.is_new():
            from datetime import datetime
            from frappe.utils import getdate, nowdate
            
            if getdate(self.delivery_date) < getdate(nowdate()):
                frappe.msgprint(
                    "Delivery date is in the past. Please verify if this is correct.",
                    title="Past Delivery Date",
                    indicator="orange"
                )
    
    def before_save(self):
        """Pre-save operations."""
        # Fetch item details if not already fetched
        if self.item_code and not self.item_name:
            item = frappe.get_doc("Item", self.item_code)
            self.item_name = item.item_name
            if not self.description:
                self.description = item.description
            if not self.unit:
                self.unit = item.stock_uom