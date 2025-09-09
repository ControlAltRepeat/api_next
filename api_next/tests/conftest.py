# Copyright (c) 2025, API Industrial Services Inc. and contributors
# For license information, please see license.txt

"""Pytest configuration and fixtures for API_Next tests."""

import pytest
import frappe
from frappe.utils import get_datetime, now_datetime, add_to_date
from unittest.mock import Mock, patch
import json


@pytest.fixture(scope="session", autouse=True)
def frappe_session():
	"""Initialize Frappe session for all tests."""
	frappe.init(site="test_site")
	frappe.connect()
	yield
	frappe.destroy()


@pytest.fixture(autouse=True)
def setup_test_environment():
	"""Setup and cleanup for each test."""
	# Setup
	frappe.set_user("Administrator")
	frappe.clear_cache()
	
	yield
	
	# Cleanup
	frappe.db.rollback()
	frappe.clear_cache()


@pytest.fixture
def test_employee():
	"""Create a test employee."""
	employee_id = "EMP-TEST-001"
	if not frappe.db.exists("Employee", employee_id):
		employee = frappe.get_doc({
			"doctype": "Employee",
			"employee": employee_id,
			"employee_name": "Test Employee",
			"first_name": "Test",
			"last_name": "Employee",
			"status": "Active"
		})
		employee.insert(ignore_permissions=True)
	return frappe.get_doc("Employee", employee_id)


@pytest.fixture
def test_item():
	"""Create a test item."""
	item_code = "TEST-ITEM-001"
	if not frappe.db.exists("Item", item_code):
		item = frappe.get_doc({
			"doctype": "Item",
			"item_code": item_code,
			"item_name": "Test Item",
			"stock_uom": "Nos",
			"is_stock_item": 1,
			"item_group": "All Item Groups"
		})
		item.insert(ignore_permissions=True)
	return frappe.get_doc("Item", item_code)


@pytest.fixture
def test_customer():
	"""Create a test customer."""
	customer_name = "Test Customer Ltd."
	if not frappe.db.exists("Customer", customer_name):
		customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": customer_name,
			"customer_type": "Company",
			"customer_group": "All Customer Groups",
			"territory": "All Territories"
		})
		customer.insert(ignore_permissions=True)
	return frappe.get_doc("Customer", customer_name)


@pytest.fixture
def test_job_order(test_customer):
	"""Create a test job order."""
	job_order = frappe.get_doc({
		"doctype": "Job Order",
		"customer": test_customer.name,
		"job_title": "Test Job Order",
		"description": "Test job order description",
		"priority": "Medium",
		"estimated_start_date": add_to_date(now_datetime(), days=1),
		"estimated_completion_date": add_to_date(now_datetime(), days=10),
		"project_manager": "Administrator"
	})
	job_order.insert(ignore_permissions=True)
	return job_order


@pytest.fixture
def test_job_material_requisition(test_job_order):
	"""Create a test material requisition."""
	requisition = frappe.get_doc({
		"doctype": "Job Material Requisition",
		"job_order": test_job_order.name,
		"required_date": add_to_date(now_datetime(), days=2),
		"priority": "Medium",
		"status": "Draft",
		"requested_by": "Administrator"
	})
	requisition.insert(ignore_permissions=True)
	return requisition


@pytest.fixture
def mock_erpnext_item():
	"""Mock ERPNext item integration."""
	with patch("frappe.get_doc") as mock_get_doc:
		mock_item = Mock()
		mock_item.name = "TEST-ITEM-001"
		mock_item.item_name = "Test Item"
		mock_item.stock_uom = "Nos"
		mock_item.standard_rate = 100.0
		mock_get_doc.return_value = mock_item
		yield mock_item


@pytest.fixture
def mock_material_request():
	"""Mock ERPNext Material Request."""
	with patch("frappe.get_doc") as mock_get_doc:
		mock_mr = Mock()
		mock_mr.name = "MAT-REQ-001"
		mock_mr.docstatus = 1
		mock_mr.status = "Pending"
		mock_get_doc.return_value = mock_mr
		yield mock_mr


@pytest.fixture
def mock_purchase_order():
	"""Mock ERPNext Purchase Order."""
	with patch("frappe.get_doc") as mock_get_doc:
		mock_po = Mock()
		mock_po.name = "PO-001"
		mock_po.docstatus = 1
		mock_po.status = "To Receive"
		mock_get_doc.return_value = mock_po
		yield mock_po


@pytest.fixture
def test_user_role(request):
	"""Create a test user with specific role."""
	role = getattr(request, 'param', 'Employee')
	user_email = f"test_{role.lower()}@test.com"
	
	if not frappe.db.exists("User", user_email):
		user = frappe.get_doc({
			"doctype": "User",
			"email": user_email,
			"first_name": f"Test {role}",
			"send_welcome_email": 0,
			"roles": [{"role": role}]
		})
		user.insert(ignore_permissions=True)
	
	yield user_email
	
	# Cleanup - reset to Administrator
	frappe.set_user("Administrator")


@pytest.fixture
def performance_timer():
	"""Timer fixture for performance tests."""
	import time
	
	class Timer:
		def __init__(self):
			self.start_time = None
			self.end_time = None
		
		def start(self):
			self.start_time = time.perf_counter()
		
		def stop(self):
			self.end_time = time.perf_counter()
			return self.elapsed()
		
		def elapsed(self):
			if self.start_time and self.end_time:
				return self.end_time - self.start_time
			return None
	
	return Timer()


@pytest.fixture
def mock_notification_send():
	"""Mock notification sending to prevent actual emails/notifications during tests."""
	with patch("frappe.sendmail") as mock_sendmail, \
		 patch("frappe.publish_realtime") as mock_publish:
		yield {
			"sendmail": mock_sendmail,
			"publish_realtime": mock_publish
		}


@pytest.fixture
def test_workflow_data():
	"""Provide test data for workflow tests."""
	return {
		"phases": [
			{"phase_number": 1, "phase_name": "Planning", "status": "Active"},
			{"phase_number": 2, "phase_name": "Procurement", "status": "Pending"},
			{"phase_number": 3, "phase_name": "Mobilization", "status": "Pending"},
			{"phase_number": 4, "phase_name": "Execution", "status": "Pending"},
			{"phase_number": 5, "phase_name": "Quality Control", "status": "Pending"},
			{"phase_number": 6, "phase_name": "Testing", "status": "Pending"},
			{"phase_number": 7, "phase_name": "Commissioning", "status": "Pending"},
			{"phase_number": 8, "phase_name": "Handover", "status": "Pending"},
			{"phase_number": 9, "phase_name": "Close-out", "status": "Pending"}
		],
		"valid_transitions": {
			"Planning": ["Procurement"],
			"Procurement": ["Mobilization"],
			"Mobilization": ["Execution"],
			"Execution": ["Quality Control"],
			"Quality Control": ["Testing"],
			"Testing": ["Commissioning"],
			"Commissioning": ["Handover"],
			"Handover": ["Close-out"],
			"Close-out": []
		}
	}


class MockResponse:
	"""Mock HTTP response for API tests."""
	def __init__(self, json_data, status_code=200):
		self.json_data = json_data
		self.status_code = status_code
	
	def json(self):
		return self.json_data
	
	def raise_for_status(self):
		if self.status_code >= 400:
			raise Exception(f"HTTP {self.status_code}")


@pytest.fixture
def api_test_client():
	"""Create a test client for API tests."""
	from frappe.test_runner import TestClient
	return TestClient(frappe.local.site)


# Pytest markers for test categorization
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.api = pytest.mark.api
pytest.mark.workflow = pytest.mark.workflow
pytest.mark.security = pytest.mark.security
pytest.mark.performance = pytest.mark.performance
pytest.mark.slow = pytest.mark.slow