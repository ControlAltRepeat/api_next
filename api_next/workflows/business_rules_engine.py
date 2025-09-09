# Copyright (c) 2025, API Next and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from typing import Dict, List, Any, Optional
import json
from datetime import datetime, timedelta

class BusinessRulesEngine:
    """
    Flexible business rules engine for workflow decision making.
    
    Supports:
    - Conditional logic evaluation
    - Dynamic rule configuration
    - Context-aware rule execution
    - Rule chaining and dependencies
    """
    
    def __init__(self):
        self.rule_cache = {}
        self.context = {}
    
    def evaluate(self, context: Dict[str, Any], rule_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Evaluate business rules based on provided context.
        
        Args:
            context: Dictionary containing document data and environment variables
            rule_type: Optional filter for specific rule types
            
        Returns:
            Dictionary with evaluation results and triggered actions
        """
        self.context = context
        results = {
            "rules_evaluated": [],
            "rules_passed": [],
            "rules_failed": [],
            "actions_triggered": [],
            "overall_result": True
        }
        
        # Get applicable rules
        rules = self._get_applicable_rules(context, rule_type)
        
        for rule in rules:
            try:
                rule_result = self.execute_rule(rule, context)
                results["rules_evaluated"].append(rule["name"])
                
                if rule_result["passed"]:
                    results["rules_passed"].append(rule["name"])
                    if rule_result.get("actions"):
                        results["actions_triggered"].extend(rule_result["actions"])
                else:
                    results["rules_failed"].append(rule["name"])
                    results["overall_result"] = False
                    
            except Exception as e:
                frappe.log_error(f"Rule evaluation error ({rule.get('name', 'unknown')}): {str(e)}")
                results["rules_failed"].append(rule.get("name", "unknown"))
                results["overall_result"] = False
        
        return results
    
    def execute_rule(self, rule: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single business rule.
        
        Args:
            rule: Rule definition dictionary
            context: Execution context
            
        Returns:
            Dictionary with execution results
        """
        rule_name = rule.get("name", "unnamed_rule")
        
        try:
            # Evaluate conditions
            conditions_result = self.evaluate_conditions(rule.get("conditions", []), context)
            
            result = {
                "rule_name": rule_name,
                "passed": conditions_result["all_passed"],
                "conditions_evaluated": conditions_result["total"],
                "conditions_passed": conditions_result["passed"],
                "actions": []
            }
            
            # Execute actions if conditions pass
            if conditions_result["all_passed"] and rule.get("actions"):
                for action in rule["actions"]:
                    action_result = self._execute_action(action, context)
                    if action_result:
                        result["actions"].append(action_result)
            
            return result
            
        except Exception as e:
            frappe.log_error(f"Rule execution error ({rule_name}): {str(e)}")
            return {
                "rule_name": rule_name,
                "passed": False,
                "error": str(e),
                "actions": []
            }
    
    def evaluate_conditions(self, conditions: List[Dict[str, Any]], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a list of conditions with support for AND/OR logic.
        
        Args:
            conditions: List of condition dictionaries
            context: Evaluation context
            
        Returns:
            Dictionary with evaluation results
        """
        if not conditions:
            return {"all_passed": True, "total": 0, "passed": 0}
        
        results = []
        
        for condition in conditions:
            try:
                condition_result = self._evaluate_single_condition(condition, context)
                results.append(condition_result)
            except Exception as e:
                frappe.log_error(f"Condition evaluation error: {str(e)}")
                results.append(False)
        
        # Apply logic operator (default is AND)
        logic_operator = conditions[0].get("logic", "AND") if conditions else "AND"
        
        if logic_operator.upper() == "OR":
            all_passed = any(results)
        else:  # AND logic
            all_passed = all(results)
        
        return {
            "all_passed": all_passed,
            "total": len(results),
            "passed": sum(results),
            "individual_results": results
        }
    
    def _get_applicable_rules(self, context: Dict[str, Any], rule_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get applicable business rules based on context and type."""
        # In a real implementation, this would fetch from database or configuration
        # For now, return predefined rules
        
        rules = [
            {
                "name": "job_order_approval_threshold",
                "type": "approval",
                "description": "Jobs over $10,000 require manager approval",
                "conditions": [
                    {
                        "field": "total_cost",
                        "operator": ">",
                        "value": 10000,
                        "logic": "AND"
                    }
                ],
                "actions": [
                    {
                        "type": "require_approval",
                        "role": "Project Manager"
                    }
                ]
            },
            {
                "name": "urgent_job_priority",
                "type": "priority",
                "description": "Urgent jobs get priority resource allocation",
                "conditions": [
                    {
                        "field": "priority",
                        "operator": "==",
                        "value": "Urgent",
                        "logic": "AND"
                    }
                ],
                "actions": [
                    {
                        "type": "priority_allocation",
                        "level": "high"
                    }
                ]
            },
            {
                "name": "material_lead_time_check",
                "type": "material",
                "description": "Check material lead times before planning",
                "conditions": [
                    {
                        "field": "has_materials",
                        "operator": "==",
                        "value": True,
                        "logic": "AND"
                    }
                ],
                "actions": [
                    {
                        "type": "check_lead_times"
                    }
                ]
            },
            {
                "name": "weekend_work_approval",
                "type": "scheduling",
                "description": "Weekend work requires special approval",
                "conditions": [
                    {
                        "field": "scheduled_weekend",
                        "operator": "==",
                        "value": True,
                        "logic": "AND"
                    }
                ],
                "actions": [
                    {
                        "type": "require_approval",
                        "role": "Operations Manager"
                    }
                ]
            },
            {
                "name": "quality_check_requirement",
                "type": "quality",
                "description": "High-risk jobs require quality inspector sign-off",
                "conditions": [
                    {
                        "field": "risk_level",
                        "operator": "in",
                        "value": ["High", "Critical"],
                        "logic": "AND"
                    }
                ],
                "actions": [
                    {
                        "type": "require_quality_inspection"
                    }
                ]
            }
        ]
        
        # Filter by rule type if specified
        if rule_type:
            rules = [rule for rule in rules if rule.get("type") == rule_type]
        
        return rules
    
    def _evaluate_single_condition(self, condition: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Evaluate a single condition against context."""
        field = condition.get("field")
        operator = condition.get("operator")
        expected_value = condition.get("value")
        
        if not field or not operator:
            return False
        
        # Get actual value from context
        actual_value = self._get_field_value(field, context)
        
        # Evaluate based on operator
        if operator == "==":
            return actual_value == expected_value
        elif operator == "!=":
            return actual_value != expected_value
        elif operator == ">":
            return float(actual_value or 0) > float(expected_value)
        elif operator == ">=":
            return float(actual_value or 0) >= float(expected_value)
        elif operator == "<":
            return float(actual_value or 0) < float(expected_value)
        elif operator == "<=":
            return float(actual_value or 0) <= float(expected_value)
        elif operator == "in":
            return actual_value in expected_value if isinstance(expected_value, list) else False
        elif operator == "not_in":
            return actual_value not in expected_value if isinstance(expected_value, list) else True
        elif operator == "contains":
            return str(expected_value) in str(actual_value or "")
        elif operator == "not_contains":
            return str(expected_value) not in str(actual_value or "")
        elif operator == "starts_with":
            return str(actual_value or "").startswith(str(expected_value))
        elif operator == "ends_with":
            return str(actual_value or "").endswith(str(expected_value))
        elif operator == "regex":
            import re
            return bool(re.search(str(expected_value), str(actual_value or "")))
        elif operator == "is_null":
            return actual_value is None or actual_value == ""
        elif operator == "is_not_null":
            return actual_value is not None and actual_value != ""
        elif operator == "date_before":
            return self._compare_dates(actual_value, expected_value, "<")
        elif operator == "date_after":
            return self._compare_dates(actual_value, expected_value, ">")
        elif operator == "date_equals":
            return self._compare_dates(actual_value, expected_value, "==")
        else:
            frappe.log_error(f"Unknown operator: {operator}")
            return False
    
    def _get_field_value(self, field: str, context: Dict[str, Any]) -> Any:
        """Get field value from context with support for nested fields."""
        if "." in field:
            # Handle nested field access (e.g., "doc.customer_name")
            parts = field.split(".")
            value = context
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                elif hasattr(value, part):
                    value = getattr(value, part)
                else:
                    return None
            return value
        else:
            # Direct field access
            if isinstance(context, dict):
                return context.get(field)
            elif hasattr(context, field):
                return getattr(context, field)
            else:
                return None
    
    def _compare_dates(self, date1: Any, date2: Any, operator: str) -> bool:
        """Compare two dates with specified operator."""
        try:
            if isinstance(date1, str):
                date1 = datetime.strptime(date1, "%Y-%m-%d")
            if isinstance(date2, str):
                date2 = datetime.strptime(date2, "%Y-%m-%d")
            
            if operator == "<":
                return date1 < date2
            elif operator == ">":
                return date1 > date2
            elif operator == "==":
                return date1 == date2
            else:
                return False
                
        except (ValueError, TypeError):
            return False
    
    def _execute_action(self, action: Dict[str, Any], context: Dict[str, Any]) -> Optional[str]:
        """Execute a business rule action."""
        action_type = action.get("type")
        
        try:
            if action_type == "require_approval":
                return self._require_approval_action(action, context)
            elif action_type == "priority_allocation":
                return self._priority_allocation_action(action, context)
            elif action_type == "check_lead_times":
                return self._check_lead_times_action(action, context)
            elif action_type == "require_quality_inspection":
                return self._require_quality_inspection_action(action, context)
            elif action_type == "send_notification":
                return self._send_notification_action(action, context)
            elif action_type == "set_field":
                return self._set_field_action(action, context)
            elif action_type == "create_task":
                return self._create_task_action(action, context)
            else:
                frappe.log_error(f"Unknown action type: {action_type}")
                return None
                
        except Exception as e:
            frappe.log_error(f"Action execution error ({action_type}): {str(e)}")
            return None
    
    def _require_approval_action(self, action: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Handle require approval action."""
        role = action.get("role", "Manager")
        return f"approval_required:{role}"
    
    def _priority_allocation_action(self, action: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Handle priority allocation action."""
        level = action.get("level", "normal")
        return f"priority_set:{level}"
    
    def _check_lead_times_action(self, action: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Handle lead time check action."""
        return "lead_times_checked"
    
    def _require_quality_inspection_action(self, action: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Handle quality inspection requirement action."""
        return "quality_inspection_required"
    
    def _send_notification_action(self, action: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Handle send notification action."""
        recipient = action.get("recipient", "Administrator")
        message = action.get("message", "Business rule triggered")
        return f"notification_sent:{recipient}:{message}"
    
    def _set_field_action(self, action: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Handle set field action."""
        field = action.get("field")
        value = action.get("value")
        return f"field_set:{field}:{value}"
    
    def _create_task_action(self, action: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Handle create task action."""
        task_type = action.get("task_type", "general")
        return f"task_created:{task_type}"
    
    def add_custom_rule(self, rule: Dict[str, Any]) -> bool:
        """Add a custom business rule at runtime."""
        try:
            # Validate rule structure
            required_fields = ["name", "conditions", "actions"]
            if not all(field in rule for field in required_fields):
                return False
            
            # Store in cache or database
            rule_name = rule["name"]
            self.rule_cache[rule_name] = rule
            
            return True
            
        except Exception as e:
            frappe.log_error(f"Custom rule addition error: {str(e)}")
            return False
    
    def remove_custom_rule(self, rule_name: str) -> bool:
        """Remove a custom business rule."""
        try:
            if rule_name in self.rule_cache:
                del self.rule_cache[rule_name]
                return True
            return False
            
        except Exception as e:
            frappe.log_error(f"Custom rule removal error: {str(e)}")
            return False
    
    def get_rule_documentation(self) -> Dict[str, Any]:
        """Get documentation for all available rules and operators."""
        return {
            "operators": {
                "comparison": ["==", "!=", ">", ">=", "<", "<="],
                "inclusion": ["in", "not_in"],
                "string": ["contains", "not_contains", "starts_with", "ends_with", "regex"],
                "null_checks": ["is_null", "is_not_null"],
                "date": ["date_before", "date_after", "date_equals"]
            },
            "action_types": {
                "approval": ["require_approval"],
                "priority": ["priority_allocation"],
                "notification": ["send_notification"],
                "field_operations": ["set_field"],
                "task_management": ["create_task"],
                "quality": ["require_quality_inspection"],
                "material": ["check_lead_times"]
            },
            "context_fields": {
                "job_order": [
                    "customer_name", "project_name", "job_type", "priority",
                    "total_cost", "total_material_cost", "total_labor_cost",
                    "start_date", "end_date", "status", "workflow_state",
                    "has_materials", "risk_level", "scheduled_weekend"
                ]
            }
        }