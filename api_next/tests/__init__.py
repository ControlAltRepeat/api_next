# Copyright (c) 2025, API Industrial Services Inc. and contributors
# For license information, please see license.txt

"""Test module for API_Next ERP system."""

import frappe
import unittest
from frappe.utils import get_datetime, now_datetime, add_to_date


class APINextTestCase(unittest.TestCase):
	"""Base test case class for API_Next tests with common setup and utilities."""
	
	@classmethod
	def setUpClass(cls):
		"""One-time setup for test class."""
		frappe.set_user("Administrator")
		cls.setup_test_data()
	
	@classmethod
	def setup_test_data(cls):
		"""Setup common test data that can be reused across tests."""
		pass
	
	def setUp(self):
		"""Setup for each test method."""
		frappe.clear_cache()
		frappe.set_user("Administrator")
	
	def tearDown(self):
		"""Cleanup after each test."""
		frappe.db.rollback()
		frappe.clear_cache()
	
	def create_test_employee(self, employee_id="EMP-TEST-001", employee_name="Test Employee"):
		"""Create a test employee for labor tests."""
		if not frappe.db.exists("Employee", employee_id):
			employee = frappe.get_doc({
				"doctype": "Employee",
				"employee": employee_id,
				"employee_name": employee_name,
				"first_name": employee_name.split()[0],
				"last_name": employee_name.split()[-1],
				"status": "Active"
			})
			employee.insert(ignore_permissions=True)
			return employee
		return frappe.get_doc("Employee", employee_id)
	
	def create_test_item(self, item_code="TEST-ITEM-001", item_name="Test Item"):
		"""Create a test item for material tests."""
		if not frappe.db.exists("Item", item_code):
			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_name,
				"stock_uom": "Nos",
				"is_stock_item": 1,
				"item_group": "All Item Groups"
			})
			item.insert(ignore_permissions=True)
			return item
		return frappe.get_doc("Item", item_code)
	
	def create_test_customer(self, customer_name="Test Customer Ltd."):
		"""Create a test customer for job order tests."""
		if not frappe.db.exists("Customer", customer_name):
			customer = frappe.get_doc({
				"doctype": "Customer",
				"customer_name": customer_name,
				"customer_type": "Company",
				"customer_group": "All Customer Groups",
				"territory": "All Territories"
			})
			customer.insert(ignore_permissions=True)
			return customer
		return frappe.get_doc("Customer", customer_name)
	
	def assertDocumentEqual(self, doc1, doc2, fields=None):
		"""Assert that two documents are equal for specified fields."""
		if fields is None:
			fields = doc1.meta.get_fieldnames()
		
		for field in fields:
			if field in ["name", "creation", "modified", "modified_by", "owner"]:
				continue
			self.assertEqual(
				getattr(doc1, field, None),
				getattr(doc2, field, None),
				f"Field '{field}' does not match: {getattr(doc1, field, None)} != {getattr(doc2, field, None)}"
			)
	
	def assertDateTimeClose(self, dt1, dt2, delta_seconds=60):
		"""Assert that two datetime values are close within specified seconds."""
		if isinstance(dt1, str):
			dt1 = get_datetime(dt1)
		if isinstance(dt2, str):
			dt2 = get_datetime(dt2)
		
		diff = abs((dt1 - dt2).total_seconds())
		self.assertLessEqual(
			diff, 
			delta_seconds, 
			f"DateTime values are not close enough: {dt1} and {dt2} (diff: {diff}s)"
		)