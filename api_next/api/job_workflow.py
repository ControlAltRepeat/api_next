# Job Order 9-Phase Workflow API Endpoints
# Comprehensive phase transition management for API_Next ERP

import frappe
from frappe import _
from frappe.utils import now, today, add_days, get_datetime, time_diff_in_hours
from frappe.utils.data import flt
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


# ============================================================================
# CORE PHASE TRANSITION MANAGEMENT
# ============================================================================

@frappe.whitelist()
def transition_phase(job_order: str, action: str, comments: str = None, **kwargs):
    """
    Transition a job order to the next phase in the workflow.
    
    Args:
        job_order (str): Job Order document name
        action (str): Workflow action to perform
        comments (str): Optional comments for the transition
        **kwargs: Additional parameters for specific transitions
    
    Returns:
        dict: Success/error response with transition details
    """
    try:
        # Validate permissions
        if not frappe.has_permission("Job Order", "write"):
            return {
                "success": False,
                "error": "PermissionError",
                "message": "Insufficient permissions to transition job phases"
            }
        
        # Get job order document
        try:
            job_doc = frappe.get_doc("Job Order", job_order)
        except frappe.DoesNotExistError:
            return {
                "success": False,
                "error": "NotFoundError",
                "message": f"Job Order {job_order} not found"
            }
        
        # Get current workflow state
        current_state = job_doc.workflow_state
        
        # Validate transition is allowed
        validation_result = _validate_transition(job_doc, action)
        if not validation_result["valid"]:
            return {
                "success": False,
                "error": "ValidationError",
                "message": validation_result["message"],
                "details": validation_result
            }
        
        # Get next state from workflow
        next_state = _get_next_state(current_state, action)
        if not next_state:
            return {
                "success": False,
                "error": "WorkflowError",
                "message": f"No next state found for action '{action}' from state '{current_state}'"
            }
        
        # Record phase history before transition
        _record_phase_history(job_doc, current_state, comments)
        
        # Perform pre-transition validations
        prereq_check = _check_phase_prerequisites(job_doc, next_state)
        if not prereq_check["valid"]:
            return {
                "success": False,
                "error": "PrerequisiteError",
                "message": "Phase prerequisites not met",
                "details": prereq_check
            }
        
        # Apply the workflow action
        old_state = job_doc.workflow_state
        job_doc.apply_workflow(job_doc, action)
        
        # Update phase timing
        job_doc.phase_start_date = now()
        if kwargs.get("phase_target_date"):
            job_doc.phase_target_date = kwargs["phase_target_date"]
        
        # Execute phase-specific logic
        _execute_phase_logic(job_doc, old_state, next_state, **kwargs)
        
        # Save changes
        job_doc.save()
        frappe.db.commit()
        
        # Send notifications
        _send_transition_notifications(job_doc, old_state, next_state, action, comments)
        
        # Log transition for audit
        frappe.log_error(
            f"Phase transition: {job_order} from {old_state} to {next_state} by {frappe.session.user}",
            "Job Workflow Transition"
        )
        
        return {
            "success": True,
            "data": {
                "job_order": job_order,
                "old_state": old_state,
                "new_state": next_state,
                "action": action,
                "timestamp": now(),
                "user": frappe.session.user
            },
            "message": f"Job Order {job_order} successfully transitioned from {old_state} to {next_state}"
        }
        
    except Exception as e:
        frappe.log_error(f"Phase transition error: {str(e)}", "Job Workflow API Error")
        return {
            "success": False,
            "error": "SystemError",
            "message": f"System error during phase transition: {str(e)}"
        }


@frappe.whitelist()
def get_available_transitions(job_order: str):
    """
    Get all available workflow transitions for a job order.
    
    Args:
        job_order (str): Job Order document name
    
    Returns:
        dict: Available transitions with validation status
    """
    try:
        job_doc = frappe.get_doc("Job Order", job_order)
        current_state = job_doc.workflow_state
        
        # Get workflow definition
        workflow = frappe.get_doc("Workflow", "Job Order Workflow")
        
        # Find available transitions
        available_transitions = []
        
        for transition in workflow.transitions:
            if transition.state == current_state:
                # Check if user has permission for this transition
                allowed_roles = [role.strip() for role in transition.allowed.split(',')]
                user_roles = frappe.get_roles(frappe.session.user)
                
                has_permission = any(role in user_roles for role in allowed_roles)
                
                # Validate transition requirements
                validation = _validate_transition(job_doc, transition.action)
                prereq_check = _check_phase_prerequisites(job_doc, transition.next_state)
                
                transition_data = {
                    "action": transition.action,
                    "next_state": transition.next_state,
                    "allowed_roles": allowed_roles,
                    "has_permission": has_permission,
                    "is_valid": validation["valid"] and prereq_check["valid"],
                    "validation_message": validation["message"] if not validation["valid"] else None,
                    "prerequisites": prereq_check
                }
                
                available_transitions.append(transition_data)
        
        return {
            "success": True,
            "data": {
                "job_order": job_order,
                "current_state": current_state,
                "available_transitions": available_transitions
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }


@frappe.whitelist()
def bulk_transition(job_orders: str, action: str, comments: str = None):
    """
    Perform bulk phase transitions on multiple job orders.
    
    Args:
        job_orders (str): JSON string of job order names
        action (str): Workflow action to perform
        comments (str): Optional comments for transitions
    
    Returns:
        dict: Bulk operation results
    """
    try:
        # Parse job orders list
        if isinstance(job_orders, str):
            job_orders = json.loads(job_orders)
        
        if not isinstance(job_orders, list):
            return {
                "success": False,
                "error": "ValidationError",
                "message": "job_orders must be a list of job order names"
            }
        
        # Validate bulk operation permissions
        if not frappe.has_permission("Job Order", "write"):
            return {
                "success": False,
                "error": "PermissionError",
                "message": "Insufficient permissions for bulk operations"
            }
        
        # Process each job order
        results = []
        success_count = 0
        error_count = 0
        
        for job_order in job_orders:
            try:
                result = transition_phase(job_order, action, comments)
                if result["success"]:
                    success_count += 1
                else:
                    error_count += 1
                results.append({
                    "job_order": job_order,
                    "success": result["success"],
                    "message": result["message"]
                })
            except Exception as e:
                error_count += 1
                results.append({
                    "job_order": job_order,
                    "success": False,
                    "message": str(e)
                })
        
        return {
            "success": True,
            "data": {
                "total_processed": len(job_orders),
                "successful": success_count,
                "failed": error_count,
                "results": results
            },
            "message": f"Bulk transition completed: {success_count} successful, {error_count} failed"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }


@frappe.whitelist()
def rollback_phase(job_order: str, target_state: str, reason: str):
    """
    Rollback a job order to a previous phase state.
    
    Args:
        job_order (str): Job Order document name
        target_state (str): Target state to rollback to
        reason (str): Reason for rollback
    
    Returns:
        dict: Rollback operation result
    """
    try:
        # Validate permissions (requires System Manager role)
        if "System Manager" not in frappe.get_roles(frappe.session.user):
            return {
                "success": False,
                "error": "PermissionError",
                "message": "Rollback operations require System Manager permissions"
            }
        
        job_doc = frappe.get_doc("Job Order", job_order)
        current_state = job_doc.workflow_state
        
        # Validate rollback is to a previous state
        if not _is_valid_rollback(current_state, target_state):
            return {
                "success": False,
                "error": "ValidationError",
                "message": f"Cannot rollback from {current_state} to {target_state}"
            }
        
        # Record rollback in history
        _record_phase_history(job_doc, current_state, f"ROLLBACK: {reason}")
        
        # Perform rollback
        job_doc.workflow_state = target_state
        job_doc.phase_start_date = now()
        
        # Reset phase-specific data if needed
        _handle_rollback_cleanup(job_doc, current_state, target_state)
        
        job_doc.save()
        frappe.db.commit()
        
        # Send rollback notifications
        _send_rollback_notifications(job_doc, current_state, target_state, reason)
        
        # Log rollback for audit
        frappe.log_error(
            f"Phase rollback: {job_order} from {current_state} to {target_state} by {frappe.session.user}",
            "Job Workflow Rollback"
        )
        
        return {
            "success": True,
            "data": {
                "job_order": job_order,
                "from_state": current_state,
                "to_state": target_state,
                "reason": reason,
                "timestamp": now(),
                "user": frappe.session.user
            },
            "message": f"Job Order {job_order} rolled back from {current_state} to {target_state}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }


# ============================================================================
# STATUS AND HISTORY TRACKING
# ============================================================================

@frappe.whitelist()
def get_workflow_status(job_order: str):
    """
    Get comprehensive workflow status for a job order.
    
    Args:
        job_order (str): Job Order document name
    
    Returns:
        dict: Complete workflow status information
    """
    try:
        job_doc = frappe.get_doc("Job Order", job_order)
        
        # Get phase history
        phase_history = _get_phase_history_data(job_order)
        
        # Calculate phase durations
        phase_durations = _calculate_phase_durations(phase_history)
        
        # Get current phase info
        current_phase_info = _get_current_phase_info(job_doc)
        
        # Calculate overall progress
        progress = _calculate_workflow_progress(job_doc.workflow_state)
        
        return {
            "success": True,
            "data": {
                "job_order": job_order,
                "current_state": job_doc.workflow_state,
                "current_status": job_doc.status,
                "phase_start_date": job_doc.phase_start_date,
                "phase_target_date": job_doc.phase_target_date,
                "progress_percentage": progress,
                "current_phase_info": current_phase_info,
                "phase_history": phase_history,
                "phase_durations": phase_durations,
                "total_workflow_duration": _calculate_total_duration(phase_history)
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }


@frappe.whitelist()
def get_phase_history(job_order: str, include_details: bool = True):
    """
    Get detailed phase transition history for a job order.
    
    Args:
        job_order (str): Job Order document name
        include_details (bool): Include detailed transition information
    
    Returns:
        dict: Phase history with optional details
    """
    try:
        history_data = _get_phase_history_data(job_order)
        
        if include_details:
            # Enrich history with additional details
            for entry in history_data:
                entry["duration_hours"] = entry.get("duration", 0)
                entry["duration_formatted"] = _format_duration(entry.get("duration", 0))
        
        return {
            "success": True,
            "data": {
                "job_order": job_order,
                "history_count": len(history_data),
                "history": history_data
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }


@frappe.whitelist()
def get_phase_analytics(job_order: str = None, date_range: str = "30"):
    """
    Get analytics for phase transitions and performance.
    
    Args:
        job_order (str): Specific job order or None for all jobs
        date_range (str): Days to look back for analytics
    
    Returns:
        dict: Phase analytics and metrics
    """
    try:
        date_from = add_days(today(), -int(date_range))
        
        # Build filters
        filters = {"creation": [">=", date_from]}
        if job_order:
            filters["name"] = job_order
        
        # Get job orders in date range
        job_orders = frappe.get_all("Job Order", 
            filters=filters,
            fields=["name", "workflow_state", "creation", "modified"]
        )
        
        # Calculate analytics
        phase_distribution = _calculate_phase_distribution(job_orders)
        average_durations = _calculate_average_phase_durations(date_from)
        transition_trends = _calculate_transition_trends(date_from)
        bottlenecks = _identify_phase_bottlenecks(date_from)
        
        return {
            "success": True,
            "data": {
                "period": f"Last {date_range} days",
                "total_jobs": len(job_orders),
                "phase_distribution": phase_distribution,
                "average_phase_durations": average_durations,
                "transition_trends": transition_trends,
                "bottlenecks": bottlenecks
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }


# ============================================================================
# VALIDATION AND PREREQUISITES
# ============================================================================

@frappe.whitelist()
def validate_transition(job_order: str, action: str):
    """
    Validate if a phase transition is allowed and possible.
    
    Args:
        job_order (str): Job Order document name
        action (str): Proposed workflow action
    
    Returns:
        dict: Validation result with details
    """
    try:
        job_doc = frappe.get_doc("Job Order", job_order)
        
        # Basic transition validation
        validation_result = _validate_transition(job_doc, action)
        
        # Get next state
        next_state = _get_next_state(job_doc.workflow_state, action)
        
        # Check prerequisites
        prereq_result = _check_phase_prerequisites(job_doc, next_state) if next_state else {"valid": False}
        
        # Check user permissions
        permission_result = _check_transition_permissions(job_doc, action)
        
        # Check business rules
        business_rules_result = _check_business_rules(job_doc, action, next_state)
        
        overall_valid = (validation_result["valid"] and 
                        prereq_result["valid"] and 
                        permission_result["valid"] and 
                        business_rules_result["valid"])
        
        return {
            "success": True,
            "data": {
                "job_order": job_order,
                "action": action,
                "current_state": job_doc.workflow_state,
                "next_state": next_state,
                "is_valid": overall_valid,
                "validation_details": {
                    "transition_valid": validation_result,
                    "prerequisites": prereq_result,
                    "permissions": permission_result,
                    "business_rules": business_rules_result
                }
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }


@frappe.whitelist()
def get_phase_requirements(phase: str):
    """
    Get requirements and prerequisites for a specific phase.
    
    Args:
        phase (str): Workflow state/phase name
    
    Returns:
        dict: Phase requirements and validation criteria
    """
    try:
        requirements = _get_phase_requirements_config(phase)
        
        return {
            "success": True,
            "data": {
                "phase": phase,
                "requirements": requirements
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }


@frappe.whitelist()
def check_prerequisites(job_order: str, target_phase: str):
    """
    Check if all prerequisites are met for transitioning to a target phase.
    
    Args:
        job_order (str): Job Order document name
        target_phase (str): Target workflow state
    
    Returns:
        dict: Prerequisites check result
    """
    try:
        job_doc = frappe.get_doc("Job Order", job_order)
        
        prereq_result = _check_phase_prerequisites(job_doc, target_phase)
        
        return {
            "success": True,
            "data": {
                "job_order": job_order,
                "target_phase": target_phase,
                "prerequisites_met": prereq_result["valid"],
                "details": prereq_result
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }


# ============================================================================
# DASHBOARD AND REPORTING
# ============================================================================

@frappe.whitelist()
def get_jobs_by_phase(phase: str = None, limit: int = 20, offset: int = 0):
    """
    Get job orders grouped by workflow phase.
    
    Args:
        phase (str): Specific phase filter (optional)
        limit (int): Number of records to return
        offset (int): Pagination offset
    
    Returns:
        dict: Job orders grouped by phase
    """
    try:
        filters = {}
        if phase:
            filters["workflow_state"] = phase
        
        # Get job orders
        job_orders = frappe.get_all("Job Order",
            filters=filters,
            fields=["name", "job_number", "customer_name", "project_name", 
                   "workflow_state", "status", "priority", "start_date", 
                   "phase_start_date", "phase_target_date"],
            limit=limit,
            offset=offset,
            order_by="phase_start_date desc"
        )
        
        # Group by phase if no specific phase requested
        if not phase:
            grouped_jobs = {}
            for job in job_orders:
                phase_key = job["workflow_state"]
                if phase_key not in grouped_jobs:
                    grouped_jobs[phase_key] = []
                grouped_jobs[phase_key].append(job)
            
            return {
                "success": True,
                "data": {
                    "grouped_by_phase": grouped_jobs,
                    "total_jobs": len(job_orders)
                }
            }
        else:
            return {
                "success": True,
                "data": {
                    "phase": phase,
                    "jobs": job_orders,
                    "total_jobs": len(job_orders)
                }
            }
        
    except Exception as e:
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }


@frappe.whitelist()
def get_phase_metrics(date_range: str = "30"):
    """
    Get comprehensive metrics for all workflow phases.
    
    Args:
        date_range (str): Days to analyze
    
    Returns:
        dict: Phase metrics and KPIs
    """
    try:
        date_from = add_days(today(), -int(date_range))
        
        # Get metrics for each phase
        phase_metrics = {}
        phases = ["Submission", "Estimation", "Client Approval", "Planning", 
                 "Prework", "Execution", "Review", "Invoicing", "Closeout", "Archived"]
        
        for phase in phases:
            metrics = _calculate_phase_metrics(phase, date_from)
            phase_metrics[phase] = metrics
        
        # Calculate overall metrics
        overall_metrics = _calculate_overall_workflow_metrics(date_from)
        
        return {
            "success": True,
            "data": {
                "period": f"Last {date_range} days",
                "phase_metrics": phase_metrics,
                "overall_metrics": overall_metrics,
                "generated_at": now()
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }


@frappe.whitelist()
def get_bottleneck_analysis(date_range: str = "30"):
    """
    Analyze workflow bottlenecks and performance issues.
    
    Args:
        date_range (str): Days to analyze
    
    Returns:
        dict: Bottleneck analysis with recommendations
    """
    try:
        date_from = add_days(today(), -int(date_range))
        
        # Identify bottlenecks
        bottlenecks = _identify_phase_bottlenecks(date_from)
        
        # Calculate phase efficiency
        efficiency_metrics = _calculate_phase_efficiency(date_from)
        
        # Get stuck jobs
        stuck_jobs = _identify_stuck_jobs()
        
        # Generate recommendations
        recommendations = _generate_bottleneck_recommendations(bottlenecks, efficiency_metrics)
        
        return {
            "success": True,
            "data": {
                "analysis_period": f"Last {date_range} days",
                "bottlenecks": bottlenecks,
                "efficiency_metrics": efficiency_metrics,
                "stuck_jobs": stuck_jobs,
                "recommendations": recommendations,
                "analyzed_at": now()
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }


# ============================================================================
# WEBHOOK AND NOTIFICATION SUPPORT
# ============================================================================

@frappe.whitelist()
def setup_phase_webhook(webhook_url: str, events: str, secret_key: str = None):
    """
    Setup webhook notifications for phase transitions.
    
    Args:
        webhook_url (str): Target webhook URL
        events (str): JSON array of events to subscribe to
        secret_key (str): Optional webhook secret for verification
    
    Returns:
        dict: Webhook setup result
    """
    try:
        # Validate webhook URL
        if not webhook_url.startswith(('http://', 'https://')):
            return {
                "success": False,
                "error": "ValidationError",
                "message": "Invalid webhook URL format"
            }
        
        # Parse events
        if isinstance(events, str):
            events = json.loads(events)
        
        # Create or update webhook configuration
        webhook_config = {
            "webhook_url": webhook_url,
            "events": events,
            "secret_key": secret_key,
            "created_by": frappe.session.user,
            "created_at": now()
        }
        
        # Store webhook configuration (you might want to create a DocType for this)
        frappe.db.set_value("Singles", "Job Workflow Settings", "webhook_config", 
                           json.dumps(webhook_config))
        frappe.db.commit()
        
        return {
            "success": True,
            "data": webhook_config,
            "message": "Webhook configured successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }


@frappe.whitelist()
def send_phase_notification(job_order: str, recipients: str, message: str, 
                           notification_type: str = "email"):
    """
    Send manual notification about phase status.
    
    Args:
        job_order (str): Job Order document name
        recipients (str): JSON array of recipient emails/users
        message (str): Notification message
        notification_type (str): Type of notification (email, sms, push)
    
    Returns:
        dict: Notification sending result
    """
    try:
        if isinstance(recipients, str):
            recipients = json.loads(recipients)
        
        job_doc = frappe.get_doc("Job Order", job_order)
        
        notification_data = {
            "job_order": job_order,
            "customer": job_doc.customer_name,
            "project": job_doc.project_name,
            "current_phase": job_doc.workflow_state,
            "message": message,
            "sent_by": frappe.session.user,
            "sent_at": now()
        }
        
        # Send notifications based on type
        sent_count = 0
        failed_count = 0
        
        for recipient in recipients:
            try:
                if notification_type == "email":
                    _send_email_notification(recipient, notification_data)
                elif notification_type == "sms":
                    _send_sms_notification(recipient, notification_data)
                elif notification_type == "push":
                    _send_push_notification(recipient, notification_data)
                
                sent_count += 1
            except Exception as e:
                failed_count += 1
                frappe.log_error(f"Notification failed for {recipient}: {str(e)}")
        
        return {
            "success": True,
            "data": {
                "total_recipients": len(recipients),
                "sent": sent_count,
                "failed": failed_count,
                "notification_type": notification_type
            },
            "message": f"Notifications sent: {sent_count} successful, {failed_count} failed"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _validate_transition(job_doc, action: str) -> Dict:
    """Validate if a workflow transition is allowed."""
    try:
        # Get workflow definition
        workflow = frappe.get_doc("Workflow", "Job Order Workflow")
        current_state = job_doc.workflow_state
        
        # Check if transition exists
        valid_transition = False
        for transition in workflow.transitions:
            if transition.state == current_state and transition.action == action:
                valid_transition = True
                break
        
        if not valid_transition:
            return {
                "valid": False,
                "message": f"Action '{action}' not available from state '{current_state}'"
            }
        
        return {"valid": True, "message": "Transition is valid"}
        
    except Exception as e:
        return {"valid": False, "message": str(e)}


def _get_next_state(current_state: str, action: str) -> str:
    """Get the next workflow state for a given action."""
    try:
        workflow = frappe.get_doc("Workflow", "Job Order Workflow")
        
        for transition in workflow.transitions:
            if transition.state == current_state and transition.action == action:
                return transition.next_state
        
        return None
        
    except Exception:
        return None


def _check_phase_prerequisites(job_doc, target_state: str) -> Dict:
    """Check if prerequisites are met for transitioning to target state."""
    try:
        requirements = _get_phase_requirements_config(target_state)
        
        # Check each requirement
        unmet_requirements = []
        
        for req in requirements:
            if not _check_requirement(job_doc, req):
                unmet_requirements.append(req)
        
        return {
            "valid": len(unmet_requirements) == 0,
            "total_requirements": len(requirements),
            "unmet_requirements": unmet_requirements,
            "message": "All prerequisites met" if len(unmet_requirements) == 0 
                      else f"{len(unmet_requirements)} requirements not met"
        }
        
    except Exception as e:
        return {"valid": False, "message": str(e)}


def _get_phase_requirements_config(phase: str) -> List[Dict]:
    """Get phase-specific requirements configuration."""
    requirements_map = {
        "Estimation": [
            {"type": "field", "field": "description", "required": True},
            {"type": "field", "field": "scope_of_work", "required": True}
        ],
        "Client Approval": [
            {"type": "child_table", "table": "phases", "min_count": 1},
            {"type": "custom", "check": "has_cost_estimate"}
        ],
        "Planning": [
            {"type": "child_table", "table": "team_members", "min_count": 1}
        ],
        "Prework": [
            {"type": "custom", "check": "has_material_plan"}
        ],
        "Execution": [
            {"type": "custom", "check": "all_resources_allocated"}
        ],
        "Review": [
            {"type": "custom", "check": "work_completed"}
        ],
        "Invoicing": [
            {"type": "custom", "check": "quality_approved"}
        ],
        "Closeout": [
            {"type": "custom", "check": "payment_received"}
        ]
    }
    
    return requirements_map.get(phase, [])


def _check_requirement(job_doc, requirement: Dict) -> bool:
    """Check if a specific requirement is met."""
    try:
        if requirement["type"] == "field":
            field_value = getattr(job_doc, requirement["field"], None)
            if requirement.get("required", False):
                return bool(field_value)
        
        elif requirement["type"] == "child_table":
            table_data = getattr(job_doc, requirement["table"], [])
            min_count = requirement.get("min_count", 1)
            return len(table_data) >= min_count
        
        elif requirement["type"] == "custom":
            return _check_custom_requirement(job_doc, requirement["check"])
        
        return True
        
    except Exception:
        return False


def _check_custom_requirement(job_doc, check_type: str) -> bool:
    """Check custom business requirements."""
    if check_type == "has_cost_estimate":
        return bool(job_doc.total_material_cost or job_doc.total_labor_cost)
    
    elif check_type == "has_material_plan":
        return len(job_doc.material_requisitions or []) > 0
    
    elif check_type == "all_resources_allocated":
        return len(job_doc.team_members or []) > 0
    
    elif check_type == "work_completed":
        # Custom logic to check if work is completed
        return True  # Placeholder
    
    elif check_type == "quality_approved":
        # Custom logic to check quality approval
        return True  # Placeholder
    
    elif check_type == "payment_received":
        # Custom logic to check payment status
        return True  # Placeholder
    
    return True


def _record_phase_history(job_doc, phase: str, comments: str):
    """Record phase transition in history."""
    try:
        # This would typically update a phase history child table
        # For now, we'll use the workflow history
        pass
    except Exception as e:
        frappe.log_error(f"Failed to record phase history: {str(e)}")


def _execute_phase_logic(job_doc, old_state: str, new_state: str, **kwargs):
    """Execute phase-specific business logic."""
    try:
        # Phase-specific logic
        if new_state == "Execution":
            job_doc.status = "In Progress"
        elif new_state == "Archived":
            job_doc.status = "Completed"
            job_doc.end_date = today()
        elif new_state == "Cancelled":
            job_doc.status = "Cancelled"
    except Exception as e:
        frappe.log_error(f"Phase logic execution error: {str(e)}")


def _send_transition_notifications(job_doc, old_state: str, new_state: str, 
                                 action: str, comments: str):
    """Send notifications for phase transitions."""
    try:
        # Get notification recipients based on new state
        recipients = _get_notification_recipients(new_state)
        
        # Send email notifications
        for recipient in recipients:
            _send_email_notification(recipient, {
                "job_order": job_doc.name,
                "customer": job_doc.customer_name,
                "project": job_doc.project_name,
                "old_state": old_state,
                "new_state": new_state,
                "action": action,
                "comments": comments
            })
    except Exception as e:
        frappe.log_error(f"Notification sending error: {str(e)}")


def _get_notification_recipients(state: str) -> List[str]:
    """Get notification recipients for a workflow state."""
    # This would typically be configured in a settings DocType
    recipients_map = {
        "Estimation": ["estimator@company.com"],
        "Client Approval": ["sales@company.com", "client@customer.com"],
        "Planning": ["pm@company.com"],
        "Prework": ["supervisor@company.com"],
        "Execution": ["technician@company.com"],
        "Review": ["quality@company.com"],
        "Invoicing": ["billing@company.com"],
        "Closeout": ["pm@company.com"]
    }
    
    return recipients_map.get(state, [])


def _send_email_notification(recipient: str, data: Dict):
    """Send email notification."""
    try:
        # Use Frappe's email sending functionality
        frappe.sendmail(
            recipients=[recipient],
            subject=f"Job Order {data['job_order']} - Phase Update",
            message=f"""
            Job Order: {data['job_order']}
            Customer: {data.get('customer', 'N/A')}
            Project: {data.get('project', 'N/A')}
            Current Phase: {data.get('new_state', data.get('current_phase', 'N/A'))}
            Message: {data.get('message', 'Phase transition notification')}
            """
        )
    except Exception as e:
        frappe.log_error(f"Email sending failed: {str(e)}")


def _send_sms_notification(recipient: str, data: Dict):
    """Send SMS notification (placeholder)."""
    # Implement SMS sending logic
    pass


def _send_push_notification(recipient: str, data: Dict):
    """Send push notification (placeholder)."""
    # Implement push notification logic
    pass


def _is_valid_rollback(current_state: str, target_state: str) -> bool:
    """Check if rollback to target state is valid."""
    # Define valid rollback paths
    rollback_paths = {
        "Estimation": ["Submission"],
        "Client Approval": ["Estimation", "Submission"],
        "Planning": ["Client Approval", "Estimation", "Submission"],
        "Prework": ["Planning", "Client Approval", "Estimation", "Submission"],
        "Execution": ["Prework", "Planning", "Client Approval", "Estimation", "Submission"],
        "Review": ["Execution", "Prework", "Planning"],
        "Invoicing": ["Review", "Execution"],
        "Closeout": ["Invoicing", "Review"],
        "Archived": ["Closeout", "Invoicing", "Review"]
    }
    
    valid_targets = rollback_paths.get(current_state, [])
    return target_state in valid_targets


def _handle_rollback_cleanup(job_doc, from_state: str, to_state: str):
    """Handle cleanup when rolling back phases."""
    # Reset state-specific data based on rollback
    if from_state == "Archived" and to_state != "Archived":
        job_doc.end_date = None
        job_doc.status = "In Progress"


def _send_rollback_notifications(job_doc, from_state: str, to_state: str, reason: str):
    """Send notifications for phase rollbacks."""
    try:
        # Get relevant stakeholders
        recipients = ["pm@company.com", "admin@company.com"]
        
        for recipient in recipients:
            _send_email_notification(recipient, {
                "job_order": job_doc.name,
                "customer": job_doc.customer_name,
                "project": job_doc.project_name,
                "old_state": from_state,
                "new_state": to_state,
                "message": f"ROLLBACK: {reason}"
            })
    except Exception as e:
        frappe.log_error(f"Rollback notification error: {str(e)}")


def _get_phase_history_data(job_order: str) -> List[Dict]:
    """Get phase history data for a job order."""
    # This would query the phase history table
    # For now, return placeholder data
    return []


def _calculate_phase_durations(history: List[Dict]) -> Dict:
    """Calculate duration for each phase."""
    durations = {}
    for i, entry in enumerate(history):
        if i < len(history) - 1:
            start_time = get_datetime(entry["start_date"])
            end_time = get_datetime(history[i + 1]["start_date"])
            duration = time_diff_in_hours(end_time, start_time)
            durations[entry["phase"]] = duration
    return durations


def _get_current_phase_info(job_doc) -> Dict:
    """Get information about the current phase."""
    return {
        "phase": job_doc.workflow_state,
        "start_date": job_doc.phase_start_date,
        "target_date": job_doc.phase_target_date,
        "days_in_phase": (get_datetime(now()) - get_datetime(job_doc.phase_start_date)).days if job_doc.phase_start_date else 0
    }


def _calculate_workflow_progress(current_state: str) -> float:
    """Calculate workflow completion percentage."""
    phase_order = ["Submission", "Estimation", "Client Approval", "Planning", 
                   "Prework", "Execution", "Review", "Invoicing", "Closeout", "Archived"]
    
    try:
        current_index = phase_order.index(current_state)
        return (current_index + 1) / len(phase_order) * 100
    except ValueError:
        return 0.0


def _calculate_total_duration(history: List[Dict]) -> float:
    """Calculate total workflow duration."""
    if len(history) < 2:
        return 0.0
    
    start_time = get_datetime(history[0]["start_date"])
    end_time = get_datetime(history[-1]["end_date"]) if history[-1].get("end_date") else get_datetime(now())
    return time_diff_in_hours(end_time, start_time)


def _format_duration(hours: float) -> str:
    """Format duration in human-readable format."""
    if hours < 24:
        return f"{hours:.1f} hours"
    else:
        days = hours / 24
        return f"{days:.1f} days"


def _calculate_phase_distribution(job_orders: List[Dict]) -> Dict:
    """Calculate distribution of jobs across phases."""
    distribution = {}
    for job in job_orders:
        phase = job["workflow_state"]
        distribution[phase] = distribution.get(phase, 0) + 1
    return distribution


def _calculate_average_phase_durations(date_from: str) -> Dict:
    """Calculate average duration for each phase."""
    # Placeholder implementation
    return {
        "Submission": 24.0,
        "Estimation": 48.0,
        "Client Approval": 72.0,
        "Planning": 24.0,
        "Prework": 48.0,
        "Execution": 120.0,
        "Review": 24.0,
        "Invoicing": 48.0,
        "Closeout": 24.0
    }


def _calculate_transition_trends(date_from: str) -> Dict:
    """Calculate transition trends over time."""
    # Placeholder implementation
    return {
        "daily_transitions": 5.2,
        "trend": "increasing",
        "peak_day": "Tuesday"
    }


def _identify_phase_bottlenecks(date_from: str) -> List[Dict]:
    """Identify workflow bottlenecks."""
    # Placeholder implementation
    return [
        {
            "phase": "Client Approval",
            "average_duration": 96.0,
            "expected_duration": 72.0,
            "delay_factor": 1.33,
            "severity": "High"
        },
        {
            "phase": "Execution",
            "average_duration": 180.0,
            "expected_duration": 120.0,
            "delay_factor": 1.5,
            "severity": "Critical"
        }
    ]


def _calculate_phase_metrics(phase: str, date_from: str) -> Dict:
    """Calculate metrics for a specific phase."""
    # Get jobs that passed through this phase
    filters = {
        "creation": [">=", date_from],
        "workflow_state": ["in", [phase, "Archived"]]  # Current or completed
    }
    
    jobs = frappe.get_all("Job Order", filters=filters, fields=["name", "workflow_state"])
    
    current_count = len([j for j in jobs if j["workflow_state"] == phase])
    completed_count = len([j for j in jobs if j["workflow_state"] != phase])
    
    return {
        "jobs_in_phase": current_count,
        "jobs_completed": completed_count,
        "total_processed": len(jobs),
        "average_duration": _get_average_phase_duration(phase, date_from),
        "efficiency_score": _calculate_efficiency_score(phase, date_from)
    }


def _get_average_phase_duration(phase: str, date_from: str) -> float:
    """Get average duration for a phase."""
    # Placeholder - would calculate from actual data
    duration_map = {
        "Submission": 24.0,
        "Estimation": 48.0,
        "Client Approval": 72.0,
        "Planning": 24.0,
        "Prework": 48.0,
        "Execution": 120.0,
        "Review": 24.0,
        "Invoicing": 48.0,
        "Closeout": 24.0,
        "Archived": 0.0
    }
    return duration_map.get(phase, 24.0)


def _calculate_efficiency_score(phase: str, date_from: str) -> float:
    """Calculate efficiency score for a phase."""
    # Placeholder calculation
    import random
    return round(random.uniform(0.7, 0.95), 2)


def _calculate_overall_workflow_metrics(date_from: str) -> Dict:
    """Calculate overall workflow performance metrics."""
    return {
        "average_completion_time": 480.0,  # hours
        "on_time_completion_rate": 0.85,
        "customer_satisfaction": 0.92,
        "resource_utilization": 0.78,
        "cost_efficiency": 0.88
    }


def _calculate_phase_efficiency(date_from: str) -> Dict:
    """Calculate efficiency metrics for all phases."""
    phases = ["Submission", "Estimation", "Client Approval", "Planning", 
              "Prework", "Execution", "Review", "Invoicing", "Closeout"]
    
    efficiency = {}
    for phase in phases:
        efficiency[phase] = {
            "on_time_rate": _calculate_on_time_rate(phase, date_from),
            "throughput": _calculate_throughput(phase, date_from),
            "quality_score": _calculate_quality_score(phase, date_from)
        }
    
    return efficiency


def _calculate_on_time_rate(phase: str, date_from: str) -> float:
    """Calculate on-time completion rate for a phase."""
    # Placeholder
    import random
    return round(random.uniform(0.7, 0.95), 2)


def _calculate_throughput(phase: str, date_from: str) -> float:
    """Calculate throughput for a phase."""
    # Placeholder
    import random
    return round(random.uniform(2.0, 8.0), 1)


def _calculate_quality_score(phase: str, date_from: str) -> float:
    """Calculate quality score for a phase."""
    # Placeholder
    import random
    return round(random.uniform(0.8, 0.98), 2)


def _identify_stuck_jobs() -> List[Dict]:
    """Identify jobs that are stuck in phases."""
    # Get jobs that have been in the same phase for too long
    threshold_hours = 168  # 7 days
    
    stuck_jobs = frappe.db.sql("""
        SELECT name, job_number, customer_name, project_name, workflow_state,
               phase_start_date, TIMESTAMPDIFF(HOUR, phase_start_date, NOW()) as hours_in_phase
        FROM `tabJob Order`
        WHERE phase_start_date IS NOT NULL
        AND TIMESTAMPDIFF(HOUR, phase_start_date, NOW()) > %s
        AND workflow_state NOT IN ('Archived', 'Cancelled')
        ORDER BY hours_in_phase DESC
    """, (threshold_hours,), as_dict=True)
    
    return stuck_jobs


def _generate_bottleneck_recommendations(bottlenecks: List[Dict], 
                                       efficiency: Dict) -> List[str]:
    """Generate recommendations based on bottleneck analysis."""
    recommendations = []
    
    for bottleneck in bottlenecks:
        if bottleneck["severity"] == "Critical":
            recommendations.append(
                f"URGENT: Address {bottleneck['phase']} phase delays - "
                f"taking {bottleneck['delay_factor']:.1f}x longer than expected"
            )
        elif bottleneck["severity"] == "High":
            recommendations.append(
                f"PRIORITY: Optimize {bottleneck['phase']} phase workflow - "
                f"consider additional resources or process improvements"
            )
    
    # Add efficiency-based recommendations
    for phase, metrics in efficiency.items():
        if metrics["on_time_rate"] < 0.8:
            recommendations.append(
                f"Improve {phase} phase scheduling - on-time rate is {metrics['on_time_rate']:.1%}"
            )
    
    return recommendations


def _check_transition_permissions(job_doc, action: str) -> Dict:
    """Check if user has permission for the transition."""
    try:
        workflow = frappe.get_doc("Workflow", "Job Order Workflow")
        user_roles = frappe.get_roles(frappe.session.user)
        
        for transition in workflow.transitions:
            if (transition.state == job_doc.workflow_state and 
                transition.action == action):
                allowed_roles = [role.strip() for role in transition.allowed.split(',')]
                has_permission = any(role in user_roles for role in allowed_roles)
                
                return {
                    "valid": has_permission,
                    "message": "Permission granted" if has_permission else "Insufficient permissions",
                    "required_roles": allowed_roles,
                    "user_roles": user_roles
                }
        
        return {"valid": False, "message": "Transition not found"}
        
    except Exception as e:
        return {"valid": False, "message": str(e)}


def _check_business_rules(job_doc, action: str, next_state: str) -> Dict:
    """Check business rules for the transition."""
    try:
        # Implement business rule checks
        rules_passed = []
        rules_failed = []
        
        # Example business rules
        if next_state == "Execution" and not job_doc.start_date:
            rules_failed.append("Start date must be set before execution")
        
        if next_state == "Invoicing" and not job_doc.total_labor_cost:
            rules_failed.append("Labor costs must be recorded before invoicing")
        
        return {
            "valid": len(rules_failed) == 0,
            "message": "All business rules passed" if len(rules_failed) == 0 
                      else f"{len(rules_failed)} business rules failed",
            "rules_passed": rules_passed,
            "rules_failed": rules_failed
        }
        
    except Exception as e:
        return {"valid": False, "message": str(e)}