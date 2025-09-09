import frappe
import json
import os

def create_workspaces():
    """Create and install API_Next workspaces"""
    
    workspace_dir = frappe.get_app_path("api_next", "workspace")
    
    workspaces = [
        "api_next/api_next.json",
        "job_management/job_management.json", 
        "materials_management/materials_management.json",
        "resource_management/resource_management.json"
    ]
    
    for workspace_file in workspaces:
        file_path = os.path.join(workspace_dir, workspace_file)
        
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                workspace_data = json.load(f)
            
            # Check if workspace already exists
            if not frappe.db.exists("Workspace", workspace_data.get("name")):
                # Create new workspace document
                workspace = frappe.new_doc("Workspace")
                workspace.update(workspace_data)
                workspace.insert(ignore_permissions=True)
                print(f"Created workspace: {workspace.name}")
            else:
                # Update existing workspace
                workspace = frappe.get_doc("Workspace", workspace_data.get("name"))
                workspace.update(workspace_data)
                workspace.save(ignore_permissions=True)
                print(f"Updated workspace: {workspace.name}")
    
    frappe.db.commit()
    print("Workspaces setup complete!")

if __name__ == "__main__":
    frappe.init(site="site1.local")
    frappe.connect()
    create_workspaces()
    frappe.destroy()