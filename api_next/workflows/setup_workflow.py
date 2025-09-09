# Copyright (c) 2025, API Next and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import json
import os

def setup_job_order_workflow():
    """
    Setup the complete Job Order workflow system.
    
    This function:
    1. Creates required roles
    2. Imports workflow definition
    3. Sets up permissions
    4. Creates custom fields if needed
    5. Enables workflow for Job Order DocType
    """
    
    frappe.flags.ignore_permissions = True
    
    try:
        # Step 1: Create roles
        create_workflow_roles()
        
        # Step 2: Import workflow
        import_workflow_definition()
        
        # Step 3: Setup permissions
        setup_workflow_permissions()
        
        # Step 4: Enable workflow
        enable_job_order_workflow()
        
        # Step 5: Create sample notifications
        setup_notification_templates()
        
        frappe.db.commit()
        
        print("✅ Job Order Workflow setup completed successfully!")
        return True
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Workflow setup error: {str(e)}")
        print(f"❌ Workflow setup failed: {str(e)}")
        return False
    
    finally:
        frappe.flags.ignore_permissions = False

def create_workflow_roles():
    """Create workflow-related roles."""
    roles_to_create = [
        "Job Coordinator", "Estimator", "Client", "Sales Manager",
        "Project Manager", "Resource Coordinator", "Site Supervisor",
        "Technician", "Quality Inspector", "Billing Clerk",
        "Accountant", "Document Controller", "Material Coordinator",
        "Operations Manager"
    ]
    
    for role_name in roles_to_create:
        if not frappe.db.exists("Role", role_name):
            role_doc = frappe.get_doc({
                "doctype": "Role",
                "role_name": role_name,
                "desk_access": 1,
                "is_custom": 1
            })
            role_doc.insert(ignore_if_duplicate=True)
            print(f"Created role: {role_name}")

def import_workflow_definition():
    """Import the workflow definition from fixtures."""
    fixtures_path = frappe.get_app_path("api_next", "fixtures")
    workflow_file = os.path.join(fixtures_path, "workflow_job_order.json")
    
    if os.path.exists(workflow_file):
        with open(workflow_file, 'r') as f:
            workflow_data = json.load(f)
        
        for workflow in workflow_data:
            if not frappe.db.exists("Workflow", workflow["name"]):
                workflow_doc = frappe.get_doc(workflow)
                workflow_doc.insert(ignore_permissions=True)
                print(f"Created workflow: {workflow['name']}")
            else:
                # Update existing workflow
                existing_workflow = frappe.get_doc("Workflow", workflow["name"])
                existing_workflow.update(workflow)
                existing_workflow.save(ignore_permissions=True)
                print(f"Updated workflow: {workflow['name']}")

def setup_workflow_permissions():
    """Setup role-based permissions for workflow states."""
    job_order_meta = frappe.get_meta("Job Order")
    
    # Define role permissions for Job Order
    role_permissions = [
        {
            "role": "Job Coordinator",
            "permlevel": 0,
            "read": 1, "write": 1, "create": 1, "submit": 0, "cancel": 0, "delete": 0
        },
        {
            "role": "Estimator", 
            "permlevel": 0,
            "read": 1, "write": 1, "create": 0, "submit": 0, "cancel": 0, "delete": 0
        },
        {
            "role": "Client",
            "permlevel": 0,
            "read": 1, "write": 0, "create": 0, "submit": 0, "cancel": 0, "delete": 0
        },
        {
            "role": "Sales Manager",
            "permlevel": 0,
            "read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1, "delete": 0
        },
        {
            "role": "Project Manager",
            "permlevel": 0,
            "read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1, "delete": 1
        },
        {
            "role": "Site Supervisor",
            "permlevel": 0,
            "read": 1, "write": 1, "create": 0, "submit": 0, "cancel": 0, "delete": 0
        },
        {
            "role": "Quality Inspector",
            "permlevel": 0,
            "read": 1, "write": 1, "create": 0, "submit": 0, "cancel": 0, "delete": 0
        },
        {
            "role": "Billing Clerk",
            "permlevel": 0,
            "read": 1, "write": 1, "create": 0, "submit": 0, "cancel": 0, "delete": 0
        }
    ]
    
    # Clear existing permissions and add new ones
    frappe.db.delete("DocPerm", {"parent": "Job Order", "role": ["in", [p["role"] for p in role_permissions]]})
    
    for perm in role_permissions:
        perm_doc = frappe.get_doc({
            "doctype": "DocPerm",
            "parent": "Job Order",
            "parenttype": "DocType",
            "parentfield": "permissions",
            **perm
        })
        perm_doc.insert(ignore_permissions=True)
    
    print("Setup workflow permissions")

def enable_job_order_workflow():
    """Enable workflow for Job Order DocType."""
    # Update Job Order DocType to use workflow
    job_order_meta = frappe.get_doc("DocType", "Job Order")
    
    # Set workflow settings
    if not job_order_meta.has_web_view:
        job_order_meta.has_web_view = 0
    
    job_order_meta.save(ignore_permissions=True)
    
    # Link workflow to DocType
    workflow_name = "Job Order Workflow"
    if frappe.db.exists("Workflow", workflow_name):
        workflow_doc = frappe.get_doc("Workflow", workflow_name)
        workflow_doc.document_type = "Job Order"
        workflow_doc.is_active = 1
        workflow_doc.save(ignore_permissions=True)
        
        print(f"Enabled workflow for Job Order: {workflow_name}")

def setup_notification_templates():
    """Create email templates for workflow notifications."""
    templates = [
        {
            "name": "Job Order Phase Transition",
            "subject": "Job Order {job_number} - Phase Updated to {to_phase}",
            "response": """
Dear Team,

Job Order {job_number} has been transitioned from {from_phase} to {to_phase}.

Project: {project_name}
Customer: {customer_name}
Transition Date: {transition_date}
User: {user}

Please take appropriate action as per the new phase requirements.

Best regards,
API Industrial Services
            """
        },
        {
            "name": "Job Order Escalation Alert",
            "subject": "ESCALATION: Job Order {job_number} requires attention",
            "response": """
ATTENTION REQUIRED

Job Order {job_number} has been in {current_phase} phase for an extended period and requires immediate attention.

Project: {project_name}
Customer: {customer_name}
Current Phase: {current_phase}
Days in Phase: {days_in_phase}

Please review and take appropriate action to move this job forward.

API Industrial Services
            """
        }
    ]
    
    for template in templates:
        if not frappe.db.exists("Email Template", template["name"]):
            email_template = frappe.get_doc({
                "doctype": "Email Template",
                "name": template["name"],
                "subject": template["subject"],
                "response": template["response"],
                "use_html": 0
            })
            email_template.insert(ignore_permissions=True)
            print(f"Created email template: {template['name']}")

def reset_workflow():
    """Reset the workflow setup (for development/testing)."""
    try:
        # Disable workflow
        if frappe.db.exists("Workflow", "Job Order Workflow"):
            workflow = frappe.get_doc("Workflow", "Job Order Workflow")
            workflow.is_active = 0
            workflow.save(ignore_permissions=True)
        
        # Delete workflow history
        frappe.db.delete("Job Order Workflow History")
        
        # Reset job orders to default state
        job_orders = frappe.get_all("Job Order", fields=["name"])
        for job in job_orders:
            job_doc = frappe.get_doc("Job Order", job.name)
            job_doc.workflow_state = "Submission"
            job_doc.save(ignore_permissions=True)
        
        frappe.db.commit()
        print("✅ Workflow reset completed")
        
    except Exception as e:
        frappe.db.rollback()
        print(f"❌ Workflow reset failed: {str(e)}")

# CLI commands for bench
def execute():
    """Execute workflow setup via bench command."""
    setup_job_order_workflow()

if __name__ == "__main__":
    setup_job_order_workflow()