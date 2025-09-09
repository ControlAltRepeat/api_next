"""
Role Management System for API_Next ERP
Handles role-based permissions, field-level access, and workflow-specific permissions
"""

import frappe
from frappe import _
from frappe.permissions import add_permission, update_permission_property
from typing import Dict, List, Optional, Tuple


class APINextRoleManager:
    """Centralized role and permission management for API_Next ERP"""
    
    # Role hierarchy - higher number means higher authority
    ROLE_HIERARCHY = {
        "API Employee": 1,
        "Billing Clerk": 2,
        "Quality Inspector": 3,
        "Materials Coordinator": 4,
        "Field Supervisor": 5,
        "Estimator": 6,
        "Planner": 7,
        "Job Manager": 8,
        "API Manager": 9,
        "System Manager": 10
    }
    
    # Phase-specific role mappings
    PHASE_ROLES = {
        "Submission": ["Job Manager", "API Manager", "System Manager"],
        "Estimation": ["Estimator", "Job Manager", "API Manager", "System Manager"],
        "Client Approval": ["Job Manager", "API Manager", "System Manager"],
        "Planning": ["Planner", "Job Manager", "API Manager", "System Manager"],
        "Prework": ["Planner", "Materials Coordinator", "Job Manager", "API Manager", "System Manager"],
        "Execution": ["Field Supervisor", "Materials Coordinator", "Job Manager", "API Manager", "System Manager"],
        "Review": ["Quality Inspector", "Field Supervisor", "Job Manager", "API Manager", "System Manager"],
        "Invoicing": ["Billing Clerk", "Job Manager", "API Manager", "System Manager"],
        "Closeout": ["Job Manager", "API Manager", "System Manager"],
        "Archived": ["API Manager", "System Manager"],
        "Cancelled": ["Job Manager", "API Manager", "System Manager"]
    }
    
    # Financial field restrictions
    FINANCIAL_FIELDS = [
        "total_material_cost",
        "total_labor_cost", 
        "estimated_cost",
        "actual_cost",
        "profit_margin",
        "billing_rate",
        "cost_rate"
    ]
    
    FINANCIAL_ROLES = [
        "Job Manager",
        "API Manager", 
        "Billing Clerk",
        "System Manager"
    ]

    @staticmethod
    def setup_all_permissions():
        """Setup all permissions for API_Next ERP system"""
        try:
            APINextRoleManager._setup_job_order_permissions()
            APINextRoleManager._setup_material_permissions()
            APINextRoleManager._setup_labor_permissions()
            APINextRoleManager._setup_workflow_permissions()
            APINextRoleManager._setup_settings_permissions()
            
            frappe.db.commit()
            frappe.msgprint(_("All permissions setup successfully"))
            
        except Exception as e:
            frappe.log_error(f"Error setting up permissions: {str(e)}")
            frappe.throw(_("Failed to setup permissions: {0}").format(str(e)))

    @staticmethod
    def _setup_job_order_permissions():
        """Setup Job Order permissions based on workflow phases"""
        doctype = "Job Order"
        
        # Clear existing permissions except System Manager
        existing_perms = frappe.get_all("Custom DocPerm", 
                                       filters={"parent": doctype, "role": ["!=", "System Manager"]})
        for perm in existing_perms:
            frappe.delete_doc("Custom DocPerm", perm.name, ignore_permissions=True)
        
        # API Manager - Full access
        add_permission(doctype, "API Manager", 0)
        update_permission_property(doctype, "API Manager", 0, "read", 1)
        update_permission_property(doctype, "API Manager", 0, "write", 1)
        update_permission_property(doctype, "API Manager", 0, "create", 1)
        update_permission_property(doctype, "API Manager", 0, "delete", 1)
        update_permission_property(doctype, "API Manager", 0, "submit", 1)
        update_permission_property(doctype, "API Manager", 0, "cancel", 1)
        update_permission_property(doctype, "API Manager", 0, "export", 1)
        update_permission_property(doctype, "API Manager", 0, "print", 1)
        update_permission_property(doctype, "API Manager", 0, "email", 1)
        update_permission_property(doctype, "API Manager", 0, "report", 1)
        
        # Job Manager - Full operational access
        add_permission(doctype, "Job Manager", 0)
        update_permission_property(doctype, "Job Manager", 0, "read", 1)
        update_permission_property(doctype, "Job Manager", 0, "write", 1)
        update_permission_property(doctype, "Job Manager", 0, "create", 1)
        update_permission_property(doctype, "Job Manager", 0, "delete", 1)
        update_permission_property(doctype, "Job Manager", 0, "submit", 1)
        update_permission_property(doctype, "Job Manager", 0, "cancel", 1)
        update_permission_property(doctype, "Job Manager", 0, "export", 1)
        update_permission_property(doctype, "Job Manager", 0, "print", 1)
        update_permission_property(doctype, "Job Manager", 0, "email", 1)
        update_permission_property(doctype, "Job Manager", 0, "report", 1)
        
        # Estimator - Read/Write during estimation phase
        add_permission(doctype, "Estimator", 0)
        update_permission_property(doctype, "Estimator", 0, "read", 1)
        update_permission_property(doctype, "Estimator", 0, "write", 1)
        update_permission_property(doctype, "Estimator", 0, "create", 1)
        update_permission_property(doctype, "Estimator", 0, "if_owner", 1)
        
        # Planner - Read/Write during planning phase
        add_permission(doctype, "Planner", 0)
        update_permission_property(doctype, "Planner", 0, "read", 1)
        update_permission_property(doctype, "Planner", 0, "write", 1)
        
        # Field Supervisor - Read/Write during execution
        add_permission(doctype, "Field Supervisor", 0)
        update_permission_property(doctype, "Field Supervisor", 0, "read", 1)
        update_permission_property(doctype, "Field Supervisor", 0, "write", 1)
        
        # Materials Coordinator - Read/Write for materials
        add_permission(doctype, "Materials Coordinator", 0)
        update_permission_property(doctype, "Materials Coordinator", 0, "read", 1)
        update_permission_property(doctype, "Materials Coordinator", 0, "write", 1)
        
        # Quality Inspector - Read/Write during review
        add_permission(doctype, "Quality Inspector", 0)
        update_permission_property(doctype, "Quality Inspector", 0, "read", 1)
        update_permission_property(doctype, "Quality Inspector", 0, "write", 1)
        
        # Billing Clerk - Read/Write during invoicing
        add_permission(doctype, "Billing Clerk", 0)
        update_permission_property(doctype, "Billing Clerk", 0, "read", 1)
        update_permission_property(doctype, "Billing Clerk", 0, "write", 1)
        
        # API Employee - Read only for assigned jobs
        add_permission(doctype, "API Employee", 0)
        update_permission_property(doctype, "API Employee", 0, "read", 1)
        update_permission_property(doctype, "API Employee", 0, "if_owner", 1)

    @staticmethod
    def _setup_material_permissions():
        """Setup Job Order Material permissions"""
        doctype = "Job Order Material"
        
        # Materials Coordinator - Full access
        add_permission(doctype, "Materials Coordinator", 0)
        update_permission_property(doctype, "Materials Coordinator", 0, "read", 1)
        update_permission_property(doctype, "Materials Coordinator", 0, "write", 1)
        update_permission_property(doctype, "Materials Coordinator", 0, "create", 1)
        update_permission_property(doctype, "Materials Coordinator", 0, "delete", 1)
        
        # Job Manager - Full access
        add_permission(doctype, "Job Manager", 0)
        update_permission_property(doctype, "Job Manager", 0, "read", 1)
        update_permission_property(doctype, "Job Manager", 0, "write", 1)
        update_permission_property(doctype, "Job Manager", 0, "create", 1)
        update_permission_property(doctype, "Job Manager", 0, "delete", 1)
        
        # API Manager - Full access
        add_permission(doctype, "API Manager", 0)
        update_permission_property(doctype, "API Manager", 0, "read", 1)
        update_permission_property(doctype, "API Manager", 0, "write", 1)
        update_permission_property(doctype, "API Manager", 0, "create", 1)
        update_permission_property(doctype, "API Manager", 0, "delete", 1)
        
        # Field Supervisor - Read access
        add_permission(doctype, "Field Supervisor", 0)
        update_permission_property(doctype, "Field Supervisor", 0, "read", 1)
        
        # Estimator - Read access
        add_permission(doctype, "Estimator", 0)
        update_permission_property(doctype, "Estimator", 0, "read", 1)

    @staticmethod
    def _setup_labor_permissions():
        """Setup Job Order Labor permissions"""
        doctype = "Job Order Labor"
        
        # Field Supervisor - Full access
        add_permission(doctype, "Field Supervisor", 0)
        update_permission_property(doctype, "Field Supervisor", 0, "read", 1)
        update_permission_property(doctype, "Field Supervisor", 0, "write", 1)
        update_permission_property(doctype, "Field Supervisor", 0, "create", 1)
        update_permission_property(doctype, "Field Supervisor", 0, "delete", 1)
        
        # Planner - Full access
        add_permission(doctype, "Planner", 0)
        update_permission_property(doctype, "Planner", 0, "read", 1)
        update_permission_property(doctype, "Planner", 0, "write", 1)
        update_permission_property(doctype, "Planner", 0, "create", 1)
        update_permission_property(doctype, "Planner", 0, "delete", 1)
        
        # Job Manager - Full access
        add_permission(doctype, "Job Manager", 0)
        update_permission_property(doctype, "Job Manager", 0, "read", 1)
        update_permission_property(doctype, "Job Manager", 0, "write", 1)
        update_permission_property(doctype, "Job Manager", 0, "create", 1)
        update_permission_property(doctype, "Job Manager", 0, "delete", 1)
        
        # API Manager - Full access
        add_permission(doctype, "API Manager", 0)
        update_permission_property(doctype, "API Manager", 0, "read", 1)
        update_permission_property(doctype, "API Manager", 0, "write", 1)
        update_permission_property(doctype, "API Manager", 0, "create", 1)
        update_permission_property(doctype, "API Manager", 0, "delete", 1)
        
        # API Employee - Read/Write for own entries
        add_permission(doctype, "API Employee", 0)
        update_permission_property(doctype, "API Employee", 0, "read", 1)
        update_permission_property(doctype, "API Employee", 0, "write", 1)
        update_permission_property(doctype, "API Employee", 0, "create", 1)
        update_permission_property(doctype, "API Employee", 0, "if_owner", 1)

    @staticmethod
    def _setup_workflow_permissions():
        """Setup workflow-related DocType permissions"""
        doctypes = ["Job Order Phase", "Job Order Phase History", "Job Order Workflow History"]
        
        for doctype in doctypes:
            # API Manager - Full access
            add_permission(doctype, "API Manager", 0)
            update_permission_property(doctype, "API Manager", 0, "read", 1)
            update_permission_property(doctype, "API Manager", 0, "write", 1)
            update_permission_property(doctype, "API Manager", 0, "create", 1)
            update_permission_property(doctype, "API Manager", 0, "delete", 1)
            
            # Job Manager - Full access
            add_permission(doctype, "Job Manager", 0)
            update_permission_property(doctype, "Job Manager", 0, "read", 1)
            update_permission_property(doctype, "Job Manager", 0, "write", 1)
            update_permission_property(doctype, "Job Manager", 0, "create", 1)
            update_permission_property(doctype, "Job Manager", 0, "delete", 1)
            
            # All other roles - Read only
            roles = ["Estimator", "Planner", "Materials Coordinator", "Field Supervisor", 
                    "Quality Inspector", "Billing Clerk", "API Employee"]
            for role in roles:
                add_permission(doctype, role, 0)
                update_permission_property(doctype, role, 0, "read", 1)

    @staticmethod
    def _setup_settings_permissions():
        """Setup API Settings permissions"""
        doctype = "API Settings"
        
        # Only System Manager should have access to settings
        add_permission(doctype, "System Manager", 0)
        update_permission_property(doctype, "System Manager", 0, "read", 1)
        update_permission_property(doctype, "System Manager", 0, "write", 1)
        update_permission_property(doctype, "System Manager", 0, "create", 1)
        update_permission_property(doctype, "System Manager", 0, "delete", 1)

    @staticmethod
    def can_access_phase(user_roles: List[str], workflow_state: str) -> bool:
        """Check if user roles can access a specific workflow phase"""
        if not workflow_state or workflow_state not in APINextRoleManager.PHASE_ROLES:
            return False
            
        allowed_roles = APINextRoleManager.PHASE_ROLES[workflow_state]
        return any(role in allowed_roles for role in user_roles)

    @staticmethod
    def can_access_financial_data(user_roles: List[str]) -> bool:
        """Check if user can access financial data"""
        return any(role in APINextRoleManager.FINANCIAL_ROLES for role in user_roles)

    @staticmethod
    def get_user_role_hierarchy_level(user_roles: List[str]) -> int:
        """Get the highest hierarchy level for user's roles"""
        max_level = 0
        for role in user_roles:
            if role in APINextRoleManager.ROLE_HIERARCHY:
                max_level = max(max_level, APINextRoleManager.ROLE_HIERARCHY[role])
        return max_level

    @staticmethod
    def filter_fields_by_permission(doc, user_roles: List[str]) -> Dict:
        """Filter document fields based on user permissions"""
        filtered_doc = doc.as_dict()
        
        # Hide financial fields if user doesn't have financial access
        if not APINextRoleManager.can_access_financial_data(user_roles):
            for field in APINextRoleManager.FINANCIAL_FIELDS:
                if field in filtered_doc:
                    filtered_doc[field] = None
                    
        return filtered_doc

    @staticmethod
    def validate_workflow_transition(doc, user_roles: List[str]) -> bool:
        """Validate if user can perform workflow transitions"""
        current_phase = doc.get("workflow_state")
        if not current_phase:
            return True
            
        return APINextRoleManager.can_access_phase(user_roles, current_phase)


def setup_api_next_permissions():
    """Entry point for setting up all API_Next permissions"""
    APINextRoleManager.setup_all_permissions()


# Frappe whitelist functions for client-side access
@frappe.whitelist()
def check_phase_access(workflow_state):
    """Check if current user can access a workflow phase"""
    user_roles = frappe.get_roles(frappe.session.user)
    return APINextRoleManager.can_access_phase(user_roles, workflow_state)


@frappe.whitelist() 
def check_financial_access():
    """Check if current user can access financial data"""
    user_roles = frappe.get_roles(frappe.session.user)
    return APINextRoleManager.can_access_financial_data(user_roles)


@frappe.whitelist()
def get_user_hierarchy_level():
    """Get current user's role hierarchy level"""
    user_roles = frappe.get_roles(frappe.session.user)
    return APINextRoleManager.get_user_role_hierarchy_level(user_roles)


def get_job_order_permission_query_conditions(user):
    """Get permission query conditions for Job Order list view"""
    if not user:
        user = frappe.session.user
        
    user_roles = frappe.get_roles(user)
    
    # System Manager and API Manager can see all
    if "System Manager" in user_roles or "API Manager" in user_roles:
        return ""
    
    conditions = []
    
    # Job Manager can see all job orders
    if "Job Manager" in user_roles:
        return ""
    
    # Other roles see based on workflow phase and assignment
    role_conditions = []
    
    for role in user_roles:
        if role in APINextRoleManager.PHASE_ROLES:
            # Get phases this role can access
            accessible_phases = []
            for phase, allowed_roles in APINextRoleManager.PHASE_ROLES.items():
                if role in allowed_roles:
                    accessible_phases.append(f"'{phase}'")
            
            if accessible_phases:
                role_conditions.append(f"`workflow_state` in ({','.join(accessible_phases)})")
    
    # Add owner condition for API Employee
    if "API Employee" in user_roles:
        role_conditions.append(f"`owner` = '{user}'")
    
    if role_conditions:
        conditions.append(f"({' OR '.join(role_conditions)})")
    
    return " AND ".join(conditions) if conditions else "1=0"


def has_job_order_permission(doc, user):
    """Check if user has permission for specific Job Order"""
    if not user:
        user = frappe.session.user
        
    user_roles = frappe.get_roles(user)
    
    # System Manager and API Manager always have permission
    if "System Manager" in user_roles or "API Manager" in user_roles:
        return True
    
    # Job Manager has permission for all job orders
    if "Job Manager" in user_roles:
        return True
    
    # Check if user can access current workflow phase
    workflow_state = doc.get("workflow_state")
    if workflow_state and APINextRoleManager.can_access_phase(user_roles, workflow_state):
        return True
    
    # Check if user is owner (for API Employee)
    if doc.get("owner") == user:
        return True
    
    return False