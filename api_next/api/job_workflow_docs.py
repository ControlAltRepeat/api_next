# Job Workflow API Documentation and Examples
# Comprehensive API documentation with examples and usage guidelines

import frappe
from frappe import _
import json
from typing import Dict, List


# ============================================================================
# API DOCUMENTATION ENDPOINTS
# ============================================================================

@frappe.whitelist(allow_guest=True)
def get_api_documentation():
    """
    Get comprehensive API documentation for job workflow endpoints.
    
    Returns:
        dict: Complete API documentation
    """
    try:
        documentation = {
            "api_version": "1.0.0",
            "base_url": frappe.utils.get_url(),
            "authentication": {
                "methods": ["Session Authentication", "API Key", "Token Authentication"],
                "description": "All endpoints require authentication unless marked as public"
            },
            "endpoints": _get_endpoint_documentation(),
            "examples": _get_api_examples(),
            "error_codes": _get_error_codes(),
            "rate_limiting": {
                "default_limit": "100 requests per hour",
                "rate_limit_headers": ["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]
            },
            "webhook_support": {
                "supported_events": ["phase_transition", "job_created", "job_completed"],
                "security": "HMAC-SHA256 signature verification",
                "retry_policy": "Exponential backoff with 3 retries"
            }
        }
        
        return {
            "success": True,
            "data": documentation,
            "message": "API documentation retrieved successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }


@frappe.whitelist(allow_guest=True)
def get_endpoint_reference(endpoint_name: str = None):
    """
    Get detailed reference for specific endpoint or all endpoints.
    
    Args:
        endpoint_name (str): Specific endpoint name (optional)
    
    Returns:
        dict: Endpoint reference documentation
    """
    try:
        endpoints = _get_endpoint_documentation()
        
        if endpoint_name:
            endpoint_info = next(
                (ep for ep in endpoints if ep["name"] == endpoint_name), 
                None
            )
            
            if not endpoint_info:
                return {
                    "success": False,
                    "error": "NotFound",
                    "message": f"Endpoint '{endpoint_name}' not found"
                }
            
            return {
                "success": True,
                "data": endpoint_info,
                "message": f"Reference for endpoint '{endpoint_name}'"
            }
        
        return {
            "success": True,
            "data": {
                "total_endpoints": len(endpoints),
                "endpoints": endpoints
            },
            "message": "All endpoint references retrieved"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }


@frappe.whitelist(allow_guest=True)
def get_api_examples(category: str = None):
    """
    Get API usage examples.
    
    Args:
        category (str): Example category (transition, reporting, etc.)
    
    Returns:
        dict: API usage examples
    """
    try:
        examples = _get_api_examples()
        
        if category:
            category_examples = examples.get(category)
            if not category_examples:
                return {
                    "success": False,
                    "error": "NotFound",
                    "message": f"No examples found for category '{category}'"
                }
            
            return {
                "success": True,
                "data": {
                    "category": category,
                    "examples": category_examples
                }
            }
        
        return {
            "success": True,
            "data": {
                "categories": list(examples.keys()),
                "examples": examples
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }


# ============================================================================
# DOCUMENTATION DATA GENERATORS
# ============================================================================

def _get_endpoint_documentation() -> List[Dict]:
    """Generate comprehensive endpoint documentation."""
    
    endpoints = [
        # Core Phase Transition Management
        {
            "name": "transition_phase",
            "method": "POST",
            "url": "/api/method/api_next.api.job_workflow.transition_phase",
            "category": "Phase Transitions",
            "description": "Transition a job order to the next phase in the workflow",
            "parameters": {
                "job_order": {"type": "string", "required": True, "description": "Job Order document name"},
                "action": {"type": "string", "required": True, "description": "Workflow action to perform"},
                "comments": {"type": "string", "required": False, "description": "Optional comments for the transition"}
            },
            "response": {
                "success": {"type": "boolean", "description": "Operation success status"},
                "data": {
                    "job_order": {"type": "string", "description": "Job order name"},
                    "old_state": {"type": "string", "description": "Previous workflow state"},
                    "new_state": {"type": "string", "description": "New workflow state"},
                    "action": {"type": "string", "description": "Action performed"},
                    "timestamp": {"type": "datetime", "description": "Transition timestamp"},
                    "user": {"type": "string", "description": "User who performed transition"}
                }
            },
            "required_permissions": ["Job Order: write"],
            "rate_limit": "100 requests/hour",
            "example_request": {
                "job_order": "JOB-25-00001",
                "action": "Request Estimation",
                "comments": "Initial review completed"
            }
        },
        
        {
            "name": "get_available_transitions",
            "method": "GET",
            "url": "/api/method/api_next.api.job_workflow.get_available_transitions",
            "category": "Phase Transitions",
            "description": "Get all available workflow transitions for a job order",
            "parameters": {
                "job_order": {"type": "string", "required": True, "description": "Job Order document name"}
            },
            "response": {
                "success": {"type": "boolean", "description": "Operation success status"},
                "data": {
                    "job_order": {"type": "string", "description": "Job order name"},
                    "current_state": {"type": "string", "description": "Current workflow state"},
                    "available_transitions": {"type": "array", "description": "List of available transitions"}
                }
            },
            "required_permissions": ["Job Order: read"],
            "rate_limit": "200 requests/hour"
        },
        
        {
            "name": "bulk_transition",
            "method": "POST",
            "url": "/api/method/api_next.api.job_workflow.bulk_transition",
            "category": "Bulk Operations",
            "description": "Perform bulk phase transitions on multiple job orders",
            "parameters": {
                "job_orders": {"type": "string", "required": True, "description": "JSON array of job order names"},
                "action": {"type": "string", "required": True, "description": "Workflow action to perform"},
                "comments": {"type": "string", "required": False, "description": "Optional comments"}
            },
            "response": {
                "success": {"type": "boolean", "description": "Operation success status"},
                "data": {
                    "total_processed": {"type": "integer", "description": "Total jobs processed"},
                    "successful": {"type": "integer", "description": "Successfully transitioned jobs"},
                    "failed": {"type": "integer", "description": "Failed transitions"},
                    "results": {"type": "array", "description": "Detailed results for each job"}
                }
            },
            "required_permissions": ["Job Order: write"],
            "rate_limit": "10 requests/hour"
        },
        
        # Status and History Tracking
        {
            "name": "get_workflow_status",
            "method": "GET", 
            "url": "/api/method/api_next.api.job_workflow.get_workflow_status",
            "category": "Status Tracking",
            "description": "Get comprehensive workflow status for a job order",
            "parameters": {
                "job_order": {"type": "string", "required": True, "description": "Job Order document name"}
            },
            "response": {
                "success": {"type": "boolean", "description": "Operation success status"},
                "data": {
                    "job_order": {"type": "string", "description": "Job order name"},
                    "current_state": {"type": "string", "description": "Current workflow state"},
                    "progress_percentage": {"type": "float", "description": "Workflow completion percentage"},
                    "phase_history": {"type": "array", "description": "Phase transition history"},
                    "phase_durations": {"type": "object", "description": "Time spent in each phase"}
                }
            },
            "required_permissions": ["Job Order: read"],
            "rate_limit": "200 requests/hour"
        },
        
        {
            "name": "get_phase_history",
            "method": "GET",
            "url": "/api/method/api_next.api.job_workflow.get_phase_history", 
            "category": "Status Tracking",
            "description": "Get detailed phase transition history for a job order",
            "parameters": {
                "job_order": {"type": "string", "required": True, "description": "Job Order document name"},
                "include_details": {"type": "boolean", "required": False, "description": "Include detailed information"}
            },
            "response": {
                "success": {"type": "boolean", "description": "Operation success status"},
                "data": {
                    "job_order": {"type": "string", "description": "Job order name"},
                    "history_count": {"type": "integer", "description": "Number of history entries"},
                    "history": {"type": "array", "description": "Detailed phase history"}
                }
            },
            "required_permissions": ["Job Order: read"],
            "rate_limit": "200 requests/hour"
        },
        
        # Dashboard and Reporting
        {
            "name": "get_jobs_by_phase",
            "method": "GET",
            "url": "/api/method/api_next.api.job_workflow.get_jobs_by_phase",
            "category": "Reporting",
            "description": "Get job orders grouped by workflow phase",
            "parameters": {
                "phase": {"type": "string", "required": False, "description": "Specific phase filter"},
                "limit": {"type": "integer", "required": False, "description": "Number of records to return (default: 20)"},
                "offset": {"type": "integer", "required": False, "description": "Pagination offset (default: 0)"}
            },
            "response": {
                "success": {"type": "boolean", "description": "Operation success status"},
                "data": {
                    "grouped_by_phase": {"type": "object", "description": "Jobs grouped by phase"},
                    "total_jobs": {"type": "integer", "description": "Total number of jobs"}
                }
            },
            "required_permissions": ["Job Order: read"],
            "rate_limit": "100 requests/hour"
        },
        
        {
            "name": "get_phase_metrics",
            "method": "GET",
            "url": "/api/method/api_next.api.job_workflow.get_phase_metrics",
            "category": "Analytics",
            "description": "Get comprehensive metrics for all workflow phases",
            "parameters": {
                "date_range": {"type": "string", "required": False, "description": "Days to analyze (default: 30)"}
            },
            "response": {
                "success": {"type": "boolean", "description": "Operation success status"},
                "data": {
                    "period": {"type": "string", "description": "Analysis period"},
                    "phase_metrics": {"type": "object", "description": "Metrics for each phase"},
                    "overall_metrics": {"type": "object", "description": "Overall workflow metrics"}
                }
            },
            "required_permissions": ["Job Order: read"],
            "rate_limit": "50 requests/hour"
        },
        
        {
            "name": "get_bottleneck_analysis",
            "method": "GET", 
            "url": "/api/method/api_next.api.job_workflow.get_bottleneck_analysis",
            "category": "Analytics",
            "description": "Analyze workflow bottlenecks and performance issues",
            "parameters": {
                "date_range": {"type": "string", "required": False, "description": "Days to analyze (default: 30)"}
            },
            "response": {
                "success": {"type": "boolean", "description": "Operation success status"},
                "data": {
                    "analysis_period": {"type": "string", "description": "Analysis period"},
                    "bottlenecks": {"type": "array", "description": "Identified bottlenecks"},
                    "efficiency_metrics": {"type": "object", "description": "Phase efficiency metrics"},
                    "recommendations": {"type": "array", "description": "Improvement recommendations"}
                }
            },
            "required_permissions": ["Job Order: read"],
            "rate_limit": "20 requests/hour"
        },
        
        # Advanced Features
        {
            "name": "schedule_phase_transition",
            "method": "POST",
            "url": "/api/method/api_next.api.job_workflow_advanced.schedule_phase_transition",
            "category": "Advanced Features",
            "description": "Schedule a phase transition for future execution",
            "parameters": {
                "job_order": {"type": "string", "required": True, "description": "Job Order document name"},
                "action": {"type": "string", "required": True, "description": "Workflow action to perform"},
                "scheduled_date": {"type": "datetime", "required": True, "description": "Date/time to execute transition"},
                "comments": {"type": "string", "required": False, "description": "Optional comments"},
                "conditions": {"type": "string", "required": False, "description": "JSON conditions to check before execution"}
            },
            "response": {
                "success": {"type": "boolean", "description": "Operation success status"},
                "data": {
                    "scheduled_transition_id": {"type": "string", "description": "Scheduled transition ID"},
                    "job_order": {"type": "string", "description": "Job order name"},
                    "scheduled_date": {"type": "datetime", "description": "Scheduled execution time"}
                }
            },
            "required_permissions": ["Job Order: write"],
            "rate_limit": "50 requests/hour"
        },
        
        {
            "name": "get_realtime_workflow_status",
            "method": "GET",
            "url": "/api/method/api_next.api.job_workflow_advanced.get_realtime_workflow_status",
            "category": "Real-time Monitoring",
            "description": "Get real-time workflow status across all active jobs",
            "parameters": {},
            "response": {
                "success": {"type": "boolean", "description": "Operation success status"},
                "data": {
                    "timestamp": {"type": "datetime", "description": "Data timestamp"},
                    "phase_distribution": {"type": "array", "description": "Jobs by phase"},
                    "recent_transitions": {"type": "array", "description": "Recent transitions"},
                    "stuck_jobs": {"type": "array", "description": "Jobs stuck in phases"},
                    "alerts": {"type": "array", "description": "System alerts"}
                }
            },
            "required_permissions": ["Job Order: read"],
            "rate_limit": "200 requests/hour"
        }
    ]
    
    return endpoints


def _get_api_examples() -> Dict:
    """Generate comprehensive API usage examples."""
    
    examples = {
        "transition": {
            "basic_transition": {
                "description": "Perform a basic phase transition",
                "request": {
                    "method": "POST",
                    "url": "/api/method/api_next.api.job_workflow.transition_phase",
                    "headers": {
                        "Content-Type": "application/json",
                        "Authorization": "Bearer YOUR_API_TOKEN"
                    },
                    "body": {
                        "job_order": "JOB-25-00001",
                        "action": "Request Estimation",
                        "comments": "Initial review completed, ready for estimation"
                    }
                },
                "response": {
                    "success": True,
                    "data": {
                        "job_order": "JOB-25-00001",
                        "old_state": "Submission",
                        "new_state": "Estimation",
                        "action": "Request Estimation",
                        "timestamp": "2025-09-09 10:30:00",
                        "user": "user@company.com"
                    },
                    "message": "Job Order JOB-25-00001 successfully transitioned from Submission to Estimation"
                }
            },
            
            "bulk_transition": {
                "description": "Perform bulk transitions on multiple jobs",
                "request": {
                    "method": "POST",
                    "url": "/api/method/api_next.api.job_workflow.bulk_transition",
                    "body": {
                        "job_orders": "[\"JOB-25-00001\", \"JOB-25-00002\", \"JOB-25-00003\"]",
                        "action": "Approve and Plan",
                        "comments": "Batch approval after client meeting"
                    }
                },
                "response": {
                    "success": True,
                    "data": {
                        "total_processed": 3,
                        "successful": 2,
                        "failed": 1,
                        "results": [
                            {"job_order": "JOB-25-00001", "success": True, "message": "Transition successful"},
                            {"job_order": "JOB-25-00002", "success": True, "message": "Transition successful"},
                            {"job_order": "JOB-25-00003", "success": False, "message": "Prerequisites not met"}
                        ]
                    }
                }
            }
        },
        
        "reporting": {
            "get_phase_distribution": {
                "description": "Get jobs grouped by workflow phase",
                "request": {
                    "method": "GET",
                    "url": "/api/method/api_next.api.job_workflow.get_jobs_by_phase?limit=10"
                },
                "response": {
                    "success": True,
                    "data": {
                        "grouped_by_phase": {
                            "Submission": [
                                {"name": "JOB-25-00001", "customer_name": "ABC Corp", "project_name": "Equipment Install"},
                                {"name": "JOB-25-00002", "customer_name": "XYZ Ltd", "project_name": "Maintenance Service"}
                            ],
                            "Estimation": [
                                {"name": "JOB-25-00003", "customer_name": "Tech Co", "project_name": "System Upgrade"}
                            ]
                        },
                        "total_jobs": 3
                    }
                }
            },
            
            "get_workflow_metrics": {
                "description": "Get comprehensive workflow performance metrics",
                "request": {
                    "method": "GET",
                    "url": "/api/method/api_next.api.job_workflow.get_phase_metrics?date_range=7"
                },
                "response": {
                    "success": True,
                    "data": {
                        "period": "Last 7 days",
                        "phase_metrics": {
                            "Submission": {"jobs_in_phase": 5, "average_duration": 24.0, "efficiency_score": 0.92},
                            "Estimation": {"jobs_in_phase": 3, "average_duration": 48.0, "efficiency_score": 0.78},
                            "Execution": {"jobs_in_phase": 8, "average_duration": 120.0, "efficiency_score": 0.85}
                        },
                        "overall_metrics": {
                            "average_completion_time": 480.0,
                            "on_time_completion_rate": 0.85,
                            "resource_utilization": 0.78
                        }
                    }
                }
            }
        },
        
        "validation": {
            "check_available_transitions": {
                "description": "Check what transitions are available for a job",
                "request": {
                    "method": "GET",
                    "url": "/api/method/api_next.api.job_workflow.get_available_transitions?job_order=JOB-25-00001"
                },
                "response": {
                    "success": True,
                    "data": {
                        "job_order": "JOB-25-00001",
                        "current_state": "Submission",
                        "available_transitions": [
                            {
                                "action": "Request Estimation",
                                "next_state": "Estimation",
                                "has_permission": True,
                                "is_valid": True
                            },
                            {
                                "action": "Cancel Job",
                                "next_state": "Cancelled",
                                "has_permission": True,
                                "is_valid": True
                            }
                        ]
                    }
                }
            },
            
            "validate_transition": {
                "description": "Validate if a specific transition is allowed",
                "request": {
                    "method": "GET",
                    "url": "/api/method/api_next.api.job_workflow.validate_transition?job_order=JOB-25-00001&action=Request Estimation"
                },
                "response": {
                    "success": True,
                    "data": {
                        "job_order": "JOB-25-00001",
                        "action": "Request Estimation",
                        "current_state": "Submission",
                        "next_state": "Estimation",
                        "is_valid": True,
                        "validation_details": {
                            "transition_valid": {"valid": True, "message": "Transition is valid"},
                            "prerequisites": {"valid": True, "total_requirements": 2, "unmet_requirements": []},
                            "permissions": {"valid": True, "message": "Permission granted"},
                            "business_rules": {"valid": True, "message": "All business rules passed"}
                        }
                    }
                }
            }
        },
        
        "webhooks": {
            "webhook_setup": {
                "description": "Set up webhook notifications for phase transitions",
                "request": {
                    "method": "POST",
                    "url": "/api/method/api_next.api.job_workflow.setup_phase_webhook",
                    "body": {
                        "webhook_url": "https://your-system.com/webhook/job-transitions",
                        "events": "[\"phase_transition\", \"job_completed\"]",
                        "secret_key": "your-secret-key"
                    }
                },
                "response": {
                    "success": True,
                    "data": {
                        "webhook_url": "https://your-system.com/webhook/job-transitions",
                        "events": ["phase_transition", "job_completed"],
                        "created_by": "user@company.com",
                        "created_at": "2025-09-09 10:30:00"
                    },
                    "message": "Webhook configured successfully"
                }
            },
            
            "webhook_payload_example": {
                "description": "Example webhook payload for phase transition",
                "webhook_payload": {
                    "event": "phase_transition",
                    "timestamp": "2025-09-09T10:30:00Z",
                    "data": {
                        "job_order": "JOB-25-00001",
                        "customer": "ABC Corp",
                        "project": "Equipment Installation",
                        "old_state": "Submission",
                        "new_state": "Estimation",
                        "action": "Request Estimation",
                        "user": "pm@company.com",
                        "comments": "Initial review completed"
                    }
                },
                "headers": {
                    "X-Webhook-Signature": "sha256=calculated_hmac_signature",
                    "Content-Type": "application/json",
                    "User-Agent": "API-Next-Webhook/1.0"
                }
            }
        },
        
        "error_handling": {
            "permission_error": {
                "description": "Example of permission error response",
                "response": {
                    "success": False,
                    "error": "PermissionError",
                    "message": "Insufficient permissions to transition job phases",
                    "required_roles": ["Project Manager", "System Manager"],
                    "user_roles": ["Employee"]
                }
            },
            
            "validation_error": {
                "description": "Example of validation error response",
                "response": {
                    "success": False,
                    "error": "ValidationError",
                    "message": "Phase prerequisites not met",
                    "details": {
                        "valid": False,
                        "total_requirements": 3,
                        "unmet_requirements": [
                            {"type": "field", "field": "description", "required": True},
                            {"type": "child_table", "table": "team_members", "min_count": 1}
                        ]
                    }
                }
            },
            
            "rate_limit_error": {
                "description": "Example of rate limit exceeded response",
                "response": {
                    "success": False,
                    "error": "RateLimitExceeded",
                    "message": "Rate limit exceeded: 101/100 requests in 3600 seconds",
                    "rate_limit_info": {
                        "limit": 100,
                        "current_requests": 101,
                        "window_seconds": 3600,
                        "reset_time": 1694259600
                    }
                }
            }
        }
    }
    
    return examples


def _get_error_codes() -> Dict:
    """Generate error code documentation."""
    
    return {
        "PermissionError": {
            "description": "User lacks required permissions for the operation",
            "typical_causes": [
                "Insufficient role permissions",
                "No access to specific DocType",
                "Missing workflow transition permissions"
            ],
            "resolution": "Check user roles and DocType permissions"
        },
        
        "ValidationError": {
            "description": "Input validation failed or business rules not met",
            "typical_causes": [
                "Missing required parameters",
                "Invalid parameter values",
                "Business rule violations",
                "Prerequisites not met"
            ],
            "resolution": "Verify input parameters and ensure all prerequisites are satisfied"
        },
        
        "NotFoundError": {
            "description": "Requested resource was not found",
            "typical_causes": [
                "Invalid Job Order ID",
                "Deleted or non-existent record",
                "Incorrect document name"
            ],
            "resolution": "Verify the resource identifier and ensure the record exists"
        },
        
        "WorkflowError": {
            "description": "Workflow-specific operation failed",
            "typical_causes": [
                "Invalid workflow transition",
                "Workflow not configured properly",
                "State machine violation"
            ],
            "resolution": "Check workflow configuration and valid transitions"
        },
        
        "RateLimitExceeded": {
            "description": "API rate limit exceeded",
            "typical_causes": [
                "Too many requests in time window",
                "Bulk operations exceeding limits"
            ],
            "resolution": "Reduce request frequency or contact administrator for limit increase"
        },
        
        "SystemError": {
            "description": "Internal system error occurred",
            "typical_causes": [
                "Database connection issues",
                "Server configuration problems",
                "Unexpected application errors"
            ],
            "resolution": "Contact system administrator or check server logs"
        }
    }


# ============================================================================
# CURL EXAMPLES GENERATOR
# ============================================================================

@frappe.whitelist(allow_guest=True)
def get_curl_examples(endpoint: str = None):
    """
    Get cURL command examples for API endpoints.
    
    Args:
        endpoint (str): Specific endpoint name (optional)
    
    Returns:
        dict: cURL examples for API testing
    """
    try:
        base_url = frappe.utils.get_url()
        
        curl_examples = {
            "transition_phase": f"""
# Transition a job to the next phase
curl -X POST "{base_url}/api/method/api_next.api.job_workflow.transition_phase" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_API_TOKEN" \\
  -d '{{
    "job_order": "JOB-25-00001",
    "action": "Request Estimation",
    "comments": "Ready for cost estimation"
  }}'
            """,
            
            "get_workflow_status": f"""
# Get workflow status for a job
curl -X GET "{base_url}/api/method/api_next.api.job_workflow.get_workflow_status?job_order=JOB-25-00001" \\
  -H "Authorization: Bearer YOUR_API_TOKEN"
            """,
            
            "bulk_transition": f"""
# Perform bulk phase transitions
curl -X POST "{base_url}/api/method/api_next.api.job_workflow.bulk_transition" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_API_TOKEN" \\
  -d '{{
    "job_orders": "[\\"JOB-25-00001\\", \\"JOB-25-00002\\"]",
    "action": "Approve and Plan",
    "comments": "Batch approval"
  }}'
            """,
            
            "get_phase_metrics": f"""
# Get phase performance metrics
curl -X GET "{base_url}/api/method/api_next.api.job_workflow.get_phase_metrics?date_range=30" \\
  -H "Authorization: Bearer YOUR_API_TOKEN"
            """,
            
            "schedule_transition": f"""
# Schedule a future phase transition
curl -X POST "{base_url}/api/method/api_next.api.job_workflow_advanced.schedule_phase_transition" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_API_TOKEN" \\
  -d '{{
    "job_order": "JOB-25-00001",
    "action": "Begin Execution",
    "scheduled_date": "2025-09-15 09:00:00",
    "comments": "Auto-start execution on Monday"
  }}'
            """,
            
            "webhook_setup": f"""
# Set up webhook notifications
curl -X POST "{base_url}/api/method/api_next.api.job_workflow.setup_phase_webhook" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_API_TOKEN" \\
  -d '{{
    "webhook_url": "https://your-system.com/webhook",
    "events": "[\\"phase_transition\\", \\"job_completed\\"]",
    "secret_key": "your-webhook-secret"
  }}'
            """
        }
        
        if endpoint:
            if endpoint not in curl_examples:
                return {
                    "success": False,
                    "error": "NotFound",
                    "message": f"No cURL example found for endpoint '{endpoint}'"
                }
            
            return {
                "success": True,
                "data": {
                    "endpoint": endpoint,
                    "curl_example": curl_examples[endpoint].strip()
                }
            }
        
        return {
            "success": True,
            "data": {
                "base_url": base_url,
                "curl_examples": curl_examples,
                "authentication_note": "Replace YOUR_API_TOKEN with your actual API token"
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }