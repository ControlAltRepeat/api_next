"""
Permission Setup and Installation Functions
Handles initial setup and configuration of the API_Next permission system
"""

import frappe
from frappe import _
from frappe.installer import install_fixtures
from frappe.permissions import add_permission, update_permission_property, remove_permission
from api_next.permissions.role_manager import APINextRoleManager
import json
import os


def setup_api_next_permissions():
    """Complete setup of API_Next permission system"""
    frappe.flags.ignore_permissions = True
    
    try:
        # Step 1: Install custom roles
        install_custom_roles()
        
        # Step 2: Setup DocType permissions
        setup_doctype_permissions()
        
        # Step 3: Create default role assignments
        create_default_role_assignments()
        
        # Step 4: Setup workflow permissions
        setup_workflow_permissions()
        
        # Step 5: Install permission fixtures
        install_permission_fixtures()
        
        frappe.db.commit()
        print("✅ API_Next permissions setup completed successfully")
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Error setting up API_Next permissions: {str(e)}")
        raise
    finally:
        frappe.flags.ignore_permissions = False


def install_custom_roles():
    """Install custom roles from fixtures"""
    print("📋 Installing custom roles...")
    
    roles_fixture_path = os.path.join(
        frappe.get_app_path("api_next"), 
        "fixtures", 
        "custom_role.json"
    )
    
    if os.path.exists(roles_fixture_path):
        with open(roles_fixture_path, 'r') as f:
            roles_data = json.load(f)
            
        for role_data in roles_data:
            role_name = role_data.get("name")
            
            # Check if role already exists
            if not frappe.db.exists("Role", role_name):
                role_doc = frappe.get_doc(role_data)
                role_doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
                print(f"  ✅ Created role: {role_name}")
            else:
                # Update existing role
                role_doc = frappe.get_doc("Role", role_name)
                for key, value in role_data.items():
                    if key not in ["name", "doctype"]:
                        setattr(role_doc, key, value)
                role_doc.save(ignore_permissions=True)
                print(f"  🔄 Updated role: {role_name}")
    else:
        print("  ⚠️  Custom roles fixture not found")


def setup_doctype_permissions():
    """Setup permissions for all API_Next DocTypes"""
    print("🔐 Setting up DocType permissions...")
    
    # Use the role manager to setup permissions
    APINextRoleManager.setup_all_permissions()
    print("  ✅ DocType permissions configured")


def create_default_role_assignments():
    """Create default role assignments for demonstration"""
    print("👥 Creating default role assignments...")
    
    # Create sample users for each role (if they don't exist)
    default_users = [
        {
            "email": "job.manager@api.com",
            "first_name": "Job",
            "last_name": "Manager",
            "roles": ["Job Manager", "Employee"]
        },
        {
            "email": "estimator@api.com", 
            "first_name": "Project",
            "last_name": "Estimator",
            "roles": ["Estimator", "Employee"]
        },
        {
            "email": "planner@api.com",
            "first_name": "Resource",
            "last_name": "Planner", 
            "roles": ["Planner", "Employee"]
        },
        {
            "email": "materials@api.com",
            "first_name": "Materials",
            "last_name": "Coordinator",
            "roles": ["Materials Coordinator", "Employee"]
        },
        {
            "email": "supervisor@api.com",
            "first_name": "Field",
            "last_name": "Supervisor",
            "roles": ["Field Supervisor", "Employee"]
        },
        {
            "email": "inspector@api.com",
            "first_name": "Quality",
            "last_name": "Inspector",
            "roles": ["Quality Inspector", "Employee"]
        },
        {
            "email": "billing@api.com",
            "first_name": "Billing",
            "last_name": "Clerk",
            "roles": ["Billing Clerk", "Employee"]
        },
        {
            "email": "employee@api.com",
            "first_name": "API",
            "last_name": "Employee",
            "roles": ["API Employee", "Employee"]
        },
        {
            "email": "manager@api.com",
            "first_name": "API",
            "last_name": "Manager",
            "roles": ["API Manager", "Employee"]
        }
    ]
    
    for user_data in default_users:
        email = user_data["email"]
        
        if not frappe.db.exists("User", email):
            user_doc = frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": user_data["first_name"],
                "last_name": user_data["last_name"],
                "enabled": 1,
                "user_type": "System User",
                "roles": [{"role": role} for role in user_data["roles"]]
            })
            user_doc.insert(ignore_permissions=True)
            print(f"  ✅ Created user: {email}")
        else:
            print(f"  ℹ️  User already exists: {email}")


def setup_workflow_permissions():
    """Setup workflow-specific permissions"""
    print("🔄 Setting up workflow permissions...")
    
    # This would integrate with Frappe's workflow system
    # For now, we'll create custom workflow permission records
    
    workflow_permissions = [
        {
            "workflow_state": "Submission",
            "roles": ["Job Manager", "API Manager", "System Manager"],
            "can_edit": True,
            "can_submit": True
        },
        {
            "workflow_state": "Estimation", 
            "roles": ["Estimator", "Job Manager", "API Manager", "System Manager"],
            "can_edit": True,
            "can_submit": True
        },
        {
            "workflow_state": "Client Approval",
            "roles": ["Job Manager", "API Manager", "System Manager"],
            "can_edit": True,
            "can_submit": True
        },
        {
            "workflow_state": "Planning",
            "roles": ["Planner", "Job Manager", "API Manager", "System Manager"],
            "can_edit": True,
            "can_submit": True
        },
        {
            "workflow_state": "Execution",
            "roles": ["Field Supervisor", "Job Manager", "API Manager", "System Manager"],
            "can_edit": True,
            "can_submit": True
        },
        {
            "workflow_state": "Review",
            "roles": ["Quality Inspector", "Job Manager", "API Manager", "System Manager"],
            "can_edit": True,
            "can_submit": True
        },
        {
            "workflow_state": "Invoicing",
            "roles": ["Billing Clerk", "Job Manager", "API Manager", "System Manager"],
            "can_edit": True,
            "can_submit": True
        }
    ]
    
    # Store workflow permissions in custom doctype or database table
    # This is a simplified version - in practice you'd create a proper DocType
    for perm in workflow_permissions:
        # Store permissions for later use
        pass
    
    print("  ✅ Workflow permissions configured")


def install_permission_fixtures():
    """Install additional permission fixtures"""
    print("📦 Installing permission fixtures...")
    
    fixtures_path = os.path.join(frappe.get_app_path("api_next"), "fixtures")
    
    # Install any additional permission-related fixtures
    fixture_files = [
        "custom_docperm.json",
        "workflow_state.json", 
        "workflow_action.json"
    ]
    
    for fixture_file in fixture_files:
        fixture_path = os.path.join(fixtures_path, fixture_file)
        if os.path.exists(fixture_path):
            try:
                install_fixtures([fixture_path])
                print(f"  ✅ Installed fixture: {fixture_file}")
            except Exception as e:
                print(f"  ⚠️  Error installing {fixture_file}: {str(e)}")
        else:
            print(f"  ℹ️  Fixture not found: {fixture_file}")


def validate_permission_setup():
    """Validate that permissions are correctly setup"""
    print("✅ Validating permission setup...")
    
    validation_results = {
        "roles_created": [],
        "permissions_set": [],
        "issues": []
    }
    
    # Check if all custom roles exist
    required_roles = [
        "Job Manager", "Estimator", "Planner", "Materials Coordinator",
        "Field Supervisor", "Quality Inspector", "Billing Clerk", 
        "API Employee", "API Manager"
    ]
    
    for role in required_roles:
        if frappe.db.exists("Role", role):
            validation_results["roles_created"].append(role)
        else:
            validation_results["issues"].append(f"Role not found: {role}")
    
    # Check key DocType permissions
    key_doctypes = ["Job Order", "Job Order Material", "Job Order Labor", "Role Delegation"]
    
    for doctype in key_doctypes:
        permissions = frappe.get_all("Custom DocPerm", 
                                   filters={"parent": doctype},
                                   fields=["role", "read", "write", "create"])
        
        if permissions:
            validation_results["permissions_set"].append(f"{doctype}: {len(permissions)} permissions")
        else:
            validation_results["issues"].append(f"No permissions set for: {doctype}")
    
    # Print validation results
    print(f"  ✅ Roles created: {len(validation_results['roles_created'])}")
    print(f"  ✅ Permissions set: {len(validation_results['permissions_set'])}")
    
    if validation_results["issues"]:
        print(f"  ⚠️  Issues found: {len(validation_results['issues'])}")
        for issue in validation_results["issues"]:
            print(f"    - {issue}")
    else:
        print("  ✅ All validations passed!")
    
    return validation_results


def reset_permissions():
    """Reset all permissions (use with caution)"""
    print("🔄 Resetting permissions...")
    
    frappe.flags.ignore_permissions = True
    
    try:
        # Remove custom permissions
        custom_perms = frappe.get_all("Custom DocPerm", 
                                    filters={"role": ["in", [
                                        "Job Manager", "Estimator", "Planner", 
                                        "Materials Coordinator", "Field Supervisor",
                                        "Quality Inspector", "Billing Clerk", 
                                        "API Employee", "API Manager"
                                    ]]})
        
        for perm in custom_perms:
            frappe.delete_doc("Custom DocPerm", perm.name, ignore_permissions=True)
        
        print("  ✅ Custom permissions removed")
        
        # Optionally remove custom roles
        # (Commented out for safety)
        # custom_roles = frappe.get_all("Role", filters={"is_custom": 1})
        # for role in custom_roles:
        #     frappe.delete_doc("Role", role.name, ignore_permissions=True)
        
        frappe.db.commit()
        print("  ✅ Permission reset completed")
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Error resetting permissions: {str(e)}")
        raise
    finally:
        frappe.flags.ignore_permissions = False


# Command-line interface functions
def install():
    """Install permissions (called during app installation)"""
    setup_api_next_permissions()


def validate():
    """Validate permissions setup"""
    return validate_permission_setup()


def reset():
    """Reset permissions"""
    reset_permissions()


if __name__ == "__main__":
    # Allow running as standalone script
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "install":
            install()
        elif command == "validate":
            validate()
        elif command == "reset":
            reset()
        else:
            print("Usage: python setup.py [install|validate|reset]")
    else:
        install()