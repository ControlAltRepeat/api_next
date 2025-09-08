# API endpoints for Job Management System
import frappe
from frappe import _
from frappe.utils import today, add_days
import json

@frappe.whitelist(allow_guest=False)
def create_job_order(customer_name, project_name, job_type, start_date, description=None):
    """Create a new job order"""
    try:
        job_order = frappe.get_doc({
            "doctype": "Job Order",
            "customer_name": customer_name,
            "project_name": project_name,
            "job_type": job_type,
            "start_date": start_date,
            "description": description,
            "status": "Draft",
            "priority": "Medium"
        })
        job_order.insert()
        frappe.db.commit()
        
        return {
            "success": True,
            "job_number": job_order.name,
            "message": f"Job Order {job_order.name} created successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist(allow_guest=False)
def get_job_orders(status=None, customer=None):
    """Get list of job orders with filters"""
    filters = {}
    if status:
        filters["status"] = status
    if customer:
        filters["customer_name"] = ["like", f"%{customer}%"]
    
    job_orders = frappe.get_all("Job Order",
        filters=filters,
        fields=["name", "job_number", "customer_name", "project_name", 
                "status", "priority", "start_date", "end_date"]
    )
    
    return {
        "success": True,
        "data": job_orders
    }

@frappe.whitelist(allow_guest=False)
def update_job_status(job_number, new_status):
    """Update job order status"""
    try:
        job_order = frappe.get_doc("Job Order", job_number)
        job_order.status = new_status
        job_order.save()
        frappe.db.commit()
        
        return {
            "success": True,
            "message": f"Job {job_number} status updated to {new_status}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist(allow_guest=False)
def add_labor_entry(job_number, employee_name, date, hours, description=None):
    """Add labor time entry to a job"""
    try:
        job_order = frappe.get_doc("Job Order", job_number)
        
        # Add labor entry to the job
        job_order.append("labor_entries", {
            "employee_name": employee_name,
            "date": date,
            "hours": hours,
            "description": description,
            "cost": hours * 50  # Default hourly rate
        })
        
        job_order.save()
        frappe.db.commit()
        
        return {
            "success": True,
            "message": f"Labor entry added for {employee_name}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist(allow_guest=False)
def get_job_summary(job_number):
    """Get detailed summary of a job order"""
    try:
        job_order = frappe.get_doc("Job Order", job_number)
        
        return {
            "success": True,
            "data": {
                "job_number": job_order.name,
                "customer": job_order.customer_name,
                "project": job_order.project_name,
                "status": job_order.status,
                "start_date": str(job_order.start_date),
                "end_date": str(job_order.end_date) if job_order.end_date else None,
                "total_material_cost": job_order.total_material_cost,
                "total_labor_hours": job_order.total_labor_hours,
                "total_labor_cost": job_order.total_labor_cost,
                "phases": len(job_order.phases) if job_order.phases else 0,
                "team_size": len(job_order.team_members) if job_order.team_members else 0
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist(allow_guest=False)
def create_material_requisition(job_number, items):
    """Create material requisition for a job"""
    try:
        # Parse items if string
        if isinstance(items, str):
            items = json.loads(items)
        
        job_order = frappe.get_doc("Job Order", job_number)
        
        for item in items:
            job_order.append("material_requisitions", {
                "item_name": item.get("name"),
                "quantity": item.get("quantity"),
                "unit_cost": item.get("unit_cost", 0),
                "total_cost": item.get("quantity", 0) * item.get("unit_cost", 0)
            })
        
        job_order.save()
        frappe.db.commit()
        
        return {
            "success": True,
            "message": f"Material requisition created for job {job_number}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
