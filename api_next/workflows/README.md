# Job Order Workflow System

This document provides comprehensive documentation for the 9-phase Job Order workflow system implemented in the API_Next ERP project.

## Overview

The Job Order Workflow system manages the complete lifecycle of job orders from initial submission through final archival. It enforces business rules, role-based permissions, and provides comprehensive audit trails.

## Architecture

### Core Components

1. **JobOrderWorkflow** - Main workflow state machine
2. **BusinessRulesEngine** - Flexible rules evaluation
3. **WorkflowNotificationManager** - Notification handling
4. **Job Order Workflow History** - Audit trail tracking

### 9-Phase Workflow

| Phase | Description | Key Activities |
|-------|-------------|----------------|
| 1. Submission | Initial job request | Job details entry, basic validation |
| 2. Estimation | Cost and time estimates | Material lists, labor estimates, pricing |
| 3. Client Approval | Customer approval | Client review, contract terms, approval |
| 4. Planning | Resource allocation | Team assignment, scheduling, permits |
| 5. Prework | Preparation phase | Material ordering, equipment prep |
| 6. Execution | Active work | On-site work, progress tracking |
| 7. Review | Quality assurance | Quality checks, client walkthrough |
| 8. Invoicing | Billing process | Invoice generation, payment processing |
| 9. Closeout | Final documentation | Document archival, project closure |

### Special States

- **Archived** - Final completed state
- **Cancelled** - Cancelled jobs (can be reactivated)

## Implementation Files

### Core Workflow Files

```
api_next/workflows/
├── __init__.py                    # Module initialization
├── job_order_workflow.py          # Main workflow state machine
├── business_rules_engine.py       # Business rules evaluation
├── notification_manager.py        # Notification handling
├── setup_workflow.py             # Setup and installation
├── test_workflow.py               # Testing utilities
└── README.md                      # This documentation
```

### DocType Integration

```
api_next/job_management/doctype/
├── job_order/
│   ├── job_order.json            # Enhanced with workflow fields
│   └── job_order.py              # Workflow integration methods
└── job_order_workflow_history/
    ├── job_order_workflow_history.json  # Audit trail DocType
    └── job_order_workflow_history.py    # History tracking logic
```

### Fixtures and Configuration

```
api_next/fixtures/
├── workflow_job_order.json       # Frappe workflow definition
└── roles_job_workflow.json       # Required roles definition
```

### Frontend Components

```
api_next/public/js/
└── job_order_workflow_dashboard.js  # Workflow monitoring dashboard
```

## Setup Instructions

### 1. Install the Workflow System

```bash
# Via bench console
bench console
>>> from api_next.workflows.setup_workflow import setup_job_order_workflow
>>> setup_job_order_workflow()

# Or via Python script
cd /path/to/frappe-bench
python -c "
import frappe
frappe.init(site='your-site')
frappe.connect()
from api_next.workflows.setup_workflow import setup_job_order_workflow
setup_job_order_workflow()
"
```

### 2. Test the Installation

```bash
# Run workflow tests
bench console
>>> from api_next.workflows.test_workflow import run_all_tests
>>> run_all_tests()
```

### 3. Migrate Database

```bash
bench migrate
```

## Usage Guide

### Basic Workflow Operations

#### 1. Transition a Job Order

```python
# Via API
job_order = frappe.get_doc("Job Order", "JOB-25-00001")
result = job_order.transition_workflow("Estimation", "Moving to estimation phase")

# Via workflow class
from api_next.workflows.job_order_workflow import JobOrderWorkflow
result = JobOrderWorkflow.execute_transition(job_order, "Estimation", comment="Ready for estimation")
```

#### 2. Validate Transitions

```python
from api_next.workflows.job_order_workflow import JobOrderWorkflow

# Check if transition is valid
validation = JobOrderWorkflow.validate_transition(job_order, "Submission", "Estimation")
if validation["valid"]:
    print("Transition is allowed")
else:
    print(f"Transition blocked: {validation['message']}")
```

#### 3. Get Workflow Information

```python
# Get current workflow status
job_order = frappe.get_doc("Job Order", "JOB-25-00001")
workflow_info = job_order.get_workflow_info()

# Get phase summary
phase_summary = job_order.get_phase_summary()
```

### Business Rules Configuration

#### 1. Evaluate Rules

```python
from api_next.workflows.business_rules_engine import BusinessRulesEngine

rules_engine = BusinessRulesEngine()
context = {
    "total_cost": 15000,
    "priority": "Urgent",
    "has_materials": True
}

results = rules_engine.evaluate(context)
```

#### 2. Add Custom Rules

```python
custom_rule = {
    "name": "high_value_approval",
    "type": "approval",
    "conditions": [
        {
            "field": "total_cost",
            "operator": ">",
            "value": 50000
        }
    ],
    "actions": [
        {
            "type": "require_approval",
            "role": "Operations Manager"
        }
    ]
}

rules_engine.add_custom_rule(custom_rule)
```

### Workflow History and Analytics

#### 1. Get Job Workflow Summary

```python
from api_next.job_management.doctype.job_order_workflow_history.job_order_workflow_history import JobOrderWorkflowHistory

summary = JobOrderWorkflowHistory.get_job_workflow_summary("JOB-25-00001")
print(f"Total transitions: {summary['total_transitions']}")
print(f"Current phase: {summary['current_phase']}")
```

#### 2. Get System-wide Metrics

```python
metrics = JobOrderWorkflowHistory.get_workflow_metrics()
print(f"Completion rate: {metrics['completion_rate']}%")
print(f"Average completion time: {metrics['average_completion_time_hours']} hours")
```

## Role-Based Permissions

### Workflow Roles

| Role | Phases | Permissions |
|------|--------|-------------|
| Job Coordinator | Submission | Create, Submit |
| Estimator | Estimation | Edit, Approve |
| Client | Client Approval | View, Approve |
| Sales Manager | Client Approval | Edit, Approve |
| Project Manager | All | Full Access |
| Resource Coordinator | Planning | Edit, Approve |
| Site Supervisor | Prework, Execution | Edit, Progress |
| Technician | Execution | View, Update |
| Quality Inspector | Review | Edit, Approve |
| Billing Clerk | Invoicing | Edit, Generate |
| Accountant | Invoicing | Approve, Process |
| Document Controller | Closeout | Archive, Manage |

### Permission Matrix

Each phase has specific permissions:
- **View**: Can see the job order
- **Edit**: Can modify phase-specific fields
- **Approve**: Can transition to next phase
- **Full Access**: All operations (Project Manager, System Manager)

## API Reference

### Job Order Methods

```python
# Workflow transition
job_order.transition_workflow(new_state, comment=None)

# Get workflow information
job_order.get_workflow_info()

# Get phase summary
job_order.get_phase_summary()

# Update workflow timestamps
job_order.update_workflow_timestamps()
```

### Workflow Class Methods

```python
# Get phase configuration
JobOrderWorkflow.get_phase_config(phase_name)

# Get valid transitions
JobOrderWorkflow.get_valid_transitions(current_phase)

# Validate transition
JobOrderWorkflow.validate_transition(doc, from_state, to_state, user)

# Execute transition
JobOrderWorkflow.execute_transition(doc, new_state, user, comment)
```

### Business Rules Methods

```python
# Evaluate rules
BusinessRulesEngine.evaluate(context, rule_type)

# Execute single rule
BusinessRulesEngine.execute_rule(rule, context)

# Add custom rule
BusinessRulesEngine.add_custom_rule(rule)
```

## Configuration Options

### Workflow Phases

Phases can be configured by modifying the `PHASES` dictionary in `JobOrderWorkflow`:

```python
PHASES = {
    "Phase Name": {
        "phase_order": 1,
        "transitions": ["Next Phase"],
        "required_fields": ["field1", "field2"],
        "permissions": {
            "submit": ["Role1", "Role2"]
        },
        "auto_actions": ["action1", "action2"],
        "validation_rules": ["rule1", "rule2"],
        "escalation": {
            "timeout_days": 7,
            "escalate_to": ["Manager Role"]
        }
    }
}
```

### Business Rules

Rules are defined in `BusinessRulesEngine._get_applicable_rules()`:

```python
{
    "name": "rule_name",
    "type": "rule_type",
    "description": "Rule description",
    "conditions": [
        {
            "field": "field_name",
            "operator": "==",
            "value": "expected_value",
            "logic": "AND"
        }
    ],
    "actions": [
        {
            "type": "action_type",
            "parameter": "value"
        }
    ]
}
```

### Notification Templates

Templates are configured in `WorkflowNotificationManager._load_notification_templates()`:

```python
{
    "template_name": {
        "subject": "Email subject with {placeholders}",
        "body": "Email body with {placeholders}"
    }
}
```

## Troubleshooting

### Common Issues

1. **Workflow not appearing**: Ensure workflow is active and linked to Job Order DocType
2. **Permission denied**: Check user roles and workflow state permissions
3. **Validation failures**: Review required fields and business rules
4. **Notification not sent**: Verify email settings and recipient roles

### Debug Mode

Enable debug logging for workflow operations:

```python
frappe.flags.debug_workflow = True
```

### Reset Workflow

To reset the workflow system:

```python
from api_next.workflows.setup_workflow import reset_workflow
reset_workflow()
```

## Performance Considerations

1. **Database Indexing**: Workflow state and transition dates are indexed
2. **Bulk Operations**: Use batch processing for large datasets
3. **Notification Queuing**: Notifications are queued for background processing
4. **History Archival**: Consider archiving old workflow history records

## Security

1. **Role-based Access**: All transitions require appropriate roles
2. **Audit Trail**: Complete history of all state changes
3. **IP Tracking**: Source IP addresses logged for transitions
4. **Permission Validation**: Multi-level permission checks

## Integration Points

### ERPNext Integration

The workflow integrates with standard ERPNext modules:
- **User and Role Management**
- **Email System**
- **Notification Framework**
- **Report Builder**

### Custom Integration

Extend the workflow by:
1. Adding custom validation rules
2. Creating custom auto-actions
3. Implementing custom notification channels
4. Adding phase-specific business logic

## Future Enhancements

Planned improvements:
1. **Parallel Workflows**: Support for parallel approval chains
2. **Conditional Routing**: Dynamic phase routing based on conditions
3. **Mobile Notifications**: Push notifications for mobile apps
4. **AI-powered Insights**: Machine learning for bottleneck prediction
5. **External Integrations**: API connections to external systems

## Support

For technical support:
1. Check logs: `bench logs`
2. Review error logs: `bench show-config`
3. Enable debug mode: `frappe.flags.debug_workflow = True`
4. Run tests: `python api_next/workflows/test_workflow.py`

## License

Copyright (c) 2025, API Next and contributors
For license information, please see license.txt