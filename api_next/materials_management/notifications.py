# Copyright (c) 2024, API Next and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate, formatdate, get_datetime
from frappe.utils.user import get_user_fullname
import json


def send_requisition_notification(requisition_name, event_type, recipients):
    """Send notification for requisition events"""
    try:
        requisition = frappe.get_doc("Job Material Requisition", requisition_name)
        
        # Prepare notification data based on event type
        if event_type == "approved":
            send_approval_notification(requisition, recipients)
        elif event_type == "rejected":
            send_rejection_notification(requisition, recipients)
        elif event_type == "submitted":
            send_submission_notification(requisition, recipients)
        elif event_type == "urgent":
            send_urgent_notification(requisition, recipients)
        
    except Exception as e:
        frappe.log_error(f"Error sending requisition notification: {str(e)}")


def send_approval_notification(requisition, recipients):
    """Send notification when requisition is approved"""
    try:
        subject = _("Material Requisition {0} has been approved").format(requisition.name)
        
        template_data = {
            "requisition": requisition,
            "job_order_title": frappe.db.get_value("Job Order", requisition.job_order, "title") if requisition.job_order else "",
            "approved_by_name": get_user_fullname(requisition.approved_by) if requisition.approved_by else "",
            "items_count": len(requisition.items),
            "total_cost": requisition.total_estimated_cost or 0
        }
        
        message = frappe.render_template("""
        <div style="font-family: Arial, sans-serif; max-width: 600px;">
            <h3 style="color: #28a745;">Material Requisition Approved</h3>
            
            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <strong>Requisition:</strong> {{ requisition.name }}<br>
                <strong>Title:</strong> {{ requisition.title }}<br>
                {% if job_order_title %}
                <strong>Job Order:</strong> {{ job_order_title }}<br>
                {% endif %}
                <strong>Required By:</strong> {{ frappe.utils.formatdate(requisition.required_by) }}<br>
                <strong>Priority:</strong> {{ requisition.priority }}<br>
                <strong>Items:</strong> {{ items_count }}<br>
                <strong>Estimated Cost:</strong> {{ frappe.utils.fmt_money(total_cost, currency="CAD") }}<br>
                <strong>Approved By:</strong> {{ approved_by_name }}<br>
                <strong>Approval Date:</strong> {{ frappe.utils.format_datetime(requisition.approval_date) }}
            </div>
            
            {% if requisition.approver_notes %}
            <div style="background: #fff3cd; padding: 10px; border-radius: 5px; margin: 10px 0;">
                <strong>Approver Notes:</strong><br>
                {{ requisition.approver_notes }}
            </div>
            {% endif %}
            
            <p>A Material Request will be created automatically in ERPNext for procurement.</p>
            
            <div style="margin-top: 20px;">
                <a href="/app/job-material-requisition/{{ requisition.name }}" 
                   style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                   View Requisition
                </a>
            </div>
        </div>
        """, template_data)
        
        # Send email notification
        for recipient in recipients:
            try:
                frappe.sendmail(
                    recipients=[recipient],
                    subject=subject,
                    message=message,
                    header=["Material Requisition Update", "green"]
                )
            except Exception as e:
                frappe.log_error(f"Error sending email to {recipient}: {str(e)}")
        
        # Send in-app notification
        for recipient in recipients:
            try:
                notification_doc = frappe.get_doc({
                    "doctype": "Notification Log",
                    "subject": subject,
                    "for_user": recipient,
                    "type": "Alert",
                    "document_type": "Job Material Requisition",
                    "document_name": requisition.name,
                    "email_content": message
                })
                notification_doc.insert(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(f"Error creating notification for {recipient}: {str(e)}")
        
    except Exception as e:
        frappe.log_error(f"Error sending approval notification: {str(e)}")


def send_rejection_notification(requisition, recipients):
    """Send notification when requisition is rejected"""
    try:
        subject = _("Material Requisition {0} has been rejected").format(requisition.name)
        
        template_data = {
            "requisition": requisition,
            "job_order_title": frappe.db.get_value("Job Order", requisition.job_order, "title") if requisition.job_order else "",
            "items_count": len(requisition.items)
        }
        
        message = frappe.render_template("""
        <div style="font-family: Arial, sans-serif; max-width: 600px;">
            <h3 style="color: #dc3545;">Material Requisition Rejected</h3>
            
            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <strong>Requisition:</strong> {{ requisition.name }}<br>
                <strong>Title:</strong> {{ requisition.title }}<br>
                {% if job_order_title %}
                <strong>Job Order:</strong> {{ job_order_title }}<br>
                {% endif %}
                <strong>Required By:</strong> {{ frappe.utils.formatdate(requisition.required_by) }}<br>
                <strong>Priority:</strong> {{ requisition.priority }}<br>
                <strong>Items:</strong> {{ items_count }}
            </div>
            
            {% if requisition.rejection_reason %}
            <div style="background: #f8d7da; padding: 10px; border-radius: 5px; margin: 10px 0;">
                <strong>Rejection Reason:</strong><br>
                {{ requisition.rejection_reason }}
            </div>
            {% endif %}
            
            <p>Please review and modify the requisition as needed before resubmitting.</p>
            
            <div style="margin-top: 20px;">
                <a href="/app/job-material-requisition/{{ requisition.name }}" 
                   style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                   View Requisition
                </a>
            </div>
        </div>
        """, template_data)
        
        # Send notifications
        for recipient in recipients:
            try:
                frappe.sendmail(
                    recipients=[recipient],
                    subject=subject,
                    message=message,
                    header=["Material Requisition Update", "red"]
                )
                
                notification_doc = frappe.get_doc({
                    "doctype": "Notification Log",
                    "subject": subject,
                    "for_user": recipient,
                    "type": "Alert",
                    "document_type": "Job Material Requisition",
                    "document_name": requisition.name,
                    "email_content": message
                })
                notification_doc.insert(ignore_permissions=True)
                
            except Exception as e:
                frappe.log_error(f"Error sending rejection notification to {recipient}: {str(e)}")
        
    except Exception as e:
        frappe.log_error(f"Error sending rejection notification: {str(e)}")


def send_fulfillment_notification(requisition_name, notification_type, recipients):
    """Send notification for material fulfillment events"""
    try:
        requisition = frappe.get_doc("Job Material Requisition", requisition_name)
        
        if notification_type == "completed":
            subject = _("Material Requisition {0} - All items received").format(requisition.name)
            color = "green"
            header_text = "Material Requisition Completed"
        elif notification_type == "partial":
            subject = _("Material Requisition {0} - Partial fulfillment").format(requisition.name)
            color = "orange"
            header_text = "Material Requisition Partially Fulfilled"
        else:
            return
        
        # Calculate fulfillment statistics
        total_items = len(requisition.items)
        fulfilled_items = 0
        partially_fulfilled = 0
        
        for item in requisition.items:
            if frappe.utils.flt(item.quantity_received) >= frappe.utils.flt(item.quantity_requested):
                fulfilled_items += 1
            elif frappe.utils.flt(item.quantity_received) > 0:
                partially_fulfilled += 1
        
        template_data = {
            "requisition": requisition,
            "job_order_title": frappe.db.get_value("Job Order", requisition.job_order, "title") if requisition.job_order else "",
            "total_items": total_items,
            "fulfilled_items": fulfilled_items,
            "partially_fulfilled": partially_fulfilled,
            "pending_items": total_items - fulfilled_items - partially_fulfilled,
            "notification_type": notification_type,
            "header_text": header_text
        }
        
        message = frappe.render_template("""
        <div style="font-family: Arial, sans-serif; max-width: 600px;">
            <h3 style="color: {{ color }};">{{ header_text }}</h3>
            
            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <strong>Requisition:</strong> {{ requisition.name }}<br>
                <strong>Title:</strong> {{ requisition.title }}<br>
                {% if job_order_title %}
                <strong>Job Order:</strong> {{ job_order_title }}<br>
                {% endif %}
                <strong>Material Request:</strong> {{ requisition.material_request }}<br>
                <strong>Status:</strong> {{ requisition.status }}
            </div>
            
            <div style="background: #e9ecef; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h4>Fulfillment Summary:</h4>
                <ul>
                    <li>Total Items: {{ total_items }}</li>
                    <li>Fully Received: {{ fulfilled_items }}</li>
                    <li>Partially Received: {{ partially_fulfilled }}</li>
                    <li>Pending: {{ pending_items }}</li>
                </ul>
            </div>
            
            {% if notification_type == "completed" %}
            <p style="color: green; font-weight: bold;">All materials have been received and are ready for use.</p>
            {% else %}
            <p style="color: orange;">Some materials have been received. Please coordinate with the warehouse team for remaining items.</p>
            {% endif %}
            
            <div style="margin-top: 20px;">
                <a href="/app/job-material-requisition/{{ requisition.name }}" 
                   style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                   View Requisition
                </a>
            </div>
        </div>
        """, template_data)
        
        # Send notifications
        for recipient in recipients:
            try:
                frappe.sendmail(
                    recipients=[recipient],
                    subject=subject,
                    message=message,
                    header=["Material Fulfillment Update", color]
                )
                
                notification_doc = frappe.get_doc({
                    "doctype": "Notification Log",
                    "subject": subject,
                    "for_user": recipient,
                    "type": "Alert" if notification_type == "completed" else "Share",
                    "document_type": "Job Material Requisition",
                    "document_name": requisition.name,
                    "email_content": message
                })
                notification_doc.insert(ignore_permissions=True)
                
            except Exception as e:
                frappe.log_error(f"Error sending fulfillment notification to {recipient}: {str(e)}")
        
    except Exception as e:
        frappe.log_error(f"Error sending fulfillment notification: {str(e)}")


def send_urgent_notification(requisition, recipients):
    """Send urgent notification for high priority or overdue requisitions"""
    try:
        subject = _("URGENT: Material Requisition {0} requires attention").format(requisition.name)
        
        # Determine urgency reason
        urgency_reason = ""
        if requisition.priority == "Urgent":
            urgency_reason = "This requisition is marked as URGENT priority."
        elif requisition.required_by:
            from frappe.utils import date_diff
            days_diff = date_diff(requisition.required_by, nowdate())
            if days_diff <= 0:
                urgency_reason = f"This requisition is overdue by {abs(days_diff)} day(s)."
            elif days_diff <= 2:
                urgency_reason = f"This requisition is due in {days_diff} day(s)."
        
        template_data = {
            "requisition": requisition,
            "job_order_title": frappe.db.get_value("Job Order", requisition.job_order, "title") if requisition.job_order else "",
            "urgency_reason": urgency_reason,
            "items_count": len(requisition.items)
        }
        
        message = frappe.render_template("""
        <div style="font-family: Arial, sans-serif; max-width: 600px;">
            <h3 style="color: #dc3545;">🚨 URGENT: Material Requisition Attention Required</h3>
            
            <div style="background: #f8d7da; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 5px solid #dc3545;">
                <strong>{{ urgency_reason }}</strong>
            </div>
            
            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <strong>Requisition:</strong> {{ requisition.name }}<br>
                <strong>Title:</strong> {{ requisition.title }}<br>
                {% if job_order_title %}
                <strong>Job Order:</strong> {{ job_order_title }}<br>
                {% endif %}
                <strong>Required By:</strong> {{ frappe.utils.formatdate(requisition.required_by) }}<br>
                <strong>Priority:</strong> <span style="color: #dc3545; font-weight: bold;">{{ requisition.priority }}</span><br>
                <strong>Status:</strong> {{ requisition.status }}<br>
                <strong>Approval Status:</strong> {{ requisition.approval_status }}<br>
                <strong>Items:</strong> {{ items_count }}
            </div>
            
            <p style="color: #dc3545; font-weight: bold;">
                Immediate action is required to prevent project delays.
            </p>
            
            <div style="margin-top: 20px;">
                <a href="/app/job-material-requisition/{{ requisition.name }}" 
                   style="background: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                   Take Action Now
                </a>
            </div>
        </div>
        """, template_data)
        
        # Send high priority notifications
        for recipient in recipients:
            try:
                frappe.sendmail(
                    recipients=[recipient],
                    subject=subject,
                    message=message,
                    header=["URGENT: Material Requisition", "red"],
                    priority=1  # High priority
                )
                
                notification_doc = frappe.get_doc({
                    "doctype": "Notification Log",
                    "subject": subject,
                    "for_user": recipient,
                    "type": "Alert",
                    "document_type": "Job Material Requisition",
                    "document_name": requisition.name,
                    "email_content": message
                })
                notification_doc.insert(ignore_permissions=True)
                
            except Exception as e:
                frappe.log_error(f"Error sending urgent notification to {recipient}: {str(e)}")
        
    except Exception as e:
        frappe.log_error(f"Error sending urgent notification: {str(e)}")


def check_overdue_requisitions():
    """Scheduled task to check for overdue requisitions"""
    try:
        from frappe.utils import add_days
        
        # Get requisitions that are overdue or due soon
        overdue_requisitions = frappe.get_all(
            "Job Material Requisition",
            filters={
                "required_by": ["<=", add_days(nowdate(), 2)],
                "status": ["in", ["Draft", "Pending Approval", "Approved"]],
                "docstatus": 0
            },
            fields=["name", "required_by", "priority", "job_order", "owner"]
        )
        
        for req in overdue_requisitions:
            # Get recipients for urgent notification
            recipients = [req.owner]
            
            # Add materials coordinators
            materials_coordinators = frappe.get_all(
                "Has Role",
                filters={"role": "Materials Coordinator"},
                pluck="parent"
            )
            recipients.extend(materials_coordinators)
            
            # Add job manager if different from owner
            if req.job_order:
                job_order = frappe.get_doc("Job Order", req.job_order)
                if job_order.owner and job_order.owner not in recipients:
                    recipients.append(job_order.owner)
            
            # Send urgent notification
            frappe.enqueue(
                "api_next.materials_management.notifications.send_requisition_notification",
                requisition_name=req.name,
                event_type="urgent",
                recipients=list(set(recipients)),
                queue="short"
            )
        
    except Exception as e:
        frappe.log_error(f"Error checking overdue requisitions: {str(e)}")


def send_daily_summary():
    """Send daily summary of material requisitions to coordinators"""
    try:
        # Get materials coordinators
        coordinators = frappe.get_all(
            "Has Role",
            filters={"role": "Materials Coordinator"},
            pluck="parent"
        )
        
        if not coordinators:
            return
        
        # Get today's statistics
        today = nowdate()
        
        pending_approvals = frappe.db.count(
            "Job Material Requisition",
            {"approval_status": "Pending", "requisition_date": today}
        )
        
        approved_today = frappe.db.count(
            "Job Material Requisition",
            {"approval_status": "Approved", "approval_date": ["like", f"{today}%"]}
        )
        
        overdue_count = frappe.db.count(
            "Job Material Requisition",
            {"required_by": ["<", today], "status": ["in", ["Draft", "Pending Approval"]]}
        )
        
        urgent_count = frappe.db.count(
            "Job Material Requisition",
            {"priority": "Urgent", "status": ["in", ["Draft", "Pending Approval", "Approved"]]}
        )
        
        subject = f"Daily Material Requisitions Summary - {formatdate(today)}"
        
        message = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px;">
            <h3>Daily Material Requisitions Summary</h3>
            <p><strong>Date:</strong> {formatdate(today)}</p>
            
            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h4>Today's Statistics:</h4>
                <ul>
                    <li><strong>Pending Approvals:</strong> {pending_approvals}</li>
                    <li><strong>Approved Today:</strong> {approved_today}</li>
                    <li><strong>Overdue Requisitions:</strong> {overdue_count}</li>
                    <li><strong>Urgent Priority:</strong> {urgent_count}</li>
                </ul>
            </div>
            
            <div style="margin-top: 20px;">
                <a href="/app/job-material-requisition" 
                   style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                   View All Requisitions
                </a>
            </div>
        </div>
        """
        
        for coordinator in coordinators:
            try:
                frappe.sendmail(
                    recipients=[coordinator],
                    subject=subject,
                    message=message,
                    header=["Daily Summary", "blue"]
                )
            except Exception as e:
                frappe.log_error(f"Error sending daily summary to {coordinator}: {str(e)}")
        
    except Exception as e:
        frappe.log_error(f"Error sending daily summary: {str(e)}")