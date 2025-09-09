# Job Order Dashboard API Endpoints
# Comprehensive dashboard data and analytics endpoints

import frappe
from frappe import _
from frappe.utils import today, add_days, now_datetime, date_diff, flt, cint
import json
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional


@frappe.whitelist()
def get_calendar_events(start_date=None, end_date=None, view_type="month"):
    """Get job order events for calendar display."""
    try:
        if not start_date:
            start_date = today()
        if not end_date:
            if view_type == "month":
                end_date = add_days(start_date, 30)
            elif view_type == "week":
                end_date = add_days(start_date, 7)
            else:
                end_date = add_days(start_date, 1)
        
        # Get jobs with dates in the range
        events = frappe.db.sql("""
            SELECT 
                name, job_number, customer_name, project_name,
                workflow_state, priority, status,
                start_date, end_date, phase_start_date, phase_target_date,
                total_material_cost, total_labor_cost
            FROM `tabJob Order`
            WHERE (
                (start_date BETWEEN %s AND %s) OR
                (end_date BETWEEN %s AND %s) OR  
                (phase_target_date BETWEEN %s AND %s) OR
                (start_date <= %s AND end_date >= %s)
            )
            AND workflow_state NOT IN ('Cancelled')
            ORDER BY start_date, phase_start_date
        """, (start_date, end_date, start_date, end_date, 
              start_date, end_date, start_date, end_date), as_dict=True)
        
        # Format events for calendar
        calendar_events = []
        for job in events:
            # Job start event
            if job.get("start_date"):
                calendar_events.append({
                    "id": f"start_{job.name}",
                    "title": f"Start: {job.job_number} - {job.project_name}",
                    "start": job.start_date.isoformat() if job.start_date else None,
                    "end": job.start_date.isoformat() if job.start_date else None,
                    "allDay": True,
                    "className": f"event-start priority-{job.priority.lower() if job.priority else 'medium'}",
                    "extendedProps": {
                        "type": "start",
                        "job": job.name,
                        "customer": job.customer_name,
                        "phase": job.workflow_state,
                        "priority": job.priority
                    }
                })
            
            # Job end event  
            if job.get("end_date"):
                calendar_events.append({
                    "id": f"end_{job.name}",
                    "title": f"End: {job.job_number} - {job.project_name}",
                    "start": job.end_date.isoformat() if job.end_date else None,
                    "end": job.end_date.isoformat() if job.end_date else None,
                    "allDay": True,
                    "className": f"event-end priority-{job.priority.lower() if job.priority else 'medium'}",
                    "extendedProps": {
                        "type": "end",
                        "job": job.name,
                        "customer": job.customer_name,
                        "phase": job.workflow_state,
                        "priority": job.priority
                    }
                })
            
            # Phase target date
            if job.get("phase_target_date"):
                is_overdue = job.phase_target_date < date.today()
                calendar_events.append({
                    "id": f"phase_{job.name}",
                    "title": f"Phase Due: {job.job_number} - {job.workflow_state}",
                    "start": job.phase_target_date.isoformat(),
                    "end": job.phase_target_date.isoformat(),
                    "allDay": True,
                    "className": f"event-phase {'overdue' if is_overdue else ''} priority-{job.priority.lower() if job.priority else 'medium'}",
                    "extendedProps": {
                        "type": "phase_due",
                        "job": job.name,
                        "customer": job.customer_name,
                        "phase": job.workflow_state,
                        "priority": job.priority,
                        "overdue": is_overdue
                    }
                })
        
        return {
            "success": True,
            "data": calendar_events
        }
        
    except Exception as e:
        frappe.log_error(f"Calendar events error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def get_advanced_job_list(filters=None, sort_by="creation", sort_order="desc", 
                         page=1, limit=20, search=""):
    """Get advanced job list with filtering, sorting and pagination."""
    try:
        # Parse filters
        if isinstance(filters, str):
            filters = json.loads(filters)
        
        # Build filter conditions
        filter_conditions = []
        filter_values = []
        
        if filters:
            if filters.get("phase"):
                filter_conditions.append("workflow_state = %s")
                filter_values.append(filters["phase"])
            
            if filters.get("priority"):
                filter_conditions.append("priority = %s")
                filter_values.append(filters["priority"])
            
            if filters.get("customer"):
                filter_conditions.append("customer_name LIKE %s")
                filter_values.append(f"%{filters['customer']}%")
            
            if filters.get("status"):
                filter_conditions.append("status = %s")
                filter_values.append(filters["status"])
            
            if filters.get("date_from"):
                filter_conditions.append("creation >= %s")
                filter_values.append(filters["date_from"])
            
            if filters.get("date_to"):
                filter_conditions.append("creation <= %s")
                filter_values.append(filters["date_to"])
        
        # Add search condition
        if search:
            search_condition = """(
                job_number LIKE %s OR 
                customer_name LIKE %s OR 
                project_name LIKE %s OR
                description LIKE %s
            )"""
            filter_conditions.append(search_condition)
            search_term = f"%{search}%"
            filter_values.extend([search_term, search_term, search_term, search_term])
        
        # Build WHERE clause
        where_clause = ""
        if filter_conditions:
            where_clause = "WHERE " + " AND ".join(filter_conditions)
        
        # Validate sort parameters
        valid_sort_fields = [
            "creation", "job_number", "customer_name", "project_name",
            "workflow_state", "priority", "start_date", "end_date", "status"
        ]
        if sort_by not in valid_sort_fields:
            sort_by = "creation"
        
        if sort_order.lower() not in ["asc", "desc"]:
            sort_order = "desc"
        
        # Calculate pagination
        offset = (cint(page) - 1) * cint(limit)
        
        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM `tabJob Order`
            {where_clause}
        """
        total_count = frappe.db.sql(count_query, filter_values, as_dict=True)[0]["total"]
        
        # Get jobs
        jobs_query = f"""
            SELECT 
                name, job_number, customer_name, project_name, description,
                workflow_state, status, priority, start_date, end_date,
                phase_start_date, phase_target_date, creation, modified,
                total_material_cost, total_labor_cost,
                CASE 
                    WHEN phase_target_date IS NOT NULL AND phase_target_date < CURDATE()
                    THEN 1 ELSE 0 
                END as is_overdue
            FROM `tabJob Order`
            {where_clause}
            ORDER BY {sort_by} {sort_order}
            LIMIT {limit} OFFSET {offset}
        """
        
        jobs = frappe.db.sql(jobs_query, filter_values, as_dict=True)
        
        # Enrich job data
        for job in jobs:
            job["total_value"] = flt(job.get("total_material_cost", 0)) + flt(job.get("total_labor_cost", 0))
            job["progress"] = calculate_phase_progress(job.get("workflow_state"))
            
            # Calculate days in current phase
            if job.get("phase_start_date"):
                job["days_in_phase"] = date_diff(today(), job.phase_start_date)
            else:
                job["days_in_phase"] = 0
        
        # Calculate pagination info
        total_pages = (total_count + cint(limit) - 1) // cint(limit)
        
        return {
            "success": True,
            "data": {
                "jobs": jobs,
                "pagination": {
                    "current_page": cint(page),
                    "total_pages": total_pages,
                    "total_count": total_count,
                    "limit": cint(limit),
                    "has_next": cint(page) < total_pages,
                    "has_prev": cint(page) > 1
                }
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Advanced job list error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def get_analytics_data(period="30", chart_type="all"):
    """Get comprehensive analytics data for dashboard charts."""
    try:
        period_days = cint(period)
        date_from = add_days(today(), -period_days)
        
        analytics_data = {}
        
        if chart_type in ["all", "phase_duration"]:
            analytics_data["phase_duration"] = get_phase_duration_analytics(date_from)
        
        if chart_type in ["all", "revenue_trend"]:
            analytics_data["revenue_trend"] = get_revenue_trend_analytics(date_from)
        
        if chart_type in ["all", "bottleneck"]:
            analytics_data["bottleneck"] = get_bottleneck_analytics(date_from)
        
        if chart_type in ["all", "customer_performance"]:
            analytics_data["customer_performance"] = get_customer_performance_analytics(date_from)
        
        if chart_type in ["all", "resource_utilization"]:
            analytics_data["resource_utilization"] = get_resource_utilization_analytics(date_from)
        
        return {
            "success": True,
            "data": analytics_data,
            "period": period_days,
            "date_from": date_from
        }
        
    except Exception as e:
        frappe.log_error(f"Analytics data error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


def get_phase_duration_analytics(date_from):
    """Get phase duration analytics."""
    try:
        # Get phase durations from workflow history
        phase_durations = frappe.db.sql("""
            SELECT 
                workflow_state as phase,
                AVG(CASE WHEN phase_start_date IS NOT NULL AND end_date IS NOT NULL
                    THEN DATEDIFF(end_date, phase_start_date)
                    WHEN phase_start_date IS NOT NULL 
                    THEN DATEDIFF(CURDATE(), phase_start_date)
                    ELSE NULL END) as avg_duration,
                COUNT(*) as job_count
            FROM `tabJob Order`
            WHERE creation >= %s
            AND workflow_state IS NOT NULL
            GROUP BY workflow_state
            ORDER BY avg_duration DESC
        """, (date_from,), as_dict=True)
        
        return {
            "labels": [d["phase"] for d in phase_durations],
            "data": [flt(d["avg_duration"]) for d in phase_durations],
            "job_counts": [d["job_count"] for d in phase_durations]
        }
        
    except Exception as e:
        frappe.log_error(f"Phase duration analytics error: {str(e)}")
        return {"labels": [], "data": [], "job_counts": []}


def get_revenue_trend_analytics(date_from):
    """Get revenue trend analytics."""
    try:
        # Get monthly revenue data
        revenue_data = frappe.db.sql("""
            SELECT 
                DATE_FORMAT(creation, '%%Y-%%m') as month,
                SUM(IFNULL(total_material_cost, 0) + IFNULL(total_labor_cost, 0)) as revenue,
                COUNT(*) as job_count
            FROM `tabJob Order`
            WHERE creation >= %s
            GROUP BY DATE_FORMAT(creation, '%%Y-%%m')
            ORDER BY month
        """, (date_from,), as_dict=True)
        
        return {
            "labels": [d["month"] for d in revenue_data],
            "revenue": [flt(d["revenue"]) for d in revenue_data],
            "job_counts": [d["job_count"] for d in revenue_data]
        }
        
    except Exception as e:
        frappe.log_error(f"Revenue trend analytics error: {str(e)}")
        return {"labels": [], "revenue": [], "job_counts": []}


def get_bottleneck_analytics(date_from):
    """Get bottleneck analytics."""
    try:
        # Identify phases with longest durations and highest job counts
        bottlenecks = frappe.db.sql("""
            SELECT 
                workflow_state as phase,
                COUNT(*) as jobs_in_phase,
                AVG(CASE WHEN phase_start_date IS NOT NULL 
                    THEN DATEDIFF(CURDATE(), phase_start_date)
                    ELSE 0 END) as avg_days_in_phase,
                SUM(CASE WHEN phase_target_date IS NOT NULL AND CURDATE() > phase_target_date
                    THEN 1 ELSE 0 END) as overdue_jobs
            FROM `tabJob Order`
            WHERE creation >= %s
            AND workflow_state IS NOT NULL
            AND workflow_state NOT IN ('Archived', 'Cancelled')
            GROUP BY workflow_state
            HAVING jobs_in_phase > 0
            ORDER BY avg_days_in_phase DESC, jobs_in_phase DESC
        """, (date_from,), as_dict=True)
        
        # Calculate bottleneck scores
        for bottleneck in bottlenecks:
            avg_days = flt(bottleneck["avg_days_in_phase"])
            job_count = bottleneck["jobs_in_phase"]
            overdue_count = bottleneck["overdue_jobs"]
            
            # Simple bottleneck score: (avg_days * job_count) + (overdue_count * 10)
            bottleneck["bottleneck_score"] = (avg_days * job_count) + (overdue_count * 10)
            
            # Severity rating
            if bottleneck["bottleneck_score"] > 100:
                bottleneck["severity"] = "Critical"
            elif bottleneck["bottleneck_score"] > 50:
                bottleneck["severity"] = "High" 
            elif bottleneck["bottleneck_score"] > 20:
                bottleneck["severity"] = "Medium"
            else:
                bottleneck["severity"] = "Low"
        
        return bottlenecks[:10]  # Top 10 bottlenecks
        
    except Exception as e:
        frappe.log_error(f"Bottleneck analytics error: {str(e)}")
        return []


def get_customer_performance_analytics(date_from):
    """Get customer performance analytics."""
    try:
        customer_data = frappe.db.sql("""
            SELECT 
                customer_name,
                COUNT(*) as total_jobs,
                SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed_jobs,
                SUM(IFNULL(total_material_cost, 0) + IFNULL(total_labor_cost, 0)) as total_value,
                AVG(CASE WHEN status = 'Completed' AND start_date IS NOT NULL AND end_date IS NOT NULL
                    THEN DATEDIFF(end_date, start_date) ELSE NULL END) as avg_duration
            FROM `tabJob Order`
            WHERE creation >= %s
            AND customer_name IS NOT NULL
            GROUP BY customer_name
            HAVING total_jobs > 0
            ORDER BY total_value DESC
            LIMIT 10
        """, (date_from,), as_dict=True)
        
        # Calculate completion rates
        for customer in customer_data:
            total = customer["total_jobs"]
            completed = customer["completed_jobs"]
            customer["completion_rate"] = (completed / total * 100) if total > 0 else 0
        
        return {
            "labels": [c["customer_name"] for c in customer_data],
            "total_jobs": [c["total_jobs"] for c in customer_data],
            "completion_rates": [flt(c["completion_rate"]) for c in customer_data],
            "total_values": [flt(c["total_value"]) for c in customer_data]
        }
        
    except Exception as e:
        frappe.log_error(f"Customer performance analytics error: {str(e)}")
        return {"labels": [], "total_jobs": [], "completion_rates": [], "total_values": []}


def get_resource_utilization_analytics(date_from):
    """Get resource utilization analytics."""
    try:
        # This would typically pull from resource allocation tables
        # For now, providing sample structure
        utilization_data = frappe.db.sql("""
            SELECT 
                workflow_state as phase,
                COUNT(DISTINCT customer_name) as customers_served,
                SUM(IFNULL(total_labor_hours, 0)) as total_labor_hours,
                AVG(IFNULL(total_labor_hours, 0)) as avg_labor_hours
            FROM `tabJob Order`
            WHERE creation >= %s
            AND workflow_state IS NOT NULL
            GROUP BY workflow_state
            ORDER BY total_labor_hours DESC
        """, (date_from,), as_dict=True)
        
        return {
            "phases": [d["phase"] for d in utilization_data],
            "labor_hours": [flt(d["total_labor_hours"]) for d in utilization_data],
            "customers_served": [d["customers_served"] for d in utilization_data]
        }
        
    except Exception as e:
        frappe.log_error(f"Resource utilization analytics error: {str(e)}")
        return {"phases": [], "labor_hours": [], "customers_served": []}


@frappe.whitelist() 
def get_job_detail(job_name):
    """Get detailed information for a specific job order."""
    try:
        job = frappe.get_doc("Job Order", job_name)
        
        # Get workflow history
        workflow_history = frappe.get_all(
            "Job Order Workflow History",
            filters={"job_order": job_name},
            fields=["from_phase", "to_phase", "transition_date", "user", "comment"],
            order_by="transition_date desc"
        ) if frappe.db.exists("DocType", "Job Order Workflow History") else []
        
        # Get team members
        team_members = getattr(job, "team_members", [])
        
        # Get materials
        materials = getattr(job, "material_requisitions", [])
        
        # Calculate progress
        progress = calculate_phase_progress(job.workflow_state)
        
        return {
            "success": True,
            "data": {
                "basic_info": {
                    "name": job.name,
                    "job_number": job.job_number,
                    "customer_name": job.customer_name,
                    "project_name": job.project_name,
                    "description": job.description,
                    "workflow_state": job.workflow_state,
                    "status": job.status,
                    "priority": job.priority,
                    "progress": progress
                },
                "dates": {
                    "start_date": job.start_date,
                    "end_date": job.end_date,
                    "phase_start_date": job.phase_start_date,
                    "phase_target_date": job.phase_target_date,
                    "creation": job.creation,
                    "modified": job.modified
                },
                "financial": {
                    "total_material_cost": job.total_material_cost or 0,
                    "total_labor_cost": job.total_labor_cost or 0,
                    "total_labor_hours": job.total_labor_hours or 0,
                    "total_value": (job.total_material_cost or 0) + (job.total_labor_cost or 0)
                },
                "workflow_history": workflow_history,
                "team_members": [dict(member) for member in team_members],
                "materials": [dict(material) for material in materials]
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Job detail error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def export_dashboard_data(export_type="summary", filters=None):
    """Export dashboard data to various formats."""
    try:
        if export_type == "summary":
            data = get_dashboard_overview()
        elif export_type == "jobs":
            data = get_advanced_job_list(filters=filters, limit=1000)
        elif export_type == "analytics":
            data = get_analytics_data(period="90")
        else:
            return {
                "success": False,
                "error": "Invalid export type"
            }
        
        return {
            "success": True,
            "data": data,
            "export_type": export_type,
            "timestamp": now_datetime()
        }
        
    except Exception as e:
        frappe.log_error(f"Export error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


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
def update_job_phase(job_name, new_phase, comments=""):
    """Quick update job phase from dashboard."""
    try:
        job = frappe.get_doc("Job Order", job_name)
        
        # Use the workflow transition API
        from api_next.api.job_workflow import transition_phase
        
        # Map phase to action (this would need to match your workflow)
        phase_actions = {
            "Estimation": "start_estimation",
            "Client Approval": "submit_estimate", 
            "Planning": "approve_estimate",
            "Prework": "start_planning",
            "Execution": "start_prework",
            "Review": "start_execution",
            "Invoicing": "complete_work",
            "Closeout": "approve_invoice",
            "Archived": "close_job"
        }
        
        action = phase_actions.get(new_phase)
        if not action:
            return {
                "success": False,
                "error": f"No action mapped for phase {new_phase}"
            }
        
        result = transition_phase(job_name, action, comments)
        return result
        
    except Exception as e:
        frappe.log_error(f"Update job phase error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }