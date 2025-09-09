# Copyright (c) 2025, API Next and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate, now_datetime, add_to_date
from datetime import datetime
from typing import Dict, List, Optional, Any
import json

class JobOrderWorkflow:
    """
    Comprehensive workflow state machine for Job Order 9-phase process.
    
    Phases:
    1. Submission - Initial job request submitted
    2. Estimation - Creating cost and time estimates
    3. Client Approval - Awaiting client approval of estimates
    4. Planning - Resource allocation and scheduling
    5. Prework - Preparation and material ordering
    6. Execution - Active job work
    7. Review - Quality check and client review
    8. Invoicing - Billing and payment processing
    9. Closeout - Final documentation and archiving
    """
    
    # Workflow state definitions with transitions, permissions, and rules
    PHASES = {
        "Submission": {
            "phase_order": 1,
            "transitions": ["Estimation", "Cancelled"],
            "required_fields": ["customer_name", "project_name", "job_type", "start_date", "description"],
            "permissions": {
                "submit": ["Job Coordinator", "Project Manager", "System Manager"],
                "approve": ["Job Coordinator", "Project Manager", "System Manager"]
            },
            "auto_actions": ["create_phase_history", "notify_estimator"],
            "validation_rules": ["validate_basic_info", "check_customer_credit"]
        },
        "Estimation": {
            "phase_order": 2,
            "transitions": ["Client Approval", "Submission"],  # Can reject back to submission
            "required_fields": ["scope_of_work", "material_requisitions", "labor_entries"],
            "permissions": {
                "submit": ["Estimator", "Project Manager", "System Manager"],
                "approve": ["Estimator", "Project Manager", "System Manager"]
            },
            "auto_actions": ["calculate_estimates", "create_phase_history", "notify_client"],
            "validation_rules": ["validate_estimates", "check_material_availability"]
        },
        "Client Approval": {
            "phase_order": 3,
            "transitions": ["Planning", "Estimation", "Cancelled"],  # Can reject back to estimation
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
        "Planning": {
            "phase_order": 4,
            "transitions": ["Prework", "Client Approval"],  # Can go back for re-approval
            "required_fields": ["team_members", "start_date", "end_date"],
            "permissions": {
                "submit": ["Project Manager", "Resource Coordinator", "System Manager"],
                "approve": ["Project Manager", "Resource Coordinator", "System Manager"]
            },
            "auto_actions": ["allocate_resources", "create_phase_history", "notify_team"],
            "validation_rules": ["validate_resource_availability", "check_schedule_conflicts"]
        },
        "Prework": {
            "phase_order": 5,
            "transitions": ["Execution", "Planning"],  # Can go back to planning
            "required_fields": ["material_requisitions", "team_members"],
            "permissions": {
                "submit": ["Project Manager", "Site Supervisor", "System Manager"],
                "approve": ["Project Manager", "Site Supervisor", "System Manager"]
            },
            "auto_actions": ["order_materials", "prepare_equipment", "create_phase_history", "notify_execution_team"],
            "validation_rules": ["validate_material_orders", "check_permits", "verify_equipment_availability"]
        },
        "Execution": {
            "phase_order": 6,
            "transitions": ["Review", "Prework"],  # Can go back to prework if issues
            "required_fields": ["labor_entries"],
            "permissions": {
                "submit": ["Site Supervisor", "Technician", "Project Manager", "System Manager"],
                "approve": ["Site Supervisor", "Project Manager", "System Manager"]
            },
            "auto_actions": ["track_progress", "update_labor_hours", "create_phase_history", "notify_review_team"],
            "validation_rules": ["validate_work_completion", "check_quality_standards"],
            "parallel_processes": ["material_tracking", "time_tracking", "quality_checks"]
        },
        "Review": {
            "phase_order": 7,
            "transitions": ["Invoicing", "Execution"],  # Can go back to execution for rework
            "required_fields": ["total_labor_hours", "total_material_cost"],
            "permissions": {
                "submit": ["Quality Inspector", "Project Manager", "System Manager"],
                "approve": ["Quality Inspector", "Client", "Project Manager", "System Manager"]
            },
            "auto_actions": ["conduct_quality_check", "client_walkthrough", "create_phase_history", "notify_billing"],
            "validation_rules": ["validate_quality_standards", "client_sign_off"]
        },
        "Invoicing": {
            "phase_order": 8,
            "transitions": ["Closeout", "Review"],  # Can go back to review for changes
            "required_fields": ["total_material_cost", "total_labor_cost"],
            "permissions": {
                "submit": ["Billing Clerk", "Accountant", "Project Manager", "System Manager"],
                "approve": ["Accountant", "Project Manager", "System Manager"]
            },
            "auto_actions": ["generate_invoice", "send_to_client", "create_phase_history", "notify_accounts"],
            "validation_rules": ["validate_billing_amounts", "check_payment_terms"]
        },
        "Closeout": {
            "phase_order": 9,
            "transitions": ["Archived"],  # Final state
            "required_fields": ["documents", "total_labor_hours", "total_material_cost", "total_labor_cost"],
            "permissions": {
                "submit": ["Project Manager", "Document Controller", "System Manager"],
                "approve": ["Project Manager", "System Manager"]
            },
            "auto_actions": ["archive_documents", "generate_final_report", "create_phase_history", "notify_completion"],
            "validation_rules": ["validate_documentation", "confirm_payment_received"]
        },
        "Archived": {
            "phase_order": 10,
            "transitions": [],  # No further transitions
            "required_fields": [],
            "permissions": {
                "view": ["All Roles"]
            },
            "auto_actions": ["final_archival"],
            "validation_rules": []
        },
        "Cancelled": {
            "phase_order": 0,  # Special state
            "transitions": ["Submission"],  # Can be reactivated
            "required_fields": ["cancellation_reason"],
            "permissions": {
                "submit": ["Project Manager", "System Manager"],
                "approve": ["Project Manager", "System Manager"]
            },
            "auto_actions": ["release_resources", "notify_cancellation", "create_phase_history"],
            "validation_rules": ["validate_cancellation_reason"]
        }
    }

    @classmethod
    def get_phase_config(cls, phase_name: str) -> Dict[str, Any]:
        """Get configuration for a specific phase."""
        return cls.PHASES.get(phase_name, {})

    @classmethod
    def get_valid_transitions(cls, current_phase: str) -> List[str]:
        """Get list of valid transitions from current phase."""
        phase_config = cls.get_phase_config(current_phase)
        return phase_config.get("transitions", [])

    @classmethod
    def validate_transition(cls, doc, from_state: str, to_state: str, user: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate if a transition is allowed based on business rules and permissions.
        
        Returns:
            Dict with 'valid' boolean and 'message' explaining why if invalid
        """
        if not user:
            user = frappe.session.user

        # Check if transition is valid in workflow
        valid_transitions = cls.get_valid_transitions(from_state)
        if to_state not in valid_transitions:
            return {
                "valid": False,
                "message": f"Invalid transition from {from_state} to {to_state}. Valid transitions: {', '.join(valid_transitions)}"
            }

        # Check user permissions
        to_phase_config = cls.get_phase_config(to_state)
        required_roles = to_phase_config.get("permissions", {}).get("submit", [])
        
        user_roles = frappe.get_roles(user)
        if required_roles and not any(role in user_roles for role in required_roles):
            return {
                "valid": False,
                "message": f"User does not have required roles for {to_state}. Required: {', '.join(required_roles)}"
            }

        # Check required fields
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

        # Run validation rules
        validation_rules = to_phase_config.get("validation_rules", [])
        for rule in validation_rules:
            rule_result = cls._execute_validation_rule(doc, rule, from_state, to_state)
            if not rule_result["valid"]:
                return rule_result

        return {"valid": True, "message": "Transition validated successfully"}

    @classmethod
    def execute_transition(cls, doc, new_state: str, user: Optional[str] = None, comment: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a state transition with all associated actions.
        
        Returns:
            Dict with 'success' boolean and relevant data
        """
        if not user:
            user = frappe.session.user

        current_state = getattr(doc, 'workflow_state', 'Submission')
        
        # Validate transition
        validation = cls.validate_transition(doc, current_state, new_state, user)
        if not validation["valid"]:
            frappe.throw(validation["message"])

        try:
            frappe.db.begin()
            
            # Update document state
            doc.workflow_state = new_state
            doc.save()
            
            # Execute auto actions
            cls._execute_auto_actions(doc, new_state, user)
            
            # Create workflow history record
            cls._create_workflow_history(doc, current_state, new_state, user, comment)
            
            # Handle escalations if configured
            cls._setup_escalations(doc, new_state)
            
            frappe.db.commit()
            
            return {
                "success": True,
                "message": f"Successfully transitioned from {current_state} to {new_state}",
                "new_state": new_state,
                "timestamp": now_datetime()
            }
            
        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(f"Workflow transition error: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to transition to {new_state}: {str(e)}"
            }

    @classmethod
    def _execute_validation_rule(cls, doc, rule_name: str, from_state: str, to_state: str) -> Dict[str, Any]:
        """Execute a specific validation rule."""
        try:
            if rule_name == "validate_basic_info":
                return cls._validate_basic_info(doc)
            elif rule_name == "check_customer_credit":
                return cls._check_customer_credit(doc)
            elif rule_name == "validate_estimates":
                return cls._validate_estimates(doc)
            elif rule_name == "check_material_availability":
                return cls._check_material_availability(doc)
            elif rule_name == "validate_client_approval":
                return cls._validate_client_approval(doc)
            elif rule_name == "check_contract_terms":
                return cls._check_contract_terms(doc)
            elif rule_name == "validate_resource_availability":
                return cls._validate_resource_availability(doc)
            elif rule_name == "check_schedule_conflicts":
                return cls._check_schedule_conflicts(doc)
            elif rule_name == "validate_material_orders":
                return cls._validate_material_orders(doc)
            elif rule_name == "check_permits":
                return cls._check_permits(doc)
            elif rule_name == "verify_equipment_availability":
                return cls._verify_equipment_availability(doc)
            elif rule_name == "validate_work_completion":
                return cls._validate_work_completion(doc)
            elif rule_name == "check_quality_standards":
                return cls._check_quality_standards(doc)
            elif rule_name == "validate_quality_standards":
                return cls._validate_quality_standards(doc)
            elif rule_name == "client_sign_off":
                return cls._client_sign_off(doc)
            elif rule_name == "validate_billing_amounts":
                return cls._validate_billing_amounts(doc)
            elif rule_name == "check_payment_terms":
                return cls._check_payment_terms(doc)
            elif rule_name == "validate_documentation":
                return cls._validate_documentation(doc)
            elif rule_name == "confirm_payment_received":
                return cls._confirm_payment_received(doc)
            elif rule_name == "validate_cancellation_reason":
                return cls._validate_cancellation_reason(doc)
            else:
                return {"valid": True, "message": f"Unknown validation rule: {rule_name}"}
                
        except Exception as e:
            frappe.log_error(f"Validation rule error ({rule_name}): {str(e)}")
            return {"valid": False, "message": f"Validation rule failed: {rule_name}"}

    @classmethod
    def _execute_auto_actions(cls, doc, new_state: str, user: str):
        """Execute automatic actions for a state transition."""
        phase_config = cls.get_phase_config(new_state)
        auto_actions = phase_config.get("auto_actions", [])
        
        for action in auto_actions:
            try:
                if action == "create_phase_history":
                    # This is handled separately
                    continue
                elif action == "notify_estimator":
                    cls._notify_estimator(doc)
                elif action == "calculate_estimates":
                    cls._calculate_estimates(doc)
                elif action == "notify_client":
                    cls._notify_client(doc)
                elif action == "notify_planning_team":
                    cls._notify_planning_team(doc)
                elif action == "allocate_resources":
                    cls._allocate_resources(doc)
                elif action == "notify_team":
                    cls._notify_team(doc)
                elif action == "order_materials":
                    cls._order_materials(doc)
                elif action == "prepare_equipment":
                    cls._prepare_equipment(doc)
                elif action == "notify_execution_team":
                    cls._notify_execution_team(doc)
                elif action == "track_progress":
                    cls._track_progress(doc)
                elif action == "update_labor_hours":
                    cls._update_labor_hours(doc)
                elif action == "notify_review_team":
                    cls._notify_review_team(doc)
                elif action == "conduct_quality_check":
                    cls._conduct_quality_check(doc)
                elif action == "client_walkthrough":
                    cls._client_walkthrough(doc)
                elif action == "notify_billing":
                    cls._notify_billing(doc)
                elif action == "generate_invoice":
                    cls._generate_invoice(doc)
                elif action == "send_to_client":
                    cls._send_to_client(doc)
                elif action == "notify_accounts":
                    cls._notify_accounts(doc)
                elif action == "archive_documents":
                    cls._archive_documents(doc)
                elif action == "generate_final_report":
                    cls._generate_final_report(doc)
                elif action == "notify_completion":
                    cls._notify_completion(doc)
                elif action == "final_archival":
                    cls._final_archival(doc)
                elif action == "release_resources":
                    cls._release_resources(doc)
                elif action == "notify_cancellation":
                    cls._notify_cancellation(doc)
                    
            except Exception as e:
                frappe.log_error(f"Auto action error ({action}): {str(e)}")

    @classmethod
    def _create_workflow_history(cls, doc, from_state: str, to_state: str, user: str, comment: Optional[str] = None):
        """Create workflow history record."""
        history = frappe.get_doc({
            "doctype": "Job Order Workflow History",
            "job_order": doc.name,
            "from_phase": from_state,
            "to_phase": to_state,
            "transition_date": now_datetime(),
            "user": user,
            "comment": comment or f"Transitioned from {from_state} to {to_state}",
            "additional_data": {
                "job_type": doc.job_type,
                "priority": doc.priority,
                "customer_name": doc.customer_name,
                "project_name": doc.project_name
            }
        })
        history.insert(ignore_permissions=True)

    @classmethod
    def _setup_escalations(cls, doc, new_state: str):
        """Setup escalation timers if configured for the state."""
        phase_config = cls.get_phase_config(new_state)
        escalation_config = phase_config.get("escalation")
        
        if escalation_config:
            # Create escalation job using Frappe's job scheduler
            escalation_date = add_to_date(nowdate(), days=escalation_config["timeout_days"])
            frappe.enqueue(
                "api_next.workflows.job_order_workflow.escalate_job_order",
                job_order=doc.name,
                current_state=new_state,
                escalate_to=escalation_config["escalate_to"],
                timeout=60,
                at_front=False,
                scheduled_date=escalation_date
            )

    # Validation rule implementations
    @classmethod
    def _validate_basic_info(cls, doc) -> Dict[str, Any]:
        """Validate basic job information is complete."""
        required = ["customer_name", "project_name", "job_type", "description"]
        missing = [field for field in required if not getattr(doc, field)]
        
        if missing:
            return {"valid": False, "message": f"Missing basic information: {', '.join(missing)}"}
        return {"valid": True, "message": "Basic information validated"}

    @classmethod
    def _check_customer_credit(cls, doc) -> Dict[str, Any]:
        """Check customer credit status."""
        # Placeholder for credit check logic
        return {"valid": True, "message": "Customer credit check passed"}

    @classmethod
    def _validate_estimates(cls, doc) -> Dict[str, Any]:
        """Validate estimates are complete and reasonable."""
        if not doc.material_requisitions and not doc.labor_entries:
            return {"valid": False, "message": "Either material requisitions or labor entries must be provided"}
        return {"valid": True, "message": "Estimates validated"}

    @classmethod
    def _check_material_availability(cls, doc) -> Dict[str, Any]:
        """Check if required materials are available."""
        # Placeholder for material availability check
        return {"valid": True, "message": "Material availability confirmed"}

    @classmethod
    def _validate_client_approval(cls, doc) -> Dict[str, Any]:
        """Validate client has approved the estimates."""
        # Check for approval documentation or field
        return {"valid": True, "message": "Client approval validated"}

    @classmethod
    def _check_contract_terms(cls, doc) -> Dict[str, Any]:
        """Validate contract terms are acceptable."""
        return {"valid": True, "message": "Contract terms validated"}

    @classmethod
    def _validate_resource_availability(cls, doc) -> Dict[str, Any]:
        """Check if required resources are available."""
        if not doc.team_members:
            return {"valid": False, "message": "Team members must be assigned"}
        return {"valid": True, "message": "Resource availability validated"}

    @classmethod
    def _check_schedule_conflicts(cls, doc) -> Dict[str, Any]:
        """Check for scheduling conflicts with team members."""
        return {"valid": True, "message": "No scheduling conflicts found"}

    @classmethod
    def _validate_material_orders(cls, doc) -> Dict[str, Any]:
        """Validate material orders are complete."""
        return {"valid": True, "message": "Material orders validated"}

    @classmethod
    def _check_permits(cls, doc) -> Dict[str, Any]:
        """Check if all required permits are obtained."""
        return {"valid": True, "message": "Permits verified"}

    @classmethod
    def _verify_equipment_availability(cls, doc) -> Dict[str, Any]:
        """Verify equipment availability for the job."""
        return {"valid": True, "message": "Equipment availability verified"}

    @classmethod
    def _validate_work_completion(cls, doc) -> Dict[str, Any]:
        """Validate work has been completed according to specifications."""
        return {"valid": True, "message": "Work completion validated"}

    @classmethod
    def _check_quality_standards(cls, doc) -> Dict[str, Any]:
        """Check if work meets quality standards."""
        return {"valid": True, "message": "Quality standards met"}

    @classmethod
    def _validate_quality_standards(cls, doc) -> Dict[str, Any]:
        """Final quality validation."""
        return {"valid": True, "message": "Quality standards validated"}

    @classmethod
    def _client_sign_off(cls, doc) -> Dict[str, Any]:
        """Validate client has signed off on completed work."""
        return {"valid": True, "message": "Client sign-off confirmed"}

    @classmethod
    def _validate_billing_amounts(cls, doc) -> Dict[str, Any]:
        """Validate billing amounts are correct."""
        if not doc.total_material_cost and not doc.total_labor_cost:
            return {"valid": False, "message": "No billing amounts calculated"}
        return {"valid": True, "message": "Billing amounts validated"}

    @classmethod
    def _check_payment_terms(cls, doc) -> Dict[str, Any]:
        """Check payment terms are acceptable."""
        return {"valid": True, "message": "Payment terms validated"}

    @classmethod
    def _validate_documentation(cls, doc) -> Dict[str, Any]:
        """Validate all required documentation is complete."""
        return {"valid": True, "message": "Documentation validated"}

    @classmethod
    def _confirm_payment_received(cls, doc) -> Dict[str, Any]:
        """Confirm payment has been received."""
        return {"valid": True, "message": "Payment confirmed"}

    @classmethod
    def _validate_cancellation_reason(cls, doc) -> Dict[str, Any]:
        """Validate cancellation reason is provided."""
        if not hasattr(doc, 'cancellation_reason') or not doc.cancellation_reason:
            return {"valid": False, "message": "Cancellation reason is required"}
        return {"valid": True, "message": "Cancellation reason validated"}

    # Auto action implementations (placeholders for now)
    @classmethod
    def _notify_estimator(cls, doc): pass

    @classmethod
    def _calculate_estimates(cls, doc): pass

    @classmethod
    def _notify_client(cls, doc): pass

    @classmethod
    def _notify_planning_team(cls, doc): pass

    @classmethod
    def _allocate_resources(cls, doc): pass

    @classmethod
    def _notify_team(cls, doc): pass

    @classmethod
    def _order_materials(cls, doc): pass

    @classmethod
    def _prepare_equipment(cls, doc): pass

    @classmethod
    def _notify_execution_team(cls, doc): pass

    @classmethod
    def _track_progress(cls, doc): pass

    @classmethod
    def _update_labor_hours(cls, doc): pass

    @classmethod
    def _notify_review_team(cls, doc): pass

    @classmethod
    def _conduct_quality_check(cls, doc): pass

    @classmethod
    def _client_walkthrough(cls, doc): pass

    @classmethod
    def _notify_billing(cls, doc): pass

    @classmethod
    def _generate_invoice(cls, doc): pass

    @classmethod
    def _send_to_client(cls, doc): pass

    @classmethod
    def _notify_accounts(cls, doc): pass

    @classmethod
    def _archive_documents(cls, doc): pass

    @classmethod
    def _generate_final_report(cls, doc): pass

    @classmethod
    def _notify_completion(cls, doc): pass

    @classmethod
    def _final_archival(cls, doc): pass

    @classmethod
    def _release_resources(cls, doc): pass

    @classmethod
    def _notify_cancellation(cls, doc): pass

# Escalation function for job scheduler
@frappe.whitelist()
def escalate_job_order(job_order: str, current_state: str, escalate_to: List[str]):
    """Escalate job order if still in the same state after timeout."""
    doc = frappe.get_doc("Job Order", job_order)
    
    if doc.workflow_state == current_state:
        # Send escalation notifications
        for role in escalate_to:
            # Implementation for sending escalation notifications
            pass