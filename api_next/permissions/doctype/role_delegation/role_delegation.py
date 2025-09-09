"""
Role Delegation DocType Controller
Handles delegation logic, validation, and automatic activation/deactivation
"""

import frappe
from frappe.model.document import Document
from frappe import _
from datetime import datetime, date
from typing import List, Dict, Optional


class RoleDelegation(Document):
    """Role Delegation Document Controller"""
    
    def validate(self):
        """Validate delegation settings"""
        self.validate_dates()
        self.validate_delegator_delegatee()
        self.validate_delegation_scope()
        self.validate_role_permissions()
        
    def on_submit(self):
        """Activate delegation if within validity period"""
        if self.should_auto_activate():
            self.activate_delegation()
            
    def on_cancel(self):
        """Deactivate delegation"""
        self.deactivate_delegation()
        
    def validate_dates(self):
        """Validate start and end dates"""
        if self.end_date and self.start_date and self.end_date < self.start_date:
            frappe.throw(_("End date cannot be before start date"))
            
        if self.start_date and self.start_date < date.today():
            if not self.is_new():
                frappe.throw(_("Start date cannot be in the past"))
    
    def validate_delegator_delegatee(self):
        """Validate delegator and delegatee are different and valid"""
        if self.delegator == self.delegatee:
            frappe.throw(_("Delegator and delegatee cannot be the same user"))
            
        # Check if delegator has the roles they're trying to delegate
        delegator_roles = frappe.get_roles(self.delegator)
        
        if self.delegation_type == "Full Role" and self.specific_roles:
            for role_row in self.specific_roles:
                role = role_row.get("role") or role_row.get("value")
                if role not in delegator_roles:
                    frappe.throw(_("Delegator {0} does not have role {1}").format(self.delegator, role))
    
    def validate_delegation_scope(self):
        """Validate delegation scope settings"""
        if self.delegation_type == "Full Role" and not self.specific_roles:
            frappe.throw(_("Please specify roles to delegate when using Full Role delegation"))
            
        if self.delegation_type == "Specific DocTypes" and not self.specific_doctypes:
            frappe.throw(_("Please specify DocTypes when using Specific DocTypes delegation"))
            
        if self.delegation_type == "Specific Documents" and not self.specific_documents:
            frappe.throw(_("Please specify document names when using Specific Documents delegation"))
    
    def validate_role_permissions(self):
        """Validate that delegatee can receive the delegated permissions"""
        # Check if there are conflicting active delegations
        existing_delegations = frappe.get_all("Role Delegation",
            filters={
                "delegatee": self.delegatee,
                "is_active": 1,
                "name": ["!=", self.name],
                "start_date": ["<=", self.end_date or "2099-12-31"],
                "end_date": [">=", self.start_date]
            }
        )
        
        if existing_delegations:
            frappe.msgprint(_("Warning: User {0} has other active delegations during this period").format(self.delegatee))
    
    def should_auto_activate(self) -> bool:
        """Check if delegation should be auto-activated"""
        if not self.auto_activate or not self.is_active:
            return False
            
        today = date.today()
        return (self.start_date <= today and 
                (not self.end_date or self.end_date >= today))
    
    def activate_delegation(self):
        """Activate the delegation by granting roles/permissions"""
        try:
            if self.delegation_type == "Full Role":
                self._grant_role_permissions()
            elif self.delegation_type == "Specific DocTypes":
                self._grant_doctype_permissions()
            elif self.delegation_type == "Specific Documents":
                self._grant_document_permissions()
            elif self.delegation_type == "Approval Only":
                self._grant_approval_permissions()
                
            # Log activation
            self._log_delegation_activity("Activated")
            
            # Send notifications
            if self.notification_settings != "None":
                self._send_activation_notification()
                
            frappe.db.commit()
            
        except Exception as e:
            frappe.log_error(f"Error activating delegation {self.name}: {str(e)}")
            frappe.throw(_("Failed to activate delegation: {0}").format(str(e)))
    
    def deactivate_delegation(self):
        """Deactivate the delegation by removing roles/permissions"""
        try:
            if self.delegation_type == "Full Role":
                self._revoke_role_permissions()
            elif self.delegation_type == "Specific DocTypes":
                self._revoke_doctype_permissions()
            elif self.delegation_type == "Specific Documents":
                self._revoke_document_permissions()
            elif self.delegation_type == "Approval Only":
                self._revoke_approval_permissions()
                
            # Log deactivation
            self._log_delegation_activity("Deactivated")
            
            # Send notifications
            if self.notification_settings != "None":
                self._send_deactivation_notification()
                
            frappe.db.commit()
            
        except Exception as e:
            frappe.log_error(f"Error deactivating delegation {self.name}: {str(e)}")
    
    def _grant_role_permissions(self):
        """Grant full role permissions to delegatee"""
        for role_row in self.specific_roles:
            role = role_row.get("role") or role_row.get("value")
            if role:
                # Add role to user if not already present
                if not frappe.db.exists("Has Role", {"parent": self.delegatee, "role": role}):
                    role_doc = frappe.get_doc({
                        "doctype": "Has Role",
                        "parent": self.delegatee,
                        "parenttype": "User",
                        "parentfield": "roles",
                        "role": role
                    })
                    role_doc.insert(ignore_permissions=True)
                    
                # Mark as delegated role
                frappe.db.set_value("Has Role", 
                                  {"parent": self.delegatee, "role": role},
                                  "delegated_from", self.delegator)
    
    def _revoke_role_permissions(self):
        """Revoke delegated role permissions"""
        for role_row in self.specific_roles:
            role = role_row.get("role") or role_row.get("value")
            if role:
                # Remove only if it was delegated
                has_role = frappe.db.get_value("Has Role",
                    {"parent": self.delegatee, "role": role, "delegated_from": self.delegator},
                    "name"
                )
                if has_role:
                    frappe.delete_doc("Has Role", has_role, ignore_permissions=True)
    
    def _grant_doctype_permissions(self):
        """Grant specific DocType permissions"""
        # This would create temporary permission records
        # Implementation depends on specific requirements
        pass
    
    def _revoke_doctype_permissions(self):
        """Revoke specific DocType permissions"""
        # Remove temporary permission records
        pass
    
    def _grant_document_permissions(self):
        """Grant permissions for specific documents"""
        # Add delegatee to document shares or custom permission records
        pass
    
    def _revoke_document_permissions(self):
        """Revoke permissions for specific documents"""
        # Remove delegatee from document shares
        pass
    
    def _grant_approval_permissions(self):
        """Grant approval-only permissions"""
        # Create approval delegation records
        pass
    
    def _revoke_approval_permissions(self):
        """Revoke approval-only permissions"""
        # Remove approval delegation records
        pass
    
    def _log_delegation_activity(self, action: str):
        """Log delegation activity"""
        frappe.logger().info(f"Role Delegation {action}: {self.name} - {self.delegator} -> {self.delegatee}")
        
        # Create activity log
        activity_log = frappe.get_doc({
            "doctype": "Activity Log",
            "subject": f"Role Delegation {action}",
            "content": f"{action} delegation from {self.delegator_name} to {self.delegatee_name}",
            "reference_doctype": "Role Delegation",
            "reference_name": self.name,
            "user": frappe.session.user
        })
        activity_log.insert(ignore_permissions=True)
    
    def _send_activation_notification(self):
        """Send delegation activation notification"""
        recipients = self._get_notification_recipients()
        
        subject = f"Role Delegation Activated: {self.delegator_name} → {self.delegatee_name}"
        message = f"""
        Role delegation has been activated:
        
        From: {self.delegator_name} ({self.delegator})
        To: {self.delegatee_name} ({self.delegatee})
        
        Delegation Type: {self.delegation_type}
        Reason: {self.delegation_reason}
        Valid Until: {self.end_date or 'No end date'}
        
        Please ensure appropriate handover of responsibilities.
        """
        
        for recipient in recipients:
            frappe.sendmail(
                recipients=[recipient],
                subject=subject,
                message=message,
                reference_doctype="Role Delegation",
                reference_name=self.name
            )
    
    def _send_deactivation_notification(self):
        """Send delegation deactivation notification"""
        recipients = self._get_notification_recipients()
        
        subject = f"Role Delegation Deactivated: {self.delegator_name} → {self.delegatee_name}"
        message = f"""
        Role delegation has been deactivated:
        
        From: {self.delegator_name} ({self.delegator})
        To: {self.delegatee_name} ({self.delegatee})
        
        Responsibilities have been returned to the original user.
        """
        
        for recipient in recipients:
            frappe.sendmail(
                recipients=[recipient],
                subject=subject,
                message=message,
                reference_doctype="Role Delegation",
                reference_name=self.name
            )
    
    def _get_notification_recipients(self) -> List[str]:
        """Get list of notification recipients based on settings"""
        recipients = []
        
        if self.notification_settings in ["Email Delegator", "Email Both"]:
            recipients.append(self.delegator)
            
        if self.notification_settings in ["Email Both"]:
            recipients.append(self.delegatee)
            
        if self.notification_settings == "Email All Managers":
            # Get all managers/API Managers
            managers = frappe.get_all("Has Role",
                filters={"role": ["in", ["API Manager", "Job Manager"]]},
                fields=["parent"]
            )
            recipients.extend([m.parent for m in managers])
            
        return list(set(recipients))  # Remove duplicates


def check_and_activate_delegations():
    """Scheduled function to auto-activate delegations"""
    today = date.today()
    
    # Find delegations that should be activated
    pending_delegations = frappe.get_all("Role Delegation",
        filters={
            "is_active": 1,
            "auto_activate": 1,
            "start_date": ["<=", today],
            "end_date": [">=", today],
            "docstatus": 1
        }
    )
    
    for delegation in pending_delegations:
        try:
            doc = frappe.get_doc("Role Delegation", delegation.name)
            if doc.should_auto_activate():
                doc.activate_delegation()
        except Exception as e:
            frappe.log_error(f"Error auto-activating delegation {delegation.name}: {str(e)}")


def check_and_deactivate_expired_delegations():
    """Scheduled function to deactivate expired delegations"""
    today = date.today()
    
    # Find expired delegations
    expired_delegations = frappe.get_all("Role Delegation",
        filters={
            "is_active": 1,
            "end_date": ["<", today],
            "docstatus": 1
        }
    )
    
    for delegation in expired_delegations:
        try:
            doc = frappe.get_doc("Role Delegation", delegation.name)
            doc.deactivate_delegation()
            doc.db_set("is_active", 0)
        except Exception as e:
            frappe.log_error(f"Error deactivating expired delegation {delegation.name}: {str(e)}")


@frappe.whitelist()
def get_active_delegations_for_user(user=None):
    """Get active delegations for a user"""
    if not user:
        user = frappe.session.user
        
    delegations = frappe.get_all("Role Delegation",
        filters={
            "delegatee": user,
            "is_active": 1,
            "start_date": ["<=", date.today()],
            "end_date": [">=", date.today()],
            "docstatus": 1
        },
        fields=["name", "delegator", "delegator_name", "delegation_type", "delegation_reason", "end_date"]
    )
    
    return delegations


@frappe.whitelist()
def get_delegation_summary():
    """Get delegation summary for current user"""
    user = frappe.session.user
    
    # Delegations TO this user
    received_delegations = get_active_delegations_for_user(user)
    
    # Delegations FROM this user
    given_delegations = frappe.get_all("Role Delegation",
        filters={
            "delegator": user,
            "is_active": 1,
            "start_date": ["<=", date.today()],
            "end_date": [">=", date.today()],
            "docstatus": 1
        },
        fields=["name", "delegatee", "delegatee_name", "delegation_type", "delegation_reason", "end_date"]
    )
    
    return {
        "received": received_delegations,
        "given": given_delegations
    }