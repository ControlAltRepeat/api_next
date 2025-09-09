# API Settings DocType

## Overview
The API Settings DocType is a singleton (single instance) DocType that manages system-wide configuration for the API_Next ERP system. It provides centralized control over job numbering, default values, notifications, and integration settings.

## Features

### Job Number Settings
- Configurable job number format (YY-XXX or JOB-YY-XXXXX)
- Automatic annual reset of job counters
- Tracks current counter and last reset date

### Default Values
- Default job priority (Low, Normal, High, Critical)
- Default labor rate per hour
- Default markup percentage for pricing
- Default tax rate

### Notification Settings
- Email notification toggle
- SMS notification toggle
- Daily digest timing
- Escalation hours for stuck phases

### System Settings
- Auto-archive completed jobs
- Configurable archive delay
- Audit trail controls
- Estimate approval thresholds

### Integration Settings
- ERPNext integration toggle
- Customer synchronization
- Item synchronization
- Accounting dimension configuration

## Usage

### Getting Settings
```python
from api_next.api_next.doctype.api_settings.api_settings import APISettings

# Get singleton instance
settings = APISettings.get_settings()

# Use helper methods
priority = settings.get_default_job_priority()
labor_rate = settings.get_default_labor_rate()
```

### Job Number Generation
```python
# Generate next job number
settings = APISettings.get_settings()
job_number = settings.get_next_job_number()  # Returns "25-001" or "JOB-25-00001"
```

### API Endpoints
```javascript
// Get next job number via API
frappe.call({
    method: 'api_next.api_next.doctype.api_settings.api_settings.get_next_job_number',
    callback: function(r) {
        console.log('Next job number:', r.message);
    }
});

// Get settings via API
frappe.call({
    method: 'api_next.api_next.doctype.api_settings.api_settings.get_api_settings',
    callback: function(r) {
        console.log('Settings:', r.message);
    }
});
```

## Validation Rules

1. **Labor Rate**: Must be non-negative
2. **Markup Percentage**: Must be non-negative
3. **Tax Rate**: Must be between 0 and 100
4. **Escalation Hours**: Must be at least 1
5. **Archive Days**: Required when auto-archive is enabled, must be at least 1
6. **ERPNext Integration**: Must be enabled before enabling customer/item sync

## Permissions
- Only **System Manager** role has full access
- Other roles can read settings but cannot modify

## Integration Points

### Job Order DocType
- Uses API Settings for default priority and job numbering
- Respects approval thresholds for estimates

### Material Requisition
- Uses default markup and tax rates
- Integrates with ERPNext based on sync settings

### Notification System
- Honors email/SMS preferences
- Uses digest timing and escalation rules

### Workflow System
- Uses escalation hours for phase transitions
- Respects audit trail settings

## Installation

The DocType will be automatically created when the api_next app is installed or migrated. Default values are set for immediate use.

## Testing

Run tests with:
```bash
bench run-tests --app api_next --module api_next.api_next.doctype.api_settings.test_api_settings
```

## File Structure
```
api_settings/
├── api_settings.json          # DocType definition
├── api_settings.py           # Controller with business logic
├── api_settings.js           # Frontend form scripts
├── test_api_settings.py      # Unit tests
├── __init__.py              # Python module init
└── README.md               # This documentation
```