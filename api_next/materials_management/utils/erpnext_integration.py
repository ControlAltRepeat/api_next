# Copyright (c) 2024, API Next and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate, flt, cint, get_datetime
from typing import Dict, List, Optional
import json


def monitor_material_request_fulfillment(job_material_requisition):
    """Background job to monitor Material Request fulfillment"""
    try:
        requisition = frappe.get_doc("Job Material Requisition", job_material_requisition)
        
        if not requisition.material_request:
            frappe.log_error("No Material Request linked to monitor", "Material Request Monitor")
            return
        
        # Update fulfillment status
        requisition.update_fulfillment_status()
        
        # Check if notification needed for completion
        if requisition.status == "Received":
            send_fulfillment_notification(requisition.name, "completed")
        elif requisition.status == "Partially Received":
            send_fulfillment_notification(requisition.name, "partial")
        
        frappe.db.commit()
        
    except Exception as e:
        frappe.log_error(f"Error monitoring Material Request fulfillment: {str(e)}")


def sync_material_request_to_job_costs(material_request_name):
    """Sync Material Request costs back to Job Order"""
    try:
        # Find requisitions linked to this Material Request
        requisitions = frappe.get_all(
            "Job Material Requisition",
            filters={"material_request": material_request_name},
            fields=["name", "job_order"]
        )
        
        for req_data in requisitions:
            requisition = frappe.get_doc("Job Material Requisition", req_data.name)
            
            if requisition.job_order:
                update_job_order_material_costs(requisition)
                
        frappe.db.commit()
        
    except Exception as e:
        frappe.log_error(f"Error syncing Material Request costs to jobs: {str(e)}")


def update_job_order_material_costs(requisition):
    """Update Job Order with actual material costs"""
    try:
        job_order = frappe.get_doc("Job Order", requisition.job_order)
        
        # Calculate actual costs from linked Purchase Orders/Stock Entries
        actual_costs = calculate_actual_material_costs(requisition)
        
        # Update job order material costs
        for item in requisition.items:
            # Find corresponding job order material
            job_material = None
            for jm in job_order.materials:
                if jm.item_code == item.item_code:
                    job_material = jm
                    break
            
            if job_material:
                # Update with actual costs
                actual_cost = actual_costs.get(item.item_code, 0)
                if actual_cost > 0:
                    job_material.actual_cost = actual_cost
                    job_material.variance = actual_cost - (job_material.estimated_cost or 0)
        
        # Recalculate totals
        job_order.calculate_totals()
        job_order.save()
        
    except Exception as e:
        frappe.log_error(f"Error updating job order material costs: {str(e)}")


def calculate_actual_material_costs(requisition):
    """Calculate actual costs from Purchase Orders and Stock Entries"""
    actual_costs = {}
    
    if not requisition.material_request:
        return actual_costs
    
    try:
        # Get Purchase Orders linked to Material Request
        purchase_orders = frappe.get_all(
            "Purchase Order Item",
            filters={"material_request": requisition.material_request},
            fields=["parent", "item_code", "qty", "rate", "amount"]
        )
        
        for po_item in purchase_orders:
            if po_item.item_code not in actual_costs:
                actual_costs[po_item.item_code] = 0
            actual_costs[po_item.item_code] += flt(po_item.amount)
        
        # Get Stock Entries if no Purchase Orders
        if not purchase_orders:
            stock_entries = frappe.get_all(
                "Stock Entry Detail",
                filters={
                    "material_request": requisition.material_request,
                    "s_warehouse": ["is", "set"]  # Only consider issues from stock
                },
                fields=["item_code", "qty", "valuation_rate", "amount"]
            )
            
            for se_item in stock_entries:
                if se_item.item_code not in actual_costs:
                    actual_costs[se_item.item_code] = 0
                
                cost = flt(se_item.amount) or (flt(se_item.qty) * flt(se_item.valuation_rate))
                actual_costs[se_item.item_code] += cost
        
    except Exception as e:
        frappe.log_error(f"Error calculating actual material costs: {str(e)}")
    
    return actual_costs


def create_stock_reservation(requisition_name):
    """Create stock reservation for approved requisition items"""
    try:
        requisition = frappe.get_doc("Job Material Requisition", requisition_name)
        
        if requisition.approval_status != "Approved":
            return
        
        for item in requisition.items:
            if not item.warehouse:
                continue
            
            # Check if stock reservation already exists
            existing_reservation = frappe.get_all(
                "Stock Reservation Entry",
                filters={
                    "item_code": item.item_code,
                    "warehouse": item.warehouse,
                    "project": requisition.project,
                    "voucher_type": "Job Material Requisition",
                    "voucher_no": requisition.name
                }
            )
            
            if existing_reservation:
                continue
            
            # Check available stock
            try:
                from erpnext.stock.utils import get_stock_balance
                available_qty = get_stock_balance(
                    item_code=item.item_code,
                    warehouse=item.warehouse,
                    posting_date=nowdate()
                )
                
                quantity_to_reserve = min(
                    flt(item.quantity_approved or item.quantity_requested),
                    flt(available_qty)
                )
                
                if quantity_to_reserve > 0:
                    # Create Stock Reservation Entry
                    reservation = frappe.new_doc("Stock Reservation Entry")
                    reservation.item_code = item.item_code
                    reservation.warehouse = item.warehouse
                    reservation.qty = quantity_to_reserve
                    reservation.project = requisition.project
                    reservation.voucher_type = "Job Material Requisition"
                    reservation.voucher_no = requisition.name
                    reservation.reservation_based_on = "Material Request"
                    reservation.company = frappe.defaults.get_user_default("Company")
                    
                    reservation.save()
                    reservation.submit()
                    
            except Exception as e:
                frappe.log_error(f"Error creating stock reservation for {item.item_code}: {str(e)}")
        
    except Exception as e:
        frappe.log_error(f"Error creating stock reservations: {str(e)}")


def handle_material_request_update(doc, method):
    """Handle Material Request document events"""
    try:
        # Find linked Job Material Requisitions
        requisitions = frappe.get_all(
            "Job Material Requisition",
            filters={"material_request": doc.name},
            pluck="name"
        )
        
        for req_name in requisitions:
            requisition = frappe.get_doc("Job Material Requisition", req_name)
            
            # Update fulfillment status
            requisition.update_fulfillment_status()
            
            # Schedule cost sync if needed
            if method in ["on_submit", "on_update_after_submit"]:
                frappe.enqueue(
                    "api_next.materials_management.utils.erpnext_integration.sync_material_request_to_job_costs",
                    material_request_name=doc.name,
                    queue="default",
                    timeout=300
                )
                
    except Exception as e:
        frappe.log_error(f"Error handling Material Request update: {str(e)}")


def handle_purchase_order_update(doc, method):
    """Handle Purchase Order events that affect material requisitions"""
    try:
        # Find Material Requests linked to this Purchase Order
        material_requests = []
        for item in doc.items:
            if item.material_request:
                material_requests.append(item.material_request)
        
        material_requests = list(set(material_requests))
        
        for mr_name in material_requests:
            frappe.enqueue(
                "api_next.materials_management.utils.erpnext_integration.sync_material_request_to_job_costs",
                material_request_name=mr_name,
                queue="default",
                timeout=300
            )
            
    except Exception as e:
        frappe.log_error(f"Error handling Purchase Order update: {str(e)}")


def handle_stock_entry_submit(doc, method):
    """Handle Stock Entry submission that affects material requisitions"""
    try:
        # Find Material Requests linked to this Stock Entry
        material_requests = []
        for item in doc.items:
            if item.material_request:
                material_requests.append(item.material_request)
        
        material_requests = list(set(material_requests))
        
        for mr_name in material_requests:
            frappe.enqueue(
                "api_next.materials_management.utils.erpnext_integration.monitor_material_request_fulfillment",
                job_material_requisition=get_requisition_from_material_request(mr_name),
                queue="default",
                timeout=300
            )
            
    except Exception as e:
        frappe.log_error(f"Error handling Stock Entry submit: {str(e)}")


def get_requisition_from_material_request(material_request_name):
    """Get Job Material Requisition from Material Request name"""
    requisition = frappe.get_value(
        "Job Material Requisition",
        {"material_request": material_request_name},
        "name"
    )
    return requisition


def send_fulfillment_notification(requisition_name, notification_type):
    """Send notification for material fulfillment events"""
    try:
        requisition = frappe.get_doc("Job Material Requisition", requisition_name)
        
        recipients = []
        
        # Add job order owner
        if requisition.job_order:
            job_order = frappe.get_doc("Job Order", requisition.job_order)
            if job_order.owner:
                recipients.append(job_order.owner)
        
        # Add materials coordinators
        materials_coordinators = frappe.get_all(
            "Has Role",
            filters={"role": "Materials Coordinator"},
            pluck="parent"
        )
        recipients.extend(materials_coordinators)
        
        if recipients:
            frappe.enqueue(
                "api_next.materials_management.notifications.send_fulfillment_notification",
                requisition_name=requisition_name,
                notification_type=notification_type,
                recipients=list(set(recipients)),
                queue="short"
            )
            
    except Exception as e:
        frappe.log_error(f"Error sending fulfillment notification: {str(e)}")


def schedule_recurring_sync():
    """Schedule recurring sync of material requisitions with ERPNext"""
    try:
        # Get all active requisitions with linked Material Requests
        active_requisitions = frappe.get_all(
            "Job Material Requisition",
            filters={
                "status": ["in", ["Ordered", "Partially Received"]],
                "material_request": ["is", "set"],
                "docstatus": 1
            },
            pluck="name"
        )
        
        for req_name in active_requisitions:
            frappe.enqueue(
                "api_next.materials_management.utils.erpnext_integration.monitor_material_request_fulfillment",
                job_material_requisition=req_name,
                queue="long",
                timeout=300
            )
            
    except Exception as e:
        frappe.log_error(f"Error scheduling recurring sync: {str(e)}")


def validate_material_request_sync(requisition):
    """Validate that requisition can be synced to Material Request"""
    errors = []
    
    # Check approval status
    if requisition.approval_status != "Approved":
        errors.append(_("Requisition must be approved before sync"))
    
    # Check if items exist
    if not requisition.items:
        errors.append(_("No items found in requisition"))
    
    # Validate items
    for item in requisition.items:
        if not item.item_code:
            errors.append(_("Row {0}: Item Code is required").format(item.idx))
        
        if not item.quantity_requested or item.quantity_requested <= 0:
            errors.append(_("Row {0}: Quantity must be greater than 0").format(item.idx))
        
        # Check if item exists in ERPNext
        if not frappe.db.exists("Item", item.item_code):
            errors.append(_("Row {0}: Item {1} does not exist").format(item.idx, item.item_code))
        
        # Check if warehouse exists
        if item.warehouse and not frappe.db.exists("Warehouse", item.warehouse):
            errors.append(_("Row {0}: Warehouse {1} does not exist").format(item.idx, item.warehouse))
    
    # Check company
    company = frappe.defaults.get_user_default("Company")
    if not company:
        errors.append(_("Default company not set"))
    
    return errors


def get_material_request_items_status(material_request_name):
    """Get detailed status of Material Request items"""
    try:
        mr = frappe.get_doc("Material Request", material_request_name)
        
        items_status = []
        for item in mr.items:
            status = {
                "item_code": item.item_code,
                "qty": item.qty,
                "ordered_qty": item.ordered_qty or 0,
                "received_qty": item.received_qty or 0,
                "pending_qty": flt(item.qty) - flt(item.received_qty or 0),
                "fulfillment_percentage": (flt(item.received_qty or 0) / flt(item.qty)) * 100 if item.qty else 0
            }
            items_status.append(status)
        
        return items_status
        
    except Exception as e:
        frappe.log_error(f"Error getting Material Request items status: {str(e)}")
        return []


@frappe.whitelist()
def force_sync_all_requisitions():
    """Force sync all pending requisitions - admin function"""
    if not frappe.has_permission("System Manager"):
        frappe.throw(_("Only System Manager can force sync all requisitions"))
    
    try:
        # Get all requisitions that need sync
        requisitions = frappe.get_all(
            "Job Material Requisition",
            filters={
                "approval_status": "Approved",
                "status": ["in", ["Approved", "Ordered", "Partially Received"]],
                "docstatus": 1
            },
            pluck="name"
        )
        
        synced = 0
        errors = 0
        
        for req_name in requisitions:
            try:
                requisition = frappe.get_doc("Job Material Requisition", req_name)
                
                if not requisition.material_request:
                    requisition.create_material_request()
                else:
                    requisition.update_fulfillment_status()
                
                synced += 1
                
            except Exception as e:
                frappe.log_error(f"Error syncing requisition {req_name}: {str(e)}")
                errors += 1
        
        frappe.db.commit()
        
        return {
            "status": "success",
            "synced": synced,
            "errors": errors,
            "message": _("Synced {0} requisitions, {1} errors").format(synced, errors)
        }
        
    except Exception as e:
        frappe.log_error(f"Error in force sync: {str(e)}")
        frappe.throw(_("Force sync failed: {0}").format(str(e)))