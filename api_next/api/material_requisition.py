# Copyright (c) 2024, API Next and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate, flt, cint
import json
from typing import Dict, List, Optional


@frappe.whitelist()
def get_requisitions_list(
    job_order=None,
    status=None,
    approval_status=None,
    priority=None,
    from_date=None,
    to_date=None,
    limit=20,
    offset=0
):
    """Get filtered list of material requisitions"""
    
    filters = {"docstatus": ["!=", 2]}  # Exclude cancelled documents
    
    if job_order:
        filters["job_order"] = job_order
    if status:
        filters["status"] = status
    if approval_status:
        filters["approval_status"] = approval_status
    if priority:
        filters["priority"] = priority
    if from_date:
        filters["requisition_date"] = [">=", from_date]
    if to_date:
        filters["requisition_date"] = ["<=", to_date]
    
    # Apply permission filters
    user_roles = frappe.get_roles()
    if "System Manager" not in user_roles and "Materials Coordinator" not in user_roles:
        # Limit to user's job orders if not admin/coordinator
        user_job_orders = frappe.get_all(
            "Job Order",
            filters={"owner": frappe.session.user},
            pluck="name"
        )
        if user_job_orders:
            filters["job_order"] = ["in", user_job_orders]
        else:
            # No access to any job orders
            return {"data": [], "total": 0}
    
    # Get total count
    total = frappe.db.count("Job Material Requisition", filters)
    
    # Get data
    requisitions = frappe.get_all(
        "Job Material Requisition",
        filters=filters,
        fields=[
            "name", "title", "job_order", "requisition_date", "required_by",
            "priority", "status", "approval_status", "total_estimated_cost",
            "approved_by", "approval_date", "material_request"
        ],
        order_by="requisition_date desc, creation desc",
        limit=limit,
        start=offset
    )
    
    # Enhance data with additional info
    for req in requisitions:
        # Get job order title
        if req.job_order:
            req.job_order_title = frappe.db.get_value("Job Order", req.job_order, "title")
        
        # Get items count
        req.items_count = frappe.db.count(
            "Job Material Requisition Item",
            {"parent": req.name}
        )
        
        # Calculate fulfillment percentage
        req.fulfillment_percentage = calculate_fulfillment_percentage(req.name)
    
    return {
        "data": requisitions,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@frappe.whitelist()
def get_requisition_details(name):
    """Get detailed information for a material requisition"""
    if not frappe.has_permission("Job Material Requisition", "read", name):
        frappe.throw(_("Insufficient permissions to view this requisition"))
    
    # Get main document
    requisition = frappe.get_doc("Job Material Requisition", name)
    
    # Get items with additional details
    items = []
    for item in requisition.items:
        item_dict = item.as_dict()
        
        # Add stock availability
        if item.warehouse:
            try:
                from erpnext.stock.utils import get_stock_balance
                item_dict["available_stock"] = get_stock_balance(
                    item_code=item.item_code,
                    warehouse=item.warehouse,
                    posting_date=nowdate()
                )
            except:
                item_dict["available_stock"] = 0
        else:
            item_dict["available_stock"] = 0
        
        # Calculate fulfillment percentage
        if item.quantity_requested:
            fulfillment = (flt(item.quantity_received) / flt(item.quantity_requested)) * 100
            item_dict["fulfillment_percentage"] = min(100, fulfillment)
        else:
            item_dict["fulfillment_percentage"] = 0
        
        items.append(item_dict)
    
    # Get job order details
    job_order_details = {}
    if requisition.job_order:
        job_order = frappe.get_doc("Job Order", requisition.job_order)
        job_order_details = {
            "name": job_order.name,
            "title": job_order.title,
            "status": job_order.status,
            "customer": job_order.customer,
            "project": job_order.project
        }
    
    # Get Material Request details if linked
    material_request_details = {}
    if requisition.material_request:
        try:
            mr = frappe.get_doc("Material Request", requisition.material_request)
            material_request_details = {
                "name": mr.name,
                "status": mr.status,
                "transaction_date": mr.transaction_date,
                "per_ordered": mr.per_ordered,
                "per_received": mr.per_received
            }
        except:
            pass
    
    return {
        "requisition": requisition.as_dict(),
        "items": items,
        "job_order": job_order_details,
        "material_request": material_request_details,
        "can_approve": can_approve_requisition(requisition),
        "can_edit": frappe.has_permission("Job Material Requisition", "write", name)
    }


@frappe.whitelist()
def sync_with_erpnext(requisition_name):
    """Manually trigger sync with ERPNext Material Request"""
    if not frappe.has_permission("Job Material Requisition", "write", requisition_name):
        frappe.throw(_("Insufficient permissions"))
    
    try:
        requisition = frappe.get_doc("Job Material Requisition", requisition_name)
        
        if requisition.approval_status != "Approved":
            frappe.throw(_("Cannot sync unapproved requisition"))
        
        if requisition.material_request:
            # Update fulfillment status
            requisition.update_fulfillment_status()
            return {
                "status": "success",
                "message": _("Fulfillment status updated from Material Request {0}").format(requisition.material_request)
            }
        else:
            # Create Material Request
            requisition.create_material_request()
            return {
                "status": "success",
                "message": _("Material Request created: {0}").format(requisition.material_request)
            }
            
    except Exception as e:
        frappe.log_error(f"Error syncing with ERPNext: {str(e)}")
        frappe.throw(_("Sync failed: {0}").format(str(e)))


def calculate_fulfillment_percentage(requisition_name):
    """Calculate overall fulfillment percentage for a requisition"""
    items = frappe.get_all(
        "Job Material Requisition Item",
        filters={"parent": requisition_name},
        fields=["quantity_requested", "quantity_received"]
    )
    
    if not items:
        return 0
    
    total_requested = sum(flt(item.quantity_requested) for item in items)
    total_received = sum(flt(item.quantity_received) for item in items)
    
    if total_requested == 0:
        return 0
    
    return min(100, (total_received / total_requested) * 100)


def can_approve_requisition(requisition):
    """Check if current user can approve the requisition"""
    user_roles = frappe.get_roles()
    
    # System Manager and Materials Coordinator can always approve
    if any(role in ["System Manager", "Materials Coordinator"] for role in user_roles):
        return True
    
    # Job Manager can approve for their jobs
    if "Job Manager" in user_roles:
        if requisition.job_order:
            job_order = frappe.get_doc("Job Order", requisition.job_order)
            if job_order.owner == frappe.session.user:
                return True
    
    # Check role delegations
    delegations = frappe.get_all(
        "Role Delegation",
        filters={
            "delegated_to": frappe.session.user,
            "role": ["in", ["Materials Coordinator", "Job Manager"]],
            "is_active": 1
        }
    )
    
    return len(delegations) > 0