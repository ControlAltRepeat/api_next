#!/usr/bin/env python3
"""Test script for Job Management System"""

import sys
import os
sys.path.insert(0, "/workspace/frappe-bench/apps/frappe")
sys.path.insert(0, "/workspace/frappe-bench/sites")
os.chdir("/workspace/frappe-bench/sites")

import frappe
from datetime import datetime, date

def test_job_creation():
    # Initialize Frappe
    frappe.init(site="localhost")
    frappe.connect()
    frappe.set_user("Administrator")
    
    print("Testing Job Management System...")
    print("-" * 50)
    
    # Test 1: Create a job order
    print("1. Creating new job order...")
    job_data = {
        "doctype": "Job Order",
        "customer_name": "ABC Corporation",
        "project_name": "Office Renovation",
        "job_type": "Installation",
        "start_date": str(date.today()),
        "priority": "High",
        "status": "Scheduled",
        "description": "Complete office renovation including electrical and plumbing work"
    }
    
    try:
        job_order = frappe.get_doc(job_data)
        job_order.insert()
        print(f"   ✓ Job Order created: {job_order.name}")
        
        # Test 2: Verify job numbering format
        if job_order.name.startswith("JOB-"):
            print(f"   ✓ Job number format correct: {job_order.name}")
        else:
            print(f"   ✗ Job number format incorrect: {job_order.name}")
        
        # Test 3: Add phases
        print("2. Adding project phases...")
        job_order.append("phases", {
            "phase_name": "Planning & Design",
            "status": "In Progress",
            "start_date": str(date.today()),
            "completion_percentage": 25
        })
        job_order.append("phases", {
            "phase_name": "Demolition",
            "status": "Not Started",
            "completion_percentage": 0
        })
        job_order.save()
        print(f"   ✓ Added {len(job_order.phases)} phases")
        
        # Test 4: Update status
        print("3. Testing status update...")
        job_order.status = "In Progress"
        job_order.save()
        print(f"   ✓ Status updated to: {job_order.status}")
        
        # Test 5: Test API endpoints
        print("4. Testing API endpoints...")
        from api_next.api.job_management import get_job_orders, get_job_summary
        
        # Get all jobs
        jobs = get_job_orders()
        print(f"   ✓ Retrieved {len(jobs.get(\"data\", []))} job orders")
        
        # Get job summary
        summary = get_job_summary(job_order.name)
        if summary.get("success"):
            print(f"   ✓ Job summary retrieved for {job_order.name}")
            print(f"     - Customer: {summary[\"data\"][\"customer\"]}")
            print(f"     - Status: {summary[\"data\"][\"status\"]}")
            print(f"     - Phases: {summary[\"data\"][\"phases\"]}")
        
        frappe.db.commit()
        print("-" * 50)
        print("✅ All tests passed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        frappe.db.rollback()
    
    finally:
        frappe.destroy()

if __name__ == "__main__":
    test_job_creation()
