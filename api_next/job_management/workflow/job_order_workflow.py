# Copyright (c) 2025, API Next and contributors
# For license information, please see license.txt

from datetime import datetime
from typing import Dict, List, Optional, Any
import json

# Handle Frappe import gracefully for testing
try:
    import frappe
    from frappe import _
    from frappe.utils import nowdate, now_datetime, add_to_date
    HAS_FRAPPE = True
except ImportError:
    HAS_FRAPPE = False
    # Mock frappe functions for testing
    def nowdate():
        return datetime.now().date()
    
    def now_datetime():
        return datetime.now()
    
    def add_to_date(date, days=0):
        from datetime import timedelta
        return date + timedelta(days=days)

# Import the main workflow implementation
try:
    from api_next.workflows.job_order_workflow import JobOrderWorkflow as BaseJobOrderWorkflow
    HAS_BASE_WORKFLOW = True
except ImportError:
    HAS_BASE_WORKFLOW = False
    BaseJobOrderWorkflow = None

class JobOrderWorkflow:
    """
    Job Order Workflow State Machine for 9-phase process.
    
    This class provides an instance-based interface for the workflow system
    while leveraging the comprehensive implementation in api_next.workflows.
    
    Phases:
    1. SUBMISSION - Initial job request submitted
    2. ESTIMATION - Creating cost and time estimates  
    3. CLIENT_APPROVAL - Awaiting client approval of estimates
    4. PLANNING - Resource allocation and scheduling
    5. PREWORK - Preparation and material ordering
    6. EXECUTION - Active job work
    7. QC_REVIEW - Quality check and client review
    8. INVOICING - Billing and payment processing
    9. CLOSEOUT - Final documentation and archiving
    """
    
    def __init__(self):
        """Initialize the workflow instance."""
        self._phases = {
            "SUBMISSION": {
                "phase_order": 1,
                "name": "Submission",
                "description": "Initial job request submitted",
                "transitions": ["ESTIMATION", "Cancelled"],
                "required_fields": ["customer_name", "project_name", "job_type", "start_date", "description"],
                "permissions": {
                    "submit": ["Job Coordinator", "Project Manager", "System Manager"],
                    "approve": ["Job Coordinator", "Project Manager", "System Manager"]
                },
                "auto_actions": ["create_phase_history", "notify_estimator"],
                "validation_rules": ["validate_basic_info", "check_customer_credit"]
            },
            "ESTIMATION": {
                "phase_order": 2,
                "name": "Estimation", 
                "description": "Creating cost and time estimates",
                "transitions": ["CLIENT_APPROVAL", "SUBMISSION"],
                "required_fields": ["scope_of_work", "material_requisitions", "labor_entries"],
                "permissions": {
                    "submit": ["Estimator", "Project Manager", "System Manager"],
                    "approve": ["Estimator", "Project Manager", "System Manager"]
                },
                "auto_actions": ["calculate_estimates", "create_phase_history", "notify_client"],
                "validation_rules": ["validate_estimates", "check_material_availability"]
            },
            "CLIENT_APPROVAL": {
                "phase_order": 3,
                "name": "Client Approval",
                "description": "Awaiting client approval of estimates", 
                "transitions": ["PLANNING", "ESTIMATION", "Cancelled"],
                "required_fields": ["total_material_cost", "total_labor_cost"],
                "permissions": {
                    "submit": ["Client", "Sales Manager", "Project Manager", "System Manager"],
                    "approve": ["Client", "Sales Manager", "Project Manager", "System Manager"]
                },
                "auto_actions": ["create_phase_history", "notify_planning_team"],
                "validation_rules": ["validate_client_approval", "check_contract_terms"],
                "escalation": {
                    "timeout_days": 7,
                    "escalate_to": ["Sales Manager", "Project Manager"]
                }
            },
            "PLANNING": {
                "phase_order": 4,
                "name": "Planning",
                "description": "Resource allocation and scheduling",
                "transitions": ["PREWORK", "CLIENT_APPROVAL"],
                "required_fields": ["team_members", "start_date", "end_date"],
                "permissions": {
                    "submit": ["Project Manager", "Resource Coordinator", "System Manager"],
                    "approve": ["Project Manager", "Resource Coordinator", "System Manager"]
                },
                "auto_actions": ["allocate_resources", "create_phase_history", "notify_team"],
                "validation_rules": ["validate_resource_availability", "check_schedule_conflicts"]
            },
            "PREWORK": {
                "phase_order": 5,
                "name": "Prework",
                "description": "Preparation and material ordering",
                "transitions": ["EXECUTION", "PLANNING"],
                "required_fields": ["material_requisitions", "team_members"],
                "permissions": {
                    "submit": ["Project Manager", "Site Supervisor", "System Manager"],
                    "approve": ["Project Manager", "Site Supervisor", "System Manager"]
                },
                "auto_actions": ["order_materials", "prepare_equipment", "create_phase_history", "notify_execution_team"],
                "validation_rules": ["validate_material_orders", "check_permits", "verify_equipment_availability"]
            },
            "EXECUTION": {
                "phase_order": 6,
                "name": "Execution",
                "description": "Active job work",
                "transitions": ["QC_REVIEW", "PREWORK"],
                "required_fields": ["labor_entries"],
                "permissions": {
                    "submit": ["Site Supervisor", "Technician", "Project Manager", "System Manager"],
                    "approve": ["Site Supervisor", "Project Manager", "System Manager"]
                },
                "auto_actions": ["track_progress", "update_labor_hours", "create_phase_history", "notify_review_team"],
                "validation_rules": ["validate_work_completion", "check_quality_standards"],
                "parallel_processes": ["material_tracking", "time_tracking", "quality_checks"]
            },
            "QC_REVIEW": {
                "phase_order": 7,
                "name": "QC Review",
                "description": "Quality check and client review",
                "transitions": ["INVOICING", "EXECUTION"],
                "required_fields": ["total_labor_hours", "total_material_cost"],
                "permissions": {
                    "submit": ["Quality Inspector", "Project Manager", "System Manager"],
                    "approve": ["Quality Inspector", "Client", "Project Manager", "System Manager"]
                },
                "auto_actions": ["conduct_quality_check", "client_walkthrough", "create_phase_history", "notify_billing"],
                "validation_rules": ["validate_quality_standards", "client_sign_off"]
            },
            "INVOICING": {
                "phase_order": 8,
                "name": "Invoicing",
                "description": "Billing and payment processing",
                "transitions": ["CLOSEOUT", "QC_REVIEW"],
                "required_fields": ["total_material_cost", "total_labor_cost"],
                "permissions": {
                    "submit": ["Billing Clerk", "Accountant", "Project Manager", "System Manager"],
                    "approve": ["Accountant", "Project Manager", "System Manager"]
                },
                "auto_actions": ["generate_invoice", "send_to_client", "create_phase_history", "notify_accounts"],
                "validation_rules": ["validate_billing_amounts", "check_payment_terms"]
            },
            "CLOSEOUT": {
                "phase_order": 9,
                "name": "Closeout",
                "description": "Final documentation and archiving",
                "transitions": ["Archived"],
                "required_fields": ["documents", "total_labor_hours", "total_material_cost", "total_labor_cost"],
                "permissions": {
                    "submit": ["Project Manager", "Document Controller", "System Manager"],
                    "approve": ["Project Manager", "System Manager"]
                },
                "auto_actions": ["archive_documents", "generate_final_report", "create_phase_history", "notify_completion"],
                "validation_rules": ["validate_documentation", "confirm_payment_received"]
            }
        }
        
        # Build transitions dictionary for easy lookup
        self._transitions = {}
        for phase_name, config in self._phases.items():
            self._transitions[phase_name] = config.get("transitions", [])
    
    @property
    def phases(self) -> Dict[str, Dict[str, Any]]:
        """Get all workflow phases configuration."""
        return self._phases
    
    @property 
    def transitions(self) -> Dict[str, List[str]]:
        """Get transition matrix showing valid transitions from each phase."""
        return self._transitions
    
    def get_phase_config(self, phase_name: str) -> Dict[str, Any]:
        """Get configuration for a specific phase."""
        return self._phases.get(phase_name, {})
    
    def get_valid_transitions(self, current_phase: str) -> List[str]:
        """Get list of valid transitions from current phase."""
        return self._transitions.get(current_phase, [])
    
    def validate_transition(self, doc, from_state: str, to_state: str, user: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate if a transition is allowed based on business rules and permissions.
        
        Args:
            doc: The job order document
            from_state: Current workflow state
            to_state: Target workflow state
            user: User attempting the transition (defaults to current user)
            
        Returns:
            Dict with 'valid' boolean and 'message' explaining validation result
        """
        if HAS_BASE_WORKFLOW:
            # Use the comprehensive validation from the base workflow
            return BaseJobOrderWorkflow.validate_transition(doc, from_state, to_state, user)
        else:
            # Fallback basic validation
            if not user:
                if HAS_FRAPPE:
                    user = frappe.session.user
                else:
                    user = "test_user"

            # Check if transition is valid in workflow
            valid_transitions = self.get_valid_transitions(from_state)
            if to_state not in valid_transitions:
                return {
                    "valid": False,
                    "message": f"Invalid transition from {from_state} to {to_state}. Valid transitions: {', '.join(valid_transitions)}"
                }

            # Check required fields
            to_phase_config = self.get_phase_config(to_state)
            required_fields = to_phase_config.get("required_fields", [])
            missing_fields = []
            for field in required_fields:
                if not getattr(doc, field, None):
                    missing_fields.append(field)
            
            if missing_fields:
                return {
                    "valid": False,
                    "message": f"Missing required fields for {to_state}: {', '.join(missing_fields)}"
                }

            return {"valid": True, "message": "Transition validated successfully"}
    
    def execute_transition(self, doc, new_state: str, user: Optional[str] = None, comment: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a state transition with all associated actions.
        
        Args:
            doc: The job order document
            new_state: Target workflow state
            user: User executing the transition (defaults to current user)
            comment: Optional comment for the transition
            
        Returns:
            Dict with 'success' boolean and relevant data
        """
        if HAS_BASE_WORKFLOW:
            # Use the comprehensive execution from the base workflow
            return BaseJobOrderWorkflow.execute_transition(doc, new_state, user, comment)
        else:
            # Fallback basic execution
            if not user:
                if HAS_FRAPPE:
                    user = frappe.session.user
                else:
                    user = "test_user"

            current_state = getattr(doc, 'workflow_state', 'SUBMISSION')
            
            # Validate transition
            validation = self.validate_transition(doc, current_state, new_state, user)
            if not validation["valid"]:
                if HAS_FRAPPE:
                    frappe.throw(validation["message"])
                else:
                    raise Exception(validation["message"])

            try:
                if HAS_FRAPPE:
                    frappe.db.begin()
                
                # Update document state
                doc.workflow_state = new_state
                if HAS_FRAPPE and hasattr(doc, 'save'):
                    doc.save()
                
                if HAS_FRAPPE:
                    frappe.db.commit()
                
                return {
                    "success": True,
                    "message": f"Successfully transitioned from {current_state} to {new_state}",
                    "new_state": new_state,
                    "timestamp": now_datetime()
                }
                
            except Exception as e:
                if HAS_FRAPPE:
                    frappe.db.rollback()
                    frappe.log_error(f"Workflow transition error: {str(e)}")
                return {
                    "success": False,
                    "message": f"Failed to transition to {new_state}: {str(e)}"
                }
    
    def get_workflow_info(self, doc) -> Dict[str, Any]:
        """
        Get workflow information including valid transitions.
        
        Args:
            doc: The job order document
            
        Returns:
            Dict with current state, valid transitions, and phase configuration
        """
        current_state = getattr(doc, 'workflow_state', 'SUBMISSION')
        
        return {
            "current_state": current_state,
            "valid_transitions": self.get_valid_transitions(current_state),
            "phase_config": self.get_phase_config(current_state),
            "workflow_history": self._get_workflow_history(doc)
        }
    
    def _get_workflow_history(self, doc) -> List[Dict[str, Any]]:
        """Get workflow transition history for the job order."""
        if not HAS_FRAPPE:
            return []
            
        try:
            return frappe.get_all(
                "Job Order Workflow History",
                filters={"job_order": doc.name},
                fields=["from_phase", "to_phase", "transition_date", "user", "comment"],
                order_by="transition_date desc"
            )
        except Exception:
            # Return empty list if history doctype doesn't exist yet
            return []
    
    def get_phase_summary(self, doc) -> List[Dict[str, Any]]:
        """
        Get summary of all phases and their status.
        
        Args:
            doc: The job order document
            
        Returns:
            List of phase summaries ordered by phase sequence
        """
        phases = []
        current_state = getattr(doc, 'workflow_state', 'SUBMISSION')
        current_order = self._phases.get(current_state, {}).get("phase_order", 1)
        
        for phase_name, config in self._phases.items():
            phase_order = config.get("phase_order", 0)
            if phase_order > 0:  # Exclude special states like Cancelled
                phases.append({
                    "name": phase_name,
                    "display_name": config.get("name", phase_name),
                    "description": config.get("description", ""),
                    "order": phase_order,
                    "is_current": phase_name == current_state,
                    "is_completed": phase_order < current_order,
                    "required_fields": config.get("required_fields", []),
                    "permissions": config.get("permissions", {})
                })
        
        # Sort by phase order
        phases.sort(key=lambda x: x["order"])
        
        return phases

# For backwards compatibility, also create class-level methods
@classmethod 
def validate_transition_static(cls, doc, from_state: str, to_state: str, user: Optional[str] = None) -> Dict[str, Any]:
    """Static method for transition validation."""
    workflow = JobOrderWorkflow()
    return workflow.validate_transition(doc, from_state, to_state, user)

@classmethod
def execute_transition_static(cls, doc, new_state: str, user: Optional[str] = None, comment: Optional[str] = None) -> Dict[str, Any]:
    """Static method for transition execution.""" 
    workflow = JobOrderWorkflow()
    return workflow.execute_transition(doc, new_state, user, comment)

# Attach static methods to class
JobOrderWorkflow.validate_transition_static = validate_transition_static
JobOrderWorkflow.execute_transition_static = execute_transition_static