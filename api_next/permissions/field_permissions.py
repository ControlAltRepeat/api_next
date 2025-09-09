"""
Field-Level Permissions for API_Next ERP
Handles dynamic field visibility and editing permissions based on user roles and workflow states
"""

import frappe
from frappe import _
from typing import Dict, List, Optional, Any
from frappe.model.document import Document


class FieldPermissionManager:
    """Manages field-level permissions for API_Next documents"""
    
    # Financial fields that require special permissions
    FINANCIAL_FIELDS = {
        "Job Order": [
            "total_material_cost",
            "total_labor_cost",
            "estimated_cost",
            "actual_cost",
            "profit_margin",
            "markup_percentage",
            "final_cost"
        ],
        "Job Order Material": [
            "cost_per_unit",
            "total_cost",
            "markup_percentage",
            "selling_price"
        ],
        "Job Order Labor": [
            "billing_rate",
            "cost_rate", 
            "total_billing_amount",
            "total_cost_amount"
        ]
    }
    
    # Sensitive fields that require higher permissions
    SENSITIVE_FIELDS = {
        "Job Order": [
            "internal_notes",
            "confidential_remarks",
            "profit_analysis",
            "competitor_pricing"
        ]
    }
    
    # Workflow-based field permissions
    WORKFLOW_FIELD_PERMISSIONS = {
        "Submission": {
            "editable": ["customer_name", "project_name", "job_type", "description", "scope_of_work", "start_date", "end_date"],
            "readonly": ["workflow_state", "phase_start_date", "total_material_cost", "total_labor_cost"],
            "hidden": ["cancellation_reason"]
        },
        "Estimation": {
            "editable": ["description", "scope_of_work", "estimated_cost", "material_requisitions"],
            "readonly": ["customer_name", "project_name", "workflow_state"],
            "hidden": ["cancellation_reason"]
        },
        "Client Approval": {
            "editable": ["client_approval_notes"],
            "readonly": ["estimated_cost", "description", "scope_of_work"],
            "hidden": ["cancellation_reason"]
        },
        "Planning": {
            "editable": ["team_members", "phase_target_date", "labor_entries", "material_requisitions"],
            "readonly": ["estimated_cost", "customer_name"],
            "hidden": ["cancellation_reason"]
        },
        "Prework": {
            "editable": ["material_requisitions", "team_members", "labor_entries"],
            "readonly": ["estimated_cost", "customer_name", "description"],
            "hidden": ["cancellation_reason"]
        },
        "Execution": {
            "editable": ["labor_entries", "material_requisitions", "progress_notes"],
            "readonly": ["estimated_cost", "team_members"],
            "hidden": ["cancellation_reason"]
        },
        "Review": {
            "editable": ["quality_notes", "review_comments"],
            "readonly": ["labor_entries", "material_requisitions"],
            "hidden": ["cancellation_reason"]
        },
        "Invoicing": {
            "editable": ["billing_notes", "invoice_details"],
            "readonly": ["labor_entries", "material_requisitions", "quality_notes"],
            "hidden": ["cancellation_reason"]
        },
        "Closeout": {
            "editable": ["closeout_notes", "lessons_learned"],
            "readonly": ["*"],  # Most fields readonly
            "hidden": ["cancellation_reason"]
        },
        "Cancelled": {
            "editable": ["cancellation_reason"],
            "readonly": ["*"],
            "hidden": []
        }
    }
    
    # Role-based field permissions
    ROLE_FIELD_PERMISSIONS = {
        "API Employee": {
            "hidden": ["total_material_cost", "total_labor_cost", "profit_margin", "billing_rate", "cost_rate"],
            "readonly": ["customer_name", "project_name", "estimated_cost"]
        },
        "Estimator": {
            "editable": ["estimated_cost", "material_requisitions", "scope_of_work"],
            "hidden": ["internal_notes", "confidential_remarks"]
        },
        "Materials Coordinator": {
            "editable": ["material_requisitions", "total_material_cost"],
            "readonly": ["estimated_cost", "labor_entries"]
        },
        "Field Supervisor": {
            "editable": ["labor_entries", "progress_notes"],
            "readonly": ["material_requisitions", "estimated_cost"]
        },
        "Quality Inspector": {
            "editable": ["quality_notes", "review_comments"],
            "readonly": ["labor_entries", "material_requisitions"]
        },
        "Billing Clerk": {
            "editable": ["billing_notes", "invoice_details", "total_material_cost", "total_labor_cost"],
            "readonly": ["labor_entries", "material_requisitions"]
        }
    }

    @staticmethod
    def get_field_permissions(doctype: str, doc: Document, user: Optional[str] = None) -> Dict[str, Dict[str, bool]]:
        """Get field permissions for a document"""
        if not user:
            user = frappe.session.user
            
        user_roles = frappe.get_roles(user)
        workflow_state = doc.get("workflow_state") if doc else None
        
        permissions = {
            "read": {},
            "write": {},
            "hidden": {}
        }
        
        # Get all fields for the doctype
        meta = frappe.get_meta(doctype)
        all_fields = [field.fieldname for field in meta.fields if field.fieldtype not in ["Section Break", "Column Break", "HTML"]]
        
        # Initialize all fields as readable and writable by default
        for field in all_fields:
            permissions["read"][field] = True
            permissions["write"][field] = True
            permissions["hidden"][field] = False
        
        # Apply workflow-based permissions
        if workflow_state and workflow_state in FieldPermissionManager.WORKFLOW_FIELD_PERMISSIONS:
            workflow_perms = FieldPermissionManager.WORKFLOW_FIELD_PERMISSIONS[workflow_state]
            
            # Set readonly fields
            readonly_fields = workflow_perms.get("readonly", [])
            if "*" in readonly_fields:
                # All fields readonly except editable ones
                editable_fields = workflow_perms.get("editable", [])
                for field in all_fields:
                    if field not in editable_fields:
                        permissions["write"][field] = False
            else:
                for field in readonly_fields:
                    if field in permissions["write"]:
                        permissions["write"][field] = False
            
            # Set hidden fields
            hidden_fields = workflow_perms.get("hidden", [])
            for field in hidden_fields:
                if field in permissions["hidden"]:
                    permissions["hidden"][field] = True
                    permissions["read"][field] = False
                    permissions["write"][field] = False
        
        # Apply role-based permissions
        for role in user_roles:
            if role in FieldPermissionManager.ROLE_FIELD_PERMISSIONS:
                role_perms = FieldPermissionManager.ROLE_FIELD_PERMISSIONS[role]
                
                # Set hidden fields for role
                hidden_fields = role_perms.get("hidden", [])
                for field in hidden_fields:
                    if field in permissions["hidden"]:
                        permissions["hidden"][field] = True
                        permissions["read"][field] = False
                        permissions["write"][field] = False
                
                # Set readonly fields for role
                readonly_fields = role_perms.get("readonly", [])
                for field in readonly_fields:
                    if field in permissions["write"]:
                        permissions["write"][field] = False
        
        # Apply financial field restrictions
        if doctype in FieldPermissionManager.FINANCIAL_FIELDS:
            financial_fields = FieldPermissionManager.FINANCIAL_FIELDS[doctype]
            can_access_financial = FieldPermissionManager._can_access_financial_data(user_roles)
            
            if not can_access_financial:
                for field in financial_fields:
                    if field in permissions["hidden"]:
                        permissions["hidden"][field] = True
                        permissions["read"][field] = False
                        permissions["write"][field] = False
        
        # Apply sensitive field restrictions
        if doctype in FieldPermissionManager.SENSITIVE_FIELDS:
            sensitive_fields = FieldPermissionManager.SENSITIVE_FIELDS[doctype]
            can_access_sensitive = FieldPermissionManager._can_access_sensitive_data(user_roles)
            
            if not can_access_sensitive:
                for field in sensitive_fields:
                    if field in permissions["hidden"]:
                        permissions["hidden"][field] = True
                        permissions["read"][field] = False
                        permissions["write"][field] = False
        
        return permissions

    @staticmethod
    def _can_access_financial_data(user_roles: List[str]) -> bool:
        """Check if user can access financial data"""
        financial_roles = ["Job Manager", "API Manager", "Billing Clerk", "System Manager"]
        return any(role in financial_roles for role in user_roles)

    @staticmethod
    def _can_access_sensitive_data(user_roles: List[str]) -> bool:
        """Check if user can access sensitive data"""
        sensitive_roles = ["Job Manager", "API Manager", "System Manager"]
        return any(role in sensitive_roles for role in user_roles)

    @staticmethod
    def filter_document_fields(doc: Document, user: Optional[str] = None) -> Dict[str, Any]:
        """Filter document fields based on user permissions"""
        if not user:
            user = frappe.session.user
            
        doctype = doc.doctype
        permissions = FieldPermissionManager.get_field_permissions(doctype, doc, user)
        
        filtered_doc = {}
        
        for field, value in doc.as_dict().items():
            # Check if field should be hidden
            if permissions["hidden"].get(field, False):
                continue
                
            # Check if user can read the field
            if permissions["read"].get(field, True):
                filtered_doc[field] = value
            else:
                filtered_doc[field] = None
                
        return filtered_doc

    @staticmethod
    def validate_field_permissions(doc: Document, user: Optional[str] = None):
        """Validate that user has permission to modify fields"""
        if not user:
            user = frappe.session.user
            
        # Skip validation for System Manager
        if "System Manager" in frappe.get_roles(user):
            return
            
        doctype = doc.doctype
        permissions = FieldPermissionManager.get_field_permissions(doctype, doc, user)
        
        # Check if document exists (update vs create)
        if doc.name and frappe.db.exists(doctype, doc.name):
            # Get original document for comparison
            original_doc = frappe.get_doc(doctype, doc.name)
            
            # Check each field for unauthorized changes
            for field in doc.as_dict():
                if field in ["modified", "modified_by", "creation", "owner"]:
                    continue
                    
                # Skip if field is not writable
                if not permissions["write"].get(field, True):
                    original_value = original_doc.get(field)
                    current_value = doc.get(field)
                    
                    # If values differ, user tried to modify readonly field
                    if original_value != current_value:
                        frappe.throw(_("You don't have permission to modify field '{0}'").format(field))


def apply_field_permissions_to_form(doc, method):
    """Hook function to apply field permissions to forms"""
    user = frappe.session.user
    
    # Get permissions for current user
    permissions = FieldPermissionManager.get_field_permissions(doc.doctype, doc, user)
    
    # Store permissions in doc for client-side access
    doc._field_permissions = permissions


def validate_field_permissions_on_save(doc, method):
    """Hook function to validate field permissions on save"""
    FieldPermissionManager.validate_field_permissions(doc)


@frappe.whitelist()
def get_field_permissions_for_doc(doctype: str, name: str):
    """API endpoint to get field permissions for a document"""
    doc = frappe.get_doc(doctype, name)
    permissions = FieldPermissionManager.get_field_permissions(doctype, doc)
    return permissions


@frappe.whitelist()
def check_field_permission(doctype: str, fieldname: str, permission_type: str):
    """API endpoint to check specific field permission"""
    # For new documents, create a temporary doc
    doc = frappe.new_doc(doctype)
    permissions = FieldPermissionManager.get_field_permissions(doctype, doc)
    
    return permissions.get(permission_type, {}).get(fieldname, False)


def setup_field_permission_hooks():
    """Setup hooks for field permission enforcement"""
    # This would be called during app installation
    hooks_config = {
        "Job Order": {
            "validate": "api_next.permissions.field_permissions.validate_field_permissions_on_save",
            "before_load": "api_next.permissions.field_permissions.apply_field_permissions_to_form"
        },
        "Job Order Material": {
            "validate": "api_next.permissions.field_permissions.validate_field_permissions_on_save",
            "before_load": "api_next.permissions.field_permissions.apply_field_permissions_to_form"
        },
        "Job Order Labor": {
            "validate": "api_next.permissions.field_permissions.validate_field_permissions_on_save",
            "before_load": "api_next.permissions.field_permissions.apply_field_permissions_to_form"
        }
    }
    
    return hooks_config