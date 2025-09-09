# Copyright (c) 2025, API Next and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import now_datetime, nowdate
from datetime import datetime
from api_next.workflows.job_order_workflow import JobOrderWorkflow
from api_next.workflows.business_rules_engine import BusinessRulesEngine

class JobOrder(Document):
    def autoname(self):
        # Generate job number in format JOB-YY-XXXXX
        self.name = make_autoname("JOB-.YY.-.#####")
        self.job_number = self.name
    
    def validate(self):
        self.validate_dates()
        self.calculate_totals()
        self.update_phase_status()
        self.validate_workflow_transition()
        self.apply_business_rules()
    
    def validate_dates(self):
        if self.end_date and self.start_date:
            if self.end_date < self.start_date:
                frappe.throw("End Date cannot be before Start Date")
    
    def calculate_totals(self):
        # Calculate total material cost
        total_material = 0
        if self.material_requisitions:
            for item in self.material_requisitions:
                if item.amount:
                    total_material += item.amount
        self.total_material_cost = total_material
        
        # Calculate total labor hours and cost
        total_hours = 0
        total_labor_cost = 0
        if self.labor_entries:
            for entry in self.labor_entries:
                if entry.hours_actual:
                    total_hours += entry.hours_actual
                elif entry.hours_estimated:
                    # Use estimated hours if actual not recorded yet
                    total_hours += entry.hours_estimated
                if entry.amount:
                    total_labor_cost += entry.amount
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
    
    def on_update_after_submit(self):
        """Recalculate totals when child tables are modified after submit."""
        self.calculate_totals()
        self.update_workflow_timestamps()
    
    @frappe.whitelist()
    def update_status(self, new_status):
        self.status = new_status
        self.save()
        return {"status": "success", "message": f"Job status updated to {new_status}"}
    
    @frappe.whitelist()
    def recalculate_totals(self):
        """Manually recalculate all totals - useful for API calls."""
        self.calculate_totals()
        self.save()
        return {
            "total_material_cost": self.total_material_cost,
            "total_labor_hours": self.total_labor_hours,
            "total_labor_cost": self.total_labor_cost
        }
    
    def validate_workflow_transition(self):
        """Validate workflow state transitions."""
        if not hasattr(self, '_original_workflow_state'):
            return
        
        old_state = self._original_workflow_state
        new_state = self.workflow_state
        
        if old_state and old_state != new_state:
            validation = JobOrderWorkflow.validate_transition(self, old_state, new_state)
            if not validation["valid"]:
                frappe.throw(validation["message"])
    
    def apply_business_rules(self):
        """Apply business rules based on current state and data."""
        try:
            rules_engine = BusinessRulesEngine()
            context = {
                "doc": self,
                "customer_name": self.customer_name,
                "project_name": self.project_name,
                "job_type": self.job_type,
                "priority": self.priority,
                "total_cost": (self.total_material_cost or 0) + (self.total_labor_cost or 0),
                "total_material_cost": self.total_material_cost or 0,
                "total_labor_cost": self.total_labor_cost or 0,
                "start_date": self.start_date,
                "end_date": self.end_date,
                "status": self.status,
                "workflow_state": self.workflow_state,
                "has_materials": bool(self.material_requisitions),
                "risk_level": self.get("risk_level", "Low"),
                "scheduled_weekend": self._is_scheduled_weekend()
            }
            
            results = rules_engine.evaluate(context)
            
            # Handle rule results
            for action in results.get("actions_triggered", []):
                self._handle_rule_action(action)
                
        except Exception as e:
            frappe.log_error(f"Business rules application error: {str(e)}")
    
    def _is_scheduled_weekend(self):
        """Check if job is scheduled on weekend."""
        if not self.start_date:
            return False
        
        import calendar
        weekday = calendar.weekday(self.start_date.year, self.start_date.month, self.start_date.day)
        return weekday >= 5  # Saturday = 5, Sunday = 6
    
    def _handle_rule_action(self, action):
        """Handle business rule action results."""
        if action.startswith("approval_required:"):
            role = action.split(":")[1]
            self._create_approval_request(role)
        elif action.startswith("priority_set:"):
            level = action.split(":")[1]
            if level == "high" and self.priority != "Urgent":
                self.priority = "High"
        elif action == "quality_inspection_required":
            self._flag_quality_inspection_required()
    
    def _create_approval_request(self, role):
        """Create approval request for specified role."""
        # Placeholder for approval request creation
        frappe.msgprint(f"Approval required from {role} for this job order")
    
    def _flag_quality_inspection_required(self):
        """Flag that quality inspection is required."""
        # Placeholder for quality inspection flagging
        frappe.msgprint("Quality inspection required for this job")
    
    def update_workflow_timestamps(self):
        """Update phase start date when workflow state changes."""
        if not hasattr(self, '_original_workflow_state'):
            return
            
        old_state = self._original_workflow_state
        new_state = self.workflow_state
        
        if old_state != new_state:
            self.phase_start_date = now_datetime()
    
    def before_save(self):
        """Store original workflow state for comparison."""
        if not self.is_new():
            original_doc = frappe.get_doc(self.doctype, self.name)
            self._original_workflow_state = original_doc.workflow_state
        else:
            self._original_workflow_state = None
    
    @frappe.whitelist()
    def transition_workflow(self, new_state, comment=None):
        """API method to transition workflow state."""
        try:
            current_state = self.workflow_state or "Submission"
            
            # Execute workflow transition
            result = JobOrderWorkflow.execute_transition(self, new_state, comment=comment)
            
            if result["success"]:
                # Reload the document to get updated state
                self.reload()
                return {
                    "status": "success",
                    "message": result["message"],
                    "new_state": result["new_state"],
                    "timestamp": result["timestamp"]
                }
            else:
                return {
                    "status": "error",
                    "message": result["message"]
                }
                
        except Exception as e:
            frappe.log_error(f"Workflow transition API error: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to transition workflow: {str(e)}"
            }
    
    @frappe.whitelist()
    def get_workflow_info(self):
        """Get workflow information including valid transitions."""
        current_state = self.workflow_state or "Submission"
        
        return {
            "current_state": current_state,
            "valid_transitions": JobOrderWorkflow.get_valid_transitions(current_state),
            "phase_config": JobOrderWorkflow.get_phase_config(current_state),
            "workflow_history": self._get_workflow_history()
        }
    
    def _get_workflow_history(self):
        """Get workflow transition history for this job order."""
        return frappe.get_all(
            "Job Order Workflow History",
            filters={"job_order": self.name},
            fields=["from_phase", "to_phase", "transition_date", "user", "comment", "user_role", "duration_in_previous_phase"],
            order_by="transition_date desc"
        )
    
    @frappe.whitelist()
    def get_phase_summary(self):
        """Get summary of all phases and their status."""
        phases = []
        
        for phase_name, config in JobOrderWorkflow.PHASES.items():
            phase_order = config.get("phase_order", 0)
            if phase_order > 0:  # Exclude special states like Cancelled
                phases.append({
                    "name": phase_name,
                    "order": phase_order,
                    "is_current": phase_name == self.workflow_state,
                    "is_completed": phase_order < JobOrderWorkflow.PHASES.get(self.workflow_state, {}).get("phase_order", 0),
                    "required_fields": config.get("required_fields", []),
                    "permissions": config.get("permissions", {})
                })
        
        # Sort by phase order
        phases.sort(key=lambda x: x["order"])
        
        return phases
