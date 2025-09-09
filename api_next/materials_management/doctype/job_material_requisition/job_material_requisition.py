# Copyright (c) 2024, API Next and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, now, flt, cint
from typing import Dict, List, Optional
import json


class JobMaterialRequisition(Document):
    """Custom Material Requisition with ERPNext integration"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.material_request_doc = None
    
    def validate(self):
        """Validate the requisition before saving"""
        self.validate_required_by_date()
        self.validate_items()
        self.calculate_totals()
        self.set_title()
        self.validate_approval_workflow()
    
    def validate_required_by_date(self):
        """Ensure required by date is not in the past"""
        if self.required_by and self.required_by < nowdate():
            frappe.throw(_("Required by date cannot be in the past"))
    
    def validate_items(self):
        """Validate requisition items"""
        if not self.items:
            frappe.throw(_("Please add at least one item to the requisition"))
        
        for item in self.items:
            if not item.quantity_requested or item.quantity_requested <= 0:
                frappe.throw(_("Row {0}: Quantity requested must be greater than 0").format(item.idx))
            
            if item.job_allocation and (item.job_allocation < 0 or item.job_allocation > 100):
                frappe.throw(_("Row {0}: Job allocation must be between 0 and 100%").format(item.idx))
            
            # Set default warehouse if not specified
            if not item.warehouse and self.warehouse:
                item.warehouse = self.warehouse
    
    def calculate_totals(self):
        """Calculate total estimated cost"""
        total = 0
        for item in self.items:
            if item.estimated_cost:
                total += flt(item.estimated_cost)
        
        self.total_estimated_cost = total
    
    def set_title(self):
        """Auto-generate title if not set"""
        if not self.title and self.job_order:
            job_order_doc = frappe.get_doc("Job Order", self.job_order)
            self.title = f"Material Requisition for {job_order_doc.title}"
    
    def validate_approval_workflow(self):
        """Validate approval workflow logic"""
        if self.approval_status == "Approved" and not self.approved_by:
            self.approved_by = frappe.session.user
            self.approval_date = now()
        
        if self.approval_status == "Approved" and self.status == "Draft":
            self.status = "Approved"
        
        if self.approval_status == "Rejected" and self.status != "Cancelled":
            self.status = "Cancelled"
    
    def on_submit(self):
        """Actions to perform on submission"""
        if self.approval_status != "Approved":
            frappe.throw(_("Cannot submit requisition without approval"))
        
        # Create ERPNext Material Request if approved
        if self.approval_status == "Approved" and not self.material_request:
            self.create_material_request()
    
    def on_cancel(self):
        """Actions to perform on cancellation"""
        self.status = "Cancelled"
        
        # Cancel linked Material Request if exists
        if self.material_request:
            try:
                material_request = frappe.get_doc("Material Request", self.material_request)
                if material_request.docstatus == 1:
                    material_request.cancel()
                    frappe.msgprint(_("Linked Material Request {0} has been cancelled").format(self.material_request))
            except Exception as e:
                frappe.log_error(f"Error cancelling Material Request: {str(e)}")
    
    def create_material_request(self):
        """Create ERPNext Material Request from this requisition"""
        try:
            # Create Material Request
            material_request = frappe.new_doc("Material Request")
            material_request.material_request_type = "Purchase"
            material_request.transaction_date = self.requisition_date
            material_request.schedule_date = self.required_by
            material_request.company = frappe.defaults.get_user_default("Company")
            
            # Set project if available
            if self.project:
                material_request.project = self.project
            
            # Add items
            for item in self.items:
                mr_item = material_request.append("items")
                mr_item.item_code = item.item_code
                mr_item.qty = item.quantity_approved or item.quantity_requested
                mr_item.uom = item.unit
                mr_item.warehouse = item.warehouse
                mr_item.schedule_date = self.required_by
                
                # Store reference for tracking
                item.material_request_item = mr_item.name
            
            # Save and submit Material Request
            material_request.save()
            material_request.submit()
            
            # Update this document with Material Request reference
            self.material_request = material_request.name
            self.status = "Ordered"
            self.save()
            
            frappe.msgprint(_("Material Request {0} created successfully").format(material_request.name))
            
            # Schedule background job to monitor fulfillment
            frappe.enqueue(
                "api_next.materials_management.utils.monitor_material_request_fulfillment",
                job_material_requisition=self.name,
                queue="default",
                timeout=300
            )
            
        except Exception as e:
            frappe.log_error(f"Error creating Material Request: {str(e)}")
            frappe.throw(_("Failed to create Material Request: {0}").format(str(e)))
    
    def update_fulfillment_status(self):
        """Update fulfillment status from linked Material Request"""
        if not self.material_request:
            return
        
        try:
            material_request = frappe.get_doc("Material Request", self.material_request)
            
            total_requested = 0
            total_ordered = 0
            total_received = 0
            
            for item in self.items:
                # Find corresponding Material Request item
                mr_item = None
                for mr_i in material_request.items:
                    if mr_i.item_code == item.item_code:
                        mr_item = mr_i
                        break
                
                if mr_item:
                    item.quantity_ordered = mr_item.ordered_qty or 0
                    item.quantity_received = mr_i.received_qty or 0
                    
                    total_requested += flt(item.quantity_requested)
                    total_ordered += flt(item.quantity_ordered)
                    total_received += flt(item.quantity_received)
            
            # Update status based on fulfillment
            if total_received >= total_requested:
                self.status = "Received"
            elif total_received > 0:
                self.status = "Partially Received"
            elif total_ordered > 0:
                self.status = "Ordered"
            
            self.save()
            
        except Exception as e:
            frappe.log_error(f"Error updating fulfillment status: {str(e)}")
    
    @frappe.whitelist()
    def approve_requisition(self, approver_notes=None):
        """Approve the requisition"""
        if not frappe.has_permission(self.doctype, "write", self.name):
            frappe.throw(_("Insufficient permissions to approve this requisition"))
        
        self.approval_status = "Approved"
        self.approved_by = frappe.session.user
        self.approval_date = now()
        self.status = "Approved"
        
        if approver_notes:
            self.approver_notes = approver_notes
        
        # Auto-approve quantities if not already set
        for item in self.items:
            if not item.quantity_approved:
                item.quantity_approved = item.quantity_requested
        
        self.save()
        
        # Send notification
        self.send_approval_notification()
        
        return {"status": "success", "message": _("Requisition approved successfully")}
    
    @frappe.whitelist()
    def reject_requisition(self, rejection_reason):
        """Reject the requisition"""
        if not frappe.has_permission(self.doctype, "write", self.name):
            frappe.throw(_("Insufficient permissions to reject this requisition"))
        
        if not rejection_reason:
            frappe.throw(_("Rejection reason is required"))
        
        self.approval_status = "Rejected"
        self.rejection_reason = rejection_reason
        self.status = "Cancelled"
        self.save()
        
        # Send notification
        self.send_rejection_notification()
        
        return {"status": "success", "message": _("Requisition rejected")}
    
    def send_approval_notification(self):
        """Send notification when requisition is approved"""
        try:
            # Get job order owner and materials coordinator
            recipients = []
            
            if self.job_order:
                job_order = frappe.get_doc("Job Order", self.job_order)
                if job_order.owner:
                    recipients.append(job_order.owner)
            
            # Add materials coordinators
            materials_coordinators = frappe.get_all(
                "Has Role",
                filters={"role": "Materials Coordinator"},
                fields=["parent"]
            )
            recipients.extend([mc.parent for mc in materials_coordinators])
            
            if recipients:
                frappe.enqueue(
                    "api_next.materials_management.notifications.send_requisition_notification",
                    requisition_name=self.name,
                    event_type="approved",
                    recipients=list(set(recipients)),
                    queue="short"
                )
        except Exception as e:
            frappe.log_error(f"Error sending approval notification: {str(e)}")
    
    def send_rejection_notification(self):
        """Send notification when requisition is rejected"""
        try:
            # Get job order owner
            recipients = []
            
            if self.job_order:
                job_order = frappe.get_doc("Job Order", self.job_order)
                if job_order.owner:
                    recipients.append(job_order.owner)
            
            if recipients:
                frappe.enqueue(
                    "api_next.materials_management.notifications.send_requisition_notification",
                    requisition_name=self.name,
                    event_type="rejected",
                    recipients=list(set(recipients)),
                    queue="short"
                )
        except Exception as e:
            frappe.log_error(f"Error sending rejection notification: {str(e)}")


@frappe.whitelist()
def create_from_job_order(job_order, items_data=None, required_by=None, priority="Normal"):
    """Create material requisition from job order"""
    if not frappe.has_permission("Job Material Requisition", "create"):
        frappe.throw(_("Insufficient permissions to create material requisition"))
    
    # Get job order details
    job_order_doc = frappe.get_doc("Job Order", job_order)
    
    # Create new requisition
    requisition = frappe.new_doc("Job Material Requisition")
    requisition.job_order = job_order
    requisition.requisition_date = nowdate()
    requisition.required_by = required_by or job_order_doc.scheduled_end_date
    requisition.priority = priority
    requisition.warehouse = job_order_doc.warehouse
    requisition.project = job_order_doc.project
    
    # Add items from job order materials or provided data
    if items_data:
        items_list = json.loads(items_data) if isinstance(items_data, str) else items_data
        for item_data in items_list:
            item = requisition.append("items")
            item.item_code = item_data.get("item_code")
            item.quantity_requested = item_data.get("quantity", 1)
            item.warehouse = item_data.get("warehouse") or requisition.warehouse
            item.notes = item_data.get("notes", "")
    else:
        # Get materials from job order
        job_materials = frappe.get_all(
            "Job Order Material",
            filters={"parent": job_order},
            fields=["item_code", "quantity", "warehouse", "notes"]
        )
        
        for material in job_materials:
            item = requisition.append("items")
            item.item_code = material.item_code
            item.quantity_requested = material.quantity
            item.warehouse = material.warehouse or requisition.warehouse
            item.notes = material.notes or ""
    
    requisition.save()
    
    return {
        "status": "success",
        "requisition_name": requisition.name,
        "message": _("Material requisition created successfully")
    }


@frappe.whitelist()
def get_requisition_dashboard_data(name):
    """Get dashboard data for material requisition"""
    requisition = frappe.get_doc("Job Material Requisition", name)
    
    # Calculate fulfillment statistics
    total_items = len(requisition.items)
    fully_received_items = 0
    partially_received_items = 0
    
    for item in requisition.items:
        if flt(item.quantity_received) >= flt(item.quantity_requested):
            fully_received_items += 1
        elif flt(item.quantity_received) > 0:
            partially_received_items += 1
    
    return {
        "total_items": total_items,
        "fully_received_items": fully_received_items,
        "partially_received_items": partially_received_items,
        "pending_items": total_items - fully_received_items - partially_received_items,
        "total_estimated_cost": requisition.total_estimated_cost,
        "material_request": requisition.material_request,
        "status": requisition.status,
        "approval_status": requisition.approval_status
    }