# Copyright (c) 2025, API Next and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import today, add_days, now_datetime, date_diff, flt
import json
from datetime import datetime, timedelta


def get_context(context):
    """Get context data for the Job Order Dashboard page."""
    context.title = _("Job Order Dashboard")
    context.show_search = 1
    context.show_sidebar = 0
    
    # Get dashboard data
    context.dashboard_data = get_dashboard_overview()
    return context


@frappe.whitelist()
def get_dashboard_overview():
    """Get overview statistics for the Job Order Dashboard."""
    try:
        # Get basic counts
        total_jobs = frappe.db.count("Job Order")
        active_jobs = frappe.db.count("Job Order", {"status": ["!=", "Completed"]})
        completed_jobs = frappe.db.count("Job Order", {"status": "Completed"})
        
        # Get phase distribution
        phase_distribution = frappe.db.sql("""
            SELECT workflow_state, COUNT(*) as count
            FROM `tabJob Order`
            WHERE workflow_state IS NOT NULL
            GROUP BY workflow_state
            ORDER BY count DESC
        """, as_dict=True)
        
        # Get priority distribution
        priority_distribution = frappe.db.sql("""
            SELECT priority, COUNT(*) as count
            FROM `tabJob Order`
            WHERE priority IS NOT NULL
            GROUP BY priority
            ORDER BY 
                CASE priority
                    WHEN 'Urgent' THEN 1
                    WHEN 'High' THEN 2  
                    WHEN 'Medium' THEN 3
                    WHEN 'Low' THEN 4
                    ELSE 5
                END
        """, as_dict=True)
        
        # Get recent activity (last 30 days)
        thirty_days_ago = add_days(today(), -30)
        recent_jobs = frappe.db.sql("""
            SELECT name, job_number, customer_name, project_name, 
                   workflow_state, status, priority, creation,
                   total_material_cost, total_labor_cost
            FROM `tabJob Order`
            WHERE creation >= %s
            ORDER BY creation DESC
            LIMIT 10
        """, (thirty_days_ago,), as_dict=True)
        
        # Calculate financial metrics
        financial_metrics = get_financial_overview()
        
        # Get performance metrics
        performance_metrics = get_performance_metrics()
        
        # Get overdue jobs
        overdue_jobs = get_overdue_jobs()
        
        return {
            "success": True,
            "data": {
                "summary": {
                    "total_jobs": total_jobs,
                    "active_jobs": active_jobs,
                    "completed_jobs": completed_jobs,
                    "completion_rate": round((completed_jobs / total_jobs * 100) if total_jobs > 0 else 0, 1)
                },
                "phase_distribution": phase_distribution,
                "priority_distribution": priority_distribution,
                "recent_jobs": recent_jobs,
                "financial_metrics": financial_metrics,
                "performance_metrics": performance_metrics,
                "overdue_jobs": overdue_jobs,
                "last_updated": now_datetime()
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Dashboard overview error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "data": {}
        }


@frappe.whitelist()
def get_phase_timeline_data(limit=50, phase_filter=None):
    """Get timeline data for job order phases."""
    try:
        filters = {}
        if phase_filter:
            filters["workflow_state"] = phase_filter
        
        # Get job orders with phase timing
        jobs = frappe.get_all("Job Order",
            filters=filters,
            fields=[
                "name", "job_number", "customer_name", "project_name",
                "workflow_state", "status", "priority", "start_date", "end_date",
                "phase_start_date", "phase_target_date", "creation"
            ],
            limit=limit,
            order_by="phase_start_date desc"
        )
        
        # Calculate phase durations and status
        timeline_data = []
        for job in jobs:
            phase_duration = None
            is_overdue = False
            
            if job.get("phase_start_date"):
                if job.get("workflow_state") == "Archived" and job.get("end_date"):
                    # Completed job
                    phase_duration = date_diff(job.end_date, job.phase_start_date)
                else:
                    # Active job
                    phase_duration = date_diff(today(), job.phase_start_date)
                
                # Check if overdue
                if job.get("phase_target_date") and today() > job.phase_target_date:
                    is_overdue = True
            
            timeline_data.append({
                **job,
                "phase_duration_days": phase_duration,
                "is_overdue": is_overdue,
                "phase_progress": calculate_phase_progress(job.workflow_state)
            })
        
        return {
            "success": True,
            "data": timeline_data
        }
        
    except Exception as e:
        frappe.log_error(f"Timeline data error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist() 
def get_financial_overview():
    """Get financial overview for dashboard."""
    try:
        # Get total project values
        total_value = frappe.db.sql("""
            SELECT 
                SUM(IFNULL(total_material_cost, 0) + IFNULL(total_labor_cost, 0)) as total_value,
                SUM(CASE WHEN status = 'Completed' THEN 
                    IFNULL(total_material_cost, 0) + IFNULL(total_labor_cost, 0) 
                    ELSE 0 END) as completed_value,
                SUM(CASE WHEN status != 'Completed' THEN 
                    IFNULL(total_material_cost, 0) + IFNULL(total_labor_cost, 0) 
                    ELSE 0 END) as pending_value
            FROM `tabJob Order`
        """, as_dict=True)[0]
        
        # Monthly revenue trend (last 6 months)
        six_months_ago = add_days(today(), -180)
        monthly_revenue = frappe.db.sql("""
            SELECT 
                DATE_FORMAT(creation, '%%Y-%%m') as month,
                SUM(IFNULL(total_material_cost, 0) + IFNULL(total_labor_cost, 0)) as revenue
            FROM `tabJob Order`
            WHERE creation >= %s AND status = 'Completed'
            GROUP BY DATE_FORMAT(creation, '%%Y-%%m')
            ORDER BY month
        """, (six_months_ago,), as_dict=True)
        
        return {
            "total_value": flt(total_value.get("total_value", 0)),
            "completed_value": flt(total_value.get("completed_value", 0)),
            "pending_value": flt(total_value.get("pending_value", 0)),
            "monthly_revenue": monthly_revenue
        }
        
    except Exception as e:
        frappe.log_error(f"Financial overview error: {str(e)}")
        return {}


@frappe.whitelist()
def get_performance_metrics():
    """Get performance metrics for dashboard."""
    try:
        # Average job completion time
        avg_completion = frappe.db.sql("""
            SELECT AVG(DATEDIFF(end_date, start_date)) as avg_days
            FROM `tabJob Order`
            WHERE status = 'Completed' AND start_date IS NOT NULL AND end_date IS NOT NULL
        """, as_dict=True)[0]
        
        # On-time completion rate (last 30 days)
        thirty_days_ago = add_days(today(), -30)
        completion_stats = frappe.db.sql("""
            SELECT 
                COUNT(*) as total_completed,
                SUM(CASE WHEN end_date <= phase_target_date THEN 1 ELSE 0 END) as on_time_completed
            FROM `tabJob Order`
            WHERE status = 'Completed' 
            AND end_date >= %s
            AND phase_target_date IS NOT NULL
        """, (thirty_days_ago,), as_dict=True)[0]
        
        # Phase distribution efficiency
        phase_efficiency = frappe.db.sql("""
            SELECT 
                workflow_state,
                COUNT(*) as job_count,
                AVG(CASE WHEN phase_start_date IS NOT NULL 
                    THEN DATEDIFF(CURDATE(), phase_start_date) 
                    ELSE NULL END) as avg_days_in_phase
            FROM `tabJob Order`
            WHERE workflow_state IS NOT NULL
            AND workflow_state NOT IN ('Archived', 'Cancelled')
            GROUP BY workflow_state
        """, as_dict=True)
        
        on_time_rate = 0
        if completion_stats.get("total_completed", 0) > 0:
            on_time_rate = (completion_stats.get("on_time_completed", 0) / 
                           completion_stats.get("total_completed", 1)) * 100
        
        return {
            "avg_completion_days": flt(avg_completion.get("avg_days", 0)),
            "on_time_completion_rate": round(on_time_rate, 1),
            "total_completed_30days": completion_stats.get("total_completed", 0),
            "phase_efficiency": phase_efficiency
        }
        
    except Exception as e:
        frappe.log_error(f"Performance metrics error: {str(e)}")
        return {}


@frappe.whitelist()
def get_overdue_jobs():
    """Get jobs that are overdue or at risk."""
    try:
        overdue_jobs = frappe.db.sql("""
            SELECT 
                name, job_number, customer_name, project_name,
                workflow_state, priority, phase_target_date,
                DATEDIFF(CURDATE(), phase_target_date) as days_overdue
            FROM `tabJob Order`
            WHERE phase_target_date IS NOT NULL
            AND phase_target_date < CURDATE()
            AND workflow_state NOT IN ('Archived', 'Cancelled', 'Completed')
            ORDER BY days_overdue DESC
            LIMIT 10
        """, as_dict=True)
        
        # Jobs at risk (due within 3 days)
        at_risk_jobs = frappe.db.sql("""
            SELECT 
                name, job_number, customer_name, project_name,
                workflow_state, priority, phase_target_date,
                DATEDIFF(phase_target_date, CURDATE()) as days_remaining
            FROM `tabJob Order`
            WHERE phase_target_date IS NOT NULL
            AND phase_target_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 3 DAY)
            AND workflow_state NOT IN ('Archived', 'Cancelled', 'Completed')
            ORDER BY days_remaining ASC
            LIMIT 10
        """, as_dict=True)
        
        return {
            "overdue": overdue_jobs,
            "at_risk": at_risk_jobs
        }
        
    except Exception as e:
        frappe.log_error(f"Overdue jobs error: {str(e)}")
        return {"overdue": [], "at_risk": []}


def calculate_phase_progress(workflow_state):
    """Calculate progress percentage based on workflow phase."""
    phase_progress = {
        "Submission": 10,
        "Estimation": 20,
        "Client Approval": 30,
        "Planning": 40,
        "Prework": 50,
        "Execution": 70,
        "Review": 80,
        "Invoicing": 90,
        "Closeout": 95,
        "Archived": 100
    }
    return phase_progress.get(workflow_state, 0)


@frappe.whitelist()
def get_jobs_for_kanban(filters=None):
    """Get jobs formatted for Kanban board display."""
    try:
        # Parse filters
        if isinstance(filters, str):
            filters = json.loads(filters)
        
        filter_conditions = {}
        if filters:
            if filters.get("customer"):
                filter_conditions["customer_name"] = filters["customer"]
            if filters.get("priority"):
                filter_conditions["priority"] = filters["priority"] 
            if filters.get("date_range"):
                if filters["date_range"] == "this_month":
                    filter_conditions["creation"] = [">=", today().replace(day=1)]
                elif filters["date_range"] == "this_week":
                    filter_conditions["creation"] = [">=", add_days(today(), -7)]
        
        # Get jobs
        jobs = frappe.get_all("Job Order",
            filters=filter_conditions,
            fields=[
                "name", "job_number", "customer_name", "project_name",
                "workflow_state", "status", "priority", "start_date", "end_date",
                "phase_start_date", "phase_target_date", "total_material_cost", 
                "total_labor_cost", "creation"
            ],
            order_by="phase_start_date desc"
        )
        
        # Group by workflow state
        kanban_data = {}
        phases = ["Submission", "Estimation", "Client Approval", "Planning", 
                 "Prework", "Execution", "Review", "Invoicing", "Closeout", "Archived"]
        
        # Initialize phases
        for phase in phases:
            kanban_data[phase] = {
                "title": phase,
                "jobs": [],
                "count": 0,
                "total_value": 0
            }
        
        # Group jobs by phase
        for job in jobs:
            phase = job.get("workflow_state")
            if phase and phase in kanban_data:
                job_value = flt(job.get("total_material_cost", 0)) + flt(job.get("total_labor_cost", 0))
                
                kanban_data[phase]["jobs"].append({
                    **job,
                    "total_value": job_value,
                    "is_overdue": (job.get("phase_target_date") and 
                                  today() > job.phase_target_date),
                    "progress": calculate_phase_progress(phase)
                })
                kanban_data[phase]["count"] += 1
                kanban_data[phase]["total_value"] += job_value
        
        return {
            "success": True,
            "data": kanban_data
        }
        
    except Exception as e:
        frappe.log_error(f"Kanban data error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }