app_name = "api_next"
app_title = "API Industrial Services"
app_publisher = "API Industrial Services Inc."
app_description = "Field/Shop Services ERP System"
app_email = "support@api-industrial.com"
app_license = "Proprietary"
app_icon = "octicon octicon-tools"
app_color = "#1E4A8B"
app_logo_url = "/assets/api_next/images/logo.png"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "api_next",
# 		"logo": "/assets/api_next/logo.png",
# 		"title": "API Next",
# 		"route": "/api_next",
# 		"has_permission": "api_next.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = [
	"/assets/api_next/css/job_dashboard.css",
	"/assets/api_next/css/custom_branding.css"
]
app_include_js = [
	"/assets/api_next/js/components/dashboard_utils.js",
	"/assets/api_next/js/components/kanban_board.js",
	"/assets/api_next/js/components/calendar_view.js"
]

# include js, css files in header of web template
# web_include_css = "/assets/api_next/css/api_next.css"
# web_include_js = "/assets/api_next/js/api_next.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "api_next/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
page_js = {
	"job-order-dashboard": "public/js/page/job_order_dashboard/job_order_dashboard.js"
}

# include js in doctype views
doctype_js = {
	"Job Material Requisition": "public/js/job_material_requisition.js"
}
doctype_list_js = {
	"Job Material Requisition": "public/js/job_material_requisition_list.js"
}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "api_next/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "api_next.utils.jinja_methods",
# 	"filters": "api_next.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "api_next.install.before_install"
# after_install = "api_next.permissions.setup.setup_api_next_permissions"

# Fixtures
# --------

fixtures = [
	{
		"dt": "Page",
		"filters": {
			"name": ["in", ["job-order-dashboard"]]
		}
	}
]

# Uninstallation
# ------------

# before_uninstall = "api_next.uninstall.before_uninstall"
# after_uninstall = "api_next.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "api_next.utils.before_app_install"
# after_app_install = "api_next.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "api_next.utils.before_app_uninstall"
# after_app_uninstall = "api_next.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "api_next.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
	"Job Order": "api_next.permissions.role_manager.get_job_order_permission_query_conditions",
}

has_permission = {
	"Job Order": "api_next.permissions.role_manager.has_job_order_permission",
}

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
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
	},
	"Job Material Requisition": {
		"validate": "api_next.permissions.field_permissions.validate_field_permissions_on_save",
		"before_load": "api_next.permissions.field_permissions.apply_field_permissions_to_form"
	},
	# ERPNext Integration Events
	"Material Request": {
		"on_submit": "api_next.materials_management.utils.erpnext_integration.handle_material_request_update",
		"on_update_after_submit": "api_next.materials_management.utils.erpnext_integration.handle_material_request_update",
		"on_cancel": "api_next.materials_management.utils.erpnext_integration.handle_material_request_update"
	},
	"Purchase Order": {
		"on_submit": "api_next.materials_management.utils.erpnext_integration.handle_purchase_order_update",
		"on_update_after_submit": "api_next.materials_management.utils.erpnext_integration.handle_purchase_order_update"
	},
	"Stock Entry": {
		"on_submit": "api_next.materials_management.utils.erpnext_integration.handle_stock_entry_submit"
	}
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"api_next.permissions.doctype.role_delegation.role_delegation.check_and_activate_delegations",
		"api_next.permissions.doctype.role_delegation.role_delegation.check_and_deactivate_expired_delegations",
		"api_next.materials_management.notifications.check_overdue_requisitions",
		"api_next.materials_management.notifications.send_daily_summary"
	],
	"hourly": [
		"api_next.materials_management.utils.erpnext_integration.schedule_recurring_sync"
	]
}

# Testing
# -------

# before_tests = "api_next.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "api_next.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "api_next.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["api_next.utils.before_request"]
# after_request = ["api_next.utils.after_request"]

# Job Events
# ----------
# before_job = ["api_next.utils.before_job"]
# after_job = ["api_next.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"api_next.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

