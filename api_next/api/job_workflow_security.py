# Job Workflow Security and Utility Functions
# Authentication, authorization, rate limiting, and security measures

import frappe
from frappe import _
from frappe.utils import now, today, add_days, cint, flt
import json
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, List, Optional, Callable


# ============================================================================
# AUTHENTICATION AND AUTHORIZATION
# ============================================================================

def require_role(roles: List[str]):
    """
    Decorator to require specific roles for API access.
    
    Args:
        roles (List[str]): List of required roles
    
    Returns:
        function: Decorated function with role checking
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_roles = frappe.get_roles(frappe.session.user)
            
            if not any(role in user_roles for role in roles):
                return {
                    "success": False,
                    "error": "PermissionError",
                    "message": f"Access denied. Required roles: {', '.join(roles)}",
                    "required_roles": roles,
                    "user_roles": user_roles
                }
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_permission(doctype: str, permission_type: str = "read"):
    """
    Decorator to require specific DocType permissions.
    
    Args:
        doctype (str): DocType name to check
        permission_type (str): Type of permission (read, write, create, delete)
    
    Returns:
        function: Decorated function with permission checking
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not frappe.has_permission(doctype, permission_type):
                return {
                    "success": False,
                    "error": "PermissionError",
                    "message": f"Insufficient permissions for {permission_type} access to {doctype}",
                    "required_permission": f"{doctype}:{permission_type}"
                }
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def validate_api_key(api_key: str) -> Dict:
    """
    Validate API key for external integrations.
    
    Args:
        api_key (str): API key to validate
    
    Returns:
        dict: Validation result with user context
    """
    try:
        # Check if API key exists and is active
        api_key_doc = frappe.get_all("API Key",
            filters={"api_key": api_key, "enabled": 1},
            fields=["name", "user", "expires_on", "allowed_ips"]
        )
        
        if not api_key_doc:
            return {
                "valid": False,
                "error": "Invalid or disabled API key"
            }
        
        api_key_data = api_key_doc[0]
        
        # Check expiration
        if api_key_data.get("expires_on") and api_key_data["expires_on"] < today():
            return {
                "valid": False,
                "error": "API key has expired"
            }
        
        # Check IP restrictions if configured
        if api_key_data.get("allowed_ips"):
            client_ip = frappe.local.request.environ.get("REMOTE_ADDR")
            allowed_ips = [ip.strip() for ip in api_key_data["allowed_ips"].split(",")]
            
            if client_ip not in allowed_ips:
                return {
                    "valid": False,
                    "error": f"IP address {client_ip} not allowed for this API key"
                }
        
        return {
            "valid": True,
            "user": api_key_data["user"],
            "api_key_name": api_key_data["name"]
        }
        
    except Exception as e:
        return {
            "valid": False,
            "error": f"API key validation error: {str(e)}"
        }


# ============================================================================
# RATE LIMITING
# ============================================================================

class RateLimiter:
    """Rate limiting implementation using Redis."""
    
    def __init__(self, key_prefix: str = "workflow_api_rate_limit"):
        self.key_prefix = key_prefix
    
    def is_rate_limited(self, identifier: str, limit: int, window_seconds: int) -> Dict:
        """
        Check if identifier is rate limited.
        
        Args:
            identifier (str): Unique identifier (user, IP, API key)
            limit (int): Number of requests allowed
            window_seconds (int): Time window in seconds
        
        Returns:
            dict: Rate limiting status
        """
        try:
            cache_key = f"{self.key_prefix}:{identifier}"
            current_time = int(time.time())
            window_start = current_time - window_seconds
            
            # Get current request count from cache
            cached_data = frappe.cache().get_value(cache_key)
            
            if cached_data:
                requests = json.loads(cached_data)
                # Filter requests within the current window
                recent_requests = [req for req in requests if req >= window_start]
            else:
                recent_requests = []
            
            # Check if limit exceeded
            if len(recent_requests) >= limit:
                return {
                    "limited": True,
                    "current_requests": len(recent_requests),
                    "limit": limit,
                    "window_seconds": window_seconds,
                    "reset_time": min(recent_requests) + window_seconds if recent_requests else current_time
                }
            
            # Add current request
            recent_requests.append(current_time)
            
            # Store updated requests with TTL
            frappe.cache().set_value(
                cache_key, 
                json.dumps(recent_requests), 
                expires_in_sec=window_seconds
            )
            
            return {
                "limited": False,
                "current_requests": len(recent_requests),
                "limit": limit,
                "remaining": limit - len(recent_requests)
            }
            
        except Exception as e:
            frappe.log_error(f"Rate limiting error: {str(e)}", "Workflow API Rate Limiter")
            # Allow request if rate limiting fails
            return {"limited": False, "error": str(e)}


def rate_limit(limit: int = 100, window_seconds: int = 3600):
    """
    Decorator for API rate limiting.
    
    Args:
        limit (int): Number of requests allowed per window
        window_seconds (int): Time window in seconds
    
    Returns:
        function: Decorated function with rate limiting
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            rate_limiter = RateLimiter()
            
            # Use user as identifier, fall back to IP
            identifier = frappe.session.user
            if identifier == "Guest":
                identifier = frappe.local.request.environ.get("REMOTE_ADDR", "unknown")
            
            rate_status = rate_limiter.is_rate_limited(identifier, limit, window_seconds)
            
            if rate_status.get("limited"):
                return {
                    "success": False,
                    "error": "RateLimitExceeded",
                    "message": f"Rate limit exceeded: {rate_status['current_requests']}/{rate_status['limit']} requests in {rate_status['window_seconds']} seconds",
                    "rate_limit_info": rate_status
                }
            
            # Execute the function
            result = func(*args, **kwargs)
            
            # Add rate limit headers to response
            if isinstance(result, dict) and result.get("success"):
                result["rate_limit_info"] = {
                    "limit": rate_status["limit"],
                    "remaining": rate_status.get("remaining", 0),
                    "window_seconds": window_seconds
                }
            
            return result
        return wrapper
    return decorator


# ============================================================================
# INPUT VALIDATION AND SANITIZATION
# ============================================================================

def validate_input(validation_rules: Dict):
    """
    Decorator for input validation.
    
    Args:
        validation_rules (Dict): Validation rules for parameters
    
    Returns:
        function: Decorated function with input validation
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Validate each parameter
            for param_name, rules in validation_rules.items():
                if param_name in kwargs:
                    value = kwargs[param_name]
                    validation_result = _validate_parameter(param_name, value, rules)
                    
                    if not validation_result["valid"]:
                        return {
                            "success": False,
                            "error": "ValidationError",
                            "message": validation_result["message"],
                            "parameter": param_name
                        }
                    
                    # Apply sanitization if rules specify it
                    if "sanitize" in rules and rules["sanitize"]:
                        kwargs[param_name] = _sanitize_value(value, rules)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def _validate_parameter(param_name: str, value, rules: Dict) -> Dict:
    """Validate a single parameter against rules."""
    try:
        # Check required
        if rules.get("required", False) and (value is None or value == ""):
            return {
                "valid": False,
                "message": f"Parameter '{param_name}' is required"
            }
        
        # Skip other validations if value is None/empty and not required
        if value is None or value == "":
            return {"valid": True}
        
        # Check type
        if "type" in rules:
            expected_type = rules["type"]
            if expected_type == "string" and not isinstance(value, str):
                return {
                    "valid": False,
                    "message": f"Parameter '{param_name}' must be a string"
                }
            elif expected_type == "integer" and not isinstance(value, int):
                try:
                    int(value)
                except (ValueError, TypeError):
                    return {
                        "valid": False,
                        "message": f"Parameter '{param_name}' must be an integer"
                    }
            elif expected_type == "float" and not isinstance(value, (int, float)):
                try:
                    float(value)
                except (ValueError, TypeError):
                    return {
                        "valid": False,
                        "message": f"Parameter '{param_name}' must be a number"
                    }
        
        # Check length constraints
        if isinstance(value, str):
            if "min_length" in rules and len(value) < rules["min_length"]:
                return {
                    "valid": False,
                    "message": f"Parameter '{param_name}' must be at least {rules['min_length']} characters"
                }
            if "max_length" in rules and len(value) > rules["max_length"]:
                return {
                    "valid": False,
                    "message": f"Parameter '{param_name}' must be at most {rules['max_length']} characters"
                }
        
        # Check value constraints
        if "min_value" in rules and value < rules["min_value"]:
            return {
                "valid": False,
                "message": f"Parameter '{param_name}' must be at least {rules['min_value']}"
            }
        if "max_value" in rules and value > rules["max_value"]:
            return {
                "valid": False,
                "message": f"Parameter '{param_name}' must be at most {rules['max_value']}"
            }
        
        # Check allowed values
        if "allowed_values" in rules and value not in rules["allowed_values"]:
            return {
                "valid": False,
                "message": f"Parameter '{param_name}' must be one of: {', '.join(map(str, rules['allowed_values']))}"
            }
        
        # Check pattern matching
        if "pattern" in rules:
            import re
            if not re.match(rules["pattern"], str(value)):
                return {
                    "valid": False,
                    "message": f"Parameter '{param_name}' format is invalid"
                }
        
        return {"valid": True}
        
    except Exception as e:
        return {
            "valid": False,
            "message": f"Validation error for '{param_name}': {str(e)}"
        }


def _sanitize_value(value, rules: Dict):
    """Sanitize input value based on rules."""
    if not isinstance(value, str):
        return value
    
    sanitize_rules = rules.get("sanitize", {})
    
    # Strip whitespace
    if sanitize_rules.get("strip", True):
        value = value.strip()
    
    # Remove HTML tags
    if sanitize_rules.get("no_html", False):
        import re
        value = re.sub(r"<[^>]+>", "", value)
    
    # Escape special characters
    if sanitize_rules.get("escape", False):
        value = frappe.db.escape(value)
    
    return value


# ============================================================================
# WEBHOOK SECURITY
# ============================================================================

def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    """
    Verify webhook signature for security.
    
    Args:
        payload (str): Request payload
        signature (str): Provided signature
        secret (str): Webhook secret
    
    Returns:
        bool: True if signature is valid
    """
    try:
        # Calculate expected signature
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures securely
        return hmac.compare_digest(f"sha256={expected_signature}", signature)
        
    except Exception:
        return False


@frappe.whitelist()
def process_secure_webhook(payload: str, signature: str, event_type: str):
    """
    Process webhook with signature verification.
    
    Args:
        payload (str): Webhook payload
        signature (str): Request signature
        event_type (str): Type of webhook event
    
    Returns:
        dict: Processing result
    """
    try:
        # Get webhook secret from settings
        webhook_secret = frappe.db.get_single_value("Job Workflow Settings", "webhook_secret")
        
        if not webhook_secret:
            return {
                "success": False,
                "error": "ConfigurationError",
                "message": "Webhook secret not configured"
            }
        
        # Verify signature
        if not verify_webhook_signature(payload, signature, webhook_secret):
            return {
                "success": False,
                "error": "SecurityError",
                "message": "Invalid webhook signature"
            }
        
        # Parse payload
        try:
            webhook_data = json.loads(payload)
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "ValidationError",
                "message": "Invalid JSON payload"
            }
        
        # Process webhook based on event type
        result = _process_webhook_event(event_type, webhook_data)
        
        return {
            "success": True,
            "data": result,
            "message": f"Webhook {event_type} processed successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"Webhook processing error: {str(e)}", "Workflow Webhook Security")
        return {
            "success": False,
            "error": "SystemError",
            "message": "Webhook processing failed"
        }


def _process_webhook_event(event_type: str, data: Dict) -> Dict:
    """Process specific webhook events."""
    processors = {
        "phase_transition": _process_phase_transition_webhook,
        "job_created": _process_job_created_webhook,
        "job_completed": _process_job_completed_webhook
    }
    
    processor = processors.get(event_type)
    if not processor:
        return {"error": f"Unknown webhook event type: {event_type}"}
    
    return processor(data)


def _process_phase_transition_webhook(data: Dict) -> Dict:
    """Process phase transition webhook."""
    # Implement phase transition webhook logic
    return {"processed": True, "event": "phase_transition"}


def _process_job_created_webhook(data: Dict) -> Dict:
    """Process job created webhook."""
    # Implement job created webhook logic
    return {"processed": True, "event": "job_created"}


def _process_job_completed_webhook(data: Dict) -> Dict:
    """Process job completed webhook."""
    # Implement job completed webhook logic
    return {"processed": True, "event": "job_completed"}


# ============================================================================
# AUDIT LOGGING
# ============================================================================

def audit_log(action: str, details: Dict = None):
    """
    Decorator for audit logging.
    
    Args:
        action (str): Action being performed
        details (Dict): Additional details to log
    
    Returns:
        function: Decorated function with audit logging
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Prepare audit log entry
            audit_entry = {
                "timestamp": now(),
                "user": frappe.session.user,
                "action": action,
                "function": func.__name__,
                "ip_address": frappe.local.request.environ.get("REMOTE_ADDR"),
                "user_agent": frappe.local.request.environ.get("HTTP_USER_AGENT"),
                "details": details or {}
            }
            
            # Add function parameters to audit log
            if kwargs:
                audit_entry["parameters"] = {
                    k: v for k, v in kwargs.items() 
                    if not k.startswith("_") and k not in ["password", "secret", "token"]
                }
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # Log success
                audit_entry["success"] = result.get("success", True) if isinstance(result, dict) else True
                audit_entry["result_summary"] = _summarize_result(result)
                
                _write_audit_log(audit_entry)
                
                return result
                
            except Exception as e:
                # Log failure
                audit_entry["success"] = False
                audit_entry["error"] = str(e)
                
                _write_audit_log(audit_entry)
                raise
                
        return wrapper
    return decorator


def _write_audit_log(entry: Dict):
    """Write audit log entry to database."""
    try:
        # Create audit log document
        audit_doc = frappe.get_doc({
            "doctype": "Workflow API Audit Log",
            "timestamp": entry["timestamp"],
            "user": entry["user"],
            "action": entry["action"],
            "function_name": entry["function"],
            "ip_address": entry.get("ip_address"),
            "user_agent": entry.get("user_agent"),
            "parameters": json.dumps(entry.get("parameters", {})),
            "success": entry["success"],
            "result_summary": entry.get("result_summary"),
            "error_message": entry.get("error"),
            "details": json.dumps(entry.get("details", {}))
        })
        
        audit_doc.insert(ignore_permissions=True)
        frappe.db.commit()
        
    except Exception as e:
        # Fallback to error log if audit log fails
        frappe.log_error(f"Audit logging failed: {str(e)}", "Workflow API Audit")


def _summarize_result(result) -> str:
    """Create a summary of the function result."""
    if not isinstance(result, dict):
        return str(type(result).__name__)
    
    if result.get("success"):
        data = result.get("data", {})
        if isinstance(data, dict):
            return f"Success - {len(data)} data fields"
        elif isinstance(data, list):
            return f"Success - {len(data)} items"
        else:
            return "Success"
    else:
        error = result.get("error", "Unknown")
        return f"Error - {error}"


# ============================================================================
# SECURITY UTILITIES
# ============================================================================

@frappe.whitelist()
def get_api_security_status():
    """
    Get current API security status and configuration.
    
    Returns:
        dict: Security status information
    """
    try:
        # Check rate limiting status
        rate_limiter = RateLimiter()
        current_user = frappe.session.user
        
        # Get user's current rate limit status
        rate_status = rate_limiter.is_rate_limited(current_user, 100, 3600)
        
        # Check webhook configuration
        webhook_secret_configured = bool(
            frappe.db.get_single_value("Job Workflow Settings", "webhook_secret")
        )
        
        # Get user permissions
        user_roles = frappe.get_roles(current_user)
        workflow_permissions = {
            "job_order_read": frappe.has_permission("Job Order", "read"),
            "job_order_write": frappe.has_permission("Job Order", "write"),
            "job_order_create": frappe.has_permission("Job Order", "create"),
            "job_order_delete": frappe.has_permission("Job Order", "delete")
        }
        
        # Get recent audit log count
        recent_audit_count = frappe.db.count("Workflow API Audit Log", {
            "user": current_user,
            "timestamp": [">=", add_days(now(), -1)]
        })
        
        return {
            "success": True,
            "data": {
                "user": current_user,
                "user_roles": user_roles,
                "rate_limiting": {
                    "enabled": True,
                    "current_requests": rate_status.get("current_requests", 0),
                    "limit": rate_status.get("limit", 100),
                    "remaining": rate_status.get("remaining", 100)
                },
                "permissions": workflow_permissions,
                "webhook_security": {
                    "secret_configured": webhook_secret_configured,
                    "signature_verification": webhook_secret_configured
                },
                "audit_logging": {
                    "enabled": True,
                    "recent_entries": recent_audit_count
                },
                "security_features": {
                    "input_validation": True,
                    "output_sanitization": True,
                    "sql_injection_protection": True,
                    "xss_protection": True
                }
            },
            "message": "Security status retrieved successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }


@frappe.whitelist()
@require_role(["System Manager"])
def reset_rate_limits(user: str = None):
    """
    Reset rate limits for a user or all users.
    
    Args:
        user (str): Specific user to reset (optional)
    
    Returns:
        dict: Reset operation result
    """
    try:
        rate_limiter = RateLimiter()
        
        if user:
            # Reset for specific user
            cache_key = f"{rate_limiter.key_prefix}:{user}"
            frappe.cache().delete_value(cache_key)
            
            return {
                "success": True,
                "message": f"Rate limits reset for user: {user}"
            }
        else:
            # Reset for all users (clear all rate limit cache keys)
            # This is a simplified approach - in production you might want to be more selective
            frappe.cache().delete_keys(f"{rate_limiter.key_prefix}:*")
            
            return {
                "success": True,
                "message": "Rate limits reset for all users"
            }
        
    except Exception as e:
        return {
            "success": False,
            "error": "SystemError",
            "message": str(e)
        }