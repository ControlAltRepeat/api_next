# Copyright (c) 2024, API Next and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class JobMaterialRequisitionItem(Document):
    """Material Requisition Item with cost calculation and validation"""
    
    def validate(self):
        """Validate requisition item"""
        self.validate_quantities()
        self.calculate_estimated_cost()
    
    def validate_quantities(self):
        """Validate quantity fields"""
        if self.quantity_requested and self.quantity_requested <= 0:
            frappe.throw(_("Quantity requested must be greater than 0"))
        
        if self.quantity_approved and self.quantity_approved > self.quantity_requested:
            frappe.throw(_("Quantity approved cannot be greater than quantity requested"))
        
        if self.quantity_received and self.quantity_received > (self.quantity_approved or self.quantity_requested):
            frappe.throw(_("Quantity received cannot be greater than quantity approved"))
    
    def calculate_estimated_cost(self):
        """Calculate estimated cost based on item valuation"""
        if not self.item_code or not self.quantity_requested:
            return
        
        try:
            # Get last purchase rate or valuation rate
            last_purchase_rate = frappe.db.get_value(
                "Item Price",
                {
                    "item_code": self.item_code,
                    "price_list": frappe.get_cached_value("Buying Settings", None, "buying_price_list")
                },
                "price_list_rate"
            )
            
            if not last_purchase_rate:
                # Try to get valuation rate
                last_purchase_rate = frappe.db.get_value(
                    "Item",
                    self.item_code,
                    "valuation_rate"
                ) or 0
            
            if last_purchase_rate:
                quantity = self.quantity_approved if self.quantity_approved else self.quantity_requested
                self.estimated_cost = flt(last_purchase_rate) * flt(quantity)
            
        except Exception as e:
            frappe.log_error(f"Error calculating estimated cost for item {self.item_code}: {str(e)}")
    
    def get_available_stock(self):
        """Get available stock for the item in specified warehouse"""
        if not self.item_code or not self.warehouse:
            return 0
        
        try:
            from erpnext.stock.utils import get_stock_balance
            
            stock_balance = get_stock_balance(
                item_code=self.item_code,
                warehouse=self.warehouse,
                posting_date=frappe.utils.nowdate()
            )
            
            return flt(stock_balance)
            
        except Exception as e:
            frappe.log_error(f"Error getting stock balance: {str(e)}")
            return 0
    
    def get_fulfillment_percentage(self):
        """Calculate fulfillment percentage"""
        if not self.quantity_requested:
            return 0
        
        received_qty = flt(self.quantity_received)
        requested_qty = flt(self.quantity_requested)
        
        return min(100, (received_qty / requested_qty) * 100)


@frappe.whitelist()
def get_item_details(item_code, warehouse=None):
    """Get item details for requisition form"""
    if not item_code:
        return {}
    
    item = frappe.get_doc("Item", item_code)
    
    result = {
        "item_name": item.item_name,
        "description": item.description,
        "stock_uom": item.stock_uom,
        "image": item.image,
        "valuation_rate": item.valuation_rate or 0
    }
    
    # Get current stock if warehouse is specified
    if warehouse:
        try:
            from erpnext.stock.utils import get_stock_balance
            
            stock_balance = get_stock_balance(
                item_code=item_code,
                warehouse=warehouse,
                posting_date=frappe.utils.nowdate()
            )
            
            result["available_stock"] = flt(stock_balance)
            
        except Exception as e:
            frappe.log_error(f"Error getting stock balance: {str(e)}")
            result["available_stock"] = 0
    
    # Get latest purchase rate
    try:
        buying_price_list = frappe.get_cached_value("Buying Settings", None, "buying_price_list")
        if buying_price_list:
            price_list_rate = frappe.db.get_value(
                "Item Price",
                {
                    "item_code": item_code,
                    "price_list": buying_price_list
                },
                "price_list_rate"
            )
            
            if price_list_rate:
                result["last_purchase_rate"] = flt(price_list_rate)
            else:
                result["last_purchase_rate"] = result["valuation_rate"]
        
    except Exception as e:
        frappe.log_error(f"Error getting purchase rate: {str(e)}")
        result["last_purchase_rate"] = result["valuation_rate"]
    
    return result


@frappe.whitelist()
def validate_item_availability(item_code, quantity, warehouse=None):
    """Validate if requested quantity is available in stock"""
    if not item_code or not quantity:
        return {"available": False, "message": "Invalid item or quantity"}
    
    try:
        quantity = flt(quantity)
        
        if warehouse:
            from erpnext.stock.utils import get_stock_balance
            
            available_qty = get_stock_balance(
                item_code=item_code,
                warehouse=warehouse,
                posting_date=frappe.utils.nowdate()
            )
            
            if flt(available_qty) >= quantity:
                return {
                    "available": True,
                    "available_qty": flt(available_qty),
                    "message": f"Available quantity: {available_qty}"
                }
            else:
                return {
                    "available": False,
                    "available_qty": flt(available_qty),
                    "message": f"Insufficient stock. Available: {available_qty}, Required: {quantity}"
                }
        else:
            # Check total stock across all warehouses
            total_stock = frappe.db.sql("""
                SELECT SUM(actual_qty)
                FROM `tabStock Ledger Entry`
                WHERE item_code = %s
                AND is_cancelled = 0
            """, (item_code,))[0][0] or 0
            
            if flt(total_stock) >= quantity:
                return {
                    "available": True,
                    "available_qty": flt(total_stock),
                    "message": f"Total available quantity: {total_stock}"
                }
            else:
                return {
                    "available": False,
                    "available_qty": flt(total_stock),
                    "message": f"Insufficient total stock. Available: {total_stock}, Required: {quantity}"
                }
    
    except Exception as e:
        frappe.log_error(f"Error validating item availability: {str(e)}")
        return {"available": False, "message": "Error checking availability"}