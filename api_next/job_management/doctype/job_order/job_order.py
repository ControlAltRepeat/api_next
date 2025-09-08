# Copyright (c) 2025, API Next and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from datetime import datetime

class JobOrder(Document):
    def autoname(self):
        # Generate job number in format JOB-YY-XXXXX
        self.name = make_autoname("JOB-.YY.-.#####")
        self.job_number = self.name
    
    def validate(self):
        self.validate_dates()
        self.calculate_totals()
        self.update_phase_status()
    
    def validate_dates(self):
        if self.end_date and self.start_date:
            if self.end_date < self.start_date:
                frappe.throw("End Date cannot be before Start Date")
    
    def calculate_totals(self):
        # Calculate total material cost
        total_material = 0
        if self.material_requisitions:
            for item in self.material_requisitions:
                if item.total_cost:
                    total_material += item.total_cost
        self.total_material_cost = total_material
        
        # Calculate total labor hours and cost
        total_hours = 0
        total_labor_cost = 0
        if self.labor_entries:
            for entry in self.labor_entries:
                if entry.hours:
                    total_hours += entry.hours
                if entry.cost:
                    total_labor_cost += entry.cost
        self.total_labor_hours = total_hours
        self.total_labor_cost = total_labor_cost
    
    def update_phase_status(self):
        # Auto-update status based on phases
        if self.phases:
            all_completed = all(phase.status == "Completed" for phase in self.phases)
            any_in_progress = any(phase.status == "In Progress" for phase in self.phases)
            
            if all_completed:
                self.status = "Completed"
            elif any_in_progress:
                self.status = "In Progress"
    
    def on_submit(self):
        # Create material requisitions when job is confirmed
        self.create_material_requisitions()
    
    def create_material_requisitions(self):
        # Logic to create actual material requisition documents
        pass
    
    @frappe.whitelist()
    def update_status(self, new_status):
        self.status = new_status
        self.save()
        return {"status": "success", "message": f"Job status updated to {new_status}"}
