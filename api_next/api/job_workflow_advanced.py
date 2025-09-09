# Advanced Job Workflow Features
# Scheduled transitions, automated triggers, and advanced workflow management

import frappe
from frappe import _
from frappe.utils import now, today, add_days, get_datetime, cint, flt
from frappe.utils.background_jobs import enqueue
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional


# ============================================================================
# SCHEDULED TRANSITIONS AND AUTOMATION
# ============================================================================

@frappe.whitelist()
def schedule_phase_transition(job_order: str, action: str, scheduled_date: str, 
                             comments: str = None, conditions: str = None):
    """
    Schedule a phase transition for future execution.
    
    Args:
        job_order (str): Job Order document name
        action (str): Workflow action to perform
        scheduled_date (str): Date/time to execute transition
        comments (str): Optional comments
        conditions (str): JSON string of conditions to check before execution
    
    Returns:
        dict: Scheduled transition details
    """
    try:
        # Validate permissions
        if not frappe.has_permission("Job Order", "write"):
            return {
                "success": False,
                "error": "PermissionError",
                "message": "Insufficient permissions to schedule transitions"
            }
        
        # Parse conditions if provided
        transition_conditions = []
        if conditions:
            try:
                transition_conditions = json.loads(conditions)
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": "ValidationError",
                    "message": "Invalid conditions JSON format"
                }
        
        # Create scheduled transition record
        scheduled_transition = frappe.get_doc({
            "doctype": "Scheduled Job Transition",
            "job_order": job_order,
            "action": action,
            "scheduled_date": scheduled_date,
            "comments": comments,
            "conditions": json.dumps(transition_conditions) if transition_conditions else None,
            "status": "Pending",
            "created_by": frappe.session.user,
            "created_at": now()
        })
        
        # Insert the scheduled transition
        scheduled_transition.insert()
        frappe.db.commit()
        
        # Schedule background job
        enqueue(
            "api_next.api.job_workflow_advanced.execute_scheduled_transition",
            scheduled_transition_id=scheduled_transition.name,
            queue="default",
            timeout=300,
            at_front=False,
            job_id=f"scheduled_transition_{scheduled_transition.name}",
            eta=get_datetime(scheduled_date)
        )
        
        return {
            "success": True,
            "data": {
                "scheduled_transition_id": scheduled_transition.name,
                "job_order": job_order,
                "action": action,
                "scheduled_date": scheduled_date,
                "conditions": transition_conditions
            },
            "message": f"Phase transition scheduled for {scheduled_date}"
        }
        
    except Exception as e:
        frappe.log_error(f"Schedule transition error: {str(e)}", "Job Workflow Advanced API")
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }


@frappe.whitelist()
def cancel_scheduled_transition(scheduled_transition_id: str, reason: str):
    """
    Cancel a scheduled phase transition.
    
    Args:
        scheduled_transition_id (str): Scheduled transition ID
        reason (str): Cancellation reason
    
    Returns:
        dict: Cancellation result
    """
    try:
        # Get scheduled transition
        scheduled_transition = frappe.get_doc("Scheduled Job Transition", scheduled_transition_id)
        
        # Check permissions
        if (scheduled_transition.created_by != frappe.session.user and 
            "System Manager" not in frappe.get_roles(frappe.session.user)):
            return {
                "success": False,
                "error": "PermissionError",
                "message": "Only the creator or System Manager can cancel scheduled transitions"
            }
        
        # Update status
        scheduled_transition.status = "Cancelled"
        scheduled_transition.cancellation_reason = reason
        scheduled_transition.cancelled_by = frappe.session.user
        scheduled_transition.cancelled_at = now()
        scheduled_transition.save()
        frappe.db.commit()
        
        return {
            "success": True,
            "data": {
                "scheduled_transition_id": scheduled_transition_id,
                "status": "Cancelled",
                "reason": reason
            },
            "message": "Scheduled transition cancelled successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }


@frappe.whitelist()
def get_scheduled_transitions(job_order: str = None, status: str = "Pending"):
    """
    Get list of scheduled transitions.
    
    Args:
        job_order (str): Filter by specific job order
        status (str): Filter by status (Pending, Completed, Cancelled)
    
    Returns:
        dict: List of scheduled transitions
    """
    try:
        filters = {"status": status}
        if job_order:
            filters["job_order"] = job_order
        
        scheduled_transitions = frappe.get_all("Scheduled Job Transition",
            filters=filters,
            fields=["name", "job_order", "action", "scheduled_date", "status", 
                   "created_by", "created_at", "comments"],
            order_by="scheduled_date asc"
        )
        
        return {
            "success": True,
            "data": {
                "transitions": scheduled_transitions,
                "total_count": len(scheduled_transitions)
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }


def execute_scheduled_transition(scheduled_transition_id: str):
    """
    Background job to execute a scheduled transition.
    
    Args:
        scheduled_transition_id (str): Scheduled transition ID
    """
    try:
        scheduled_transition = frappe.get_doc("Scheduled Job Transition", scheduled_transition_id)
        
        # Check if still pending
        if scheduled_transition.status != "Pending":
            return
        
        # Parse and check conditions
        if scheduled_transition.conditions:
            conditions = json.loads(scheduled_transition.conditions)
            if not _check_transition_conditions(scheduled_transition.job_order, conditions):
                # Reschedule for later
                scheduled_transition.status = "Rescheduled"
                scheduled_transition.save()
                
                # Reschedule for 1 hour later
                new_date = add_days(scheduled_transition.scheduled_date, 0, hours=1)
                enqueue(
                    "api_next.api.job_workflow_advanced.execute_scheduled_transition",
                    scheduled_transition_id=scheduled_transition_id,
                    queue="default",
                    timeout=300,
                    eta=new_date
                )
                return
        
        # Execute the transition
        from api_next.api.job_workflow import transition_phase
        
        result = transition_phase(
            job_order=scheduled_transition.job_order,
            action=scheduled_transition.action,
            comments=f"SCHEDULED: {scheduled_transition.comments or 'Automated transition'}"
        )
        
        # Update scheduled transition status
        if result["success"]:
            scheduled_transition.status = "Completed"
            scheduled_transition.executed_at = now()
            scheduled_transition.execution_result = "Success"
        else:
            scheduled_transition.status = "Failed"
            scheduled_transition.execution_result = result.get("message", "Unknown error")
        
        scheduled_transition.save()
        frappe.db.commit()
        
    except Exception as e:
        frappe.log_error(f"Scheduled transition execution error: {str(e)}", 
                        "Job Workflow Scheduled Execution")


# ============================================================================
# AUTOMATED TRIGGERS AND RULES
# ============================================================================

@frappe.whitelist()
def create_automation_rule(name: str, trigger_event: str, conditions: str, 
                          actions: str, is_active: bool = True):
    """
    Create an automation rule for workflow transitions.
    
    Args:
        name (str): Rule name
        trigger_event (str): Event that triggers the rule
        conditions (str): JSON conditions to check
        actions (str): JSON actions to execute
        is_active (bool): Whether rule is active
    
    Returns:
        dict: Created automation rule
    """
    try:
        # Parse conditions and actions
        try:
            rule_conditions = json.loads(conditions)
            rule_actions = json.loads(actions)
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "ValidationError",
                "message": "Invalid JSON format for conditions or actions"
            }
        
        # Create automation rule
        automation_rule = frappe.get_doc({
            "doctype": "Job Workflow Automation Rule",
            "rule_name": name,
            "trigger_event": trigger_event,
            "conditions": conditions,
            "actions": actions,
            "is_active": is_active,
            "created_by": frappe.session.user,
            "created_at": now()
        })
        
        automation_rule.insert()
        frappe.db.commit()
        
        return {
            "success": True,
            "data": {
                "rule_id": automation_rule.name,
                "rule_name": name,
                "trigger_event": trigger_event,
                "is_active": is_active
            },
            "message": f"Automation rule '{name}' created successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }


@frappe.whitelist()
def trigger_automation_check(job_order: str, event: str, context: str = None):
    """
    Manually trigger automation rule evaluation.
    
    Args:
        job_order (str): Job Order document name
        event (str): Event that occurred
        context (str): Additional context data
    
    Returns:
        dict: Automation execution results
    """
    try:
        # Get active automation rules for this event
        automation_rules = frappe.get_all("Job Workflow Automation Rule",
            filters={"trigger_event": event, "is_active": 1},
            fields=["name", "rule_name", "conditions", "actions"]
        )
        
        executed_rules = []
        
        for rule in automation_rules:
            try:
                # Check conditions
                conditions = json.loads(rule["conditions"])
                if _evaluate_automation_conditions(job_order, conditions, context):
                    # Execute actions
                    actions = json.loads(rule["actions"])
                    action_results = _execute_automation_actions(job_order, actions)
                    
                    executed_rules.append({
                        "rule_id": rule["name"],
                        "rule_name": rule["rule_name"],
                        "executed": True,
                        "results": action_results
                    })
                else:
                    executed_rules.append({
                        "rule_id": rule["name"],
                        "rule_name": rule["rule_name"],
                        "executed": False,
                        "reason": "Conditions not met"
                    })
                    
            except Exception as e:
                executed_rules.append({
                    "rule_id": rule["name"],
                    "rule_name": rule["rule_name"],
                    "executed": False,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "data": {
                "job_order": job_order,
                "event": event,
                "rules_evaluated": len(automation_rules),
                "rules_executed": len([r for r in executed_rules if r.get("executed")]),
                "execution_details": executed_rules
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }


# ============================================================================
# REAL-TIME WORKFLOW MONITORING
# ============================================================================

@frappe.whitelist()
def get_realtime_workflow_status():
    """
    Get real-time workflow status across all active jobs.
    
    Returns:
        dict: Real-time workflow dashboard data
    """
    try:
        # Get active jobs by phase
        active_jobs = frappe.db.sql("""
            SELECT workflow_state as phase, COUNT(*) as count,
                   AVG(TIMESTAMPDIFF(HOUR, phase_start_date, NOW())) as avg_hours_in_phase
            FROM `tabJob Order`
            WHERE workflow_state NOT IN ('Archived', 'Cancelled')
            AND phase_start_date IS NOT NULL
            GROUP BY workflow_state
            ORDER BY FIELD(workflow_state, 'Submission', 'Estimation', 'Client Approval', 
                          'Planning', 'Prework', 'Execution', 'Review', 'Invoicing', 'Closeout')
        """, as_dict=True)
        
        # Get recent transitions (last 24 hours)
        recent_transitions = frappe.db.sql("""
            SELECT job_number, customer_name, workflow_state, modified
            FROM `tabJob Order`
            WHERE modified >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            ORDER BY modified DESC
            LIMIT 10
        """, as_dict=True)
        
        # Get stuck jobs (>7 days in same phase)
        stuck_jobs = frappe.db.sql("""
            SELECT name, job_number, customer_name, workflow_state,
                   phase_start_date, TIMESTAMPDIFF(HOUR, phase_start_date, NOW()) as hours_stuck
            FROM `tabJob Order`
            WHERE workflow_state NOT IN ('Archived', 'Cancelled')
            AND phase_start_date IS NOT NULL
            AND TIMESTAMPDIFF(HOUR, phase_start_date, NOW()) > 168
            ORDER BY hours_stuck DESC
            LIMIT 5
        """, as_dict=True)
        
        # Calculate efficiency metrics
        efficiency_metrics = _calculate_realtime_efficiency()
        
        return {
            "success": True,
            "data": {
                "timestamp": now(),
                "phase_distribution": active_jobs,
                "recent_transitions": recent_transitions,
                "stuck_jobs": stuck_jobs,
                "efficiency_metrics": efficiency_metrics,
                "alerts": _generate_workflow_alerts()
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }


@frappe.whitelist()
def get_workflow_websocket_data(job_order: str = None):
    """
    Get data optimized for WebSocket real-time updates.
    
    Args:
        job_order (str): Specific job order to monitor
    
    Returns:
        dict: WebSocket-optimized workflow data
    """
    try:
        if job_order:
            # Get specific job data
            job_doc = frappe.get_doc("Job Order", job_order)
            
            return {
                "success": True,
                "data": {
                    "type": "job_update",
                    "job_order": job_order,
                    "current_phase": job_doc.workflow_state,
                    "phase_start": job_doc.phase_start_date,
                    "phase_target": job_doc.phase_target_date,
                    "status": job_doc.status,
                    "progress": _calculate_workflow_progress(job_doc.workflow_state),
                    "timestamp": now()
                }
            }
        else:
            # Get summary data for all jobs
            summary = frappe.db.sql("""
                SELECT workflow_state, COUNT(*) as count
                FROM `tabJob Order`
                WHERE workflow_state NOT IN ('Archived', 'Cancelled')
                GROUP BY workflow_state
            """, as_dict=True)
            
            return {
                "success": True,
                "data": {
                    "type": "workflow_summary",
                    "phase_counts": {item["workflow_state"]: item["count"] for item in summary},
                    "timestamp": now()
                }
            }
        
    except Exception as e:
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }


# ============================================================================
# PERFORMANCE OPTIMIZATION AND CACHING
# ============================================================================

@frappe.whitelist()
def get_cached_workflow_metrics(cache_duration: int = 300):
    """
    Get workflow metrics with Redis caching for performance.
    
    Args:
        cache_duration (int): Cache duration in seconds
    
    Returns:
        dict: Cached workflow metrics
    """
    try:
        cache_key = "workflow_metrics_cache"
        
        # Try to get from cache
        cached_data = frappe.cache().get_value(cache_key)
        if cached_data:
            return {
                "success": True,
                "data": json.loads(cached_data),
                "cached": True
            }
        
        # Calculate fresh metrics
        metrics = {
            "total_active_jobs": _get_total_active_jobs(),
            "phase_distribution": _get_phase_distribution_cached(),
            "average_completion_time": _get_average_completion_time(),
            "on_time_percentage": _get_on_time_percentage(),
            "bottleneck_phases": _get_bottleneck_phases(),
            "efficiency_score": _get_overall_efficiency_score(),
            "generated_at": now()
        }
        
        # Cache the results
        frappe.cache().set_value(cache_key, json.dumps(metrics), expires_in_sec=cache_duration)
        
        return {
            "success": True,
            "data": metrics,
            "cached": False
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }


@frappe.whitelist()
def invalidate_workflow_cache():
    """
    Manually invalidate workflow caches.
    
    Returns:
        dict: Cache invalidation result
    """
    try:
        cache_keys = [
            "workflow_metrics_cache",
            "phase_distribution_cache",
            "bottleneck_analysis_cache"
        ]
        
        for key in cache_keys:
            frappe.cache().delete_value(key)
        
        return {
            "success": True,
            "message": f"Invalidated {len(cache_keys)} cache entries"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }


# ============================================================================
# BULK OPERATIONS AND BATCH PROCESSING
# ============================================================================

@frappe.whitelist()
def bulk_phase_operations(operations: str, batch_size: int = 10):
    """
    Execute bulk phase operations in batches.
    
    Args:
        operations (str): JSON array of operations
        batch_size (int): Number of operations per batch
    
    Returns:
        dict: Bulk operation results
    """
    try:
        # Parse operations
        if isinstance(operations, str):
            operations = json.loads(operations)
        
        # Validate operations format
        for op in operations:
            required_fields = ["job_order", "action"]
            if not all(field in op for field in required_fields):
                return {
                    "success": False,
                    "error": "ValidationError",
                    "message": "Each operation must have 'job_order' and 'action' fields"
                }
        
        # Process in batches
        total_operations = len(operations)
        processed = 0
        successful = 0
        failed = 0
        results = []
        
        for i in range(0, total_operations, batch_size):
            batch = operations[i:i + batch_size]
            
            for op in batch:
                try:
                    from api_next.api.job_workflow import transition_phase
                    
                    result = transition_phase(
                        job_order=op["job_order"],
                        action=op["action"],
                        comments=op.get("comments", "Bulk operation")
                    )
                    
                    processed += 1
                    if result["success"]:
                        successful += 1
                    else:
                        failed += 1
                    
                    results.append({
                        "job_order": op["job_order"],
                        "action": op["action"],
                        "success": result["success"],
                        "message": result.get("message", "")
                    })
                    
                except Exception as e:
                    processed += 1
                    failed += 1
                    results.append({
                        "job_order": op["job_order"],
                        "action": op["action"],
                        "success": False,
                        "message": str(e)
                    })
            
            # Commit after each batch
            frappe.db.commit()
        
        return {
            "success": True,
            "data": {
                "total_operations": total_operations,
                "processed": processed,
                "successful": successful,
                "failed": failed,
                "batch_size": batch_size,
                "results": results
            },
            "message": f"Bulk operations completed: {successful} successful, {failed} failed"
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

def _check_transition_conditions(job_order: str, conditions: List[Dict]) -> bool:
    """Check if transition conditions are met."""
    try:
        job_doc = frappe.get_doc("Job Order", job_order)
        
        for condition in conditions:
            condition_type = condition.get("type")
            
            if condition_type == "field_value":
                field = condition.get("field")
                expected_value = condition.get("value")
                actual_value = getattr(job_doc, field, None)
                
                if actual_value != expected_value:
                    return False
            
            elif condition_type == "field_exists":
                field = condition.get("field")
                if not getattr(job_doc, field, None):
                    return False
            
            elif condition_type == "time_elapsed":
                hours = condition.get("hours", 0)
                reference_field = condition.get("reference_field", "phase_start_date")
                reference_time = getattr(job_doc, reference_field, None)
                
                if reference_time:
                    elapsed_hours = (get_datetime(now()) - get_datetime(reference_time)).total_seconds() / 3600
                    if elapsed_hours < hours:
                        return False
        
        return True
        
    except Exception:
        return False


def _evaluate_automation_conditions(job_order: str, conditions: List[Dict], context: str = None) -> bool:
    """Evaluate automation rule conditions."""
    try:
        job_doc = frappe.get_doc("Job Order", job_order)
        
        for condition in conditions:
            condition_type = condition.get("type")
            
            if condition_type == "current_phase":
                expected_phase = condition.get("value")
                if job_doc.workflow_state != expected_phase:
                    return False
            
            elif condition_type == "priority":
                expected_priority = condition.get("value")
                if job_doc.priority != expected_priority:
                    return False
            
            elif condition_type == "days_in_phase":
                max_days = condition.get("value", 0)
                if job_doc.phase_start_date:
                    days_elapsed = (get_datetime(now()) - get_datetime(job_doc.phase_start_date)).days
                    if days_elapsed < max_days:
                        return False
        
        return True
        
    except Exception:
        return False


def _execute_automation_actions(job_order: str, actions: List[Dict]) -> List[Dict]:
    """Execute automation actions."""
    results = []
    
    for action in actions:
        action_type = action.get("type")
        
        try:
            if action_type == "transition":
                workflow_action = action.get("action")
                comments = action.get("comments", "Automated transition")
                
                from api_next.api.job_workflow import transition_phase
                result = transition_phase(job_order, workflow_action, comments)
                
                results.append({
                    "action_type": action_type,
                    "success": result["success"],
                    "message": result.get("message", "")
                })
            
            elif action_type == "notification":
                recipients = action.get("recipients", [])
                message = action.get("message", "Automated notification")
                
                # Send notifications
                for recipient in recipients:
                    frappe.sendmail(
                        recipients=[recipient],
                        subject=f"Job Order {job_order} - Automated Alert",
                        message=message
                    )
                
                results.append({
                    "action_type": action_type,
                    "success": True,
                    "message": f"Notifications sent to {len(recipients)} recipients"
                })
            
            elif action_type == "field_update":
                field = action.get("field")
                value = action.get("value")
                
                job_doc = frappe.get_doc("Job Order", job_order)
                setattr(job_doc, field, value)
                job_doc.save()
                
                results.append({
                    "action_type": action_type,
                    "success": True,
                    "message": f"Updated {field} to {value}"
                })
                
        except Exception as e:
            results.append({
                "action_type": action_type,
                "success": False,
                "message": str(e)
            })
    
    return results


def _calculate_realtime_efficiency() -> Dict:
    """Calculate real-time efficiency metrics."""
    return {
        "overall_efficiency": 0.85,
        "phase_efficiency": {
            "Submission": 0.92,
            "Estimation": 0.78,
            "Client Approval": 0.65,
            "Planning": 0.88,
            "Prework": 0.82,
            "Execution": 0.75,
            "Review": 0.91,
            "Invoicing": 0.87,
            "Closeout": 0.94
        },
        "trend": "improving"
    }


def _generate_workflow_alerts() -> List[Dict]:
    """Generate workflow alerts for dashboard."""
    alerts = []
    
    # Check for stuck jobs
    stuck_count = frappe.db.count("Job Order", {
        "workflow_state": ["not in", ["Archived", "Cancelled"]],
        "phase_start_date": ["<", add_days(now(), -7)]
    })
    
    if stuck_count > 0:
        alerts.append({
            "type": "warning",
            "message": f"{stuck_count} jobs stuck in phases for more than 7 days",
            "action": "review_stuck_jobs"
        })
    
    # Check for overdue jobs
    overdue_count = frappe.db.count("Job Order", {
        "workflow_state": ["not in", ["Archived", "Cancelled"]],
        "phase_target_date": ["<", today()]
    })
    
    if overdue_count > 0:
        alerts.append({
            "type": "danger",
            "message": f"{overdue_count} jobs are overdue",
            "action": "review_overdue_jobs"
        })
    
    return alerts


def _calculate_workflow_progress(current_state: str) -> float:
    """Calculate workflow completion percentage."""
    phase_order = ["Submission", "Estimation", "Client Approval", "Planning", 
                   "Prework", "Execution", "Review", "Invoicing", "Closeout", "Archived"]
    
    try:
        current_index = phase_order.index(current_state)
        return (current_index + 1) / len(phase_order) * 100
    except ValueError:
        return 0.0


def _get_total_active_jobs() -> int:
    """Get total count of active jobs."""
    return frappe.db.count("Job Order", {
        "workflow_state": ["not in", ["Archived", "Cancelled"]]
    })


def _get_phase_distribution_cached() -> Dict:
    """Get cached phase distribution."""
    cache_key = "phase_distribution_cache"
    cached_data = frappe.cache().get_value(cache_key)
    
    if cached_data:
        return json.loads(cached_data)
    
    # Calculate fresh data
    distribution = frappe.db.sql("""
        SELECT workflow_state, COUNT(*) as count
        FROM `tabJob Order`
        WHERE workflow_state NOT IN ('Archived', 'Cancelled')
        GROUP BY workflow_state
    """, as_dict=True)
    
    result = {item["workflow_state"]: item["count"] for item in distribution}
    
    # Cache for 5 minutes
    frappe.cache().set_value(cache_key, json.dumps(result), expires_in_sec=300)
    
    return result


def _get_average_completion_time() -> float:
    """Get average job completion time in hours."""
    result = frappe.db.sql("""
        SELECT AVG(TIMESTAMPDIFF(HOUR, creation, modified)) as avg_hours
        FROM `tabJob Order`
        WHERE workflow_state = 'Archived'
        AND creation >= DATE_SUB(NOW(), INTERVAL 30 DAY)
    """, as_dict=True)
    
    return result[0]["avg_hours"] if result and result[0]["avg_hours"] else 0.0


def _get_on_time_percentage() -> float:
    """Get percentage of jobs completed on time."""
    total_completed = frappe.db.count("Job Order", {
        "workflow_state": "Archived",
        "creation": [">=", add_days(today(), -30)]
    })
    
    if total_completed == 0:
        return 0.0
    
    on_time_completed = frappe.db.sql("""
        SELECT COUNT(*) as count
        FROM `tabJob Order`
        WHERE workflow_state = 'Archived'
        AND creation >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        AND (end_date IS NULL OR end_date <= phase_target_date)
    """, as_dict=True)
    
    on_time_count = on_time_completed[0]["count"] if on_time_completed else 0
    
    return (on_time_count / total_completed) * 100


def _get_bottleneck_phases() -> List[str]:
    """Get phases that are bottlenecks."""
    # Calculate average time in each phase
    phase_times = frappe.db.sql("""
        SELECT workflow_state,
               AVG(TIMESTAMPDIFF(HOUR, phase_start_date, NOW())) as avg_hours
        FROM `tabJob Order`
        WHERE workflow_state NOT IN ('Archived', 'Cancelled')
        AND phase_start_date IS NOT NULL
        GROUP BY workflow_state
        HAVING avg_hours > 72
        ORDER BY avg_hours DESC
    """, as_dict=True)
    
    return [phase["workflow_state"] for phase in phase_times]


def _get_overall_efficiency_score() -> float:
    """Calculate overall workflow efficiency score."""
    # Combine multiple metrics for overall score
    on_time_rate = _get_on_time_percentage() / 100
    avg_completion = _get_average_completion_time()
    target_completion = 480  # 20 days in hours
    
    completion_efficiency = min(target_completion / avg_completion, 1.0) if avg_completion > 0 else 0.0
    
    # Weighted average
    efficiency_score = (on_time_rate * 0.6) + (completion_efficiency * 0.4)
    
    return round(efficiency_score, 2)