# API_Next ERP Permission System

A comprehensive role-based permission system with field-level access control, workflow-based permissions, and delegation capabilities.

## Overview

The API_Next permission system provides:

- **9 Custom Roles** tailored to the job workflow
- **Workflow-Based Permissions** that adapt to job phases  
- **Field-Level Access Control** for sensitive data protection
- **Role Delegation System** for vacation coverage and approval workflows
- **Performance-Optimized** permission checks
- **Comprehensive Testing** suite

## Custom Roles

### Management Roles
- **API Manager** - Senior management with full system access
- **Job Manager** - Overall job oversight and strategic decisions

### Operational Roles  
- **Estimator** - Creates and modifies job estimates
- **Planner** - Resource allocation and scheduling
- **Materials Coordinator** - Materials requisition and inventory
- **Field Supervisor** - On-site execution management
- **Quality Inspector** - Review phase and quality control
- **Billing Clerk** - Invoicing and financial operations

### General Access
- **API Employee** - Basic employee with limited access

## Permission Matrix

| Role | Job Order | Materials | Labor | Financial Data | Settings |
|------|-----------|-----------|-------|----------------|----------|
| API Manager | Full | Full | Full | ✅ | ✅ |
| Job Manager | Full | Full | Full | ✅ | ❌ |
| Estimator | Phase-based | Read | Read | ❌ | ❌ |
| Planner | Phase-based | Read | Full | ❌ | ❌ |
| Materials Coordinator | Phase-based | Full | Read | ❌ | ❌ |
| Field Supervisor | Phase-based | Read | Full | ❌ | ❌ |
| Quality Inspector | Phase-based | Read | Read | ❌ | ❌ |
| Billing Clerk | Phase-based | Read | Read | ✅ | ❌ |
| API Employee | Owner only | ❌ | Own entries | ❌ | ❌ |

## Workflow-Based Permissions

Permissions automatically adapt based on job workflow phase:

### Submission Phase
- **Editable**: Basic job details, customer info, scope
- **Readonly**: Workflow state, calculated fields
- **Access**: Job Manager, API Manager

### Estimation Phase  
- **Editable**: Estimates, material requirements, scope refinements
- **Readonly**: Customer details, workflow state
- **Access**: Estimator, Job Manager, API Manager

### Planning Phase
- **Editable**: Team assignment, resource allocation, scheduling
- **Readonly**: Estimates, customer details
- **Access**: Planner, Job Manager, API Manager

### Execution Phase
- **Editable**: Labor tracking, material usage, progress updates
- **Readonly**: Planning details, estimates
- **Access**: Field Supervisor, Job Manager, API Manager

### Review Phase
- **Editable**: Quality notes, review comments, inspection results
- **Readonly**: Execution data, planning details  
- **Access**: Quality Inspector, Job Manager, API Manager

### Invoicing Phase
- **Editable**: Billing details, invoice information
- **Readonly**: All operational data
- **Access**: Billing Clerk, Job Manager, API Manager

## Field-Level Permissions

### Financial Fields (Restricted Access)
- `total_material_cost`, `total_labor_cost`
- `estimated_cost`, `actual_cost`, `profit_margin`
- `billing_rate`, `cost_rate`
- **Access**: Job Manager, API Manager, Billing Clerk only

### Sensitive Fields (Management Only)
- `internal_notes`, `confidential_remarks`
- `profit_analysis`, `competitor_pricing`
- **Access**: Job Manager, API Manager only

### Calculated Fields (Always Readonly)
- `workflow_state`, `phase_start_date`
- `total_labor_hours`, `job_number`

## Role Delegation System

### Delegation Types
1. **Full Role** - Delegate complete role permissions
2. **Specific DocTypes** - Delegate access to certain document types
3. **Specific Documents** - Delegate access to individual documents
4. **Approval Only** - Delegate approval permissions only

### Delegation Features
- **Automatic Activation** - Based on date ranges
- **Expiration Handling** - Auto-deactivation of expired delegations
- **Notification System** - Email alerts for delegations
- **Audit Trail** - Complete logging of delegation activities
- **Vacation Coverage** - Seamless handover mechanisms

### Usage Example
```python
# Create a delegation for vacation coverage
delegation = frappe.get_doc({
    "doctype": "Role Delegation",
    "delegator": "job.manager@api.com",
    "delegatee": "backup.manager@api.com", 
    "delegation_type": "Full Role",
    "specific_roles": [{"role": "Job Manager"}],
    "start_date": "2024-12-01",
    "end_date": "2024-12-15",
    "delegation_reason": "Vacation",
    "auto_activate": 1
})
delegation.insert()
```

## API Usage

### Check User Permissions
```python
import frappe
from api_next.permissions.role_manager import APINextRoleManager

# Check if user can access workflow phase
can_access = APINextRoleManager.can_access_phase(
    user_roles=["Estimator"], 
    workflow_state="Estimation"
)

# Check financial data access
can_see_costs = APINextRoleManager.can_access_financial_data(
    user_roles=["Job Manager"]
)

# Get user's role hierarchy level
hierarchy_level = APINextRoleManager.get_user_role_hierarchy_level(
    user_roles=["Job Manager", "API Employee"]
)
```

### Field-Level Permissions
```python
from api_next.permissions.field_permissions import FieldPermissionManager

# Get field permissions for a document
permissions = FieldPermissionManager.get_field_permissions(
    doctype="Job Order",
    doc=job_order,
    user="estimator@api.com"
)

# Filter document fields based on permissions
filtered_doc = FieldPermissionManager.filter_document_fields(
    doc=job_order,
    user="estimator@api.com"
)
```

### Client-Side Permission Checks
```javascript
// Check phase access from frontend
frappe.call({
    method: "api_next.permissions.role_manager.check_phase_access",
    args: {
        workflow_state: "Estimation"
    },
    callback: function(r) {
        if (r.message) {
            // User can access this phase
        }
    }
});

// Check financial data access
frappe.call({
    method: "api_next.permissions.role_manager.check_financial_access",
    callback: function(r) {
        if (r.message) {
            // Show financial fields
        } else {
            // Hide financial fields
        }
    }
});
```

## Setup and Installation

### Automatic Setup
Permissions are automatically configured during app installation via the `after_install` hook.

### Manual Setup
```bash
# Install permissions
bench console
>>> from api_next.permissions.setup import setup_api_next_permissions
>>> setup_api_next_permissions()

# Validate setup
>>> from api_next.permissions.setup import validate_permission_setup
>>> validate_permission_setup()
```

### Reset Permissions (Caution)
```bash
bench console  
>>> from api_next.permissions.setup import reset_permissions
>>> reset_permissions()
```

## Testing

### Run Permission Tests
```bash
# Run all permission tests
bench console
>>> from api_next.permissions.tests.test_role_permissions import run_permission_tests
>>> run_permission_tests()

# Run performance tests
>>> from api_next.permissions.tests.test_performance import run_performance_tests  
>>> run_performance_tests()
```

### Test Coverage
- **Role Hierarchy Tests** - Verify role level calculations
- **Phase Access Tests** - Validate workflow-based permissions
- **Field Permission Tests** - Check field-level access control
- **Delegation Tests** - Test delegation creation and validation
- **Performance Tests** - Ensure system scalability
- **Integration Tests** - Verify cross-component functionality

## Performance Considerations

### Optimization Features
- **Role hierarchy caching** for faster lookups
- **Bulk permission checks** for list views
- **Minimal database queries** for permission validation
- **Efficient field filtering** algorithms

### Performance Benchmarks
- Role hierarchy calculation: < 1ms
- Field permission lookup: < 10ms  
- Document filtering: < 50ms
- Bulk operations (100 docs): < 5s

## Security Features

### Data Protection
- **Financial data isolation** from unauthorized roles
- **Sensitive field masking** for lower-privilege users
- **Workflow state validation** prevents unauthorized transitions
- **Audit logging** for all permission changes

### Access Control
- **Phase-based restrictions** limit access to current workflow stage
- **Owner-based permissions** for API Employees
- **Delegation boundaries** prevent privilege escalation
- **Query-level filtering** ensures data isolation

## Troubleshooting

### Common Issues

1. **Permission Denied Errors**
   - Verify user has required role
   - Check workflow phase access
   - Validate field-level permissions

2. **Delegation Not Working**
   - Check delegation is active and within date range
   - Verify delegator has roles being delegated
   - Ensure no conflicting delegations

3. **Performance Issues**
   - Review query conditions for list views
   - Check for inefficient permission queries
   - Consider caching optimization

### Debug Commands
```python
# Check user's effective roles
frappe.get_roles("user@example.com")

# View active delegations
from api_next.permissions.doctype.role_delegation.role_delegation import get_active_delegations_for_user
get_active_delegations_for_user("user@example.com")

# Test permission query
from api_next.permissions.role_manager import get_job_order_permission_query_conditions
get_job_order_permission_query_conditions("user@example.com")
```

## File Structure

```
api_next/permissions/
├── __init__.py
├── README.md
├── role_manager.py              # Core role and permission logic
├── field_permissions.py        # Field-level access control
├── setup.py                    # Installation and configuration
├── doctype/
│   └── role_delegation/        # Delegation system DocType
├── tests/
│   ├── test_role_permissions.py # Core permission tests
│   └── test_performance.py     # Performance benchmarks
└── fixtures/
    └── custom_role.json        # Role definitions
```

## Integration Points

### Frappe Hooks
- `after_install` - Automatic permission setup
- `doc_events` - Field permission validation
- `scheduler_events` - Delegation management
- `permission_query_conditions` - List view filtering
- `has_permission` - Document access control

### Workflow Integration
- Automatic permission adaptation to workflow phases
- Transition validation based on user roles
- Phase-specific field access control

### ERPNext Integration  
- Compatible with standard ERPNext permission system
- Extends DocType permissions with custom logic
- Maintains audit trail through standard mechanisms

## Future Enhancements

### Planned Features
- **Permission caching system** for improved performance
- **Advanced delegation rules** with conditional logic
- **Time-based permission grants** for temporary access
- **Permission analytics dashboard** for administrators
- **Mobile-optimized permission checks** for field workers

### API Extensions
- **GraphQL permission layer** for modern integrations
- **Webhook permission validation** for external systems
- **OAuth2 integration** for third-party applications

---

For technical support and feature requests, please refer to the main API_Next documentation or contact the development team.